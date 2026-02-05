"""Keyboard layouts for the bot."""
from bot.keyboards.main import (
    get_main_menu_keyboard,
    get_settings_keyboard,
    get_limits_keyboard,
    get_subscription_keyboard,
    get_confirm_keyboard,
    get_back_keyboard
)
from bot.keyboards.inline import (
    get_image_actions_keyboard,
    get_video_model_keyboard,
    get_video_actions_keyboard,
    get_document_actions_keyboard,
    get_gpt_model_keyboard,
    get_image_style_keyboard,
    get_image_size_keyboard
)

__all__ = [
    "get_main_menu_keyboard",
    "get_settings_keyboard",
    "get_limits_keyboard",
    "get_subscription_keyboard",
    "get_confirm_keyboard",
    "get_back_keyboard",
    "get_image_actions_keyboard",
    "get_video_model_keyboard",
    "get_video_actions_keyboard",
    "get_document_actions_keyboard",
    "get_gpt_model_keyboard",
    "get_image_style_keyboard",
    "get_image_size_keyboard"
]
