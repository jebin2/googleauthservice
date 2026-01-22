import pytest
import os
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch

from google_auth_service.fastapi_router import GoogleAuth
from google_auth_service.google_provider import GoogleUserInfo
from google_auth_service.user_store import InMemoryUserStore

# Helper to verify standard token claims
def verify_token_basic(token, jwt_service):
    payload = jwt_service.verify_token(token)
    assert payload.user_id == "test_user_123"
    assert payload.email == "test@example.com"
    return payload

@pytest.fixture
def auth_setup():
    app = FastAPI()
    
    # Mock Google Service
    jwt_secret = "test_secret_key_1234567890"
    client_id = "test_client_id"
    
    with patch("google_auth_service.fastapi_router.GoogleAuthService") as MockGoogle:
        # Configure Mock
        mock_google_instance = MockGoogle.return_value
        
        # Setup Auth with dual tokens enabled
        auth = GoogleAuth(
            client_id=client_id,
            jwt_secret=jwt_secret,
            enable_dual_tokens=True,
            mobile_support=True
        )
        
        # Override the mock instance on the auth object to be sure
        auth.google = mock_google_instance
        
        app.include_router(auth.get_router())
        
        client = TestClient(app)
        yield client, auth, mock_google_instance

def test_login_web_flow_sets_cookie(auth_setup):
    client, auth, mock_google = auth_setup
    
    # Mock successful Google verification
    mock_google.verify_token.return_value = GoogleUserInfo(
        google_id="gid_123",
        email="test@example.com",
        name="Test User",
        picture="http://pic.com",
        email_verified=True
    )
    
    # WEB client (default or explicit)
    response = client.post(
        "/auth/google",
        json={"id_token": "valid_google_token", "client_type": "web"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Access token in body
    assert "access_token" in data
    assert "refresh_token" not in data # Should be in cookie
    
    # Check Cookie
    assert auth.cookie_name in response.cookies
    cookie_token = response.cookies[auth.cookie_name]
    
    # Verify cookie contains refresh token (since dual_tokens=True)
    payload = auth.jwt.verify_token(cookie_token)
    assert payload.token_type == "refresh"

def test_login_mobile_flow_returns_json(auth_setup):
    client, auth, mock_google = auth_setup
    
    mock_google.verify_token.return_value = GoogleUserInfo(
        google_id="gid_123",
        email="test@example.com",
        name="Test User",
        picture="http://pic.com",
        email_verified=True
    )
    
    # MOBILE client
    response = client.post(
        "/auth/google",
        json={"id_token": "valid_google_token", "client_type": "mobile"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Both tokens in body
    assert "access_token" in data
    assert "refresh_token" in data
    
    # Verify types
    acc_payload = auth.jwt.verify_token(data["access_token"])
    assert acc_payload.token_type == "access"
    
    ref_payload = auth.jwt.verify_token(data["refresh_token"])
    assert ref_payload.token_type == "refresh"

def test_refresh_flow_web_cookie(auth_setup):
    client, auth, mock_google = auth_setup
    
    # Pre-seed user
    user_id = "test_user_123"
    email = "test@example.com"
    auth.user_store._users[user_id] = {"user_id": user_id, "email": email, "token_version": 1}
    
    # Create valid refresh token
    refresh_token = auth.jwt.create_refresh_token(user_id, email)
    
    # Wait to ensure iat changes (JWT uses seconds)
    import time
    time.sleep(1.1)

    # Send request with cookie
    client.cookies.set(auth.cookie_name, refresh_token)
    response = client.post("/auth/refresh", json={})
    
    assert response.status_code == 200
    
    # New cookie set?
    assert auth.cookie_name in response.cookies
    new_cookie = response.cookies[auth.cookie_name]
    assert new_cookie != refresh_token # Rotated
    
    # Verify new cookie is refresh token
    payload = auth.jwt.verify_token(new_cookie)
    assert payload.token_type == "refresh"

def test_refresh_flow_mobile_body(auth_setup):
    client, auth, mock_google = auth_setup
    
    # Pre-seed user
    user_id = "test_user_123"
    email = "test@example.com"
    auth.user_store._users[user_id] = {"user_id": user_id, "email": email, "token_version": 1}
    
    # Create valid refresh token
    refresh_token = auth.jwt.create_refresh_token(user_id, email)
    
    # Wait to ensure iat changes (JWT uses seconds)
    import time
    time.sleep(1.1)
    
    # Send request with body
    response = client.post("/auth/refresh", json={"refresh_token": refresh_token})
    
    assert response.status_code == 200
    data = response.json()
    
    # Should contain new refresh token in body
    assert "refresh_token" in data
    assert data["refresh_token"] != refresh_token
    
    payload = auth.jwt.verify_token(data["refresh_token"])
    assert payload.token_type == "refresh"
