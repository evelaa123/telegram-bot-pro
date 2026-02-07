"""
Database models for Telegram AI Assistant.
Defines all SQLAlchemy ORM models.
"""
import enum
from datetime import datetime, date
from decimal import Decimal
from typing import Optional, Dict, Any, List

from sqlalchemy import (
    String, Integer, BigInteger, Text, Boolean, DateTime, Date,
    Numeric, Enum, ForeignKey, Index, UniqueConstraint, JSON
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from database.connection import Base


class RequestType(enum.Enum):
    """Types of user requests."""
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    VOICE = "voice"
    DOCUMENT = "document"
    PRESENTATION = "presentation"
    VIDEO_ANIMATE = "video_animate"
    LONG_VIDEO = "long_video"


class SubscriptionType(enum.Enum):
    """User subscription types."""
    FREE = "free"
    PREMIUM = "premium"


class ReminderType(enum.Enum):
    """Types of reminders."""
    DIARY = "diary"          # Personal diary entry
    CHANNEL_EVENT = "channel_event"  # Channel event reminder
    ALARM = "alarm"          # Alarm/wake up


class RequestStatus(enum.Enum):
    """Status of requests."""
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VideoTaskStatus(enum.Enum):
    """Status of video generation tasks."""
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


class AdminRole(enum.Enum):
    """Admin roles with different permissions."""
    SUPERADMIN = "superadmin"
    ADMIN = "admin"
    VIEWER = "viewer"


class User(Base):
    """
    Telegram user model.
    Stores user information, settings, subscription, and custom limits.
    """
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    first_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    language_code: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Subscription fields
    subscription_type: Mapped[SubscriptionType] = mapped_column(
        Enum(SubscriptionType),
        default=SubscriptionType.FREE,
        nullable=False
    )
    subscription_expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Custom limits override global defaults (JSONB)
    custom_limits: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    
    # User settings (JSONB)
    # Supported settings:
    # - image_style: DALL-E style (vivid, natural)
    # - auto_voice_process: Auto-process voice messages
    # - language: UI language (ru, en)
    # - timezone: User timezone for reminders
    settings: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON, 
        nullable=True,
        default=lambda: {
            "image_style": "vivid",
            "auto_voice_process": False,
            "language": "ru",
            "timezone": "Europe/Moscow"
        }
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), 
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    last_active_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    requests: Mapped[List["Request"]] = relationship(
        "Request",
        back_populates="user",
        lazy="selectin"
    )
    daily_limits: Mapped[List["DailyLimit"]] = relationship(
        "DailyLimit",
        back_populates="user",
        lazy="selectin"
    )
    video_tasks: Mapped[List["VideoTask"]] = relationship(
        "VideoTask",
        back_populates="user",
        lazy="selectin"
    )
    diary_entries: Mapped[List["DiaryEntry"]] = relationship(
        "DiaryEntry",
        back_populates="user",
        lazy="selectin"
    )
    reminders: Mapped[List["Reminder"]] = relationship(
        "Reminder",
        back_populates="user",
        lazy="selectin"
    )
    subscriptions: Mapped[List["Subscription"]] = relationship(
        "Subscription",
        back_populates="user",
        lazy="selectin"
    )
    
    @property
    def is_premium(self) -> bool:
        """Check if user has active premium subscription."""
        if self.subscription_type == SubscriptionType.FREE:
            return False
        if self.subscription_expires_at is None:
            return False
        from datetime import timezone
        return self.subscription_expires_at > datetime.now(timezone.utc)
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, telegram_id={self.telegram_id}, username={self.username})>"


class Request(Base):
    """
    User request log.
    Stores all API requests for analytics and billing.
    """
    __tablename__ = "requests"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    type: Mapped[RequestType] = mapped_column(Enum(RequestType), nullable=False, index=True)
    prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    response_preview: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    
    tokens_input: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    tokens_output: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    
    model: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    status: Mapped[RequestStatus] = mapped_column(
        Enum(RequestStatus), 
        default=RequestStatus.SUCCESS,
        nullable=False
    )
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="requests")
    
    __table_args__ = (
        Index("ix_requests_user_type_date", "user_id", "type", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Request(id={self.id}, user_id={self.user_id}, type={self.type.value})>"


class DailyLimit(Base):
    """
    Daily usage limits per user.
    Tracks usage counters that reset daily.
    """
    __tablename__ = "daily_limits"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    
    text_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    image_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    video_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    voice_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    document_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    presentation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    video_animate_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    long_video_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="daily_limits")
    
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_user_date"),
        Index("ix_daily_limits_user_date", "user_id", "date"),
    )
    
    def __repr__(self) -> str:
        return f"<DailyLimit(user_id={self.user_id}, date={self.date})>"


class VideoTask(Base):
    """
    Video generation task queue.
    Tracks async video generation jobs.
    """
    __tablename__ = "video_tasks"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    openai_video_id: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(50), default="sora-2", nullable=False)
    
    status: Mapped[VideoTaskStatus] = mapped_column(
        Enum(VideoTaskStatus),
        default=VideoTaskStatus.QUEUED,
        nullable=False,
        index=True
    )
    progress: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    
    # Telegram file_id of the result
    result_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # Chat info for sending result
    chat_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Video parameters
    duration_seconds: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    resolution: Mapped[str] = mapped_column(String(20), default="1280x720", nullable=False)
    reference_image_file_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="video_tasks")
    
    def __repr__(self) -> str:
        return f"<VideoTask(id={self.id}, status={self.status.value})>"


class Admin(Base):
    """
    Admin panel users.
    Separate from Telegram users.
    """
    __tablename__ = "admins"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    
    role: Mapped[AdminRole] = mapped_column(
        Enum(AdminRole),
        default=AdminRole.VIEWER,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    last_login_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Updated settings
    settings_updated: Mapped[List["Setting"]] = relationship(
        "Setting",
        back_populates="updated_by_admin",
        foreign_keys="Setting.updated_by"
    )
    
    def __repr__(self) -> str:
        return f"<Admin(id={self.id}, username={self.username}, role={self.role.value})>"


class Setting(Base):
    """
    Application settings.
    Key-value store for dynamic configuration.
    """
    __tablename__ = "settings"
    
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    value: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    updated_by: Mapped[Optional[int]] = mapped_column(
        Integer,
        ForeignKey("admins.id"),
        nullable=True
    )
    
    # Relationships
    updated_by_admin: Mapped[Optional["Admin"]] = relationship(
        "Admin",
        back_populates="settings_updated",
        foreign_keys=[updated_by]
    )
    
    def __repr__(self) -> str:
        return f"<Setting(key={self.key})>"


class DiaryEntry(Base):
    """
    User diary entries for the personal assistant feature.
    """
    __tablename__ = "diary_entries"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Optional tags/categories as JSON array
    tags: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    
    # Mood tracking (1-5 scale)
    mood: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="diary_entries")
    
    __table_args__ = (
        Index("ix_diary_user_date", "user_id", "date"),
    )
    
    def __repr__(self) -> str:
        return f"<DiaryEntry(id={self.id}, user_id={self.user_id}, date={self.date})>"


class Reminder(Base):
    """
    User reminders including alarms, channel events, and personal tasks.
    """
    __tablename__ = "reminders"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    type: Mapped[ReminderType] = mapped_column(Enum(ReminderType), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    # When to remind
    remind_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True
    )
    
    # For recurring reminders (e.g., daily alarm)
    # Format: "daily", "weekly:1,3,5" (Mon, Wed, Fri), "monthly:15"
    recurrence: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    
    # Channel post reference (for channel event reminders)
    channel_message_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    channel_id: Mapped[Optional[int]] = mapped_column(BigInteger, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_sent: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    last_triggered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="reminders")
    
    __table_args__ = (
        Index("ix_reminders_user_time", "user_id", "remind_at"),
        Index("ix_reminders_active_time", "is_active", "remind_at"),
    )
    
    def __repr__(self) -> str:
        return f"<Reminder(id={self.id}, type={self.type.value}, remind_at={self.remind_at})>"


class Subscription(Base):
    """
    Subscription payment records.
    Tracks all premium subscription purchases.
    """
    __tablename__ = "subscriptions"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Payment details
    payment_id: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    payment_provider: Mapped[str] = mapped_column(String(50), nullable=False)  # yookassa, robokassa, etc.
    amount_rub: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    
    # Subscription period
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    cancelled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="subscriptions")
    
    __table_args__ = (
        Index("ix_subscriptions_user_active", "user_id", "is_active"),
    )
    
    def __repr__(self) -> str:
        return f"<Subscription(id={self.id}, user_id={self.user_id}, expires_at={self.expires_at})>"


class SupportMessage(Base):
    """
    Support chat messages between users and admins.
    Enables tech support functionality.
    """
    __tablename__ = "support_messages"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    
    # Message content
    message: Mapped[str] = mapped_column(Text, nullable=False)
    
    # Direction: True = user -> admin, False = admin -> user
    is_from_user: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    # Admin who responded (if admin message)
    admin_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("admins.id"), nullable=True)
    
    # Status
    is_read: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    # Relationships
    user: Mapped["User"] = relationship("User", foreign_keys=[user_id])
    admin: Mapped[Optional["Admin"]] = relationship("Admin", foreign_keys=[admin_id])
    
    __table_args__ = (
        Index("ix_support_messages_user_created", "user_id", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<SupportMessage(id={self.id}, user_id={self.user_id}, is_from_user={self.is_from_user})>"


class APIUsageLog(Base):
    """
    Detailed API usage log for cost tracking and analytics.
    Tracks every API call with cost information.
    """
    __tablename__ = "api_usage_logs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    
    provider: Mapped[str] = mapped_column(String(50), nullable=False, index=True)  # cometapi, gigachat
    model: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    endpoint: Mapped[str] = mapped_column(String(100), nullable=False)  # chat, image, video, audio
    
    # Token/unit counts
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Cost tracking
    cost_usd: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 6), nullable=True)
    cost_rub: Mapped[Optional[Decimal]] = mapped_column(Numeric(10, 4), nullable=True)
    
    # Response time
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    
    # Status
    success: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    
    __table_args__ = (
        Index("ix_api_usage_provider_date", "provider", "created_at"),
        Index("ix_api_usage_model_date", "model", "created_at"),
    )
    
    def __repr__(self) -> str:
        return f"<APIUsageLog(id={self.id}, provider={self.provider}, model={self.model})>"
