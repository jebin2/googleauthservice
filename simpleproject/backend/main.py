"""
Simple Project - FastAPI Backend Demo

Demonstrates how to use google_auth_service for authentication.
"""

import os
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv

# Import from pip-installed google-auth-service package
from google_auth_service import (
    GoogleAuth,
    create_auth_middleware,
    RouteConfig,
    GoogleUserInfo
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

# In-memory user store (replace with real database in production)
users_db: dict = {}

# --- Database Callbacks ---

async def load_user(user_id: str):
    """Load user from in-memory store."""
    return users_db.get(user_id)

async def on_google_login(google_info: GoogleUserInfo):
    """Create or update user on Google login."""
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
        
    return users_db[user_id]

# --- Setup Google Auth Service ---

# Initialize GoogleAuth (High-level API)
auth = GoogleAuth(
    client_id=GOOGLE_CLIENT_ID,
    jwt_secret=JWT_SECRET,
)

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

# --- Add Auth Routes ---

# This adds /auth/google, /auth/refresh, /auth/logout, /auth/me
app.include_router(
    auth.get_router(
        user_saver=on_google_login,
        user_loader=load_user,
    )
)

# --- Middleware for Route Protection ---

# We still use middleware for protecting other routes
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
    # We can reuse the middleware's logic
    auth_header = request.headers.get("Authorization")
    
    # Attempt middleware authentication
    result = await auth_middleware.authenticate(
        path=request.url.path,
        auth_header=auth_header,
    )
    
    if result.is_authenticated:
        return result.user
        
    # As a fallback for endpoints that might rely on cookie but are behind middleware
    # (Middleware primarily checks Header, but let's check cookie if middleware failed/skipped)
    # Actually, for consistency, the frontend Sends Bearer token for API calls.
    # The cookie is strictly for SESSION RESTORATION (refresh).
    
    if result.error:
         raise HTTPException(status_code=401, detail=result.error)
         
    raise HTTPException(status_code=401, detail="Not authenticated")


# Routes
@app.get("/")
async def root():
    """Health check."""
    return {"status": "ok", "service": "google-auth-demo"}


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/api/protected")
async def protected_route(user: dict = Depends(get_current_user)):
    """Example protected API endpoint."""
    return {
        "message": f"Hello {user.get('name') or user['email']}!",
        "user_id": user["user_id"],
        "description": "This is a protected endpoint that requires authentication.",
    }


if __name__ == "__main__":
    import uvicorn
    print("🚀 Starting Google Auth Demo server...")
    print(f"   Google Client ID: {'✅ Set' if GOOGLE_CLIENT_ID else '❌ Not set'}")
    print(f"   JWT Secret: {'✅ Set' if os.getenv('JWT_SECRET') else '⚠️ Using default'}")
    print()
    uvicorn.run(app, host="0.0.0.0", port=8000)
