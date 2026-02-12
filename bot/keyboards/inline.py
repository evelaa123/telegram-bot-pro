"""
Inline keyboard layouts for various bot features.
"""
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_subscription_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """
    Get subscription prompt keyboard.
    """
    texts = {
        "ru": {
            "subscribe": "⭐ Оформить подписку",
            "close": "❌ Закрыть"
        },
        "en": {
            "subscribe": "⭐ Get Subscription",
            "close": "❌ Close"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t["subscribe"],
            callback_data="subscription:buy"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["close"],
            callback_data="subscription:close"
        )
    )
    
    return builder.as_markup()


def get_image_actions_keyboard(
    prompt: str = "",
    language: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Get image generation result actions keyboard.
    """
    texts = {
        "ru": {
            "regenerate": "🔄 Сгенерировать ещё",
            "edit": "✏️ Изменить промпт",
            "variation": "🎨 Вариация",
            "animate": "🎞 Оживить фото"
        },
        "en": {
            "regenerate": "🔄 Generate Again",
            "edit": "✏️ Edit Prompt",
            "variation": "🎨 Variation",
            "animate": "🎞 Animate Photo"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t["regenerate"],
            callback_data="image:regenerate"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["edit"],
            callback_data="image:edit"
        ),
        InlineKeyboardButton(
            text=t["variation"],
            callback_data="image:variation"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["animate"],
            callback_data="image:animate"
        )
    )
    
    return builder.as_markup()


def get_photo_actions_keyboard(
    file_id: str = None,  # deprecated, не используется
    language: str = "ru"
) -> InlineKeyboardMarkup:
    texts = {
        "ru": {"animate": "🎞 Оживить фото"},
        "en": {"animate": "🎞 Animate Photo"}
    }
    t = texts.get(language, texts["ru"])
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t["animate"],
            callback_data="photo:animate"
        )
    )
    return builder.as_markup()

def get_long_video_purchase_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """Keyboard for one-time long video purchase (not included in premium)."""
    texts = {
        "ru": {
            "buy_one": "💰 Купить разовую генерацию",
            "cancel": "❌ Отмена"
        },
        "en": {
            "buy_one": "💰 Buy one-time generation",
            "cancel": "❌ Cancel"
        }
    }
    t = texts.get(language, texts["ru"])
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t["buy_one"],
            callback_data="video:long:buy_one"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["cancel"],
            callback_data="video:cancel"
        )
    )
    return builder.as_markup()


def get_video_model_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """
    Get video model selection keyboard.
    CometAPI models:
    - sora-2: Fast mode (4/8/12 sec)
    - sora-2-pro: High quality (4/8/12 sec)
    """
    texts = {
        "ru": {
            "sora2": "⚡ Быстрый (sora-2)",
            "sora2_pro": "🎬 Качество (sora-2-pro)",
            "long_video": "🎥 Длинное видео (💰 Разовый платёж)",
            "cancel": "❌ Отмена"
        },
        "en": {
            "sora2": "⚡ Fast (sora-2)",
            "sora2_pro": "🎬 Quality (sora-2-pro)",
            "long_video": "🎥 Long Video (💰 One-time)",
            "cancel": "❌ Cancel"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t["sora2"],
            callback_data="video:model:sora-2"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["sora2_pro"],
            callback_data="video:model:sora-2-pro"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["long_video"],
            callback_data="video:long"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["cancel"],
            callback_data="video:cancel"
        )
    )
    
    return builder.as_markup()


def get_video_duration_keyboard(language: str = "ru", model: str = "sora-2") -> InlineKeyboardMarkup:
    """
    Get video duration selection keyboard.
    CometAPI durations: 4, 8, or 12 seconds for both models.
    """
    texts = {
        "ru": {
            "4s": "4 сек",
            "8s": "8 сек",
            "12s": "12 сек",
            "cancel": "❌ Отмена"
        },
        "en": {
            "4s": "4 sec",
            "8s": "8 sec",
            "12s": "12 sec",
            "cancel": "❌ Cancel"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=t["4s"], callback_data="video:duration:4"),
        InlineKeyboardButton(text=t["8s"], callback_data="video:duration:8"),
        InlineKeyboardButton(text=t["12s"], callback_data="video:duration:12")
    )
    builder.row(
        InlineKeyboardButton(text=t["cancel"], callback_data="video:cancel")
    )
    
    return builder.as_markup()




def get_video_actions_keyboard(
    video_id: str,
    language: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Get video generation result actions keyboard.
    NOTE: video_id is stored in Redis, not in callback_data (to avoid 64-byte limit)
    """
    texts = {
        "ru": {
            "regenerate": "🔄 Сгенерировать ещё",
            "remix": "🎨 Ремикс видео"
        },
        "en": {
            "regenerate": "🔄 Generate Again",
            "remix": "🎨 Remix Video"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t["regenerate"],
            callback_data="video:regenerate"
        ),
        InlineKeyboardButton(
            text=t["remix"],
            callback_data="video:remix"  # video_id stored separately in Redis
        )
    )
    
    return builder.as_markup()


def get_document_actions_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """
    Get document processing actions keyboard.
    """
    texts = {
        "ru": {
            "summarize": "📝 Суммаризировать",
            "question": "❓ Задать вопрос",
            "translate": "🌐 Перевести"
        },
        "en": {
            "summarize": "📝 Summarize",
            "question": "❓ Ask Question",
            "translate": "🌐 Translate"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t["summarize"],
            callback_data="document:summarize"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["question"],
            callback_data="document:question"
        ),
        InlineKeyboardButton(
            text=t["translate"],
            callback_data="document:translate"
        )
    )
    
    return builder.as_markup()


def get_gpt_model_keyboard(
    current_model: str = "gpt-4o-mini",
    language: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Get GPT model selection keyboard.
    """
    texts = {
        "ru": {
            "gpt4o": "🧠 GPT-4o (умнее)",
            "gpt4o_mini": "⚡ GPT-4o-mini (быстрее)",
            "back": "◀️ Назад"
        },
        "en": {
            "gpt4o": "🧠 GPT-4o (Smarter)",
            "gpt4o_mini": "⚡ GPT-4o-mini (Faster)",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    # Add checkmark to current model
    gpt4o_text = f"✓ {t['gpt4o']}" if current_model == "gpt-4o" else t["gpt4o"]
    gpt4o_mini_text = f"✓ {t['gpt4o_mini']}" if current_model == "gpt-4o-mini" else t["gpt4o_mini"]
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=gpt4o_text,
            callback_data="model:gpt-4o"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=gpt4o_mini_text,
            callback_data="model:gpt-4o-mini"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["back"],
            callback_data="settings:back_to_settings"
        )
    )
    
    return builder.as_markup()


def get_image_style_keyboard(
    current_style: str = "vivid",
    language: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Get image style selection keyboard.
    """
    texts = {
        "ru": {
            "vivid": "🎨 Vivid (яркий)",
            "natural": "🌿 Natural (естественный)",
            "back": "◀️ Назад"
        },
        "en": {
            "vivid": "🎨 Vivid (Dramatic)",
            "natural": "🌿 Natural (Realistic)",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    vivid_text = f"✓ {t['vivid']}" if current_style == "vivid" else t["vivid"]
    natural_text = f"✓ {t['natural']}" if current_style == "natural" else t["natural"]
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=vivid_text, callback_data="style:vivid")
    )
    builder.row(
        InlineKeyboardButton(text=natural_text, callback_data="style:natural")
    )
    builder.row(
        InlineKeyboardButton(text=t["back"], callback_data="settings:back_to_settings")
    )
    
    return builder.as_markup()


def get_image_size_keyboard(language: str = "ru") -> InlineKeyboardMarkup:
    """
    Get image size selection keyboard for DALL-E 3.
    """
    texts = {
        "ru": {
            "square": "◻️ Квадрат (1024x1024)",
            "horizontal": "▭ Горизонтальный (1792x1024)",
            "vertical": "▯ Вертикальный (1024x1792)",
            "cancel": "❌ Отмена"
        },
        "en": {
            "square": "◻️ Square (1024x1024)",
            "horizontal": "▭ Horizontal (1792x1024)",
            "vertical": "▯ Vertical (1024x1792)",
            "cancel": "❌ Cancel"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=t["square"],
            callback_data="image_size:1024x1024"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["horizontal"],
            callback_data="image_size:1792x1024"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["vertical"],
            callback_data="image_size:1024x1792"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["cancel"],
            callback_data="image:cancel"
        )
    )
    
    return builder.as_markup()


def get_language_keyboard(
    current_language: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Get language selection keyboard.
    """
    ru_text = "✓ 🇷🇺 Русский" if current_language == "ru" else "🇷🇺 Русский"
    en_text = "✓ 🇬🇧 English" if current_language == "en" else "🇬🇧 English"
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text=ru_text, callback_data="language:ru"),
        InlineKeyboardButton(text=en_text, callback_data="language:en")
    )
    builder.row(
        InlineKeyboardButton(
            text="◀️ Back" if current_language == "en" else "◀️ Назад",
            callback_data="settings:back_to_settings"
        )
    )
    
    return builder.as_markup()


def get_ai_provider_keyboard(
    current_provider: str = "openai",
    qwen_available: bool = True,
    language: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Get AI provider selection keyboard.
    
    Args:
        current_provider: Currently selected provider (openai or qwen)
        qwen_available: Whether Qwen API is configured and available
        language: UI language
    """
    texts = {
        "ru": {
            "openai": "🤖 OpenAI (GPT-4o)",
            "qwen": "🔮 Qwen (Alibaba)",
            "qwen_unavailable": "🔮 Qwen (не настроен)",
            "back": "◀️ Назад"
        },
        "en": {
            "openai": "🤖 OpenAI (GPT-4o)",
            "qwen": "🔮 Qwen (Alibaba)",
            "qwen_unavailable": "🔮 Qwen (not configured)",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    # Add checkmark to current provider
    openai_text = f"✓ {t['openai']}" if current_provider == "openai" else t["openai"]
    
    if qwen_available:
        qwen_text = f"✓ {t['qwen']}" if current_provider == "qwen" else t["qwen"]
    else:
        qwen_text = t["qwen_unavailable"]
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=openai_text,
            callback_data="provider:openai"
        )
    )
    
    # Only make Qwen button clickable if it's available
    if qwen_available:
        builder.row(
            InlineKeyboardButton(
                text=qwen_text,
                callback_data="provider:qwen"
            )
        )
    else:
        builder.row(
            InlineKeyboardButton(
                text=qwen_text,
                callback_data="provider:qwen_unavailable"
            )
        )
    
    builder.row(
        InlineKeyboardButton(
            text=t["back"],
            callback_data="settings:back_to_settings"
        )
    )
    
    return builder.as_markup()


def get_qwen_model_keyboard(
    current_model: str = "qwen-plus",
    language: str = "ru"
) -> InlineKeyboardMarkup:
    """
    Get Qwen model selection keyboard.
    """
    texts = {
        "ru": {
            "qwen_turbo": "⚡ Qwen Turbo (быстрый)",
            "qwen_plus": "🎯 Qwen Plus (баланс)",
            "qwen_max": "🧠 Qwen Max (умнее)",
            "back": "◀️ Назад"
        },
        "en": {
            "qwen_turbo": "⚡ Qwen Turbo (Fast)",
            "qwen_plus": "🎯 Qwen Plus (Balanced)",
            "qwen_max": "🧠 Qwen Max (Smarter)",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    
    # Add checkmark to current model
    turbo_text = f"✓ {t['qwen_turbo']}" if current_model == "qwen-turbo" else t["qwen_turbo"]
    plus_text = f"✓ {t['qwen_plus']}" if current_model == "qwen-plus" else t["qwen_plus"]
    max_text = f"✓ {t['qwen_max']}" if current_model == "qwen-max" else t["qwen_max"]
    
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=turbo_text,
            callback_data="qwen_model:qwen-turbo"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=plus_text,
            callback_data="qwen_model:qwen-plus"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=max_text,
            callback_data="qwen_model:qwen-max"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text=t["back"],
            callback_data="settings:back_to_settings"
        )
    )
    
    return builder.as_markup()


def get_pagination_keyboard(
    current_page: int,
    total_pages: int,
    callback_prefix: str
) -> InlineKeyboardMarkup:
    """
    Get pagination keyboard.
    """
    builder = InlineKeyboardBuilder()
    
    buttons = []
    
    if current_page > 1:
        buttons.append(
            InlineKeyboardButton(
                text="◀️",
                callback_data=f"{callback_prefix}:page:{current_page - 1}"
            )
        )
    
    buttons.append(
        InlineKeyboardButton(
            text=f"{current_page}/{total_pages}",
            callback_data="noop"
        )
    )
    
    if current_page < total_pages:
        buttons.append(
            InlineKeyboardButton(
                text="▶️",
                callback_data=f"{callback_prefix}:page:{current_page + 1}"
            )
        )
    
    builder.row(*buttons)
    
    return builder.as_markup()
