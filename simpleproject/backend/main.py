"""
Simple Project - FastAPI Backend Demo

Demonstrates how to use google_auth_service for authentication.
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Import from pip-installed google-auth-service package
from google_auth_service import (
    GoogleAuthService,
    GoogleUserInfo,
    GoogleInvalidTokenError,
    GoogleConfigError,
    JWTService,
    RouteConfig,
    create_auth_middleware,
)

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

# Validate required env vars
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
JWT_SECRET = os.getenv("JWT_SECRET")

if not GOOGLE_CLIENT_ID:
    print("⚠️  WARNING: GOOGLE_CLIENT_ID not set. Set it in .env file.")
if not JWT_SECRET:
    print("⚠️  WARNING: JWT_SECRET not set. Using default (NOT FOR PRODUCTION).")
    JWT_SECRET = "demo-secret-key-not-for-production-use"

# Initialize services
google_auth = GoogleAuthService(client_id=GOOGLE_CLIENT_ID) if GOOGLE_CLIENT_ID else None
jwt_service = JWTService(secret_key=JWT_SECRET)

# In-memory user store (replace with real database in production)
users_db: dict = {}


# Request/Response models
class GoogleAuthRequest(BaseModel):
    id_token: str


class AuthResponse(BaseModel):
    success: bool
    access_token: str
    user_id: str
    email: str
    name: Optional[str] = None


class UserResponse(BaseModel):
    user_id: str
    email: str
    name: Optional[str] = None
    created_at: str


# Create FastAPI app
app = FastAPI(
    title="Google Auth Demo",
    description="Simple demo of google-auth-service library",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Auth middleware setup
async def load_user(user_id: str):
    """Load user from in-memory store."""
    return users_db.get(user_id)


auth_middleware = create_auth_middleware(
    user_loader=load_user,
    jwt_secret=JWT_SECRET,
    route_config=RouteConfig(
        required=["/api/*"],
        public=["/", "/health", "/auth/*"],
    ),
)


# Dependency to get current user
async def get_current_user(request: Request):
    """Get authenticated user from request."""
    auth_header = request.headers.get("Authorization")
    result = await auth_middleware.authenticate(
        path=request.url.path,
        auth_header=auth_header,
    )
    
    if result.error:
        raise HTTPException(status_code=401, detail=result.error)
    
    if not result.user:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    return result.user


# Routes
@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "service": "google-auth-demo"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/auth/google", response_model=AuthResponse)
async def google_login(request: GoogleAuthRequest):
    """
    Authenticate with Google ID token.
    
    1. Verify Google ID token
    2. Create/update user in database
    3. Return JWT access token
    """
    if not google_auth:
        raise HTTPException(
            status_code=503,
            detail="Google authentication not configured. Set GOOGLE_CLIENT_ID in .env"
        )
    
    try:
        # Verify Google token
        google_info: GoogleUserInfo = google_auth.verify_token(request.id_token)
    except GoogleInvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")
    except GoogleConfigError as e:
        raise HTTPException(status_code=503, detail=f"Auth service misconfigured: {str(e)}")
    
    # Create user ID from Google ID
    user_id = f"user_{google_info.google_id[:8]}"
    
    # Create/update user in memory store
    if user_id not in users_db:
        users_db[user_id] = {
            "user_id": user_id,
            "email": google_info.email,
            "name": google_info.name,
            "google_id": google_info.google_id,
            "picture": google_info.picture,
            "created_at": datetime.utcnow().isoformat(),
            "token_version": 1,
        }
        print(f"✅ New user created: {google_info.email}")
    else:
        users_db[user_id]["name"] = google_info.name
        users_db[user_id]["picture"] = google_info.picture
        print(f"✅ User logged in: {google_info.email}")
    
    # Create JWT access token
    access_token = jwt_service.create_access_token(
        user_id=user_id,
        email=google_info.email,
        token_version=users_db[user_id]["token_version"],
    )
    
    return AuthResponse(
        success=True,
        access_token=access_token,
        user_id=user_id,
        email=google_info.email,
        name=google_info.name,
    )


@app.get("/auth/me", response_model=UserResponse)
async def get_me(user: dict = Depends(get_current_user)):
    """Get current authenticated user info."""
    return UserResponse(
        user_id=user["user_id"],
        email=user["email"],
        name=user.get("name"),
        created_at=user["created_at"],
    )


@app.get("/api/protected")
async def protected_route(user: dict = Depends(get_current_user)):
    """Example protected API endpoint."""
    return {
        "message": f"Hello {user.get('name') or user['email']}!",
        "user_id": user["user_id"],
        "description": "This is a protected endpoint that requires authentication.",
    }


@app.post("/auth/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Logout and invalidate tokens."""
    # Increment token version to invalidate all existing tokens
    if user["user_id"] in users_db:
        users_db[user["user_id"]]["token_version"] += 1
    
    return {"success": True, "message": "Logged out successfully"}


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Google Auth Demo server...")
    print(f"   Google Client ID: {'✅ Set' if GOOGLE_CLIENT_ID else '❌ Not set'}")
    print(f"   JWT Secret: {'✅ Set' if os.getenv('JWT_SECRET') else '⚠️ Using default'}")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
