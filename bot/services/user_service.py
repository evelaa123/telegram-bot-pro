"""
User management service.
Handles user creation, updates, and settings.
"""
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import attributes

from database import async_session_maker
from database.models import User
from database.redis_client import redis_client
from config import settings
import structlog

logger = structlog.get_logger()


class UserService:
    """
    Service for managing Telegram users.
    """
    
    async def get_or_create_user(
        self,
        telegram_id: int,
        username: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        language_code: Optional[str] = None
    ) -> User:
        """Get existing user or create new one."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                update_needed = False
                
                if username and user.username != username:
                    user.username = username
                    update_needed = True
                if first_name and user.first_name != first_name:
                    user.first_name = first_name
                    update_needed = True
                if last_name and user.last_name != last_name:
                    user.last_name = last_name
                    update_needed = True
                if language_code and user.language_code != language_code:
                    user.language_code = language_code
                    update_needed = True
                
                user.last_active_at = datetime.utcnow()
                
                await session.commit()
                
                if update_needed:
                    await redis_client.invalidate_user_settings(telegram_id)
                
                return user
            
            # Create new user
            default_settings = {
                "gpt_model": settings.default_gpt_model,
                "image_style": "vivid",
                "auto_voice_process": False,
                "language": language_code or "ru"
            }
            
            user = User(
                telegram_id=telegram_id,
                username=username,
                first_name=first_name,
                last_name=last_name,
                language_code=language_code,
                settings=default_settings,
                last_active_at=datetime.utcnow()
            )
            
            session.add(user)
            await session.commit()
            await session.refresh(user)
            
            logger.info("New user created", telegram_id=telegram_id, username=username)
            
            return user
    
    async def get_user_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        """Get user by Telegram ID."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            return result.scalar_one_or_none()
    
    async def get_user_by_id(self, user_id: int) -> Optional[User]:
        """Get user by database ID."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.id == user_id)
            )
            return result.scalar_one_or_none()
    
    async def update_user_settings(
        self,
        telegram_id: int,
        new_settings: Dict[str, Any]
    ) -> Optional[User]:
        """
        Update user settings.
        ИСПРАВЛЕНО: правильное обновление JSON поля
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.warning(f"User not found: {telegram_id}")
                return None
            
            # Получаем текущие настройки (копируем!)
            current_settings = dict(user.settings) if user.settings else {}
            
            # Обновляем
            current_settings.update(new_settings)
            
            # ВАЖНО: присваиваем новый dict чтобы SQLAlchemy увидел изменение
            user.settings = current_settings
            
            # Явно помечаем поле как изменённое
            attributes.flag_modified(user, "settings")
            
            await session.commit()
            await session.refresh(user)
            
            # Обновляем кеш
            await redis_client.set_user_settings(telegram_id, user.settings)
            
            logger.info(
                "User settings updated",
                telegram_id=telegram_id,
                updated_keys=list(new_settings.keys()),
                new_values=new_settings
            )
            
            return user
    
    async def get_user_settings(self, telegram_id: int) -> Dict[str, Any]:
        """Get user settings (with caching)."""
        # Check cache first
        cached = await redis_client.get_user_settings(telegram_id)
        if cached:
            return cached
        
        # Get from database
        user = await self.get_user_by_telegram_id(telegram_id)
        
        if not user or not user.settings:
            return {
                "gpt_model": settings.default_gpt_model,
                "image_style": "vivid",
                "auto_voice_process": False,
                "language": "ru"
            }
        
        # Cache and return
        await redis_client.set_user_settings(telegram_id, user.settings)
        return user.settings
    
    async def get_user_language(self, telegram_id: int) -> str:
        """Get user's preferred language."""
        user_settings = await self.get_user_settings(telegram_id)
        return user_settings.get("language", "ru")
    
    async def block_user(self, telegram_id: int) -> bool:
        """Block user from using the bot."""
        async with async_session_maker() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_blocked=True)
            )
            await session.commit()
            
            if result.rowcount > 0:
                logger.warning("User blocked", telegram_id=telegram_id)
                return True
            return False
    
    async def unblock_user(self, telegram_id: int) -> bool:
        """Unblock user."""
        async with async_session_maker() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(is_blocked=False)
            )
            await session.commit()
            
            if result.rowcount > 0:
                logger.info("User unblocked", telegram_id=telegram_id)
                return True
            return False
    
    async def is_user_blocked(self, telegram_id: int) -> bool:
        """Check if user is blocked."""
        user = await self.get_user_by_telegram_id(telegram_id)
        return user.is_blocked if user else False
    
    async def set_custom_limits(
        self,
        telegram_id: int,
        limits: Dict[str, int]
    ) -> Optional[User]:
        """Set custom limits for user."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return None
            
            valid_keys = {"text", "image", "video", "voice", "document", "presentation", "video_animate", "long_video"}
            custom_limits = dict(user.custom_limits) if user.custom_limits else {}
            
            for key, value in limits.items():
                if key in valid_keys and isinstance(value, int) and value >= -1:
                    custom_limits[key] = value
            
            user.custom_limits = custom_limits
            attributes.flag_modified(user, "custom_limits")
            
            await session.commit()
            await session.refresh(user)
            
            logger.info("Custom limits set", telegram_id=telegram_id, limits=custom_limits)
            
            return user
    
    async def clear_custom_limits(self, telegram_id: int) -> bool:
        """Clear custom limits for user."""
        async with async_session_maker() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(custom_limits=None)
            )
            await session.commit()
            
            return result.rowcount > 0
    
    async def update_last_active(self, telegram_id: int) -> None:
        """Update user's last activity timestamp."""
        async with async_session_maker() as session:
            await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(last_active_at=datetime.utcnow())
            )
            await session.commit()
    
    # ============================================
    # REFERRAL SYSTEM METHODS
    # ============================================
    
    async def find_user_by_referral_code(self, code: str) -> Optional[User]:
        """Find user by their referral code."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.referral_code == code)
            )
            return result.scalar_one_or_none()
    
    async def set_referral(self, telegram_id: int, referrer_telegram_id: int, referral_code: str) -> bool:
        """Set the referrer for a user (only if not already set)."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            # Only set if not already referred
            if user.referred_by:
                return False
            
            user.referred_by = referrer_telegram_id
            await session.commit()
            
            logger.info(
                "Referral set",
                user_id=telegram_id,
                referrer_id=referrer_telegram_id
            )
            return True
    
    async def get_or_create_referral_code(self, telegram_id: int) -> Optional[str]:
        """Get existing referral code or return None if not set."""
        async with async_session_maker() as session:
            result = await session.execute(
                select(User.referral_code).where(User.telegram_id == telegram_id)
            )
            row = result.scalar_one_or_none()
            return row
    
    async def save_referral_code(self, telegram_id: int, code: str) -> bool:
        """Save a referral code for user."""
        async with async_session_maker() as session:
            result = await session.execute(
                update(User)
                .where(User.telegram_id == telegram_id)
                .values(referral_code=code)
            )
            await session.commit()
            return result.rowcount > 0
    
    async def get_referral_stats(self, telegram_id: int) -> Dict[str, Any]:
        """Get referral statistics for a user."""
        from sqlalchemy import func as sqlfunc
        
        async with async_session_maker() as session:
            # Count invited users
            count_result = await session.execute(
                select(sqlfunc.count(User.id)).where(User.referred_by == telegram_id)
            )
            invited_count = count_result.scalar() or 0
            
            # Get total earnings
            user_result = await session.execute(
                select(User.referral_earnings).where(User.telegram_id == telegram_id)
            )
            total_earnings = float(user_result.scalar() or 0)
            
            return {
                "invited_count": invited_count,
                "total_earnings": total_earnings
            }
    
    async def credit_referral_cashback(self, referred_telegram_id: int, payment_amount: float, cashback_percent: float = 15.0) -> Optional[float]:
        """
        Credit cashback to the referrer when a referred user makes a payment.
        
        Args:
            referred_telegram_id: The user who made the payment
            payment_amount: Amount paid
            cashback_percent: Percentage to give to referrer (default 15%)
            
        Returns:
            Cashback amount credited, or None if no referrer
        """
        from decimal import Decimal
        
        async with async_session_maker() as session:
            # Find the referred user
            result = await session.execute(
                select(User).where(User.telegram_id == referred_telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user or not user.referred_by:
                return None
            
            # Find referrer
            referrer_result = await session.execute(
                select(User).where(User.telegram_id == user.referred_by)
            )
            referrer = referrer_result.scalar_one_or_none()
            
            if not referrer:
                return None
            
            cashback = round(payment_amount * cashback_percent / 100, 2)
            referrer.referral_earnings = Decimal(str(float(referrer.referral_earnings or 0) + cashback))
            
            await session.commit()
            
            logger.info(
                "Referral cashback credited",
                referrer_id=referrer.telegram_id,
                referred_id=referred_telegram_id,
                payment=payment_amount,
                cashback=cashback
            )
            
            return cashback


# Global service instance
user_service = UserService()
