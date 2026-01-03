"""
JWT Provider Tests

Tests for JWT token creation, verification, and error handling.
"""

import pytest
from datetime import datetime, timedelta
from google_auth_service.jwt_provider import (
    JWTService,
    TokenPayload,
    create_access_token,
    create_refresh_token,
    verify_access_token,
    TokenExpiredError,
    InvalidTokenError,
    ConfigurationError,
)


class TestJWTService:
    """Test JWTService class functionality."""

    @pytest.fixture
    def jwt_service(self):
        """Create a JWTService instance for testing."""
        return JWTService(
            secret_key="test-secret-key-that-is-long-enough-for-testing",
            access_expiry_minutes=15,
            refresh_expiry_days=7,
        )

    def test_create_access_token(self, jwt_service):
        """Test access token creation."""
        token = jwt_service.create_access_token(
            user_id="user123",
            email="test@example.com",
        )
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_refresh_token(self, jwt_service):
        """Test refresh token creation."""
        token = jwt_service.create_refresh_token(
            user_id="user123",
            email="test@example.com",
        )
        
        assert token is not None
        assert isinstance(token, str)

    def test_verify_valid_token(self, jwt_service):
        """Test verification of a valid token."""
        token = jwt_service.create_access_token(
            user_id="user123",
            email="test@example.com",
            token_version=1,
        )
        
        payload = jwt_service.verify_token(token)
        
        assert payload.user_id == "user123"
        assert payload.email == "test@example.com"
        assert payload.token_type == "access"
        assert payload.token_version == 1
        assert not payload.is_expired

    def test_verify_refresh_token_type(self, jwt_service):
        """Test that refresh token has correct type."""
        token = jwt_service.create_refresh_token(
            user_id="user123",
            email="test@example.com",
        )
        
        payload = jwt_service.verify_token(token)
        
        assert payload.token_type == "refresh"

    def test_verify_expired_token_raises(self, jwt_service):
        """Test that expired token raises TokenExpiredError."""
        # Create token with negative expiry (already expired)
        token = jwt_service.create_token(
            user_id="user123",
            email="test@example.com",
            expiry_delta=timedelta(seconds=-1),
        )
        
        with pytest.raises(TokenExpiredError):
            jwt_service.verify_token(token)

    def test_verify_invalid_token_raises(self, jwt_service):
        """Test that invalid token raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            jwt_service.verify_token("invalid-token-string")

    def test_verify_empty_token_raises(self, jwt_service):
        """Test that empty token raises InvalidTokenError."""
        with pytest.raises(InvalidTokenError):
            jwt_service.verify_token("")

    def test_verify_token_safe_returns_none_for_invalid(self, jwt_service):
        """Test that verify_token_safe returns None for invalid tokens."""
        result = jwt_service.verify_token_safe("invalid-token")
        assert result is None

    def test_verify_token_safe_returns_payload_for_valid(self, jwt_service):
        """Test that verify_token_safe returns payload for valid tokens."""
        token = jwt_service.create_access_token("user123", "test@example.com")
        result = jwt_service.verify_token_safe(token)
        
        assert result is not None
        assert result.user_id == "user123"

    def test_decode_without_verification(self, jwt_service):
        """Test decode_without_verification ignores expiry."""
        # Create expired token
        token = jwt_service.create_token(
            user_id="user123",
            email="test@example.com",
            expiry_delta=timedelta(seconds=-1),
        )
        
        # Should not raise even though expired
        payload = jwt_service.decode_without_verification(token)
        
        assert payload["sub"] == "user123"
        assert payload["email"] == "test@example.com"

    def test_token_version_included(self, jwt_service):
        """Test that token version is correctly included."""
        token = jwt_service.create_access_token(
            user_id="user123",
            email="test@example.com",
            token_version=5,
        )
        
        payload = jwt_service.verify_token(token)
        assert payload.token_version == 5

    def test_extra_claims_stored(self, jwt_service):
        """Test that extra claims are stored and retrieved."""
        token = jwt_service.create_access_token(
            user_id="user123",
            email="test@example.com",
            extra_claims={"role": "admin", "org_id": "org456"},
        )
        
        payload = jwt_service.verify_token(token)
        assert payload.extra["role"] == "admin"
        assert payload.extra["org_id"] == "org456"


class TestJWTServiceConfiguration:
    """Test JWTService configuration and initialization."""

    def test_missing_secret_raises(self, monkeypatch):
        """Test that missing secret key raises ConfigurationError."""
        monkeypatch.delenv("JWT_SECRET", raising=False)
        
        with pytest.raises(ConfigurationError):
            JWTService()

    def test_env_var_fallback(self, monkeypatch):
        """Test that JWT_SECRET env var is used as fallback."""
        monkeypatch.setenv("JWT_SECRET", "env-secret-key-that-is-long-enough")
        
        service = JWTService()
        assert service.secret_key == "env-secret-key-that-is-long-enough"

    def test_custom_algorithm(self):
        """Test custom algorithm configuration."""
        service = JWTService(
            secret_key="test-secret-key-long-enough-for-test",
            algorithm="HS384",
        )
        
        assert service.algorithm == "HS384"

    def test_custom_expiry_times(self):
        """Test custom expiry time configuration."""
        service = JWTService(
            secret_key="test-secret-key-long-enough-for-test",
            access_expiry_minutes=30,
            refresh_expiry_days=14,
        )
        
        assert service.access_expiry_minutes == 30
        assert service.refresh_expiry_days == 14


class TestConvenienceFunctions:
    """Test module-level convenience functions."""

    def test_create_access_token_function(self, monkeypatch):
        """Test create_access_token convenience function."""
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-long-enough-for-test")
        
        # Reset singleton
        import google_auth_service.jwt_provider as jwt_module
        jwt_module._default_service = None
        
        token = create_access_token("user123", "test@example.com")
        assert token is not None

    def test_create_refresh_token_function(self, monkeypatch):
        """Test create_refresh_token convenience function."""
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-long-enough-for-test")
        
        import google_auth_service.jwt_provider as jwt_module
        jwt_module._default_service = None
        
        token = create_refresh_token("user123", "test@example.com")
        assert token is not None

    def test_verify_access_token_function(self, monkeypatch):
        """Test verify_access_token convenience function."""
        monkeypatch.setenv("JWT_SECRET", "test-secret-key-long-enough-for-test")
        
        import google_auth_service.jwt_provider as jwt_module
        jwt_module._default_service = None
        
        token = create_access_token("user123", "test@example.com")
        payload = verify_access_token(token)
        
        assert payload.user_id == "user123"
