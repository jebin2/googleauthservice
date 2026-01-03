import React, { useState, useEffect } from 'react';
import { getAvatarCacheKey } from '../googleAuthService';

interface UserAvatarProps {
    /** Profile picture URL */
    src?: string | null;
    /** User's display name */
    name?: string | null;
    /** User's email (required for fallback) */
    email: string;
    /** Avatar size */
    size?: 'sm' | 'md' | 'lg';
    /** Additional CSS class */
    className?: string;
}

// Cache avatar as data URL in localStorage
async function cacheAvatar(url: string, cacheKey: string): Promise<string | null> {
    try {
        const response = await fetch(url);
        if (!response.ok) return null;

        const blob = await response.blob();
        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onloadend = () => {
                const dataUrl = reader.result as string;
                try {
                    localStorage.setItem(cacheKey, dataUrl);
                } catch {
                    // localStorage full, ignore
                }
                resolve(dataUrl);
            };
            reader.onerror = () => resolve(null);
            reader.readAsDataURL(blob);
        });
    } catch {
        return null;
    }
}

// Get cached avatar from localStorage
function getCachedAvatar(cacheKey: string): string | null {
    try {
        return localStorage.getItem(cacheKey);
    } catch {
        return null;
    }
}

/**
 * Clear cached avatar from localStorage
 */
export function clearCachedAvatar(): void {
    try {
        localStorage.removeItem(getAvatarCacheKey());
    } catch {
        // ignore
    }
}

const sizeConfig = {
    sm: { dimension: 32, fontSize: 14 },
    md: { dimension: 40, fontSize: 16 },
    lg: { dimension: 48, fontSize: 18 },
};

const avatarColors = [
    '#6366f1', // indigo
    '#8b5cf6', // purple
    '#ec4899', // pink
    '#3b82f6', // blue
    '#14b8a6', // teal
    '#10b981', // emerald
    '#f97316', // orange
];

/**
 * User avatar component with image caching and fallback to initials
 * 
 * @example
 * ```tsx
 * <UserAvatar
 *     src={user.profilePicture}
 *     name={user.name}
 *     email={user.email}
 *     size="md"
 * />
 * ```
 */
const UserAvatar: React.FC<UserAvatarProps> = ({
    src,
    name,
    email,
    size = 'md',
    className = '',
}) => {
    const [imageSrc, setImageSrc] = useState<string | null>(src || null);
    const [imageError, setImageError] = useState(false);

    const config = sizeConfig[size];

    // Get initials from name or email
    const getInitials = (): string => {
        if (name) {
            return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
        }
        return email[0].toUpperCase();
    };

    // Generate a consistent color based on email
    const getAvatarColor = (): string => {
        const index = email.charCodeAt(0) % avatarColors.length;
        return avatarColors[index];
    };

    // Try to cache avatar on first load or use cached version on error
    useEffect(() => {
        if (src && !imageError) {
            const cacheKey = getAvatarCacheKey();
            cacheAvatar(src, cacheKey).catch(() => { });
        }
    }, [src, imageError]);

    // Handle image load error
    const handleError = (): void => {
        const cacheKey = getAvatarCacheKey();
        const cached = getCachedAvatar(cacheKey);
        if (cached && cached !== imageSrc) {
            setImageSrc(cached);
        } else {
            setImageError(true);
        }
    };

    const baseStyle: React.CSSProperties = {
        width: config.dimension,
        height: config.dimension,
        borderRadius: '50%',
        border: '2px solid white',
        boxShadow: '0 1px 2px 0 rgb(0 0 0 / 0.05)',
    };

    // Show image if available and no error
    if (imageSrc && !imageError) {
        return (
            <img
                src={imageSrc}
                alt={name || email}
                className={className}
                style={baseStyle}
                onError={handleError}
            />
        );
    }

    // Fallback to initials
    return (
        <div
            className={className}
            style={{
                ...baseStyle,
                backgroundColor: getAvatarColor(),
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'white',
                fontWeight: 700,
                fontSize: config.fontSize,
            }}
        >
            {getInitials()}
        </div>
    );
};

export default UserAvatar;
