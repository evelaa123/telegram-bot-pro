"""Settings schemas."""
from datetime import datetime
from typing import Optional, Dict, Any, Literal
from pydantic import BaseModel, Field


class GlobalLimits(BaseModel):
    """Global limits configuration."""
    text: int = Field(10, ge=0)
    image: int = Field(5, ge=0)
    video: int = Field(5, ge=0)
    voice: int = Field(5, ge=0)
    document: int = Field(10, ge=0)


class BotSettings(BaseModel):
    """Bot behavior settings."""
    is_enabled: bool = True
    disabled_message: str = "Бот временно отключён. Попробуйте позже."
    subscription_check_enabled: bool = True
    channel_id: int = 0
    channel_username: str = ""


class ApiSettings(BaseModel):
    """
    API configuration settings.
    Note: AI models are now fixed (not configurable by admin):
    - Text: qwen-3-max via CometAPI
    - Image: dall-e-3 via CometAPI
    - Video: sora-2 via CometAPI
    - Voice: whisper-1 via CometAPI
    - Presentations: GigaChat (direct API)
    """
    # Legacy fields - kept for compatibility but not used
    default_gpt_model: str = "qwen-3-max"
    default_image_model: str = "dall-e-3"
    default_video_model: str = "sora-2"
    default_qwen_model: str = "qwen-3-max"
    default_ai_provider: Literal["openai", "qwen", "cometapi"] = "cometapi"
    
    # Active settings
    max_context_messages: int = 20
    context_ttl_seconds: int = 1800
    openai_timeout: int = 120


class ApiKeysSettings(BaseModel):
    """API keys configuration for updating."""
    cometapi_api_key: Optional[str] = Field(None, description="CometAPI API Key (Primary)")
    gigachat_credentials: Optional[str] = Field(None, description="GigaChat Base64 credentials")
    openai_api_key: Optional[str] = Field(None, description="OpenAI API Key (Fallback)")
    qwen_api_key: Optional[str] = Field(None, description="Qwen API Key (Legacy)")


class ApiKeysStatus(BaseModel):
    """API keys status (without revealing actual keys)."""
    cometapi_configured: bool = False
    gigachat_configured: bool = False
    openai_configured: bool = False
    qwen_configured: bool = False
    cometapi_key_preview: Optional[str] = None
    openai_key_preview: Optional[str] = None
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
    updated_at: Optional[datetime] = None
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
