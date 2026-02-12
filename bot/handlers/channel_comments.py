"""
Channel comments & group handler.
Handles bot mentions, commands, and all content types in groups/channels.
Supports: text, photos, voice, audio, documents — full functionality with reply_to.
"""
import re
from typing import Tuple
from aiogram import Router, F, Bot
from aiogram.types import Message, BufferedInputFile
from aiogram.enums import ChatType
from aiogram.filters import Command

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.services.subscription_service import subscription_service
from bot.services.settings_service import settings_service
from config import settings as config_settings
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
import structlog

logger = structlog.get_logger()
router = Router()

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


async def send_reply(message: Message, text: str, photo: BufferedInputFile = None, parse_mode: str = None):
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
async def group_cmd_new(message: Message, bot: Bot):
    """Handle /new in groups — clear context."""
    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    user_id = message.from_user.id
    await redis_client.clear_context(user_id)
    await redis_client.clear_document_context(user_id)
    await redis_client.clear_user_state(user_id)

    if language == "ru":
        text = "🔄 Контекст очищен. Можете задать новый вопрос."
    else:
        text = "🔄 Context cleared. You can ask a new question."

    await send_reply(message, text)


@router.message(
    Command("image"),
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
)
async def group_cmd_image(message: Message, bot: Bot):
    """Handle /image <prompt> in groups — generate image directly from args."""
    db_user, language = await _check_user_access(message, bot)
    if not db_user:
        return

    user_id = message.from_user.id
    prompt = _strip_command(message.text or "")

    if not prompt or len(prompt.strip()) < 3:
        if language == "ru":
            await send_reply(message, "🖼 Используйте: /image [описание картинки]\n\nНапример: /image кот в космосе")
        else:
            await send_reply(message, "🖼 Usage: /image [image description]\n\nExample: /image cat in space")
        return

    await generate_image_response(message, user_id, prompt, language)



# ============================================
# VOICE HANDLER FOR GROUPS
# ============================================

@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.voice,
)
async def handle_group_voice(message: Message, bot: Bot):
    """Handle voice messages in groups — transcribe when bot is triggered."""
    # Voice messages: always process if it's a reply to bot, or has mention in caption
    bot_info = await bot.get_me()
    bot_username = bot_info.username or ""

    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_info.id
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
async def handle_group_audio(message: Message, bot: Bot):
    """Handle audio files in groups — transcribe when bot is triggered."""
    bot_info = await bot.get_me()
    bot_username = bot_info.username or ""

    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_info.id
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
async def handle_group_document(message: Message, bot: Bot):
    """Handle documents in groups — analyze when bot is triggered."""
    bot_info = await bot.get_me()
    bot_username = bot_info.username or ""

    caption = message.caption or ""
    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_info.id
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
async def handle_group_message(message: Message, bot: Bot):
    """Handle text and photo messages in groups/supergroups."""

    user = message.from_user
    if not user:
        return

    text = message.text or message.caption or ""
    has_photo = bool(message.photo)

    # Skip commands — they are handled above
    if _is_command(text):
        return

    bot_info = await bot.get_me()
    bot_username = bot_info.username or ""

    # Check trigger
    is_reply_to_bot = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_info.id
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
        await send_reply(message, f"⚠️ Лимит анализа исчерпан ({current}/{max_limit})")
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


async def generate_image_response(message: Message, user_id: int, prompt: str, language: str):
    """Generate image."""
    has_limit, current, max_limit = await limit_service.check_limit(user_id, RequestType.IMAGE)
    if not has_limit:
        await send_reply(message, f"⚠️ Лимит картинок исчерпан ({current}/{max_limit})")
        return

    if not prompt or len(prompt.strip()) < 3:
        await send_reply(message, "🤔 Опиши что нарисовать!")
        return

    status_msg = await send_reply(message, "🎨 Рисую...")

    try:
        image_url, usage = await ai_service.generate_image(
            prompt=prompt,
            size="1024x1024",
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


async def generate_text_response(message: Message, user_id: int, prompt: str, language: str):
    """Generate text response."""
    has_limit, current, max_limit = await limit_service.check_limit(user_id, RequestType.TEXT)
    if not has_limit:
        await send_reply(message, f"⚠️ Лимит запросов исчерпан ({current}/{max_limit})")
        return

    try:
        messages = [
            {
                "role": "system",
                "content": f"You are a helpful assistant in a group chat. Be concise (2-3 paragraphs max). Respond in {'Russian' if language == 'ru' else 'English'}."
            },
            {"role": "user", "content": prompt}
        ]

        response, usage = await ai_service.generate_text(
            messages=messages,
            telegram_id=user_id
        )

        if len(response) > 4000:
            response = response[:4000] + "..."

        await send_reply(message, response)

        await limit_service.increment_usage(user_id, RequestType.TEXT)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.TEXT,
            prompt=prompt[:500],
            response_preview=response[:500],
            model=usage.get("model", "gpt-4o-mini"),
            status=RequestStatus.SUCCESS,
            cost_usd=float(usage.get("cost_usd", 0))
        )

    except Exception as e:
        logger.error("Text error", error=str(e))
        await send_reply(message, f"❌ Ошибка: {str(e)[:100]}")

        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.TEXT,
            prompt=prompt[:500],
            model="gpt-4o-mini",
            status=RequestStatus.FAILED,
            error_message=str(e)
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
        if language == "ru":
            await send_reply(message, f"⚠️ Лимит распознавания голоса исчерпан ({current}/{max_limit})")
        else:
            await send_reply(message, f"⚠️ Voice recognition limit reached ({current}/{max_limit})")
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
        await send_reply(message, f"⚠️ Лимит распознавания голоса исчерпан ({current}/{max_limit})")
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
        await send_reply(message, f"⚠️ Лимит документов исчерпан ({current}/{max_limit})")
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

        # Extract text from document
        content, images = await document_service.process_document(file_data, filename)

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
