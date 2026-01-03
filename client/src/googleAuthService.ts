/**
 * Google Authentication Service
 * 
 * Handles Google Sign-In, JWT token management, and user session.
 * 
 * @example
 * ```typescript
 * import { configureGoogleAuth, initializeAuth, onAuthStateChange } from './googleAuthService';
 * 
 * // Configure
 * configureGoogleAuth({
 *     clientId: 'your-client-id.apps.googleusercontent.com',
 *     apiBaseUrl: 'https://api.yoursite.com',
 * });
 * 
 * // Subscribe to auth changes
 * onAuthStateChange((user) => {
 *     console.log('Auth state:', user);
 * });
 * 
 * // Initialize (restores session from cookie)
 * const user = await initializeAuth();
 * ```
 */

import { multiSet, multiGet, multiGetSync, multiRemove } from './multiStorageService';
import type {
    GoogleUser,
    GoogleAuthConfig,
    GoogleButtonConfig,
    AuthApiResponse,
    UserInfoResponse,
    AuthCallback,
    GoogleCredentialResponse,
    PromptNotification,
} from './types';

// Configuration
let CONFIG: GoogleAuthConfig = {
    clientId: '',
    apiBaseUrl: '',
    storagePrefix: 'auth',
};

// In-memory token storage (cleared on page refresh)
let accessToken: string | null = null;

// Dynamic storage keys based on prefix
function getStorageKeys() {
    return {
        user: `${CONFIG.storagePrefix}_user`,
        avatarCache: `${CONFIG.storagePrefix}_avatar_cache`,
    };
}

// Event callbacks
let authStateCallbacks: AuthCallback[] = [];

/**
 * Configure the Google Auth service
 * @param config.clientId - Google OAuth Client ID
 * @param config.apiBaseUrl - Backend API base URL
 * @param config.storagePrefix - Prefix for all storage keys (default: 'auth')
 */
export function configureGoogleAuth(config: GoogleAuthConfig): void {
    CONFIG.clientId = config.clientId;
    CONFIG.apiBaseUrl = config.apiBaseUrl;
    if (config.storagePrefix) {
        CONFIG.storagePrefix = config.storagePrefix;
    }
}

/**
 * Get the avatar cache key (for UserAvatar component)
 */
export function getAvatarCacheKey(): string {
    return getStorageKeys().avatarCache;
}

/**
 * Subscribe to auth state changes
 */
export function onAuthStateChange(callback: AuthCallback): () => void {
    authStateCallbacks.push(callback);
    // Return unsubscribe function
    return () => {
        authStateCallbacks = authStateCallbacks.filter(cb => cb !== callback);
    };
}

/**
 * Notify all subscribers of auth state change
 */
function notifyAuthStateChange(user: GoogleUser | null): void {
    authStateCallbacks.forEach(cb => cb(user));
}

/**
 * Update user credits from API response (avoids extra API call)
 * Call this when you receive credits_remaining from job APIs
 */
export async function updateUserCredits(newCredits: number): Promise<void> {
    const user = getCurrentUserSync();
    if (!user) return;

    const updatedUser: GoogleUser = {
        ...user,
        credits: newCredits,
    };

    await multiSet(getStorageKeys().user, updatedUser);
    notifyAuthStateChange(updatedUser);
}

/**
 * Initialize Google Sign-In library
 */
export function initGoogleAuth(): Promise<void> {
    return new Promise((resolve, reject) => {
        if (!CONFIG.clientId) {
            reject(new Error('Google Client ID not configured. Call configureGoogleAuth first.'));
            return;
        }

        // Wait for Google Identity Services to load
        const checkGoogleLoaded = () => {
            if (window.google?.accounts?.id) {
                window.google.accounts.id.initialize({
                    client_id: CONFIG.clientId,
                    callback: handleGoogleCredentialResponse,
                    auto_select: false,
                    cancel_on_tap_outside: true,
                });
                resolve();
            } else {
                setTimeout(checkGoogleLoaded, 100);
            }
        };

        checkGoogleLoaded();

        // Timeout after 10 seconds
        setTimeout(() => {
            reject(new Error('Google Identity Services failed to load'));
        }, 10000);
    });
}

/**
 * Handle the credential response from Google
 */
async function handleGoogleCredentialResponse(response: GoogleCredentialResponse): Promise<void> {
    try {
        const authResponse = await authenticateWithServer(response.credential);
        if (authResponse.success) {
            const user: GoogleUser = {
                userId: authResponse.user_id,
                email: authResponse.email,
                name: authResponse.name,
                credits: authResponse.credits,
                isNewUser: authResponse.is_new_user,
            };

            // Store access token in memory
            accessToken = authResponse.access_token;

            // Store user info in multi-storage
            await multiSet(getStorageKeys().user, user);

            notifyAuthStateChange(user);
        }
    } catch (error) {
        console.error('Google authentication failed:', error);
        notifyAuthStateChange(null);
    }
}

/**
 * Send Google ID token to server for authentication
 */
async function authenticateWithServer(idToken: string): Promise<AuthApiResponse> {
    const response = await fetch(`${CONFIG.apiBaseUrl}/auth/google`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            id_token: idToken,
            client_type: 'web',
        }),
        credentials: 'include',
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({ error: { message: 'Try again.' } }));
        throw new Error(errorData.error?.message || errorData.detail || 'Try again.');
    }

    return response.json();
}

/**
 * Trigger Google Sign-In popup
 */
export function signInWithGoogle(): void {
    if (!window.google?.accounts?.id) {
        console.error('Google Identity Services not loaded');
        return;
    }

    window.google.accounts.id.prompt((notification: PromptNotification) => {
        if (notification.isNotDisplayed() || notification.isSkippedMoment()) {
            console.log(
                'One Tap not displayed:',
                notification.getNotDisplayedReason?.() || notification.getSkippedReason?.()
            );
        }
    });
}

/**
 * Render Google Sign-In button in a container
 */
export function renderGoogleButton(container: HTMLElement, config?: Partial<GoogleButtonConfig>): void {
    if (!window.google?.accounts?.id) {
        console.error('Google Identity Services not loaded');
        return;
    }

    window.google.accounts.id.renderButton(container, {
        type: 'standard',
        theme: 'outline',
        size: 'large',
        text: 'signin_with',
        shape: 'pill',
        ...config,
    });
}

/**
 * Sign out and clear session
 */
export async function signOut(): Promise<void> {
    const user = getCurrentUserSync();
    const token = accessToken;

    // Clear access token from memory
    accessToken = null;

    // Clear user info from all storage
    await multiRemove(getStorageKeys().user);

    // Disable auto-select for future
    if (window.google?.accounts?.id) {
        window.google.accounts.id.disableAutoSelect();

        // Revoke if we have user email
        if (user?.email) {
            window.google.accounts.id.revoke(user.email, () => {
                console.log('Google session revoked');
            });
        }
    }

    // Call server logout to clear HttpOnly cookie
    try {
        if (token) {
            await fetch(`${CONFIG.apiBaseUrl}/auth/logout`, {
                method: 'POST',
                headers: {
                    Authorization: `Bearer ${token}`,
                },
                credentials: 'include',
            });
        }
    } catch (e) {
        // Ignore errors on logout
    }

    notifyAuthStateChange(null);

    // Re-initialize Google Auth for future sign-ins
    try {
        await initGoogleAuth();
    } catch (e) {
        console.error('Failed to re-initialize Google Auth after sign out:', e);
    }
}

/**
 * Get stored access token (from memory)
 */
export function getAccessToken(): string | null {
    return accessToken;
}

/**
 * Get current user from storage (sync - tries localStorage first, then cookie)
 */
function getCurrentUserSync(): GoogleUser | null {
    const userStr = multiGetSync(getStorageKeys().user);
    if (!userStr) return null;

    try {
        return JSON.parse(userStr);
    } catch {
        return null;
    }
}

/**
 * Get current user from storage (async - checks all storage mechanisms)
 */
export async function getCurrentUser(): Promise<GoogleUser | null> {
    const userStr = await multiGet(getStorageKeys().user);
    if (!userStr) return null;

    try {
        return JSON.parse(userStr);
    } catch {
        return null;
    }
}

/**
 * Check if user is authenticated (sync check)
 */
export function isAuthenticated(): boolean {
    return !!(accessToken && getCurrentUserSync());
}

/**
 * Refresh the access token using HttpOnly cookie
 */
export async function refreshToken(): Promise<boolean> {
    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/auth/refresh`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({}),
            credentials: 'include',
        });

        if (!response.ok) {
            await signOut();
            return false;
        }

        const data = await response.json();
        if (data.success && data.access_token) {
            accessToken = data.access_token;
            return true;
        }

        return false;
    } catch (error) {
        console.error('Token refresh failed:', error);
        return false;
    }
}

/**
 * Fetch current user info from server (refreshes credits, etc.)
 */
export async function fetchUserInfo(): Promise<GoogleUser | null> {
    const token = getAccessToken();
    if (!token) return null;

    try {
        const response = await fetch(`${CONFIG.apiBaseUrl}/auth/me`, {
            headers: {
                Authorization: `Bearer ${token}`,
            },
            credentials: 'include',
        });

        if (!response.ok) {
            if (response.status === 401) {
                await signOut();
            }
            return null;
        }

        const data: UserInfoResponse = await response.json();
        const user: GoogleUser = {
            userId: data.user_id,
            email: data.email,
            name: data.name,
            profilePicture: data.profile_picture,
            credits: data.credits,
            isNewUser: false,
        };

        await multiSet(getStorageKeys().user, user);
        notifyAuthStateChange(user);

        return user;
    } catch (error) {
        console.error('Failed to fetch user info:', error);
        return null;
    }
}

/**
 * Initialize auth and restore session if available
 * This proactively tries to refresh from HttpOnly cookie on page load
 */
export async function initializeAuth(): Promise<GoogleUser | null> {
    // If we already have a token in memory, verify it's still valid
    if (accessToken) {
        const freshUser = await fetchUserInfo();
        if (freshUser) {
            return freshUser;
        }
    }

    // Check if user has ever signed in before
    if (!getCurrentUserSync()) {
        try {
            await initGoogleAuth();
        } catch (error) {
            console.error('Failed to initialize Google Auth:', error);
        }
        return null;
    }

    // Try to restore session from HttpOnly cookie
    try {
        const refreshed = await refreshToken();
        if (refreshed) {
            const user = await fetchUserInfo();
            if (user) {
                return user;
            }
        }
    } catch (error) {
        // Silent fail
    }

    // Initialize Google Sign-In for future sign-ins
    try {
        await initGoogleAuth();
    } catch (error) {
        console.error('Failed to initialize Google Auth:', error);
    }

    return null;
}

/**
 * Make an authenticated API request
 */
export async function authenticatedFetch(
    url: string,
    options: RequestInit = {}
): Promise<Response> {
    const token = getAccessToken();

    const headers = new Headers(options.headers);
    if (token) {
        headers.set('Authorization', `Bearer ${token}`);
    }

    const response = await fetch(url, {
        ...options,
        headers,
        credentials: 'include',
    });

    // Handle 401 by refreshing token and retrying
    if (response.status === 401 && token) {
        const refreshed = await refreshToken();
        if (refreshed) {
            const newToken = getAccessToken();
            headers.set('Authorization', `Bearer ${newToken}`);
            return fetch(url, { ...options, headers, credentials: 'include' });
        }
        await signOut();
    }

    return response;
}
