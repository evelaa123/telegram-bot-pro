"""
Assistant features handlers.
Includes: Diary, Reminders, Alarms.
"""
from datetime import datetime, date, timedelta, timezone
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

from bot.services.user_service import user_service
from bot.keyboards.main import get_assistant_menu_keyboard
from bot.keyboards.inline import InlineKeyboardBuilder, InlineKeyboardButton
from database.connection import async_session_maker as async_session
from database.models import DiaryEntry, Reminder, ReminderType
from sqlalchemy import select, and_, delete
from sqlalchemy.orm import selectinload

import structlog

logger = structlog.get_logger()
router = Router()


class DiaryStates(StatesGroup):
    """FSM states for diary operations."""
    writing_entry = State()
    editing_entry = State()


class ReminderStates(StatesGroup):
    """FSM states for reminder operations."""
    setting_title = State()
    setting_time = State()
    setting_description = State()


class AlarmStates(StatesGroup):
    """FSM states for alarm operations."""
    setting_time = State()
    setting_recurrence = State()


# =========================================
# Assistant Menu
# =========================================

@router.message(F.text.in_({"🗓 Ассистент", "🗓 Assistant"}))
async def show_assistant_menu(message: Message):
    """Show assistant features menu."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        text = (
            "🗓 <b>Персональный ассистент</b>\n\n"
            "Выберите функцию:\n\n"
            "📔 <b>Ежедневник</b> — записывайте важные события и мысли\n"
            "🔔 <b>Напоминания</b> — получайте напоминания о событиях канала\n"
            "⏰ <b>Будильник</b> — установите персональные напоминания"
        )
    else:
        text = (
            "🗓 <b>Personal Assistant</b>\n\n"
            "Choose a feature:\n\n"
            "📔 <b>Diary</b> — write down important events and thoughts\n"
            "🔔 <b>Reminders</b> — get reminders about channel events\n"
            "⏰ <b>Alarm</b> — set personal reminders"
        )
    
    await message.answer(text, reply_markup=get_assistant_menu_keyboard(language))


@router.callback_query(F.data == "assistant:back")
async def callback_assistant_back(callback: CallbackQuery):
    """Go back from assistant menu."""
    await callback.message.delete()
    await callback.answer()


# =========================================
# Diary Functions
# =========================================

@router.callback_query(F.data == "assistant:diary")
async def callback_diary_menu(callback: CallbackQuery):
    """Show diary menu."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        text = (
            "📔 <b>Ежедневник</b>\n\n"
            "Здесь вы можете вести личные записи.\n"
            "Выберите действие:"
        )
    else:
        text = (
            "📔 <b>Diary</b>\n\n"
            "Here you can keep personal notes.\n"
            "Choose an action:"
        )
    
    keyboard = get_diary_keyboard(language)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


def get_diary_keyboard(language: str = "ru"):
    """Get diary actions keyboard."""
    texts = {
        "ru": {
            "new": "✏️ Новая запись",
            "today": "📅 Сегодня",
            "history": "📖 История",
            "back": "◀️ Назад"
        },
        "en": {
            "new": "✏️ New Entry",
            "today": "📅 Today",
            "history": "📖 History",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text=t["new"], callback_data="diary:new"))
    builder.row(
        InlineKeyboardButton(text=t["today"], callback_data="diary:today"),
        InlineKeyboardButton(text=t["history"], callback_data="diary:history")
    )
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="diary:back"))
    
    return builder.as_markup()


@router.callback_query(F.data == "diary:back")
async def callback_diary_back(callback: CallbackQuery):
    """Go back to assistant menu."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    if language == "ru":
        text = (
            "🗓 <b>Персональный ассистент</b>\n\n"
            "Выберите функцию:"
        )
    else:
        text = (
            "🗓 <b>Personal Assistant</b>\n\n"
            "Choose a feature:"
        )
    
    await callback.message.edit_text(text, reply_markup=get_assistant_menu_keyboard(language))
    await callback.answer()


@router.callback_query(F.data == "diary:new")
async def callback_diary_new(callback: CallbackQuery, state: FSMContext):
    """Start creating new diary entry."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    await state.set_state(DiaryStates.writing_entry)
    
    if language == "ru":
        text = (
            "✏️ <b>Новая запись в ежедневнике</b>\n\n"
            "Напишите вашу запись. Вы можете описать события дня, "
            "свои мысли или важные заметки.\n\n"
            "Отправьте текст сообщением:"
        )
    else:
        text = (
            "✏️ <b>New Diary Entry</b>\n\n"
            "Write your entry. You can describe the day's events, "
            "your thoughts, or important notes.\n\n"
            "Send the text as a message:"
        )
    
    cancel_kb = InlineKeyboardBuilder()
    cancel_text = "❌ Отмена" if language == "ru" else "❌ Cancel"
    cancel_kb.row(InlineKeyboardButton(text=cancel_text, callback_data="diary:cancel"))
    
    await callback.message.edit_text(text, reply_markup=cancel_kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "diary:cancel")
async def callback_diary_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel diary entry."""
    await state.clear()
    await callback_diary_menu(callback)


@router.message(DiaryStates.writing_entry)
async def process_diary_entry(message: Message, state: FSMContext):
    """Process and save diary entry."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    content = message.text
    today = date.today()
    
    # Get user from DB
    db_user = await user_service.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    
    # Save diary entry
    async with async_session() as session:
        entry = DiaryEntry(
            user_id=db_user.id,
            date=today,
            content=content
        )
        session.add(entry)
        await session.commit()
    
    await state.clear()
    
    if language == "ru":
        text = (
            "✅ <b>Запись сохранена!</b>\n\n"
            f"📅 Дата: {today.strftime('%d.%m.%Y')}\n"
            f"📝 Текст: {content[:100]}{'...' if len(content) > 100 else ''}"
        )
    else:
        text = (
            "✅ <b>Entry saved!</b>\n\n"
            f"📅 Date: {today.strftime('%Y-%m-%d')}\n"
            f"📝 Text: {content[:100]}{'...' if len(content) > 100 else ''}"
        )
    
    await message.answer(text, reply_markup=get_diary_keyboard(language))


@router.callback_query(F.data == "diary:today")
async def callback_diary_today(callback: CallbackQuery):
    """Show today's diary entries."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    db_user = await user_service.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    today = date.today()
    
    async with async_session() as session:
        result = await session.execute(
            select(DiaryEntry)
            .where(and_(
                DiaryEntry.user_id == db_user.id,
                DiaryEntry.date == today
            ))
            .order_by(DiaryEntry.created_at.desc())
        )
        entries = result.scalars().all()
    
    if not entries:
        if language == "ru":
            text = f"📅 <b>Записи за {today.strftime('%d.%m.%Y')}</b>\n\nЗаписей пока нет."
        else:
            text = f"📅 <b>Entries for {today.strftime('%Y-%m-%d')}</b>\n\nNo entries yet."
    else:
        if language == "ru":
            text = f"📅 <b>Записи за {today.strftime('%d.%m.%Y')}</b>\n\n"
        else:
            text = f"📅 <b>Entries for {today.strftime('%Y-%m-%d')}</b>\n\n"
        
        for i, entry in enumerate(entries, 1):
            time_str = entry.created_at.strftime('%H:%M')
            content_preview = entry.content[:200] + '...' if len(entry.content) > 200 else entry.content
            text += f"<b>{i}. {time_str}</b>\n{content_preview}\n\n"
    
    await callback.message.edit_text(text, reply_markup=get_diary_keyboard(language))
    await callback.answer()


@router.callback_query(F.data == "diary:history")
async def callback_diary_history(callback: CallbackQuery):
    """Show diary history (last 7 days)."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    db_user = await user_service.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    week_ago = date.today() - timedelta(days=7)
    
    async with async_session() as session:
        result = await session.execute(
            select(DiaryEntry)
            .where(and_(
                DiaryEntry.user_id == db_user.id,
                DiaryEntry.date >= week_ago
            ))
            .order_by(DiaryEntry.date.desc(), DiaryEntry.created_at.desc())
            .limit(10)
        )
        entries = result.scalars().all()
    
    if not entries:
        if language == "ru":
            text = "📖 <b>История записей</b>\n\nЗаписей за последнюю неделю нет."
        else:
            text = "📖 <b>Entry History</b>\n\nNo entries in the last week."
    else:
        if language == "ru":
            text = "📖 <b>История записей (последние 7 дней)</b>\n\n"
        else:
            text = "📖 <b>Entry History (last 7 days)</b>\n\n"
        
        current_date = None
        for entry in entries:
            if entry.date != current_date:
                current_date = entry.date
                date_str = current_date.strftime('%d.%m.%Y') if language == "ru" else current_date.strftime('%Y-%m-%d')
                text += f"\n📅 <b>{date_str}</b>\n"
            
            time_str = entry.created_at.strftime('%H:%M')
            content_preview = entry.content[:100] + '...' if len(entry.content) > 100 else entry.content
            text += f"• {time_str}: {content_preview}\n"
    
    await callback.message.edit_text(text, reply_markup=get_diary_keyboard(language))
    await callback.answer()


# =========================================
# Reminders Functions
# =========================================

@router.callback_query(F.data == "assistant:reminders")
async def callback_reminders_menu(callback: CallbackQuery):
    """Show reminders menu."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    db_user = await user_service.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    
    # Get active reminders
    async with async_session() as session:
        result = await session.execute(
            select(Reminder)
            .where(and_(
                Reminder.user_id == db_user.id,
                Reminder.is_active == True,
                Reminder.type == ReminderType.CHANNEL_EVENT
            ))
            .order_by(Reminder.remind_at)
            .limit(5)
        )
        reminders = result.scalars().all()
    
    if language == "ru":
        text = "🔔 <b>Напоминания о событиях канала</b>\n\n"
        if reminders:
            for r in reminders:
                time_str = r.remind_at.strftime('%d.%m %H:%M')
                text += f"• {time_str}: {r.title}\n"
        else:
            text += "У вас пока нет активных напоминаний.\n\n"
        text += "\nЧтобы создать напоминание, перешлите пост из канала."
    else:
        text = "🔔 <b>Channel Event Reminders</b>\n\n"
        if reminders:
            for r in reminders:
                time_str = r.remind_at.strftime('%Y-%m-%d %H:%M')
                text += f"• {time_str}: {r.title}\n"
        else:
            text += "You have no active reminders.\n\n"
        text += "\nTo create a reminder, forward a post from the channel."
    
    keyboard = get_reminders_keyboard(language)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


def get_reminders_keyboard(language: str = "ru"):
    """Get reminders actions keyboard."""
    texts = {
        "ru": {
            "list": "📋 Все напоминания",
            "clear": "🗑 Очистить",
            "back": "◀️ Назад"
        },
        "en": {
            "list": "📋 All Reminders",
            "clear": "🗑 Clear All",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text=t["list"], callback_data="reminders:list"))
    builder.row(InlineKeyboardButton(text=t["clear"], callback_data="reminders:clear"))
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="reminders:back"))
    
    return builder.as_markup()


@router.callback_query(F.data == "reminders:back")
async def callback_reminders_back(callback: CallbackQuery):
    """Go back to assistant menu."""
    await callback_diary_back(callback)


# =========================================
# Alarm Functions
# =========================================

@router.callback_query(F.data == "assistant:alarm")
async def callback_alarm_menu(callback: CallbackQuery):
    """Show alarm menu."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    db_user = await user_service.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    
    # Get active alarms
    async with async_session() as session:
        result = await session.execute(
            select(Reminder)
            .where(and_(
                Reminder.user_id == db_user.id,
                Reminder.is_active == True,
                Reminder.type == ReminderType.ALARM
            ))
            .order_by(Reminder.remind_at)
            .limit(5)
        )
        alarms = result.scalars().all()
    
    if language == "ru":
        text = "⏰ <b>Будильник</b>\n\n"
        if alarms:
            text += "<b>Активные будильники:</b>\n"
            for a in alarms:
                time_str = a.remind_at.strftime('%H:%M')
                recurrence = ""
                if a.recurrence == "daily":
                    recurrence = " (ежедневно)"
                text += f"• {time_str}{recurrence}: {a.title}\n"
        else:
            text += "У вас нет активных будильников."
    else:
        text = "⏰ <b>Alarm</b>\n\n"
        if alarms:
            text += "<b>Active alarms:</b>\n"
            for a in alarms:
                time_str = a.remind_at.strftime('%H:%M')
                recurrence = ""
                if a.recurrence == "daily":
                    recurrence = " (daily)"
                text += f"• {time_str}{recurrence}: {a.title}\n"
        else:
            text += "You have no active alarms."
    
    keyboard = get_alarm_keyboard(language)
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()


def get_alarm_keyboard(language: str = "ru"):
    """Get alarm actions keyboard."""
    texts = {
        "ru": {
            "new": "➕ Новый будильник",
            "list": "📋 Все будильники",
            "back": "◀️ Назад"
        },
        "en": {
            "new": "➕ New Alarm",
            "list": "📋 All Alarms",
            "back": "◀️ Back"
        }
    }
    
    t = texts.get(language, texts["ru"])
    builder = InlineKeyboardBuilder()
    
    builder.row(InlineKeyboardButton(text=t["new"], callback_data="alarm:new"))
    builder.row(InlineKeyboardButton(text=t["list"], callback_data="alarm:list"))
    builder.row(InlineKeyboardButton(text=t["back"], callback_data="alarm:back"))
    
    return builder.as_markup()


@router.callback_query(F.data == "alarm:back")
async def callback_alarm_back(callback: CallbackQuery):
    """Go back to assistant menu."""
    await callback_diary_back(callback)


@router.callback_query(F.data == "alarm:new")
async def callback_alarm_new(callback: CallbackQuery, state: FSMContext):
    """Start creating new alarm."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    await state.set_state(AlarmStates.setting_time)
    
    if language == "ru":
        text = (
            "⏰ <b>Новый будильник</b>\n\n"
            "Введите время в формате ЧЧ:ММ\n"
            "Например: 07:30 или 14:00"
        )
    else:
        text = (
            "⏰ <b>New Alarm</b>\n\n"
            "Enter time in format HH:MM\n"
            "Example: 07:30 or 14:00"
        )
    
    cancel_kb = InlineKeyboardBuilder()
    cancel_text = "❌ Отмена" if language == "ru" else "❌ Cancel"
    cancel_kb.row(InlineKeyboardButton(text=cancel_text, callback_data="alarm:cancel"))
    
    await callback.message.edit_text(text, reply_markup=cancel_kb.as_markup())
    await callback.answer()


@router.callback_query(F.data == "alarm:cancel")
async def callback_alarm_cancel(callback: CallbackQuery, state: FSMContext):
    """Cancel alarm creation."""
    await state.clear()
    await callback_alarm_menu(callback)


@router.message(AlarmStates.setting_time)
async def process_alarm_time(message: Message, state: FSMContext):
    """Process alarm time input."""
    user = message.from_user
    language = await user_service.get_user_language(user.id)
    
    time_str = message.text.strip()
    
    # Parse time
    try:
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            raise ValueError()
    except:
        if language == "ru":
            await message.answer("❌ Неверный формат времени. Используйте ЧЧ:ММ (например, 07:30)")
        else:
            await message.answer("❌ Invalid time format. Use HH:MM (e.g., 07:30)")
        return
    
    # Save alarm
    db_user = await user_service.get_or_create_user(user.id, user.username, user.first_name, user.last_name)
    
    # Calculate next alarm time
    now = datetime.now(timezone.utc)
    alarm_time = now.replace(hour=hours, minute=minutes, second=0, microsecond=0)
    if alarm_time <= now:
        alarm_time += timedelta(days=1)
    
    async with async_session() as session:
        reminder = Reminder(
            user_id=db_user.id,
            type=ReminderType.ALARM,
            title=f"Будильник на {time_str}" if language == "ru" else f"Alarm at {time_str}",
            remind_at=alarm_time,
            recurrence="daily"  # Default to daily
        )
        session.add(reminder)
        await session.commit()
    
    await state.clear()
    
    if language == "ru":
        text = f"✅ <b>Будильник установлен!</b>\n\nВремя: {time_str}\nПовтор: ежедневно"
    else:
        text = f"✅ <b>Alarm set!</b>\n\nTime: {time_str}\nRepeat: daily"
    
    await message.answer(text, reply_markup=get_alarm_keyboard(language))
