"""
Tests for bot services.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date


class TestUserService:
    """Tests for UserService."""
    
    @pytest.mark.asyncio
    async def test_get_or_create_user_new(self, db_session):
        """Test creating a new user."""
        from bot.services.user_service import UserService
        
        service = UserService(db_session)
        
        # Mock user data
        user_data = MagicMock()
        user_data.id = 123456789
        user_data.username = "testuser"
        user_data.first_name = "Test"
        user_data.last_name = "User"
        user_data.language_code = "en"
        
        user = await service.get_or_create_user(user_data)
        
        assert user is not None
        assert user.telegram_id == 123456789
        assert user.username == "testuser"
    
    @pytest.mark.asyncio
    async def test_get_or_create_user_existing(self, db_session):
        """Test getting an existing user."""
        from bot.services.user_service import UserService
        from database.models import User
        
        # Create existing user
        existing_user = User(
            telegram_id=123456789,
            username="existinguser",
            first_name="Existing",
            last_name="User"
        )
        db_session.add(existing_user)
        await db_session.commit()
        
        service = UserService(db_session)
        
        user_data = MagicMock()
        user_data.id = 123456789
        user_data.username = "updateduser"
        user_data.first_name = "Updated"
        user_data.last_name = "User"
        user_data.language_code = "ru"
        
        user = await service.get_or_create_user(user_data)
        
        assert user is not None
        assert user.telegram_id == 123456789
        # Username should be updated
        assert user.username == "updateduser"


class TestLimitService:
    """Tests for LimitService."""
    
    @pytest.mark.asyncio
    async def test_check_limit_available(self, db_session, mock_redis):
        """Test checking limits when available."""
        from bot.services.limit_service import LimitService
        from database.models import User
        
        # Create user
        user = User(
            telegram_id=123456789,
            username="testuser"
        )
        db_session.add(user)
        await db_session.commit()
        
        service = LimitService(db_session, mock_redis)
        
        can_use, remaining = await service.check_limit(
            user_id=123456789,
            limit_type="text"
        )
        
        assert can_use is True
        assert remaining >= 0
    
    @pytest.mark.asyncio
    async def test_increment_usage(self, db_session, mock_redis):
        """Test incrementing usage counter."""
        from bot.services.limit_service import LimitService
        from database.models import User
        
        user = User(
            telegram_id=123456789,
            username="testuser"
        )
        db_session.add(user)
        await db_session.commit()
        
        service = LimitService(db_session, mock_redis)
        
        # Increment usage
        result = await service.increment_usage(
            user_id=123456789,
            limit_type="text"
        )
        
        assert result is True


class TestSubscriptionService:
    """Tests for SubscriptionService."""
    
    @pytest.mark.asyncio
    async def test_check_subscription_cached(self, mock_bot, mock_redis):
        """Test subscription check with cached result."""
        from bot.services.subscription_service import SubscriptionService
        
        # Cache says user is subscribed
        mock_redis.get = AsyncMock(return_value=b"1")
        
        service = SubscriptionService(mock_bot, mock_redis, channel_id=-1001234567890)
        
        is_subscribed = await service.check_subscription(123456789)
        
        assert is_subscribed is True
        # Should not call API when cached
        mock_bot.get_chat_member.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_check_subscription_api(self, mock_bot, mock_redis):
        """Test subscription check via API."""
        from bot.services.subscription_service import SubscriptionService
        
        # No cache
        mock_redis.get = AsyncMock(return_value=None)
        
        # Mock API response
        member = MagicMock()
        member.status = "member"
        mock_bot.get_chat_member = AsyncMock(return_value=member)
        
        service = SubscriptionService(mock_bot, mock_redis, channel_id=-1001234567890)
        
        is_subscribed = await service.check_subscription(123456789)
        
        assert is_subscribed is True
        mock_bot.get_chat_member.assert_called_once()
        mock_redis.set.assert_called_once()


class TestOpenAIService:
    """Tests for OpenAIService."""
    
    @pytest.mark.asyncio
    async def test_generate_text_response(self, mock_openai):
        """Test generating text response."""
        from bot.services.openai_service import OpenAIService
        
        service = OpenAIService(mock_openai)
        
        response = await service.generate_text(
            prompt="Hello, how are you?",
            model="gpt-4o-mini"
        )
        
        assert response is not None
        assert "Test response" in response
    
    @pytest.mark.asyncio
    async def test_generate_image(self, mock_openai):
        """Test generating image."""
        from bot.services.openai_service import OpenAIService
        
        service = OpenAIService(mock_openai)
        
        result = await service.generate_image(
            prompt="A beautiful sunset",
            size="1024x1024",
            style="vivid"
        )
        
        assert result is not None
        assert "url" in result
        assert result["url"] == "https://example.com/image.png"
    
    @pytest.mark.asyncio
    async def test_transcribe_audio(self, mock_openai):
        """Test audio transcription."""
        from bot.services.openai_service import OpenAIService
        
        service = OpenAIService(mock_openai)
        
        text = await service.transcribe_audio(
            audio_file=b"fake_audio_data",
            language="en"
        )
        
        assert text == "Transcribed text"
