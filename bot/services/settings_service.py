"""
Bot settings service.
Загружает настройки из таблицы settings в БД.
"""
from typing import Optional, Dict, Any
from sqlalchemy import select
from database import async_session_maker
from database.models import Setting
from database.redis_client import redis_client
import structlog

logger = structlog.get_logger()


class SettingsService:
    """
    Сервис для работы с настройками бота из БД.
    Читает из таблицы settings (key-value store).
    """
    
    CACHE_KEY = "bot:db_settings"
    CACHE_TTL = 30  # секунд
    
    async def get_all_settings(self) -> Dict[str, Any]:
        """Получить все настройки из БД."""
        # Проверяем кеш
        try:
            cached = await redis_client.client.get(self.CACHE_KEY)
            if cached:
                import json
                return json.loads(cached)
        except Exception as e:
            logger.warning(f"Redis cache error: {e}")
        
        # Загружаем из БД
        settings_data = await self._load_from_db()
        
        # Кешируем
        if settings_data:
            try:
                import json
                await redis_client.client.setex(
                    self.CACHE_KEY,
                    self.CACHE_TTL,
                    json.dumps(settings_data)
                )
            except Exception as e:
                logger.warning(f"Redis cache set error: {e}")
        
        return settings_data
    
    async def _load_from_db(self) -> Dict[str, Any]:
        """Загрузить настройки из БД."""
        try:
            async with async_session_maker() as session:
                result = await session.execute(select(Setting))
                settings_rows = result.scalars().all()
                
                all_settings = {}
                for row in settings_rows:
                    all_settings[row.key] = row.value
                
                logger.debug(f"Loaded settings from DB: {list(all_settings.keys())}")
                return all_settings
                
        except Exception as e:
            logger.error(f"Failed to load settings from DB: {e}")
            return {}
    
    async def get_bot_settings(self) -> Dict[str, Any]:
        """Получить настройки бота (ключ 'bot')."""
        all_settings = await self.get_all_settings()
        return all_settings.get("bot", {})
    
    async def is_bot_enabled(self) -> bool:
        """Проверить, включён ли бот."""
        bot_settings = await self.get_bot_settings()
        
        # Ключ из админки: "is_enabled" (не "bot_enabled"!)
        return bot_settings.get("is_enabled", True)
    
    async def get_disabled_message(self) -> str:
        """Получить сообщение при отключённом боте."""
        bot_settings = await self.get_bot_settings()
        return bot_settings.get("disabled_message", "Бот временно отключён. Попробуйте позже.")
    
    async def is_subscription_required(self) -> bool:
        """Проверить, требуется ли подписка на канал."""
        bot_settings = await self.get_bot_settings()
        
        # Ключ из админки: "subscription_check_enabled"
        return bot_settings.get("subscription_check_enabled", True)
    
    async def get_channel_id(self) -> Optional[int]:
        """Получить ID канала для проверки подписки."""
        bot_settings = await self.get_bot_settings()
        channel_id = bot_settings.get("channel_id")
        
        if channel_id:
            try:
                return int(channel_id)
            except (ValueError, TypeError):
                pass
        return None
    
    async def get_channel_username(self) -> Optional[str]:
        """Получить username канала."""
        bot_settings = await self.get_bot_settings()
        return bot_settings.get("channel_username")
    
    async def get_limits_settings(self) -> Dict[str, int]:
        """Получить настройки лимитов (ключ 'limits')."""
        all_settings = await self.get_all_settings()
        return all_settings.get("limits", {})
    
    async def get_api_settings(self) -> Dict[str, Any]:
        """Получить настройки API (ключ 'api')."""
        all_settings = await self.get_all_settings()
        return all_settings.get("api", {})
    
    async def invalidate_cache(self):
        """Сбросить кеш настроек."""
        try:
            await redis_client.client.delete(self.CACHE_KEY)
            logger.info("Settings cache invalidated")
        except Exception as e:
            logger.warning(f"Failed to invalidate cache: {e}")


# Глобальный экземпляр
settings_service = SettingsService()
