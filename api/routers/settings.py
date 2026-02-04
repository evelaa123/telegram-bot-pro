"""
Settings router.
Handles global configuration endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from api.schemas.settings import (
    GlobalSettings, GlobalLimits, BotSettings, ApiSettings,
    ApiKeysSettings, ApiKeysStatus,
    SettingResponse, SettingUpdate
)
from api.services.auth_service import get_current_admin, require_role
from database import async_session_maker
from database.models import Setting, Admin
from config import settings as app_settings
import structlog

logger = structlog.get_logger()
router = APIRouter()


# Default settings
DEFAULT_SETTINGS = {
    "limits": {
        "text": app_settings.default_text_limit,
        "image": app_settings.default_image_limit,
        "video": app_settings.default_video_limit,
        "voice": app_settings.default_voice_limit,
        "document": app_settings.default_document_limit,
    },
    "bot": {
        "is_enabled": True,
        "disabled_message": "Бот временно отключён. Попробуйте позже.",
        "subscription_check_enabled": True,
        "channel_id": app_settings.telegram_channel_id,
        "channel_username": app_settings.telegram_channel_username,
    },
    "api": {
        "default_gpt_model": app_settings.default_gpt_model,
        "default_image_model": app_settings.default_image_model,
        "default_video_model": app_settings.default_video_model,
        "default_qwen_model": app_settings.default_qwen_model,
        "default_ai_provider": app_settings.default_ai_provider,
        "max_context_messages": app_settings.max_context_messages,
        "context_ttl_seconds": app_settings.context_ttl_seconds,
        "openai_timeout": app_settings.openai_timeout,
    },
    "api_keys": {
        "openai_api_key": None,
        "qwen_api_key": None,
    }
}


def mask_api_key(key: str) -> str:
    """Mask API key for display, showing only first and last 4 characters."""
    if not key or len(key) < 12:
        return "***"
    return f"{key[:7]}...{key[-4:]}"


def get_api_keys_status() -> ApiKeysStatus:
    """Get current API keys status from environment."""
    openai_key = app_settings.openai_api_key
    qwen_key = app_settings.qwen_api_key
    
    return ApiKeysStatus(
        openai_configured=bool(openai_key and len(openai_key) > 10),
        qwen_configured=bool(qwen_key and len(qwen_key) > 10),
        openai_key_preview=mask_api_key(openai_key) if openai_key else None,
        qwen_key_preview=mask_api_key(qwen_key) if qwen_key else None,
    )


async def get_setting(key: str) -> dict:
    """Get setting value from database or default."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if setting:
            return setting.value
        
        return DEFAULT_SETTINGS.get(key, {})


async def set_setting(key: str, value: dict, admin_id: int) -> Setting:
    """Set setting value in database."""
    async with async_session_maker() as session:
        stmt = insert(Setting).values(
            key=key,
            value=value,
            updated_by=admin_id
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=['key'],
            set_={
                'value': value,
                'updated_by': admin_id
            }
        )
        await session.execute(stmt)
        await session.commit()
        
        result = await session.execute(
            select(Setting).where(Setting.key == key)
        )
        return result.scalar_one()


@router.get("", response_model=GlobalSettings)
async def get_all_settings(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get all global settings."""
    limits = await get_setting("limits")
    bot = await get_setting("bot")
    api = await get_setting("api")
    api_keys_status = get_api_keys_status()
    
    return GlobalSettings(
        limits=GlobalLimits(**limits),
        bot=BotSettings(**bot),
        api=ApiSettings(**api),
        api_keys_status=api_keys_status
    )


@router.get("/limits", response_model=GlobalLimits)
async def get_limits_settings(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get global limits settings."""
    limits = await get_setting("limits")
    return GlobalLimits(**limits)


@router.put("/limits", response_model=GlobalLimits)
async def update_limits_settings(
    limits: GlobalLimits,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Update global limits settings."""
    await set_setting("limits", limits.model_dump(), current_admin.id)
    
    logger.info(
        "Global limits updated",
        limits=limits.model_dump(),
        admin=current_admin.username
    )
    
    return limits


@router.get("/bot", response_model=BotSettings)
async def get_bot_settings(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get bot behavior settings."""
    bot = await get_setting("bot")
    return BotSettings(**bot)


@router.put("/bot", response_model=BotSettings)
async def update_bot_settings(
    bot: BotSettings,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Update bot behavior settings."""
    await set_setting("bot", bot.model_dump(), current_admin.id)
    
    # СБРАСЫВАЕМ КЕШ НАСТРОЕК В БОТЕ
    try:
        from bot.services.settings_service import settings_service
        await settings_service.invalidate_cache()
    except Exception as e:
        logger.warning(f"Failed to invalidate bot settings cache: {e}")
    
    logger.info(
        "Bot settings updated",
        bot=bot.model_dump(),
        admin=current_admin.username
    )
    
    return bot



@router.get("/api", response_model=ApiSettings)
async def get_api_settings(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get API configuration settings."""
    api = await get_setting("api")
    return ApiSettings(**api)


@router.put("/api", response_model=ApiSettings)
async def update_api_settings(
    api: ApiSettings,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Update API configuration settings."""
    await set_setting("api", api.model_dump(), current_admin.id)
    
    logger.info(
        "API settings updated",
        api=api.model_dump(),
        admin=current_admin.username
    )
    
    return api


@router.get("/api-keys/status", response_model=ApiKeysStatus)
async def get_api_keys_status_endpoint(
    current_admin: Admin = Depends(get_current_admin)
):
    """Get API keys configuration status (without revealing full keys)."""
    return get_api_keys_status()


@router.put("/api-keys")
async def update_api_keys(
    api_keys: ApiKeysSettings,
    current_admin: Admin = Depends(require_role(["superadmin"]))
):
    """
    Update API keys configuration.
    
    NOTE: This updates the .env file and requires a server restart to take effect.
    Only superadmin can modify API keys.
    """
    import os
    
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
    
    try:
        # Read current .env file
        env_lines = []
        if os.path.exists(env_path):
            with open(env_path, 'r') as f:
                env_lines = f.readlines()
        
        # Update or add API keys
        openai_updated = False
        qwen_updated = False
        new_lines = []
        
        for line in env_lines:
            stripped = line.strip()
            
            if stripped.startswith("OPENAI_API_KEY=") and api_keys.openai_api_key is not None:
                new_lines.append(f"OPENAI_API_KEY={api_keys.openai_api_key}\n")
                openai_updated = True
            elif stripped.startswith("QWEN_API_KEY=") and api_keys.qwen_api_key is not None:
                new_lines.append(f"QWEN_API_KEY={api_keys.qwen_api_key}\n")
                qwen_updated = True
            else:
                new_lines.append(line)
        
        # Add keys if not found in file
        if api_keys.openai_api_key is not None and not openai_updated:
            # Find position after OpenAI section comment or at the end
            insert_pos = len(new_lines)
            for i, line in enumerate(new_lines):
                if "# OpenAI" in line:
                    insert_pos = i + 1
                    break
            new_lines.insert(insert_pos, f"OPENAI_API_KEY={api_keys.openai_api_key}\n")
        
        if api_keys.qwen_api_key is not None and not qwen_updated:
            # Add after OPENAI_API_KEY or at the end
            insert_pos = len(new_lines)
            for i, line in enumerate(new_lines):
                if line.strip().startswith("OPENAI_API_KEY="):
                    insert_pos = i + 1
                    break
            
            # Check if QWEN section exists
            qwen_section_exists = any("# Qwen" in line for line in new_lines)
            if not qwen_section_exists:
                new_lines.insert(insert_pos, "\n# Qwen API (Alibaba Cloud DashScope)\n")
                insert_pos += 1
            
            new_lines.insert(insert_pos, f"QWEN_API_KEY={api_keys.qwen_api_key}\n")
        
        # Write updated .env file
        with open(env_path, 'w') as f:
            f.writelines(new_lines)
        
        logger.info(
            "API keys updated in .env file",
            admin=current_admin.username,
            openai_updated=api_keys.openai_api_key is not None,
            qwen_updated=api_keys.qwen_api_key is not None
        )
        
        return {
            "success": True,
            "message": "API keys updated. Server restart required for changes to take effect.",
            "openai_updated": api_keys.openai_api_key is not None,
            "qwen_updated": api_keys.qwen_api_key is not None
        }
        
    except Exception as e:
        logger.error("Failed to update API keys", error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update API keys: {str(e)}"
        )


@router.get("/{key}", response_model=SettingResponse)
async def get_setting_by_key(
    key: str,
    current_admin: Admin = Depends(get_current_admin)
):
    """Get specific setting by key."""
    async with async_session_maker() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == key)
        )
        setting = result.scalar_one_or_none()
        
        if not setting:
            # Check if it's a default setting
            if key in DEFAULT_SETTINGS:
                return SettingResponse(
                    key=key,
                    value=DEFAULT_SETTINGS[key],
                    updated_at=None,
                    updated_by_username=None
                )
            
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Setting not found"
            )
        
        # Get admin username if updated_by is set
        admin_username = None
        if setting.updated_by:
            admin_result = await session.execute(
                select(Admin.username).where(Admin.id == setting.updated_by)
            )
            admin_username = admin_result.scalar()
        
        return SettingResponse(
            key=setting.key,
            value=setting.value,
            updated_at=setting.updated_at,
            updated_by_username=admin_username
        )


@router.put("/{key}", response_model=SettingResponse)
async def update_setting_by_key(
    key: str,
    update: SettingUpdate,
    current_admin: Admin = Depends(require_role(["superadmin", "admin"]))
):
    """Update specific setting by key."""
    setting = await set_setting(key, update.value, current_admin.id)
    
    logger.info(
        "Setting updated",
        key=key,
        admin=current_admin.username
    )
    
    return SettingResponse(
        key=setting.key,
        value=setting.value,
        updated_at=setting.updated_at,
        updated_by_username=current_admin.username
    )
