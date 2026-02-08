"""
Photo message handler.
Handles photo messages sent by users.
"""
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction
from database.models import RequestType, RequestStatus
from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.inline import get_subscription_keyboard, get_photo_actions_keyboard
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
    
    # Check if user is in animate_photo state
    if state and state.startswith("animate_photo_wait"):
        # User sent a NEW photo to animate
        await handle_animate_new_photo(message, user.id)
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
        
        # Save file_id to Redis for animate button (avoids 64-byte callback_data limit)
        await redis_client.client.set(
            f"user:{user_id}:last_photo_file_id",
            photo.file_id,
            ex=3600
        )
        
        # Show result with Animate button (no file_id in callback_data!)
        await status_msg.edit_text(
            result,
            reply_markup=get_photo_actions_keyboard(language=language)
        )
        
        # Get actual model used from usage info
        model_used = usage.get("model", "vision")
        
        # Increment usage and record request
        await limit_service.increment_usage(user_id, RequestType.IMAGE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500],
            response_preview=result[:500],
            model=model_used,
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
            model="vision",
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


async def handle_animate_new_photo(message: Message, user_id: int):
    """
    Handle photo sent when user is in 'animate_photo_wait' state.
    User wants to animate this specific photo.
    """
    language = await user_service.get_user_language(user_id)
    
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Set state to animate_photo with this file_id, ask for prompt
    await redis_client.set_user_state(user_id, f"animate_photo:{file_id}")
    
    if language == "ru":
        await message.answer(
            "🎞 <b>Оживление фото</b>\n\n"
            "Опишите, как должно двигаться/оживать изображение.\n\n"
            "<i>Например: \u00abКамера медленно приближается, волосы развеваются на ветру\u00bb</i>\n\n"
            "Или отправьте просто точку (.) для автоматического оживления."
        )
    else:
        await message.answer(
            "🎞 <b>Animate Photo</b>\n\n"
            "Describe how the image should move/animate.\n\n"
            "<i>Example: 'Camera slowly zooms in, hair blowing in the wind'</i>\n\n"
            "Or send just a dot (.) for automatic animation."
        )


@router.callback_query(F.data == "photo:animate")
async def callback_photo_animate(callback: CallbackQuery):
    """Handle animate photo button from photo analysis result."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    # Check premium
    from bot.services.subscription_service import subscription_service
    is_premium = await subscription_service.check_premium(user.id)
    
    if not is_premium:
        if language == "ru":
            await callback.answer("💎 Оживление фото доступно только для премиум-подписчиков!", show_alert=True)
        else:
            await callback.answer("💎 Animate photo is available for premium subscribers only!", show_alert=True)
        return
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.VIDEO_ANIMATE
    )
    
    if not has_limit:
        if language == "ru":
            await callback.answer(f"⚠️ Лимит оживления фото исчерпан ({max_limit})", show_alert=True)
        else:
            await callback.answer(f"⚠️ Animate photo limit reached ({max_limit})", show_alert=True)
        return
    
    # Get file_id from Redis (saved during photo analysis)
    file_id = await redis_client.client.get(f"user:{user.id}:last_photo_file_id")
    
    if not file_id:
        if language == "ru":
            await callback.answer("Фото не найдено. Отправьте фото заново.", show_alert=True)
        else:
            await callback.answer("Photo not found. Send photo again.", show_alert=True)
        return
    
    file_id = file_id.decode() if isinstance(file_id, bytes) else file_id
    
    await redis_client.set_user_state(user.id, f"animate_photo:{file_id}")
    
    if language == "ru":
        await callback.message.answer(
            "🎞 <b>Оживление фото</b>\n\n"
            "Опишите, как должно двигаться/оживать изображение.\n\n"
            "<i>Например: «Камера медленно приближается, волосы развеваются на ветру»</i>\n\n"
            "Или отправьте точку (.) для автоматического оживления."
        )
    else:
        await callback.message.answer(
            "🎞 <b>Animate Photo</b>\n\n"
            "Describe how the image should move/animate.\n\n"
            "<i>Example: 'Camera slowly zooms in, hair blowing in the wind'</i>\n\n"
            "Or send a dot (.) for automatic animation."
        )
    
    await callback.answer()
