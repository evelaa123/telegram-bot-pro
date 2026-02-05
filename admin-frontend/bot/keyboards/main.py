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
    Layout: 2 columns grid with new features.
    """
    texts = {
        "ru": {
            "text": "💬 Текст",
            "image": "🖼 Изображение",
            "video": "🎬 Видео",
            "voice": "🎤 Голос",
            "presentation": "📊 Презентация",
            "assistant": "🗓 Ассистент",
            "settings": "⚙️ Настройки",
            "limits": "📊 Лимиты",
            "support": "📨 Поддержка",
            "new_dialog": "🔄 Новый диалог"
        },
        "en": {
            "text": "💬 Text",
            "image": "🖼 Image",
            "video": "🎬 Video",
            "voice": "🎤 Voice",
            "presentation": "📊 Presentation",
            "assistant": "🗓 Assistant",
            "settings": "⚙️ Settings",
            "limits": "📊 Limits",
            "support": "📨 Support",
            "new_dialog": "🔄 New Dialog"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = ReplyKeyboardBuilder()
    
    # Row 1: Text, Image
    builder.add(KeyboardButton(text=t["text"]))
    builder.add(KeyboardButton(text=t["image"]))
    
    # Row 2: Video, Voice
    builder.add(KeyboardButton(text=t["video"]))
    builder.add(KeyboardButton(text=t["voice"]))
    
    # Row 3: Presentation, Assistant
    builder.add(KeyboardButton(text=t["presentation"]))
    builder.add(KeyboardButton(text=t["assistant"]))
    
    # Row 4: Settings, Support
    builder.add(KeyboardButton(text=t["settings"]))
    builder.add(KeyboardButton(text=t["support"]))
    
    # Row 5: Limits, New Dialog
    builder.add(KeyboardButton(text=t["limits"]))
    builder.add(KeyboardButton(text=t["new_dialog"]))
    
    # Adjust layout: 2-2-2-2-2
    builder.adjust(2, 2, 2, 2, 2)
    
    return builder.as_markup(resize_keyboard=True)


def get_settings_keyboard(
    current_style: str = "vivid",
    auto_voice: bool = False,
    language: str = "ru",
    **kwargs  # Accept but ignore legacy params
) -> InlineKeyboardMarkup:
    """
    Get settings inline keyboard.
    Simplified - no model selection (fixed by TZ).
    """
    texts = {
        "ru": {
            "style": "🎨 Стиль изображений",
            "voice": "🎤 Авто-обработка голоса",
            "lang": "🌐 Язык",
            "timezone": "🕐 Часовой пояс",
            "subscription": "💳 Подписка",
            "back": "◀️ Назад"
        },
        "en": {
            "style": "🎨 Image Style",
            "voice": "🎤 Auto Voice Processing",
            "lang": "🌐 Language",
            "timezone": "🕐 Timezone",
            "subscription": "💳 Subscription",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    # Style display
    style_display = "Vivid" if current_style == "vivid" else "Natural"
    
    # Voice processing display
    voice_display = "✅" if auto_voice else "❌"
    
    # Language display
    lang_display = "🇷🇺 RU" if language == "ru" else "🇬🇧 EN"
    
    builder = InlineKeyboardBuilder()
    
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
            text=t["timezone"],
            callback_data="settings:timezone"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["subscription"],
            callback_data="settings:subscription"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["back"],
            callback_data="settings:back"
        )
    )
    
    return builder.as_markup()


def get_assistant_menu_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """
    Get assistant features menu keyboard.
    Includes: Diary, Reminders, Alarms.
    """
    texts = {
        "ru": {
            "diary": "📔 Ежедневник",
            "reminders": "🔔 Напоминания",
            "alarm": "⏰ Будильник",
            "back": "◀️ Назад"
        },
        "en": {
            "diary": "📔 Diary",
            "reminders": "🔔 Reminders",
            "alarm": "⏰ Alarm",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=t["diary"], callback_data="assistant:diary")
    )
    builder.row(
        InlineKeyboardButton(text=t["reminders"], callback_data="assistant:reminders")
    )
    builder.row(
        InlineKeyboardButton(text=t["alarm"], callback_data="assistant:alarm")
    )
    builder.row(
        InlineKeyboardButton(text=t["back"], callback_data="assistant:back")
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
