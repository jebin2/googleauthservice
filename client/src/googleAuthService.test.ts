/**
 * Google Auth Service Tests
 * 
 * Tests for the core authentication service.
 */

import { describe, it, expect, beforeEach, vi } from 'vitest';

// Note: Full testing of googleAuthService requires mocking the window.google 
// object and fetch API. These are basic unit tests for configuration.

describe('googleAuthService', () => {
    beforeEach(() => {
        vi.resetModules();
    });

    describe('configureGoogleAuth', () => {
        it('should configure clientId and apiBaseUrl', async () => {
            const { configureGoogleAuth } = await import('./googleAuthService');

            // Should not throw
            configureGoogleAuth({
                clientId: 'test-client-id',
                apiBaseUrl: 'https://api.test.com',
            });
        });

        it('should accept custom storagePrefix', async () => {
            const { configureGoogleAuth, getAvatarCacheKey } = await import('./googleAuthService');

            configureGoogleAuth({
                clientId: 'test-client-id',
                apiBaseUrl: 'https://api.test.com',
                storagePrefix: 'custom',
            });

            expect(getAvatarCacheKey()).toBe('custom_avatar_cache');
        });
    });

    describe('getAvatarCacheKey', () => {
        it('should return default cache key', async () => {
            const { configureGoogleAuth, getAvatarCacheKey } = await import('./googleAuthService');

            configureGoogleAuth({
                clientId: 'test-client-id',
                apiBaseUrl: 'https://api.test.com',
            });

            expect(getAvatarCacheKey()).toBe('auth_avatar_cache');
        });
    });

    describe('onAuthStateChange', () => {
        it('should return unsubscribe function', async () => {
            const { onAuthStateChange } = await import('./googleAuthService');

            const callback = vi.fn();
            const unsubscribe = onAuthStateChange(callback);

            expect(typeof unsubscribe).toBe('function');
        });
    });

    describe('getAccessToken', () => {
        it('should return null by default', async () => {
            const { getAccessToken } = await import('./googleAuthService');

            expect(getAccessToken()).toBeNull();
        });
    });

    describe('isAuthenticated', () => {
        it('should return false when no token', async () => {
            const { isAuthenticated } = await import('./googleAuthService');

            expect(isAuthenticated()).toBe(false);
        });
    });
});
