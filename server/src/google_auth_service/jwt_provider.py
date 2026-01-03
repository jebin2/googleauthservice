"""
JWT Token Provider

Standalone JWT token creation and verification service.
Supports access tokens (short-lived) and refresh tokens (long-lived).

Usage:
    from google_auth_service import JWTService, TokenPayload
    
    # Initialize with secret key
    jwt_service = JWTService(secret_key="your-secret-key")
    
    # Create tokens
    access_token = jwt_service.create_access_token(user_id="user123", email="user@example.com")
    refresh_token = jwt_service.create_refresh_token(user_id="user123", email="user@example.com")
    
    # Verify a token
    payload = jwt_service.verify_token(access_token)
    print(payload.user_id, payload.email)

Environment Variables:
    JWT_SECRET: Your secret key for signing tokens (required)
    JWT_ACCESS_EXPIRY_MINUTES: Access token expiry (default: 15)
    JWT_REFRESH_EXPIRY_DAYS: Refresh token expiry (default: 7)
    JWT_ALGORITHM: Algorithm to use (default: HS256)

Dependencies:
    PyJWT>=2.8.0

Generate a secure secret:
    python -c "import secrets; print(secrets.token_urlsafe(64))"
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

import jwt

logger = logging.getLogger(__name__)


@dataclass
class TokenPayload:
    """
    Payload extracted from a verified JWT token.
    
    Attributes:
        user_id: The user's unique identifier (sub claim)
        email: The user's email address
        issued_at: When the token was issued
        expires_at: When the token expires
        token_version: Version number for token invalidation
        token_type: "access" or "refresh"
        extra: Any additional claims in the token
    """
    user_id: str
    email: str
    issued_at: datetime
    expires_at: datetime
    token_version: int = 1
    token_type: str = "access"
    extra: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def is_expired(self) -> bool:
        """Check if the token has expired."""
        return datetime.utcnow() > self.expires_at
    
    @property
    def time_until_expiry(self) -> timedelta:
        """Get time remaining until expiry."""
        return self.expires_at - datetime.utcnow()


class JWTError(Exception):
    """Base exception for JWT errors."""
    pass


class TokenExpiredError(JWTError):
    """Raised when the token has expired."""
    pass


class InvalidTokenError(JWTError):
    """Raised when the token is invalid."""
    pass


class ConfigurationError(JWTError):
    """Raised when the service is not properly configured."""
    pass


class JWTService:
    """
    Service for creating and verifying JWT tokens.
    
    This service handles JWT token lifecycle for authentication.
    It's designed to be modular and reusable across different applications.
    
    Example:
        service = JWTService(secret_key="my-secret")
        
        # Create token
        token = service.create_access_token(user_id="u123", email="a@b.com")
        
        # Verify token
        try:
            payload = service.verify_token(token)
            print(f"User: {payload.user_id}")
        except TokenExpiredError:
            print("Token expired, please login again")
        except InvalidTokenError:
            print("Invalid token")
    """
    
    # Default configuration
    DEFAULT_ALGORITHM = "HS256"
    DEFAULT_ACCESS_EXPIRY_MINUTES = 15
    DEFAULT_REFRESH_EXPIRY_DAYS = 7
    
    def __init__(
        self,
        secret_key: Optional[str] = None,
        algorithm: Optional[str] = None,
        access_expiry_minutes: Optional[int] = None,
        refresh_expiry_days: Optional[int] = None
    ):
        """
        Initialize the JWT Service.
        
        Args:
            secret_key: Secret key for signing tokens.
            algorithm: JWT algorithm (default: HS256).
            access_expiry_minutes: Access token expiry (default: 15 min).
            refresh_expiry_days: Refresh token expiry (default: 7 days).
        """
        self.secret_key = secret_key or os.getenv("JWT_SECRET")
        self.algorithm = algorithm or os.getenv("JWT_ALGORITHM", self.DEFAULT_ALGORITHM)
        
        self.access_expiry_minutes = access_expiry_minutes or int(
            os.getenv("JWT_ACCESS_EXPIRY_MINUTES", str(self.DEFAULT_ACCESS_EXPIRY_MINUTES))
        )
        self.refresh_expiry_days = refresh_expiry_days or int(
            os.getenv("JWT_REFRESH_EXPIRY_DAYS", str(self.DEFAULT_REFRESH_EXPIRY_DAYS))
        )
        
        if not self.secret_key:
            raise ConfigurationError(
                "JWT secret key is required. Either pass secret_key parameter "
                "or set JWT_SECRET environment variable. "
                "Generate one with: python -c \"import secrets; print(secrets.token_urlsafe(64))\""
            )
        
        # Warn if secret is too short
        if len(self.secret_key) < 32:
            logger.warning(
                "JWT secret key is short (< 32 chars). "
                "Consider using a longer secret for better security."
            )
        
        logger.info(
            f"JWTService initialized (alg={self.algorithm}, "
            f"access={self.access_expiry_minutes}m, refresh={self.refresh_expiry_days}d)"
        )
    
    def create_token(
        self,
        user_id: str,
        email: str,
        token_type: str = "access",
        token_version: int = 1,
        extra_claims: Optional[Dict[str, Any]] = None,
        expiry_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT token.
        
        Args:
            user_id: User's unique identifier
            email: User's email address
            token_type: "access" or "refresh"
            token_version: Version for invalidation
            extra_claims: Additional claims to include
            expiry_delta: Custom expiry duration
        
        Returns:
            Encoded JWT token string
        """
        now = datetime.utcnow()
        
        if expiry_delta:
            expires_at = now + expiry_delta
        elif token_type == "refresh":
            expires_at = now + timedelta(days=self.refresh_expiry_days)
        else:
            expires_at = now + timedelta(minutes=self.access_expiry_minutes)
        
        payload = {
            "sub": user_id,
            "email": email,
            "type": token_type,
            "tv": token_version,
            "iat": now,
            "exp": expires_at,
        }
        
        if extra_claims:
            payload.update(extra_claims)
        
        token = jwt.encode(payload, self.secret_key, algorithm=self.algorithm)
        
        logger.debug(f"Created {token_type} token for {user_id}")
        return token

    def create_access_token(
        self,
        user_id: str,
        email: str,
        token_version: int = 1,
        **kwargs
    ) -> str:
        """Create a short-lived access token."""
        return self.create_token(user_id, email, "access", token_version, **kwargs)

    def create_refresh_token(
        self,
        user_id: str,
        email: str,
        token_version: int = 1,
        **kwargs
    ) -> str:
        """Create a long-lived refresh token."""
        return self.create_token(user_id, email, "refresh", token_version, **kwargs)
    
    def verify_token(self, token: str) -> TokenPayload:
        """
        Verify a JWT token and extract the payload.
        
        Args:
            token: The JWT token to verify.
        
        Returns:
            TokenPayload: Dataclass containing the verified payload.
        
        Raises:
            TokenExpiredError: If the token has expired.
            InvalidTokenError: If the token is invalid or malformed.
        """
        if not token:
            raise InvalidTokenError("Token cannot be empty")
        
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            
            # Extract standard claims
            user_id = payload.get("sub")
            email = payload.get("email")
            token_type = payload.get("type", "access")
            token_version = payload.get("tv", 1)
            iat = payload.get("iat")
            exp = payload.get("exp")
            
            if not user_id or not email:
                raise InvalidTokenError("Token missing required claims (sub, email)")
            
            # Convert timestamps
            issued_at = datetime.utcfromtimestamp(iat) if isinstance(iat, (int, float)) else iat
            expires_at = datetime.utcfromtimestamp(exp) if isinstance(exp, (int, float)) else exp
            
            # Extract extra claims
            standard_claims = {"sub", "email", "type", "tv", "iat", "exp"}
            extra = {k: v for k, v in payload.items() if k not in standard_claims}
            
            return TokenPayload(
                user_id=user_id,
                email=email,
                issued_at=issued_at,
                expires_at=expires_at,
                token_version=token_version,
                token_type=token_type,
                extra=extra
            )
            
        except jwt.ExpiredSignatureError:
            logger.debug("Token verification failed: expired")
            raise TokenExpiredError("Token has expired")
        except jwt.InvalidTokenError as e:
            logger.debug(f"Token verification failed: {e}")
            raise InvalidTokenError(f"Invalid token: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            raise InvalidTokenError(f"Token verification error: {str(e)}")
    
    def verify_token_safe(self, token: str) -> Optional[TokenPayload]:
        """
        Verify a JWT token without raising exceptions.
        
        Args:
            token: The JWT token to verify.
        
        Returns:
            TokenPayload if valid, None if invalid or expired.
        """
        try:
            return self.verify_token(token)
        except JWTError:
            return None
    
    def decode_without_verification(self, token: str) -> Dict[str, Any]:
        """
        Decode token without verifying expiry. Useful for refresh flow.
        
        Args:
            token: The JWT token to decode
            
        Returns:
            Token payload as dictionary
            
        Raises:
            InvalidTokenError: If token is malformed
        """
        try:
            return jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm],
                options={"verify_exp": False}
            )
        except jwt.InvalidTokenError as e:
            raise InvalidTokenError(f"Cannot decode token: {str(e)}")


# Singleton instance for convenience
_default_service: Optional[JWTService] = None


def get_jwt_service() -> JWTService:
    """
    Get the default JWTService instance.
    
    Creates a singleton instance using environment variables.
    
    Returns:
        JWTService: The default service instance.
    
    Raises:
        ConfigurationError: If JWT_SECRET is not set.
    """
    global _default_service
    if _default_service is None:
        _default_service = JWTService()
    return _default_service


def create_access_token(user_id: str, email: str, token_version: int = 1, **kwargs) -> str:
    """Convenience function to create an access token."""
    return get_jwt_service().create_access_token(user_id, email, token_version, **kwargs)


def create_refresh_token(user_id: str, email: str, token_version: int = 1, **kwargs) -> str:
    """Convenience function to create a refresh token."""
    return get_jwt_service().create_refresh_token(user_id, email, token_version, **kwargs)


def verify_access_token(token: str) -> TokenPayload:
    """
    Convenience function to verify a token using the default service.
    
    Args:
        token: The JWT token to verify.
    
    Returns:
        TokenPayload: Verified token payload.
    
    Raises:
        TokenExpiredError: If the token has expired.
        InvalidTokenError: If the token is invalid.
    """
    return get_jwt_service().verify_token(token)


__all__ = [
    "JWTService",
    "TokenPayload",
    "create_access_token",
    "create_refresh_token",
    "verify_access_token",
    "get_jwt_service",
    "JWTError",
    "TokenExpiredError",
    "InvalidTokenError",
    "ConfigurationError",
]
