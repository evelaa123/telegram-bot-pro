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
        RequestType.DOCUMENT: "document_count",
        RequestType.PRESENTATION: "presentation_count",
        RequestType.VIDEO_ANIMATE: "video_animate_count",
        RequestType.LONG_VIDEO: "long_video_count",
    }
    
    async def get_user_limits(self, telegram_id: int) -> Dict[str, int]:
        """
        Get user's rate limits (custom or global defaults).
        For premium users, use premium limits from DB settings.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            Dict with limit values for each type
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            base_limits = settings.default_limits.copy()
            # Add new types with defaults
            base_limits.setdefault("presentation", 3)
            base_limits.setdefault("video_animate", 0)  # Free users: 0 (premium only)
            base_limits.setdefault("long_video", 0)     # Free users: 0 (premium only)
            
            if user and user.is_premium:
                # Use premium limits from DB settings or env
                try:
                    from api.routers.settings import get_setting
                    db_limits = await get_setting("limits")
                    base_limits = {
                        "text": db_limits.get("premium_text", -1),
                        "image": db_limits.get("premium_image", -1),
                        "video": db_limits.get("premium_video", -1),
                        "voice": db_limits.get("premium_voice", -1),
                        "document": db_limits.get("premium_document", -1),
                        "presentation": db_limits.get("premium_presentation", -1),
                        "video_animate": db_limits.get("premium_video_animate", 10),
                        "long_video": db_limits.get("premium_long_video", 3),
                    }
                except Exception:
                    # Fallback: premium = unlimited
                    base_limits = {
                        "text": -1, "image": -1, "video": -1,
                        "voice": -1, "document": -1, "presentation": -1,
                        "video_animate": 10, "long_video": 3,
                    }
            else:
                # Use free limits from DB settings
                try:
                    from api.routers.settings import get_setting
                    db_limits = await get_setting("limits")
                    base_limits = {
                        "text": db_limits.get("text", base_limits["text"]),
                        "image": db_limits.get("image", base_limits["image"]),
                        "video": db_limits.get("video", base_limits["video"]),
                        "voice": db_limits.get("voice", base_limits["voice"]),
                        "document": db_limits.get("document", base_limits["document"]),
                        "presentation": db_limits.get("presentation", base_limits.get("presentation", 3)),
                        "video_animate": 0,
                        "long_video": 0,
                    }
                except Exception:
                    pass
            
            # Custom user overrides take priority
            if user and user.custom_limits:
                base_limits.update(user.custom_limits)
            
            return base_limits
    
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
                    "text": 0, "image": 0, "video": 0,
                    "voice": 0, "document": 0, "presentation": 0,
                    "video_animate": 0, "long_video": 0,
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
                    "text": 0, "image": 0, "video": 0,
                    "voice": 0, "document": 0, "presentation": 0,
                    "video_animate": 0, "long_video": 0,
                }
            
            return {
                "text": daily_limit.text_count,
                "image": daily_limit.image_count,
                "video": daily_limit.video_count,
                "voice": daily_limit.voice_count,
                "document": daily_limit.document_count,
                "presentation": getattr(daily_limit, 'presentation_count', 0),
                "video_animate": getattr(daily_limit, 'video_animate_count', 0),
                "long_video": getattr(daily_limit, 'long_video_count', 0),
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
        
        remaining = {}
        for key in limits:
            if limits[key] == -1:
                remaining[key] = -1  # Unlimited
            else:
                remaining[key] = max(0, limits[key] - usage[key])
        
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
            
        Note:
            If max_limit is -1, user has unlimited access.
        """
        type_key = request_type.value  # text, image, etc.
        
        limits = await self.get_user_limits(telegram_id)
        usage = await self.get_today_usage(telegram_id)
        
        max_limit = limits.get(type_key, 0)
        current = usage.get(type_key, 0)
        
        # -1 means unlimited
        if max_limit == -1:
            return True, current, -1
        
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
                document_count=1 if request_type == RequestType.DOCUMENT else 0,
                presentation_count=1 if request_type == RequestType.PRESENTATION else 0,
                video_animate_count=1 if request_type == RequestType.VIDEO_ANIMATE else 0,
                long_video_count=1 if request_type == RequestType.LONG_VIDEO else 0,
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
        
        def format_limit(rem, lim, lang):
            """Format limit display, handling unlimited (-1)."""
            if lim == -1:
                return "∞" if lang == "ru" else "∞"
            return f"{rem}/{lim}"
        
        if language == "ru":
            text = (
                "📊 <b>Ваши лимиты на сегодня:</b>\n\n"
                f"💬 Текст: {format_limit(remaining['text'], limits['text'], 'ru')}\n"
                f"🖼 Изображения: {format_limit(remaining['image'], limits['image'], 'ru')}\n"
                f"🎬 Видео: {format_limit(remaining['video'], limits['video'], 'ru')}\n"
                f"🎤 Голосовые: {format_limit(remaining['voice'], limits['voice'], 'ru')}\n"
                f"📊 Презентации: {format_limit(remaining.get('presentation', 0), limits.get('presentation', 3), 'ru')}\n"
                f"📄 Документы: {format_limit(remaining['document'], limits['document'], 'ru')}\n"
            )
            # Show premium features if user has them
            va_lim = limits.get('video_animate', 0)
            lv_lim = limits.get('long_video', 0)
            if va_lim != 0:
                text += f"🎞 Оживление фото: {format_limit(remaining.get('video_animate', 0), va_lim, 'ru')}\n"
            if lv_lim != 0:
                text += f"🎥 Длинное видео: {format_limit(remaining.get('long_video', 0), lv_lim, 'ru')}\n"
            text += (
                f"\n🔄 Обновление лимитов через: {hours_left}ч {minutes_left}м\n\n"
                "💳 Оформите подписку для увеличения лимитов!"
            )
        else:
            text = (
                "📊 <b>Your Daily Limits:</b>\n\n"
                f"💬 Text: {format_limit(remaining['text'], limits['text'], 'en')}\n"
                f"🖼 Images: {format_limit(remaining['image'], limits['image'], 'en')}\n"
                f"🎬 Videos: {format_limit(remaining['video'], limits['video'], 'en')}\n"
                f"🎤 Voice: {format_limit(remaining['voice'], limits['voice'], 'en')}\n"
                f"📊 Presentations: {format_limit(remaining.get('presentation', 0), limits.get('presentation', 3), 'en')}\n"
                f"📄 Documents: {format_limit(remaining['document'], limits['document'], 'en')}\n"
            )
            va_lim = limits.get('video_animate', 0)
            lv_lim = limits.get('long_video', 0)
            if va_lim != 0:
                text += f"🎞 Animate Photo: {format_limit(remaining.get('video_animate', 0), va_lim, 'en')}\n"
            if lv_lim != 0:
                text += f"🎥 Long Video: {format_limit(remaining.get('long_video', 0), lv_lim, 'en')}\n"
            text += (
                f"\n🔄 Limits reset in: {hours_left}h {minutes_left}m\n\n"
                "💳 Get subscription for more limits!"
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
                    document_count=0,
                    presentation_count=0,
                    video_animate_count=0,
                    long_video_count=0,
                )
            )
            await session.commit()
            
            logger.info("User limits reset", telegram_id=telegram_id)
            return result.rowcount > 0


# Global service instance
limit_service = LimitService()
