"""
Authentication middleware.
Handles user registration, subscription checks, and bot enabled check.
"""
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware, Bot
from aiogram.types import Message, CallbackQuery, Update

from bot.services.user_service import user_service
from bot.services.subscription_service import subscription_service
from bot.services.settings_service import settings_service
from bot.keyboards.main import get_subscription_keyboard
from config import settings as config_settings
import structlog

logger = structlog.get_logger()


class AuthMiddleware(BaseMiddleware):
    """
    Middleware for user authentication and subscription verification.
    """
    
    BYPASS_COMMANDS = {'/start', '/help'}
    BYPASS_CALLBACKS = {'subscription:check'}
    
    async def __call__(
        self,
        handler: Callable[[Update, Dict[str, Any]], Awaitable[Any]],
        event: Update,
        data: Dict[str, Any]
    ) -> Any:
        """Process update through middleware."""
        
        user = None
        chat_id = None
        chat_type = None
        
        if isinstance(event, Message):
            user = event.from_user
            chat_id = event.chat.id
            chat_type = event.chat.type
        elif isinstance(event, CallbackQuery):
            user = event.from_user
            chat_id = event.message.chat.id if event.message else None
            chat_type = event.message.chat.type if event.message else None
        else:
            return await handler(event, data)
        
        if not user:
            return await handler(event, data)
        
        # ============================================
        # ГРУППЫ/КАНАЛЫ - ПРОПУСКАЕМ БЕЗ ПРОВЕРОК
        # Все проверки будут в channel_comments.py
        # после проверки триггера (упоминания бота)
        # ============================================
        if chat_type in ('group', 'supergroup', 'channel'):
            data['chat_type'] = chat_type
            return await handler(event, data)
        
        # ============================================
        # ДАЛЕЕ - ТОЛЬКО ДЛЯ ЛИЧНЫХ ЧАТОВ (private)
        # ============================================
        
        # 1. ПРОВЕРКА: ВКЛЮЧЁН ЛИ БОТ
        try:
            is_enabled = await settings_service.is_bot_enabled()
            
            if not is_enabled:
                disabled_msg = await settings_service.get_disabled_message()
                logger.info(f"Bot is disabled, blocking user {user.id}")
                
                if isinstance(event, Message):
                    await event.answer(f"🔒 {disabled_msg}")
                elif isinstance(event, CallbackQuery):
                    await event.answer(disabled_msg, show_alert=True)
                
                return None
        except Exception as e:
            logger.error(f"Error checking bot enabled status: {e}")
        
        # 2. РЕГИСТРАЦИЯ / ОБНОВЛЕНИЕ ПОЛЬЗОВАТЕЛЯ
        db_user = await user_service.get_or_create_user(
            telegram_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            language_code=user.language_code
        )
        
        data['db_user'] = db_user
        data['chat_type'] = chat_type
        
        # 3. ПРОВЕРКА БЛОКИРОВКИ
        if db_user.is_blocked:
            logger.warning("Blocked user attempted access", telegram_id=user.id)
            if isinstance(event, Message):
                await event.answer("🚫 Ваш аккаунт заблокирован.")
            elif isinstance(event, CallbackQuery):
                await event.answer("🚫 Ваш аккаунт заблокирован.", show_alert=True)
            return None
        
        # 4. ПРОВЕРКА BYPASS КОМАНД
        should_bypass = False
        
        if isinstance(event, Message) and event.text:
            command = event.text.split()[0].lower()
            should_bypass = command in self.BYPASS_COMMANDS
        elif isinstance(event, CallbackQuery) and event.data:
            should_bypass = event.data in self.BYPASS_CALLBACKS
        
        if should_bypass:
            return await handler(event, data)
        
        # 5. ПРОВЕРКА ПОДПИСКИ
        bot: Bot = data.get('bot')
        if not bot:
            return await handler(event, data)
        
        try:
            subscription_required = await settings_service.is_subscription_required()
            
            if subscription_required:
                channel_id = await settings_service.get_channel_id()
                if not channel_id:
                    channel_id = config_settings.telegram_channel_id
                
                channel_username = await settings_service.get_channel_username()
                if not channel_username:
                    channel_username = config_settings.telegram_channel_username
                
                if channel_id:
                    is_subscribed = await subscription_service.check_subscription(
                        bot, user.id, channel_id
                    )
                    data['is_subscribed'] = is_subscribed
                    
                    if not is_subscribed:
                        language = db_user.settings.get('language', 'ru') if db_user.settings else 'ru'
                        message_text = await subscription_service.get_subscription_message(language)
                        keyboard = get_subscription_keyboard(
                            channel_username or "@channel",
                            language
                        )
                        
                        if isinstance(event, Message):
                            await event.answer(message_text, reply_markup=keyboard)
                        elif isinstance(event, CallbackQuery):
                            if event.message:
                                await event.message.answer(message_text, reply_markup=keyboard)
                            await event.answer()
                        
                        return None
                        
        except Exception as e:
            logger.error(f"Error checking subscription: {e}")
        
        return await handler(event, data)
