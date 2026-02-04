"""
Async task definitions for video generation.
Uses arq for task queue management.
"""
import asyncio
from datetime import datetime
from typing import Optional
from arq import create_pool
from arq.connections import RedisSettings, ArqRedis
from sqlalchemy import select, update

from database import async_session_maker
from database.models import VideoTask, VideoTaskStatus, RequestType, RequestStatus
from database.redis_client import redis_client
from bot.services.openai_service import openai_service
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
        
        # Create video in OpenAI
        video_info = await openai_service.create_video(
            prompt=task.prompt,
            model=task.model,
            duration=task.duration_seconds
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
        
        final_status = await openai_service.wait_for_video(
            video_id=video_id,
            poll_interval=settings.video_poll_interval,
            progress_callback=progress_callback
        )
        
        # Download video
        video_bytes = await openai_service.download_video(video_id)
        
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
        
        # Increment usage and record request
        await limit_service.increment_usage(telegram_id, RequestType.VIDEO)
        await limit_service.record_request(
            telegram_id=telegram_id,
            request_type=RequestType.VIDEO,
            prompt=task.prompt[:500],
            model=task.model,
            status=RequestStatus.SUCCESS
        )
        
        logger.info(
            "Video generation completed",
            task_id=task_id,
            video_id=video_id
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
        
        if language == "ru":
            error_text = (
                "❌ <b>Ошибка генерации видео</b>\n\n"
                "К сожалению, не удалось сгенерировать видео.\n"
                "Лимит не списан. Попробуйте ещё раз."
            )
        else:
            error_text = (
                "❌ <b>Video Generation Error</b>\n\n"
                "Unfortunately, video generation failed.\n"
                "Limit not charged. Please try again."
            )
        
        await bot.send_message(
            chat_id=task.chat_id,
            text=error_text,
            parse_mode="HTML"
        )
        
        await bot.session.close()
        
        # Record failed request
        await limit_service.record_request(
            telegram_id=telegram_id,
            request_type=RequestType.VIDEO,
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
        
        # Create remix
        remix_info = await openai_service.remix_video(
            video_id=original_video_id,
            change_prompt=change_prompt
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
        await openai_service.wait_for_video(new_video_id)
        
        # Download and send
        video_bytes = await openai_service.download_video(new_video_id)
        
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


# Worker class for arq
class WorkerSettings:
    """arq worker settings."""
    
    functions = [
        process_video_generation,
        process_video_remix
    ]
    
    redis_settings = get_redis_settings()
    
    max_jobs = settings.worker_concurrency
    job_timeout = 600  # 10 minutes
    
    @staticmethod
    async def on_startup(ctx):
        """Worker startup hook."""
        logger.info("Worker started")
        await redis_client.connect()
    
    @staticmethod
    async def on_shutdown(ctx):
        """Worker shutdown hook."""
        logger.info("Worker shutting down")
        await redis_client.close()
