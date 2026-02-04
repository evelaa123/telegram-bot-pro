"""
Image generation handler.
Handles DALL-E 3 and Qwen Wanx image generation.
"""
import asyncio
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.enums import ChatAction

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.inline import get_image_actions_keyboard, get_image_size_keyboard
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


@router.message(Command("image"))
async def cmd_image(message: Message):
    """Handle /image command - start image generation flow."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.IMAGE
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита генерации изображений на сегодня ({max_limit}).\n"
                "Лимиты обновятся в полночь UTC."
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily image generation limit ({max_limit}).\n"
                "Limits reset at midnight UTC."
            )
        return
    
    # Get user's AI provider
    user_settings = await user_service.get_user_settings(user.id)
    ai_provider = user_settings.get("ai_provider", "openai")
    
    # Check if Qwen is available for images
    qwen_available = ai_service.is_provider_available("qwen", "image")
    
    if language == "ru":
        provider_info = ""
        if ai_provider == "qwen" and qwen_available:
            provider_info = "\n🔮 Используется: Qwen (Wanx)"
        else:
            provider_info = "\n🤖 Используется: OpenAI (DALL-E 3)"
        
        text = (
            f"🖼 <b>Генерация изображений</b>\n\n"
            f"Осталось сегодня: {max_limit - current} из {max_limit}"
            f"{provider_info}\n\n"
            "Выберите размер изображения:"
        )
    else:
        provider_info = ""
        if ai_provider == "qwen" and qwen_available:
            provider_info = "\n🔮 Using: Qwen (Wanx)"
        else:
            provider_info = "\n🤖 Using: OpenAI (DALL-E 3)"
        
        text = (
            f"🖼 <b>Image Generation</b>\n\n"
            f"Remaining today: {max_limit - current} of {max_limit}"
            f"{provider_info}\n\n"
            "Choose image size:"
        )
    
    await message.answer(text, reply_markup=get_image_size_keyboard(language))


@router.callback_query(F.data.startswith("image_size:"))
async def callback_image_size(callback: CallbackQuery):
    """Handle image size selection."""
    user = callback.from_user
    size = callback.data.split(":")[1]  # 1024x1024, 1792x1024, 1024x1792
    
    # Store selected size and switch to image prompt mode
    await redis_client.set_user_state(user.id, f"image_prompt:{size}")
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.edit_text(
            f"🖼 <b>Размер выбран: {size}</b>\n\n"
            "Теперь опишите изображение, которое хотите создать.\n\n"
            "<i>Например: «Кот-космонавт на Луне, цифровое искусство»</i>"
        )
    else:
        await callback.message.edit_text(
            f"🖼 <b>Size selected: {size}</b>\n\n"
            "Now describe the image you want to create.\n\n"
            "<i>Example: 'An astronaut cat on the Moon, digital art'</i>"
        )
    
    await callback.answer()


@router.callback_query(F.data == "image:cancel")
async def callback_image_cancel(callback: CallbackQuery):
    """Handle image generation cancel."""
    user = callback.from_user
    await redis_client.clear_user_state(user.id)
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.edit_text("❌ Генерация изображения отменена.")
    else:
        await callback.message.edit_text("❌ Image generation cancelled.")
    
    await callback.answer()


@router.callback_query(F.data == "image:regenerate")
async def callback_image_regenerate(callback: CallbackQuery):
    """Handle image regeneration with same prompt."""
    user = callback.from_user
    
    # Get last prompt from state
    state = await redis_client.get_user_state(user.id)
    
    if not state or not state.startswith("last_image_prompt:"):
        language = await user_service.get_user_language(user.id)
        if language == "ru":
            await callback.answer("Промпт не найден. Создайте новое изображение.", show_alert=True)
        else:
            await callback.answer("Prompt not found. Create a new image.", show_alert=True)
        return
    
    parts = state.split(":", 2)
    if len(parts) < 3:
        await callback.answer("Error getting prompt", show_alert=True)
        return
    
    size = parts[1]
    prompt = parts[2]
    
    await callback.answer("Regenerating...")
    await generate_image(callback.message, user.id, prompt, size, is_callback=True)


@router.callback_query(F.data == "image:edit")
async def callback_image_edit(callback: CallbackQuery):
    """Handle prompt edit request."""
    user = callback.from_user
    
    # Get current settings and switch to edit mode
    state = await redis_client.get_user_state(user.id)
    
    if state and state.startswith("last_image_prompt:"):
        parts = state.split(":", 2)
        size = parts[1] if len(parts) > 1 else "1024x1024"
        await redis_client.set_user_state(user.id, f"image_prompt:{size}")
    else:
        await redis_client.set_user_state(user.id, "image_prompt:1024x1024")
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.answer(
            "✏️ Введите новый промпт для изображения:"
        )
    else:
        await callback.message.answer(
            "✏️ Enter a new prompt for the image:"
        )
    
    await callback.answer()


async def generate_image(
    message: Message,
    user_id: int,
    prompt: str,
    size: str = "1024x1024",
    is_callback: bool = False
):
    """
    Generate image with AI (DALL-E 3 or Qwen Wanx based on user settings).
    
    Args:
        message: Message to reply to
        user_id: Telegram user ID
        prompt: Image description
        size: Image size
        is_callback: Whether called from callback (for editing message)
    """
    language = await user_service.get_user_language(user_id)
    user_settings = await user_service.get_user_settings(user_id)
    style = user_settings.get("image_style", "vivid")
    ai_provider = user_settings.get("ai_provider", "openai")
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user_id, RequestType.IMAGE
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита генерации изображений на сегодня ({max_limit}).\n"
                "Лимиты обновятся в полночь UTC."
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily image generation limit ({max_limit}).\n"
                "Limits reset at midnight UTC."
            )
        return
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
    
    # Determine which provider will be used
    actual_provider = ai_provider
    if ai_provider == "qwen" and not ai_service.is_provider_available("qwen", "image"):
        actual_provider = "openai"
    
    # Send progress message
    if language == "ru":
        provider_name = "Qwen Wanx" if actual_provider == "qwen" else "DALL-E 3"
        progress_msg = await message.answer(f"🎨 Генерирую изображение ({provider_name})...")
    else:
        provider_name = "Qwen Wanx" if actual_provider == "qwen" else "DALL-E 3"
        progress_msg = await message.answer(f"🎨 Generating image ({provider_name})...")
    
    # Animate progress
    animation_task = asyncio.create_task(
        animate_progress(progress_msg, language)
    )
    
    try:
        # Generate image using unified AI service
        image_url, usage = await ai_service.generate_image(
            prompt=prompt,
            size=size,
            style=style,
            telegram_id=user_id
        )
        
        # Stop animation
        animation_task.cancel()
        
        # Download image
        provider_used = usage.get("model", "").startswith("wanx") and "qwen" or "openai"
        image_bytes = await ai_service.download_image(image_url, provider=provider_used)
        
        # Send image
        photo = BufferedInputFile(image_bytes, filename="generated_image.png")
        
        # Prepare caption
        model_used = usage.get("model", "unknown")
        revised_prompt = usage.get("revised_prompt", prompt)
        if len(revised_prompt) > 800:
            revised_prompt = revised_prompt[:800] + "..."
        
        if language == "ru":
            caption = f"🖼 <b>Сгенерировано ({model_used}):</b>\n<i>{revised_prompt}</i>"
        else:
            caption = f"🖼 <b>Generated ({model_used}):</b>\n<i>{revised_prompt}</i>"
        
        # Delete progress message
        try:
            await progress_msg.delete()
        except Exception:
            pass
        
        # Send photo with action buttons
        await message.answer_photo(
            photo=photo,
            caption=caption,
            reply_markup=get_image_actions_keyboard(language=language)
        )
        
        # Store prompt for potential regeneration
        await redis_client.set_user_state(
            user_id, 
            f"last_image_prompt:{size}:{prompt}"
        )
        
        # Increment usage and record
        await limit_service.increment_usage(user_id, RequestType.IMAGE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500],
            model=model_used,
            cost_usd=float(usage.get("cost_usd", 0)),
            status=RequestStatus.SUCCESS
        )
        
        logger.info(
            "Image generated",
            user_id=user_id,
            model=model_used,
            size=size,
            style=style
        )
        
    except Exception as e:
        animation_task.cancel()
        logger.error("Image generation error", user_id=user_id, error=str(e))
        
        # Record failed request
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500],
            model="unknown",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )
        
        # Delete progress message
        try:
            await progress_msg.delete()
        except Exception:
            pass
        
        # Send error message
        error_str = str(e).lower()
        if "content_policy" in error_str or "safety" in error_str:
            if language == "ru":
                error_text = (
                    "⚠️ Ваш запрос нарушает правила контента.\n"
                    "Пожалуйста, измените описание и попробуйте снова."
                )
            else:
                error_text = (
                    "⚠️ Your request violates content policy.\n"
                    "Please modify your description and try again."
                )
        else:
            if language == "ru":
                error_text = (
                    f"❌ Произошла ошибка при генерации изображения.\n"
                    f"Попробуйте ещё раз или измените описание.\n\n"
                    f"<i>Ошибка: {str(e)[:200]}</i>"
                )
            else:
                error_text = (
                    f"❌ An error occurred while generating the image.\n"
                    f"Please try again or modify your description.\n\n"
                    f"<i>Error: {str(e)[:200]}</i>"
                )
        
        await message.answer(error_text)


async def animate_progress(message: Message, language: str):
    """Animate progress message with dots."""
    base_text = "🎨 Генерирую изображение" if language == "ru" else "🎨 Generating image"
    dots = [".", "..", "..."]
    i = 0
    
    try:
        while True:
            try:
                await message.edit_text(f"{base_text}{dots[i % 3]}")
            except Exception:
                pass
            i += 1
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
