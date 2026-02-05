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
from bot.keyboards.inline import get_video_model_keyboard, get_video_duration_keyboard
from database.redis_client import redis_client
from database.models import RequestType
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
                "Лимиты обновятся в полночь UTC."
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily video generation limit ({max_limit}).\n"
                "Limits reset at midnight UTC."
            )
        return
    
    if language == "ru":
        text = (
            "🎬 <b>Генерация видео</b>\n\n"
            f"Осталось сегодня: {max_limit - current} из {max_limit}\n\n"
            "<b>Режимы:</b>\n"
            "• <b>Быстрый</b> — генерация за 1-3 мин\n"
            "• <b>Качество</b> — высокое качество (5-10 мин)\n\n"
            "⚠️ <b>Ограничения:</b>\n"
            "• Нельзя создавать реальных людей\n"
            "• Нельзя использовать копирайтный контент\n\n"
            "Выберите режим:"
        )
    else:
        text = (
            "🎬 <b>Video Generation</b>\n\n"
            f"Remaining today: {max_limit - current} of {max_limit}\n\n"
            "<b>Modes:</b>\n"
            "• <b>Fast</b> — generation in 1-3 min\n"
            "• <b>Quality</b> — high quality (5-10 min)\n\n"
            "⚠️ <b>Restrictions:</b>\n"
            "• Cannot create real people\n"
            "• Cannot use copyrighted content\n\n"
            "Choose a mode:"
        )
    
    await message.answer(text, reply_markup=get_video_model_keyboard(language))


@router.callback_query(F.data.startswith("video:model:"))
async def callback_video_model(callback: CallbackQuery):
    """Handle video model selection."""
    user = callback.from_user
    model = callback.data.split(":")[2]  # sora-2-all or sora-2-pro-all
    
    # Store model and show duration selection
    await redis_client.set_user_state(user.id, f"video_model:{model}")
    
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        mode_name = "Быстрый" if model == "sora-2-all" else "Высокое качество"
        await callback.message.edit_text(
            f"🎬 <b>Режим: {mode_name}</b>\n\n"
            "Выберите длительность видео:",
            reply_markup=get_video_duration_keyboard(language, model)
        )
    else:
        mode_name = "Fast" if model == "sora-2-all" else "High Quality"
        await callback.message.edit_text(
            f"🎬 <b>Mode: {mode_name}</b>\n\n"
            "Choose video duration:",
            reply_markup=get_video_duration_keyboard(language, model)
        )
    
    await callback.answer()


@router.callback_query(F.data.startswith("video:duration:"))
async def callback_video_duration(callback: CallbackQuery):
    """Handle video duration selection."""
    user = callback.from_user
    duration = int(callback.data.split(":")[2])  # 10, 15, or 25
    
    # Get model from state
    state = await redis_client.get_user_state(user.id)
    if not state or not state.startswith("video_model:"):
        await callback.answer("Сначала выберите модель", show_alert=True)
        return
    
    model = state.split(":")[1]
    
    # Store full config for prompt input
    await redis_client.set_user_state(user.id, f"video_prompt:{model}:{duration}")
    
    language = await user_service.get_user_language(user.id)
    
    # Calculate estimated price
    price = "$0.08" if model == "sora-2-all" else "$0.80"
    
    if language == "ru":
        mode_name = "Быстрый" if model == "sora-2-all" else "Высокое качество"
        await callback.message.edit_text(
            f"🎬 <b>Настройки видео:</b>\n"
            f"• Режим: {mode_name}\n"
            f"• Длительность: {duration} сек\n"
            f"• Разрешение: 1280x720\n"
            f"• Стоимость: {price}\n\n"
            "Теперь опишите видео, которое хотите создать.\n\n"
            "<i>Например: «Кот играет на пианино в джазовом клубе, нуар стиль»</i>\n\n"
            "⚠️ <b>Ограничения:</b>\n"
            "• Нельзя создавать реальных людей\n"
            "• Нельзя использовать копирайтный контент\n"
            "• Только для аудитории 18+"
        )
    else:
        mode_name = "Fast" if model == "sora-2-all" else "High Quality"
        await callback.message.edit_text(
            f"🎬 <b>Video settings:</b>\n"
            f"• Mode: {mode_name}\n"
            f"• Duration: {duration} sec\n"
            f"• Resolution: 1280x720\n"
            f"• Cost: {price}\n\n"
            "Now describe the video you want to create.\n\n"
            "<i>Example: 'A cat playing piano in a jazz club, noir style'</i>\n\n"
            "⚠️ <b>Restrictions:</b>\n"
            "• Cannot create real people\n"
            "• Cannot use copyrighted content\n"
            "• 18+ audience only"
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


@router.callback_query(F.data.startswith("video:remix:"))
async def callback_video_remix(callback: CallbackQuery):
    """Handle video remix request."""
    user = callback.from_user
    video_id = callback.data.split(":")[2]
    
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
                "Лимиты обновятся в полночь UTC."
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily video generation limit ({max_limit}).\n"
                "Limits reset at midnight UTC."
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
    if model == "sora-2-all":
        time_estimate = "1-3 минуты" if language == "ru" else "1-3 minutes"
    else:
        time_estimate = "5-10 минут" if language == "ru" else "5-10 minutes"
    
    mode_name_ru = "Быстрый" if model == "sora-2-all" else "Высокое качество"
    mode_name_en = "Fast" if model == "sora-2-all" else "High Quality"
    
    if language == "ru":
        await message.answer(
            "🎬 <b>Видео поставлено в очередь на генерацию!</b>\n\n"
            f"📝 Промпт: <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n"
            f"🤖 Режим: {mode_name_ru}\n"
            f"⏱ Длительность: {duration} сек\n\n"
            f"⏳ Примерное время генерации: {time_estimate}\n\n"
            "Я отправлю вам готовое видео, когда оно будет готово.\n"
            "Вы можете продолжать пользоваться ботом."
        )
    else:
        await message.answer(
            "🎬 <b>Video queued for generation!</b>\n\n"
            f"📝 Prompt: <i>{prompt[:200]}{'...' if len(prompt) > 200 else ''}</i>\n"
            f"🤖 Mode: {mode_name_en}\n"
            f"⏱ Duration: {duration} sec\n\n"
            f"⏳ Estimated time: {time_estimate}\n\n"
            "I'll send you the finished video when it's ready.\n"
            "You can continue using the bot."
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
                f"⚠️ Вы достигли лимита генерации видео на сегодня ({max_limit})."
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily video generation limit ({max_limit})."
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
