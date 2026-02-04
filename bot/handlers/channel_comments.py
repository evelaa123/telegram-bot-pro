"""
Channel comments handler.
Handles bot mentions and keywords in channel comments and groups.
Supports: text messages, photos with captions.
"""
import re
from typing import Tuple
from aiogram import Router, F, Bot
from aiogram.types import Message, BufferedInputFile
from aiogram.enums import ChatType

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.services.subscription_service import subscription_service
from bot.services.settings_service import settings_service
from config import settings as config_settings
from database.models import RequestType, RequestStatus
import structlog

logger = structlog.get_logger()
router = Router()

# Ключевые слова для генерации изображений
IMAGE_KEYWORDS = [
    "сгенерируй", "нарисуй", "создай картинку", "создай изображение",
    "сделай картинку", "сделай изображение", "покажи как выглядит",
    "визуализируй", "изобрази", "нарисуй мне", "сгенери",
    "generate", "draw", "create image", "make picture", "visualize",
    "покажи", "пикчу", "арт", "картинку"
]

# Ключевые слова для анализа изображений
ANALYZE_KEYWORDS = [
    "что это", "что здесь", "опиши", "проанализируй", "анализ",
    "что на фото", "что на картинке", "что изображено", "распознай",
    "what is this", "what's this", "describe", "analyze", "what do you see"
]

# Ключевые слова для текста
TEXT_KEYWORDS = [
    "расскажи", "объясни", "что такое", "как", "почему", "зачем",
    "ответь", "помоги", "подскажи", "напиши", "скажи",
    "tell", "explain", "what is", "how", "why", "help"
]

# Триггеры для вызова бота
BOT_TRIGGERS = [
    "бот", "bot", "ии", "ai", "гпт", "gpt", "ассистент", "assistant"
]


def is_bot_triggered(text: str, bot_username: str) -> bool:
    """Check if message is addressed to bot."""
    if not text:
        return False
    
    text_lower = text.lower().strip()
    
    # @username
    if bot_username and f"@{bot_username.lower()}" in text_lower:
        return True
    
    # Триггер в начале или после обращения
    for trigger in BOT_TRIGGERS:
        if text_lower.startswith(trigger):
            return True
        if text_lower.startswith(f"{trigger},"):
            return True
        if text_lower.startswith(f"{trigger} "):
            return True
        # "привет бот" - триггер не в начале
        if f" {trigger}" in text_lower or f",{trigger}" in text_lower:
            return True
    
    return False


def get_intent_and_prompt(text: str, bot_username: str, has_photo: bool = False) -> Tuple[str, str]:
    """
    Determine intent and extract clean prompt.
    """
    if not text:
        return ('analyze' if has_photo else 'auto', '')
    
    text_lower = text.lower()
    
    # Убираем триггеры из текста
    cleaned = text
    all_triggers = BOT_TRIGGERS.copy()
    if bot_username:
        all_triggers.append(f"@{bot_username.lower()}")
        all_triggers.append(bot_username.lower())
    
    for trigger in all_triggers:
        cleaned = re.sub(rf'^{re.escape(trigger)}[,\s]*', '', cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(rf'[,\s]*{re.escape(trigger)}[,\s]*', ' ', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    
    # =============================================
    # ЕСЛИ ЕСТЬ ФОТО - ПО УМОЛЧАНИЮ АНАЛИЗ
    # =============================================
    if has_photo:
        # Проверяем, не хочет ли пользователь сгенерировать картинку
        for kw in IMAGE_KEYWORDS:
            if kw in text_lower:
                prompt = re.sub(rf'\b{re.escape(kw)}\b', '', cleaned, flags=re.IGNORECASE).strip()
                prompt = re.sub(r'^[,.\s]+', '', prompt).strip()
                return 'image', prompt if prompt else cleaned
        
        # Фото + любой текст = анализ фото
        return 'analyze', cleaned if cleaned else "Опиши что на изображении"
    
    # =============================================
    # НЕТ ФОТО - определяем намерение по тексту
    # =============================================
    
    # Проверяем ключевые слова для генерации картинок
    for kw in IMAGE_KEYWORDS:
        if kw in text_lower:
            prompt = re.sub(rf'\b{re.escape(kw)}\b', '', cleaned, flags=re.IGNORECASE).strip()
            prompt = re.sub(r'^[,.\s]+', '', prompt).strip()
            return 'image', prompt if prompt else cleaned
    
    # Проверяем ключевые слова для текста
    for kw in TEXT_KEYWORDS:
        if kw in text_lower:
            return 'text', cleaned
    
    return 'auto', cleaned


# ============================================
# ВСПОМОГАТЕЛЬНАЯ ФУНКЦИЯ ДЛЯ ОТПРАВКИ
# ============================================
async def send_message(message: Message, text: str, photo: BufferedInputFile = None):
    """
    Send message with proper thread_id for channel comments.
    """
    thread_id = message.message_thread_id
    
    logger.warning(
        "SEND_MESSAGE called",
        chat_id=message.chat.id,
        reply_to=message.message_id,
        thread_id=thread_id,
        has_photo=photo is not None,
        text_preview=text[:50] if text else "(empty)"
    )
    
    if photo:
        return await message.bot.send_photo(
            chat_id=message.chat.id,
            photo=photo,
            caption=text,
            reply_to_message_id=message.message_id,
            message_thread_id=thread_id
        )
    else:
        return await message.bot.send_message(
            chat_id=message.chat.id,
            text=text,
            reply_to_message_id=message.message_id,
            message_thread_id=thread_id
        )


# ============================================
# ХЕНДЛЕР ДЛЯ ГРУПП - ТЕКСТ И ФОТО
# ============================================
@router.message(
    F.chat.type.in_({ChatType.GROUP, ChatType.SUPERGROUP}),
    F.text | F.photo
)
async def handle_group_message(message: Message, bot: Bot):
    """
    Handle messages in groups/supergroups.
    """
    
    # ДЕБАГ В САМОМ НАЧАЛЕ
    logger.warning(
        "=== INCOMING MESSAGE ===",
        chat_id=message.chat.id,
        message_id=message.message_id,
        thread_id=message.message_thread_id,
        content_type=message.content_type,
        has_photo=bool(message.photo),
        has_text=bool(message.text),
        has_caption=bool(message.caption),
        text_or_caption=(message.text or message.caption or "")[:50]
    )
    
    user = message.from_user
    if not user:
        return
    
    # Получаем текст
    text = message.text or message.caption or ""
    has_photo = bool(message.photo)
    
    # Username бота
    bot_info = await bot.get_me()
    bot_username = bot_info.username or ""
    
    # =============================================
    # ПРОВЕРКА ТРИГГЕРА
    # =============================================
    is_reply_to_bot = (
        message.reply_to_message and 
        message.reply_to_message.from_user and 
        message.reply_to_message.from_user.id == bot_info.id
    )
    
    is_mention = is_bot_triggered(text, bot_username)
    
    # Нет триггера - игнор
    if not is_mention and not is_reply_to_bot:
        return
    
    # =============================================
    # ТРИГГЕР ЕСТЬ - проверки
    # =============================================
    
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
    
    # Регистрируем пользователя
    db_user = await user_service.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code
    )
    
    language = db_user.settings.get('language', 'ru') if db_user.settings else 'ru'
    
    # Проверка блокировки
    if db_user.is_blocked:
        logger.warning("Blocked user in group", telegram_id=user.id)
        await send_message(message, "🚫 Ваш аккаунт заблокирован.")
        return
    
    # Проверка подписки
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
                
                if not is_subscribed:
                    if language == 'ru':
                        text_msg = f"🔒 Подпишись на канал {channel_username} чтобы использовать бота"
                    else:
                        text_msg = f"🔒 Subscribe to {channel_username} to use the bot"
                    
                    await send_message(message, text_msg)
                    return
                    
    except Exception as e:
        logger.error(f"Subscription check error: {e}")
    
    # =============================================
    # ОПРЕДЕЛЯЕМ НАМЕРЕНИЕ И ОБРАБАТЫВАЕМ
    # =============================================
    
    intent, prompt = get_intent_and_prompt(text, bot_username, has_photo)
    
    # =============================================
    # КОНТЕКСТ ИЗ REPLY - ТОЛЬКО ЕСЛИ НЕТ ФОТО И ОТВЕТ НА ПОЛЬЗОВАТЕЛЯ
    # =============================================
    if not has_photo and message.reply_to_message and not is_reply_to_bot:
        # Проверяем что это ответ на сообщение пользователя, а не на пост канала
        reply_msg = message.reply_to_message
        # Пост канала обычно не имеет from_user или from_user.is_bot = False для каналов
        if reply_msg.from_user and not reply_msg.from_user.is_bot:
            reply_text = reply_msg.text or reply_msg.caption or ""
            if reply_text and len(reply_text) < 500:  # Ограничиваем контекст
                prompt = f"Контекст: {reply_text}\n\nЗапрос: {prompt}"
    
    logger.info(
        "Processing request",
        intent=intent,
        has_photo=has_photo,
        prompt_preview=prompt[:80] if prompt else "(empty)"
    )
    
    # Обрабатываем
    if has_photo:
        # Фото всегда анализируем (если не просят сгенерировать картинку)
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
        await send_message(message, "🤔 Что именно сделать? Напиши подробнее!")


async def analyze_photo_response(message: Message, user_id: int, prompt: str, language: str):
    """Analyze photo with GPT-4 Vision."""
    
    logger.warning(
        "ANALYZE_PHOTO_RESPONSE called",
        chat_id=message.chat.id,
        message_id=message.message_id,
        thread_id=message.message_thread_id,
        prompt=prompt[:100]
    )
    
    has_limit, current, max_limit = await limit_service.check_limit(user_id, RequestType.DOCUMENT)
    if not has_limit:
        await send_message(message, f"⚠️ Лимит анализа исчерпан ({current}/{max_limit})")
        return
    
    if not message.photo:
        await send_message(message, "🤔 Не вижу фото для анализа")
        return
    
    status_msg = await send_message(message, "🔍 Анализирую изображение...")
    
    try:
        # Скачиваем фото
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        file_data = await message.bot.download_file(file.file_path)
        image_bytes = file_data.read() if hasattr(file_data, 'read') else file_data
        
        # Промпт
        if language == 'ru':
            full_prompt = f"{prompt}\n\nОтвечай на русском языке."
        else:
            full_prompt = prompt
        
        logger.info(f"Calling AI analyze_image with prompt: {full_prompt[:100]}")
        
        # Анализ
        result, usage = await ai_service.analyze_image(
            image_data=image_bytes,
            prompt=full_prompt,
            telegram_id=user_id
        )
        
        logger.info(f"AI analyze_image result: {result[:200]}")
        
        if len(result) > 4000:
            result = result[:4000] + "..."
        
        try:
            await status_msg.delete()
        except:
            pass
        
        logger.warning(
            "SENDING ANALYZE RESULT",
            chat_id=message.chat.id,
            message_id=message.message_id,
            thread_id=message.message_thread_id,
            result_len=len(result),
            result_preview=result[:100]
        )
        
        await send_message(message, f"🔍 {result}")
        
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
        
        logger.info("Photo analyzed in group", user_id=user_id)
        
    except Exception as e:
        logger.error("Photo analysis error", error=str(e), exc_info=True)
        try:
            await status_msg.delete()
        except:
            pass
        await send_message(message, f"❌ Ошибка анализа: {str(e)[:100]}")
        
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
        await send_message(message, f"⚠️ Лимит картинок исчерпан ({current}/{max_limit})")
        return
    
    if not prompt or len(prompt.strip()) < 3:
        await send_message(message, "🤔 Опиши что нарисовать!")
        return
    
    status_msg = await send_message(message, "🎨 Рисую...")
    
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
        except:
            pass
        
        await send_message(message, f"🖼 {caption}", photo=photo)
        
        await limit_service.increment_usage(user_id, RequestType.IMAGE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500],
            model="dall-e-3",
            status=RequestStatus.SUCCESS,
            cost_usd=float(usage.get("cost_usd", 0))
        )
        
        logger.info("Image generated in group", user_id=user_id)
        
    except Exception as e:
        logger.error("Image error", error=str(e))
        try:
            await status_msg.delete()
        except:
            pass
        await send_message(message, f"❌ Ошибка: {str(e)[:100]}")
        
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
        await send_message(message, f"⚠️ Лимит запросов исчерпан ({current}/{max_limit})")
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
        
        await send_message(message, response)
        
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
        
        logger.info("Text response in group", user_id=user_id)
        
    except Exception as e:
        logger.error("Text error", error=str(e))
        await send_message(message, f"❌ Ошибка: {str(e)[:100]}")
        
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.TEXT,
            prompt=prompt[:500],
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
        
        logger.info(f"Auto-detect: '{result.strip()}'")
        
        if "IMAGE" in result.upper():
            await generate_image_response(message, user_id, prompt, language)
        else:
            await generate_text_response(message, user_id, prompt, language)
            
    except Exception as e:
        logger.error("Auto-detect failed", error=str(e))
        await generate_text_response(message, user_id, prompt, language)
