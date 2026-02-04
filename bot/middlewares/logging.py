"""
Logging middleware.
Logs all incoming updates for debugging and analytics.
"""
import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import Message, CallbackQuery, Update, InlineQuery

import structlog

logger = structlog.get_logger()


class LoggingMiddleware(BaseMiddleware):
    """
    Middleware for logging all incoming updates.
    Tracks timing and user activity.
    """
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Log update and measure handler execution time."""
        
        start_time = time.time()
        
        # Extract event info for logging
        event_info = self._extract_event_info(event)
        
        logger.info(
            "Incoming update",
            **event_info
        )
        
        try:
            result = await handler(event, data)
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.info(
                "Update handled successfully",
                duration_ms=duration_ms,
                **event_info
            )
            
            return result
            
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            
            logger.error(
                "Update handler error",
                error=str(e),
                error_type=type(e).__name__,
                duration_ms=duration_ms,
                **event_info
            )
            
            raise
    
    def _extract_event_info(self, event: Update) -> Dict[str, Any]:
        """Extract relevant info from update for logging."""
        
        info = {"update_type": type(event).__name__}
        
        if isinstance(event, Message):
            info.update({
                "user_id": event.from_user.id if event.from_user else None,
                "username": event.from_user.username if event.from_user else None,
                "chat_id": event.chat.id,
                "chat_type": event.chat.type,
                "message_type": self._get_message_type(event),
            })
            
            # Add text preview (truncated for privacy)
            if event.text:
                info["text_preview"] = event.text[:50] + "..." if len(event.text) > 50 else event.text
            
        elif isinstance(event, CallbackQuery):
            info.update({
                "user_id": event.from_user.id,
                "username": event.from_user.username,
                "callback_data": event.data,
            })
            
        elif isinstance(event, InlineQuery):
            info.update({
                "user_id": event.from_user.id,
                "username": event.from_user.username,
                "query_preview": event.query[:50] if event.query else None,
            })
        
        return info
    
    def _get_message_type(self, message: Message) -> str:
        """Determine message content type."""
        
        if message.text:
            return "text"
        elif message.photo:
            return "photo"
        elif message.document:
            return "document"
        elif message.voice:
            return "voice"
        elif message.audio:
            return "audio"
        elif message.video:
            return "video"
        elif message.video_note:
            return "video_note"
        elif message.sticker:
            return "sticker"
        elif message.animation:
            return "animation"
        else:
            return "other"
