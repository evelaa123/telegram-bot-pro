"""
Throttling middleware.
Prevents spam and abuse by rate limiting requests.
"""
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update

from database.redis_client import redis_client
import structlog

logger = structlog.get_logger()


class ThrottlingMiddleware(BaseMiddleware):
    """
    Middleware for rate limiting user requests.
    Uses Redis sliding window counter.
    """
    
    def __init__(
        self,
        rate_limit: int = 30,  # requests
        time_window: int = 60,  # seconds
        key_prefix: str = "throttle"
    ):
        """
        Initialize throttling middleware.
        
        Args:
            rate_limit: Maximum requests per time window
            time_window: Time window in seconds
            key_prefix: Redis key prefix
        """
        self.rate_limit = rate_limit
        self.time_window = time_window
        self.key_prefix = key_prefix
        super().__init__()
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Check rate limit before processing update."""
        
        # Extract user ID
        user_id = None
        
        if isinstance(event, Message):
            user_id = event.from_user.id if event.from_user else None
        elif isinstance(event, CallbackQuery):
            user_id = event.from_user.id
        
        if not user_id:
            return await handler(event, data)
        
        # Check rate limit
        key = f"{self.key_prefix}:user:{user_id}"
        
        is_allowed = await redis_client.check_rate_limit(
            key,
            self.rate_limit,
            self.time_window
        )
        
        if not is_allowed:
            logger.warning(
                "User throttled",
                user_id=user_id,
                rate_limit=self.rate_limit,
                time_window=self.time_window
            )
            
            # Send throttle message
            if isinstance(event, Message):
                await event.answer(
                    "⏳ Слишком много запросов. Пожалуйста, подождите немного."
                )
            elif isinstance(event, CallbackQuery):
                await event.answer(
                    "⏳ Слишком много запросов. Подождите немного.",
                    show_alert=True
                )
            
            return None
        
        return await handler(event, data)
