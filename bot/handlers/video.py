"""
Video generation handler.
Handles Sora video generation (queued processing).
"""
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction

from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.inline import get_video_model_keyboard, get_video_duration_keyboard, get_subscription_keyboard
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


@router.message(Command("video"))
async def cmd_video(message: Message):
    """Handle /video command - start video generation flow."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.VIDEO
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита генерации видео на сегодня ({max_limit}).\n"
                "Лимиты обновятся в полночь UTC.\n\n"
                "💎 <b>Хотите больше видео?</b>\n"
                "Оформите подписку для увеличения лимитов!",
                reply_markup=get_subscription_keyboard(language)
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily video generation limit ({max_limit}).\n"
                "Limits reset at midnight UTC.\n\n"
                "💎 <b>Want more videos?</b>\n"
                "Subscribe to increase your limits!",
                reply_markup=get_subscription_keyboard(language)
            )
        return
    
    if language == "ru":
        text = (
            "🎬 <b>Генерация видео</b>\n\n"
            f"Осталось сегодня: {max_limit - current} из {max_limit}\n\n"
            "<b>Модели:</b>\n"
            "• <b>sora-2</b> — быстрый режим (1-3 мин)\n"
            "• <b>sora-2-pro</b> — высокое качество (5-10 мин)\n\n"
            "<b>Длительности:</b> 4, 8 или 12 секунд\n"
            "<b>Разрешение:</b> 720x1280\n\n"
            "⚠️ Нельзя создавать реальных людей и копирайтный контент\n\n"
            "Выберите модель:"
        )
    else:
        text = (
            "🎬 <b>Video Generation</b>\n\n"
            f"Remaining today: {max_limit - current} of {max_limit}\n\n"
            "<b>Models:</b>\n"
            "• <b>sora-2</b> — fast mode (1-3 min)\n"
            "• <b>sora-2-pro</b> — high quality (5-10 min)\n\n"
            "<b>Durations:</b> 4, 8 or 12 seconds\n"
            "<b>Resolution:</b> 720x1280\n\n"
            "⚠️ Cannot create real people or copyrighted content\n\n"
            "Choose a model:"
        )
    
    await message.answer(text, reply_markup=get_video_model_keyboard(language))


@router.callback_query(F.data.startswith("video:model:"))
async def callback_video_model(callback: CallbackQuery):
    """Handle video model selection."""
    user = callback.from_user
    model = callback.data.split(":")[2]  # sora-2 or sora-2-pro
    
    # Store model and show duration selection
    await redis_client.set_user_state(user.id, f"video_model:{model}")
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.edit_text(
            f"🎬 <b>Модель: {model}</b>\n\n"
            "Выберите длительность видео:",
            reply_markup=get_video_duration_keyboard(language, model)
        )
    else:
        await callback.message.edit_text(
            f"🎬 <b>Model: {model}</b>\n\n"
            "Choose video duration:",
            reply_markup=get_video_duration_keyboard(language, model)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("video:duration:"))
async def callback_video_duration(callback: CallbackQuery):
    """Handle video duration selection."""
    user = callback.from_user
    duration = int(callback.data.split(":")[2])  # 4, 8, or 12
    
    # Get model from state
    state = await redis_client.get_user_state(user.id)
    if not state or not state.startswith("video_model:"):
        await callback.answer("Сначала выберите модель", show_alert=True)
        return
    
    model = state.split(":")[1]
    
    # Store full config for prompt input
    await redis_client.set_user_state(user.id, f"video_prompt:{model}:{duration}")
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.edit_text(
            f"🎬 <b>Настройки видео:</b>\n"
            f"• Модель: {model}\n"
            f"• Длительность: {duration} сек\n"
            f"• Разрешение: 720x1280\n\n"
            "Теперь опишите видео, которое хотите создать.\n\n"
            "<i>Например: «Кот играет на пианино в джазовом клубе, нуар стиль»</i>\n\n"
            "⚠️ Нельзя создавать реальных людей и копирайтный контент"
        )
    else:
        await callback.message.edit_text(
            f"🎬 <b>Video settings:</b>\n"
            f"• Model: {model}\n"
            f"• Duration: {duration} sec\n"
            f"• Resolution: 720x1280\n\n"
            "Now describe the video you want to create.\n\n"
            "<i>Example: 'A cat playing piano in a jazz club, noir style'</i>\n\n"
            "⚠️ Cannot create real people or copyrighted content"
        )
    
    await callback.answer()


@router.callback_query(F.data == "video:long")
async def callback_video_long(callback: CallbackQuery):
    """Handle long video (premium) selection."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    # Check if user is premium
    from bot.services.subscription_service import subscription_service
    is_premium = await subscription_service.check_premium(user.id)
    
    if not is_premium:
        if language == "ru":
            await callback.answer(
                "💎 Длинные видео доступны только для Premium подписчиков!",
                show_alert=True
            )
        else:
            await callback.answer(
                "💎 Long videos are available for Premium subscribers only!",
                show_alert=True
            )
        return
    
    # Check limits for long video
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.LONG_VIDEO
    )
    
    if not has_limit:
        if language == "ru":
            await callback.answer(
                f"⚠️ Лимит длинных видео исчерпан ({max_limit})",
                show_alert=True
            )
        else:
            await callback.answer(
                f"⚠️ Long video limit reached ({max_limit})",
                show_alert=True
            )
        return
    
    # Set state and ask for prompt
    await redis_client.set_user_state(user.id, "long_video_prompt:sora-2")
    
    if language == "ru":
        remaining = max_limit - current if max_limit != -1 else "∞"
        await callback.message.edit_text(
            "🎥 <b>Длинное видео (Premium)</b>\n\n"
            f"Осталось: {remaining}\n\n"
            "📐 3 клипа по 12 сек = ~36 секунд\n"
            "🤖 Модель: sora-2\n\n"
            "Опишите сюжет для длинного видео.\n\n"
            "<i>Например: «Космический корабль пролетает через пояс астероидов и "
            "приближается к планете с кольцами»</i>"
        )
    else:
        remaining = max_limit - current if max_limit != -1 else "∞"
        await callback.message.edit_text(
            "🎥 <b>Long Video (Premium)</b>\n\n"
            f"Remaining: {remaining}\n\n"
            "📐 3 clips x 12 sec = ~36 seconds\n"
            "🤖 Model: sora-2\n\n"
            "Describe the plot for a long video.\n\n"
            "<i>Example: 'A spaceship flying through an asteroid belt and "
            "approaching a ringed planet'</i>"
        )
    
    await callback.answer()


@router.callback_query(F.data == "video:cancel")
async def callback_video_cancel(callback: CallbackQuery):
    """Handle video generation cancel."""
    user = callback.from_user
    await redis_client.clear_user_state(user.id)
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.edit_text("❌ Генерация видео отменена.")
    else:
        await callback.message.edit_text("❌ Video generation cancelled.")
    
    await callback.answer()


@router.callback_query(F.data == "video:regenerate")
async def callback_video_regenerate(callback: CallbackQuery):
    """Handle video regeneration."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.answer(
            "🎬 <b>Новое видео</b>\n\n"
            "Выберите модель для генерации:",
            reply_markup=get_video_model_keyboard(language)
        )
    else:
        await callback.message.answer(
            "🎬 <b>New Video</b>\n\n"
            "Choose generation model:",
            reply_markup=get_video_model_keyboard(language)
        )
    
    await callback.answer()


@router.callback_query(F.data == "video:remix")
async def callback_video_remix(callback: CallbackQuery):
    """Handle video remix request."""
    user = callback.from_user
    
    # Get video_id from last_video_id stored in Redis
    video_id = await redis_client.client.get(f"user:{user.id}:last_video_id")
    if not video_id:
        language = await user_service.get_user_language(user.id)
        if language == "ru":
            await callback.answer("Видео не найдено", show_alert=True)
        else:
            await callback.answer("Video not found", show_alert=True)
        return
    
    video_id = video_id.decode() if isinstance(video_id, bytes) else video_id
    
    # Store video ID for remix
    await redis_client.set_user_state(user.id, f"video_remix:{video_id}")
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        await callback.message.answer(
            "🎨 <b>Ремикс видео</b>\n\n"
            "Опишите, какие изменения нужно внести:\n\n"
            "<i>Например:\n"
            "• «Измени цвет собаки на золотистый»\n"
            "• «Добавь дождь и драматическое освещение»\n"
            "• «Сделай цветовую палитру более тёплой»</i>\n\n"
            "Лучше вносить одно конкретное изменение за раз."
        )
    else:
        await callback.message.answer(
            "🎨 <b>Video Remix</b>\n\n"
            "Describe what changes to make:\n\n"
            "<i>Examples:\n"
            "• 'Change the dog's color to golden'\n"
            "• 'Add rain and dramatic lighting'\n"
            "• 'Make the color palette warmer'</i>\n\n"
            "It's better to make one specific change at a time."
        )
    
    await callback.answer()


# ============================================
# ФУНКЦИИ ДЛЯ ВЫЗОВА ИЗ text.py
# (НЕ обработчики роутера!)
# ============================================

async def queue_video_generation(
    message: Message,
    user_id: int,
    prompt: str,
    model: str,
    duration: int
):
    """
    Queue video generation task.
    Вызывается из text.py когда пользователь в состоянии video_prompt.
    """
    language = await user_service.get_user_language(user_id)
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user_id, RequestType.VIDEO
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита генерации видео на сегодня ({max_limit}).\n"
                "Лимиты обновятся в полночь UTC.\n\n"
                "💎 Оформите подписку для увеличения лимитов!",
                reply_markup=get_subscription_keyboard(language)
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily video generation limit ({max_limit}).\n"
                "Limits reset at midnight UTC.\n\n"
                "💎 Subscribe to increase your limits!",
                reply_markup=get_subscription_keyboard(language)
            )
        return
    
    # Validate prompt (basic content check)
    prohibited_keywords = [
        "real person", "celebrity", "politician", "public figure",
        "реальный человек", "знаменитость", "политик"
    ]
    
    prompt_lower = prompt.lower()
    for keyword in prohibited_keywords:
        if keyword in prompt_lower:
            if language == "ru":
                await message.answer(
                    "⚠️ Ваш запрос содержит запрещённый контент.\n"
                    "Нельзя создавать видео с реальными людьми."
                )
            else:
                await message.answer(
                    "⚠️ Your request contains prohibited content.\n"
                    "Cannot create videos with real people."
                )
            return
    
    # Queue the task
    try:
        from worker.tasks import queue_video_task
        
        task_id = await queue_video_task(
            user_id=user_id,
            chat_id=message.chat.id,
            prompt=prompt,
            model=model,
            duration=duration
        )
    except Exception as e:
        logger.error(f"Failed to queue video task: {e}")
        task_id = "pending"
    
    # Clear user state
    await redis_client.clear_user_state(user_id)
    
    # Estimate time based on model
    if model == "sora-2":
        time_estimate = "1-3 минуты" if language == "ru" else "1-3 minutes"
    else:  # sora-2-pro
        time_estimate = "5-10 минут" if language == "ru" else "5-10 minutes"
    
    if language == "ru":
        await message.answer(
            "🎬 <b>Видео поставлено в очередь!</b>\n\n"
            f"📝 Промпт: <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n"
            f"🤖 Модель: {model}\n"
            f"⏱ Длительность: {duration} сек\n\n"
            f"⏳ Примерное время: {time_estimate}\n\n"
            "Я отправлю готовое видео, когда оно будет готово."
        )
    else:
        await message.answer(
            "🎬 <b>Video queued!</b>\n\n"
            f"📝 Prompt: <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n"
            f"🤖 Model: {model}\n"
            f"⏱ Duration: {duration} sec\n\n"
            f"⏳ Estimated time: {time_estimate}\n\n"
            "I'll send you the video when it's ready."
        )
    
    logger.info(
        "Video generation queued",
        user_id=user_id,
        task_id=task_id,
        model=model,
        duration=duration
    )


async def queue_video_remix(
    message: Message,
    user_id: int,
    video_id: str,
    change_prompt: str
):
    """
    Queue video remix task.
    Вызывается из text.py когда пользователь в состоянии video_remix.
    """
    language = await user_service.get_user_language(user_id)
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user_id, RequestType.VIDEO
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита генерации видео на сегодня ({max_limit}).\n\n"
                "💎 Оформите подписку для увеличения лимитов!",
                reply_markup=get_subscription_keyboard(language)
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily video generation limit ({max_limit}).\n\n"
                "💎 Subscribe to increase your limits!",
                reply_markup=get_subscription_keyboard(language)
            )
        return
    
    # Queue the remix task
    try:
        from worker.tasks import queue_video_remix_task
        
        task_id = await queue_video_remix_task(
            user_id=user_id,
            chat_id=message.chat.id,
            original_video_id=video_id,
            change_prompt=change_prompt
        )
    except Exception as e:
        logger.error(f"Failed to queue video remix task: {e}")
        task_id = "pending"
    
    # Clear user state
    await redis_client.clear_user_state(user_id)
    
    if language == "ru":
        await message.answer(
            "🎨 <b>Ремикс видео поставлен в очередь!</b>\n\n"
            f"📝 Изменения: <i>{change_prompt[:200]}{'...' if len(change_prompt) > 200 else ''}</i>\n\n"
            "⏳ Примерное время: 2-5 минут\n\n"
            "Я отправлю вам результат, когда будет готово."
        )
    else:
        await message.answer(
            "🎨 <b>Video remix queued!</b>\n\n"
            f"📝 Changes: <i>{change_prompt[:200]}{'...' if len(change_prompt) > 200 else ''}</i>\n\n"
            "⏳ Estimated time: 2-5 minutes\n\n"
            "I'll send you the result when it's ready."
        )
    
    logger.info(
        "Video remix queued",
        user_id=user_id,
        task_id=task_id,
        original_video_id=video_id
    )


async def queue_animate_photo(
    message: Message,
    user_id: int,
    photo_file_id: str,
    prompt: str
):
    """
    Queue image-to-video (animate photo) task.
    Premium only feature.
    """
    language = await user_service.get_user_language(user_id)
    
    # Check limits for video_animate
    has_limit, current, max_limit = await limit_service.check_limit(
        user_id, RequestType.VIDEO_ANIMATE
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Лимит оживления фото исчерпан ({max_limit}).\n\n"
                "💎 Лимит обновится завтра.",
                reply_markup=get_subscription_keyboard(language)
            )
        else:
            await message.answer(
                f"⚠️ Animate photo limit reached ({max_limit}).\n\n"
                "💎 Limit resets tomorrow.",
                reply_markup=get_subscription_keyboard(language)
            )
        return
    
    # Queue the task
    try:
        from worker.tasks import queue_video_task
        
        task_id = await queue_video_task(
            user_id=user_id,
            chat_id=message.chat.id,
            prompt=prompt,
            model="sora-2",
            duration=4,
            reference_image_file_id=photo_file_id
        )
    except Exception as e:
        logger.error(f"Failed to queue animate photo task: {e}")
        task_id = "pending"
    
    # Clear user state
    await redis_client.clear_user_state(user_id)
    
    if language == "ru":
        await message.answer(
            "🎞 <b>Оживление фото в очереди!</b>\n\n"
            f"📝 Промпт: <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n\n"
            "⏳ Примерное время: 1-3 минуты\n\n"
            "Я отправлю готовое видео, когда оно будет готово."
        )
    else:
        await message.answer(
            "🎞 <b>Photo animation queued!</b>\n\n"
            f"📝 Prompt: <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n\n"
            "⏳ Estimated time: 1-3 minutes\n\n"
            "I'll send you the video when it's ready."
        )
    
    logger.info(
        "Animate photo queued",
        user_id=user_id,
        task_id=task_id,
        photo_file_id=photo_file_id
    )


async def queue_long_video_generation(
    message: Message,
    user_id: int,
    prompt: str,
    model: str = "sora-2"
):
    """
    Queue long video generation (stitching multiple clips).
    Premium only feature.
    """
    language = await user_service.get_user_language(user_id)
    
    # Check premium
    from bot.services.subscription_service import subscription_service
    is_premium = await subscription_service.check_premium(user_id)
    
    if not is_premium:
        if language == "ru":
            await message.answer(
                "💎 Генерация длинных видео доступна только для премиум-подписчиков!",
                reply_markup=get_subscription_keyboard(language)
            )
        else:
            await message.answer(
                "💎 Long video generation is available for premium subscribers only!",
                reply_markup=get_subscription_keyboard(language)
            )
        return
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user_id, RequestType.LONG_VIDEO
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Лимит длинных видео исчерпан ({max_limit}).\n\n"
                "💎 Лимит обновится завтра.",
                reply_markup=get_subscription_keyboard(language)
            )
        else:
            await message.answer(
                f"⚠️ Long video limit reached ({max_limit}).\n\n"
                "💎 Limit resets tomorrow.",
                reply_markup=get_subscription_keyboard(language)
            )
        return
    
    # Queue multiple video tasks (3 clips of 12 sec = 36 sec total)
    try:
        from worker.tasks import queue_long_video_task
        
        task_id = await queue_long_video_task(
            user_id=user_id,
            chat_id=message.chat.id,
            prompt=prompt,
            model=model,
            num_clips=3,
            clip_duration=12
        )
    except Exception as e:
        logger.error(f"Failed to queue long video task: {e}")
        task_id = "pending"
    
    # Clear user state
    await redis_client.clear_user_state(user_id)
    
    if language == "ru":
        await message.answer(
            "🎥 <b>Длинное видео в очереди!</b>\n\n"
            f"📝 Промпт: <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n"
            f"🤖 Модель: {model}\n"
            "📐 3 клипа по 12 сек = ~36 секунд\n\n"
            "⏳ Примерное время: 5-15 минут\n\n"
            "Я отправлю готовое видео, когда оно будет готово."
        )
    else:
        await message.answer(
            "🎥 <b>Long video queued!</b>\n\n"
            f"📝 Prompt: <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n"
            f"🤖 Model: {model}\n"
            "📐 3 clips x 12 sec = ~36 seconds\n\n"
            "⏳ Estimated time: 5-15 minutes\n\n"
            "I'll send you the video when it's ready."
        )
    
    logger.info(
        "Long video queued",
        user_id=user_id,
        task_id=task_id,
        model=model
    )
