"""
Start and help command handlers.
"""
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards.main import get_main_menu_keyboard
from bot.services.user_service import user_service
from database.redis_client import redis_client
from config import settings

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command."""
    user = message.from_user
    
    # Get user's language preference
    language = await user_service.get_user_language(user.id)
    
    # Clear any existing state
    await redis_client.clear_user_state(user.id)
    await redis_client.clear_context(user.id)
    
    if language == "ru":
        welcome_text = (
            f"👋 Привет, <b>{user.first_name}</b>!\n\n"
            "Я — ИИ-ассистент с возможностями:\n\n"
            "💬 <b>Текст</b> — отвечаю на вопросы, помогаю с задачами\n"
            "🖼 <b>Изображения</b> — генерирую картинки по описанию\n"
            "🎬 <b>Видео</b> — создаю короткие видеоролики\n"
            "🎤 <b>Голос</b> — распознаю голосовые сообщения\n"
            "📄 <b>Документы</b> — анализирую и отвечаю на вопросы\n\n"
            "Просто напишите мне или выберите действие в меню 👇"
        )
    else:
        welcome_text = (
            f"👋 Hello, <b>{user.first_name}</b>!\n\n"
            "I'm an AI assistant with capabilities:\n\n"
            "💬 <b>Text</b> — answering questions, helping with tasks\n"
            "🖼 <b>Images</b> — generating pictures from descriptions\n"
            "🎬 <b>Video</b> — creating short video clips\n"
            "🎤 <b>Voice</b> — recognizing voice messages\n"
            "📄 <b>Documents</b> — analyzing and answering questions\n\n"
            "Just write to me or choose an action from the menu 👇"
        )
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_menu_keyboard(language)
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Handle /help command."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        help_text = (
            "📚 <b>Справка по использованию бота</b>\n\n"
            "<b>Команды:</b>\n"
            "/start — перезапустить бота\n"
            "/help — показать эту справку\n"
            "/new — начать новый диалог\n"
            "/image — режим генерации изображений\n"
            "/video — режим генерации видео\n"
            "/limits — показать ваши лимиты\n"
            "/settings — настройки\n\n"
            
            "<b>Текстовые запросы:</b>\n"
            "Просто напишите любой вопрос или задачу — я отвечу.\n"
            "Контекст сохраняется в течение 30 минут.\n\n"
            
            "<b>Генерация изображений:</b>\n"
            "Нажмите «🖼 Изображение» или /image, затем опишите картинку.\n"
            "Доступны размеры: квадрат, горизонтальный, вертикальный.\n\n"
            
            "<b>Генерация видео:</b>\n"
            "Нажмите «🎬 Видео» или /video, выберите модель и опишите видео.\n"
            "Генерация занимает 1-10 минут.\n\n"
            
            "<b>Голосовые сообщения:</b>\n"
            "Отправьте голосовое — я его распознаю.\n"
            "В настройках можно включить авто-ответ на распознанный текст.\n\n"
            
            "<b>Документы:</b>\n"
            "Отправьте файл (PDF, Word, Excel, PowerPoint, изображение).\n"
            "Я проанализирую содержимое и отвечу на вопросы."
        )
    else:
        help_text = (
            "📚 <b>Bot Usage Guide</b>\n\n"
            "<b>Commands:</b>\n"
            "/start — restart the bot\n"
            "/help — show this help\n"
            "/new — start new dialog\n"
            "/image — image generation mode\n"
            "/video — video generation mode\n"
            "/limits — show your limits\n"
            "/settings — settings\n\n"
            
            "<b>Text Requests:</b>\n"
            "Just write any question or task — I'll answer.\n"
            "Context is saved for 30 minutes.\n\n"
            
            "<b>Image Generation:</b>\n"
            "Click '🖼 Image' or /image, then describe the picture.\n"
            "Available sizes: square, horizontal, vertical.\n\n"
            
            "<b>Video Generation:</b>\n"
            "Click '🎬 Video' or /video, choose model and describe video.\n"
            "Generation takes 1-10 minutes.\n\n"
            
            "<b>Voice Messages:</b>\n"
            "Send a voice message — I'll transcribe it.\n"
            "You can enable auto-response to transcribed text in settings.\n\n"
            
            "<b>Documents:</b>\n"
            "Send a file (PDF, Word, Excel, PowerPoint, image).\n"
            "I'll analyze the content and answer questions."
        )
    
    await message.answer(help_text)


@router.message(Command("new"))
async def cmd_new_dialog(message: Message):
    """Handle /new command - clear context and start fresh."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    # Clear context and document context
    await redis_client.clear_context(user.id)
    await redis_client.clear_document_context(user.id)
    await redis_client.clear_user_state(user.id)
    
    if language == "ru":
        text = (
            "🔄 <b>Новый диалог начат!</b>\n\n"
            "Контекст предыдущего разговора очищен.\n"
            "Можете задать новый вопрос."
        )
    else:
        text = (
            "🔄 <b>New dialog started!</b>\n\n"
            "Previous conversation context cleared.\n"
            "You can ask a new question."
        )
    
    await message.answer(text)


@router.message(F.text == "🔄 Новый диалог")
@router.message(F.text == "🔄 New Dialog")
async def btn_new_dialog(message: Message):
    """Handle new dialog button."""
    await cmd_new_dialog(message)


@router.message(Command("limits"))
async def cmd_limits(message: Message):
    """Handle /limits command."""
    from bot.services.limit_service import limit_service
    
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    limits_text = await limit_service.get_limits_text(user.id, language)
    
    from bot.keyboards.main import get_limits_keyboard
    await message.answer(limits_text, reply_markup=get_limits_keyboard(language))


# ============================================
# Reply Keyboard Button Handlers
# ============================================

@router.message(F.text.in_({"📊 Лимиты", "📊 Limits", "📊 Мои лимиты", "📊 My Limits"}))
async def btn_limits(message: Message):
    """Handle limits button from Reply keyboard."""
    await cmd_limits(message)


@router.message(F.text.in_({"⚙️ Настройки", "⚙️ Settings"}))
async def btn_settings(message: Message):
    """Handle settings button from Reply keyboard."""
    from bot.handlers.settings import show_settings
    await show_settings(message)


@router.message(F.text.in_({"💬 Текст", "💬 Text"}))
async def btn_text_mode(message: Message):
    """Handle text mode button - just confirm mode."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    # Clear any special mode state
    await redis_client.clear_user_state(user.id)
    
    if language == "ru":
        text = (
            "💬 <b>Текстовый режим активен</b>\n\n"
            "Просто напишите ваш вопрос или задачу, и я отвечу.\n"
            "Я помню контекст последних сообщений."
        )
    else:
        text = (
            "💬 <b>Text mode active</b>\n\n"
            "Just write your question or task, and I'll respond.\n"
            "I remember the context of recent messages."
        )
    
    await message.answer(text)


@router.message(F.text.in_({"🖼 Изображение", "🖼 Image"}))
async def btn_image_mode(message: Message):
    """Handle image mode button."""
    from bot.handlers.image import cmd_image
    await cmd_image(message)


@router.message(F.text.in_({"🎬 Видео", "🎬 Video"}))
async def btn_video_mode(message: Message):
    """Handle video mode button."""
    from bot.handlers.video import cmd_video
    await cmd_video(message)


@router.message(F.text.in_({"📄 Документ", "📄 Document"}))
async def btn_document_mode(message: Message):
    """Handle document mode button."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        text = (
            "📄 <b>Режим работы с документами</b>\n\n"
            "Отправьте мне файл для анализа:\n"
            "• PDF документы\n"
            "• Word (.docx)\n"
            "• Excel (.xlsx)\n"
            "• PowerPoint (.pptx)\n"
            "• Изображения с текстом\n"
            "• Текстовые файлы (.txt, .md, .csv, .json)\n\n"
            "После загрузки вы сможете задавать вопросы по содержимому."
        )
    else:
        text = (
            "📄 <b>Document Mode</b>\n\n"
            "Send me a file to analyze:\n"
            "• PDF documents\n"
            "• Word (.docx)\n"
            "• Excel (.xlsx)\n"
            "• PowerPoint (.pptx)\n"
            "• Images with text\n"
            "• Text files (.txt, .md, .csv, .json)\n\n"
            "After uploading, you can ask questions about the content."
        )
    
    await message.answer(text)


@router.message(F.text.in_({"🎤 Голос", "🎤 Voice"}))
async def btn_voice_mode(message: Message):
    """Handle voice mode button."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        text = (
            "🎤 <b>Режим голосовых сообщений</b>\n\n"
            "Отправьте голосовое сообщение или аудиофайл,\n"
            "и я распознаю речь и создам текстовую транскрипцию.\n\n"
            "📝 <b>Доступные функции:</b>\n"
            "• Распознавание голосовых сообщений\n"
            "• Транскрипция аудиофайлов (mp3, wav, ogg, m4a...)\n"
            "• Создание протоколов совещаний\n\n"
            "💡 В настройках можно включить авто-обработку —\n"
            "распознанный текст автоматически отправится как запрос к ИИ."
        )
    else:
        text = (
            "🎤 <b>Voice Message Mode</b>\n\n"
            "Send a voice message or audio file,\n"
            "and I'll recognize the speech and create a transcription.\n\n"
            "📝 <b>Available features:</b>\n"
            "• Voice message recognition\n"
            "• Audio file transcription (mp3, wav, ogg, m4a...)\n"
            "• Meeting protocol creation\n\n"
            "💡 In settings, you can enable auto-processing —\n"
            "the transcribed text will be automatically sent as an AI request."
        )
    
    await message.answer(text)


@router.message(F.text.in_({"📨 Поддержка", "📨 Support"}))
async def btn_support(message: Message):
    """Handle support button from Reply keyboard."""
    from bot.handlers.support import cmd_support
    await cmd_support(message)
