"""
General callback handlers.
Handles subscription checks, limit refreshes, and photo:animate callbacks.
"""
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery

from bot.services.subscription_service import subscription_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.main import get_subscription_keyboard, get_limits_keyboard, get_main_menu_keyboard
from database.redis_client import redis_client
from database.models import RequestType
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


@router.callback_query(F.data == "subscription:buy")
async def callback_subscription_buy(callback: CallbackQuery):
    """Handle subscription buy button — create payment and show payment link.
    
    This is triggered from limit-reached messages and subscription info.
    Instead of duplicating subscription text, go directly to payment.
    """
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    # Check if already premium
    is_premium = await subscription_service.check_premium(user.id)
    if is_premium:
        if language == "ru":
            await callback.answer("✅ У вас уже есть премиум подписка!", show_alert=True)
        else:
            await callback.answer("✅ You already have a premium subscription!", show_alert=True)
        return
    
    # Create payment (1 month)
    payment_url, payment_id = await subscription_service.create_payment(user.id, months=1)
    
    if payment_url:
        from aiogram.types import InlineKeyboardButton
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        
        builder = InlineKeyboardBuilder()
        builder.row(
            InlineKeyboardButton(
                text="💳 Оплатить" if language == "ru" else "💳 Pay",
                url=payment_url
            )
        )
        builder.row(
            InlineKeyboardButton(
                text="❌ Отмена" if language == "ru" else "❌ Cancel",
                callback_data="subscription:close"
            )
        )
        
        price = settings.premium_price_rub
        if language == "ru":
            text = (
                "💎 <b>Оформление подписки</b>\n\n"
                f"💰 Стоимость: {price}₽/месяц\n\n"
                "После оплаты вам будут доступны расширенные лимиты.\n"
                "Нажмите кнопку ниже для перехода к оплате:"
            )
        else:
            text = (
                "💎 <b>Subscribe</b>\n\n"
                f"💰 Price: {price}₽/month\n\n"
                "After payment you'll get extended limits.\n"
                "Click the button below to proceed to payment:"
            )
        
        try:
            await callback.message.edit_text(text, reply_markup=builder.as_markup())
        except Exception:
            await callback.message.answer(text, reply_markup=builder.as_markup())
    else:
        if language == "ru":
            await callback.answer(
                "❌ Оплата временно недоступна. Попробуйте позже.",
                show_alert=True
            )
        else:
            await callback.answer(
                "❌ Payment temporarily unavailable. Try later.",
                show_alert=True
            )
    
    await callback.answer()


@router.callback_query(F.data == "subscription:close")
async def callback_subscription_close(callback: CallbackQuery):
    """Handle subscription close button."""
    try:
        await callback.message.delete()
    except Exception:
        pass
    await callback.answer()


@router.callback_query(F.data == "subscription:check")
async def callback_subscription_check(callback: CallbackQuery, bot: Bot):
    """Handle subscription check button."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    # Force refresh subscription status
    is_subscribed = await subscription_service.refresh_subscription(bot, user.id)
    
    if is_subscribed:
        # Subscription confirmed
        success_message = await subscription_service.get_subscription_success_message(language)
        
        await callback.message.edit_text(success_message)
        
        # Send main menu
        await callback.message.answer(
            "📱 Главное меню:" if language == "ru" else "📱 Main menu:",
            reply_markup=get_main_menu_keyboard(language)
        )
        
        await callback.answer()
        
        logger.info("Subscription confirmed", user_id=user.id)
    else:
        # Still not subscribed
        still_needed_message = await subscription_service.get_subscription_still_needed_message(language)
        
        await callback.message.edit_text(
            still_needed_message,
            reply_markup=get_subscription_keyboard(
                settings.telegram_channel_username,
                language
            )
        )
        
        await callback.answer()


@router.callback_query(F.data == "limits:refresh")
async def callback_limits_refresh(callback: CallbackQuery):
    """Handle limits refresh button."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    limits_text = await limit_service.get_limits_text(user.id, language)
    
    try:
        await callback.message.edit_text(
            limits_text,
            reply_markup=get_limits_keyboard(language)
        )
    except Exception:
        pass  # Message not modified
    
    await callback.answer(
        "🔄 Обновлено" if language == "ru" else "🔄 Refreshed"
    )


@router.callback_query(F.data == "limits:back")
async def callback_limits_back(callback: CallbackQuery):
    """Handle limits back button."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data == "noop")
async def callback_noop(callback: CallbackQuery):
    """Handle no-operation callbacks (e.g., pagination counters)."""
    await callback.answer()


@router.callback_query(F.data == "back")
async def callback_back(callback: CallbackQuery):
    """Generic back button handler."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    from database.redis_client import redis_client
    await redis_client.clear_user_state(user.id)
    
    await callback.message.delete()
    await callback.answer()
