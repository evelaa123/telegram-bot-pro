"""
Inline mode handler.
Handles inline queries for use in any chat.
"""
import hashlib
from aiogram import Router, Bot
from aiogram.types import (
    InlineQuery,
    InlineQueryResultArticle,
    InputTextMessageContent,
    ChosenInlineResult
)

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.services.subscription_service import subscription_service
from database.models import RequestType, RequestStatus
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


async def check_channel_subscription_for_inline(bot: Bot, user_id: int) -> bool:
    """
    Check if user is subscribed to required channel.
    For inline mode we need to check channel subscription, not premium.
    
    Returns True if:
    - Subscription check is disabled in settings
    - No channel is configured
    - User is a member/admin/creator of the channel
    - Check fails (fail-open to avoid blocking users on errors)
    """
    # First, try to get settings from DB (they might be updated by admin)
    try:
        from bot.services.settings_service import settings_service
        bot_settings = await settings_service.get_bot_settings()
        subscription_check_enabled = bot_settings.get('subscription_check_enabled', False)
        channel_id = bot_settings.get('channel_id')
        channel_username = bot_settings.get('channel_username')
    except Exception:
        # Fallback to env settings
        subscription_check_enabled = getattr(settings, 'subscription_check_enabled', False)
        channel_id = getattr(settings, 'telegram_channel_id', None)
        channel_username = getattr(settings, 'telegram_channel_username', None)
    
    # If subscription check is disabled, allow
    if not subscription_check_enabled:
        logger.debug("Subscription check disabled", user_id=user_id)
        return True
    
    # If no channel configured, allow
    if not channel_id and not channel_username:
        logger.debug("No channel configured for subscription check", user_id=user_id)
        return True
    
    # Use channel_id if available, otherwise username
    # Make sure channel_id is properly formatted (negative number for channels)
    if channel_id:
        try:
            channel = int(channel_id)
            # Channels should have negative IDs starting with -100
            if channel > 0:
                channel = -channel
        except (ValueError, TypeError):
            channel = channel_id
    else:
        # For username, ensure it starts with @
        channel = channel_username if channel_username.startswith('@') else f"@{channel_username}"
    
    try:
        member = await bot.get_chat_member(channel, user_id)
        is_member = member.status in ('member', 'administrator', 'creator')
        logger.info(
            "Channel subscription check", 
            user_id=user_id, 
            channel=str(channel),
            status=member.status,
            is_member=is_member
        )
        return is_member
    except Exception as e:
        logger.warning(
            "Failed to check channel subscription - allowing access", 
            error=str(e), 
            user_id=user_id,
            channel=str(channel)
        )
        return True  # Allow if can't check (fail-open)


@router.inline_query()
async def handle_inline_query(inline_query: InlineQuery, bot: Bot):
    """Handle inline queries."""
    user = inline_query.from_user
    query = inline_query.query.strip()
    
    logger.info(
        "Inline query received",
        user_id=user.id,
        query=query[:50] if query else "(empty)"
    )
    
    # Регистрируем пользователя
    await user_service.get_or_create_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code
    )
    
    # Проверяем подписку на канал (не premium!)
    is_subscribed = await check_channel_subscription_for_inline(bot, user.id)
    
    if not is_subscribed:
        results = [
            InlineQueryResultArticle(
                id="subscription_required",
                title="🔒 Требуется подписка",
                description=f"Подпишитесь на {settings.telegram_channel_username}",
                input_message_content=InputTextMessageContent(
                    message_text=(
                        f"🔒 Для использования бота подпишитесь на канал "
                        f"{settings.telegram_channel_username}"
                    )
                )
            )
        ]
        await inline_query.answer(results, cache_time=60, is_personal=True)
        return
    
    # Проверяем лимиты
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.TEXT
    )
    
    if not has_limit:
        results = [
            InlineQueryResultArticle(
                id="limit_reached",
                title="⚠️ Лимит исчерпан",
                description=f"Использовано {current}/{max_limit} запросов",
                input_message_content=InputTextMessageContent(
                    message_text="⚠️ Дневной лимит запросов исчерпан. Попробуйте завтра."
                )
            )
        ]
        await inline_query.answer(results, cache_time=60, is_personal=True)
        return
    
    # Пустой запрос
    if not query:
        results = await get_help_results()
        await inline_query.answer(results, cache_time=300, is_personal=True)
        return
    
    # Обрабатываем запрос
    if query.startswith("/image "):
        prompt = query[7:].strip()
        results = await handle_inline_image(prompt, user.id) if prompt else await get_help_results()
    
    elif query.startswith("/translate ") or query.startswith("/перевод "):
        text = query.split(" ", 1)[1].strip() if " " in query else ""
        results = await handle_inline_translate(text, user.id) if text else await get_help_results()
    
    else:
        results = await handle_inline_text(query, user.id)
    
    await inline_query.answer(
        results,
        cache_time=0,
        is_personal=True
    )


@router.chosen_inline_result()
async def handle_chosen_inline_result(chosen_result: ChosenInlineResult):
    """
    Called when user selects an inline result.
    Here we count the usage!
    """
    user = chosen_result.from_user
    result_id = chosen_result.result_id
    query = chosen_result.query
    
    logger.info(
        "Inline result chosen",
        user_id=user.id,
        result_id=result_id,
        query=query[:50] if query else None
    )
    
    # Не считаем служебные результаты
    if result_id in ("subscription_required", "limit_reached", "error", 
                     "help_text", "help_image", "help_translate"):
        return
    
    # Определяем тип
    if result_id.startswith("translate_"):
        request_type = RequestType.TEXT
    elif result_id.startswith("image_"):
        # Для image промптов тоже считаем как TEXT (картинка не генерируется в inline)
        request_type = RequestType.TEXT
    else:
        request_type = RequestType.TEXT
    
    # Записываем использование
    await limit_service.increment_usage(user.id, request_type)
    
    await limit_service.record_request(
        telegram_id=user.id,
        request_type=request_type,
        prompt=query[:500] if query else "inline",
        model="gpt-4o-mini",
        status=RequestStatus.SUCCESS
    )
    
    logger.info(
        "Inline usage recorded",
        user_id=user.id,
        type=request_type.value
    )


async def get_help_results():
    """Help results for empty query."""
    return [
        InlineQueryResultArticle(
            id="help_text",
            title="💬 Задать вопрос",
            description="Просто напишите ваш вопрос",
            input_message_content=InputTextMessageContent(
                message_text="💡 Напишите: @bot ваш вопрос"
            )
        ),
        InlineQueryResultArticle(
            id="help_translate",
            title="🌐 Перевести текст",
            description="/translate текст или /перевод текст",
            input_message_content=InputTextMessageContent(
                message_text="💡 Напишите: @bot /translate hello world"
            )
        ),
        InlineQueryResultArticle(
            id="help_image",
            title="🖼 Промпт для картинки",
            description="/image описание картинки",
            input_message_content=InputTextMessageContent(
                message_text="💡 Напишите: @bot /image кот на луне"
            )
        )
    ]


async def handle_inline_text(query: str, user_id: int):
    """Quick GPT response for inline."""
    try:
        language = await user_service.get_user_language(user_id)
        
        messages = [
            {
                "role": "system",
                "content": (
                    "Provide brief, concise answers (2-3 sentences max). "
                    f"Respond in {'Russian' if language == 'ru' else 'the same language as the question'}."
                )
            },
            {"role": "user", "content": query}
        ]
        
        response, _ = await ai_service.generate_text(
            messages=messages,
            telegram_id=user_id,
            max_tokens=256
        )
        
        result_id = f"text_{hashlib.md5(f'{user_id}:{query}'.encode()).hexdigest()[:12]}"
        
        if len(response) > 4000:
            response = response[:4000] + "..."
        
        return [
            InlineQueryResultArticle(
                id=result_id,
                title="💬 Ответ",
                description=response[:100] + ("..." if len(response) > 100 else ""),
                input_message_content=InputTextMessageContent(
                    message_text=f"❓ <b>{query}</b>\n\n💬 {response}",
                    parse_mode="HTML"
                )
            )
        ]
        
    except Exception as e:
        logger.error("Inline text error", user_id=user_id, error=str(e))
        return [
            InlineQueryResultArticle(
                id="error",
                title="❌ Ошибка",
                description=str(e)[:50],
                input_message_content=InputTextMessageContent(
                    message_text="❌ Ошибка обработки запроса."
                )
            )
        ]


async def handle_inline_translate(text: str, user_id: int):
    """Quick translation."""
    try:
        messages = [
            {
                "role": "system",
                "content": (
                    "Translate the text. Russian→English, English→Russian. "
                    "Other languages→English. Only the translation, nothing else."
                )
            },
            {"role": "user", "content": text}
        ]
        
        translation, _ = await ai_service.generate_text(
            messages=messages,
            telegram_id=user_id,
            max_tokens=512
        )
        
        result_id = f"translate_{hashlib.md5(f'{user_id}:{text}'.encode()).hexdigest()[:12]}"
        
        return [
            InlineQueryResultArticle(
                id=result_id,
                title="🌐 Перевод",
                description=translation[:100] + ("..." if len(translation) > 100 else ""),
                input_message_content=InputTextMessageContent(
                    message_text=f"🌐 {translation}",
                    parse_mode="HTML"
                )
            )
        ]
        
    except Exception as e:
        logger.error("Inline translate error", error=str(e))
        return [
            InlineQueryResultArticle(
                id="error",
                title="❌ Ошибка перевода",
                description=str(e)[:50],
                input_message_content=InputTextMessageContent(
                    message_text="❌ Ошибка перевода."
                )
            )
        ]


async def handle_inline_image(prompt: str, user_id: int):
    """Return formatted image prompt (generation too slow for inline)."""
    result_id = f"image_{hashlib.md5(f'{user_id}:{prompt}'.encode()).hexdigest()[:12]}"
    
    return [
        InlineQueryResultArticle(
            id=result_id,
            title=f"🖼 {prompt[:50]}{'...' if len(prompt) > 50 else ''}",
            description="Нажмите чтобы отправить промпт",
            input_message_content=InputTextMessageContent(
                message_text=(
                    f"🖼 <b>Промпт для генерации:</b>\n"
                    f"<i>{prompt}</i>"
                ),
                parse_mode="HTML"
            )
        )
    ]
