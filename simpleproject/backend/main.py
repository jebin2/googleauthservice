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

# --- Setup Google Auth Service ---

# Initialize GoogleAuth (High-level API)
# Uses "batteries-included" InMemoryUserStore by default
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

# Auth Middleware (From Library)
# Automatically authenticates /api/* and adds user to request.state.user
app.add_middleware(
    auth.get_middleware(
        protected_paths=["/api/*"],
        public_paths=["/", "/health", "/auth/*"]
    )
)

# --- Add Auth Routes ---

# This adds /auth/google, /auth/refresh, /auth/logout, /auth/me
# No callbacks needed anymore - library handles user persistence
app.include_router(auth.get_router())


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
async def protected_route(user: dict = Depends(auth.current_user)):
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
