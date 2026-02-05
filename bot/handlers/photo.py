"""
Photo message handler.
Handles photo messages sent by users.
"""
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.inline import get_subscription_keyboard
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from bot.handlers.support import save_support_message
from config import settings
import structlog
import time

logger = structlog.get_logger()
router = Router()


@router.message(F.photo)
async def handle_photo_message(message: Message):
    """
    Handle photo messages.
    - If user is in support_message state: save photo to support
    - Otherwise: analyze photo with AI Vision
    """
    user = message.from_user
    
    # Check user state FIRST
    state = await redis_client.get_user_state(user.id)
    
    if state == "support_message":
        # User is in support mode - save photo to support
        await handle_support_photo(message, user.id)
        return
    
    # Otherwise - analyze photo with AI
    await handle_photo_analysis(message, user.id)


async def handle_support_photo(message: Message, user_id: int):
    """
    Handle photo sent in support mode.
    Save photo file_id to support message.
    """
    language = await user_service.get_user_language(user_id)
    
    try:
        # Get the best quality photo (last in array)
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # Build message text with photo marker
        caption = message.caption or ""
        message_text = f"[PHOTO:{file_id}]"
        if caption:
            message_text = f"{caption}\n{message_text}"
        
        # Save the message
        msg_id = await save_support_message(
            user_telegram_id=user_id,
            message_text=message_text,
            is_from_user=True
        )
        
        # Clear user state
        await redis_client.clear_user_state(user_id)
        
        if language == "ru":
            await message.answer(
                "✅ <b>Фото отправлено!</b>\n\n"
                "Наша команда поддержки рассмотрит ваше обращение и ответит вам в ближайшее время.\n\n"
                "💡 Используйте /support чтобы отправить ещё одно сообщение."
            )
        else:
            await message.answer(
                "✅ <b>Photo sent!</b>\n\n"
                "Our support team will review your request and respond shortly.\n\n"
                "💡 Use /support to send another message."
            )
        
        logger.info(
            "Support photo received",
            user_id=user_id,
            message_id=msg_id,
            file_id=file_id,
            has_caption=bool(caption)
        )
        
    except Exception as e:
        logger.error("Failed to save support photo", error=str(e), user_id=user_id)
        
        if language == "ru":
            await message.answer(
                "❌ Произошла ошибка при отправке фото. Попробуйте позже."
            )
        else:
            await message.answer(
                "❌ An error occurred while sending your photo. Please try again later."
            )


async def handle_photo_analysis(message: Message, user_id: int):
    """
    Analyze photo with AI Vision.
    """
    language = await user_service.get_user_language(user_id)
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user_id, RequestType.IMAGE
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита запросов на сегодня ({max_limit}).\n"
                "Лимиты обновятся в полночь UTC.\n\n"
                "💎 <b>Хотите больше запросов?</b>\n"
                "Оформите подписку для увеличения лимитов!",
                reply_markup=get_subscription_keyboard(language)
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily request limit ({max_limit}).\n"
                "Limits reset at midnight UTC.\n\n"
                "💎 <b>Want more requests?</b>\n"
                "Subscribe to increase your limits!",
                reply_markup=get_subscription_keyboard(language)
            )
        return
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    # Get the best quality photo
    photo = message.photo[-1]
    
    # Get caption as prompt or use default
    caption = message.caption
    if caption:
        prompt = caption
    else:
        prompt = "Опиши что изображено на фото подробно" if language == "ru" else "Describe what is shown in the photo in detail"
    
    if language == "ru":
        status_msg = await message.answer("🔍 Анализирую изображение...")
    else:
        status_msg = await message.answer("🔍 Analyzing image...")
    
    start_time = time.time()
    
    try:
        # Download the photo
        file = await message.bot.get_file(photo.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        
        # Read bytes
        import io
        image_data = io.BytesIO(file_bytes.read()).getvalue()
        
        # Analyze with AI Vision
        result, usage = await ai_service.analyze_image(
            image_data=image_data,
            prompt=prompt,
            telegram_id=user_id
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Update status message with result
        if len(result) > 4000:
            result = result[:4000] + "..."
        
        await status_msg.edit_text(result)
        
        # Increment usage and record request
        await limit_service.increment_usage(user_id, RequestType.IMAGE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500],
            response_preview=result[:500],
            model="gpt-4o-vision",
            status=RequestStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(
            "Photo analysis completed",
            user_id=user_id,
            duration_ms=duration_ms,
            result_length=len(result)
        )
        
    except Exception as e:
        logger.error("Photo analysis error", user_id=user_id, error=str(e))
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Record failed request
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500] if prompt else "photo analysis",
            model="gpt-4o-vision",
            status=RequestStatus.FAILED,
            error_message=str(e),
            duration_ms=duration_ms
        )
        
        if language == "ru":
            error_text = (
                "❌ Произошла ошибка при анализе изображения.\n"
                "Попробуйте ещё раз или отправьте другое фото."
            )
        else:
            error_text = (
                "❌ An error occurred while analyzing the image.\n"
                "Please try again or send a different photo."
            )
        
        try:
            await status_msg.edit_text(error_text)
        except Exception:
            await message.answer(error_text)
