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
from google_auth_service.fastapi_hooks import AuthHooks

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
        enable_dual_tokens: bool = True,  # Create independent Access + Refresh tokens
        mobile_support: bool = True,      # Return tokens in JSON for mobile clients
        hooks: Optional[AuthHooks] = None # Custom logic hooks
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
        self.enable_dual_tokens = enable_dual_tokens
        self.mobile_support = mobile_support
        self.hooks = hooks or AuthHooks()
        
    def _detect_client_type(self, request: Request, explicit_type: Optional[str] = None) -> str:
        """
        Detect client type (web vs mobile).
        Priorities:
        1. Explicit type in request body
        2. User-Agent header heuristic
        """
        if explicit_type:
            return explicit_type.lower()
            
        user_agent = request.headers.get("user-agent", "").lower()
        # Common desktop/web browser keywords
        browser_keywords = ["mozilla", "chrome", "firefox", "safari", "edge", "opera"]
        
        if any(keyword in user_agent for keyword in browser_keywords):
            return "web"
        return "mobile"

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
                if current_version is not None and payload.token_version != current_version:
                    raise HTTPException(status_code=401, detail="Session revoked")
                    
                user = await self.user_store.get(payload.user_id)
                if not user:
                    raise HTTPException(status_code=401, detail="User not found")
                    
                return user
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid token")
                
        return request.state.user

    def verify_websocket(self, websocket) -> Optional[TokenPayload]:
        """
        Verify WebSocket connection authentication.
        
        Call this at the start of a WebSocket handler to validate the JWT cookie.
        Returns TokenPayload if valid, None if invalid.
        
        Usage:
            @app.websocket("/ws")
            async def websocket_handler(websocket: WebSocket):
                payload = auth.verify_websocket(websocket)
                if not payload:
                    await websocket.close(code=4001, reason="Not authenticated")
                    return
                
                await websocket.accept()
                # ... handle connection
        
        Args:
            websocket: FastAPI WebSocket instance
            
        Returns:
            TokenPayload if authenticated, None if not
        """
        jwt_cookie = websocket.cookies.get(self.cookie_name)
        if not jwt_cookie:
            return None
        
        try:
            return self.jwt.verify_token(jwt_cookie)
        except (TokenExpiredError, InvalidTokenError):
            return None
        except Exception:
            return None



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
            client_type: Optional[str] = None # "web" or "mobile"

        @router.post("/google")
        async def google_login(request: GoogleAuthRequest, req: Request, response: Response):
            # Hook: Before Login (Rate Limit)
            try:
                await self.hooks.before_login(req)
            except HTTPException:
                raise
            except Exception as e:
                # If hook fails unexpectedly, log it but don't crash auth? 
                # Better to fail safe.
                pass

            # 1. Verify Google Token
            try:
                google_info = self.google.verify_token(request.id_token)
            except Exception as e:
                # Hook: Login Error (Audit Log)
                await self.hooks.on_login_error(e, req)
                raise HTTPException(status_code=401, detail=f"Invalid Google token: {str(e)}")
            
            # 2. Save/Update User via store
            user = await self.user_store.save(google_info)
            if not user:
                e = Exception("Failed to save user")
                await self.hooks.on_login_error(e, req)
                raise HTTPException(status_code=500, detail="Failed to save user")
                
            # Assume user object has user_id/id and email attributes or key access
            user_id = getattr(user, "user_id", None) or user.get("user_id")
            email = getattr(user, "email", None) or user.get("email")
            
            # Get current token version using store
            token_version = await self.user_store.get_token_version(user_id)

            # 3. Create Tokens (Dual or Single)
            access_token = self.jwt.create_access_token(
                user_id=user_id, 
                email=email,
                token_version=token_version
            )
            
            refresh_token = None
            if self.enable_dual_tokens:
                refresh_token = self.jwt.create_refresh_token(
                    user_id=user_id, 
                    email=email,
                    token_version=token_version
                )
            
            # 4. Deliver tokens based on client type
            client_type = self._detect_client_type(req, request.client_type)
            
            response_data = {
                "success": True, 
                "access_token": access_token,
                "user_id": user_id,
                "email": email,
                "name": getattr(user, "name", None) or user.get("name"),
                "picture": getattr(user, "picture", None) or user.get("picture"),
                "is_new_user": getattr(google_info, "is_new_user", False),
            }
            
            if client_type == "web":
                # WEB: Cookie for Session/Refresh, Access Token in Body
                cookie_value = refresh_token if self.enable_dual_tokens else access_token
                
                response.set_cookie(
                    key=self.cookie_name,
                    value=cookie_value,
                    httponly=True,
                    secure=self.cookie_secure,
                    samesite=self.cookie_samesite,
                    max_age=self.jwt.refresh_expiry_days * 24 * 60 * 60
                )
            elif self.mobile_support:
                # MOBILE: All tokens in Body (JSON)
                if self.enable_dual_tokens:
                    response_data["refresh_token"] = refresh_token
                else:
                    # If single token mode, mobile clients usually just store the one token
                    pass
            
            # Hook: Login Success (Audit, Backup, Link)
            tokens = {"access_token": access_token}
            if refresh_token:
                tokens["refresh_token"] = refresh_token
            
            try:
                await self.hooks.on_login_success(
                    user=user, 
                    tokens=tokens, 
                    request=req,
                    is_new_user=getattr(google_info, "is_new_user", False)
                )
            except Exception as e:
                # Don't fail the request if non-critical post-login hooks fail
                pass
                
            return response_data

        @router.post("/refresh")
        async def refresh_token(request: Request, response: Response):
            # Try to get token from Cookie (Web) OR JSON Body (Mobile)
            token = request.cookies.get(self.cookie_name)
            using_cookie = False
            
            if not token:
                # Try reading from body (Mobile support)
                try:
                    body = await request.json()
                    token = body.get("token") or body.get("refresh_token")
                except:
                    pass
            else:
                using_cookie = True
                
            if not token:
                raise HTTPException(status_code=401, detail="No refresh token provided")
            
            # Use decode_without_verification for expiry-safe extraction logic if needed, 
            # but usually refresh token MUST be valid and not expired.
            try:
                payload = self.jwt.verify_token(token)
            except Exception:
                raise HTTPException(status_code=401, detail="Invalid or expired session")
            
            # If Dual Token enabled, verify this is actually a refresh token
            if self.enable_dual_tokens and payload.token_type != "refresh":
                 raise HTTPException(status_code=401, detail="Invalid token type (expected refresh token)")

            # Strict Token Version Check
            current_version = await self.user_store.get_token_version(payload.user_id)
            if current_version is not None and payload.token_version != current_version:
                    if using_cookie:
                        response.delete_cookie(self.cookie_name)
                    raise HTTPException(status_code=401, detail="Session revoked")

            # Load user to ensure they still exist
            user = await self.user_store.get(payload.user_id)
            if not user:
                 raise HTTPException(status_code=401, detail="User not found")

            # Create new tokens
            token_version = await self.user_store.get_token_version(payload.user_id)

            new_access_token = self.jwt.create_access_token(
                user_id=payload.user_id, 
                email=payload.email,
                token_version=token_version
            )
            
            new_refresh_token = None
            if self.enable_dual_tokens:
                new_refresh_token = self.jwt.create_refresh_token(
                    user_id=payload.user_id, 
                    email=payload.email,
                    token_version=token_version
                )
            
            response_data = {
                "success": True, 
                "access_token": new_access_token,
                "user_id": payload.user_id, # User object might not be dict, use payload
            }
            # Extract user fields if available
            user_obj = user
            response_data["email"] = getattr(user_obj, "email", None) or user_obj.get("email")
            response_data["name"] = getattr(user_obj, "name", None) or user_obj.get("name")
            response_data["picture"] = getattr(user_obj, "picture", None) or user_obj.get("picture")

            if using_cookie:
                # Rotated cookie
                cookie_value = new_refresh_token if self.enable_dual_tokens else new_access_token
                response.set_cookie(
                    key=self.cookie_name,
                    value=cookie_value,
                    httponly=True,
                    secure=self.cookie_secure,
                    samesite=self.cookie_samesite,
                    max_age=self.jwt.refresh_expiry_days * 24 * 60 * 60
                )
            elif self.mobile_support and self.enable_dual_tokens:
                # Return new refresh token in body for mobile
                response_data["refresh_token"] = new_refresh_token
            
            return response_data
            
        @router.post("/logout")
        async def logout(response: Response, request: Request):
            user = None
            
            # Invalidate backend token
            token = request.cookies.get(self.cookie_name)
            if token:
                try:
                    payload = self.jwt.verify_token(token)
                    await self.user_store.invalidate_token(payload.user_id)
                    
                    # Try to fetch user for the hook
                    try:
                        user = await self.user_store.get(payload.user_id)
                    except:
                        user = None
                        
                except:
                    pass # Ignore invalid tokens during logout
            
            # Hook: Logout
            if user:
                try:
                    await self.hooks.on_logout(user, request)
                except:
                    pass
            
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
            if current_version is not None and payload.token_version != current_version:
                    raise HTTPException(status_code=401, detail="Session revoked")
                
            user = await self.user_store.get(payload.user_id)
            if not user:
                raise HTTPException(status_code=401, detail="User not found")
                
            return user

        return router
