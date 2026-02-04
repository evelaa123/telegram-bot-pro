"""
Reply keyboard layouts for the main bot menu.
"""
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder


def get_main_menu_keyboard(language: str = "ru") -> ReplyKeyboardMarkup:
    """
    Get main menu Reply keyboard.
    Layout: 2 columns grid.
    """
    texts = {
        "ru": {
            "text": "💬 Текст",
            "image": "🖼 Изображение",
            "video": "🎬 Видео",
            "document": "📄 Документ",
            "settings": "⚙️ Настройки",
            "limits": "📊 Мои лимиты",
            "new_dialog": "🔄 Новый диалог"
        },
        "en": {
            "text": "💬 Text",
            "image": "🖼 Image",
            "video": "🎬 Video",
            "document": "📄 Document",
            "settings": "⚙️ Settings",
            "limits": "📊 My Limits",
            "new_dialog": "🔄 New Dialog"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = ReplyKeyboardBuilder()
    
    # Row 1: Text, Image
    builder.add(KeyboardButton(text=t["text"]))
    builder.add(KeyboardButton(text=t["image"]))
    
    # Row 2: Video, Document  
    builder.add(KeyboardButton(text=t["video"]))
    builder.add(KeyboardButton(text=t["document"]))
    
    # Row 3: Settings, Limits
    builder.add(KeyboardButton(text=t["settings"]))
    builder.add(KeyboardButton(text=t["limits"]))
    
    # Row 4: New Dialog (centered)
    builder.add(KeyboardButton(text=t["new_dialog"]))
    
    # Adjust layout: 2-2-2-1
    builder.adjust(2, 2, 2, 1)
    
    return builder.as_markup(resize_keyboard=True)


def get_settings_keyboard(
    current_model: str = "gpt-4o-mini",
    current_style: str = "vivid",
    auto_voice: bool = False,
    language: str = "ru",
    ai_provider: str = "openai",
    qwen_model: str = "qwen-plus"
) -> InlineKeyboardMarkup:
    """
    Get settings inline keyboard.
    Shows current values and allows toggling.
    """
    texts = {
        "ru": {
            "provider": "🔌 AI Провайдер",
            "model": "🤖 Модель GPT",
            "qwen_model": "🔮 Модель Qwen",
            "style": "🎨 Стиль изображений",
            "voice": "🎤 Авто-обработка голоса",
            "lang": "🌐 Язык",
            "back": "◀️ Назад"
        },
        "en": {
            "provider": "🔌 AI Provider",
            "model": "🤖 GPT Model",
            "qwen_model": "🔮 Qwen Model",
            "style": "🎨 Image Style",
            "voice": "🎤 Auto Voice Processing",
            "lang": "🌐 Language",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    # Provider display
    provider_display = "OpenAI" if ai_provider == "openai" else "Qwen"
    
    # Model display (based on provider)
    if ai_provider == "openai":
        model_display = "GPT-4o" if current_model == "gpt-4o" else "GPT-4o-mini"
    else:
        model_display = qwen_model.replace("qwen-", "Qwen ").title()
    
    # Style display
    style_display = "Vivid" if current_style == "vivid" else "Natural"
    
    # Voice processing display
    voice_display = "✅" if auto_voice else "❌"
    
    # Language display
    lang_display = "🇷🇺 RU" if language == "ru" else "🇬🇧 EN"
    
    builder = InlineKeyboardBuilder()
    
    # AI Provider selection (NEW)
    builder.row(
        InlineKeyboardButton(
            text=f"{t['provider']}: {provider_display}",
            callback_data="settings:provider"
        )
    )
    
    # Show model selection based on current provider
    if ai_provider == "openai":
        builder.row(
            InlineKeyboardButton(
                text=f"{t['model']}: {model_display}",
                callback_data="settings:model"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=f"{t['qwen_model']}: {model_display}",
                callback_data="settings:qwen_model"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=f"{t['style']}: {style_display}",
            callback_data="settings:style"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{t['voice']}: {voice_display}",
            callback_data="settings:voice"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=f"{t['lang']}: {lang_display}",
            callback_data="settings:language"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["back"],
            callback_data="settings:back"
        )
    )
    
    return builder.as_markup()


def get_limits_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """Get limits info keyboard with refresh button."""
    texts = {
        "ru": {"refresh": "🔄 Обновить", "back": "◀️ Назад"},
        "en": {"refresh": "🔄 Refresh", "back": "◀️ Back"}
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t["refresh"], callback_data="limits:refresh"),
        InlineKeyboardButton(text=t["back"], callback_data="limits:back")
    )
    
    return builder.as_markup()


def get_subscription_keyboard(
    channel_username: str,
    language: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Get subscription check keyboard.
    Shows link to channel and check button.
    """
    texts = {
        "ru": {
            "subscribe": "📢 Подписаться на канал",
            "check": "✅ Я подписался"
        },
        "en": {
            "subscribe": "📢 Subscribe to Channel",
            "check": "✅ I Subscribed"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    # Clean channel username
    channel_link = channel_username if channel_username.startswith("@") else f"@{channel_username}"
    channel_url = f"https://t.me/{channel_link.lstrip('@')}"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t["subscribe"],
            url=channel_url
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["check"],
            callback_data="subscription:check"
        )
    )
    
    return builder.as_markup()


def get_confirm_keyboard(
    confirm_callback: str,
    cancel_callback: str,
    language: str = "ru"
) -> InlineKeyboardMarkup:
    """Generic confirm/cancel keyboard."""
    texts = {
        "ru": {"confirm": "✅ Подтвердить", "cancel": "❌ Отмена"},
        "en": {"confirm": "✅ Confirm", "cancel": "❌ Cancel"}
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t["confirm"], callback_data=confirm_callback),
        InlineKeyboardButton(text=t["cancel"], callback_data=cancel_callback)
    )
    
    return builder.as_markup()


def get_back_keyboard(callback_data: str = "back", language: str = "ru") -> InlineKeyboardMarkup:
    """Simple back button keyboard."""
    text = "◀️ Назад" if language == "ru" else "◀️ Back"
    
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text=text, callback_data=callback_data))
    
    return builder.as_markup()
