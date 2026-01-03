"""
Google Provider Tests

Tests for Google token verification (mocked - no real Google API calls).
"""

import pytest
from unittest.mock import patch, MagicMock
from google_auth_service.google_provider import (
    GoogleAuthService,
    GoogleUserInfo,
    verify_google_token,
    InvalidTokenError,
    ConfigurationError,
)


class TestGoogleAuthService:
    """Test GoogleAuthService class functionality."""

    @pytest.fixture
    def google_service(self):
        """Create a GoogleAuthService instance for testing."""
        return GoogleAuthService(client_id="test-client-id.apps.googleusercontent.com")

    def test_initialization_with_client_id(self):
        """Test service initialization with explicit client_id."""
        service = GoogleAuthService(client_id="my-client-id")
        assert service.client_id == "my-client-id"

    def test_initialization_from_env(self, monkeypatch):
        """Test service initialization from environment variable."""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "env-client-id")
        
        service = GoogleAuthService()
        assert service.client_id == "env-client-id"

    def test_initialization_fallback_env(self, monkeypatch):
        """Test fallback to old env var name."""
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.setenv("AUTH_SIGN_IN_GOOGLE_CLIENT_ID", "fallback-client-id")
        
        service = GoogleAuthService()
        assert service.client_id == "fallback-client-id"

    def test_missing_client_id_raises(self, monkeypatch):
        """Test that missing client_id raises ConfigurationError."""
        monkeypatch.delenv("GOOGLE_CLIENT_ID", raising=False)
        monkeypatch.delenv("AUTH_SIGN_IN_GOOGLE_CLIENT_ID", raising=False)
        
        with pytest.raises(ConfigurationError):
            GoogleAuthService()

    def test_empty_token_raises(self, google_service):
        """Test that empty token raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            google_service.verify_token("")

    def test_none_token_raises(self, google_service):
        """Test that None token raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            google_service.verify_token(None)

    @patch("google_auth_service.google_provider.google_id_token.verify_oauth2_token")
    def test_verify_token_success(self, mock_verify, google_service):
        """Test successful token verification with mocked Google API."""
        mock_verify.return_value = {
            "sub": "google-user-id-123",
            "email": "user@example.com",
            "email_verified": True,
            "name": "Test User",
            "given_name": "Test",
            "family_name": "User",
            "picture": "https://example.com/photo.jpg",
            "locale": "en",
            "iss": "accounts.google.com",
            "aud": "test-client-id.apps.googleusercontent.com",
        }
        
        user_info = google_service.verify_token("valid-token")
        
        assert user_info.google_id == "google-user-id-123"
        assert user_info.email == "user@example.com"
        assert user_info.email_verified == True
        assert user_info.name == "Test User"
        assert user_info.given_name == "Test"
        assert user_info.family_name == "User"
        assert user_info.picture == "https://example.com/photo.jpg"
        assert user_info.locale == "en"

    @patch("google_auth_service.google_provider.google_id_token.verify_oauth2_token")
    def test_verify_token_invalid_issuer(self, mock_verify, google_service):
        """Test that invalid issuer raises InvalidTokenError."""
        mock_verify.return_value = {
            "sub": "user-id",
            "email": "user@example.com",
            "iss": "invalid-issuer.com",
            "aud": "test-client-id.apps.googleusercontent.com",
        }
        
        with pytest.raises(InvalidTokenError, match="Invalid token issuer"):
            google_service.verify_token("token")

    @patch("google_auth_service.google_provider.google_id_token.verify_oauth2_token")
    def test_verify_token_wrong_audience(self, mock_verify, google_service):
        """Test that wrong audience raises InvalidTokenError."""
        mock_verify.return_value = {
            "sub": "user-id",
            "email": "user@example.com",
            "iss": "accounts.google.com",
            "aud": "different-client-id",
        }
        
        with pytest.raises(InvalidTokenError, match="not issued for this application"):
            google_service.verify_token("token")

    @patch("google_auth_service.google_provider.google_id_token.verify_oauth2_token")
    def test_verify_token_google_error(self, mock_verify, google_service):
        """Test that Google API errors are wrapped in InvalidTokenError."""
        mock_verify.side_effect = ValueError("Token expired")
        
        with pytest.raises(InvalidTokenError, match="Token verification failed"):
            google_service.verify_token("expired-token")

    @patch("google_auth_service.google_provider.google_id_token.verify_oauth2_token")
    def test_verify_token_safe_returns_none_on_error(self, mock_verify, google_service):
        """Test verify_token_safe returns None on error."""
        mock_verify.side_effect = ValueError("Invalid token")
        
        result = google_service.verify_token_safe("invalid-token")
        assert result is None

    @patch("google_auth_service.google_provider.google_id_token.verify_oauth2_token")
    def test_verify_token_safe_returns_user_on_success(self, mock_verify, google_service):
        """Test verify_token_safe returns user info on success."""
        mock_verify.return_value = {
            "sub": "user-id",
            "email": "user@example.com",
            "iss": "accounts.google.com",
            "aud": "test-client-id.apps.googleusercontent.com",
        }
        
        result = google_service.verify_token_safe("valid-token")
        assert result is not None
        assert result.email == "user@example.com"


class TestGoogleUserInfo:
    """Test GoogleUserInfo dataclass."""

    def test_create_with_required_fields(self):
        """Test creating GoogleUserInfo with required fields only."""
        user = GoogleUserInfo(
            google_id="123",
            email="user@example.com",
        )
        
        assert user.google_id == "123"
        assert user.email == "user@example.com"
        assert user.email_verified == True  # Default
        assert user.name is None
        assert user.picture is None

    def test_create_with_all_fields(self):
        """Test creating GoogleUserInfo with all fields."""
        user = GoogleUserInfo(
            google_id="123",
            email="user@example.com",
            email_verified=True,
            name="Test User",
            picture="https://example.com/photo.jpg",
            given_name="Test",
            family_name="User",
            locale="en",
        )
        
        assert user.name == "Test User"
        assert user.picture == "https://example.com/photo.jpg"
        assert user.given_name == "Test"
        assert user.family_name == "User"
        assert user.locale == "en"


class TestConvenienceFunction:
    """Test module-level convenience functions."""

    @patch("google_auth_service.google_provider.google_id_token.verify_oauth2_token")
    def test_verify_google_token_function(self, mock_verify, monkeypatch):
        """Test verify_google_token convenience function."""
        monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
        
        # Reset singleton
        import google_auth_service.google_provider as google_module
        google_module._default_service = None
        
        mock_verify.return_value = {
            "sub": "user-id",
            "email": "user@example.com",
            "iss": "accounts.google.com",
            "aud": "test-client-id",
        }
        
        result = verify_google_token("valid-token")
        assert result.email == "user@example.com"
