import React, { useEffect, useRef, useState } from 'react';
import { renderGoogleButton, signInWithGoogle } from '../googleAuthService';

interface GoogleSignInButtonProps {
    /** Button width (default: '100%') */
    width?: string;
    /** Custom class name for container */
    className?: string;
    /** Custom button text (default: 'Sign in') */
    text?: string;
}

/**
 * Custom styled Google Sign-In button
 * 
 * Uses invisible Google button overlay for security compliance
 * while showing a custom styled button.
 * 
 * @example
 * ```tsx
 * <GoogleSignInButton width="300px" text="Continue with Google" />
 * ```
 */
const GoogleSignInButton: React.FC<GoogleSignInButtonProps> = ({
    width = '100%',
    className = '',
    text = 'Sign in',
}) => {
    const googleButtonRef = useRef<HTMLDivElement>(null);
    const containerRef = useRef<HTMLDivElement>(null);
    const [isReady, setIsReady] = useState(false);

    useEffect(() => {
        let attempts = 0;
        const maxAttempts = 20;
        let timeoutId: ReturnType<typeof setTimeout> | null = null;

        const tryRenderButton = () => {
            if (!googleButtonRef.current || !containerRef.current) {
                return;
            }

            if (!window.google?.accounts?.id) {
                attempts++;
                if (attempts < maxAttempts) {
                    timeoutId = setTimeout(tryRenderButton, 500);
                } else {
                    console.error('Google Identity Services failed to load after maximum attempts');
                }
                return;
            }

            const containerWidth = containerRef.current.offsetWidth;

            try {
                renderGoogleButton(googleButtonRef.current, {
                    theme: 'outline',
                    size: 'large',
                    width: containerWidth,
                    shape: 'pill',
                });
                setIsReady(true);
            } catch (e) {
                console.error('Failed to render Google button:', e);
            }
        };

        tryRenderButton();

        return () => {
            if (timeoutId) {
                clearTimeout(timeoutId);
            }
        };
    }, []);

    const handleClick = () => {
        if (!isReady) {
            signInWithGoogle();
        }
    };

    return (
        <div ref={containerRef} className={`relative group ${className}`} style={{ width }}>
            {/* Custom Styled Button */}
            <button
                type="button"
                onClick={handleClick}
                style={{
                    width: '100%',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '12px',
                    padding: '12px 24px',
                    backgroundColor: 'white',
                    border: '1px solid #e2e8f0',
                    borderRadius: '9999px',
                    boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
                    cursor: 'pointer',
                    transition: 'all 0.3s',
                }}
            >
                {/* Google Icon */}
                <svg width="20" height="20" viewBox="0 0 18 18">
                    <path
                        fill="#4285F4"
                        d="M16.51 8H8.98v3h4.3c-.18 1-.74 1.48-1.6 2.04v2.01h2.6a7.8 7.8 0 0 0 2.38-5.88c0-.57-.05-.66-.15-1.18Z"
                    />
                    <path
                        fill="#34A853"
                        d="M8.98 17c2.16 0 3.97-.72 5.3-1.94l-2.6-2a4.8 4.8 0 0 1-7.18-2.54H1.83v2.07A8 8 0 0 0 8.98 17Z"
                    />
                    <path
                        fill="#FBBC05"
                        d="M4.5 10.52a4.8 4.8 0 0 1 0-3.04V5.41H1.83a8 8 0 0 0 0 7.18l2.67-2.07Z"
                    />
                    <path
                        fill="#EA4335"
                        d="M8.98 3.58c1.16 0 2.23.4 3.06 1.2l2.3-2.3A8 8 0 0 0 1.83 5.4L4.5 7.49a4.77 4.77 0 0 1 4.48-3.9Z"
                    />
                </svg>
                <span style={{ fontWeight: 600, color: '#475569' }}>{text}</span>
            </button>

            {/* Invisible Google Button Overlay */}
            <div
                ref={googleButtonRef}
                style={{
                    position: 'absolute',
                    inset: 0,
                    zIndex: 10,
                    overflow: 'hidden',
                    borderRadius: '9999px',
                    opacity: isReady ? 0.01 : 0,
                    pointerEvents: isReady ? 'auto' : 'none',
                }}
            />
        </div>
    );
};

export default GoogleSignInButton;
