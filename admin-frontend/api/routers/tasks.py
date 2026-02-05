"""
Tasks router.
Handles task queue monitoring and management.
"""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload

from api.services.auth_service import get_current_admin, require_role
from database import async_session_maker
from database.models import VideoTask, VideoTaskStatus, User, Admin
from datetime import datetime
from pydantic import BaseModel
from typing import List
import structlog

logger = structlog.get_logger()
router = APIRouter()


class TaskResponse(BaseModel):
    """Video task response model."""
    id: int
    user_telegram_id: int
    username: Optional[str] = None
    prompt: str
    model: str
    status: str
    progress: int
    error_message: Optional[str] = None
    duration_seconds: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """Task list response."""
    tasks: List[TaskResponse]
    total: int


class QueueStats(BaseModel):
    """Queue statistics."""
    queued_count: int
    in_progress_count: int
    completed_today: int
    failed_today: int
    average_wait_time_seconds: Optional[float] = None
    average_processing_time_seconds: Optional[float] = None


@router.get("/queue/stats", response_model=QueueStats)
async def get_queue_stats(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get task queue statistics."""
    async with async_session_maker() as session:
        from sqlalchemy import cast, Date
        from datetime import date
        
        today = date.today()
        
        # Queued count
        queued_result = await session.execute(
            select(func.count(VideoTask.id))
            .where(VideoTask.status == VideoTaskStatus.QUEUED)
        )
        queued_count = queued_result.scalar() or 0
        
        # In progress count
        in_progress_result = await session.execute(
            select(func.count(VideoTask.id))
            .where(VideoTask.status == VideoTaskStatus.IN_PROGRESS)
        )
        in_progress_count = in_progress_result.scalar() or 0
        
        # Completed today
        completed_result = await session.execute(
            select(func.count(VideoTask.id))
            .where(and_(
                VideoTask.status == VideoTaskStatus.COMPLETED,
                cast(VideoTask.completed_at, Date) == today
            ))
        )
        completed_today = completed_result.scalar() or 0
        
        # Failed today
        failed_result = await session.execute(
            select(func.count(VideoTask.id))
            .where(and_(
                VideoTask.status == VideoTaskStatus.FAILED,
                cast(VideoTask.completed_at, Date) == today
            ))
        )
        failed_today = failed_result.scalar() or 0
        
        # Average wait time (for completed tasks today)
        wait_time_result = await session.execute(
            select(
                func.avg(
                    func.extract('epoch', VideoTask.started_at) - 
                    func.extract('epoch', VideoTask.created_at)
                )
            )
            .where(and_(
                VideoTask.status == VideoTaskStatus.COMPLETED,
                VideoTask.started_at.isnot(None),
                cast(VideoTask.completed_at, Date) == today
            ))
        )
        average_wait_time = wait_time_result.scalar()
        
        # Average processing time
        processing_time_result = await session.execute(
            select(
                func.avg(
                    func.extract('epoch', VideoTask.completed_at) - 
                    func.extract('epoch', VideoTask.started_at)
                )
            )
            .where(and_(
                VideoTask.status == VideoTaskStatus.COMPLETED,
                VideoTask.started_at.isnot(None),
                VideoTask.completed_at.isnot(None),
                cast(VideoTask.completed_at, Date) == today
            ))
        )
        average_processing_time = processing_time_result.scalar()
        
        return QueueStats(
            queued_count=queued_count,
            in_progress_count=in_progress_count,
            completed_today=completed_today,
            failed_today=failed_today,
            average_wait_time_seconds=float(average_wait_time) if average_wait_time else None,
            average_processing_time_seconds=float(average_processing_time) if average_processing_time else None
        )


@router.get("/queue", response_model=TaskListResponse)
async def get_queue_tasks(
    status_filter: Optional[str] = Query(None, pattern="^(queued|in_progress|completed|failed)$"),
    limit: int = Query(50, ge=1, le=200),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get tasks in queue."""
    async with async_session_maker() as session:
        query = select(VideoTask, User).join(User, VideoTask.user_id == User.id)
        count_query = select(func.count(VideoTask.id))
        
        if status_filter:
            status_enum = VideoTaskStatus(status_filter)
            query = query.where(VideoTask.status == status_enum)
            count_query = count_query.where(VideoTask.status == status_enum)
        else:
            # Default: show queued and in_progress
            query = query.where(VideoTask.status.in_([
                VideoTaskStatus.QUEUED,
                VideoTaskStatus.IN_PROGRESS
            ]))
            count_query = count_query.where(VideoTask.status.in_([
                VideoTaskStatus.QUEUED,
                VideoTaskStatus.IN_PROGRESS
            ]))
        
        # Order: in_progress first, then by created_at
        query = query.order_by(
            VideoTask.status.desc(),
            VideoTask.created_at.asc()
        ).limit(limit)
        
        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get tasks
        result = await session.execute(query)
        
        tasks = [
            TaskResponse(
                id=task.id,
                user_telegram_id=user.telegram_id,
                username=user.username,
                prompt=task.prompt,
                model=task.model,
                status=task.status.value,
                progress=task.progress,
                error_message=task.error_message,
                duration_seconds=task.duration_seconds,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at
            )
            for task, user in result
        ]
        
        return TaskListResponse(tasks=tasks, total=total)


@router.get("/history", response_model=TaskListResponse)
async def get_task_history(
    status_filter: Optional[str] = Query(None, pattern="^(completed|failed)$"),
    limit: int = Query(50, ge=1, le=200),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get completed/failed tasks history."""
    async with async_session_maker() as session:
        query = select(VideoTask, User).join(User, VideoTask.user_id == User.id)
        count_query = select(func.count(VideoTask.id))
        
        # Filter to completed/failed
        completed_statuses = [VideoTaskStatus.COMPLETED, VideoTaskStatus.FAILED]
        
        if status_filter:
            status_enum = VideoTaskStatus(status_filter)
            query = query.where(VideoTask.status == status_enum)
            count_query = count_query.where(VideoTask.status == status_enum)
        else:
            query = query.where(VideoTask.status.in_(completed_statuses))
            count_query = count_query.where(VideoTask.status.in_(completed_statuses))
        
        query = query.order_by(VideoTask.completed_at.desc()).limit(limit)
        
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        result = await session.execute(query)
        
        tasks = [
            TaskResponse(
                id=task.id,
                user_telegram_id=user.telegram_id,
                username=user.username,
                prompt=task.prompt,
                model=task.model,
                status=task.status.value,
                progress=task.progress,
                error_message=task.error_message,
                duration_seconds=task.duration_seconds,
                created_at=task.created_at,
                started_at=task.started_at,
                completed_at=task.completed_at
            )
            for task, user in result
        ]
        
        return TaskListResponse(tasks=tasks, total=total)


@router.delete("/queue/{task_id}")
async def cancel_task(
    task_id: int,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """
    Cancel a queued task.
    Can only cancel tasks in 'queued' status.
    """
    async with async_session_maker() as session:
        result = await session.execute(
            select(VideoTask).where(VideoTask.id == task_id)
        )
        task = result.scalar_one_or_none()
        
        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        if task.status != VideoTaskStatus.QUEUED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel task in '{task.status.value}' status"
            )
        
        # Update to failed with cancellation message
        task.status = VideoTaskStatus.FAILED
        task.error_message = f"Cancelled by admin: {current_admin.username}"
        task.completed_at = datetime.utcnow()
        
        await session.commit()
        
        logger.info(
            "Task cancelled",
            task_id=task_id,
            admin=current_admin.username
        )
        
        return {"message": "Task cancelled"}


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: int,
    current_admin: Admin = Depends(get_current_admin)
):
    """Get specific task details."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(VideoTask, User)
            .join(User, VideoTask.user_id == User.id)
            .where(VideoTask.id == task_id)
        )
        row = result.first()
        
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Task not found"
            )
        
        task, user = row
        
        return TaskResponse(
            id=task.id,
            user_telegram_id=user.telegram_id,
            username=user.username,
            prompt=task.prompt,
            model=task.model,
            status=task.status.value,
            progress=task.progress,
            error_message=task.error_message,
            duration_seconds=task.duration_seconds,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at
        )
