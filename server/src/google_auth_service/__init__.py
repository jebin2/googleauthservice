"""
Google Auth Service - Server Module

A plug-and-play authentication library for Python web applications.
Database-agnostic design with callback-based user lookup.

Quick Start:
    from google_auth_service import (
        GoogleAuthService,
        JWTService,
        create_auth_middleware,
        AuthConfig,
    )
    
    # Initialize services
    google_auth = GoogleAuthService(client_id="your-client-id")
    jwt_service = JWTService(secret_key="your-secret")
    
    # Verify Google token
    user_info = google_auth.verify_token(id_token_from_frontend)
    
    # Create JWT
    token = jwt_service.create_access_token(user_id, email)
"""

from google_auth_service.google_provider import (
    GoogleAuthService,
    GoogleUserInfo,
    verify_google_token,
    get_google_auth_service,
    GoogleAuthError,
    InvalidTokenError as GoogleInvalidTokenError,
    ConfigurationError as GoogleConfigError,
)

from google_auth_service.jwt_provider import (
    JWTService,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    get_jwt_service,
    JWTError,
    TokenExpiredError,
    InvalidTokenError as JWTInvalidTokenError,
)

from google_auth_service.config import (
    AuthConfig,
    JWTConfig,
    GoogleConfig,
)

from google_auth_service.route_matcher import (
    RouteMatcher,
    RouteConfig,
)

from google_auth_service.middleware import (
    create_auth_middleware,
    AuthResult,
)

__version__ = "1.0.0"

__all__ = [
    # Google OAuth
    "GoogleAuthService",
    "GoogleUserInfo", 
    "verify_google_token",
    "get_google_auth_service",
    "GoogleAuthError",
    "GoogleInvalidTokenError",
    "GoogleConfigError",
    
    # JWT
    "JWTService",
    "TokenPayload",
    "create_access_token",
    "create_refresh_token",
    "verify_access_token",
    "get_jwt_service",
    "JWTError",
    "TokenExpiredError",
    "JWTInvalidTokenError",
    
    # Config
    "AuthConfig",
    "JWTConfig",
    "GoogleConfig",
    
    # Route Matching
    "RouteMatcher",
    "RouteConfig",
    
    # Middleware
    "create_auth_middleware",
    "AuthResult",
]

# Optional FastAPI integration
try:
    from google_auth_service.fastapi_router import GoogleAuth
    __all__.append("GoogleAuth")
except ImportError:
    pass
