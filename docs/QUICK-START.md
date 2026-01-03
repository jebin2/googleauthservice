# Quick Start Guide

Get Google Sign-In working in your project in 5 minutes.

## Prerequisites

1. **Google Cloud Console**: Create OAuth 2.0 credentials
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create/select a project
   - Go to APIs & Services → Credentials
   - Create OAuth 2.0 Client ID (Web application)
   - Add your domains to authorized origins

## Server Setup (Python/FastAPI)

### 1. Copy Files
```bash
cp -r server/src/google_auth_service /your/project/
```

### 2. Install Dependencies
```bash
pip install google-auth>=2.0.0 PyJWT>=2.8.0
```

### 3. Set Environment
```bash
export AUTH_SIGN_IN_GOOGLE_CLIENT_ID="your-client-id"
export JWT_SECRET="your-32-char-secret-minimum"
```

### 4. Create Auth Endpoint
```python
from fastapi import APIRouter, HTTPException
from google_auth_service import GoogleAuthService, create_access_token

router = APIRouter()
google_auth = GoogleAuthService()

@router.post("/auth/google")
async def login(id_token: str):
    user_info = google_auth.verify_token(id_token)
    # Save/fetch user from your database
    token = create_access_token(user.id, user.email)
    return {"access_token": token, "user": user}
```

## Client Setup (React/TypeScript)

### 1. Copy Files
```bash
cp -r client/src/* /your/project/src/services/auth/
```

### 2. Add Google Script
```html
<!-- index.html -->
<script src="https://accounts.google.com/gsi/client" async defer></script>
```

### 3. Configure & Initialize
```tsx
import { configureGoogleAuth, initializeAuth, GoogleSignInButton } from './services/auth';

configureGoogleAuth({
    clientId: 'your-client-id',
    apiBaseUrl: 'https://api.yoursite.com',
});

// In your app
function App() {
    useEffect(() => {
        initializeAuth().then(user => console.log('User:', user));
    }, []);
    
    return <GoogleSignInButton />;
}
```

## That's It!

For detailed docs:
- [Server Integration](../server/SERVER-LINK.md)
- [Client Integration](../client/CLIENT-LINK.md)
