"""User schemas."""
from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class UserResponse(BaseModel):
    """User response model."""
    id: int
    telegram_id: int
    username: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    language_code: Optional[str] = None
    is_blocked: bool
    custom_limits: Optional[Dict[str, int]] = None
    settings: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    last_active_at: Optional[datetime] = None
    
    # Computed fields
    total_requests: int = 0
    
    class Config:
        from_attributes = True


class UserListResponse(BaseModel):
    """Paginated user list response."""
    users: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class UserUpdate(BaseModel):
    """User update request."""
    is_blocked: Optional[bool] = None
    settings: Optional[Dict[str, Any]] = None


class UserLimitsUpdate(BaseModel):
    """User limits update request."""
    text: Optional[int] = Field(None, ge=0)
    image: Optional[int] = Field(None, ge=0)
    video: Optional[int] = Field(None, ge=0)
    voice: Optional[int] = Field(None, ge=0)
    document: Optional[int] = Field(None, ge=0)


class UserRequestHistory(BaseModel):
    """User request history item."""
    id: int
    type: str
    prompt: Optional[str] = None
    response_preview: Optional[str] = None
    model: Optional[str] = None
    status: str
    cost_usd: Optional[float] = None
    duration_ms: Optional[int] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class UserRequestHistoryResponse(BaseModel):
    """User request history response."""
    requests: List[UserRequestHistory]
    total: int


class SendMessageRequest(BaseModel):
    """Send message to user request."""
    message: str = Field(..., min_length=1, max_length=4096)
