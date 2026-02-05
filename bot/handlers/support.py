"""
Support handler.
Handles user support messages to admins.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from bot.services.user_service import user_service
from database.redis_client import redis_client
from database import async_session_maker
from database.models import SupportMessage, User
from sqlalchemy import select
import structlog

logger = structlog.get_logger()
router = Router()


@router.message(Command("support"))
async def cmd_support(message: Message):
    """Handle /support command - start support conversation."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    # Set user state to support mode
    await redis_client.set_user_state(user.id, "support_message")
    
    if language == "ru":
        await message.answer(
            "📨 <b>Техническая поддержка</b>\n\n"
            "Опишите вашу проблему или вопрос, и мы ответим вам как можно скорее.\n\n"
            "<i>Напишите ваше сообщение:</i>",
            reply_markup=get_cancel_keyboard(language)
        )
    else:
        await message.answer(
            "📨 <b>Tech Support</b>\n\n"
            "Describe your issue or question, and we'll respond as soon as possible.\n\n"
            "<i>Write your message:</i>",
            reply_markup=get_cancel_keyboard(language)
        )


@router.callback_query(F.data == "support:cancel")
async def callback_support_cancel(callback: CallbackQuery):
    """Handle support cancel."""
    user = callback.from_user
    await redis_client.clear_user_state(user.id)
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.edit_text("❌ Обращение в поддержку отменено.")
    else:
        await callback.message.edit_text("❌ Support request cancelled.")
    
    await callback.answer()


def get_cancel_keyboard(language: str = "ru"):
    """Get cancel keyboard for support."""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="❌ Отмена" if language == "ru" else "❌ Cancel",
            callback_data="support:cancel"
        )
    )
    return builder.as_markup()


async def save_support_message(
    user_telegram_id: int,
    message_text: str,
    is_from_user: bool = True,
    admin_id: int = None
) -> int:
    """
    Save support message to database.
    
    Returns:
        Message ID
    """
    async with async_session_maker() as session:
        # Get user by telegram_id
        result = await session.execute(
            select(User).where(User.telegram_id == user_telegram_id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise ValueError(f"User not found: {user_telegram_id}")
        
        support_msg = SupportMessage(
            user_id=user.id,
            message=message_text,
            is_from_user=is_from_user,
            admin_id=admin_id,
            is_read=False
        )
        
        session.add(support_msg)
        await session.commit()
        await session.refresh(support_msg)
        
        return support_msg.id


async def handle_support_message(message: Message, user_id: int):
    """
    Handle incoming support message from user.
    Called from text.py when user is in support_message state.
    """
    language = await user_service.get_user_language(user_id)
    
    try:
        # Save the message
        msg_id = await save_support_message(
            user_telegram_id=user_id,
            message_text=message.text,
            is_from_user=True
        )
        
        # Clear user state
        await redis_client.clear_user_state(user_id)
        
        if language == "ru":
            await message.answer(
                "✅ <b>Сообщение отправлено!</b>\n\n"
                "Наша команда поддержки рассмотрит ваше обращение и ответит вам в ближайшее время.\n\n"
                "💡 Используйте /support чтобы отправить ещё одно сообщение."
            )
        else:
            await message.answer(
                "✅ <b>Message sent!</b>\n\n"
                "Our support team will review your request and respond shortly.\n\n"
                "💡 Use /support to send another message."
            )
        
        logger.info(
            "Support message received",
            user_id=user_id,
            message_id=msg_id,
            message_preview=message.text[:100]
        )
        
    except Exception as e:
        logger.error("Failed to save support message", error=str(e), user_id=user_id)
        
        if language == "ru":
            await message.answer(
                "❌ Произошла ошибка при отправке сообщения. Попробуйте позже."
            )
        else:
            await message.answer(
                "❌ An error occurred while sending your message. Please try again later."
            )


async def get_unread_support_count() -> int:
    """Get count of unread support messages."""
    async with async_session_maker() as session:
        from sqlalchemy import func
        result = await session.execute(
            select(func.count(SupportMessage.id))
            .where(SupportMessage.is_from_user == True)
            .where(SupportMessage.is_read == False)
        )
        return result.scalar() or 0
