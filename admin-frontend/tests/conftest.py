"""
Pytest configuration and fixtures.
"""
import asyncio
from typing import AsyncGenerator, Generator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from database.models import Base


# Test database URL (SQLite for testing)
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Create test database engine."""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        echo=False,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncGenerator[AsyncSession, None]:
    """Create test database session."""
    async_session = async_sessionmaker(
        db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    
    async with async_session() as session:
        yield session


@pytest.fixture
def mock_bot():
    """Create mock bot instance."""
    bot = MagicMock()
    bot.send_message = AsyncMock()
    bot.edit_message_text = AsyncMock()
    bot.send_photo = AsyncMock()
    bot.send_video = AsyncMock()
    bot.send_chat_action = AsyncMock()
    bot.get_chat_member = AsyncMock()
    bot.get_file = AsyncMock()
    bot.download = AsyncMock()
    return bot


@pytest.fixture
def mock_message():
    """Create mock message object."""
    message = MagicMock()
    message.from_user = MagicMock()
    message.from_user.id = 123456789
    message.from_user.username = "testuser"
    message.from_user.first_name = "Test"
    message.from_user.last_name = "User"
    message.from_user.language_code = "en"
    message.chat = MagicMock()
    message.chat.id = 123456789
    message.chat.type = "private"
    message.text = "Test message"
    message.answer = AsyncMock()
    message.reply = AsyncMock()
    message.edit_text = AsyncMock()
    return message


@pytest.fixture
def mock_callback_query():
    """Create mock callback query object."""
    callback = MagicMock()
    callback.from_user = MagicMock()
    callback.from_user.id = 123456789
    callback.data = "test_callback"
    callback.message = MagicMock()
    callback.answer = AsyncMock()
    return callback


@pytest.fixture
def mock_redis():
    """Create mock Redis client."""
    redis = MagicMock()
    redis.get = AsyncMock(return_value=None)
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=True)
    redis.exists = AsyncMock(return_value=False)
    redis.incr = AsyncMock(return_value=1)
    redis.expire = AsyncMock(return_value=True)
    redis.hget = AsyncMock(return_value=None)
    redis.hset = AsyncMock(return_value=True)
    redis.hgetall = AsyncMock(return_value={})
    redis.lpush = AsyncMock(return_value=1)
    redis.lrange = AsyncMock(return_value=[])
    redis.ltrim = AsyncMock(return_value=True)
    return redis


@pytest.fixture
def mock_openai():
    """Create mock OpenAI client."""
    client = MagicMock()
    
    # Mock chat completion
    completion = MagicMock()
    completion.choices = [MagicMock()]
    completion.choices[0].message.content = "Test response"
    completion.usage = MagicMock()
    completion.usage.prompt_tokens = 10
    completion.usage.completion_tokens = 20
    completion.usage.total_tokens = 30
    
    client.chat.completions.create = AsyncMock(return_value=completion)
    
    # Mock image generation
    image_response = MagicMock()
    image_response.data = [MagicMock()]
    image_response.data[0].url = "https://example.com/image.png"
    image_response.data[0].revised_prompt = "Revised prompt"
    
    client.images.generate = AsyncMock(return_value=image_response)
    
    # Mock transcription
    transcription = MagicMock()
    transcription.text = "Transcribed text"
    
    client.audio.transcriptions.create = AsyncMock(return_value=transcription)
    
    return client
