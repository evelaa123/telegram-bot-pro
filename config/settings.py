"""
Application settings and configuration management.
Uses pydantic-settings for environment variable parsing and validation.
"""
from functools import lru_cache
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Main application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # Telegram Configuration
    telegram_bot_token: str = Field(..., description="Telegram Bot API Token")
    telegram_channel_id: int = Field(0, description="Channel ID for subscription check")
    telegram_channel_username: str = Field("@channel", description="Channel username for links")
    
    # OpenAI Configuration
    openai_api_key: str = Field("", description="OpenAI API Key")
    
    # Qwen Configuration (Alibaba Cloud DashScope)
    qwen_api_key: Optional[str] = Field(None, description="Qwen API Key (DashScope)")
    
    # Database
    database_url: str = Field(
        "postgresql+asyncpg://postgres:postgres@localhost:5432/telegram_ai_bot",
        description="PostgreSQL connection URL"
    )
    bot_username: str = ""
    # Redis
    redis_url: str = Field("redis://localhost:6379/0", description="Redis connection URL")
    
    # Admin Panel
    admin_secret_key: str = Field("change-me-in-production", description="JWT secret key for admin panel")
    admin_access_token_expire_minutes: int = Field(30)
    admin_refresh_token_expire_days: int = Field(7)
    
    # Default Admin
    default_admin_username: str = Field("admin")
    default_admin_password: str = Field("admin123")
    
    # Environment
    environment: str = Field("development")
    debug: bool = Field(True)
    
    # Rate Limits (per user per day)
    default_text_limit: int = Field(50)
    default_image_limit: int = Field(10)
    default_video_limit: int = Field(3)
    default_voice_limit: int = Field(20)
    default_document_limit: int = Field(10)
    
    # OpenAI Models
    default_gpt_model: str = Field("gpt-4o-mini")
    default_image_model: str = Field("dall-e-3")
    default_video_model: str = Field("sora-2")
    default_whisper_model: str = Field("whisper-1")
    
    # Qwen Models
    default_qwen_model: str = Field("qwen-plus")
    default_qwen_vl_model: str = Field("qwen-vl-plus")
    default_qwen_image_model: str = Field("wanx-v1")
    default_qwen_tts_model: str = Field("cosyvoice-v1")
    default_qwen_asr_model: str = Field("paraformer-realtime-v2")
    
    # Default AI Provider (openai or qwen)
    default_ai_provider: str = Field("openai")
    
    # Streaming Configuration
    stream_update_interval_ms: int = Field(500)
    stream_token_batch_size: int = Field(15)
    
    # Subscription Cache
    subscription_cache_ttl: int = Field(300)  # 5 minutes
    
    # Context Configuration
    max_context_messages: int = Field(20)
    context_ttl_seconds: int = Field(1800)  # 30 minutes
    
    # File Limits
    max_file_size_mb: int = Field(20)
    max_pdf_pages: int = Field(50)
    max_excel_rows: int = Field(5000)
    max_ppt_slides: int = Field(100)
    
    # API Timeouts
    openai_timeout: int = Field(120)
    telegram_timeout: int = Field(30)
    
    # Worker Configuration
    worker_concurrency: int = Field(4)
    video_poll_interval: int = Field(10)
    
    # Logging
    log_level: str = Field("INFO")
    log_format: str = Field("json")
    
    # CORS
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"]
    )
    
    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            import json
            try:
                return json.loads(v)
            except json.JSONDecodeError:
                # Handle comma-separated string
                return [s.strip() for s in v.split(",")]
        return v
    
    @field_validator("qwen_api_key", mode="before")
    @classmethod
    def validate_qwen_key(cls, v):
        """Convert empty string to None for optional field."""
        if v == "" or v is None:
            return None
        return v
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def default_limits(self) -> dict:
        return {
            "text": self.default_text_limit,
            "image": self.default_image_limit,
            "video": self.default_video_limit,
            "voice": self.default_voice_limit,
            "document": self.default_document_limit,
        }
    
    @property
    def qwen_configured(self) -> bool:
        """Check if Qwen API is configured."""
        return bool(self.qwen_api_key and len(self.qwen_api_key) > 10)
    
    @property
    def openai_configured(self) -> bool:
        """Check if OpenAI API is configured."""
        return bool(self.openai_api_key and len(self.openai_api_key) > 10)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


def reload_settings() -> Settings:
    """
    Force reload settings from .env file.
    Useful when .env is updated dynamically.
    
    Returns:
        Fresh Settings instance
    """
    get_settings.cache_clear()
    return get_settings()


def get_fresh_settings() -> Settings:
    """
    Get fresh settings without using cache.
    Does NOT clear the cache - use for one-time reads.
    
    Returns:
        New Settings instance (bypasses cache)
    """
    return Settings()


# Expose settings instance
settings = get_settings()
