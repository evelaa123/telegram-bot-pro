"""
Settings handler.
Handles user preferences and configuration.
Simplified - no model selection (fixed by TZ).
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.types import InlineKeyboardButton

from bot.services.user_service import user_service
from bot.services.subscription_service import premium_service
from bot.keyboards.main import get_settings_keyboard
from bot.keyboards.inline import (
    get_image_style_keyboard,
    get_language_keyboard,
)
import structlog

logger = structlog.get_logger()
router = Router()


@router.message(Command("settings"))
async def cmd_settings(message: Message):
    """Handle /settings command."""
    await show_settings(message)


async def show_settings(message: Message):
    """Show settings menu."""
    user = message.from_user
    user_settings = await user_service.get_user_settings(user.id)
    
    language = user_settings.get("language", "ru")
    style = user_settings.get("image_style", "vivid")
    auto_voice = user_settings.get("auto_voice_process", False)
    
    if language == "ru":
        text = (
            "⚙️ <b>Настройки</b>\n\n"
            "Выберите параметр для изменения:"
        )
    else:
        text = (
            "⚙️ <b>Settings</b>\n\n"
            "Choose a setting to change:"
        )
    
    await message.answer(
        text,
        reply_markup=get_settings_keyboard(
            current_style=style,
            auto_voice=auto_voice,
            language=language
        )
    )


# =========================================
# Subscription Settings
# =========================================

@router.callback_query(F.data == "settings:subscription")
async def callback_settings_subscription(callback: CallbackQuery):
    """Show subscription info and purchase options."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    text = await premium_service.get_subscription_text(user.id, language)
    
    # Check if already premium
    is_premium = await premium_service.check_premium(user.id)
    
    builder = InlineKeyboardBuilder()
    
    if not is_premium:
        if language == "ru":
            builder.row(
                InlineKeyboardButton(
                    text="💎 Оформить подписку",
                    callback_data="subscription:buy:1"
                )
            )
        else:
            builder.row(
                InlineKeyboardButton(
                    text="💎 Get Subscription",
                    callback_data="subscription:buy:1"
                )
            )
    
    back_text = "◀️ Назад" if language == "ru" else "◀️ Back"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="settings:back_to_settings"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("subscription:buy:"))
async def callback_buy_subscription(callback: CallbackQuery):
    """Handle subscription purchase."""
    user = callback.from_user
    months = int(callback.data.split(":")[2])
    language = await user_service.get_user_language(user.id)
    
    # Create payment
    payment_url, payment_id = await premium_service.create_payment(user.id, months)
    
    if not payment_url:
        if language == "ru":
            await callback.answer("❌ Ошибка создания платежа. Попробуйте позже.", show_alert=True)
        else:
            await callback.answer("❌ Payment creation error. Try again later.", show_alert=True)
        return
    
    # Send payment link
    builder = InlineKeyboardBuilder()
    
    if language == "ru":
        builder.row(
            InlineKeyboardButton(text="💳 Оплатить", url=payment_url)
        )
        text = (
            "💳 <b>Оплата подписки</b>\n\n"
            f"Сумма: {settings.premium_price_rub * months}₽\n"
            f"Период: {months} мес.\n\n"
            "Нажмите кнопку для перехода к оплате:"
        )
    else:
        builder.row(
            InlineKeyboardButton(text="💳 Pay", url=payment_url)
        )
        text = (
            "💳 <b>Subscription Payment</b>\n\n"
            f"Amount: {settings.premium_price_rub * months}₽\n"
            f"Period: {months} month(s)\n\n"
            "Click the button to proceed to payment:"
        )
    
    back_text = "◀️ Назад" if language == "ru" else "◀️ Back"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="settings:subscription"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


# =========================================
# Timezone Settings
# =========================================

@router.callback_query(F.data == "settings:timezone")
async def callback_settings_timezone(callback: CallbackQuery):
    """Show timezone selection."""
    user = callback.from_user
    user_settings = await user_service.get_user_settings(user.id)
    
    language = user_settings.get("language", "ru")
    current_tz = user_settings.get("timezone", "Europe/Moscow")
    
    timezones = [
        ("Europe/Moscow", "🇷🇺 Москва (UTC+3)"),
        ("Europe/Kaliningrad", "🇷🇺 Калининград (UTC+2)"),
        ("Asia/Yekaterinburg", "🇷🇺 Екатеринбург (UTC+5)"),
        ("Asia/Novosibirsk", "🇷🇺 Новосибирск (UTC+7)"),
        ("Asia/Vladivostok", "🇷🇺 Владивосток (UTC+10)"),
        ("Europe/Kiev", "🇺🇦 Киев (UTC+2)"),
        ("Europe/Minsk", "🇧🇾 Минск (UTC+3)"),
    ]
    
    if language == "ru":
        text = "🕐 <b>Выберите часовой пояс</b>\n\nТекущий: " + current_tz
    else:
        text = "🕐 <b>Select Timezone</b>\n\nCurrent: " + current_tz
    
    builder = InlineKeyboardBuilder()
    
    for tz_code, tz_name in timezones:
        prefix = "✓ " if tz_code == current_tz else ""
        builder.row(
            InlineKeyboardButton(
                text=f"{prefix}{tz_name}",
                callback_data=f"timezone:{tz_code}"
            )
        )
    
    back_text = "◀️ Назад" if language == "ru" else "◀️ Back"
    builder.row(InlineKeyboardButton(text=back_text, callback_data="settings:back_to_settings"))
    
    await callback.message.edit_text(text, reply_markup=builder.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("timezone:"))
async def callback_select_timezone(callback: CallbackQuery):
    """Handle timezone selection."""
    user = callback.from_user
    tz = callback.data.split(":")[1]
    
    await user_service.update_user_settings(user.id, {"timezone": tz})
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.answer(f"✅ Часовой пояс изменён", show_alert=True)
    else:
        await callback.answer(f"✅ Timezone changed", show_alert=True)
    
    # Go back to settings
    await callback_settings_timezone(callback)


@router.callback_query(F.data == "settings:style")
async def callback_settings_style(callback: CallbackQuery):
    """Show image style selection."""
    user = callback.from_user
    user_settings = await user_service.get_user_settings(user.id)
    
    language = user_settings.get("language", "ru")
    current_style = user_settings.get("image_style", "vivid")
    
    if language == "ru":
        text = (
            "🎨 <b>Стиль изображений</b>\n\n"
            "<b>Vivid (яркий)</b> — насыщенные цвета, драматичное освещение, "
            "выразительная композиция.\n\n"
            "<b>Natural (естественный)</b> — реалистичные цвета, "
            "натуральное освещение, фотореалистичный стиль."
        )
    else:
        text = (
            "🎨 <b>Image Style</b>\n\n"
            "<b>Vivid</b> — saturated colors, dramatic lighting, "
            "expressive composition.\n\n"
            "<b>Natural</b> — realistic colors, "
            "natural lighting, photorealistic style."
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_image_style_keyboard(current_style, language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("style:"))
async def callback_select_style(callback: CallbackQuery):
    """Handle style selection."""
    user = callback.from_user
    style = callback.data.split(":")[1]  # vivid or natural
    
    await user_service.update_user_settings(user.id, {"image_style": style})
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        style_name = "Vivid (яркий)" if style == "vivid" else "Natural (естественный)"
        await callback.answer(f"✅ Стиль изменён на {style_name}", show_alert=True)
    else:
        style_name = "Vivid" if style == "vivid" else "Natural"
        await callback.answer(f"✅ Style changed to {style_name}", show_alert=True)
    
    await callback.message.edit_reply_markup(
        reply_markup=get_image_style_keyboard(style, language)
    )


@router.callback_query(F.data == "settings:voice")
async def callback_settings_voice(callback: CallbackQuery):
    """Toggle auto voice processing."""
    user = callback.from_user
    user_settings = await user_service.get_user_settings(user.id)
    
    current_value = user_settings.get("auto_voice_process", False)
    new_value = not current_value
    
    await user_service.update_user_settings(user.id, {"auto_voice_process": new_value})
    
    language = user_settings.get("language", "ru")
    
    if language == "ru":
        if new_value:
            await callback.answer(
                "✅ Авто-обработка голоса включена.\n"
                "Голосовые сообщения будут автоматически отправляться как запрос к GPT.",
                show_alert=True
            )
        else:
            await callback.answer(
                "❌ Авто-обработка голоса выключена.\n"
                "Голосовые сообщения будут только транскрибироваться.",
                show_alert=True
            )
    else:
        if new_value:
            await callback.answer(
                "✅ Auto voice processing enabled.\n"
                "Voice messages will be automatically sent as GPT requests.",
                show_alert=True
            )
        else:
            await callback.answer(
                "❌ Auto voice processing disabled.\n"
                "Voice messages will only be transcribed.",
                show_alert=True
            )
    
    # Refresh settings keyboard
    user_settings = await user_service.get_user_settings(user.id)
    await callback.message.edit_reply_markup(
        reply_markup=get_settings_keyboard(
            current_style=user_settings.get("image_style", "vivid"),
            auto_voice=new_value,
            language=language
        )
    )


@router.callback_query(F.data == "settings:language")
async def callback_settings_language(callback: CallbackQuery):
    """Show language selection."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        text = (
            "🌐 <b>Выбор языка интерфейса</b>\n\n"
            "Выберите предпочитаемый язык:"
        )
    else:
        text = (
            "🌐 <b>Interface Language</b>\n\n"
            "Choose your preferred language:"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_language_keyboard(language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("language:"))
async def callback_select_language(callback: CallbackQuery):
    """Handle language selection."""
    user = callback.from_user
    language = callback.data.split(":")[1]  # ru or en
    
    await user_service.update_user_settings(user.id, {"language": language})
    
    if language == "ru":
        await callback.answer("✅ Язык изменён на русский", show_alert=True)
    else:
        await callback.answer("✅ Language changed to English", show_alert=True)
    
    # Обновляем inline клавиатуру
    await callback.message.edit_reply_markup(
        reply_markup=get_language_keyboard(language)
    )
    
    # НОВОЕ: Обновляем главное меню (Reply клавиатуру)
    from bot.keyboards.main import get_main_menu_keyboard
    
    if language == "ru":
        await callback.message.answer(
            "🌐 Язык интерфейса изменён.",
            reply_markup=get_main_menu_keyboard(language)
        )
    else:
        await callback.message.answer(
            "🌐 Interface language changed.",
            reply_markup=get_main_menu_keyboard(language)
        )



@router.callback_query(F.data == "settings:back_to_settings")
async def callback_back_to_settings(callback: CallbackQuery):
    """Go back to main settings menu."""
    user = callback.from_user
    user_settings = await user_service.get_user_settings(user.id)
    
    language = user_settings.get("language", "ru")
    
    if language == "ru":
        text = (
            "⚙️ <b>Настройки</b>\n\n"
            "Выберите параметр для изменения:"
        )
    else:
        text = (
            "⚙️ <b>Settings</b>\n\n"
            "Choose a setting to change:"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_settings_keyboard(
            current_style=user_settings.get("image_style", "vivid"),
            auto_voice=user_settings.get("auto_voice_process", False),
            language=language
        )
    )
    await callback.answer()


@router.callback_query(F.data == "settings:back")
async def callback_settings_close(callback: CallbackQuery):
    """Close settings menu."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.edit_text("✅ Настройки сохранены.")
    else:
        await callback.message.edit_text("✅ Settings saved.")
    
    await callback.answer()
