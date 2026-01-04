"""
Pure ASGI Middleware for Google Authentication.

Handles both HTTP and WebSocket connections at the middleware level.
For WebSocket, validates JWT from cookies and attaches user to scope.
"""
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.websockets import WebSocket, WebSocketClose
from typing import List, Optional, Any

from google_auth_service.middleware import AuthMiddlewareBase, RouteConfig
from google_auth_service.user_store import BaseUserStore
from google_auth_service.jwt_provider import JWTService, TokenExpiredError, InvalidTokenError


class GoogleAuthMiddleware:
    """
    Pure ASGI Middleware for Google Authentication.
    
    Handles both HTTP and WebSocket connections:
    - HTTP: Validates JWT and attaches user to request.state
    - WebSocket: Validates JWT from cookies and attaches user to scope
    
    Usage:
        app.add_middleware(
            GoogleAuthMiddleware, 
            google_auth=auth_instance,
            public_paths=["/"],
            protected_paths=["/api/*"]
        )
        
    For WebSocket handlers, access user via:
        user = websocket.scope.get("user")
        if not user:
            await websocket.close(code=4001)
            return
    """
    
    def __init__(
        self, 
        app,
        public_paths: List[str] = ["/", "/health", "/auth/*"],
        protected_paths: List[str] = ["/api/*"],
        google_auth: Optional[Any] = None, 
        user_store: Optional[BaseUserStore] = None,
        jwt_service: Optional[JWTService] = None,
        cookie_name: str = "auth_token",
    ):
        self.app = app
        
        # Resolve dependencies
        if google_auth:
            self.user_store = google_auth.user_store
            self.jwt_service = google_auth.jwt
            self.cookie_name = google_auth.cookie_name
        else:
            if not user_store or not jwt_service:
                raise ValueError("Must provide either 'google_auth' or both 'user_store' and 'jwt_service'")
            self.user_store = user_store
            self.jwt_service = jwt_service
            self.cookie_name = cookie_name

        # Internal loaders
        async def _loader(user_id: str):
            return await self.user_store.get(user_id)
            
        def _version_getter(user: Any):
            if isinstance(user, dict):
                return user.get("token_version", 0)
            return getattr(user, "token_version", 0)

        self.core = AuthMiddlewareBase(
            user_loader=_loader,
            jwt_service=self.jwt_service,
            token_version_getter=_version_getter,
            route_config=RouteConfig(
                public=public_paths,
                required=protected_paths,
            )
        )
        self.route_config = RouteConfig(public=public_paths, required=protected_paths)

    async def __call__(self, scope, receive, send):
        """Pure ASGI interface - handles both HTTP and WebSocket."""
        
        if scope["type"] == "http":
            await self._handle_http(scope, receive, send)
        elif scope["type"] == "websocket":
            await self._handle_websocket(scope, receive, send)
        else:
            await self.app(scope, receive, send)

    async def _handle_http(self, scope, receive, send):
        """Handle HTTP requests with JWT authentication."""
        request = Request(scope, receive, send)
        
        # Skip CORS preflight
        if request.method == "OPTIONS":
            await self.app(scope, receive, send)
            return
        
        auth_header = request.headers.get("Authorization")
        
        # Check cookie if no header
        if not auth_header:
            cookie_token = request.cookies.get(self.cookie_name)
            if cookie_token:
                auth_header = f"Bearer {cookie_token}"

        # Run core auth logic
        result = await self.core.authenticate(
            path=request.url.path,
            auth_header=auth_header,
        )
        
        if result.error:
            response = JSONResponse(
                status_code=401,
                content={"detail": result.error},
            )
            await response(scope, receive, send)
            return
        
        # Attach user to request state (accessible via request.state.user)
        scope["state"] = getattr(scope.get("state"), "__dict__", {}) if hasattr(scope.get("state"), "__dict__") else {}
        scope["state"]["user"] = result.user
        scope["state"]["auth_result"] = result
        
        # Also store in scope for easy access
        scope["user"] = result.user
        
        await self.app(scope, receive, send)

    async def _handle_websocket(self, scope, receive, send):
        """Handle WebSocket connections with JWT authentication from cookies."""
        path = scope.get("path", "/")
        
        # Check if path is public
        if self.route_config.is_public(path):
            scope["user"] = None
            await self.app(scope, receive, send)
            return
        
        # Extract cookies from scope headers
        cookies = self._parse_cookies(scope.get("headers", []))
        jwt_cookie = cookies.get(self.cookie_name)
        
        # If protected route requires auth
        if self.route_config.is_required(path):
            if not jwt_cookie:
                # Reject: No auth cookie
                await self._reject_websocket(scope, receive, send, "Not authenticated")
                return
            
            try:
                payload = self.jwt_service.verify_token(jwt_cookie)
                if not payload:
                    raise InvalidTokenError("Invalid token")
                    
                # Load user
                user = await self.user_store.get(payload.user_id)
                if not user:
                    await self._reject_websocket(scope, receive, send, "User not found")
                    return
                    
                # Attach user and payload to scope
                scope["user"] = user
                scope["auth_payload"] = payload
                
            except TokenExpiredError:
                await self._reject_websocket(scope, receive, send, "Token expired")
                return
            except (InvalidTokenError, Exception):
                await self._reject_websocket(scope, receive, send, "Invalid authentication")
                return
        else:
            # Non-required path - try to auth but don't require
            scope["user"] = None
            if jwt_cookie:
                try:
                    payload = self.jwt_service.verify_token(jwt_cookie)
                    user = await self.user_store.get(payload.user_id)
                    scope["user"] = user
                    scope["auth_payload"] = payload
                except:
                    pass  # Optional auth, ignore errors
        
        await self.app(scope, receive, send)

    async def _reject_websocket(self, scope, receive, send, reason: str):
        """Reject WebSocket connection with close message."""
        # We need to accept first, then close with reason (WebSocket protocol)
        # OR we can just not accept and close immediately
        
        # Wait for connect message
        message = await receive()
        if message["type"] == "websocket.connect":
            # Send close without accepting
            await send({
                "type": "websocket.close",
                "code": 4001,
                "reason": reason
            })

    def _parse_cookies(self, headers: list) -> dict:
        """Parse cookies from ASGI headers."""
        cookies = {}
        for key, value in headers:
            if key == b"cookie":
                cookie_str = value.decode("utf-8", errors="ignore")
                for part in cookie_str.split(";"):
                    if "=" in part:
                        name, val = part.strip().split("=", 1)
                        cookies[name] = val
        return cookies
