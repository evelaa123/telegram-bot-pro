"""
Channel comments & group handler.
Handles bot mentions, commands, and all content types in groups/channels.
Supports: text, photos, voice, audio, documents — full functionality with reply_to.
Features: cached bot_info, streaming text, inline image buttons, group context, presentations.
"""
import re
import asyncio
import time
from typing import Tuple, Optional
from aiogram import Router, F, Bot
from aiogram.types import Message, BufferedInputFile, CallbackQuery, User as TgUser
from aiogram.enums import ChatType, ChatAction
from aiogram.filters import Command

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.services.subscription_service import subscription_service
from bot.services.settings_service import settings_service
from bot.keyboards.inline import get_subscription_keyboard, get_image_size_keyboard
from config import settings as config_settings
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
import structlog

logger = structlog.get_logger()
router = Router()

# ============================================
# CACHED BOT INFO HELPER
# ============================================

async def _get_bot_username(bot: Bot, data: dict = None) -> str:
    """Get bot username from cached data or fallback to API call."""
    # Try cached bot_info from middleware / dispatcher
    if data and 'bot_info' in data:
        return data['bot_info'].username or ""
    # Fallback: call API (should rarely happen)
    info = await bot.get_me()
    return info.username or ""


async def _get_bot_id(bot: Bot, data: dict = None) -> int:
    """Get bot user id from cached data or fallback to API call."""
    if data and 'bot_info' in data:
        return data['bot_info'].id
    info = await bot.get_me()
    return info.id

# ============================================
# KEYWORDS
# ============================================

IMAGE_KEYWORDS = [
    "сгенерируй", "нарисуй", "создай картинку", "создай изображение",
    "сделай картинку", "сделай изображение", "покажи как выглядит",
    "визуализируй", "изобрази", "нарисуй мне", "сгенери",
    "generate", "draw", "create image", "make picture", "visualize",
    "покажи", "пикчу", "арт", "картинку"
]

ANALYZE_KEYWORDS = [
    "что это", "что здесь", "опиши", "проанализируй", "анализ",
    "что на фото", "что на картинке", "что изображено", "распознай",
    "what is this", "what's this", "describe", "analyze", "what do you see"
]

TEXT_KEYWORDS = [
    "расскажи", "объясни", "что такое", "как", "почему", "зачем",
    "ответь", "помоги", "подскажи", "напиши", "скажи",
    "tell", "explain", "what is", "how", "why", "help"
]

BOT_TRIGGERS = [
    "бот", "bot", "ии", "ai", "гпт", "gpt", "ассистент", "assistant"
]


# ============================================
# HELPER FUNCTIONS
# ============================================

def is_bot_triggered(text: str, bot_username: str) -> bool:
    """Check if message is addressed to bot."""
    if not text:
        return False

    text_lower = text.lower().strip()

    # @username mention
    if bot_username and f"@{bot_username.lower()}" in text_lower:
        return True

    # Trigger words
    for trigger in BOT_TRIGGERS:
        if text_lower.startswith(trigger):
            return True
        if text_lower.startswith(f"{trigger},"):
            return True
        if text_lower.startswith(f"{trigger} "):
            return True
        if f" {trigger}" in text_lower or f",{trigger}" in text_lower:
            return True

    return False


def _is_command(text: str) -> bool:
    """Check if text is a bot command like /start@botname."""
    return bool(text) and text.strip().startswith("/")


def get_intent_and_prompt(text: str, bot_username: str, has_photo: bool = False) -> Tuple[str, str]:
    """Determine intent and extract clean prompt."""
    if not text:
        return ('analyze' if has_photo else 'auto', '')

    text_lower = text.lower()

    # Clean triggers from text
    cleaned = text
    all_triggers = BOT_TRIGGERS.copy()
    if bot_username:
        all_triggers.append(f"@{bot_username.lower()}")
        all_triggers.append(bot_username.lower())

    for trigger in all_triggers:
        cleaned = re.sub(rf'^{re.escape(trigger)}[,\s]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(rf'[,\s]*{re.escape(trigger)}[,\s]*', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()

    if has_photo:
        for kw in IMAGE_KEYWORDS:
            if kw in text_lower:
                prompt = re.sub(rf'\b{re.escape(kw)}\b', '', cleaned, flags=re.IGNORECASE).strip()
                prompt = re.sub(r'^[,.\s]+', '', prompt).strip()
                return 'image', prompt if prompt else cleaned
        return 'analyze', cleaned if cleaned else "Опиши что на изображении"

    for kw in IMAGE_KEYWORDS:
        if kw in text_lower:
            prompt = re.sub(rf'\b{re.escape(kw)}\b', '', cleaned, flags=re.IGNORECASE).strip()
            prompt = re.sub(r'^[,.\s]+', '', prompt).strip()
            return 'image', prompt if prompt else cleaned

    for kw in TEXT_KEYWORDS:
        if kw in text_lower:
            return 'text', cleaned

    return 'auto', cleaned


async def send_reply(
    message: Message,
    text: str,
    photo: BufferedInputFile = None,
    parse_mode: str = None,
    reply_markup=None,
):
    """
    Send message as reply in groups (for visibility in channel comments).
    In private chats, send normally.
    Falls back to no parse_mode if Telegram can't parse entities.
    """
    from aiogram.exceptions import TelegramBadRequest

    is_group = message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)
    thread_id = message.message_thread_id if is_group else None
    reply_to = message.message_id if is_group else None

    kwargs = {
        "chat_id": message.chat.id,
        "reply_to_message_id": reply_to,
        "message_thread_id": thread_id,
    }
    if parse_mode:
        kwargs["parse_mode"] = parse_mode
    if reply_markup:
        kwargs["reply_markup"] = reply_markup

    try:
        if photo:
            kwargs["photo"] = photo
            kwargs["caption"] = text
            return await message.bot.send_photo(**kwargs)
        else:
            kwargs["text"] = text
            return await message.bot.send_message(**kwargs)
    except TelegramBadRequest as e:
        if "can't parse entities" in str(e):
            # Explicitly disable parse_mode (overrides bot default)
            kwargs["parse_mode"] = None
            logger.warning(
                "Parse entities failed, retrying without parse_mode",
                error=str(e),
                text_preview=text[:50]
            )
            if photo:
                return await message.bot.send_photo(**kwargs)
            else:
                return await message.bot.send_message(**kwargs)
        raise


async def _check_user_access(message: Message, bot: Bot) -> tuple:
    """
    Common access checks for group handlers.
    Returns (db_user, language) or raises early return via None.
    """
    user = message.from_user
    if not user:
        return None, None

    # Register user
    db_user = await user_service.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code
    )

    language = db_user.settings.get('language', 'ru') if db_user.settings else 'ru'

    # Block check
    if db_user.is_blocked:
        await send_reply(message, "🚫 Ваш аккаунт заблокирован.")
        return None, None

    # Channel subscription check
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
                is_subscribed = await subscription_service.check_channel_subscription(
                    bot, user.id, channel_id
                )
                if not is_subscribed:
                    if language == 'ru':
                        text_msg = f"🔒 Подпишись на канал {channel_username} чтобы использовать бота"
                    else:
                        text_msg = f"🔒 Subscribe to {channel_username} to use the bot"
                    await send_reply(message, text_msg)
                    return None, None
    except Exception as e:
        logger.error(f"Subscription check error: {e}")

    return db_user, language


def _strip_command(text: str) -> str:
    """Strip /command@botname from text, return remaining args."""
    if not text:
        return ""
    parts = text.strip().split(maxsplit=1)
    return parts[1] if len(parts) > 1 else ""


# ============================================
# COMMAND HANDLERS FOR GROUPS
# ============================================

@router.message(
    Command("start"),
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
)
async def group_cmd_start(message: Message, bot: Bot):
    """Handle /start in groups."""
    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    user = message.from_user
    if language == "ru":
        welcome_text = (
            f"👋 Привет, <b>{user.first_name}</b>!\n\n"
            "Я — ИИ-ассистент. Упомяни меня или ответь на моё сообщение:\n\n"
            "💬 <b>Текст</b> — отвечаю на вопросы\n"
            "🖼 <b>Изображения</b> — генерирую картинки (скажи «нарисуй ...»)\n"
            "🎤 <b>Голос</b> — распознаю голосовые (ответь на голосовое)\n"
            "📄 <b>Документы</b> — анализирую файлы (ответь на документ)\n"
            "📸 <b>Фото</b> — анализирую изображения\n\n"
            "Команды: /help /limits /image /new"
        )
    else:
        welcome_text = (
            f"👋 Hello, <b>{user.first_name}</b>!\n\n"
            "I'm an AI assistant. Mention me or reply to my message:\n\n"
            "💬 <b>Text</b> — answering questions\n"
            "🖼 <b>Images</b> — generating pictures (say «draw ...»)\n"
            "🎤 <b>Voice</b> — transcribing voice messages\n"
            "📄 <b>Documents</b> — analyzing files\n"
            "📸 <b>Photos</b> — analyzing images\n\n"
            "Commands: /help /limits /image /new"
        )

    await send_reply(message, welcome_text, parse_mode="HTML")


@router.message(
    Command("help"),
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
)
async def group_cmd_help(message: Message, bot: Bot):
    """Handle /help in groups."""
    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    if language == "ru":
        help_text = (
            "📚 <b>Справка по использованию бота в группе</b>\n\n"
            "<b>Как обратиться к боту:</b>\n"
            "• Упомяните @бот в сообщении\n"
            "• Ответьте (reply) на сообщение бота\n"
            "• Напишите «бот, ...» или «ai, ...»\n\n"
            "<b>Возможности:</b>\n"
            "💬 Текстовые запросы — просто задайте вопрос\n"
            "🖼 Генерация картинок — «нарисуй ...», «сгенерируй ...»\n"
            "📸 Анализ фото — отправьте фото с упоминанием бота\n"
            "🎤 Голос — ответьте на голосовое с упоминанием бота\n"
            "📄 Документы — ответьте на файл с упоминанием бота\n\n"
            "<b>Команды:</b>\n"
            "/limits — ваши лимиты\n"
            "/image — генерация изображения\n"
            "/new — сбросить контекст\n"
        )
    else:
        help_text = (
            "📚 <b>Bot Usage Guide (Group)</b>\n\n"
            "<b>How to call the bot:</b>\n"
            "• Mention @bot in your message\n"
            "• Reply to a bot message\n"
            "• Write «bot, ...» or «ai, ...»\n\n"
            "<b>Capabilities:</b>\n"
            "💬 Text requests — just ask a question\n"
            "🖼 Image generation — «draw ...», «generate ...»\n"
            "📸 Photo analysis — send photo with bot mention\n"
            "🎤 Voice — reply to voice message with bot mention\n"
            "📄 Documents — reply to file with bot mention\n\n"
            "<b>Commands:</b>\n"
            "/limits — your limits\n"
            "/image — generate image\n"
            "/new — reset context\n"
        )

    await send_reply(message, help_text, parse_mode="HTML")


@router.message(
    Command("limits"),
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
)
async def group_cmd_limits(message: Message, bot: Bot):
    """Handle /limits in groups."""
    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    limits_text = await limit_service.get_limits_text(message.from_user.id, language)
    await send_reply(message, limits_text, parse_mode="HTML")


@router.message(
    Command("new"),
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
)
async def group_cmd_new(message: Message, bot: Bot, **data):
    """Handle /new in groups — clear context."""
    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    user_id = message.from_user.id
    chat_id = message.chat.id
    await redis_client.clear_context(user_id)
    await redis_client.clear_document_context(user_id)
    await redis_client.clear_user_state(user_id)
    # Clear group-specific context
    await redis_client.delete(f"group_ctx:{chat_id}:{user_id}")

    if language == "ru":
        text = "🔄 Контекст очищен. Можете задать новый вопрос."
    else:
        text = "🔄 Context cleared. You can ask a new question."

    await send_reply(message, text)


@router.message(
    Command("image"),
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
)
async def group_cmd_image(message: Message, bot: Bot, **data):
    """Handle /image in groups — inline buttons for size selection or direct generation."""
    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    user_id = message.from_user.id
    prompt = _strip_command(message.text or "")

    if prompt and len(prompt.strip()) >= 3:
        # Prompt supplied inline — store and show size picker
        chat_id = message.chat.id
        key = f"group_image:{chat_id}:{user_id}"
        await redis_client.set(key, prompt, ttl=600)  # 10 min TTL

        if language == "ru":
            text = (
                f"🖼 <b>Генерация изображения</b>\n\n"
                f"📝 Промпт: <i>{prompt[:200]}</i>\n\n"
                "Выберите размер:"
            )
        else:
            text = (
                f"🖼 <b>Image Generation</b>\n\n"
                f"📝 Prompt: <i>{prompt[:200]}</i>\n\n"
                "Choose size:"
            )
        await send_reply(message, text, parse_mode="HTML",
                        reply_markup=_get_group_image_size_keyboard(language))
    else:
        # No prompt — ask the user to provide one, save state
        chat_id = message.chat.id
        key = f"group_image_wait:{chat_id}:{user_id}"
        await redis_client.set(key, "1", ttl=300)

        if language == "ru":
            await send_reply(
                message,
                "🖼 Напишите описание картинки в ответ на это сообщение.\n\n"
                "<i>Например: кот в космосе</i>",
                parse_mode="HTML",
            )
        else:
            await send_reply(
                message,
                "🖼 Reply to this message with an image description.\n\n"
                "<i>Example: cat in space</i>",
                parse_mode="HTML",
            )


@router.message(
    Command("presentation"),
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
)
async def group_cmd_presentation(message: Message, bot: Bot, **data):
    """Handle /presentation <topic> in groups."""
    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    user_id = message.from_user.id
    topic = _strip_command(message.text or "")

    if not topic or len(topic.strip()) < 3:
        if language == "ru":
            await send_reply(
                message,
                "📊 Используйте: /presentation [тема]\n\n"
                "Например: /presentation Искусственный интеллект в бизнесе"
            )
        else:
            await send_reply(
                message,
                "📊 Usage: /presentation [topic]\n\n"
                "Example: /presentation AI in business"
            )
        return

    await generate_presentation_response(message, user_id, topic, language)



# ============================================
# INLINE BUTTON CALLBACKS FOR GROUPS
# ============================================

def _get_group_image_size_keyboard(language: str = "ru"):
    """Inline keyboard for image size in groups."""
    from aiogram.types import InlineKeyboardButton
    from aiogram.utils.keyboard import InlineKeyboardBuilder

    texts = {
        "ru": {
            "square": "◻️ Квадрат (1024x1024)",
            "horizontal": "▭ Горизонтальный (1792x1024)",
            "vertical": "▯ Вертикальный (1024x1792)",
            "cancel": "❌ Отмена",
        },
        "en": {
            "square": "◻️ Square (1024x1024)",
            "horizontal": "▭ Horizontal (1792x1024)",
            "vertical": "▯ Vertical (1024x1792)",
            "cancel": "❌ Cancel",
        },
    }
    t = texts.get(language, texts["ru"])
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text=t["square"], callback_data="grp_img:1024x1024"))
    builder.row(InlineKeyboardButton(text=t["horizontal"], callback_data="grp_img:1792x1024"))
    builder.row(InlineKeyboardButton(text=t["vertical"], callback_data="grp_img:1024x1792"))
    builder.row(InlineKeyboardButton(text=t["cancel"], callback_data="grp_img:cancel"))
    return builder.as_markup()


@router.callback_query(F.data.startswith("grp_img:"))
async def callback_group_image_size(callback: CallbackQuery, bot: Bot, **data):
    """Handle image size selection in groups."""
    user = callback.from_user
    if not user:
        await callback.answer()
        return

    action = callback.data.split(":")[1]

    if action == "cancel":
        chat_id = callback.message.chat.id
        key = f"group_image:{chat_id}:{user.id}"
        await redis_client.delete(key)
        language = await user_service.get_user_language(user.id)
        cancel_text = "❌ Генерация отменена." if language == "ru" else "❌ Generation cancelled."
        try:
            await callback.message.edit_text(cancel_text)
        except Exception:
            pass
        await callback.answer()
        return

    size = action  # e.g. "1024x1024"
    chat_id = callback.message.chat.id
    key = f"group_image:{chat_id}:{user.id}"
    prompt = await redis_client.get(key)

    if not prompt:
        language = await user_service.get_user_language(user.id)
        no_prompt = "❌ Промпт не найден. Повторите /image" if language == "ru" else "❌ Prompt not found. Try /image again"
        await callback.answer(no_prompt, show_alert=True)
        return

    await redis_client.delete(key)
    language = await user_service.get_user_language(user.id)

    # Acknowledge
    try:
        await callback.message.edit_text("🎨 Рисую..." if language == "ru" else "🎨 Drawing...")
    except Exception:
        pass
    await callback.answer()

    # Generate
    await generate_image_response(callback.message, user.id, prompt, language, size=size)


# ============================================
# VOICE HANDLER FOR GROUPS
# ============================================

@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.voice,
)
async def handle_group_voice(message: Message, bot: Bot, **data):
    """Handle voice messages in groups — transcribe when bot is triggered."""
    bot_username = await _get_bot_username(bot, data)
    bot_id = await _get_bot_id(bot, data)

    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_id
    )

    # For voice, also check if user replies to a voice message WITH bot mention
    caption = message.caption or ""
    is_mention = is_bot_triggered(caption, bot_username)

    if not is_reply_to_bot and not is_mention:
        return

    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    await transcribe_voice_response(message, message.from_user.id, language)


@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.audio,
)
async def handle_group_audio(message: Message, bot: Bot, **data):
    """Handle audio files in groups — transcribe when bot is triggered."""
    bot_username = await _get_bot_username(bot, data)
    bot_id = await _get_bot_id(bot, data)

    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_id
    )

    caption = message.caption or ""
    is_mention = is_bot_triggered(caption, bot_username)

    if not is_reply_to_bot and not is_mention:
        return

    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    await transcribe_audio_response(message, message.from_user.id, language)


# ============================================
# DOCUMENT HANDLER FOR GROUPS
# ============================================

@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.document,
)
async def handle_group_document(message: Message, bot: Bot, **data):
    """Handle documents in groups — analyze when bot is triggered."""
    bot_username = await _get_bot_username(bot, data)
    bot_id = await _get_bot_id(bot, data)

    caption = message.caption or ""
    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_id
    )
    is_mention = is_bot_triggered(caption, bot_username)

    if not is_reply_to_bot and not is_mention:
        return

    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    await analyze_document_response(message, message.from_user.id, caption, language)


# ============================================
# MAIN TEXT + PHOTO HANDLER FOR GROUPS
# ============================================

@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.text | F.photo,
)
async def handle_group_message(message: Message, bot: Bot, **data):
    """Handle text and photo messages in groups/supergroups."""

    user = message.from_user
    if not user:
        return

    text = message.text or message.caption or ""
    has_photo = bool(message.photo)

    # Skip commands — they are handled above
    if _is_command(text):
        return

    bot_username = await _get_bot_username(bot, data)
    bot_id = await _get_bot_id(bot, data)

    # Check trigger
    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_id
    )
    is_mention = is_bot_triggered(text, bot_username)

    # If user replies to a message that contains a voice/doc and mentions bot
    # This handles: user replies to someone else's voice msg with "@bot transcribe this"
    if not is_mention and not is_reply_to_bot:
        return

    # Access checks
    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    logger.info(
        "Bot triggered in group",
        user_id=user.id,
        username=user.username,
        chat_id=message.chat.id,
        thread_id=message.message_thread_id,
        has_photo=has_photo,
        is_reply_to_bot=is_reply_to_bot,
        text=text[:50] if text else "(no text)"
    )

    # ---- Check if user is replying with prompt for /image (inline-button flow) ----
    chat_id = message.chat.id
    wait_key = f"group_image_wait:{chat_id}:{user.id}"
    if await redis_client.get(wait_key):
        await redis_client.delete(wait_key)
        prompt_text = text.strip()
        if prompt_text and len(prompt_text) >= 3:
            # Store prompt and show size keyboard
            key = f"group_image:{chat_id}:{user.id}"
            await redis_client.set(key, prompt_text, ttl=600)
            if language == "ru":
                t = f"🖼 <b>Промпт:</b> <i>{prompt_text[:200]}</i>\n\nВыберите размер:"
            else:
                t = f"🖼 <b>Prompt:</b> <i>{prompt_text[:200]}</i>\n\nChoose size:"
            await send_reply(message, t, parse_mode="HTML",
                            reply_markup=_get_group_image_size_keyboard(language))
            return

    # Determine intent
    intent, prompt = get_intent_and_prompt(text, bot_username, has_photo)

    # Context from reply (if replying to a user message, not bot)
    if not has_photo and message.reply_to_message and not is_reply_to_bot:
        reply_msg = message.reply_to_message

        # Check if reply target has voice — user wants transcription
        if reply_msg.voice:
            await transcribe_voice_response(message, user.id, language, voice_message=reply_msg)
            return

        # Check if reply target has audio
        if reply_msg.audio:
            await transcribe_audio_response(message, user.id, language, audio_message=reply_msg)
            return

        # Check if reply target has document
        if reply_msg.document:
            await analyze_document_response(message, user.id, prompt, language, doc_message=reply_msg)
            return

        # Check if reply target has photo — analyze it
        if reply_msg.photo:
            analyze_prompt = prompt if prompt else "Опиши что на изображении"
            await analyze_photo_response(message, user.id, analyze_prompt, language, photo_message=reply_msg)
            return

        # Text context from reply
        if reply_msg.from_user and not reply_msg.from_user.is_bot:
            reply_text = reply_msg.text or reply_msg.caption or ""
            if reply_text and len(reply_text) < 500:
                prompt = f"Контекст: {reply_text}\n\nЗапрос: {prompt}"

    # Process by intent
    if has_photo:
        if intent == 'image':
            await generate_image_response(message, user.id, prompt, language)
        else:
            await analyze_photo_response(message, user.id, prompt or "Опиши что на изображении", language)
    elif intent == 'image':
        await generate_image_response(message, user.id, prompt, language)
    elif intent == 'text':
        await generate_text_response(message, user.id, prompt, language)
    elif prompt and len(prompt.strip()) >= 2:
        await auto_detect_and_respond(message, user.id, prompt, language)
    else:
        await send_reply(message, "🤔 Что именно сделать? Напиши подробнее!")


# ============================================
# RESPONSE GENERATORS
# ============================================

async def analyze_photo_response(
    message: Message, user_id: int, prompt: str, language: str,
    photo_message: Message = None
):
    """Analyze photo with GPT-4 Vision."""
    source_msg = photo_message or message

    has_limit, current, max_limit = await limit_service.check_limit(user_id, RequestType.DOCUMENT)
    if not has_limit:
        await send_reply(
            message,
            f"⚠️ Лимит анализа исчерпан ({current}/{max_limit})" if language == "ru"
            else f"⚠️ Analysis limit reached ({current}/{max_limit})",
            reply_markup=get_subscription_keyboard(language),
        )
        return

    if not source_msg.photo:
        await send_reply(message, "🤔 Не вижу фото для анализа")
        return

    status_msg = await send_reply(message, "🔍 Анализирую изображение...")

    try:
        photo = source_msg.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        file_data = await message.bot.download_file(file.file_path)
        image_bytes = file_data.read() if hasattr(file_data, 'read') else file_data

        if language == 'ru':
            full_prompt = f"{prompt}\n\nОтвечай на русском языке."
        else:
            full_prompt = prompt

        result, usage = await ai_service.analyze_image(
            image_data=image_bytes,
            prompt=full_prompt,
            telegram_id=user_id
        )

        if len(result) > 4000:
            result = result[:4000] + "..."

        try:
            await status_msg.delete()
        except Exception:
            pass

        await send_reply(message, f"🔍 {result}")

        await limit_service.increment_usage(user_id, RequestType.DOCUMENT)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.DOCUMENT,
            prompt=prompt[:500],
            response_preview=result[:500],
            model="gpt-4o",
            status=RequestStatus.SUCCESS,
            cost_usd=float(usage.get("cost_usd", 0))
        )

    except Exception as e:
        logger.error("Photo analysis error", error=str(e), exc_info=True)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await send_reply(message, f"❌ Ошибка анализа: {str(e)[:100]}")

        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.DOCUMENT,
            prompt=prompt[:500],
            model="gpt-4o",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )


async def generate_image_response(
    message: Message, user_id: int, prompt: str, language: str, size: str = "1024x1024"
):
    """Generate image."""
    has_limit, current, max_limit = await limit_service.check_limit(user_id, RequestType.IMAGE)
    if not has_limit:
        await send_reply(
            message,
            f"⚠️ Лимит картинок исчерпан ({current}/{max_limit})" if language == "ru"
            else f"⚠️ Image limit reached ({current}/{max_limit})",
            reply_markup=get_subscription_keyboard(language),
        )
        return

    if not prompt or len(prompt.strip()) < 3:
        await send_reply(message, "🤔 Опиши что нарисовать!" if language == "ru" else "🤔 Describe what to draw!")
        return

    status_msg = await send_reply(message, "🎨 Рисую..." if language == "ru" else "🎨 Drawing...")

    try:
        image_url, usage = await ai_service.generate_image(
            prompt=prompt,
            size=size,
            telegram_id=user_id
        )

        image_bytes = await ai_service.download_image(image_url)
        photo = BufferedInputFile(image_bytes, filename="image.png")

        caption = usage.get("revised_prompt", prompt)
        if len(caption) > 900:
            caption = caption[:900] + "..."

        try:
            await status_msg.delete()
        except Exception:
            pass

        await send_reply(message, f"🖼 {caption}", photo=photo)

        await limit_service.increment_usage(user_id, RequestType.IMAGE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500],
            model="dall-e-3",
            status=RequestStatus.SUCCESS,
            cost_usd=float(usage.get("cost_usd", 0))
        )

    except Exception as e:
        logger.error("Image error", error=str(e))
        try:
            await status_msg.delete()
        except Exception:
            pass
        await send_reply(message, f"❌ Ошибка: {str(e)[:100]}")

        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500],
            model="dall-e-3",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )


def _convert_markdown_to_html(text: str) -> str:
    """Convert Markdown to Telegram HTML (same as text.py)."""
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = re.sub(r'```(\w*)\n?(.*?)```', r'<pre>\2</pre>', text, flags=re.DOTALL)
    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    text = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__([^_]+?)__', r'<b>\1</b>', text)
    text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<i>\1</i>', text)
    text = re.sub(r'(?<!_)_([^_\n]+?)_(?!_)', r'<i>\1</i>', text)
    text = re.sub(r'~~([^~]+?)~~', r'<s>\1</s>', text)
    return text


async def _get_group_context(chat_id: int, user_id: int):
    """Get per-user conversation context for a specific group."""
    import json
    key = f"group_ctx:{chat_id}:{user_id}"
    value = await redis_client.get(key)
    if value is None:
        return []
    return json.loads(value)


async def _add_to_group_context(
    chat_id: int, user_id: int, role: str, content: str, max_messages: int = 10
):
    """Add to per-user group conversation context."""
    import json
    key = f"group_ctx:{chat_id}:{user_id}"
    ctx = await _get_group_context(chat_id, user_id)
    ctx.append({"role": role, "content": content})
    if len(ctx) > max_messages:
        ctx = ctx[-max_messages:]
    await redis_client.set(key, json.dumps(ctx, ensure_ascii=False), ttl=1800)  # 30 min


async def generate_text_response(message: Message, user_id: int, prompt: str, language: str):
    """Generate text response with streaming in groups."""
    has_limit, current, max_limit = await limit_service.check_limit(user_id, RequestType.TEXT)
    if not has_limit:
        await send_reply(
            message,
            f"⚠️ Лимит запросов исчерпан ({current}/{max_limit})\n\n"
            "💎 Оформите подписку для увеличения лимитов!" if language == "ru"
            else f"⚠️ Request limit reached ({current}/{max_limit})\n\n"
            "💎 Subscribe to increase your limits!",
            reply_markup=get_subscription_keyboard(language),
        )
        return

    start_time = time.time()

    try:
        # Build context with per-user group history
        chat_id = message.chat.id
        context = await _get_group_context(chat_id, user_id)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful assistant in a group chat. Be concise (2-3 paragraphs max). "
                    f"Respond in {'Russian' if language == 'ru' else 'English'}. "
                    "Use markdown formatting when appropriate."
                ),
            },
        ]
        messages.extend(context)
        messages.append({"role": "user", "content": prompt})

        # Send initial "thinking" message
        thinking_msg = await send_reply(
            message,
            "💭 Думаю..." if language == "ru" else "💭 Thinking...",
        )

        # Stream the response
        full_response = ""
        last_update_time = time.time()
        token_count = 0

        # Group rate-limit: don't update faster than every 1s to avoid 429
        GROUP_UPDATE_INTERVAL_MS = 1000

        model = config_settings.default_text_model

        async for chunk, is_complete in ai_service.generate_text_stream(
            messages=messages,
            telegram_id=user_id,
            model=model,
        ):
            full_response += chunk
            token_count += 1

            current_time = time.time()
            time_since_update = (current_time - last_update_time) * 1000

            should_update = (
                token_count >= config_settings.stream_token_batch_size
                or time_since_update >= GROUP_UPDATE_INTERVAL_MS
                or is_complete
            )

            if should_update and full_response.strip():
                try:
                    display_text = full_response
                    if len(display_text) > 4000:
                        display_text = display_text[:4000] + "..."

                    html_text = _convert_markdown_to_html(display_text)

                    try:
                        await thinking_msg.edit_text(html_text, parse_mode="HTML")
                    except Exception:
                        await thinking_msg.edit_text(display_text)

                    last_update_time = current_time
                    token_count = 0

                    if not is_complete:
                        await asyncio.sleep(0.1)  # respect rate limits

                except Exception as e:
                    if "message is not modified" not in str(e).lower():
                        logger.warning("Stream edit fail", error=str(e))

        # Final update
        if full_response.strip():
            try:
                display_text = full_response
                if len(display_text) > 4000:
                    display_text = display_text[:4000] + "\n\n... (ответ обрезан)"
                html_text = _convert_markdown_to_html(display_text)
                try:
                    await thinking_msg.edit_text(html_text, parse_mode="HTML")
                except Exception:
                    await thinking_msg.edit_text(display_text)
            except Exception:
                pass

        duration_ms = int((time.time() - start_time) * 1000)

        # Save to group context
        await _add_to_group_context(chat_id, user_id, "user", prompt)
        await _add_to_group_context(chat_id, user_id, "assistant", full_response)

        await limit_service.increment_usage(user_id, RequestType.TEXT)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.TEXT,
            prompt=prompt[:500],
            response_preview=full_response[:500],
            model=model,
            status=RequestStatus.SUCCESS,
            cost_usd=0,
            duration_ms=duration_ms,
        )

    except Exception as e:
        logger.error("Text error in group", error=str(e))
        duration_ms = int((time.time() - start_time) * 1000)
        await send_reply(message, f"❌ Ошибка: {str(e)[:100]}")

        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.TEXT,
            prompt=prompt[:500],
            model=config_settings.default_text_model,
            status=RequestStatus.FAILED,
            error_message=str(e),
            duration_ms=duration_ms,
        )


async def transcribe_voice_response(
    message: Message, user_id: int, language: str,
    voice_message: Message = None
):
    """Transcribe voice message in group."""
    source_msg = voice_message or message
    voice = source_msg.voice

    if not voice:
        await send_reply(message, "🤔 Не вижу голосового сообщения")
        return

    has_limit, current, max_limit = await limit_service.check_limit(user_id, RequestType.VOICE)
    if not has_limit:
        await send_reply(
            message,
            f"⚠️ Лимит распознавания голоса исчерпан ({current}/{max_limit})" if language == "ru"
            else f"⚠️ Voice recognition limit reached ({current}/{max_limit})",
            reply_markup=get_subscription_keyboard(language),
        )
        return

    if voice.file_size and voice.file_size > 25 * 1024 * 1024:
        await send_reply(message, "⚠️ Голосовое слишком большое (макс 25 МБ)")
        return

    status_msg = await send_reply(message, "🎤 Распознаю речь..." if language == "ru" else "🎤 Transcribing...")

    try:
        file = await message.bot.get_file(voice.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        audio_data = file_bytes.read() if hasattr(file_bytes, 'read') else file_bytes

        text, usage = await ai_service.transcribe_audio(
            audio_data=audio_data,
            filename="voice.ogg",
            language=language if language in ["ru", "en", "zh"] else None,
            telegram_id=user_id
        )

        if not text or not text.strip():
            try:
                await status_msg.edit_text("🤔 Не удалось распознать речь." if language == "ru" else "🤔 Could not recognize speech.")
            except Exception:
                pass
            return

        if language == "ru":
            result_text = f"📝 <b>Распознанный текст:</b>\n\n{text}"
        else:
            result_text = f"📝 <b>Transcribed text:</b>\n\n{text}"

        if len(result_text) > 4000:
            result_text = result_text[:4000] + "..."

        try:
            await status_msg.edit_text(result_text, parse_mode="HTML")
        except Exception:
            try:
                await status_msg.delete()
            except Exception:
                pass
            await send_reply(message, result_text, parse_mode="HTML")

        await limit_service.increment_usage(user_id, RequestType.VOICE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.VOICE,
            response_preview=text[:500],
            model=usage.get("model", "whisper-1"),
            cost_usd=float(usage.get("cost_usd", 0)),
            status=RequestStatus.SUCCESS
        )

    except Exception as e:
        logger.error("Voice transcription error in group", error=str(e))
        try:
            await status_msg.edit_text(f"❌ Ошибка распознавания: {str(e)[:100]}")
        except Exception:
            pass

        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.VOICE,
            model="whisper-1",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )


async def transcribe_audio_response(
    message: Message, user_id: int, language: str,
    audio_message: Message = None
):
    """Transcribe audio file in group."""
    source_msg = audio_message or message
    audio = source_msg.audio

    if not audio:
        await send_reply(message, "🤔 Не вижу аудиофайла")
        return

    has_limit, current, max_limit = await limit_service.check_limit(user_id, RequestType.VOICE)
    if not has_limit:
        await send_reply(
            message,
            f"⚠️ Лимит распознавания голоса исчерпан ({current}/{max_limit})" if language == "ru"
            else f"⚠️ Voice limit reached ({current}/{max_limit})",
            reply_markup=get_subscription_keyboard(language),
        )
        return

    if audio.file_size and audio.file_size > 25 * 1024 * 1024:
        await send_reply(message, "⚠️ Аудиофайл слишком большой (макс 25 МБ)")
        return

    filename = audio.file_name or "audio.mp3"
    status_msg = await send_reply(message, "🎵 Обрабатываю аудио..." if language == "ru" else "🎵 Processing audio...")

    try:
        file = await message.bot.get_file(audio.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        audio_data = file_bytes.read() if hasattr(file_bytes, 'read') else file_bytes

        text, usage = await ai_service.transcribe_audio(
            audio_data=audio_data,
            filename=filename,
            telegram_id=user_id
        )

        if not text or not text.strip():
            try:
                await status_msg.edit_text("🤔 Не удалось распознать речь." if language == "ru" else "🤔 Could not recognize speech.")
            except Exception:
                pass
            return

        if language == "ru":
            result_text = f"📝 <b>Распознанный текст из {filename}:</b>\n\n{text}"
        else:
            result_text = f"📝 <b>Transcribed text from {filename}:</b>\n\n{text}"

        if len(result_text) > 4000:
            result_text = result_text[:4000] + "..."

        try:
            await status_msg.edit_text(result_text, parse_mode="HTML")
        except Exception:
            try:
                await status_msg.delete()
            except Exception:
                pass
            await send_reply(message, result_text, parse_mode="HTML")

        await limit_service.increment_usage(user_id, RequestType.VOICE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.VOICE,
            response_preview=text[:500],
            model=usage.get("model", "whisper-1"),
            cost_usd=float(usage.get("cost_usd", 0)),
            status=RequestStatus.SUCCESS
        )

    except Exception as e:
        logger.error("Audio transcription error in group", error=str(e))
        try:
            await status_msg.edit_text(f"❌ Ошибка: {str(e)[:100]}")
        except Exception:
            pass

        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.VOICE,
            model="whisper-1",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )


async def analyze_document_response(
    message: Message, user_id: int, prompt: str, language: str,
    doc_message: Message = None
):
    """Analyze document in group."""
    source_msg = doc_message or message
    doc = source_msg.document

    if not doc:
        await send_reply(message, "🤔 Не вижу документа")
        return

    has_limit, current, max_limit = await limit_service.check_limit(user_id, RequestType.DOCUMENT)
    if not has_limit:
        await send_reply(
            message,
            f"⚠️ Лимит документов исчерпан ({current}/{max_limit})" if language == "ru"
            else f"⚠️ Document limit reached ({current}/{max_limit})",
            reply_markup=get_subscription_keyboard(language),
        )
        return

    # Check file size (20 MB)
    if doc.file_size and doc.file_size > 20 * 1024 * 1024:
        await send_reply(message, "⚠️ Файл слишком большой (макс 20 МБ)")
        return

    filename = doc.file_name or "document"
    status_msg = await send_reply(
        message,
        f"📄 Анализирую {filename}..." if language == "ru" else f"📄 Analyzing {filename}..."
    )

    try:
        from bot.services.document_service import document_service

        file = await message.bot.get_file(doc.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        file_data = file_bytes.read() if hasattr(file_bytes, 'read') else file_bytes

        # Extract text from document (returns 3 values: text, metadata, images)
        content, _metadata, images = await document_service.process_document(file_data, filename)

        if not content and not images:
            try:
                await status_msg.edit_text("🤔 Не удалось извлечь содержимое документа.")
            except Exception:
                pass
            return

        # Build analysis prompt
        question = prompt.strip() if prompt.strip() else (
            "Проанализируй этот документ и дай краткое описание содержимого."
            if language == "ru" else
            "Analyze this document and provide a brief summary."
        )

        if language == "ru":
            full_prompt = f"Документ: {filename}\n\nСодержимое:\n{content[:3000]}\n\nЗапрос: {question}\n\nОтвечай на русском."
        else:
            full_prompt = f"Document: {filename}\n\nContent:\n{content[:3000]}\n\nQuestion: {question}"

        messages_list = [
            {"role": "system", "content": "You are a document analysis assistant. Be concise."},
            {"role": "user", "content": full_prompt}
        ]

        response, usage = await ai_service.generate_text(
            messages=messages_list,
            telegram_id=user_id
        )

        if len(response) > 4000:
            response = response[:4000] + "..."

        try:
            await status_msg.delete()
        except Exception:
            pass

        await send_reply(message, f"📄 {response}")

        await limit_service.increment_usage(user_id, RequestType.DOCUMENT)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.DOCUMENT,
            prompt=question[:500],
            response_preview=response[:500],
            model=usage.get("model", "gpt-4o-mini"),
            status=RequestStatus.SUCCESS,
            cost_usd=float(usage.get("cost_usd", 0))
        )

    except Exception as e:
        logger.error("Document analysis error in group", error=str(e), exc_info=True)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await send_reply(message, f"❌ Ошибка анализа документа: {str(e)[:100]}")

        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.DOCUMENT,
            prompt=(prompt or "")[:500],
            model="gpt-4o-mini",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )


async def auto_detect_and_respond(message: Message, user_id: int, prompt: str, language: str):
    """Auto-detect intent via AI."""
    try:
        detect_messages = [
            {
                "role": "system",
                "content": "Classify: IMAGE (user wants a picture generated) or TEXT (user wants an answer/explanation)? Reply ONLY one word."
            },
            {"role": "user", "content": prompt[:300]}
        ]

        result, _ = await ai_service.generate_text(
            messages=detect_messages,
            telegram_id=user_id,
            max_tokens=10
        )

        if "IMAGE" in result.upper():
            await generate_image_response(message, user_id, prompt, language)
        else:
            await generate_text_response(message, user_id, prompt, language)

    except Exception as e:
        logger.error("Auto-detect failed", error=str(e))
        await generate_text_response(message, user_id, prompt, language)


async def generate_presentation_response(
    message: Message, user_id: int, topic: str, language: str
):
    """Generate a presentation in a group chat."""
    has_limit, current, max_limit = await limit_service.check_limit(
        user_id, RequestType.PRESENTATION
    )
    if not has_limit:
        await send_reply(
            message,
            f"⚠️ Лимит презентаций исчерпан ({current}/{max_limit})" if language == "ru"
            else f"⚠️ Presentation limit reached ({current}/{max_limit})",
            reply_markup=get_subscription_keyboard(language),
        )
        return

    status_msg = await send_reply(
        message,
        "📊 Генерирую презентацию...\nЭто может занять 1-3 минуты." if language == "ru"
        else "📊 Generating presentation...\nThis may take 1-3 minutes.",
    )

    try:
        from bot.services.presentation_service import presentation_service

        pptx_bytes, info = await presentation_service.generate_presentation(
            topic=topic,
            slides_count=7,
            style="business",
            include_images=True,
            language=language,
        )

        await limit_service.increment_usage(user_id, RequestType.PRESENTATION)

        filename = f"presentation_{topic[:30].replace(' ', '_')}.pptx"
        document = BufferedInputFile(pptx_bytes, filename=filename)

        try:
            await status_msg.delete()
        except Exception:
            pass

        if language == "ru":
            caption = (
                f"✅ <b>Презентация готова!</b>\n\n"
                f"📝 Тема: {info.get('title', topic)}\n"
                f"📊 Слайдов: {info.get('slides_count', 7)}"
            )
        else:
            caption = (
                f"✅ <b>Presentation ready!</b>\n\n"
                f"📝 Topic: {info.get('title', topic)}\n"
                f"📊 Slides: {info.get('slides_count', 7)}"
            )

        is_group = message.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP)
        thread_id = message.message_thread_id if is_group else None
        reply_to = message.message_id if is_group else None

        await message.bot.send_document(
            chat_id=message.chat.id,
            document=document,
            caption=caption,
            parse_mode="HTML",
            reply_to_message_id=reply_to,
            message_thread_id=thread_id,
        )

    except Exception as e:
        logger.error("Presentation error in group", error=str(e), exc_info=True)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await send_reply(
            message,
            f"❌ Ошибка генерации презентации: {str(e)[:100]}" if language == "ru"
            else f"❌ Presentation generation error: {str(e)[:100]}",
        )
