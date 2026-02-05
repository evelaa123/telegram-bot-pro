"""
Main bot initialization and configuration.
"""
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.redis import RedisStorage

from config import settings

# Initialize Redis storage for FSM
storage = RedisStorage.from_url(settings.redis_url)

# Initialize bot with default properties
bot = Bot(
    token=settings.telegram_bot_token,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML,
        link_preview_is_disabled=True
    )
)

# Initialize dispatcher with Redis storage
dp = Dispatcher(storage=storage)


def create_bot() -> tuple[Bot, Dispatcher]:
    """
    Create and configure bot instance.
    Returns bot and dispatcher.
    """
    return bot, dp
