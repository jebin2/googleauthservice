from typing import Any, Dict, Optional
from fastapi import Request

class AuthHooks:
    """
    Hooks for customizing the authentication flow.
    Override these methods to inject custom logic (Rate Limiting, Audit Logs, etc).
    """
    
    async def before_login(self, request: Request):
        """
        Called before Google verification starts.
        Use for: Rate Limiting, IP blocking.
        Raise HTTPException to block the request.
        """
        pass

    async def on_login_success(self, user: Any, tokens: Dict[str, str], request: Request, is_new_user: bool = False):
        """
        Called after successful login, before response is sent.
        Use for: Audit Logging, triggering Backups, Linking Client Users.
        
        Args:
            user: The user object returned by UserStore
            tokens: Dictionary containing 'access_token' and optionally 'refresh_token'
            request: The FastAPI Request object
            is_new_user: Boolean indicating if this user was just created
        """
        pass

    async def on_login_error(self, error: Exception, request: Request):
        """
        Called when login fails (invalid token, config error, etc).
        Use for: Audit Logging of failed attempts.
        """
        pass
        
    async def on_logout(self, user: Any, request: Request):
        """
        Called after successful logout.
        Use for: Audit Logging.
        """
        pass
