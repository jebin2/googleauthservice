"""
FastAPI Router Integration for Google Auth Service.

This module provides a high-level `GoogleAuth` class that integrates
Google Sign-In and JWT session management directly into FastAPI.
"""

from typing import Optional, Callable, Awaitable, Any, List
from fastapi import APIRouter, HTTPException, Request, Response, Depends
from pydantic import BaseModel

from google_auth_service.google_provider import GoogleAuthService, GoogleUserInfo
from google_auth_service.jwt_provider import JWTService, TokenPayload, TokenExpiredError, InvalidTokenError

class GoogleAuth:
    """
    Main entry point for Google Authentication in FastAPI.
    
    Usage:
        auth = GoogleAuth(client_id="...", jwt_secret="...")
        app.include_router(auth.get_router(on_login=..., load_user=...))
    """
    
    def __init__(
        self,
        client_id: str,
        jwt_secret: str,
        jwt_algorithm: str = "HS256",
        access_expiry_minutes: int = 15,
        refresh_expiry_days: int = 7,
        cookie_name: str = "auth_token",
        cookie_secure: bool = False, # Set True in production
        cookie_samesite: str = "lax",
    ):
        self.google = GoogleAuthService(client_id=client_id)
        self.jwt = JWTService(
            secret_key=jwt_secret,
            algorithm=jwt_algorithm,
            access_expiry_minutes=access_expiry_minutes,
            refresh_expiry_days=refresh_expiry_days
        )
        self.cookie_name = cookie_name
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite

    def get_router(
        self,
        user_saver: Callable[[GoogleUserInfo], Awaitable[Any]],
        user_loader: Callable[[str], Awaitable[Optional[Any]]],
        prefix: str = "/auth",
    ) -> APIRouter:
        """
        Create a FastAPI router with auth endpoints.
        
        Args:
            user_saver: Async func to save/update user from Google info. Returns user object.
            user_loader: Async func to load user by ID. Returns user object.
            prefix: URL prefix for the router (default: /auth)
        """
        router = APIRouter(prefix=prefix, tags=["Authentication"])
        
        class GoogleAuthRequest(BaseModel):
            id_token: str

        @router.post("/google")
        async def google_login(request: GoogleAuthRequest, response: Response):
            # 1. Verify Google Token
            try:
                google_info = self.google.verify_token(request.id_token)
            except Exception as e:
                raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")
            
            # 2. Save/Update User via callback
            user = await user_saver(google_info)
            if not user:
                raise HTTPException(status_code=500, detail="Failed to save user")
                
            # Assume user object has user_id/id and email attributes or key access
            user_id = getattr(user, "user_id", None) or user.get("user_id")
            email = getattr(user, "email", None) or user.get("email")
            
            # 3. Create Access Token
            access_token = self.jwt.create_access_token(user_id=user_id, email=email)
            
            # 4. Set Cookie
            response.set_cookie(
                key=self.cookie_name,
                value=access_token,
                httponly=True,
                secure=self.cookie_secure,
                samesite=self.cookie_samesite,
                max_age=self.jwt.refresh_expiry_days * 24 * 60 * 60
            )
            
            return {
                "success": True, 
                "access_token": access_token,
                "user_id": user_id,
                "email": email,
                "name": getattr(user, "name", None) or user.get("name"),
                "picture": getattr(user, "picture", None) or user.get("picture"),
                "is_new_user": getattr(google_info, "is_new_user", False), # If tracked
            }

        @router.post("/refresh")
        async def refresh_token(request: Request, response: Response):
            token = request.cookies.get(self.cookie_name)
            if not token:
                raise HTTPException(status_code=401, detail="No session cookie")
                
            try:
                payload = self.jwt.verify_token(token)
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid session")
                
            # Load user to ensure they still exist
            user = await user_loader(payload.user_id)
            if not user:
                 raise HTTPException(status_code=401, detail="User not found")

            # Create new token
            new_token = self.jwt.create_access_token(user_id=payload.user_id, email=payload.email)
            
            response.set_cookie(
                key=self.cookie_name,
                value=new_token,
                httponly=True,
                secure=self.cookie_secure,
                samesite=self.cookie_samesite,
                max_age=self.jwt.refresh_expiry_days * 24 * 60 * 60
            )
            
            # Extract user fields for flat response
            user_id = getattr(user, "user_id", None) or user.get("user_id")
            email = getattr(user, "email", None) or user.get("email")
            
            return {
                "success": True, 
                "access_token": new_token,
                "user_id": user_id,
                "email": email,
                "name": getattr(user, "name", None) or user.get("name"),
                "picture": getattr(user, "picture", None) or user.get("picture"),
            }
            
        @router.post("/logout")
        async def logout(response: Response):
            response.delete_cookie(self.cookie_name)
            return {"success": True, "message": "Logged out"}
            
        @router.get("/me")
        async def get_me(request: Request):
            # This is a bit redundant if we have a dependency, but good for client lib
            token = request.cookies.get(self.cookie_name)
            if not token:
                # Fallback to Header if cookie missing (for API calls not from browser?)
                auth = request.headers.get("Authorization")
                if auth and auth.startswith("Bearer "):
                    token = auth.split(" ")[1]
            
            if not token:
                raise HTTPException(status_code=401, detail="Not authenticated")
                
            try:
                payload = self.jwt.verify_token(token)
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid token")
                
            user = await user_loader(payload.user_id)
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
                
            return user

        return router
