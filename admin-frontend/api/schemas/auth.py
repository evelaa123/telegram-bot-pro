"""Authentication schemas."""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class Token(BaseModel):
    """JWT token response."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Token payload data."""
    username: Optional[str] = None
    role: Optional[str] = None


class AdminLogin(BaseModel):
    """Admin login request."""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=6)


class AdminCreate(BaseModel):
    """Admin creation request."""
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    role: str = Field(default="viewer", pattern="^(superadmin|admin|viewer)$")


class AdminResponse(BaseModel):
    """Admin response model."""
    id: int
    username: str
    role: str
    is_active: bool
    last_login_at: Optional[datetime] = None
    created_at: datetime
    
    class Config:
        from_attributes = True


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    refresh_token: str


class PasswordChange(BaseModel):
    """Password change request."""
    current_password: str
    new_password: str = Field(..., min_length=8)
