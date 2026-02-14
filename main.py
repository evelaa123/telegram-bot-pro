"""
Main entry point for the Telegram AI Bot.
"""
import asyncio
import sys

import structlog

from aiogram import Bot
from aiogram.types import BotCommand

from bot.bot import bot, dp
from bot.handlers import setup_routers
from bot.middlewares import AuthMiddleware, LoggingMiddleware, ThrottlingMiddleware
from database import init_db, close_db
from database.redis_client import redis_client
from config import settings


# Configure structlog
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer() if settings.log_format == "json" else structlog.dev.ConsoleRenderer(),
    ],
    wrapper_class=structlog.stdlib.BoundLogger,
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger()


async def set_bot_commands(bot: Bot):
    """Set bot commands for menu."""
    commands = [
        BotCommand(command="start", description="Запустить бота / Start bot"),
        BotCommand(command="help", description="Справка / Help"),
        BotCommand(command="new", description="Новый диалог / New dialog"),
        BotCommand(command="image", description="Генерация изображения / Generate image"),
        BotCommand(command="video", description="Генерация видео / Generate video"),
        BotCommand(command="limits", description="Мои лимиты / My limits"),
        BotCommand(command="settings", description="Настройки / Settings"),
        BotCommand(command="referral", description="Реферальная программа / Referral program"),
    ]
    
    await bot.set_my_commands(commands)
    logger.info("Bot commands set")


async def on_startup():
    """Startup hook."""
    logger.info("Starting bot...")
    
    # Initialize database
    await init_db()
    logger.info("Database initialized")
    
    # Initialize Redis
    await redis_client.connect()
    logger.info("Redis connected")
    
    # Cache bot info at startup (avoid calling bot.get_me() on every message)
    bot_info = await bot.get_me()
    dp["bot_info"] = bot_info
    logger.info(
        "Bot info cached",
        bot_id=bot_info.id,
        bot_username=bot_info.username,
    )
    
    # Set bot commands
    await set_bot_commands(bot)
    
    logger.info("Bot started successfully", environment=settings.environment)


async def on_shutdown():
    """Shutdown hook."""
    logger.info("Shutting down bot...")
    
    # Close Redis
    await redis_client.close()
    logger.info("Redis disconnected")
    
    # Close database
    await close_db()
    logger.info("Database connection closed")
    
    logger.info("Bot shutdown complete")


async def main():
    """Main function."""
    # Register startup/shutdown hooks
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)
    
    # Setup middlewares
    dp.message.middleware(LoggingMiddleware())
    dp.message.middleware(ThrottlingMiddleware())
    dp.message.middleware(AuthMiddleware())
    
    dp.callback_query.middleware(LoggingMiddleware())
    dp.callback_query.middleware(ThrottlingMiddleware())
    dp.callback_query.middleware(AuthMiddleware())
    
    dp.inline_query.middleware(LoggingMiddleware())
    
    # Setup routers
    router = setup_routers()
    dp.include_router(router)
    
    # Start polling
    logger.info("Starting polling...")
    
    try:
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error("Polling error", error=str(e))
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    except Exception as e:
        logger.error("Fatal error", error=str(e))
        sys.exit(1)
