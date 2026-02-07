"""
Async task definitions for video generation and scheduled reminders.
Uses arq for task queue management.
"""
import asyncio
from datetime import datetime, timedelta, timezone
from typing import Optional
from arq import create_pool, cron
from arq.connections import RedisSettings, ArqRedis
from sqlalchemy import select, update, and_

from database import async_session_maker
from database.models import VideoTask, VideoTaskStatus, RequestType, RequestStatus, Reminder, ReminderType, User
from database.redis_client import redis_client
from bot.services.ai_service import ai_service
from bot.services.limit_service import limit_service
from bot.services.user_service import user_service
from config import settings
import structlog

logger = structlog.get_logger()


# Redis settings for arq
def get_redis_settings() -> RedisSettings:
    """Get Redis settings from URL."""
    # Parse redis://localhost:6379/0
    from urllib.parse import urlparse
    parsed = urlparse(settings.redis_url)
    
    return RedisSettings(
        host=parsed.hostname or 'localhost',
        port=parsed.port or 6379,
        database=int(parsed.path.lstrip('/') or 0)
    )


async def get_arq_pool() -> ArqRedis:
    """Get arq Redis connection pool."""
    return await create_pool(get_redis_settings())


async def queue_video_task(
    user_id: int,
    chat_id: int,
    prompt: str,
    model: str = "sora-2",
    duration: int = 5,
    reference_image_file_id: Optional[str] = None
) -> int:
    """
    Queue a video generation task.
    
    Returns:
        Task ID in database
    """
    # Get database user ID
    user = await user_service.get_user_by_telegram_id(user_id)
    if not user:
        raise ValueError("User not found")
    
    # Create task record in database
    async with async_session_maker() as session:
        task = VideoTask(
            user_id=user.id,
            prompt=prompt,
            model=model,
            status=VideoTaskStatus.QUEUED,
            chat_id=chat_id,
            duration_seconds=duration,
            reference_image_file_id=reference_image_file_id
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id
    
    # Queue the arq job
    pool = await get_arq_pool()
    await pool.enqueue_job(
        'process_video_generation',
        task_id=task_id
    )
    await pool.close()
    
    logger.info(
        "Video task queued",
        task_id=task_id,
        user_id=user_id,
        model=model
    )
    
    return task_id


async def queue_video_remix_task(
    user_id: int,
    chat_id: int,
    original_video_id: str,
    change_prompt: str
) -> int:
    """
    Queue a video remix task.
    
    Returns:
        Task ID in database
    """
    user = await user_service.get_user_by_telegram_id(user_id)
    if not user:
        raise ValueError("User not found")
    
    async with async_session_maker() as session:
        task = VideoTask(
            user_id=user.id,
            openai_video_id=original_video_id,
            prompt=f"REMIX: {change_prompt}",
            model="sora-2",  # Remix uses same model
            status=VideoTaskStatus.QUEUED,
            chat_id=chat_id
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id
    
    pool = await get_arq_pool()
    await pool.enqueue_job(
        'process_video_remix',
        task_id=task_id,
        original_video_id=original_video_id,
        change_prompt=change_prompt
    )
    await pool.close()
    
    logger.info(
        "Video remix task queued",
        task_id=task_id,
        user_id=user_id,
        original_video_id=original_video_id
    )
    
    return task_id


# ============================================
# ARQ Worker Functions
# ============================================

async def process_video_generation(ctx, task_id: int):
    """
    Process video generation task.
    This is the arq worker function.
    """
    logger.info("Processing video generation", task_id=task_id)
    
    # Get task from database
    async with async_session_maker() as session:
        result = await session.execute(
            select(VideoTask).where(VideoTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            logger.error("Task not found", task_id=task_id)
            return
        
        # Get user's telegram_id
        user = await user_service.get_user_by_id(task.user_id)
        if not user:
            logger.error("User not found", user_id=task.user_id)
            return
        
        telegram_id = user.telegram_id
        language = await user_service.get_user_language(telegram_id)
    
    try:
        # Update status to in_progress
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(
                    status=VideoTaskStatus.IN_PROGRESS,
                    started_at=datetime.utcnow()
                )
            )
            await session.commit()
        
        # If task has a reference image (animate photo), download it from Telegram
        input_reference = None
        if task.reference_image_file_id:
            try:
                from aiogram import Bot
                dl_bot = Bot(token=settings.telegram_bot_token)
                file = await dl_bot.get_file(task.reference_image_file_id)
                file_bytes_io = await dl_bot.download_file(file.file_path)
                import io
                input_reference = io.BytesIO(file_bytes_io.read()).getvalue()
                await dl_bot.session.close()
                logger.info(
                    "Reference image downloaded for animate",
                    task_id=task_id,
                    file_id=task.reference_image_file_id,
                    size_bytes=len(input_reference)
                )
            except Exception as img_err:
                logger.error(
                    "Failed to download reference image, proceeding without it",
                    task_id=task_id,
                    error=str(img_err)
                )
                input_reference = None
        
        # Create video using AI service (CometAPI or OpenAI fallback)
        video_info = await ai_service.create_video(
            prompt=task.prompt,
            model=task.model,
            duration=task.duration_seconds,
            telegram_id=telegram_id,
            input_reference=input_reference
        )
        
        video_id = video_info["video_id"]
        
        # Update task with video_id
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(openai_video_id=video_id)
            )
            await session.commit()
        
        # Wait for video completion with progress updates
        async def progress_callback(status_info):
            progress = status_info.get("progress", 0)
            async with async_session_maker() as session:
                await session.execute(
                    update(VideoTask)
                    .where(VideoTask.id == task_id)
                    .values(progress=progress)
                )
                await session.commit()
            
            # Optionally update user message with progress
            # (would need to store message_id)
        
        final_status = await ai_service.wait_for_video(
            video_id=video_id,
            poll_interval=settings.video_poll_interval,
            progress_callback=progress_callback
        )
        
        # Download video
        video_bytes = await ai_service.download_video(video_id)
        
        # Send to user via Telegram
        from aiogram import Bot
        from aiogram.types import BufferedInputFile
        
        bot = Bot(token=settings.telegram_bot_token)
        
        video_file = BufferedInputFile(
            video_bytes,
            filename=f"video_{task_id}.mp4"
        )
        
        # Prepare caption
        prompt_preview = task.prompt[:200] + "..." if len(task.prompt) > 200 else task.prompt
        if language == "ru":
            caption = (
                f"🎬 <b>Видео готово!</b>\n\n"
                f"📝 {prompt_preview}"
            )
        else:
            caption = (
                f"🎬 <b>Video ready!</b>\n\n"
                f"📝 {prompt_preview}"
            )
        
        # Send video
        from bot.keyboards.inline import get_video_actions_keyboard
        
        sent_message = await bot.send_video(
            chat_id=task.chat_id,
            video=video_file,
            caption=caption,
            parse_mode="HTML",
            supports_streaming=True,
            reply_markup=get_video_actions_keyboard(video_id, language)
        )
        
        await bot.session.close()
        
        # Store video_id for potential remix
        await redis_client.store_video_ids(telegram_id, video_id)
        
        # Update task as completed
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(
                    status=VideoTaskStatus.COMPLETED,
                    progress=100,
                    completed_at=datetime.utcnow(),
                    result_file_id=sent_message.video.file_id
                )
            )
            await session.commit()
        
        # Determine request type: VIDEO_ANIMATE if reference image was used, else VIDEO
        req_type = RequestType.VIDEO_ANIMATE if task.reference_image_file_id else RequestType.VIDEO
        
        # Increment usage and record request
        await limit_service.increment_usage(telegram_id, req_type)
        await limit_service.record_request(
            telegram_id=telegram_id,
            request_type=req_type,
            prompt=task.prompt[:500],
            model=task.model,
            status=RequestStatus.SUCCESS
        )
        
        logger.info(
            "Video generation completed",
            task_id=task_id,
            video_id=video_id,
            is_animate=task.reference_image_file_id is not None
        )
        
    except Exception as e:
        logger.error(
            "Video generation failed",
            task_id=task_id,
            error=str(e)
        )
        
        # Update task as failed
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(
                    status=VideoTaskStatus.FAILED,
                    error_message=str(e),
                    completed_at=datetime.utcnow()
                )
            )
            await session.commit()
        
        # Notify user of failure
        from aiogram import Bot
        
        bot = Bot(token=settings.telegram_bot_token)
        
        is_animate = task.reference_image_file_id is not None
        if language == "ru":
            action_name = "оживления фото" if is_animate else "генерации видео"
            action_verb = "оживить фото" if is_animate else "сгенерировать видео"
            error_text = (
                f"❌ <b>Ошибка {action_name}</b>\n\n"
                f"К сожалению, не удалось {action_verb}.\n"
                "Лимит не списан. Попробуйте ещё раз."
            )
        else:
            error_text = (
                f"❌ <b>{'Photo Animation' if is_animate else 'Video Generation'} Error</b>\n\n"
                f"Unfortunately, {'photo animation' if is_animate else 'video generation'} failed.\n"
                "Limit not charged. Please try again."
            )
        
        await bot.send_message(
            chat_id=task.chat_id,
            text=error_text,
            parse_mode="HTML"
        )
        
        await bot.session.close()
        
        # Record failed request
        req_type = RequestType.VIDEO_ANIMATE if task.reference_image_file_id else RequestType.VIDEO
        await limit_service.record_request(
            telegram_id=telegram_id,
            request_type=req_type,
            prompt=task.prompt[:500],
            model=task.model,
            status=RequestStatus.FAILED,
            error_message=str(e)
        )


async def process_video_remix(
    ctx,
    task_id: int,
    original_video_id: str,
    change_prompt: str
):
    """
    Process video remix task.
    """
    logger.info(
        "Processing video remix",
        task_id=task_id,
        original_video_id=original_video_id
    )
    
    # Similar to process_video_generation but with remix API
    async with async_session_maker() as session:
        result = await session.execute(
            select(VideoTask).where(VideoTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            logger.error("Task not found", task_id=task_id)
            return
        
        user = await user_service.get_user_by_id(task.user_id)
        telegram_id = user.telegram_id
        language = await user_service.get_user_language(telegram_id)
    
    try:
        # Update status
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(
                    status=VideoTaskStatus.IN_PROGRESS,
                    started_at=datetime.utcnow()
                )
            )
            await session.commit()
        
        # Create remix (note: remix may not be supported by CometAPI, using fallback)
        # If ai_service doesn't have remix_video, this will need a fallback
        if hasattr(ai_service, 'remix_video'):
            remix_info = await ai_service.remix_video(
                video_id=original_video_id,
                change_prompt=change_prompt
            )
        else:
            # Fallback: create new video with remix prompt
            remix_info = await ai_service.create_video(
                prompt=f"Based on previous video, apply changes: {change_prompt}",
                model="sora-2",
                duration=5,
                telegram_id=telegram_id
            )
        
        new_video_id = remix_info["video_id"]
        
        # Update task
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(openai_video_id=new_video_id)
            )
            await session.commit()
        
        # Wait for completion
        await ai_service.wait_for_video(new_video_id)
        
        # Download and send
        video_bytes = await ai_service.download_video(new_video_id)
        
        from aiogram import Bot
        from aiogram.types import BufferedInputFile
        from bot.keyboards.inline import get_video_actions_keyboard
        
        bot = Bot(token=settings.telegram_bot_token)
        
        video_file = BufferedInputFile(
            video_bytes,
            filename=f"remix_{task_id}.mp4"
        )
        
        if language == "ru":
            caption = (
                f"🎨 <b>Ремикс готов!</b>\n\n"
                f"📝 {change_prompt[:200]}"
            )
        else:
            caption = (
                f"🎨 <b>Remix ready!</b>\n\n"
                f"📝 {change_prompt[:200]}"
            )
        
        sent_message = await bot.send_video(
            chat_id=task.chat_id,
            video=video_file,
            caption=caption,
            parse_mode="HTML",
            supports_streaming=True,
            reply_markup=get_video_actions_keyboard(new_video_id, language)
        )
        
        await bot.session.close()
        
        # Update task
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(
                    status=VideoTaskStatus.COMPLETED,
                    progress=100,
                    completed_at=datetime.utcnow(),
                    result_file_id=sent_message.video.file_id
                )
            )
            await session.commit()
        
        # Increment usage
        await limit_service.increment_usage(telegram_id, RequestType.VIDEO)
        await limit_service.record_request(
            telegram_id=telegram_id,
            request_type=RequestType.VIDEO,
            prompt=f"REMIX: {change_prompt[:400]}",
            model="sora-2",
            status=RequestStatus.SUCCESS
        )
        
        # Store new video_id
        await redis_client.store_video_ids(telegram_id, new_video_id)
        
        logger.info(
            "Video remix completed",
            task_id=task_id,
            new_video_id=new_video_id
        )
        
    except Exception as e:
        logger.error(
            "Video remix failed",
            task_id=task_id,
            error=str(e)
        )
        
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(
                    status=VideoTaskStatus.FAILED,
                    error_message=str(e),
                    completed_at=datetime.utcnow()
                )
            )
            await session.commit()
        
        from aiogram import Bot
        
        bot = Bot(token=settings.telegram_bot_token)
        
        if language == "ru":
            await bot.send_message(
                chat_id=task.chat_id,
                text="❌ <b>Ошибка ремикса видео</b>\n\nПопробуйте ещё раз.",
                parse_mode="HTML"
            )
        else:
            await bot.send_message(
                chat_id=task.chat_id,
                text="❌ <b>Video remix error</b>\n\nPlease try again.",
                parse_mode="HTML"
            )
        
        await bot.session.close()


# ============================================
# Long Video (stitching clips)
# ============================================

async def queue_long_video_task(
    user_id: int,
    chat_id: int,
    prompt: str,
    model: str = "sora-2",
    num_clips: int = 3,
    clip_duration: int = 12
) -> int:
    """
    Queue a long video generation task (stitch multiple clips).
    Premium only.
    
    Returns:
        Task ID in database
    """
    user = await user_service.get_user_by_telegram_id(user_id)
    if not user:
        raise ValueError("User not found")
    
    # Create parent task record in database
    async with async_session_maker() as session:
        task = VideoTask(
            user_id=user.id,
            prompt=f"LONG_VIDEO({num_clips}x{clip_duration}s): {prompt}",
            model=model,
            status=VideoTaskStatus.QUEUED,
            chat_id=chat_id,
            duration_seconds=num_clips * clip_duration
        )
        session.add(task)
        await session.commit()
        await session.refresh(task)
        task_id = task.id
    
    # Queue the arq job
    pool = await get_arq_pool()
    await pool.enqueue_job(
        'process_long_video',
        task_id=task_id,
        prompt=prompt,
        model=model,
        num_clips=num_clips,
        clip_duration=clip_duration
    )
    await pool.close()
    
    logger.info(
        "Long video task queued",
        task_id=task_id,
        user_id=user_id,
        model=model,
        num_clips=num_clips,
        clip_duration=clip_duration
    )
    
    return task_id


async def process_long_video(
    ctx,
    task_id: int,
    prompt: str,
    model: str = "sora-2",
    num_clips: int = 3,
    clip_duration: int = 12
):
    """
    Process long video generation by creating multiple clips and stitching them.
    Each clip gets a continuation prompt so the narrative flows.
    """
    logger.info("Processing long video", task_id=task_id, num_clips=num_clips)
    
    # Get task info
    async with async_session_maker() as session:
        result = await session.execute(
            select(VideoTask).where(VideoTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            logger.error("Task not found", task_id=task_id)
            return
        
        user = await user_service.get_user_by_id(task.user_id)
        if not user:
            logger.error("User not found", user_id=task.user_id)
            return
        
        telegram_id = user.telegram_id
        language = await user_service.get_user_language(telegram_id)
    
    from aiogram import Bot
    from aiogram.types import BufferedInputFile
    
    bot = Bot(token=settings.telegram_bot_token)
    
    try:
        # Update status to in_progress
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(
                    status=VideoTaskStatus.IN_PROGRESS,
                    started_at=datetime.utcnow()
                )
            )
            await session.commit()
        
        # Send progress message
        if language == "ru":
            progress_msg = await bot.send_message(
                chat_id=task.chat_id,
                text=f"🎥 <b>Генерация длинного видео</b>\n\n"
                     f"📐 {num_clips} клипов по {clip_duration} сек\n"
                     f"⏳ Клип 1/{num_clips}...",
                parse_mode="HTML"
            )
        else:
            progress_msg = await bot.send_message(
                chat_id=task.chat_id,
                text=f"🎥 <b>Long Video Generation</b>\n\n"
                     f"📐 {num_clips} clips x {clip_duration} sec\n"
                     f"⏳ Clip 1/{num_clips}...",
                parse_mode="HTML"
            )
        
        # Generate clips sequentially with continuation prompts
        clip_video_bytes = []
        
        for i in range(num_clips):
            # Build continuation prompt
            if i == 0:
                clip_prompt = prompt
            else:
                clip_prompt = (
                    f"Continue the video seamlessly from the previous scene. "
                    f"Part {i+1}/{num_clips}: {prompt}"
                )
            
            # Update progress
            try:
                if language == "ru":
                    await bot.edit_message_text(
                        chat_id=task.chat_id,
                        message_id=progress_msg.message_id,
                        text=f"🎥 <b>Генерация длинного видео</b>\n\n"
                             f"📐 {num_clips} клипов по {clip_duration} сек\n"
                             f"⏳ Клип {i+1}/{num_clips}...",
                        parse_mode="HTML"
                    )
                else:
                    await bot.edit_message_text(
                        chat_id=task.chat_id,
                        message_id=progress_msg.message_id,
                        text=f"🎥 <b>Long Video Generation</b>\n\n"
                             f"📐 {num_clips} clips x {clip_duration} sec\n"
                             f"⏳ Clip {i+1}/{num_clips}...",
                        parse_mode="HTML"
                    )
            except Exception:
                pass
            
            # Create video clip
            video_info = await ai_service.create_video(
                prompt=clip_prompt,
                model=model,
                duration=clip_duration,
                telegram_id=telegram_id
            )
            
            video_id = video_info["video_id"]
            
            # Wait for completion
            await ai_service.wait_for_video(
                video_id=video_id,
                poll_interval=settings.video_poll_interval
            )
            
            # Download clip
            video_bytes = await ai_service.download_video(video_id)
            clip_video_bytes.append(video_bytes)
            
            # Update task progress
            progress = int(((i + 1) / num_clips) * 100)
            async with async_session_maker() as session:
                await session.execute(
                    update(VideoTask)
                    .where(VideoTask.id == task_id)
                    .values(progress=progress)
                )
                await session.commit()
            
            logger.info(f"Clip {i+1}/{num_clips} completed", task_id=task_id)
        
        # Try to concatenate clips with ffmpeg, fallback to sending individually
        try:
            import subprocess
            import tempfile
            import os
            
            with tempfile.TemporaryDirectory() as tmpdir:
                # Write clips to files
                clip_paths = []
                for idx, clip_bytes in enumerate(clip_video_bytes):
                    clip_path = os.path.join(tmpdir, f"clip_{idx}.mp4")
                    with open(clip_path, 'wb') as f:
                        f.write(clip_bytes)
                    clip_paths.append(clip_path)
                
                # Create concat file
                concat_file = os.path.join(tmpdir, "concat.txt")
                with open(concat_file, 'w') as f:
                    for cp in clip_paths:
                        f.write(f"file '{cp}'\n")
                
                # Concatenate with ffmpeg
                output_path = os.path.join(tmpdir, "long_video.mp4")
                result = subprocess.run(
                    [
                        'ffmpeg', '-f', 'concat', '-safe', '0',
                        '-i', concat_file,
                        '-c', 'copy',
                        '-y', output_path
                    ],
                    capture_output=True, timeout=120
                )
                
                if result.returncode == 0 and os.path.exists(output_path):
                    with open(output_path, 'rb') as f:
                        final_video = f.read()
                    
                    # Delete progress message
                    try:
                        await bot.delete_message(
                            chat_id=task.chat_id,
                            message_id=progress_msg.message_id
                        )
                    except Exception:
                        pass
                    
                    # Send single concatenated video
                    video_file = BufferedInputFile(
                        final_video,
                        filename=f"long_video_{task_id}.mp4"
                    )
                    
                    prompt_preview = prompt[:200] + "..." if len(prompt) > 200 else prompt
                    if language == "ru":
                        caption = (
                            f"🎥 <b>Длинное видео готово!</b>\n\n"
                            f"📝 {prompt_preview}\n"
                            f"📐 {num_clips} клипов = ~{num_clips * clip_duration} сек"
                        )
                    else:
                        caption = (
                            f"🎥 <b>Long video ready!</b>\n\n"
                            f"📝 {prompt_preview}\n"
                            f"📐 {num_clips} clips = ~{num_clips * clip_duration} sec"
                        )
                    
                    sent_message = await bot.send_video(
                        chat_id=task.chat_id,
                        video=video_file,
                        caption=caption,
                        parse_mode="HTML",
                        supports_streaming=True
                    )
                    
                    # Update task as completed
                    async with async_session_maker() as session:
                        await session.execute(
                            update(VideoTask)
                            .where(VideoTask.id == task_id)
                            .values(
                                status=VideoTaskStatus.COMPLETED,
                                progress=100,
                                completed_at=datetime.utcnow(),
                                result_file_id=sent_message.video.file_id
                            )
                        )
                        await session.commit()
                else:
                    raise Exception("ffmpeg concat failed")
                
        except Exception as concat_error:
            logger.warning(f"ffmpeg concat failed, sending clips individually: {concat_error}")
            
            # Delete progress message
            try:
                await bot.delete_message(
                    chat_id=task.chat_id,
                    message_id=progress_msg.message_id
                )
            except Exception:
                pass
            
            # Fallback: send clips individually
            for idx, clip_bytes in enumerate(clip_video_bytes):
                video_file = BufferedInputFile(
                    clip_bytes,
                    filename=f"clip_{idx+1}_{task_id}.mp4"
                )
                
                if language == "ru":
                    caption = f"🎥 Клип {idx+1}/{num_clips}"
                else:
                    caption = f"🎥 Clip {idx+1}/{num_clips}"
                
                await bot.send_video(
                    chat_id=task.chat_id,
                    video=video_file,
                    caption=caption,
                    parse_mode="HTML",
                    supports_streaming=True
                )
            
            # Update task as completed
            async with async_session_maker() as session:
                await session.execute(
                    update(VideoTask)
                    .where(VideoTask.id == task_id)
                    .values(
                        status=VideoTaskStatus.COMPLETED,
                        progress=100,
                        completed_at=datetime.utcnow()
                    )
                )
                await session.commit()
        
        # Increment usage and record request
        await limit_service.increment_usage(telegram_id, RequestType.LONG_VIDEO)
        await limit_service.record_request(
            telegram_id=telegram_id,
            request_type=RequestType.LONG_VIDEO,
            prompt=prompt[:500],
            model=model,
            status=RequestStatus.SUCCESS
        )
        
        logger.info("Long video generation completed", task_id=task_id)
        
    except Exception as e:
        logger.error("Long video generation failed", task_id=task_id, error=str(e))
        
        # Update task as failed
        async with async_session_maker() as session:
            await session.execute(
                update(VideoTask)
                .where(VideoTask.id == task_id)
                .values(
                    status=VideoTaskStatus.FAILED,
                    error_message=str(e),
                    completed_at=datetime.utcnow()
                )
            )
            await session.commit()
        
        if language == "ru":
            error_text = (
                "❌ <b>Ошибка генерации длинного видео</b>\n\n"
                "Лимит не списан. Попробуйте ещё раз."
            )
        else:
            error_text = (
                "❌ <b>Long Video Generation Error</b>\n\n"
                "Limit not charged. Please try again."
            )
        
        await bot.send_message(
            chat_id=task.chat_id,
            text=error_text,
            parse_mode="HTML"
        )
        
        # Record failed request
        await limit_service.record_request(
            telegram_id=telegram_id,
            request_type=RequestType.LONG_VIDEO,
            prompt=prompt[:500],
            model=model,
            status=RequestStatus.FAILED,
            error_message=str(e)
        )
    
    finally:
        await bot.session.close()


# ============================================
# Reminder/Alarm Scheduler
# ============================================

async def check_reminders(ctx):
    """
    Check for due reminders and alarms and send notifications.
    This runs every minute via cron.
    """
    logger.debug("Checking for due reminders...")
    
    now = datetime.now(timezone.utc)
    # Check reminders due in the next minute
    check_until = now + timedelta(minutes=1)
    
    async with async_session_maker() as session:
        # Get all active reminders that are due
        result = await session.execute(
            select(Reminder, User)
            .join(User, Reminder.user_id == User.id)
            .where(and_(
                Reminder.is_active == True,
                Reminder.is_sent == False,
                Reminder.remind_at <= check_until
            ))
        )
        
        reminders = result.all()
        
        if not reminders:
            return
        
        logger.info(f"Found {len(reminders)} due reminders")
        
        from aiogram import Bot
        bot = Bot(token=settings.telegram_bot_token)
        
        for reminder, user in reminders:
            try:
                # Get user language
                user_lang = user.settings.get("language", "ru") if user.settings else "ru"
                
                # Format message based on reminder type
                if reminder.type == ReminderType.ALARM:
                    if user_lang == "ru":
                        text = (
                            f"⏰ <b>Будильник!</b>\n\n"
                            f"🔔 {reminder.title}"
                        )
                    else:
                        text = (
                            f"⏰ <b>Alarm!</b>\n\n"
                            f"🔔 {reminder.title}"
                        )
                elif reminder.type == ReminderType.CHANNEL_EVENT:
                    if user_lang == "ru":
                        text = (
                            f"🔔 <b>Напоминание о событии!</b>\n\n"
                            f"📌 {reminder.title}"
                        )
                        if reminder.description:
                            text += f"\n\n{reminder.description}"
                    else:
                        text = (
                            f"🔔 <b>Event Reminder!</b>\n\n"
                            f"📌 {reminder.title}"
                        )
                        if reminder.description:
                            text += f"\n\n{reminder.description}"
                else:
                    if user_lang == "ru":
                        text = f"🔔 <b>Напоминание:</b>\n\n{reminder.title}"
                    else:
                        text = f"🔔 <b>Reminder:</b>\n\n{reminder.title}"
                
                # Send notification
                await bot.send_message(
                    chat_id=user.telegram_id,
                    text=text,
                    parse_mode="HTML"
                )
                
                logger.info(
                    "Reminder sent",
                    reminder_id=reminder.id,
                    user_id=user.telegram_id,
                    type=reminder.type.value
                )
                
                # Update reminder status
                if reminder.recurrence == "daily":
                    # For daily alarms, reschedule for next day in user's timezone
                    user_tz_name = user.settings.get("timezone", "Europe/Moscow") if user.settings else "Europe/Moscow"
                    try:
                        import zoneinfo
                        user_tz = zoneinfo.ZoneInfo(user_tz_name)
                    except Exception:
                        user_tz = timezone.utc
                    
                    # Convert current remind_at to user's TZ, add 1 day, convert back to UTC
                    remind_in_user_tz = reminder.remind_at.astimezone(user_tz)
                    next_time_user = remind_in_user_tz + timedelta(days=1)
                    next_time = next_time_user.astimezone(timezone.utc)
                    
                    await session.execute(
                        update(Reminder)
                        .where(Reminder.id == reminder.id)
                        .values(
                            remind_at=next_time,
                            last_triggered_at=now
                        )
                    )
                else:
                    # One-time reminder, mark as sent
                    await session.execute(
                        update(Reminder)
                        .where(Reminder.id == reminder.id)
                        .values(
                            is_sent=True,
                            last_triggered_at=now
                        )
                    )
                
                await session.commit()
                
            except Exception as e:
                logger.error(
                    "Failed to send reminder",
                    reminder_id=reminder.id,
                    error=str(e)
                )
        
        await bot.session.close()


# Worker class for arq
class WorkerSettings:
    """arq worker settings."""
    
    functions = [
        process_video_generation,
        process_video_remix,
        process_long_video,
        check_reminders
    ]
    
    # Cron jobs - check reminders every minute
    cron_jobs = [
        cron(check_reminders, minute={0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 59})
    ]
    
    redis_settings = get_redis_settings()
    
    max_jobs = settings.worker_concurrency
    job_timeout = 600  # 10 minutes
    
    @staticmethod
    async def on_startup(ctx):
        """Worker startup hook."""
        logger.info("Worker started with reminder scheduler")
        await redis_client.connect()
    
    @staticmethod
    async def on_shutdown(ctx):
        """Worker shutdown hook."""
        logger.info("Worker shutting down")
        await redis_client.close()
