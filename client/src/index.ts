/**
 * Google Auth Service - Client Module
 * 
 * Plug-and-play Google Sign-In for React applications.
 * 
 * @example
 * ```typescript
 * import { configureGoogleAuth, initializeAuth, GoogleSignInButton } from 'google-auth-service-client';
 * 
 * // Configure on app start
 * configureGoogleAuth({
 *     clientId: 'your-google-client-id',
 *     apiBaseUrl: 'https://api.yoursite.com',
 * });
 * 
 * // Initialize and restore session
 * const user = await initializeAuth();
 * ```
 */

// Core service
export {
    configureGoogleAuth,
    initGoogleAuth,
    signInWithGoogle,
    signOut,
    getAccessToken,
    getCurrentUser,
    isAuthenticated,
    refreshToken,
    fetchUserInfo,
    initializeAuth,
    authenticatedFetch,
    onAuthStateChange,
    updateUserCredits,
    renderGoogleButton,
    getAvatarCacheKey,
} from './googleAuthService';

// Storage service
export {
    multiSet,
    multiGet,
    multiGetSync,
    multiRemove,
} from './multiStorageService';

// Types
export type {
    GoogleUser,
    GoogleAuthConfig,
    GoogleButtonConfig,
} from './types';

// Components
export { default as GoogleSignInButton } from './components/GoogleSignInButton';
export { default as UserAvatar, clearCachedAvatar } from './components/UserAvatar';

// Context
export { GoogleAuthProvider, useGoogleAuth } from './contexts/GoogleAuthContext';
