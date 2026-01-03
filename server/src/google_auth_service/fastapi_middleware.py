from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from typing import List, Optional, Any, Callable, Awaitable

from google_auth_service.middleware import AuthMiddlewareBase, RouteConfig
from google_auth_service.user_store import BaseUserStore
from google_auth_service.jwt_provider import JWTService

class GoogleAuthMiddleware(BaseHTTPMiddleware):
    """
    FastAPI/Starlette Middleware for Google Authentication.
    
    Usage:
        app.add_middleware(
            GoogleAuthMiddleware, 
            google_auth=auth_instance,
            public_paths=["/"],
            protected_paths=["/api"]
        )
    """
    
    def __init__(
        self, 
        app,
        public_paths: List[str] = ["/", "/health", "/auth/*"],
        protected_paths: List[str] = ["/api/*"],
        # We can accept the GoogleAuth instance to avoid passing 10 args
        google_auth: Optional[Any] = None, 
        # Or individual components if used standalone
        user_store: Optional[BaseUserStore] = None,
        jwt_service: Optional[JWTService] = None,
        cookie_name: str = "auth_token",
    ):
        super().__init__(app)
        
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
            # This is synchronous in base, but our store is async.
            # Base logic expects synchronous version getter for the user object itself (if version is on user obj)
            # BUT: checking middleware.py, token_version_getter is Callable[[UserType], int].
            # If we need async db check, we might need to modify base logic or fetch validation info earlier.
            # HOWEVER: In `fastapi_router.py` previously, we defined `_version_getter` as async and passed it.
            # Let's check `middleware.py` implementation of `token_version_getter`.
            # Line 194: `user_token_version = self.token_version_getter(user)` -> Synchronous call.
            # Line 195: `if payload.token_version < user_token_version:`
            
            # The InMemoryUserStore stores version on the user object (dict).
            # So `user.get('token_version')` is sync and fine.
            # If we were using SQL, we'd load the user with version in `_loader`.
            # So this is strictly extracting property from the loaded user object.
            user_id = getattr(user, "user_id", None) or user.get("user_id")
            # If user is a dict
            if isinstance(user, dict):
                return user.get("token_version", 0)
            # If user is object
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

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS":
            return await call_next(request)
            
        auth_header = request.headers.get("Authorization")
        
        # Also check cookie if header missing (for browser nav to protected routes)
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
            return JSONResponse(
                status_code=401,
                content={"detail": result.error},
            )
        
        # Attach user to request state
        request.state.user = result.user
        request.state.auth_result = result
        
        return await call_next(request)
