import pytest
from fastapi import FastAPI, HTTPException, Request
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, patch, AsyncMock

from google_auth_service.fastapi_router import GoogleAuth
from google_auth_service.fastapi_hooks import AuthHooks
from google_auth_service.google_provider import GoogleUserInfo

# Define custom hooks for testing
class TestHooks(AuthHooks):
    def __init__(self):
        self.before_login_called = False
        self.on_success_called = False
        self.on_error_called = False
        self.on_logout_called = False
        
    async def before_login(self, request: Request):
        self.before_login_called = True
        # Simulate rate limit failure for specific client
        if request.headers.get("X-Rate-Limit-Fail"):
             raise HTTPException(status_code=429, detail="Rate Limit Exceeded")

    async def on_login_success(self, user, tokens, request, is_new_user):
        self.on_success_called = True
        self.tokens = tokens
        self.is_new_user = is_new_user

    async def on_login_error(self, error, request):
        self.on_error_called = True
        self.error = error
        
    async def on_logout(self, user, request):
        self.on_logout_called = True

@pytest.fixture
def hook_setup():
    app = FastAPI()
    hooks = TestHooks()
    
    jwt_secret = "test_secret_key_1234567890"
    client_id = "test_client_id"
    
    with patch("google_auth_service.fastapi_router.GoogleAuthService") as MockGoogle:
        mock_google_instance = MockGoogle.return_value
        
        auth = GoogleAuth(
            client_id=client_id,
            jwt_secret=jwt_secret,
            hooks=hooks
        )
        auth.google = mock_google_instance
        app.include_router(auth.get_router())
        
        client = TestClient(app)
        yield client, auth, hooks, mock_google_instance

def test_hooks_success_flow(hook_setup):
    client, auth, hooks, mock_google = hook_setup
    
    mock_google.verify_token.return_value = GoogleUserInfo(
        google_id="gid_123", email="test@example.com", name="Test", picture="p", email_verified=True
    )
    
    response = client.post("/auth/google", json={"id_token": "valid"})
    
    assert response.status_code == 200
    assert hooks.before_login_called is True
    assert hooks.on_success_called is True
    assert hooks.on_error_called is False
    assert "access_token" in hooks.tokens

def test_hooks_rate_limit_failure(hook_setup):
    client, auth, hooks, mock_google = hook_setup
    
    # Trigger rate limit via header (logic in TestHooks)
    response = client.post("/auth/google", json={"id_token": "valid"}, headers={"X-Rate-Limit-Fail": "true"})
    
    assert response.status_code == 429
    assert hooks.before_login_called is True
    assert hooks.on_success_called is False
    # Mock verify shouldn't be called if blocked early
    mock_google.verify_token.assert_not_called()

def test_hooks_login_error(hook_setup):
    client, auth, hooks, mock_google = hook_setup
    
    # Mock failure
    mock_google.verify_token.side_effect = Exception("Google Auth Failed")
    
    response = client.post("/auth/google", json={"id_token": "invalid"})
    
    assert response.status_code == 401
    assert hooks.before_login_called is True
    assert hooks.on_success_called is False
    assert hooks.on_error_called is True
    assert str(hooks.error) == "Google Auth Failed"

def test_hooks_logout(hook_setup):
    client, auth, hooks, mock_google = hook_setup
    
    # Seed user
    user_id = "u1"
    auth.user_store._users[user_id] = {"user_id": user_id, "token_version": 1}
    token = auth.jwt.create_access_token(user_id, "e@mail.com")
    
    client.cookies.set(auth.cookie_name, token)
    response = client.post("/auth/logout")
    
    assert response.status_code == 200
    assert hooks.on_logout_called is True
