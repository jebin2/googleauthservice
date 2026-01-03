"""
User Store Tests

Tests for user storage abstraction.
"""

import pytest
from datetime import datetime
from google_auth_service.user_store import (
    BaseUserStore,
    InMemoryUserStore,
)
from google_auth_service.google_provider import GoogleUserInfo


class TestInMemoryUserStore:
    """Test InMemoryUserStore implementation."""

    @pytest.fixture
    def store(self):
        """Create a fresh InMemoryUserStore for each test."""
        return InMemoryUserStore()

    @pytest.fixture
    def google_info(self):
        """Create sample GoogleUserInfo."""
        return GoogleUserInfo(
            google_id="google123456789",
            email="user@example.com",
            name="Test User",
            picture="https://example.com/photo.jpg",
        )

    @pytest.mark.asyncio
    async def test_save_creates_new_user(self, store, google_info):
        """Test that save creates a new user."""
        user = await store.save(google_info)
        
        assert user is not None
        assert user["email"] == "user@example.com"
        assert user["name"] == "Test User"
        assert user["google_id"] == "google123456789"
        assert user["picture"] == "https://example.com/photo.jpg"
        assert "user_id" in user
        assert "created_at" in user
        assert user["token_version"] == 1

    @pytest.mark.asyncio
    async def test_save_updates_existing_user(self, store, google_info):
        """Test that save updates an existing user."""
        # First save
        user1 = await store.save(google_info)
        user_id = user1["user_id"]
        
        # Update info
        updated_info = GoogleUserInfo(
            google_id="google123456789",
            email="user@example.com",
            name="Updated Name",
            picture="https://example.com/new-photo.jpg",
        )
        
        # Second save
        user2 = await store.save(updated_info)
        
        assert user2["user_id"] == user_id  # Same user
        assert user2["name"] == "Updated Name"
        assert user2["picture"] == "https://example.com/new-photo.jpg"
        assert user2["token_version"] == 1  # Not incremented

    @pytest.mark.asyncio
    async def test_get_existing_user(self, store, google_info):
        """Test retrieving an existing user."""
        saved_user = await store.save(google_info)
        user_id = saved_user["user_id"]
        
        retrieved = await store.get(user_id)
        
        assert retrieved is not None
        assert retrieved["email"] == "user@example.com"

    @pytest.mark.asyncio
    async def test_get_nonexistent_user(self, store):
        """Test retrieving a non-existent user returns None."""
        user = await store.get("nonexistent-id")
        assert user is None

    @pytest.mark.asyncio
    async def test_get_token_version(self, store, google_info):
        """Test getting token version."""
        saved_user = await store.save(google_info)
        user_id = saved_user["user_id"]
        
        version = await store.get_token_version(user_id)
        assert version == 1

    @pytest.mark.asyncio
    async def test_get_token_version_nonexistent(self, store):
        """Test getting token version for non-existent user."""
        version = await store.get_token_version("nonexistent-id")
        assert version is None

    @pytest.mark.asyncio
    async def test_invalidate_token_increments_version(self, store, google_info):
        """Test that invalidate_token increments the version."""
        saved_user = await store.save(google_info)
        user_id = saved_user["user_id"]
        
        # Initial version
        assert await store.get_token_version(user_id) == 1
        
        # Invalidate
        await store.invalidate_token(user_id)
        assert await store.get_token_version(user_id) == 2
        
        # Invalidate again
        await store.invalidate_token(user_id)
        assert await store.get_token_version(user_id) == 3

    @pytest.mark.asyncio
    async def test_invalidate_token_nonexistent_user(self, store):
        """Test that invalidating non-existent user doesn't raise."""
        # Should not raise
        await store.invalidate_token("nonexistent-id")


class TestBaseUserStore:
    """Test BaseUserStore abstract class."""

    def test_cannot_instantiate_abstract(self):
        """Test that BaseUserStore cannot be instantiated directly."""
        with pytest.raises(TypeError):
            BaseUserStore()
