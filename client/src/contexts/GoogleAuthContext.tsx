import React, { createContext, useContext, useEffect, useState } from 'react';
import {
    configureGoogleAuth,
    initializeAuth,
    onAuthStateChange,
    signOut as serviceSignOut,
    signInWithGoogle as serviceSignInWithGoogle,
    GoogleUser,
    GoogleAuthConfig,
} from '../googleAuthService';

interface GoogleAuthContextType {
    user: GoogleUser | null;
    loading: boolean;
    signIn: () => void;
    signOut: () => Promise<void>;
}

const GoogleAuthContext = createContext<GoogleAuthContextType | undefined>(undefined);

interface GoogleAuthProviderProps extends GoogleAuthConfig {
    children: React.ReactNode;
}

export const GoogleAuthProvider: React.FC<GoogleAuthProviderProps> = ({
    children,
    clientId,
    apiBaseUrl,
    storagePrefix,
}) => {
    const [user, setUser] = useState<GoogleUser | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // 1. Configure the service once
        configureGoogleAuth({ clientId, apiBaseUrl, storagePrefix });

        // 2. Subscribe to auth changes
        const unsubscribe = onAuthStateChange((newUser) => {
            setUser(newUser);
        });

        // 3. Initialize (restore session)
        initializeAuth()
            .then((restoredUser) => {
                setUser(restoredUser);
            })
            .catch((err) => {
                console.error('Auth initialization failed', err);
            })
            .finally(() => {
                setLoading(false);
            });

        return () => {
            unsubscribe();
        };
    }, [clientId, apiBaseUrl, storagePrefix]);

    const signIn = () => {
        serviceSignInWithGoogle();
    };

    const signOut = async () => {
        await serviceSignOut();
    };

    return (
        <GoogleAuthContext.Provider value={{ user, loading, signIn, signOut }}>
            {children}
        </GoogleAuthContext.Provider>
    );
};

export const useGoogleAuth = (): GoogleAuthContextType => {
    const context = useContext(GoogleAuthContext);
    if (context === undefined) {
        throw new Error('useGoogleAuth must be used within a GoogleAuthProvider');
    }
    return context;
};
