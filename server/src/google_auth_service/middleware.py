"""
Auth Middleware - Database-agnostic request authentication layer

Creates middleware that validates JWT tokens and attaches user info to requests.
Uses callback functions for database operations, making it framework/ORM agnostic.

Usage:
    from google_auth_service import create_auth_middleware, RouteConfig
    from google_auth_service.config import JWTConfig
    
    # Define user loader callback (your database logic)
    async def load_user(user_id: str):
        return await db.get_user(user_id)
    
    # Create middleware
    middleware = create_auth_middleware(
        user_loader=load_user,
        jwt_secret="your-secret",
        route_config=RouteConfig(
            required=["/api/*"],
            public=["/", "/health", "/auth/*"],
        ),
    )
    
    # Add to FastAPI
    app.add_middleware(middleware)
"""

import logging
from dataclasses import dataclass
from typing import Optional, Callable, Awaitable, Any, TypeVar

from google_auth_service.jwt_provider import (
    JWTService,
    TokenPayload,
    TokenExpiredError,
    InvalidTokenError,
    JWTError,
)
from google_auth_service.route_matcher import RouteConfig

logger = logging.getLogger(__name__)

# Type for user object (generic since we don't know the user model)
UserType = TypeVar("UserType")

# Callback types
UserLoaderCallback = Callable[[str], Awaitable[Optional[UserType]]]
TokenVersionGetter = Callable[[UserType], int]
AdminChecker = Callable[[UserType], bool]


@dataclass
class AuthResult:
    """
    Result of authentication attempt.
    
    Attributes:
        is_authenticated: Whether user is authenticated
        user: The loaded user object (if authenticated)
        user_id: User ID from token
        email: Email from token
        is_admin: Whether user is admin
        error: Error message if authentication failed
        error_code: Error code for response
    """
    is_authenticated: bool = False
    user: Optional[Any] = None
    user_id: Optional[str] = None
    email: Optional[str] = None
    is_admin: bool = False
    error: Optional[str] = None
    error_code: Optional[str] = None


class AuthMiddlewareBase:
    """
    Base authentication middleware logic.
    
    This class contains the core auth logic that can be adapted
    to different web frameworks (FastAPI, Flask, etc).
    """
    
    def __init__(
        self,
        user_loader: UserLoaderCallback,
        jwt_service: JWTService,
        route_config: RouteConfig,
        token_version_getter: Optional[TokenVersionGetter] = None,
        admin_checker: Optional[AdminChecker] = None,
        admin_emails: Optional[list] = None,
    ):
        """
        Initialize auth middleware.
        
        Args:
            user_loader: Async function that loads user by user_id
            jwt_service: JWT service instance
            route_config: Route configuration
            token_version_getter: Function to get token version from user
            admin_checker: Function to check if user is admin
            admin_emails: List of admin email addresses
        """
        self.user_loader = user_loader
        self.jwt_service = jwt_service
        self.route_config = route_config
        self.token_version_getter = token_version_getter
        self.admin_checker = admin_checker
        self.admin_emails = set(admin_emails or [])
    
    async def authenticate(
        self,
        path: str,
        auth_header: Optional[str],
    ) -> AuthResult:
        """
        Authenticate a request.
        
        Args:
            path: Request path
            auth_header: Authorization header value
        
        Returns:
            AuthResult with authentication status and user info
        """
        # Check if route is public
        if self.route_config.is_public(path):
            return AuthResult(is_authenticated=False)
        
        # Check route requirements
        requires_auth = self.route_config.is_required(path)
        allows_optional = self.route_config.is_optional(path)
        
        # If route doesn't require auth and doesn't allow optional, skip
        if not requires_auth and not allows_optional:
            return AuthResult(is_authenticated=False)
        
        # If no auth header
        if not auth_header:
            if requires_auth:
                return AuthResult(
                    is_authenticated=False,
                    error="Missing Authorization header",
                    error_code="UNAUTHORIZED",
                )
            return AuthResult(is_authenticated=False)
        
        # Validate header format
        if not auth_header.startswith("Bearer "):
            if requires_auth:
                return AuthResult(
                    is_authenticated=False,
                    error="Invalid Authorization header format. Use: Bearer <token>",
                    error_code="TOKEN_INVALID",
                )
            return AuthResult(is_authenticated=False)
        
        # Extract token
        token = auth_header.split(" ", 1)[1]
        
        # Verify token
        try:
            payload = self.jwt_service.verify_token(token)
        except TokenExpiredError:
            if requires_auth:
                return AuthResult(
                    is_authenticated=False,
                    error="Token has expired. Please sign in again.",
                    error_code="TOKEN_EXPIRED",
                )
            return AuthResult(is_authenticated=False)
        except (InvalidTokenError, JWTError) as e:
            if requires_auth:
                return AuthResult(
                    is_authenticated=False,
                    error=f"Invalid token: {str(e)}",
                    error_code="TOKEN_INVALID",
                )
            return AuthResult(is_authenticated=False)
        
        # Load user from database
        user = await self.user_loader(payload.user_id)
        
        if not user:
            if requires_auth:
                return AuthResult(
                    is_authenticated=False,
                    error="User not found or inactive",
                    error_code="USER_NOT_FOUND",
                )
            return AuthResult(is_authenticated=False)
        
        # Validate token version if getter provided
        if self.token_version_getter:
            user_token_version = self.token_version_getter(user)
            if payload.token_version < user_token_version:
                if requires_auth:
                    return AuthResult(
                        is_authenticated=False,
                        error="Token has been invalidated. Please sign in again.",
                        error_code="TOKEN_INVALID",
                    )
                return AuthResult(is_authenticated=False)
        
        # Check admin status
        is_admin = False
        if self.admin_checker:
            is_admin = self.admin_checker(user)
        elif payload.email in self.admin_emails:
            is_admin = True
        
        return AuthResult(
            is_authenticated=True,
            user=user,
            user_id=payload.user_id,
            email=payload.email,
            is_admin=is_admin,
        )


__all__ = [
    "AuthMiddlewareBase",
    "AuthResult",
]
