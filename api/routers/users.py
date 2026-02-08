"""
Users router.
Handles user management endpoints.
"""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query

from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload

from api.schemas.user import (
    UserResponse, UserListResponse, UserUpdate, 
    UserLimitsUpdate, UserRequestHistory, UserRequestHistoryResponse,
    SendMessageRequest, GrantPremiumRequest
)
from api.services.auth_service import get_current_admin, require_role
from database import async_session_maker
from database.models import User, Request, Admin
from bot.services.user_service import user_service
from config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter()


@router.get("", response_model=UserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    search: Optional[str] = None,
    is_blocked: Optional[bool] = None,
    has_custom_limits: Optional[bool] = None,
    current_admin: Admin = Depends(get_current_admin)
):
    """
    List users with pagination and filters.
    """
    async with async_session_maker() as session:
        # Base query
        query = select(User)
        count_query = select(func.count(User.id))
        
        # Apply filters
        if search:
            # ИСПРАВЛЕНО: безопасный поиск
            search_pattern = f"%{search}%"
            
            # Проверяем, является ли поиск числом (для telegram_id)
            search_filter = (
                User.username.ilike(search_pattern) |
                User.first_name.ilike(search_pattern) |
                User.last_name.ilike(search_pattern)
            )
            
            # Если поиск - число, добавляем поиск по telegram_id
            if search.isdigit():
                search_filter = search_filter | (User.telegram_id == int(search))
            
            query = query.where(search_filter)
            count_query = count_query.where(search_filter)
        
        if is_blocked is not None:
            query = query.where(User.is_blocked == is_blocked)
            count_query = count_query.where(User.is_blocked == is_blocked)
        
        if has_custom_limits is not None:
            if has_custom_limits:
                query = query.where(User.custom_limits.isnot(None))
                count_query = count_query.where(User.custom_limits.isnot(None))
            else:
                query = query.where(User.custom_limits.is_(None))
                count_query = count_query.where(User.custom_limits.is_(None))
        
        # Get total count
        total_result = await session.execute(count_query)
        total = total_result.scalar()
        
        # Pagination
        offset = (page - 1) * page_size
        query = query.order_by(desc(User.last_active_at)).offset(offset).limit(page_size)
        
        # Execute
        result = await session.execute(query)
        users = result.scalars().all()
        
        # Get request counts and build responses
        user_responses = []
        from datetime import timezone
        now = datetime.now(timezone.utc) if hasattr(datetime, 'now') else __import__('datetime').datetime.now(__import__('datetime').timezone.utc)
        
        for user in users:
            count_result = await session.execute(
                select(func.count(Request.id)).where(Request.user_id == user.id)
            )
            request_count = count_result.scalar() or 0
            
            # Build user response with subscription info
            has_active = False
            if user.subscription_type.value == "premium" and user.subscription_expires_at:
                has_active = user.subscription_expires_at > now
            
            user_data = UserResponse(
                id=user.id,
                telegram_id=user.telegram_id,
                username=user.username,
                first_name=user.first_name,
                last_name=user.last_name,
                language_code=user.language_code,
                is_blocked=user.is_blocked,
                custom_limits=user.custom_limits,
                settings=user.settings,
                created_at=user.created_at,
                updated_at=user.updated_at,
                last_active_at=user.last_active_at,
                subscription_type=user.subscription_type.value,
                subscription_expires_at=user.subscription_expires_at,
                has_active_subscription=has_active,
                total_requests=request_count
            )
            user_responses.append(user_data)
        
        total_pages = (total + page_size - 1) // page_size
        
        return UserListResponse(
            users=user_responses,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


@router.get("/{telegram_id}", response_model=UserResponse)
async def get_user(
    telegram_id: int,
    current_admin: Admin = Depends(get_current_admin)
):
    """Get user by Telegram ID."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Get request count
    async with async_session_maker() as session:
        count_result = await session.execute(
            select(func.count(Request.id)).where(Request.user_id == user.id)
        )
        request_count = count_result.scalar() or 0
    
    from datetime import timezone as tz
    now = datetime.now(tz.utc)
    
    has_active = False
    if user.subscription_type.value == "premium" and user.subscription_expires_at:
        has_active = user.subscription_expires_at > now
    
    user_data = UserResponse(
        id=user.id,
        telegram_id=user.telegram_id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
        is_blocked=user.is_blocked,
        custom_limits=user.custom_limits,
        settings=user.settings,
        created_at=user.created_at,
        updated_at=user.updated_at,
        last_active_at=user.last_active_at,
        subscription_type=user.subscription_type.value,
        subscription_expires_at=user.subscription_expires_at,
        has_active_subscription=has_active,
        total_requests=request_count
    )
    
    return user_data


@router.patch("/{telegram_id}", response_model=UserResponse)
async def update_user(
    telegram_id: int,
    update_data: UserUpdate,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Update user settings."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    async with async_session_maker() as session:
        # Get user for update
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one()
        
        if update_data.is_blocked is not None:
            user.is_blocked = update_data.is_blocked
            logger.info(
                "User block status changed",
                telegram_id=telegram_id,
                is_blocked=update_data.is_blocked,
                admin=current_admin.username
            )
        
        if update_data.settings is not None:
            current_settings = user.settings or {}
            current_settings.update(update_data.settings)
            user.settings = current_settings
        
        await session.commit()
        await session.refresh(user)
    
    return UserResponse.model_validate(user)


@router.put("/{telegram_id}/limits", response_model=UserResponse)
async def update_user_limits(
    telegram_id: int,
    limits: UserLimitsUpdate,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Update user custom limits."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Build limits dict
    limits_dict = {}
    for field in ["text", "image", "video", "voice", "document", "presentation", "video_animate", "long_video"]:
        value = getattr(limits, field)
        if value is not None:
            limits_dict[field] = value
    
    if limits_dict:
        await user_service.set_custom_limits(telegram_id, limits_dict)
        logger.info(
            "User limits updated",
            telegram_id=telegram_id,
            limits=limits_dict,
            admin=current_admin.username
        )
    
    user = await user_service.get_user_by_telegram_id(telegram_id)
    return UserResponse.model_validate(user)


@router.delete("/{telegram_id}/limits")
async def reset_user_limits(
    telegram_id: int,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Reset user custom limits to global defaults."""
    success = await user_service.clear_custom_limits(telegram_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(
        "User limits reset",
        telegram_id=telegram_id,
        admin=current_admin.username
    )
    
    return {"message": "Limits reset to defaults"}


@router.post("/{telegram_id}/premium")
async def grant_premium(
    telegram_id: int,
    request: GrantPremiumRequest,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Grant or extend premium subscription for a user."""
    from bot.services.subscription_service import subscription_service
    
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        await subscription_service.activate_subscription(
            telegram_id=telegram_id,
            months=request.months,
            payment_id=f"admin_grant_{telegram_id}_{int(datetime.now().timestamp())}",
            payment_provider="admin_grant",
            amount_rub=0
        )
        
        # Notify user via Telegram about their new premium status
        try:
            from aiogram import Bot
            bot = Bot(token=settings.telegram_bot_token)
            
            # Get user language
            language = "ru"
            try:
                language = await user_service.get_user_language(telegram_id)
            except Exception:
                pass
            
            if language == "ru":
                notify_text = (
                    "🎉 <b>Поздравляем!</b>\n\n"
                    f"Вам выдана подписка <b>Premium</b> на <b>{request.months}</b> мес.!\n\n"
                    "✅ Теперь вам доступны:\n"
                    "• Безлимитные текстовые запросы\n"
                    "• Безлимитная генерация изображений\n"
                    "• Оживление фото (image-to-video)\n"
                    "• Длинные видео (до 36 сек)\n"
                    "• И многое другое!\n\n"
                    "Используйте /limits чтобы увидеть ваши лимиты."
                )
            else:
                notify_text = (
                    "🎉 <b>Congratulations!</b>\n\n"
                    f"You've been granted <b>Premium</b> subscription for <b>{request.months}</b> month(s)!\n\n"
                    "✅ You now have access to:\n"
                    "• Unlimited text requests\n"
                    "• Unlimited image generation\n"
                    "• Photo animation (image-to-video)\n"
                    "• Long videos (up to 36 sec)\n"
                    "• And much more!\n\n"
                    "Use /limits to see your limits."
                )
            
            await bot.send_message(
                chat_id=telegram_id,
                text=notify_text,
                parse_mode="HTML"
            )
            await bot.session.close()
        except Exception as notify_err:
            logger.warning("Failed to notify user about premium grant", error=str(notify_err))
        
        logger.info(
            "Premium granted by admin",
            telegram_id=telegram_id,
            months=request.months,
            admin=current_admin.username
        )
        
        return {"message": f"Premium granted for {request.months} month(s)"}
        
    except Exception as e:
        logger.error("Failed to grant premium", error=str(e), telegram_id=telegram_id)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to grant premium: {str(e)}"
        )


@router.delete("/{telegram_id}/premium")
async def revoke_premium(
    telegram_id: int,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Revoke premium subscription from a user."""
    from database.models import SubscriptionType
    
    user = await user_service.get_user_by_telegram_id(telegram_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    async with async_session_maker() as session:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one()
        user.subscription_type = SubscriptionType.FREE
        user.subscription_expires_at = None
        await session.commit()
    
    # Notify user via Telegram about premium revocation
    try:
        from aiogram import Bot as AioBot
        bot = AioBot(token=settings.telegram_bot_token)
        
        language = "ru"
        try:
            language = await user_service.get_user_language(telegram_id)
        except Exception:
            pass
        
        if language == "ru":
            notify_text = (
                "ℹ️ <b>Изменение подписки</b>\n\n"
                "Ваша подписка Premium была отменена.\n"
                "Теперь действуют лимиты бесплатного плана.\n\n"
                "Используйте /limits чтобы увидеть ваши текущие лимиты."
            )
        else:
            notify_text = (
                "ℹ️ <b>Subscription Update</b>\n\n"
                "Your Premium subscription has been revoked.\n"
                "Free plan limits now apply.\n\n"
                "Use /limits to see your current limits."
            )
        
        await bot.send_message(
            chat_id=telegram_id,
            text=notify_text,
            parse_mode="HTML"
        )
        await bot.session.close()
    except Exception as notify_err:
        logger.warning("Failed to notify user about premium revocation", error=str(notify_err))
    
    logger.info(
        "Premium revoked by admin",
        telegram_id=telegram_id,
        admin=current_admin.username
    )
    
    return {"message": "Premium revoked", "subscription_type": "free"}


@router.post("/{telegram_id}/block")
async def block_user(
    telegram_id: int,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Block user."""
    success = await user_service.block_user(telegram_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(
        "User blocked",
        telegram_id=telegram_id,
        admin=current_admin.username
    )
    
    return {"message": "User blocked"}


@router.post("/{telegram_id}/unblock")
async def unblock_user(
    telegram_id: int,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Unblock user."""
    success = await user_service.unblock_user(telegram_id)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    logger.info(
        "User unblocked",
        telegram_id=telegram_id,
        admin=current_admin.username
    )
    
    return {"message": "User unblocked"}


@router.get("/{telegram_id}/requests", response_model=UserRequestHistoryResponse)
async def get_user_requests(
    telegram_id: int,
    limit: int = Query(100, ge=1, le=500),
    current_admin: Admin = Depends(get_current_admin)
):
    """Get user's request history."""
    user = await user_service.get_user_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    async with async_session_maker() as session:
        # Get requests
        result = await session.execute(
            select(Request)
            .where(Request.user_id == user.id)
            .order_by(desc(Request.created_at))
            .limit(limit)
        )
        requests = result.scalars().all()
        
        # Get total count
        count_result = await session.execute(
            select(func.count(Request.id)).where(Request.user_id == user.id)
        )
        total = count_result.scalar() or 0
    
    request_history = [
        UserRequestHistory(
            id=r.id,
            type=r.type.value,
            prompt=r.prompt,
            response_preview=r.response_preview,
            model=r.model,
            status=r.status.value,
            cost_usd=float(r.cost_usd) if r.cost_usd else None,
            duration_ms=r.duration_ms,
            created_at=r.created_at
        )
        for r in requests
    ]
    
    return UserRequestHistoryResponse(
        requests=request_history,
        total=total
    )


@router.post("/{telegram_id}/message")
async def send_message_to_user(
    telegram_id: int,
    request: SendMessageRequest,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Send message to user via bot."""
    from aiogram import Bot
    
    user = await user_service.get_user_by_telegram_id(telegram_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    try:
        bot = Bot(token=settings.telegram_bot_token)
        
        await bot.send_message(
            chat_id=telegram_id,
            text=f"📢 <b>Сообщение от администрации:</b>\n\n{request.message}",
            parse_mode="HTML"
        )
        
        await bot.session.close()
        
        logger.info(
            "Message sent to user",
            telegram_id=telegram_id,
            admin=current_admin.username
        )
        
        return {"message": "Message sent successfully"}
        
    except Exception as e:
        logger.error(
            "Failed to send message",
            telegram_id=telegram_id,
            error=str(e)
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to send message: {str(e)}"
        )
