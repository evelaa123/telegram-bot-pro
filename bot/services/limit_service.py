"""
Rate limiting and usage tracking service.
Manages daily limits for all request types.
"""
from datetime import date, datetime, timedelta
from typing import Dict, Optional, Tuple
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.dialects.postgresql import insert

from database import async_session_maker
from database.models import User, DailyLimit, Request, RequestType, RequestStatus
from config import settings
import structlog

logger = structlog.get_logger()


class LimitService:
    """
    Service for managing user rate limits and usage tracking.
    """
    
    REQUEST_TYPE_TO_LIMIT_FIELD = {
        RequestType.TEXT: "text_count",
        RequestType.IMAGE: "image_count",
        RequestType.VIDEO: "video_count",
        RequestType.VOICE: "voice_count",
        RequestType.DOCUMENT: "document_count"
    }
    
    async def get_user_limits(self, telegram_id: int) -> Dict[str, int]:
        """
        Get user's rate limits (custom or global defaults).
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            Dict with limit values for each type
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(User.custom_limits).where(User.telegram_id == telegram_id)
            )
            row = result.first()
            
            if row and row[0]:
                # Merge custom limits with defaults
                limits = settings.default_limits.copy()
                limits.update(row[0])
                return limits
            
            return settings.default_limits.copy()
    
    async def get_today_usage(self, telegram_id: int) -> Dict[str, int]:
        """
        Get user's usage for today.
        
        Returns:
            Dict with usage counts for each type
        """
        async with async_session_maker() as session:
            # Get user ID
            user_result = await session.execute(
                select(User.id).where(User.telegram_id == telegram_id)
            )
            user_row = user_result.first()
            
            if not user_row:
                return {
                    "text": 0,
                    "image": 0,
                    "video": 0,
                    "voice": 0,
                    "document": 0
                }
            
            user_id = user_row[0]
            today = date.today()
            
            # Get or create today's usage record
            result = await session.execute(
                select(DailyLimit).where(
                    DailyLimit.user_id == user_id,
                    DailyLimit.date == today
                )
            )
            daily_limit = result.scalar_one_or_none()
            
            if not daily_limit:
                return {
                    "text": 0,
                    "image": 0,
                    "video": 0,
                    "voice": 0,
                    "document": 0
                }
            
            return {
                "text": daily_limit.text_count,
                "image": daily_limit.image_count,
                "video": daily_limit.video_count,
                "voice": daily_limit.voice_count,
                "document": daily_limit.document_count
            }
    
    async def get_remaining_limits(
        self, 
        telegram_id: int
    ) -> Tuple[Dict[str, int], Dict[str, int], datetime]:
        """
        Get remaining limits for user.
        
        Returns:
            Tuple of (remaining_limits, max_limits, reset_time)
        """
        limits = await self.get_user_limits(telegram_id)
        usage = await self.get_today_usage(telegram_id)
        
        remaining = {
            key: max(0, limits[key] - usage[key])
            for key in limits
        }
        
        # Calculate reset time (midnight UTC)
        now = datetime.utcnow()
        tomorrow = (now + timedelta(days=1)).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        
        return remaining, limits, tomorrow
    
    async def check_limit(
        self,
        telegram_id: int,
        request_type: RequestType
    ) -> Tuple[bool, int, int]:
        """
        Check if user has remaining limit for request type.
        
        Args:
            telegram_id: Telegram user ID
            request_type: Type of request to check
            
        Returns:
            Tuple of (has_limit, current_usage, max_limit)
        """
        type_key = request_type.value  # text, image, etc.
        
        limits = await self.get_user_limits(telegram_id)
        usage = await self.get_today_usage(telegram_id)
        
        max_limit = limits.get(type_key, 0)
        current = usage.get(type_key, 0)
        
        return current < max_limit, current, max_limit
    
    async def increment_usage(
        self,
        telegram_id: int,
        request_type: RequestType
    ) -> bool:
        """
        Increment usage counter for request type.
        
        Args:
            telegram_id: Telegram user ID
            request_type: Type of request
            
        Returns:
            True if successful
        """
        async with async_session_maker() as session:
            # Get user ID
            user_result = await session.execute(
                select(User.id).where(User.telegram_id == telegram_id)
            )
            user_row = user_result.first()
            
            if not user_row:
                logger.error("User not found for limit increment", telegram_id=telegram_id)
                return False
            
            user_id = user_row[0]
            today = date.today()
            field_name = self.REQUEST_TYPE_TO_LIMIT_FIELD[request_type]
            
            # Upsert daily limit record
            stmt = insert(DailyLimit).values(
                user_id=user_id,
                date=today,
                text_count=1 if request_type == RequestType.TEXT else 0,
                image_count=1 if request_type == RequestType.IMAGE else 0,
                video_count=1 if request_type == RequestType.VIDEO else 0,
                voice_count=1 if request_type == RequestType.VOICE else 0,
                document_count=1 if request_type == RequestType.DOCUMENT else 0
            )
            
            # On conflict, increment the specific counter
            stmt = stmt.on_conflict_do_update(
                index_elements=['user_id', 'date'],
                set_={
                    field_name: getattr(DailyLimit, field_name) + 1
                }
            )
            
            await session.execute(stmt)
            await session.commit()
            
            logger.debug(
                "Usage incremented",
                telegram_id=telegram_id,
                type=request_type.value
            )
            
            return True
    
    async def record_request(
        self,
        telegram_id: int,
        request_type: RequestType,
        prompt: Optional[str] = None,
        response_preview: Optional[str] = None,
        tokens_input: Optional[int] = None,
        tokens_output: Optional[int] = None,
        cost_usd: Optional[float] = None,
        model: Optional[str] = None,
        status: RequestStatus = RequestStatus.SUCCESS,
        error_message: Optional[str] = None,
        duration_ms: Optional[int] = None
    ) -> Optional[int]:
        """
        Record a request in the database.
        
        Returns:
            Request ID or None if failed
        """
        async with async_session_maker() as session:
            # Get user ID
            user_result = await session.execute(
                select(User.id).where(User.telegram_id == telegram_id)
            )
            user_row = user_result.first()
            
            if not user_row:
                return None
            
            user_id = user_row[0]
            
            # Truncate response preview if needed
            if response_preview and len(response_preview) > 500:
                response_preview = response_preview[:497] + "..."
            
            request = Request(
                user_id=user_id,
                type=request_type,
                prompt=prompt,
                response_preview=response_preview,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                cost_usd=cost_usd,
                model=model,
                status=status,
                error_message=error_message,
                duration_ms=duration_ms
            )
            
            session.add(request)
            await session.commit()
            await session.refresh(request)
            
            return request.id
    
    async def get_limits_text(
        self,
        telegram_id: int,
        language: str = "ru"
    ) -> str:
        """
        Get formatted limits text for user display.
        
        Returns:
            Formatted string with limits info
        """
        remaining, limits, reset_time = await self.get_remaining_limits(telegram_id)
        
        # Calculate time until reset
        now = datetime.utcnow()
        time_left = reset_time - now
        hours_left = int(time_left.total_seconds() // 3600)
        minutes_left = int((time_left.total_seconds() % 3600) // 60)
        
        if language == "ru":
            text = (
                "📊 <b>Ваши лимиты на сегодня:</b>\n\n"
                f"💬 Текст: {remaining['text']}/{limits['text']}\n"
                f"🖼 Изображения: {remaining['image']}/{limits['image']}\n"
                f"🎬 Видео: {remaining['video']}/{limits['video']}\n"
                f"🎤 Голосовые: {remaining['voice']}/{limits['voice']}\n"
                f"📄 Документы: {remaining['document']}/{limits['document']}\n\n"
                f"🔄 Обновление лимитов через: {hours_left}ч {minutes_left}м"
            )
        else:
            text = (
                "📊 <b>Your Daily Limits:</b>\n\n"
                f"💬 Text: {remaining['text']}/{limits['text']}\n"
                f"🖼 Images: {remaining['image']}/{limits['image']}\n"
                f"🎬 Videos: {remaining['video']}/{limits['video']}\n"
                f"🎤 Voice: {remaining['voice']}/{limits['voice']}\n"
                f"📄 Documents: {remaining['document']}/{limits['document']}\n\n"
                f"🔄 Limits reset in: {hours_left}h {minutes_left}m"
            )
        
        return text
    
    async def reset_user_limits(self, telegram_id: int) -> bool:
        """
        Reset user's limits for today (admin action).
        
        Returns:
            True if successful
        """
        async with async_session_maker() as session:
            user_result = await session.execute(
                select(User.id).where(User.telegram_id == telegram_id)
            )
            user_row = user_result.first()
            
            if not user_row:
                return False
            
            user_id = user_row[0]
            today = date.today()
            
            result = await session.execute(
                update(DailyLimit)
                .where(
                    DailyLimit.user_id == user_id,
                    DailyLimit.date == today
                )
                .values(
                    text_count=0,
                    image_count=0,
                    video_count=0,
                    voice_count=0,
                    document_count=0
                )
            )
            await session.commit()
            
            logger.info("User limits reset", telegram_id=telegram_id)
            return result.rowcount > 0


# Global service instance
limit_service = LimitService()
