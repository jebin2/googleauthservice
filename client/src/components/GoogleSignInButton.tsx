import React, { useEffect, useRef, useState } from 'react';
import { renderGoogleButton, signInWithGoogle, initGoogleAuth } from '../googleAuthService';

interface GoogleSignInButtonProps {
    /** Button width (default: 300) */
    width?: number;
    /** Custom class name for container */
    className?: string;
    /** Use custom styled button instead of native Google button */
    useCustomStyle?: boolean;
    /** Custom button text (only for custom style) */
    text?: string;
}

/**
 * Google Sign-In button component
 * 
 * By default, renders the native Google Sign-In button.
 * Set useCustomStyle=true to show a custom styled button that triggers Google One Tap.
 * 
 * @example
 * ```tsx
 * // Native Google button (recommended)
 * <GoogleSignInButton width={300} />
 * 
 * // Custom styled button
 * <GoogleSignInButton useCustomStyle text="Continue with Google" />
 * ```
 */
const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
    width = 300,
    className = '',
    useCustomStyle = false,
    text = 'Sign in with Google',
}) => {
    const googleButtonRef = useRef<HTMLDivElement>(null);
    const [isReady, setIsReady] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (useCustomStyle) {
            // For custom style, just initialize Google Auth
            initGoogleAuth()
                .then(() => setIsReady(true))
                .catch((e) => {
                    console.error('Failed to initialize Google Auth:', e);
                    setError('Failed to load Google Sign-In');
                });
            return;
        }

        // For native button, render it in the container
        let attempts = 0;
        const maxAttempts = 20;
        let timeoutId: ReturnType<typeof setTimeout> | null = null;
        let cancelled = false;

        const tryRenderButton = async () => {
            if (cancelled) return;
            if (!googleButtonRef.current) {
                return;
            }

            if (!window.google?.accounts?.id) {
                attempts++;
                if (attempts < maxAttempts) {
                    timeoutId = setTimeout(tryRenderButton, 500);
                } else {
                    setError('Google Sign-In failed to load');
                }
                return;
            }

            try {
                await initGoogleAuth();
            } catch (e) {
                console.error('Failed to initialize Google Auth:', e);
                setError('Failed to initialize Google Sign-In');
                return;
            }

            if (cancelled) return;

            try {
                renderGoogleButton(googleButtonRef.current, {
                    theme: 'outline',
                    size: 'large',
                    width: width,
                    shape: 'pill',
                });
                setIsReady(true);
            } catch (e) {
                console.error('Failed to render Google button:', e);
                setError('Failed to render Google Sign-In button');
            }
        };

        tryRenderButton();

        return () => {
            cancelled = true;
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
        };
    }, [useCustomStyle, width]);

    const handleCustomClick = () => {
        if (isReady) {
            signInWithGoogle();
        }
    };

    if (error) {
        return (
            <div className={className} style={{ color: '#ef4444', fontSize: '14px' }}>
                {error}
            </div>
        );
    }

    // Custom styled button
    if (useCustomStyle) {
        return (
            <button
                type="button"
                onClick={handleCustomClick}
                disabled={!isReady}
                className={className}
                style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '12px',
                    padding: '12px 24px',
                    backgroundColor: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '9999px',
                    boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
                    cursor: isReady ? 'pointer' : 'wait',
                    transition: 'all 0.3s',
                    opacity: isReady ? 1 : 0.7,
                }}
            >
                <svg width="20" height="20" viewBox="0 0 18 18">
                    <path fill="#4285F4" d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18Z" />
                    <path fill="#34A853" d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17Z" />
                    <path fill="#FBBC05" d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18l2.67-2.07Z" />
                    <path fill="#EA4335" d="M8.98 3.58c1.16 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.9Z" />
                </svg>
                <span style={{ fontWeight: 600, color: '#475569' }}>{text}</span>
            </button>
        );
    }

    // Native Google button (default) - just render the container
    return (
        <div
            ref={googleButtonRef}
            className={className}
            style={{
                minHeight: '44px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
            }}
        >
            {!isReady && <span style={{ color: '#9ca3af', fontSize: '14px' }}>Loading...</span>}
        </div>
    );
};

export default GoogleSignInButton;
