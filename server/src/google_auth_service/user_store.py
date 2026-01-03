from abc import ABC, abstractmethod
from typing import Optional, Any, Dict
from datetime import datetime

from google_auth_service.google_provider import GoogleUserInfo

class BaseUserStore(ABC):
    """
    Abstract base class for user storage.
    Implement this to provide custom storage (e.g. SQLite, PostgreSQL).
    """
    
    @abstractmethod
    async def get(self, user_id: str) -> Optional[Any]:
        """Retrieve a user by their ID."""
        pass
        
    @abstractmethod
    async def save(self, google_info: GoogleUserInfo) -> Any:
        """
        Save or update a user based on Google login info.
        Should return the user object (must have 'user_id' or 'id' attribute/key).
        """
        pass
        
    @abstractmethod
    async def get_token_version(self, user_id: str) -> Optional[int]:
        """Get the current token version for a user."""
        pass
        
    @abstractmethod
    async def invalidate_token(self, user_id: str) -> None:
        """Increment the token version to invalidate existing tokens."""
        pass


class InMemoryUserStore(BaseUserStore):
    """
    Simple in-memory user storage.
    WARNING: Data is lost when the server restarts.
    """
    
    def __init__(self):
        self._users: Dict[str, Dict] = {}
        
    async def get(self, user_id: str) -> Optional[Dict]:
        return self._users.get(user_id)
        
    async def save(self, google_info: GoogleUserInfo) -> Dict:
        user_id = f"user_{google_info.google_id[:8]}"
        
        if user_id not in self._users:
            self._users[user_id] = {
                "user_id": user_id,
                "email": google_info.email,
                "name": google_info.name,
                "google_id": google_info.google_id,
                "picture": google_info.picture,
                "created_at": datetime.utcnow().isoformat(),
                "token_version": 1,
            }
        else:
            # Update mutable fields
            self._users[user_id]["name"] = google_info.name
            self._users[user_id]["picture"] = google_info.picture
            
        return self._users[user_id]
        
    async def get_token_version(self, user_id: str) -> Optional[int]:
        user = self._users.get(user_id)
        return user.get("token_version") if user else None
        
    async def invalidate_token(self, user_id: str) -> None:
        if user_id in self._users:
            self._users[user_id]["token_version"] += 1
