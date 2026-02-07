"""
Support router.
Handles tech support messaging between admins and users.
"""
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel

from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import selectinload

from api.services.auth_service import get_current_admin, require_role
from database import async_session_maker
from database.models import SupportMessage, User, Admin
from config import settings
import structlog

logger = structlog.get_logger()
router = APIRouter()


# ============================================
# Schemas
# ============================================

class SupportMessageResponse(BaseModel):
    """Support message response."""
    id: int
    user_id: int
    user_telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    message: str
    is_from_user: bool
    admin_username: Optional[str]
    is_read: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class SupportConversation(BaseModel):
    """Support conversation with a user."""
    user_id: int
    user_telegram_id: int
    username: Optional[str]
    first_name: Optional[str]
    last_message: str
    last_message_at: datetime
    unread_count: int
    has_subscription: bool


class SupportConversationsResponse(BaseModel):
    """List of support conversations."""
    conversations: List[SupportConversation]
    total_unread: int


class SendMessageRequest(BaseModel):
    """Request to send message to user."""
    user_id: int
    message: str


class SendMessageResponse(BaseModel):
    """Response after sending message."""
    success: bool
    message_id: int
    sent_to_telegram: bool


# ============================================
# Endpoints
# ============================================

@router.get("/conversations", response_model=SupportConversationsResponse)
async def get_support_conversations(
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get all support conversations grouped by user.
    Returns list of users with their last message and unread count.
    """
    async with async_session_maker() as session:
        # Get all users who have support messages
        # Subquery for last message per user
        from sqlalchemy import desc
        
        result = await session.execute(
            select(
                User.id,
                User.telegram_id,
                User.username,
                User.first_name,
                User.subscription_type,
                User.subscription_expires_at
            )
            .join(SupportMessage, SupportMessage.user_id == User.id)
            .group_by(User.id)
            .order_by(desc(func.max(SupportMessage.created_at)))
        )
        
        users = list(result)
        
        conversations = []
        total_unread = 0
        
        for user_row in users:
            user_id = user_row.id
            
            # Get last message for this user
            last_msg_result = await session.execute(
                select(SupportMessage)
                .where(SupportMessage.user_id == user_id)
                .order_by(desc(SupportMessage.created_at))
                .limit(1)
            )
            last_msg = last_msg_result.scalar_one_or_none()
            
            # Get unread count
            unread_result = await session.execute(
                select(func.count(SupportMessage.id))
                .where(and_(
                    SupportMessage.user_id == user_id,
                    SupportMessage.is_from_user == True,
                    SupportMessage.is_read == False
                ))
            )
            unread_count = unread_result.scalar() or 0
            total_unread += unread_count
            
            # Check subscription status
            has_subscription = False
            if user_row.subscription_type and user_row.subscription_type.value == "premium":
                if user_row.subscription_expires_at:
                    from datetime import timezone
                    has_subscription = user_row.subscription_expires_at > datetime.now(timezone.utc)
            
            if last_msg:
                conversations.append(SupportConversation(
                    user_id=user_id,
                    user_telegram_id=user_row.telegram_id,
                    username=user_row.username,
                    first_name=user_row.first_name,
                    last_message=last_msg.message[:100] + ("..." if len(last_msg.message) > 100 else ""),
                    last_message_at=last_msg.created_at,
                    unread_count=unread_count,
                    has_subscription=has_subscription
                ))
        
        return SupportConversationsResponse(
            conversations=conversations,
            total_unread=total_unread
        )


@router.get("/conversation/{user_id}", response_model=List[SupportMessageResponse])
async def get_conversation_messages(
    user_id: int,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Get messages for a specific conversation with a user.
    """
    async with async_session_maker() as session:
        # Get user info
        user_result = await session.execute(
            select(User).where(User.id == user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Get messages
        messages_result = await session.execute(
            select(SupportMessage, Admin)
            .outerjoin(Admin, SupportMessage.admin_id == Admin.id)
            .where(SupportMessage.user_id == user_id)
            .order_by(SupportMessage.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        
        messages = []
        for msg, admin in messages_result:
            messages.append(SupportMessageResponse(
                id=msg.id,
                user_id=msg.user_id,
                user_telegram_id=user.telegram_id,
                username=user.username,
                first_name=user.first_name,
                message=msg.message,
                is_from_user=msg.is_from_user,
                admin_username=admin.username if admin else None,
                is_read=msg.is_read,
                created_at=msg.created_at
            ))
        
        # Mark messages as read
        await session.execute(
            SupportMessage.__table__.update()
            .where(and_(
                SupportMessage.user_id == user_id,
                SupportMessage.is_from_user == True,
                SupportMessage.is_read == False
            ))
            .values(is_read=True)
        )
        await session.commit()
        
        # Return in chronological order
        messages.reverse()
        
        return messages


@router.post("/send", response_model=SendMessageResponse)
async def send_message_to_user(
    request: SendMessageRequest,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """
    Send a message from admin to user.
    The message is saved to DB and sent via Telegram.
    """
    async with async_session_maker() as session:
        # Get user
        user_result = await session.execute(
            select(User).where(User.id == request.user_id)
        )
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Save message to DB
        support_msg = SupportMessage(
            user_id=user.id,
            message=request.message,
            is_from_user=False,
            admin_id=current_admin.id,
            is_read=True  # Admin messages are "read" by definition
        )
        
        session.add(support_msg)
        await session.commit()
        await session.refresh(support_msg)
        
        # Try to send via Telegram
        sent_to_telegram = False
        try:
            from aiogram import Bot
            bot = Bot(token=settings.telegram_bot_token)
            
            # Get user language for localized header
            user_lang = user.settings.get("language", "ru") if user.settings else "ru"
            
            if user_lang == "ru":
                header = "📨 <b>Ответ от поддержки:</b>\n\n"
            else:
                header = "📨 <b>Support Response:</b>\n\n"
            
            await bot.send_message(
                chat_id=user.telegram_id,
                text=f"{header}{request.message}",
                parse_mode="HTML"
            )
            
            await bot.session.close()
            sent_to_telegram = True
            
            logger.info(
                "Support message sent to user",
                user_id=user.id,
                telegram_id=user.telegram_id,
                admin=current_admin.username
            )
            
        except Exception as e:
            logger.error(
                "Failed to send support message via Telegram",
                error=str(e),
                user_id=user.id
            )
        
        return SendMessageResponse(
            success=True,
            message_id=support_msg.id,
            sent_to_telegram=sent_to_telegram
        )


@router.get("/unread-count")
async def get_unread_count(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get total unread support messages count."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(func.count(SupportMessage.id))
            .where(and_(
                SupportMessage.is_from_user == True,
                SupportMessage.is_read == False
            ))
        )
        count = result.scalar() or 0
        
        return {"unread_count": count}


@router.get("/photo/{file_id}")
async def get_support_photo(
    file_id: str,
    current_admin: Admin = Depends(get_current_admin)
):
    """
    Proxy endpoint to download Telegram photos by file_id.
    This solves the problem of expired Telegram file URLs in the support chat.
    """
    from fastapi.responses import StreamingResponse
    import io
    
    try:
        from aiogram import Bot
        bot = Bot(token=settings.telegram_bot_token)
        
        # Get file info from Telegram
        file = await bot.get_file(file_id)
        # Download file data
        file_data = await bot.download_file(file.file_path)
        
        await bot.session.close()
        
        # Read bytes from the file-like object
        if hasattr(file_data, 'read'):
            image_bytes = file_data.read()
        else:
            image_bytes = file_data
        
        # Determine content type from file path
        content_type = "image/jpeg"
        if file.file_path and file.file_path.endswith(".png"):
            content_type = "image/png"
        
        return StreamingResponse(
            io.BytesIO(image_bytes),
            media_type=content_type,
            headers={
                "Cache-Control": "public, max-age=86400",
                "Content-Disposition": f"inline; filename=photo.jpg"
            }
        )
        
    except Exception as e:
        logger.error("Failed to fetch support photo", error=str(e), file_id=file_id)
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Photo not found or expired: {str(e)}"
        )
