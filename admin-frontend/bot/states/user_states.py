"""
FSM States for user interactions.
"""
from aiogram.fsm.state import State, StatesGroup


class UserStates(StatesGroup):
    """User FSM states for various bot modes."""
    
    # Default mode (text conversation)
    text_mode = State()
    
    # Image generation mode
    image_mode = State()
    image_awaiting_prompt = State()
    image_awaiting_size = State()
    image_awaiting_style = State()
    
    # Video generation mode
    video_mode = State()
    video_awaiting_prompt = State()
    video_awaiting_duration = State()
    video_awaiting_model = State()
    video_awaiting_reference = State()  # For reference image
    video_remix_awaiting_prompt = State()
    
    # Document mode
    document_mode = State()
    document_awaiting_file = State()
    document_awaiting_question = State()
    
    # Voice mode
    voice_mode = State()
    
    # Settings
    settings_menu = State()
    settings_language = State()
    settings_model = State()
    settings_notifications = State()
    
    # Admin states
    admin_menu = State()
    admin_broadcast = State()
    admin_broadcast_confirm = State()
    admin_set_limits = State()


class ImageGenerationStates(StatesGroup):
    """Dedicated states for image generation flow."""
    
    waiting_prompt = State()
    waiting_size_selection = State()
    waiting_style_selection = State()
    waiting_edit_prompt = State()
    waiting_variations_count = State()


class VideoGenerationStates(StatesGroup):
    """Dedicated states for video generation flow."""
    
    waiting_prompt = State()
    waiting_duration = State()
    waiting_model_selection = State()
    waiting_reference_image = State()
    waiting_remix_prompt = State()
    waiting_confirmation = State()


class DocumentProcessingStates(StatesGroup):
    """Dedicated states for document processing flow."""
    
    waiting_document = State()
    waiting_question = State()
    document_loaded = State()
    waiting_follow_up = State()


class ConversationStates(StatesGroup):
    """States for managing conversation context."""
    
    active = State()  # Active conversation with context
    idle = State()    # No active conversation
    waiting_response = State()  # Waiting for AI response
