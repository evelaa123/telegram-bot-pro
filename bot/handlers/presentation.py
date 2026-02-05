"""
Presentation generation handler.
Creates PowerPoint presentations using GigaChat and CometAPI.
"""
import io
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.services.presentation_service import presentation_service
from bot.keyboards.inline import InlineKeyboardBuilder, InlineKeyboardButton
from database.models import RequestType
import structlog

logger = structlog.get_logger()
router = Router()


class PresentationStates(StatesGroup):
    """FSM states for presentation generation."""
    waiting_topic = State()
    configuring = State()
    generating = State()


# =========================================
# Presentation Menu
# =========================================

@router.message(F.text.in_({"📊 Презентация", "📊 Presentation"}))
@router.message(Command("presentation"))
async def cmd_presentation(message: Message, state: FSMContext):
    """Handle presentation mode button/command."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    # Check limits
    can_use, remaining, limit = await limit_service.check_limit(
        user.id, RequestType.PRESENTATION
    )
    
    if not can_use:
        if language == "ru":
            text = (
                "⚠️ <b>Лимит презентаций исчерпан</b>\n\n"
                f"Дневной лимит: {limit}\n"
                "Лимит обновится завтра.\n\n"
                "💳 Оформите премиум-подписку для снятия ограничений."
            )
        else:
            text = (
                "⚠️ <b>Presentation limit reached</b>\n\n"
                f"Daily limit: {limit}\n"
                "Limit will reset tomorrow.\n\n"
                "💳 Get premium subscription to remove limits."
            )
        await message.answer(text)
        return
    
    # Show presentation menu
    if language == "ru":
        text = (
            "📊 <b>Генератор презентаций</b>\n\n"
            f"Осталось сегодня: {remaining}/{limit}\n\n"
            "Напишите тему презентации, и я создам для вас:\n"
            "• Структуру слайдов\n"
            "• Контент для каждого слайда\n"
            "• Изображения (опционально)\n"
            "• Готовый PPTX файл\n\n"
            "Или выберите из шаблонов:"
        )
    else:
        text = (
            "📊 <b>Presentation Generator</b>\n\n"
            f"Remaining today: {remaining}/{limit}\n\n"
            "Write the presentation topic, and I'll create:\n"
            "• Slide structure\n"
            "• Content for each slide\n"
            "• Images (optional)\n"
            "• Ready PPTX file\n\n"
            "Or choose from templates:"
        )
    
    await state.set_state(PresentationStates.waiting_topic)
    await message.answer(text, reply_markup=get_presentation_menu_keyboard(language))


def get_presentation_menu_keyboard(language: str = "ru"):
    """Get presentation menu keyboard with templates."""
    texts = {
        "ru": {
            "business": "💼 Бизнес",
            "education": "📚 Обучение",
            "creative": "🎨 Креатив",
            "cancel": "❌ Отмена"
        },
        "en": {
            "business": "💼 Business",
            "education": "📚 Education",
            "creative": "🎨 Creative",
            "cancel": "❌ Cancel"
        }
    }
    
    t = texts.get(language, texts["ru"])
    builder = InlineKeyboardBuilder()
    
    builder.row(
        InlineKeyboardButton(text=t["business"], callback_data="pres:style:business"),
        InlineKeyboardButton(text=t["education"], callback_data="pres:style:educational")
    )
    builder.row(
        InlineKeyboardButton(text=t["creative"], callback_data="pres:style:creative")
    )
    builder.row(
        InlineKeyboardButton(text=t["cancel"], callback_data="pres:cancel")
    )
    
    return builder.as_markup()


@router.callback_query(F.data == "pres:cancel")
async def callback_presentation_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel presentation generation."""
    await state.clear()
    
    language = await user_service.get_user_language(callback.from_user.id)
    
    if language == "ru":
        await callback.message.edit_text("❌ Генерация презентации отменена.")
    else:
        await callback.message.edit_text("❌ Presentation generation cancelled.")
    
    await callback.answer()


@router.callback_query(F.data.startswith("pres:style:"))
async def callback_select_style(callback: CallbackQuery, state: FSMContext):
    """Handle style selection (when no topic yet)."""
    style = callback.data.split(":")[2]
    await state.update_data(style=style)
    
    language = await user_service.get_user_language(callback.from_user.id)
    
    style_names = {
        "ru": {"business": "деловом", "educational": "образовательном", "creative": "креативном"},
        "en": {"business": "business", "educational": "educational", "creative": "creative"}
    }
    
    style_name = style_names[language].get(style, style)
    
    if language == "ru":
        text = (
            f"📊 Стиль: <b>{style_name}</b>\n\n"
            "Теперь напишите тему презентации:"
        )
    else:
        text = (
            f"📊 Style: <b>{style_name}</b>\n\n"
            "Now write the presentation topic:"
        )
    
    cancel_kb = InlineKeyboardBuilder()
    cancel_text = "❌ Отмена" if language == "ru" else "❌ Cancel"
    cancel_kb.row(InlineKeyboardButton(text=cancel_text, callback_data="pres:cancel"))
    
    await callback.message.edit_text(text, reply_markup=cancel_kb.as_markup())
    await callback.answer()


@router.message(PresentationStates.waiting_topic)
async def process_presentation_topic(message: Message, state: FSMContext):
    """Process presentation topic and show configuration."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    topic = message.text.strip()
    
    if len(topic) < 3:
        if language == "ru":
            await message.answer("❌ Тема слишком короткая. Введите более подробное описание.")
        else:
            await message.answer("❌ Topic is too short. Enter a more detailed description.")
        return
    
    # Get previously selected style or default
    data = await state.get_data()
    style = data.get("style", "business")
    
    await state.update_data(topic=topic)
    await state.set_state(PresentationStates.configuring)
    
    if language == "ru":
        text = (
            f"📊 <b>Настройка презентации</b>\n\n"
            f"📝 Тема: {topic}\n"
            f"🎨 Стиль: {style}\n\n"
            "Выберите количество слайдов и опции:"
        )
    else:
        text = (
            f"📊 <b>Presentation Setup</b>\n\n"
            f"📝 Topic: {topic}\n"
            f"🎨 Style: {style}\n\n"
            "Choose number of slides and options:"
        )
    
    await message.answer(text, reply_markup=get_slides_config_keyboard(language, style))


def get_slides_config_keyboard(language: str, style: str):
    """Get slides configuration keyboard."""
    texts = {
        "ru": {
            "slides_5": "5 слайдов",
            "slides_7": "7 слайдов",
            "slides_10": "10 слайдов",
            "with_images": "🖼 С картинками",
            "no_images": "📝 Без картинок",
            "cancel": "❌ Отмена"
        },
        "en": {
            "slides_5": "5 slides",
            "slides_7": "7 slides",
            "slides_10": "10 slides",
            "with_images": "🖼 With images",
            "no_images": "📝 No images",
            "cancel": "❌ Cancel"
        }
    }
    
    t = texts.get(language, texts["ru"])
    builder = InlineKeyboardBuilder()
    
    # Slides count
    builder.row(
        InlineKeyboardButton(text=t["slides_5"], callback_data=f"pres:config:5:{style}:1"),
        InlineKeyboardButton(text=t["slides_7"], callback_data=f"pres:config:7:{style}:1"),
        InlineKeyboardButton(text=t["slides_10"], callback_data=f"pres:config:10:{style}:1")
    )
    
    # Images option
    builder.row(
        InlineKeyboardButton(text=t["with_images"], callback_data=f"pres:config:5:{style}:1"),
        InlineKeyboardButton(text=t["no_images"], callback_data=f"pres:config:5:{style}:0")
    )
    
    builder.row(
        InlineKeyboardButton(text=t["cancel"], callback_data="pres:cancel")
    )
    
    return builder.as_markup()


@router.callback_query(F.data.startswith("pres:config:"))
async def callback_start_generation(callback: CallbackQuery, state: FSMContext):
    """Start presentation generation with selected configuration."""
    parts = callback.data.split(":")
    slides_count = int(parts[2])
    style = parts[3]
    include_images = parts[4] == "1"
    
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    data = await state.get_data()
    topic = data.get("topic", "Presentation")
    
    # Check limits again
    can_use, _, _ = await limit_service.check_limit(user.id, RequestType.PRESENTATION)
    if not can_use:
        if language == "ru":
            await callback.message.edit_text("⚠️ Лимит презентаций исчерпан.")
        else:
            await callback.message.edit_text("⚠️ Presentation limit reached.")
        await state.clear()
        await callback.answer()
        return
    
    await state.set_state(PresentationStates.generating)
    
    if language == "ru":
        generating_text = (
            "⏳ <b>Генерация презентации...</b>\n\n"
            f"📝 Тема: {topic}\n"
            f"📊 Слайдов: {slides_count}\n"
            f"🖼 Картинки: {'Да' if include_images else 'Нет'}\n\n"
            "Это может занять 1-3 минуты..."
        )
    else:
        generating_text = (
            "⏳ <b>Generating presentation...</b>\n\n"
            f"📝 Topic: {topic}\n"
            f"📊 Slides: {slides_count}\n"
            f"🖼 Images: {'Yes' if include_images else 'No'}\n\n"
            "This may take 1-3 minutes..."
        )
    
    progress_msg = await callback.message.edit_text(generating_text)
    await callback.answer()
    
    try:
        # Progress callback
        async def update_progress(status):
            try:
                progress = status.get("progress", 0)
                msg = status.get("message", "")
                await progress_msg.edit_text(
                    f"{generating_text}\n\n"
                    f"📈 Прогресс: {progress}% - {msg}"
                )
            except:
                pass
        
        # Generate presentation
        pptx_bytes, info = await presentation_service.generate_presentation(
            topic=topic,
            slides_count=slides_count,
            style=style,
            include_images=include_images,
            language=language,
            progress_callback=update_progress
        )
        
        # Increment usage
        await limit_service.increment_usage(user.id, RequestType.PRESENTATION)
        
        # Send file
        filename = f"presentation_{topic[:30].replace(' ', '_')}.pptx"
        document = BufferedInputFile(pptx_bytes, filename=filename)
        
        if language == "ru":
            caption = (
                f"✅ <b>Презентация готова!</b>\n\n"
                f"📝 Тема: {info['title']}\n"
                f"📊 Слайдов: {info['slides_count']}\n"
                f"🖼 Изображений: {info['usage'].get('images_generated', 0)}"
            )
        else:
            caption = (
                f"✅ <b>Presentation ready!</b>\n\n"
                f"📝 Topic: {info['title']}\n"
                f"📊 Slides: {info['slides_count']}\n"
                f"🖼 Images: {info['usage'].get('images_generated', 0)}"
            )
        
        await progress_msg.delete()
        await callback.message.answer_document(document, caption=caption)
        
    except Exception as e:
        logger.error("Presentation generation failed", error=str(e), topic=topic)
        
        if language == "ru":
            error_text = (
                "❌ <b>Ошибка генерации</b>\n\n"
                "Не удалось создать презентацию. "
                "Попробуйте другую тему или повторите позже."
            )
        else:
            error_text = (
                "❌ <b>Generation Error</b>\n\n"
                "Failed to create presentation. "
                "Try a different topic or try again later."
            )
        
        await progress_msg.edit_text(error_text)
    
    finally:
        await state.clear()
