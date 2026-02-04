"""
Subscription verification service.
"""
from typing import Optional
from aiogram import Bot
from aiogram.enums import ChatMemberStatus
from aiogram.exceptions import TelegramBadRequest, TelegramForbiddenError

from database.redis_client import redis_client
from config import settings
import structlog

logger = structlog.get_logger()


class SubscriptionService:
    """Service for verifying user subscription to the channel."""
    
    SUBSCRIBED_STATUSES = {
        ChatMemberStatus.MEMBER,
        ChatMemberStatus.ADMINISTRATOR,
        ChatMemberStatus.CREATOR,
        "member",
        "administrator", 
        "creator"
    }
    
    async def check_subscription(
        self,
        bot: Bot,
        user_id: int,
        channel_id: int = None,
        use_cache: bool = True
    ) -> bool:
        """
        Check if user is subscribed to the channel.
        
        Args:
            bot: Bot instance
            user_id: Telegram user ID
            channel_id: Channel ID (from DB or config)
            use_cache: Whether to use cached result
        """
        if not channel_id:
            channel_id = settings.telegram_channel_id
        
        if not channel_id:
            logger.warning("No channel_id configured")
            return True
        
        # Check cache
        if use_cache:
            cached = await redis_client.get_subscription_status(user_id)
            if cached is not None:
                return cached
        
        # Check via Telegram API
        try:
            member = await bot.get_chat_member(
                chat_id=channel_id,
                user_id=user_id
            )
            
            is_subscribed = member.status in self.SUBSCRIBED_STATUSES
            
            await redis_client.set_subscription_status(
                user_id,
                is_subscribed,
                ttl=settings.subscription_cache_ttl
            )
            
            return is_subscribed
            
        except TelegramBadRequest as e:
            error_str = str(e).lower()
            if "user not found" in error_str:
                await redis_client.set_subscription_status(user_id, False, ttl=settings.subscription_cache_ttl)
                return False
            if "chat not found" in error_str:
                logger.error(f"Channel not found: {channel_id}")
                return True
            logger.error(f"Telegram API error: {e}")
            return True
            
        except TelegramForbiddenError:
            logger.error(f"Bot has no access to channel {channel_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
            return True
    
    async def refresh_subscription(self, bot: Bot, user_id: int, channel_id: int = None) -> bool:
        """Force refresh subscription status."""
        await redis_client.invalidate_subscription(user_id)
        return await self.check_subscription(bot, user_id, channel_id, use_cache=False)
    
    async def get_subscription_message(self, language: str = "ru") -> str:
        """Get message for unsubscribed users."""
        from bot.services.settings_service import settings_service
        
        channel_username = await settings_service.get_channel_username()
        if not channel_username:
            channel_username = settings.telegram_channel_username or "@channel"
        
        if language == "ru":
            return (
                "🔒 <b>Доступ ограничен</b>\n\n"
                f"Для использования бота подпишитесь на канал {channel_username}.\n\n"
                "После подписки нажмите «Я подписался»."
            )
        return (
            "🔒 <b>Access Restricted</b>\n\n"
            f"Subscribe to {channel_username} to use the bot.\n\n"
            "Click 'I Subscribed' after subscribing."
        )
    
    async def get_subscription_success_message(self, language: str = "ru") -> str:
        if language == "ru":
            return "✅ <b>Подписка подтверждена!</b>\n\nМожете пользоваться ботом."
        return "✅ <b>Subscription confirmed!</b>\n\nYou can now use the bot."
    
    async def get_subscription_still_needed_message(self, language: str = "ru") -> str:
        from bot.services.settings_service import settings_service
        
        channel_username = await settings_service.get_channel_username()
        if not channel_username:
            channel_username = settings.telegram_channel_username or "@channel"
        
        if language == "ru":
            return f"❌ <b>Подписка не найдена</b>\n\nПодпишитесь на {channel_username} и попробуйте снова."
        return f"❌ <b>Subscription not found</b>\n\nSubscribe to {channel_username} and try again."


subscription_service = SubscriptionService()
