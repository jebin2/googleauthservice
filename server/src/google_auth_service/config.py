"""
Configuration Classes for Google Auth Service

Dataclasses for configuring authentication services.
"""

from dataclasses import dataclass, field
from typing import List, Optional
import os


@dataclass
class JWTConfig:
    """
    Configuration for JWT token management.
    
    Attributes:
        secret: Secret key for signing tokens (required, min 32 chars recommended)
        algorithm: JWT algorithm (default: HS256)
        access_expiry_minutes: Access token lifetime (default: 15 min)
        refresh_expiry_days: Refresh token lifetime (default: 7 days)
    
    Example:
        config = JWTConfig(secret="your-secret-key-at-least-32-chars")
    """
    secret: str
    algorithm: str = "HS256"
    access_expiry_minutes: int = 15
    refresh_expiry_days: int = 7
    
    def __post_init__(self):
        if not self.secret:
            raise ValueError("JWT secret is required")
        if len(self.secret) < 32:
            import logging
            logging.warning(
                "JWT secret is short (< 32 chars). "
                "Consider using a longer secret for better security."
            )
    
    @classmethod
    def from_env(cls) -> "JWTConfig":
        """Create config from environment variables."""
        return cls(
            secret=os.getenv("JWT_SECRET", ""),
            algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
            access_expiry_minutes=int(os.getenv("JWT_ACCESS_EXPIRY_MINUTES", "15")),
            refresh_expiry_days=int(os.getenv("JWT_REFRESH_EXPIRY_DAYS", "7")),
        )


@dataclass
class GoogleConfig:
    """
    Configuration for Google OAuth.
    
    Attributes:
        client_id: Google OAuth 2.0 Client ID
        clock_skew_seconds: Allowed clock skew for token validation (default: 0)
    
    Example:
        config = GoogleConfig(client_id="your-client-id.googleusercontent.com")
    """
    client_id: str
    clock_skew_seconds: int = 0
    
    def __post_init__(self):
        if not self.client_id:
            raise ValueError("Google Client ID is required")
    
    @classmethod
    def from_env(cls) -> "GoogleConfig":
        """Create config from environment variables."""
        return cls(
            client_id=os.getenv("AUTH_SIGN_IN_GOOGLE_CLIENT_ID", ""),
            clock_skew_seconds=int(os.getenv("GOOGLE_CLOCK_SKEW_SECONDS", "0")),
        )


@dataclass
class AuthConfig:
    """
    Complete authentication configuration.
    
    Combines JWT and Google configs with route configuration.
    
    Attributes:
        jwt: JWT configuration
        google: Google OAuth configuration
        required_urls: URL patterns that REQUIRE authentication
        optional_urls: URL patterns where auth is optional
        public_urls: URL patterns that don't need auth
        admin_emails: List of admin email addresses
    
    Example:
        config = AuthConfig(
            jwt=JWTConfig(secret="..."),
            google=GoogleConfig(client_id="..."),
            required_urls=["/api/*"],
            public_urls=["/", "/health", "/auth/*"],
        )
    """
    jwt: JWTConfig
    google: GoogleConfig
    required_urls: List[str] = field(default_factory=list)
    optional_urls: List[str] = field(default_factory=list)
    public_urls: List[str] = field(default_factory=list)
    admin_emails: List[str] = field(default_factory=list)
    
    @classmethod
    def from_env(
        cls,
        required_urls: Optional[List[str]] = None,
        optional_urls: Optional[List[str]] = None,
        public_urls: Optional[List[str]] = None,
        admin_emails: Optional[List[str]] = None,
    ) -> "AuthConfig":
        """Create config from environment with URL patterns."""
        return cls(
            jwt=JWTConfig.from_env(),
            google=GoogleConfig.from_env(),
            required_urls=required_urls or [],
            optional_urls=optional_urls or [],
            public_urls=public_urls or [],
            admin_emails=admin_emails or [],
        )


__all__ = ["JWTConfig", "GoogleConfig", "AuthConfig"]
