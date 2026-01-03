/**
 * Type definitions for Google Auth Service Client
 */

// TypeScript declarations for Google Identity Services
declare global {
    interface Window {
        google?: {
            accounts: {
                id: {
                    initialize: (config: GoogleIdConfig) => void;
                    prompt: (callback?: (notification: PromptNotification) => void) => void;
                    renderButton: (element: HTMLElement, config: GoogleButtonConfig) => void;
                    revoke: (email: string, callback: () => void) => void;
                    disableAutoSelect: () => void;
                };
            };
        };
    }
}

export interface GoogleIdConfig {
    client_id: string;
    callback: (response: GoogleCredentialResponse) => void;
    auto_select?: boolean;
    cancel_on_tap_outside?: boolean;
}

export interface GoogleCredentialResponse {
    credential: string;
    select_by?: string;
}

export interface PromptNotification {
    isNotDisplayed: () => boolean;
    isSkippedMoment: () => boolean;
    isDismissedMoment: () => boolean;
    getNotDisplayedReason: () => string;
    getSkippedReason: () => string;
    getDismissedReason: () => string;
}

export interface GoogleButtonConfig {
    type?: 'standard' | 'icon';
    theme?: 'outline' | 'filled_blue' | 'filled_black';
    size?: 'large' | 'medium' | 'small';
    text?: 'signin_with' | 'signup_with' | 'continue_with' | 'signin';
    shape?: 'rectangular' | 'pill' | 'circle' | 'square';
    logo_alignment?: 'left' | 'center';
    width?: number;
}

/**
 * User information from authentication
 */
export interface GoogleUser {
    userId: string;
    email: string;
    name?: string | null;
    profilePicture?: string | null;
    isNewUser: boolean;
}

/**
 * Configuration for the Google Auth service
 */
export interface GoogleAuthConfig {
    /** Google OAuth Client ID */
    clientId: string;
    /** Backend API base URL */
    apiBaseUrl: string;
    /** Prefix for storage keys (default: 'auth') */
    storagePrefix?: string;
}

/**
 * Auth response from server
 */
export interface AuthApiResponse {
    success: boolean;
    access_token: string;
    user_id: string;
    email: string;
    name?: string | null;
    is_new_user: boolean;
}

/**
 * User info response from /auth/me endpoint
 */
export interface UserInfoResponse {
    user_id: string;
    email: string;
    name?: string | null;
    profile_picture?: string | null;
}

/**
 * Auth state change callback
 */
export type AuthCallback = (user: GoogleUser | null) => void;
