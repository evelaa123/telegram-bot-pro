"""
Start and help command handlers.
"""
import hashlib
from aiogram import Router, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from bot.keyboards.main import get_main_menu_keyboard
from bot.services.user_service import user_service
from database.redis_client import redis_client
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


def generate_referral_code(telegram_id: int) -> str:
    """Generate a unique referral code from telegram_id."""
    raw = f"ref_{telegram_id}_{settings.jwt_secret_key[:8]}"
    return hashlib.md5(raw.encode()).hexdigest()[:12]


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Handle /start command with optional deep_link referral."""
    user = message.from_user
    
    # Get user's language preference
    language = await user_service.get_user_language(user.id)
    
    # Clear any existing state
    await redis_client.clear_user_state(user.id)
    await redis_client.clear_context(user.id)
    
    # ---- Parse deep_link for referral ----
    args = message.text.split(maxsplit=1)
    deep_link = args[1].strip() if len(args) > 1 else ""
    
    if deep_link.startswith("ref_"):
        referral_code = deep_link
        try:
            # Find referrer by code
            referrer = await user_service.find_user_by_referral_code(referral_code)
            if referrer and referrer.telegram_id != user.id:
                # Set referred_by if not already set
                await user_service.set_referral(user.id, referrer.telegram_id, referral_code)
                
                logger.info(
                    "Referral registered",
                    user_id=user.id,
                    referrer_id=referrer.telegram_id,
                    code=referral_code
                )
        except Exception as e:
            logger.error("Referral processing error", error=str(e))
    
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
            "/settings — настройки\n"
            "/about — полное описание возможностей (можно переслать)\n\n"
            
            "<b>Текстовые запросы:</b>\n"
            "Просто напишите любой вопрос или задачу — я отвечу.\n"
            "Контекст сохраняется в течение 30 минут.\n"
            "🌐 Бот сам ищет в интернете, когда нужна актуальная информация.\n\n"
            
            "<b>Генерация изображений:</b>\n"
            "Нажмите «🖼 Изображение» или /image, затем опишите картинку.\n"
            "Доступны размеры: квадрат, горизонтальный, вертикальный.\n\n"
            
            "<b>Редактирование фото:</b>\n"
            "Отправьте фото + подпись-инструкцию → «✏️ Ещё раз» для серии правок.\n\n"
            
            "<b>Несколько фото / файлов:</b>\n"
            "Отправьте альбом фото или несколько документов — бот обработает вместе.\n\n"
            
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
            "/settings — settings\n"
            "/about — full feature guide (can be forwarded)\n\n"
            
            "<b>Text Requests:</b>\n"
            "Just write any question or task — I'll answer.\n"
            "Context is saved for 30 minutes.\n"
            "🌐 The bot automatically searches the web when current info is needed.\n\n"
            
            "<b>Image Generation:</b>\n"
            "Click '🖼 Image' or /image, then describe the picture.\n"
            "Available sizes: square, horizontal, vertical.\n\n"
            
            "<b>Photo Editing:</b>\n"
            "Send photo + caption instruction → '✏️ Edit Again' for a series of edits.\n\n"
            
            "<b>Multiple Photos / Files:</b>\n"
            "Send a photo album or multiple documents — the bot processes them together.\n\n"
            
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


@router.message(F.text.in_({"💬 Текст и документы", "💬 Text & Documents", "💬 Текст", "💬 Text"}))
async def btn_text_mode(message: Message):
    """Handle text & documents mode button - just confirm mode."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    # Clear any special mode state
    await redis_client.clear_user_state(user.id)
    
    if language == "ru":
        text = (
            "💬 <b>Текст и документы — режим активен</b>\n\n"
            "Просто напишите ваш вопрос или задачу, и я отвечу.\n"
            "Я помню контекст последних сообщений.\n\n"
            "📄 Также вы можете отправить документ (PDF, Word, Excel, PowerPoint)\n"
            "или изображение с текстом — я проанализирую содержимое."
        )
    else:
        text = (
            "💬 <b>Text & Documents — mode active</b>\n\n"
            "Just write your question or task, and I'll respond.\n"
            "I remember the context of recent messages.\n\n"
            "📄 You can also send a document (PDF, Word, Excel, PowerPoint)\n"
            "or an image with text — I'll analyze the content."
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


@router.message(F.text.in_({"💎 Подписка", "💎 Subscription"}))
async def btn_subscription(message: Message):
    """Handle subscription button from Reply keyboard."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    from bot.services.subscription_service import subscription_service
    subscription_text = await subscription_service.get_subscription_text(user.id, language)
    
    from bot.keyboards.inline import get_subscription_keyboard
    await message.answer(
        subscription_text,
        reply_markup=get_subscription_keyboard(language)
    )


@router.message(Command("about"))
async def cmd_about(message: Message):
    """
    Handle /about command — send a ready-to-share summary of bot capabilities.
    Can be forwarded to others or used in channels.
    """
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    # Get bot username for the link
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    
    if language == "ru":
        about_text = (
            "🤖 <b>ИИ-ассистент — возможности бота</b>\n\n"
            
            "💬 <b>Текст и вопросы</b>\n"
            "Просто напишите вопрос — бот ответит с помощью ИИ.\n"
            "Контекст диалога сохраняется 30 мин. Команда /new — сброс.\n\n"
            
            "🌐 <b>Поиск в интернете</b>\n"
            "Бот сам решает, когда нужен поиск в интернете (погода, курсы, новости).\n"
            "Источники прикрепляются автоматически.\n\n"
            
            "🖼 <b>Генерация изображений</b>\n"
            "Нажмите «🖼 Изображение» или /image → выберите размер → опишите картинку.\n\n"
            
            "✏️ <b>Редактирование фото</b>\n"
            "Отправьте фото с подписью-инструкцией (например: «Добавь тень»).\n"
            "После редактирования нажмите «✏️ Ещё раз» или просто пишите новую инструкцию.\n\n"
            
            "📸 <b>Несколько фото (Media Group)</b>\n"
            "Отправьте несколько фото одновременно — бот проанализирует их вместе.\n"
            "Добавьте подпись к альбому — бот выполнит инструкцию.\n\n"
            
            "🎬 <b>Генерация видео</b>\n"
            "Нажмите «🎬 Видео» или /video → выберите модель → опишите видео.\n"
            "Можно оживить фото (кнопка «🎞 Оживить фото»).\n\n"
            
            "🎤 <b>Голосовые сообщения</b>\n"
            "Отправьте голосовое — бот распознает и ответит.\n"
            "Работает как текст: голосом можно рисовать, редактировать фото, задавать вопросы.\n\n"
            
            "📄 <b>Документы и файлы</b>\n"
            "Отправьте PDF, Word, Excel, PowerPoint, текстовый файл или изображение.\n"
            "Можно отправить сразу несколько файлов — бот обработает вместе.\n"
            "После загрузки задавайте вопросы по содержимому.\n\n"
            
            "📊 <b>Презентации</b>\n"
            "Скажите голосом или напишите «Создай презентацию про...» — бот сгенерирует .pptx.\n\n"
            
            "⚙️ <b>Команды:</b>\n"
            "/start — перезапуск  •  /new — новый диалог\n"
            "/image — картинка  •  /video — видео\n"
            "/limits — лимиты  •  /settings — настройки\n"
            "/about — эта справка  •  /referral — реферальная ссылка\n\n"
            
            f"▶️ Начать: @{bot_username}"
        )
    else:
        about_text = (
            "🤖 <b>AI Assistant — Bot Features</b>\n\n"
            
            "💬 <b>Text & Questions</b>\n"
            "Just write a question — the bot answers using AI.\n"
            "Dialog context is saved for 30 min. /new to reset.\n\n"
            
            "🌐 <b>Web Search</b>\n"
            "The bot automatically searches the web when needed (weather, prices, news).\n"
            "Sources are attached automatically.\n\n"
            
            "🖼 <b>Image Generation</b>\n"
            "Tap '🖼 Image' or /image → choose size → describe the picture.\n\n"
            
            "✏️ <b>Photo Editing</b>\n"
            "Send a photo with a caption instruction (e.g., 'Add a shadow').\n"
            "After editing, tap '✏️ Edit Again' or just type a new instruction.\n\n"
            
            "📸 <b>Multiple Photos (Media Group)</b>\n"
            "Send several photos at once — the bot analyzes them together.\n"
            "Add a caption to the album — the bot follows the instruction.\n\n"
            
            "🎬 <b>Video Generation</b>\n"
            "Tap '🎬 Video' or /video → choose model → describe the video.\n"
            "You can animate photos ('🎞 Animate Photo' button).\n\n"
            
            "🎤 <b>Voice Messages</b>\n"
            "Send a voice message — the bot transcribes and responds.\n"
            "Works like text: draw, edit photos, ask questions by voice.\n\n"
            
            "📄 <b>Documents & Files</b>\n"
            "Send PDF, Word, Excel, PowerPoint, text files, or images.\n"
            "You can send multiple files at once — the bot processes them together.\n"
            "Ask questions about the content after uploading.\n\n"
            
            "📊 <b>Presentations</b>\n"
            "Say or type 'Create a presentation about...' — the bot generates a .pptx.\n\n"
            
            "⚙️ <b>Commands:</b>\n"
            "/start — restart  •  /new — new dialog\n"
            "/image — picture  •  /video — video\n"
            "/limits — limits  •  /settings — settings\n"
            "/about — this guide  •  /referral — referral link\n\n"
            
            f"▶️ Start: @{bot_username}"
        )
    
    await message.answer(about_text, parse_mode="HTML")


# ============================================
# REFERRAL SYSTEM
# ============================================

@router.message(Command("referral"))
async def cmd_referral(message: Message):
    """Handle /referral command — show referral link and stats."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    # Ensure user has a referral code
    code = await user_service.get_or_create_referral_code(user.id)
    
    if not code:
        code = generate_referral_code(user.id)
        await user_service.save_referral_code(user.id, code)
    
    # Get bot username for the link
    bot_info = await message.bot.get_me()
    bot_username = bot_info.username
    
    referral_link = f"https://t.me/{bot_username}?start=ref_{code}"
    
    # Get referral stats
    stats = await user_service.get_referral_stats(user.id)
    invited_count = stats.get("invited_count", 0)
    total_earnings = stats.get("total_earnings", 0)
    
    if language == "ru":
        text = (
            "🎁 <b>Реферальная программа</b>\n\n"
            f"📎 Ваша реферальная ссылка:\n"
            f"<code>{referral_link}</code>\n\n"
            "💰 <b>Как это работает:</b>\n"
            "• Поделитесь ссылкой с друзьями\n"
            "• Когда друг оформит подписку, вы получите 15% кешбэк\n"
            "• Кешбэк начисляется при каждой оплате друга\n\n"
            f"👥 Приглашено: <b>{invited_count}</b>\n"
            f"💵 Заработано: <b>{total_earnings:.2f} ₽</b>\n\n"
            "📲 Нажмите на ссылку чтобы скопировать"
        )
    else:
        text = (
            "🎁 <b>Referral Program</b>\n\n"
            f"📎 Your referral link:\n"
            f"<code>{referral_link}</code>\n\n"
            "💰 <b>How it works:</b>\n"
            "• Share the link with friends\n"
            "• When a friend subscribes, you get 15% cashback\n"
            "• Cashback is credited for each friend's payment\n\n"
            f"👥 Invited: <b>{invited_count}</b>\n"
            f"💵 Earned: <b>{total_earnings:.2f} ₽</b>\n\n"
            "📲 Tap the link to copy"
        )
    
    await message.answer(text, parse_mode="HTML")
