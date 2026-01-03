# Client Integration Guide

Quick guide to integrate Google Auth Service client module into your React application.

## Installation

```bash
# Copy source to your project
cp -r client/src/* /path/to/your/project/src/services/auth/

# Or install peer dependencies if using as module
npm install react
```

## Prerequisites

Add Google Identity Services script to your `index.html`:

```html
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

## Quick Start

### 1. Configure on App Start

```tsx
// In App.tsx or index.tsx
import { configureGoogleAuth, initializeAuth, onAuthStateChange } from './services/auth';

// Configure (call once on app init)
configureGoogleAuth({
    clientId: import.meta.env.VITE_GOOGLE_CLIENT_ID,
    apiBaseUrl: import.meta.env.VITE_API_BASE_URL,
    storagePrefix: 'myapp_auth', // optional
});

// Subscribe to auth changes
onAuthStateChange((user) => {
    console.log('Auth state changed:', user);
});

// Initialize (restores session from cookie)
initializeAuth().then((user) => {
    if (user) {
        console.log('Session restored:', user.email);
    }
});
```

### 2. Add Sign-In Button

```tsx
import { GoogleSignInButton } from './services/auth';

function LoginPage() {
    return (
        <div>
            <h1>Welcome</h1>
            <GoogleSignInButton 
                width="300px" 
                text="Continue with Google" 
            />
        </div>
    );
}
```

### 3. Show User Avatar

```tsx
import { UserAvatar } from './services/auth';
import { useUser } from './hooks/useUser'; // Your hook

function Header() {
    const user = useUser();
    
    if (!user) return <GoogleSignInButton />;
    
    return (
        <UserAvatar
            src={user.profilePicture}
            name={user.name}
            email={user.email}
            size="md"
        />
    );
}
```

### 4. Make Authenticated API Calls

```tsx
import { authenticatedFetch } from './services/auth';

async function fetchData() {
    // Automatically adds Bearer token and handles 401 refresh
    const response = await authenticatedFetch('/api/protected');
    return response.json();
}
```

### 5. Sign Out

```tsx
import { signOut } from './services/auth';

function LogoutButton() {
    return (
        <button onClick={() => signOut()}>
            Sign Out
        </button>
    );
}
```

## React Hook Example

```tsx
// hooks/useAuth.ts
import { useState, useEffect } from 'react';
import { 
    initializeAuth, 
    onAuthStateChange, 
    signOut,
    GoogleUser 
} from '../services/auth';

export function useAuth() {
    const [user, setUser] = useState<GoogleUser | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        // Subscribe to auth changes
        const unsubscribe = onAuthStateChange(setUser);

        // Initialize on mount
        initializeAuth()
            .then(setUser)
            .finally(() => setLoading(false));

        return unsubscribe;
    }, []);

    return { user, loading, signOut };
}
```

## Environment Variables

```bash
# .env
VITE_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
VITE_API_BASE_URL=https://api.yoursite.com
```

## API Reference

### Configuration
- `configureGoogleAuth({ clientId, apiBaseUrl, storagePrefix? })`

### Authentication
- `initializeAuth()` → `Promise<GoogleUser | null>` - Restore session
- `signInWithGoogle()` - Trigger sign-in popup
- `signOut()` - Clear session
- `isAuthenticated()` → `boolean`

### Token Management
- `getAccessToken()` → `string | null`
- `refreshToken()` → `Promise<boolean>`

### User Data
- `getCurrentUser()` → `Promise<GoogleUser | null>`
- `fetchUserInfo()` → `Promise<GoogleUser | null>` - Refresh from server
- `updateUserCredits(credits)` - Update local credits

### API Calls
- `authenticatedFetch(url, options)` - Auto-adds token, handles 401

### Events
- `onAuthStateChange(callback)` → `() => void` - Returns unsubscribe

### Components
- `<GoogleSignInButton width? text? className? />`
- `<UserAvatar src? name? email size? className? />`
