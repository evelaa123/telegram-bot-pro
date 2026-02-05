"""
Photo message handler.
Handles image analysis with AI vision.
"""
import asyncio
import time
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.inline import get_subscription_keyboard
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


@router.message(F.photo)
async def handle_photo(message: Message):
    """Handle photo messages - analyze with AI vision or send to support."""
    
    # In groups, photos are handled differently
    if message.chat.type in ("group", "supergroup"):
        return
    
    user = message.from_user
    
    # Check if user is in support mode
    user_state = await redis_client.get_user_state(user.id)
    if user_state == "support_message":
        # Handle as support message with photo
        from bot.handlers.support import handle_support_message
        photo = message.photo[-1]  # Get largest photo
        await handle_support_message(message, user.id, photo_file_id=photo.file_id)
        return
    
    # Get user settings
    user_settings = await user_service.get_user_settings(user.id)
    language = user_settings.get("language", "ru")
    
    # Check limits (using TEXT limit for image analysis)
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.TEXT
    )
    
    if not has_limit:
        if language == "ru":
            text = (
                f"⚠️ Вы достигли лимита запросов на сегодня ({max_limit}).\n\n"
                "Оформите подписку для увеличения лимитов."
            )
        else:
            text = (
                f"⚠️ You've reached your daily request limit ({max_limit}).\n\n"
                "Subscribe to increase limits."
            )
        await message.answer(
            text,
            reply_markup=get_subscription_keyboard(language)
        )
        return
    
    # Get the largest photo
    photo = message.photo[-1]  # Telegram sends multiple sizes, last is largest
    
    # Check file size
    if photo.file_size and photo.file_size > 20 * 1024 * 1024:  # 20MB limit
        if language == "ru":
            await message.answer("⚠️ Изображение слишком большое. Максимум 20 МБ.")
        else:
            await message.answer("⚠️ Image is too large. Maximum 20 MB.")
        return
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    # Send progress message
    if language == "ru":
        progress_msg = await message.answer("🔍 Анализирую изображение...")
    else:
        progress_msg = await message.answer("🔍 Analyzing image...")
    
    start_time = time.time()
    
    try:
        # Download photo
        file = await message.bot.get_file(photo.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        image_data = file_bytes.read()
        
        # Get caption if any (use as prompt)
        caption = message.caption or ""
        
        # Build prompt
        if caption:
            prompt = caption
        elif language == "ru":
            prompt = "Подробно опиши это изображение. Что на нём изображено? Опиши все детали."
        else:
            prompt = "Describe this image in detail. What is shown? Describe all details."
        
        # Analyze image with AI
        response, usage = await ai_service.analyze_image(
            image_data=image_data,
            prompt=prompt,
            telegram_id=user.id
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Delete progress message
        try:
            await progress_msg.delete()
        except Exception:
            pass
        
        # Send response
        await message.answer(
            response,
            parse_mode="HTML"
        )
        
        # Increment usage
        await limit_service.increment_usage(user.id, RequestType.TEXT)
        
        # Record request
        await limit_service.record_request(
            telegram_id=user.id,
            request_type=RequestType.TEXT,
            prompt=f"[IMAGE] {prompt[:200]}",
            model=usage.get("model", "vision"),
            status=RequestStatus.SUCCESS,
            cost_usd=usage.get("cost_usd"),
            duration_ms=duration_ms,
            tokens_input=usage.get("input_tokens"),
            tokens_output=usage.get("output_tokens")
        )
        
        logger.info(
            "Photo analyzed",
            user_id=user.id,
            duration_ms=duration_ms
        )
        
    except Exception as e:
        logger.error("Photo analysis failed", error=str(e), user_id=user.id)
        
        # Delete progress message
        try:
            await progress_msg.delete()
        except Exception:
            pass
        
        if language == "ru":
            await message.answer(
                "❌ <b>Ошибка анализа изображения</b>\n\n"
                "Не удалось проанализировать изображение. Попробуйте ещё раз.",
                parse_mode="HTML"
            )
        else:
            await message.answer(
                "❌ <b>Image Analysis Error</b>\n\n"
                "Failed to analyze the image. Please try again.",
                parse_mode="HTML"
            )
        
        # Record failed request
        await limit_service.record_request(
            telegram_id=user.id,
            request_type=RequestType.TEXT,
            prompt=f"[IMAGE] {message.caption or 'analyze'}",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )
