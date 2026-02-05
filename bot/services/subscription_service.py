"""
Subscription management service.
Handles premium subscriptions and payment integration.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal
import uuid
import hmac
import hashlib

from sqlalchemy import select, update, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import async_session_maker
from database.models import User, Subscription, SubscriptionType
from config import settings
import structlog
import aiohttp

logger = structlog.get_logger()


class SubscriptionService:
    """
    Service for managing user subscriptions and payments.
    Supports YooKassa (YooMoney) payment provider.
    """
    
    # YooKassa API
    YOOKASSA_API_URL = "https://api.yookassa.ru/v3"
    
    async def check_subscription(self, telegram_id: int) -> bool:
        """
        Check if user has active subscription (alias for check_premium).
        Used by auth middleware.
        """
        return await self.check_premium(telegram_id)
    
    async def check_channel_subscription(self, bot, user_id: int, channel_id: str) -> bool:
        """
        Check if user is subscribed to a Telegram channel.
        
        Args:
            bot: Telegram bot instance
            user_id: Telegram user ID
            channel_id: Channel ID or username
            
        Returns:
            True if user is subscribed to channel
        """
        try:
            member = await bot.get_chat_member(channel_id, user_id)
            return member.status in ('member', 'administrator', 'creator')
        except Exception as e:
            logger.error("Failed to check channel subscription", error=str(e), user_id=user_id, channel_id=channel_id)
            return True  # Allow if can't check
    
    async def get_subscription_message(self, language: str = "ru") -> str:
        """
        Get message asking user to subscribe to channel.
        
        Args:
            language: User language
            
        Returns:
            Subscription request message
        """
        if language == "ru":
            return (
                "📢 <b>Подписка на канал</b>\n\n"
                "Для использования бота необходимо подписаться на наш канал.\n"
                "После подписки нажмите кнопку «Проверить подписку»."
            )
        else:
            return (
                "📢 <b>Channel Subscription</b>\n\n"
                "To use the bot, you need to subscribe to our channel.\n"
                "After subscribing, click the «Check Subscription» button."
            )
    
    async def check_premium(self, telegram_id: int) -> bool:
        """
        Check if user has active premium subscription.
        
        Args:
            telegram_id: Telegram user ID
            
        Returns:
            True if user has active premium
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(User)
                .where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return False
            
            return user.is_premium
    
    async def get_subscription_info(
        self,
        telegram_id: int
    ) -> Dict[str, Any]:
        """
        Get user's subscription information.
        
        Returns:
            Dict with subscription details
        """
        async with async_session_maker() as session:
            result = await session.execute(
                select(User)
                .where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                return {
                    "type": "free",
                    "is_premium": False,
                    "expires_at": None
                }
            
            return {
                "type": user.subscription_type.value,
                "is_premium": user.is_premium,
                "expires_at": user.subscription_expires_at
            }
    
    async def create_payment(
        self,
        telegram_id: int,
        months: int = 1
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Create payment for premium subscription.
        
        Args:
            telegram_id: Telegram user ID
            months: Number of months to subscribe
            
        Returns:
            Tuple of (payment_url, payment_id) or (None, None) on error
        """
        amount = settings.premium_price_rub * months
        
        # Generate unique payment ID
        payment_id = f"sub_{telegram_id}_{uuid.uuid4().hex[:8]}"
        
        if settings.payment_provider == "yookassa":
            return await self._create_yookassa_payment(
                telegram_id=telegram_id,
                amount=amount,
                payment_id=payment_id,
                months=months
            )
        else:
            logger.error("Unknown payment provider", provider=settings.payment_provider)
            return None, None
    
    async def _create_yookassa_payment(
        self,
        telegram_id: int,
        amount: int,
        payment_id: str,
        months: int
    ) -> Tuple[Optional[str], Optional[str]]:
        """Create YooKassa payment."""
        shop_id = settings.yookassa_shop_id
        secret_key = settings.yookassa_secret_key
        
        if not shop_id or not secret_key:
            logger.error("YooKassa not configured")
            return None, None
        
        # Create payment request
        payload = {
            "amount": {
                "value": f"{amount}.00",
                "currency": "RUB"
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": f"https://t.me/{settings.bot_username}"
            },
            "description": f"Премиум подписка на {months} мес.",
            "metadata": {
                "telegram_id": telegram_id,
                "months": months,
                "payment_id": payment_id
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "Idempotence-Key": payment_id
        }
        
        auth = aiohttp.BasicAuth(shop_id, secret_key)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.YOOKASSA_API_URL}/payments",
                    json=payload,
                    headers=headers,
                    auth=auth
                ) as response:
                    if response.status != 200:
                        error = await response.text()
                        logger.error("YooKassa payment creation failed", error=error)
                        return None, None
                    
                    data = await response.json()
                    
                    payment_url = data["confirmation"]["confirmation_url"]
                    yookassa_id = data["id"]
                    
                    logger.info(
                        "Payment created",
                        payment_id=payment_id,
                        yookassa_id=yookassa_id,
                        telegram_id=telegram_id
                    )
                    
                    return payment_url, yookassa_id
                    
        except Exception as e:
            logger.error("Failed to create YooKassa payment", error=str(e))
            return None, None
    
    async def process_payment_webhook(
        self,
        data: Dict[str, Any]
    ) -> bool:
        """
        Process payment webhook from YooKassa.
        
        Args:
            data: Webhook payload
            
        Returns:
            True if processed successfully
        """
        try:
            event = data.get("event")
            payment = data.get("object", {})
            
            if event != "payment.succeeded":
                logger.info("Ignoring webhook event", event=event)
                return True
            
            metadata = payment.get("metadata", {})
            telegram_id = metadata.get("telegram_id")
            months = metadata.get("months", 1)
            payment_id = metadata.get("payment_id")
            
            if not telegram_id:
                logger.error("Missing telegram_id in payment metadata")
                return False
            
            # Activate subscription
            return await self.activate_subscription(
                telegram_id=int(telegram_id),
                months=int(months),
                payment_id=payment_id,
                payment_provider="yookassa",
                amount_rub=Decimal(payment["amount"]["value"])
            )
            
        except Exception as e:
            logger.error("Failed to process payment webhook", error=str(e))
            return False
    
    async def activate_subscription(
        self,
        telegram_id: int,
        months: int,
        payment_id: str,
        payment_provider: str,
        amount_rub: Decimal
    ) -> bool:
        """
        Activate premium subscription for user.
        
        Args:
            telegram_id: Telegram user ID
            months: Number of months
            payment_id: Payment ID from provider
            payment_provider: Provider name
            amount_rub: Amount paid in RUB
            
        Returns:
            True if activated successfully
        """
        async with async_session_maker() as session:
            # Get user
            result = await session.execute(
                select(User).where(User.telegram_id == telegram_id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                logger.error("User not found for subscription", telegram_id=telegram_id)
                return False
            
            # Calculate subscription period
            now = datetime.now(timezone.utc)
            
            # If user already has subscription, extend it
            if user.subscription_expires_at and user.subscription_expires_at > now:
                starts_at = user.subscription_expires_at
            else:
                starts_at = now
            
            expires_at = starts_at + timedelta(days=30 * months)
            
            # Update user subscription
            user.subscription_type = SubscriptionType.PREMIUM
            user.subscription_expires_at = expires_at
            
            # Create subscription record
            subscription = Subscription(
                user_id=user.id,
                payment_id=payment_id,
                payment_provider=payment_provider,
                amount_rub=amount_rub,
                starts_at=starts_at,
                expires_at=expires_at,
                is_active=True
            )
            
            session.add(subscription)
            await session.commit()
            
            logger.info(
                "Subscription activated",
                telegram_id=telegram_id,
                expires_at=expires_at
            )
            
            return True
    
    async def refresh_subscription(self, bot, user_id: int) -> bool:
        """
        Force refresh subscription status by checking channel membership.
        
        Args:
            bot: Telegram bot instance
            user_id: Telegram user ID
            
        Returns:
            True if user is subscribed to channel
        """
        channel_id = settings.telegram_channel_id or settings.telegram_channel_username
        if not channel_id:
            return True  # No channel configured, allow access
        
        return await self.check_channel_subscription(bot, user_id, channel_id)
    
    async def get_subscription_success_message(self, language: str = "ru") -> str:
        """Get success message for subscription confirmation."""
        if language == "ru":
            return (
                "✅ <b>Подписка подтверждена!</b>\n\n"
                "Спасибо за подписку на наш канал!\n"
                "Теперь вам доступны все функции бота."
            )
        else:
            return (
                "✅ <b>Subscription confirmed!</b>\n\n"
                "Thank you for subscribing to our channel!\n"
                "All bot features are now available to you."
            )
    
    async def get_subscription_still_needed_message(self, language: str = "ru") -> str:
        """Get message when subscription is still required."""
        if language == "ru":
            return (
                "❌ <b>Подписка не обнаружена</b>\n\n"
                "Пожалуйста, подпишитесь на канал и нажмите кнопку ещё раз.\n\n"
                "Если вы уже подписались, подождите несколько секунд и попробуйте снова."
            )
        else:
            return (
                "❌ <b>Subscription not found</b>\n\n"
                "Please subscribe to the channel and press the button again.\n\n"
                "If you already subscribed, wait a few seconds and try again."
            )
    
    async def get_subscription_text(
        self,
        telegram_id: int,
        language: str = "ru"
    ) -> str:
        """
        Get formatted subscription status text.
        
        Returns:
            Formatted string with subscription info
        """
        info = await self.get_subscription_info(telegram_id)
        
        if info["is_premium"]:
            expires = info["expires_at"]
            expires_str = expires.strftime("%d.%m.%Y") if language == "ru" else expires.strftime("%Y-%m-%d")
            
            if language == "ru":
                text = (
                    "💳 <b>Ваша подписка</b>\n\n"
                    f"✅ Статус: <b>Премиум</b>\n"
                    f"📅 Действует до: {expires_str}\n\n"
                    "🚀 У вас безлимитный доступ ко всем функциям!"
                )
            else:
                text = (
                    "💳 <b>Your Subscription</b>\n\n"
                    f"✅ Status: <b>Premium</b>\n"
                    f"📅 Valid until: {expires_str}\n\n"
                    "🚀 You have unlimited access to all features!"
                )
        else:
            price = settings.premium_price_rub
            
            if language == "ru":
                text = (
                    "💳 <b>Ваша подписка</b>\n\n"
                    f"📝 Статус: <b>Бесплатный</b>\n\n"
                    "Ограничения бесплатной версии:\n"
                    "• 10 текстовых запросов/день\n"
                    "• 5 изображений/день\n"
                    "• 5 видео/день\n"
                    "• 5 голосовых/день\n"
                    "• 3 презентации/день\n\n"
                    f"💎 <b>Премиум подписка</b> — {price}₽/месяц\n"
                    "✅ Безлимитный доступ ко всем функциям!\n\n"
                    "Нажмите кнопку ниже для оформления:"
                )
            else:
                text = (
                    "💳 <b>Your Subscription</b>\n\n"
                    f"📝 Status: <b>Free</b>\n\n"
                    "Free version limits:\n"
                    "• 10 text requests/day\n"
                    "• 5 images/day\n"
                    "• 5 videos/day\n"
                    "• 5 voice/day\n"
                    "• 3 presentations/day\n\n"
                    f"💎 <b>Premium subscription</b> — {price}₽/month\n"
                    "✅ Unlimited access to all features!\n\n"
                    "Click the button below to subscribe:"
                )
        
        return text


# Global service instances
subscription_service = SubscriptionService()
premium_service = subscription_service  # Alias for compatibility
