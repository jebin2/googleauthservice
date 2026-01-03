# Google Auth Service

A "batteries-included" Google Sign-In and session management library for modern web applications.

Features:
- **Backend (Python/FastAPI)**:
  - Class-based middleware (`GoogleAuthMiddleware`) for easy integration.
  - Built-in session management with JWTs (Access + Refresh tokens).
  - Secure HttpOnly cookies.
  - User persistence (In-memory default, extensible for databases).
- **Frontend (TypeScript/React)**:
  - Plug-and-play `GoogleAuthProvider` and `useGoogleAuth` hook.
  - Automatic token refresh (transparent to the user).
  - Multi-tab session synchronization.
  - "One Tap" sign-in support.

---

## 1. Backend Installation (FastAPI)

Install directly from GitHub:

```bash
pip install "google-auth-service @ git+https://github.com/jebin2/googleauthservice.git@main#subdirectory=server"
```

### Usage

**`main.py`**:

```python
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from google_auth_service import GoogleAuth, GoogleAuthMiddleware

app = FastAPI()

# 1. Initialize Auth
auth = GoogleAuth(
    client_id="YOUR_GOOGLE_CLIENT_ID",
    jwt_secret="YOUR_SECRET_KEY"
)

# 2. Add Routes
app.include_router(auth.get_router())  # Adds /auth/google, /auth/refresh, etc.

# 3. Add Middleware (Must wrap Auth with CORS if frontend is separate)
app.add_middleware(
    GoogleAuthMiddleware, 
    google_auth=auth,
    public_paths=["/api/public"] # Optional: Whitelist paths
)

# 4. Protect Routes
@app.get("/api/protected")
async def protected_route(user = Depends(auth.current_user)):
    return {"message": "Hello authenticated user!", "user": user}
```

---

## 2. Frontend Installation (React)

Install usage:

```bash
npm install git+https://github.com/jebin2/googleauthservice.git#main
```

### Usage

**`main.tsx`**:

```tsx
import { GoogleAuthProvider } from '@jebin2/googleauthservice/client/src';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <GoogleAuthProvider 
      clientId="YOUR_GOOGLE_CLIENT_ID"
      apiBaseUrl="http://localhost:8000"
    >
      <App />
    </GoogleAuthProvider>
  </React.StrictMode>,
);
```

**`App.tsx`**:

```tsx
import { 
  useGoogleAuth, 
  GoogleSignInButton, 
  authenticatedFetch 
} from '@jebin2/googleauthservice/client/src';

function App() {
  const { user, signIn, signOut, loading } = useGoogleAuth();

  const fetchData = async () => {
      // Automatically handles token refresh
      const res = await authenticatedFetch('http://localhost:8000/api/protected');
      // ...
  };

  if (loading) return <div>Loading...</div>;

  if (!user) {
    return <GoogleSignInButton />;
  }

  return (
    <div>
      <h1>Welcome, {user.name}</h1>
      <button onClick={signOut}>Sign Out</button>
    </div>
  );
}
```

## Development

This repository is a monorepo containing both the server library and client library, plus a full example project.

- `server/`: Python package source.
- `client/`: TypeScript package source.
- `simpleproject/`: Full-stack example using the libraries.
