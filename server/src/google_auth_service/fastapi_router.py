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
from google_auth_service.user_store import BaseUserStore, InMemoryUserStore

class GoogleAuth:
    """
    Main entry point for Google Authentication in FastAPI.
    
    Usage:
        auth = GoogleAuth(client_id="...", jwt_secret="...")
        app.include_router(auth.get_router()) 
    """
    
    def __init__(
        self,
        client_id: str,
        jwt_secret: str,
        user_store: Optional[BaseUserStore] = None,
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
        self.user_store = user_store or InMemoryUserStore()
        self.cookie_name = cookie_name
        self.cookie_secure = cookie_secure
        self.cookie_samesite = cookie_samesite

    async def current_user(self, request: Request) -> Any:
        """
        FastAPI dependency to get the authenticated user.
        Assumes auth middleware has already run and populated request.state.user.
        """
        if not hasattr(request.state, "user") or not request.state.user:
            # Fallback: Validation logic if middleware wasn't used or skipped
            # Useful for routes not covered by middleware config
            token = request.cookies.get(self.cookie_name)
            if not token:
                auth_header = request.headers.get("Authorization")
                if auth_header and auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
            
            if not token:
                raise HTTPException(status_code=401, detail="Not authenticated")
                
            try:
                payload = self.jwt.verify_token(token)
                
                # Check version
                current_version = await self.user_store.get_token_version(payload.user_id)
                if current_version is not None and payload.version != current_version:
                    raise HTTPException(status_code=401, detail="Session revoked")
                    
                user = await self.user_store.get(payload.user_id)
                if not user:
                    raise HTTPException(status_code=401, detail="User not found")
                    
                return user
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid token")
                
        return request.state.user



    def get_router(
        self,
        prefix: str = "/auth",
    ) -> APIRouter:
        """
        Create a FastAPI router with auth endpoints.
        
        Args:
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
            
            # 2. Save/Update User via store
            user = await self.user_store.save(google_info)
            if not user:
                raise HTTPException(status_code=500, detail="Failed to save user")
                
            # Assume user object has user_id/id and email attributes or key access
            user_id = getattr(user, "user_id", None) or user.get("user_id")
            email = getattr(user, "email", None) or user.get("email")
            
            # Get current token version using store
            token_version = await self.user_store.get_token_version(user_id)

            # 3. Create Access Token
            access_token = self.jwt.create_access_token(
                user_id=user_id, 
                email=email,
                token_version=token_version
            )
            
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
                "is_new_user": getattr(google_info, "is_new_user", False),
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
            
            # Strict Token Version Check
            current_version = await self.user_store.get_token_version(payload.user_id)
            if current_version is not None and payload.version != current_version:
                    response.delete_cookie(self.cookie_name)
                    raise HTTPException(status_code=401, detail="Session revoked")

            # Load user to ensure they still exist
            user = await self.user_store.get(payload.user_id)
            if not user:
                 raise HTTPException(status_code=401, detail="User not found")

            # Create new token with current version
            token_version = await self.user_store.get_token_version(payload.user_id)

            new_token = self.jwt.create_access_token(
                user_id=payload.user_id, 
                email=payload.email,
                token_version=token_version
            )
            
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
        async def logout(response: Response, request: Request):
            # Invalidate backend token
            token = request.cookies.get(self.cookie_name)
            if token:
                try:
                    payload = self.jwt.verify_token(token)
                    await self.user_store.invalidate_token(payload.user_id)
                except:
                    pass # Ignore invalid tokens during logout
            
            response.delete_cookie(self.cookie_name)
            return {"success": True, "message": "Logged out"}
            
        @router.get("/me")
        async def get_me(request: Request):
            # We can now use self.current_user if we want, but explicit is fine to allow logic reuse if needed
            # Or simplified:
            # return await self.current_user(request)
            
            # But let's keep robust logic here for safety
            
            token = request.cookies.get(self.cookie_name)
            if not token:
                auth = request.headers.get("Authorization")
                if auth and auth.startswith("Bearer "):
                    token = auth.split(" ")[1]
            
            if not token:
                raise HTTPException(status_code=401, detail="Not authenticated")
                
            try:
                payload = self.jwt.verify_token(token)
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid token")

            current_version = await self.user_store.get_token_version(payload.user_id)
            if current_version is not None and payload.version != current_version:
                    raise HTTPException(status_code=401, detail="Session revoked")
                
            user = await self.user_store.get(payload.user_id)
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
                
            return user

        return router
