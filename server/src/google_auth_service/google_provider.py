"""
Google OAuth Provider

Standalone Google ID token verification service.
No database dependencies - just verifies tokens and extracts user info.

Usage:
    from google_auth_service import GoogleAuthService, GoogleUserInfo
    
    # Initialize with client ID
    auth_service = GoogleAuthService(client_id="your-google-client-id")
    
    # Or use environment variable AUTH_SIGN_IN_GOOGLE_CLIENT_ID
    auth_service = GoogleAuthService()
    
    # Verify a Google ID token
    user_info = auth_service.verify_token(id_token)
    print(user_info.email, user_info.google_id, user_info.name)

Environment Variables:
    GOOGLE_CLIENT_ID: Your Google OAuth 2.0 Client ID

Dependencies:
    google-auth>=2.0.0
"""

import os
import logging
from dataclasses import dataclass
from typing import Optional

from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests

logger = logging.getLogger(__name__)


@dataclass
class GoogleUserInfo:
    """
    User information extracted from a verified Google ID token.
    
    Attributes:
        google_id: Unique Google user identifier (sub claim)
        email: User's email address
        email_verified: Whether Google has verified the email
        name: User's display name (may be None)
        picture: URL to user's profile picture (may be None)
        given_name: User's first name (may be None)
        family_name: User's last name (may be None)
        locale: User's locale preference (may be None)
    """
    google_id: str
    email: str
    email_verified: bool = True
    name: Optional[str] = None
    picture: Optional[str] = None
    given_name: Optional[str] = None
    family_name: Optional[str] = None
    locale: Optional[str] = None


class GoogleAuthError(Exception):
    """Base exception for Google Auth errors."""
    pass


class InvalidTokenError(GoogleAuthError):
    """Raised when the token is invalid or expired."""
    pass


class ConfigurationError(GoogleAuthError):
    """Raised when the service is not properly configured."""
    pass


class GoogleAuthService:
    """
    Service for verifying Google OAuth ID tokens.
    
    This service validates ID tokens issued by Google Sign-In and extracts
    user information. It's designed to be modular and reusable across
    different applications.
    
    Example:
        service = GoogleAuthService()
        try:
            user_info = service.verify_token(token_from_frontend)
            print(f"Welcome {user_info.name}!")
        except InvalidTokenError:
            print("Invalid or expired token")
    """
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        clock_skew_seconds: int = 0
    ):
        """
        Initialize the Google Auth Service.
        
        Args:
            client_id: Google OAuth 2.0 Client ID. If not provided,
                      falls back to GOOGLE_CLIENT_ID env var.
            clock_skew_seconds: Allowed clock skew in seconds for token
                               validation (default: 0).
        
        Raises:
            ConfigurationError: If no client_id is provided or found.
        """
        # Check both env var names for compatibility
        self.client_id = client_id or os.getenv("GOOGLE_CLIENT_ID") or os.getenv("AUTH_SIGN_IN_GOOGLE_CLIENT_ID")
        self.clock_skew_seconds = clock_skew_seconds
        
        if not self.client_id:
            raise ConfigurationError(
                "Google Client ID is required. Either pass client_id parameter "
                "or set GOOGLE_CLIENT_ID environment variable."
            )
        
        logger.info(f"GoogleAuthService initialized with client_id: {self.client_id[:20]}...")
    
    def verify_token(self, id_token: str) -> GoogleUserInfo:
        """
        Verify a Google ID token and extract user information.
        
        Args:
            id_token: The ID token received from the frontend after
                     Google Sign-In.
        
        Returns:
            GoogleUserInfo: Dataclass containing user's Google profile info.
        
        Raises:
            InvalidTokenError: If the token is invalid, expired, or
                              doesn't match the expected client ID.
        """
        if not id_token:
            raise InvalidTokenError("Token cannot be empty")
        
        try:
            # Verify the token with Google
            idinfo = google_id_token.verify_oauth2_token(
                id_token,
                google_requests.Request(),
                self.client_id,
                clock_skew_in_seconds=self.clock_skew_seconds
            )
            
            # Validate issuer
            if idinfo.get("iss") not in ["accounts.google.com", "https://accounts.google.com"]:
                raise InvalidTokenError("Invalid token issuer")
            
            # Validate audience
            if idinfo.get("aud") != self.client_id:
                raise InvalidTokenError("Token was not issued for this application")
            
            # Extract user info
            return GoogleUserInfo(
                google_id=idinfo["sub"],
                email=idinfo["email"],
                email_verified=idinfo.get("email_verified", False),
                name=idinfo.get("name"),
                picture=idinfo.get("picture"),
                given_name=idinfo.get("given_name"),
                family_name=idinfo.get("family_name"),
                locale=idinfo.get("locale")
            )
            
        except ValueError as e:
            logger.warning(f"Token verification failed: {e}")
            raise InvalidTokenError(f"Token verification failed: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error during token verification: {e}")
            raise InvalidTokenError(f"Token verification error: {str(e)}")
    
    def verify_token_safe(self, id_token: str) -> Optional[GoogleUserInfo]:
        """
        Verify a Google ID token without raising exceptions.
        
        Useful for cases where you want to check validity without
        exception handling.
        
        Args:
            id_token: The ID token to verify.
        
        Returns:
            GoogleUserInfo if valid, None if invalid.
        """
        try:
            return self.verify_token(id_token)
        except GoogleAuthError:
            return None


# Singleton instance for convenience (initialized on first use)
_default_service: Optional[GoogleAuthService] = None


def get_google_auth_service() -> GoogleAuthService:
    """
    Get the default GoogleAuthService instance.
    
    Creates a singleton instance using environment variables.
    
    Returns:
        GoogleAuthService: The default service instance.
    
    Raises:
        ConfigurationError: If GOOGLE_CLIENT_ID is not set.
    """
    global _default_service
    if _default_service is None:
        _default_service = GoogleAuthService()
    return _default_service


def verify_google_token(id_token: str) -> GoogleUserInfo:
    """
    Convenience function to verify a token using the default service.
    
    Args:
        id_token: The Google ID token to verify.
    
    Returns:
        GoogleUserInfo: Verified user information.
    
    Raises:
        InvalidTokenError: If verification fails.
        ConfigurationError: If service is not configured.
    """
    return get_google_auth_service().verify_token(id_token)


__all__ = [
    "GoogleAuthService",
    "GoogleUserInfo",
    "verify_google_token",
    "get_google_auth_service",
    "GoogleAuthError",
    "InvalidTokenError",
    "ConfigurationError",
]
