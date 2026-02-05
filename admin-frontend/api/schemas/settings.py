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
    Admin can configure models via CometAPI dashboard.
    Default models:
    - Text: qwen3-max-2026-01-23 via CometAPI
    - Image: dall-e-3 via CometAPI
    - Video: sora-2 via CometAPI
    - Voice: whisper-1 via CometAPI
    - Presentations: GigaChat-2-Max (direct API)
    """
    # Base URLs - configurable by admin (applied immediately via cache invalidation)
    cometapi_base_url: str = Field("https://api.cometapi.com/v1", description="CometAPI base URL")
    gigachat_auth_url: str = Field("https://ngw.devices.sberbank.ru:9443/api/v2/oauth", description="GigaChat OAuth URL")
    gigachat_api_url: str = Field("https://gigachat.devices.sberbank.ru/api/v1", description="GigaChat API URL")
    
    # Model settings - configurable by admin
    default_text_model: str = Field("qwen3-max-2026-01-23", description="Text generation model (via CometAPI)")
    default_image_model: str = Field("dall-e-3", description="Image generation model (via CometAPI)")
    default_video_model: str = Field("sora-2", description="Video generation model (via CometAPI)")
    default_voice_model: str = Field("whisper-1", description="Speech recognition model (via CometAPI)")
    default_gigachat_model: str = Field("GigaChat-2-Max", description="GigaChat model for presentations")
    
    # Provider settings
    default_ai_provider: Literal["openai", "qwen", "cometapi"] = "cometapi"
    
    # Context settings
    max_context_messages: int = Field(20, ge=1, le=100, description="Max messages in context")
    context_ttl_seconds: int = Field(1800, ge=60, description="Context TTL in seconds")
    
    # Timeouts
    openai_timeout: int = Field(120, ge=30, le=600, description="API timeout in seconds")
    
    # Legacy fields for compatibility
    default_gpt_model: str = "qwen3-max-2026-01-23"
    default_qwen_model: str = "qwen3-max-2026-01-23"


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
