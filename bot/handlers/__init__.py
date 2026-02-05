"""Bot handlers module."""
from aiogram import Router

from bot.handlers.start import router as start_router
from bot.handlers.text import router as text_router
from bot.handlers.image import router as image_router
from bot.handlers.video import router as video_router
from bot.handlers.voice import router as voice_router
from bot.handlers.document import router as document_router
from bot.handlers.settings import router as settings_router
from bot.handlers.inline import router as inline_router
from bot.handlers.callbacks import router as callbacks_router
from bot.handlers.channel_comments import router as channel_comments_router
from bot.handlers.assistant import router as assistant_router
from bot.handlers.presentation import router as presentation_router
from bot.handlers.support import router as support_router
from bot.handlers.photo import router as photo_router


def setup_routers() -> Router:
    """
    Setup and configure all routers.
    Returns the main router with all sub-routers included.
    """
    main_router = Router()
    
    # Include all routers in order of priority
    main_router.include_router(start_router)
    main_router.include_router(callbacks_router)
    main_router.include_router(settings_router)
    main_router.include_router(assistant_router)  # Assistant features
    main_router.include_router(presentation_router)  # Presentation generation
    main_router.include_router(support_router)  # Tech support
    main_router.include_router(photo_router)  # Photo handler - BEFORE image_router!
    main_router.include_router(image_router)
    main_router.include_router(video_router)
    main_router.include_router(voice_router)
    main_router.include_router(channel_comments_router)  # Группы и комментарии - ПЕРЕД document!
    main_router.include_router(document_router)
    main_router.include_router(inline_router)
    main_router.include_router(text_router)  # Text должен быть ПОСЛЕДНИМ (catch-all)
    
    return main_router


__all__ = ["setup_routers"]
