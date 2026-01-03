# Server Integration Guide

Quick guide to integrate Google Auth Service server module into your Python web application.

## Installation

```bash
# Option 1: Copy source
cp -r server/src/google_auth_service /path/to/your/project/

# Option 2: Install dependencies
pip install google-auth>=2.0.0 PyJWT>=2.8.0
```

## Environment Variables

```bash
# Required
AUTH_SIGN_IN_GOOGLE_CLIENT_ID=your-client-id.apps.googleusercontent.com
JWT_SECRET=your-secret-key-at-least-32-chars-long

# Optional
JWT_ACCESS_EXPIRY_MINUTES=15
JWT_REFRESH_EXPIRY_DAYS=7
JWT_ALGORITHM=HS256
```

## Quick Start - FastAPI

### 1. Verify Google Token (Login Endpoint)

```python
from fastapi import APIRouter, HTTPException
from google_auth_service import (
    GoogleAuthService,
    GoogleInvalidTokenError,
    create_access_token,
    create_refresh_token,
)

router = APIRouter()
google_auth = GoogleAuthService()  # Uses env var

@router.post("/auth/google")
async def google_login(id_token: str, db: Session):
    # Verify Google token
    try:
        google_info = google_auth.verify_token(id_token)
    except GoogleInvalidTokenError:
        raise HTTPException(401, "Invalid Google token")
    
    # Find or create user in YOUR database
    user = await db.get_user_by_email(google_info.email)
    if not user:
        user = await db.create_user(
            email=google_info.email,
            name=google_info.name,
            google_id=google_info.google_id,
        )
    
    # Create JWT tokens
    access_token = create_access_token(user.id, user.email)
    refresh_token = create_refresh_token(user.id, user.email)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "user": {"id": user.id, "email": user.email},
    }
```

### 2. Protect Routes with Middleware

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from google_auth_service import create_auth_middleware, RouteConfig

app = FastAPI()

# Define your user loader (YOUR database logic)
async def load_user(user_id: str):
    return await db.get_user(user_id)

# Create auth middleware
auth = create_auth_middleware(
    user_loader=load_user,
    jwt_secret="your-secret",
    route_config=RouteConfig(
        required=["/api/*"],
        public=["/", "/health", "/auth/*"],
    ),
    token_version_getter=lambda user: user.token_version,  # Optional
    admin_emails=["admin@example.com"],
)

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
        
        result = await auth.authenticate(
            path=request.url.path,
            auth_header=request.headers.get("Authorization"),
        )
        
        if result.error:
            return JSONResponse(
                status_code=401,
                content={"error": result.error, "code": result.error_code},
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        request.state.user = result.user
        request.state.is_admin = result.is_admin
        
        return await call_next(request)

app.add_middleware(AuthMiddleware)
```

### 3. Access User in Routes

```python
@router.get("/api/profile")
async def get_profile(request: Request):
    user = request.state.user  # Populated by middleware
    return {"email": user.email, "name": user.name}
```

## Token Versioning (Logout All Devices)

```python
# In your User model:
class User:
    token_version: int = 1

# On logout (invalidate all tokens):
user.token_version += 1
db.save(user)

# Middleware will reject old tokens automatically
```

## Refresh Token Flow

```python
from google_auth_service import JWTService

jwt = JWTService()

@router.post("/auth/refresh")
async def refresh(refresh_token: str, db: Session):
    # Decode without expiry check
    payload = jwt.decode_without_verification(refresh_token)
    
    # Validate token type
    if payload.get("type") != "refresh":
        raise HTTPException(401, "Invalid token type")
    
    # Load user and check version
    user = await db.get_user(payload["sub"])
    if payload.get("tv", 1) < user.token_version:
        raise HTTPException(401, "Token invalidated")
    
    # Issue new tokens
    return {
        "access_token": jwt.create_access_token(user.id, user.email, user.token_version),
        "refresh_token": jwt.create_refresh_token(user.id, user.email, user.token_version),
    }
```

## API Reference

### GoogleAuthService
- `verify_token(id_token)` → `GoogleUserInfo`
- `verify_token_safe(id_token)` → `GoogleUserInfo | None`

### JWTService
- `create_access_token(user_id, email, token_version=1)`
- `create_refresh_token(user_id, email, token_version=1)`
- `verify_token(token)` → `TokenPayload`
- `decode_without_verification(token)` → `dict`

### RouteConfig
- `is_required(path)` → `bool`
- `is_optional(path)` → `bool`
- `is_public(path)` → `bool`
