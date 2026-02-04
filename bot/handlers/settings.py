"""
Settings handler.
Handles user preferences and configuration.
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery

from bot.services.user_service import user_service
from bot.keyboards.main import get_settings_keyboard
from bot.keyboards.inline import (
    get_gpt_model_keyboard,
    get_image_style_keyboard,
    get_language_keyboard,
    get_ai_provider_keyboard,
    get_qwen_model_keyboard
)
from bot.services.qwen_service import qwen_service
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
    model = user_settings.get("gpt_model", "gpt-4o-mini")
    style = user_settings.get("image_style", "vivid")
    auto_voice = user_settings.get("auto_voice_process", False)
    ai_provider = user_settings.get("ai_provider", "openai")
    qwen_model = user_settings.get("qwen_model", "qwen-plus")
    
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
            current_model=model,
            current_style=style,
            auto_voice=auto_voice,
            language=language,
            ai_provider=ai_provider,
            qwen_model=qwen_model
        )
    )


@router.callback_query(F.data == "settings:model")
async def callback_settings_model(callback: CallbackQuery):
    """Show GPT model selection."""
    user = callback.from_user
    user_settings = await user_service.get_user_settings(user.id)
    
    language = user_settings.get("language", "ru")
    current_model = user_settings.get("gpt_model", "gpt-4o-mini")
    
    if language == "ru":
        text = (
            "🤖 <b>Выбор модели GPT</b>\n\n"
            "<b>GPT-4o</b> — самая умная модель, лучше понимает контекст, "
            "даёт более точные ответы. Медленнее.\n\n"
            "<b>GPT-4o-mini</b> — быстрая и экономичная модель, "
            "отлично справляется с большинством задач."
        )
    else:
        text = (
            "🤖 <b>Choose GPT Model</b>\n\n"
            "<b>GPT-4o</b> — the smartest model, better context understanding, "
            "more accurate responses. Slower.\n\n"
            "<b>GPT-4o-mini</b> — fast and economical model, "
            "handles most tasks excellently."
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_gpt_model_keyboard(current_model, language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("model:"))
async def callback_select_model(callback: CallbackQuery):
    """Handle model selection."""
    user = callback.from_user
    model = callback.data.split(":")[1]  # gpt-4o or gpt-4o-mini
    
    await user_service.update_user_settings(user.id, {"gpt_model": model})
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        model_name = "GPT-4o" if model == "gpt-4o" else "GPT-4o-mini"
        await callback.answer(f"✅ Модель изменена на {model_name}", show_alert=True)
    else:
        model_name = "GPT-4o" if model == "gpt-4o" else "GPT-4o-mini"
        await callback.answer(f"✅ Model changed to {model_name}", show_alert=True)
    
    # Update keyboard to show new selection
    await callback.message.edit_reply_markup(
        reply_markup=get_gpt_model_keyboard(model, language)
    )


# =========================================
# AI Provider Selection
# =========================================

@router.callback_query(F.data == "settings:provider")
async def callback_settings_provider(callback: CallbackQuery):
    """Show AI provider selection."""
    user = callback.from_user
    user_settings = await user_service.get_user_settings(user.id)
    
    language = user_settings.get("language", "ru")
    current_provider = user_settings.get("ai_provider", "openai")
    qwen_available = qwen_service.is_configured()
    
    if language == "ru":
        text = (
            "🔌 <b>Выбор AI провайдера</b>\n\n"
            "<b>OpenAI</b> — GPT-4o, DALL-E 3, Sora, Whisper. "
            "Мощные модели, широкие возможности.\n\n"
            "<b>Qwen</b> — модели от Alibaba Cloud. "
            "Хорошее понимание китайского языка, экономичнее."
        )
        if not qwen_available:
            text += "\n\n⚠️ <i>Qwen API не настроен администратором.</i>"
    else:
        text = (
            "🔌 <b>Choose AI Provider</b>\n\n"
            "<b>OpenAI</b> — GPT-4o, DALL-E 3, Sora, Whisper. "
            "Powerful models, wide capabilities.\n\n"
            "<b>Qwen</b> — models from Alibaba Cloud. "
            "Good Chinese language understanding, more economical."
        )
        if not qwen_available:
            text += "\n\n⚠️ <i>Qwen API is not configured by admin.</i>"
    
    await callback.message.edit_text(
        text,
        reply_markup=get_ai_provider_keyboard(current_provider, qwen_available, language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("provider:"))
async def callback_select_provider(callback: CallbackQuery):
    """Handle provider selection."""
    user = callback.from_user
    provider = callback.data.split(":")[1]
    
    language = await user_service.get_user_language(user.id)
    
    # Handle unavailable Qwen
    if provider == "qwen_unavailable":
        if language == "ru":
            await callback.answer(
                "⚠️ Qwen API не настроен.\n"
                "Обратитесь к администратору для настройки.",
                show_alert=True
            )
        else:
            await callback.answer(
                "⚠️ Qwen API is not configured.\n"
                "Contact administrator to set it up.",
                show_alert=True
            )
        return
    
    # Update user settings
    await user_service.update_user_settings(user.id, {"ai_provider": provider})
    
    if language == "ru":
        provider_name = "OpenAI" if provider == "openai" else "Qwen"
        await callback.answer(f"✅ Провайдер изменён на {provider_name}", show_alert=True)
    else:
        provider_name = "OpenAI" if provider == "openai" else "Qwen"
        await callback.answer(f"✅ Provider changed to {provider_name}", show_alert=True)
    
    qwen_available = qwen_service.is_configured()
    
    # Update keyboard to show new selection
    await callback.message.edit_reply_markup(
        reply_markup=get_ai_provider_keyboard(provider, qwen_available, language)
    )


# =========================================
# Qwen Model Selection
# =========================================

@router.callback_query(F.data == "settings:qwen_model")
async def callback_settings_qwen_model(callback: CallbackQuery):
    """Show Qwen model selection."""
    user = callback.from_user
    user_settings = await user_service.get_user_settings(user.id)
    
    language = user_settings.get("language", "ru")
    current_model = user_settings.get("qwen_model", "qwen-plus")
    
    if language == "ru":
        text = (
            "🔮 <b>Выбор модели Qwen</b>\n\n"
            "<b>Qwen Turbo</b> — быстрая и экономичная модель, "
            "подходит для простых задач.\n\n"
            "<b>Qwen Plus</b> — баланс между скоростью и качеством, "
            "оптимальный выбор для большинства задач.\n\n"
            "<b>Qwen Max</b> — самая умная модель, лучше понимает контекст, "
            "подходит для сложных задач."
        )
    else:
        text = (
            "🔮 <b>Choose Qwen Model</b>\n\n"
            "<b>Qwen Turbo</b> — fast and economical model, "
            "suitable for simple tasks.\n\n"
            "<b>Qwen Plus</b> — balance between speed and quality, "
            "optimal choice for most tasks.\n\n"
            "<b>Qwen Max</b> — smartest model, better context understanding, "
            "suitable for complex tasks."
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=get_qwen_model_keyboard(current_model, language)
    )
    await callback.answer()


@router.callback_query(F.data.startswith("qwen_model:"))
async def callback_select_qwen_model(callback: CallbackQuery):
    """Handle Qwen model selection."""
    user = callback.from_user
    model = callback.data.split(":")[1]  # qwen-turbo, qwen-plus, qwen-max
    
    await user_service.update_user_settings(user.id, {"qwen_model": model})
    
    language = await user_service.get_user_language(user.id)
    
    model_names = {
        "qwen-turbo": "Qwen Turbo",
        "qwen-plus": "Qwen Plus",
        "qwen-max": "Qwen Max"
    }
    model_name = model_names.get(model, model)
    
    if language == "ru":
        await callback.answer(f"✅ Модель изменена на {model_name}", show_alert=True)
    else:
        await callback.answer(f"✅ Model changed to {model_name}", show_alert=True)
    
    # Update keyboard to show new selection
    await callback.message.edit_reply_markup(
        reply_markup=get_qwen_model_keyboard(model, language)
    )


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
            current_model=user_settings.get("gpt_model", "gpt-4o-mini"),
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
            current_model=user_settings.get("gpt_model", "gpt-4o-mini"),
            current_style=user_settings.get("image_style", "vivid"),
            auto_voice=user_settings.get("auto_voice_process", False),
            language=language,
            ai_provider=user_settings.get("ai_provider", "openai"),
            qwen_model=user_settings.get("qwen_model", "qwen-plus")
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
