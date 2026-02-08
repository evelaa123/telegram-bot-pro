"""
Dry-run test for long video pipeline.
Mocks CometAPI calls to test the full flow without spending credits.
"""
import asyncio
import os
import sys

# Подставляем мок вместо реального API
from unittest.mock import AsyncMock, MagicMock, patch

async def main():
    # Фейковые данные
    fake_video_id = "fake_video_test_123"
    fake_video_bytes = b'\x00' * 1024  # 1KB фейковое "видео"
    
    # Мокаем ai_service
    from bot.services.ai_service import ai_service
    
    # create_video возвращает video_id мгновенно
    ai_service.create_video = AsyncMock(return_value={
        "video_id": fake_video_id,
        "status": "queued",
        "model": "sora-2",
        "duration": 12
    })
    
    # wait_for_video — мгновенно "готово"
    ai_service.wait_for_video = AsyncMock(return_value={
        "video_id": fake_video_id,
        "status": "completed",
        "progress": 100
    })
    
    # download_video — возвращает фейковые байты
    ai_service.download_video = AsyncMock(return_value=fake_video_bytes)
    
    print("=== Mocks set up ===")
    print("create_video -> instant fake_video_id")
    print("wait_for_video -> instant completed")
    print("download_video -> 1KB fake bytes")
    print()
    
    # Теперь запускаем process_long_video напрямую
    from worker.tasks import process_long_video
    
    # Нужен task_id из базы — используем существующий или создаём новый
    # Сброс задачи 14 обратно в QUEUED для теста:
    from database import async_session_maker
    from database.models import VideoTask, VideoTaskStatus
    from sqlalchemy import update
    
    async with async_session_maker() as session:
        await session.execute(
            update(VideoTask)
            .where(VideoTask.id == 14)
            .values(
                status=VideoTaskStatus.QUEUED,
                error_message=None,
                started_at=None,
                completed_at=None,
                progress=0
            )
        )
        await session.commit()
    
    print("Task 14 reset to QUEUED")
    print("Running process_long_video...")
    print()
    
    # Запуск
    ctx = {}  # arq context (не используется)
    await process_long_video(
        ctx,
        task_id=14,
        prompt="Космический корабль пролетает через пояс астероидов и приближается к планете с кольцами",
        model="sora-2",
        num_clips=3,
        clip_duration=12
    )
    
    print()
    print("=== DONE ===")
    
    # Проверяем что вызовы были
    print(f"create_video called {ai_service.create_video.call_count} times")
    print(f"wait_for_video called {ai_service.wait_for_video.call_count} times")
    print(f"download_video called {ai_service.download_video.call_count} times")


if __name__ == "__main__":
    asyncio.run(main())