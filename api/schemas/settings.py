"""Settings schemas."""
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class GlobalLimits(BaseModel):
    """Global limits configuration."""
    text: int = Field(50, ge=0)
    image: int = Field(10, ge=0)
    video: int = Field(3, ge=0)
    voice: int = Field(20, ge=0)
    document: int = Field(10, ge=0)


class BotSettings(BaseModel):
    """Bot behavior settings."""
    is_enabled: bool = True
    disabled_message: str = "Бот временно отключён. Попробуйте позже."
    subscription_check_enabled: bool = True
    channel_id: int = 0
    channel_username: str = ""


class ApiSettings(BaseModel):
    """API configuration settings."""
    default_gpt_model: str = "gpt-4o-mini"
    default_image_model: str = "dall-e-3"
    default_video_model: str = "sora-2"
    default_qwen_model: str = "qwen-plus"
    default_ai_provider: Literal["openai", "qwen"] = "openai"
    max_context_messages: int = 20
    context_ttl_seconds: int = 1800
    openai_timeout: int = 120


class ApiKeysSettings(BaseModel):
    """API keys configuration - stored encrypted."""
    openai_api_key: Optional[str] = Field(None, description="OpenAI API Key")
    qwen_api_key: Optional[str] = Field(None, description="Qwen API Key (DashScope)")


class ApiKeysStatus(BaseModel):
    """API keys status (without revealing actual keys)."""
    openai_configured: bool = False
    qwen_configured: bool = False
    openai_key_preview: Optional[str] = None  # e.g. "sk-...abc123"
    qwen_key_preview: Optional[str] = None


class GlobalSettings(BaseModel):
    """All global settings."""
    limits: GlobalLimits
    bot: BotSettings
    api: ApiSettings
    api_keys_status: Optional[ApiKeysStatus] = None


class SettingResponse(BaseModel):
    """Setting response model."""
    key: str
    value: Dict[str, Any]
    updated_at: datetime
    updated_by_username: Optional[str] = None
    
    class Config:
        from_attributes = True


class SettingUpdate(BaseModel):
    """Setting update request."""
    value: Dict[str, Any]


class TextTemplate(BaseModel):
    """Bot text template."""
    key: str
    ru: str
    en: str


class TextTemplatesResponse(BaseModel):
    """Text templates response."""
    templates: Dict[str, TextTemplate]
