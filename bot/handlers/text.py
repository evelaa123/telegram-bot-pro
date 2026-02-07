"""
Text message handler.
Handles GPT text generation with streaming.
"""
import asyncio
import re
import time
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.main import get_main_menu_keyboard
from bot.keyboards.inline import get_subscription_keyboard
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


def convert_markdown_to_html(text: str, is_streaming: bool = False) -> str:
    """
    Convert Markdown formatting to Telegram HTML.
    Handles: bold, italic, code, code blocks.
    
    Args:
        text: The markdown text to convert
        is_streaming: If True, be more conservative with conversions
                     (avoid converting incomplete markdown patterns)
    """
    # Escape HTML special characters first (except those we'll use for tags)
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    
    # Code blocks (```code```) - must be first to avoid conflicts
    # Only convert complete code blocks
    text = re.sub(r'```(\w*)\n?(.*?)```', r'<pre>\2</pre>', text, flags=re.DOTALL)
    
    # Inline code (`code`) - only if complete
    text = re.sub(r'`([^`\n]+)`', r'<code>\1</code>', text)
    
    # Bold (**text**) - only complete pairs
    text = re.sub(r'\*\*([^*]+?)\*\*', r'<b>\1</b>', text)
    
    # Bold (__text__) - only complete pairs  
    text = re.sub(r'__([^_]+?)__', r'<b>\1</b>', text)
    
    # Italic (*text*) - be careful not to match ** or incomplete
    # Only match if not preceded/followed by another *
    text = re.sub(r'(?<!\*)\*([^*\n]+?)\*(?!\*)', r'<i>\1</i>', text)
    
    # Italic (_text_) - be careful not to match __ or incomplete
    text = re.sub(r'(?<!_)_([^_\n]+?)_(?!_)', r'<i>\1</i>', text)
    
    # Strikethrough (~~text~~) - only complete pairs
    text = re.sub(r'~~([^~]+?)~~', r'<s>\1</s>', text)
    
    return text


@router.message(F.text)
async def handle_text_message(message: Message):
    """
    Handle text messages - generate GPT response with streaming.
    This handler should be registered LAST as a catch-all.
    """
    user = message.from_user
    text = message.text
    
    # Skip menu buttons - they are handled by dedicated handlers in start.py
    menu_buttons = {
        "💬 Текст", "💬 Text",
        "🖼 Изображение", "🖼 Image",
        "🎬 Видео", "🎬 Video",
        "📄 Документ", "📄 Document",
        "⚙️ Настройки", "⚙️ Settings",
        "📊 Лимиты", "📊 Limits",  # Fixed: was "Мои лимиты"
        "📊 Мои лимиты", "📊 My Limits",  # Keep old variants for compatibility
        "🔄 Новый диалог", "🔄 New Dialog",
        "🎤 Голос", "🎤 Voice",  # Added missing buttons
        "📊 Презентация", "📊 Presentation",
        "🗓 Ассистент", "🗓 Assistant",
        "📨 Поддержка", "📨 Support",  # Support button
        "💎 Подписка", "💎 Subscription",  # Subscription button
    }
    
    if text in menu_buttons:
        # These are handled by dedicated handlers, skip here
        return
    
    # ============================================
    # ПРОВЕРЯЕМ СОСТОЯНИЕ ПОЛЬЗОВАТЕЛЯ
    # ============================================
    state = await redis_client.get_user_state(user.id)
    
    if state:
        logger.info(f"User {user.id} has state: {state}")
        
        # Обработка промпта для видео
        if state.startswith("video_prompt:"):
            parts = state.split(":")
            if len(parts) >= 3:
                model = parts[1]
                duration = int(parts[2])
                from bot.handlers.video import queue_video_generation
                await queue_video_generation(message, user.id, text, model, duration)
                return
        
        # Обработка ремикса видео
        elif state.startswith("video_remix:"):
            video_id = state.split(":")[1]
            from bot.handlers.video import queue_video_remix
            await queue_video_remix(message, user.id, video_id, text)
            return
        
        # Обработка промпта для изображения
        elif state.startswith("image_prompt:"):
            size = state.split(":")[1]
            from bot.handlers.image import generate_image
            await generate_image(message, user.id, text, size)
            return
        
        # Обработка оживления фото (image-to-video)
        elif state.startswith("animate_photo:"):
            file_id = state.split(":", 1)[1]
            from bot.handlers.video import queue_animate_photo
            # Treat "." or empty/whitespace as auto-animate
            if not text.strip() or text.strip() == ".":
                prompt = "Animate this photo with gentle natural motion, subtle camera movement"
            else:
                prompt = text
            await queue_animate_photo(message, user.id, file_id, prompt)
            return
        
        # Обработка промпта для длинного видео
        elif state.startswith("long_video_prompt:"):
            parts = state.split(":")
            model = parts[1] if len(parts) > 1 else "sora-2"
            from bot.handlers.video import queue_long_video_generation
            await queue_long_video_generation(message, user.id, text, model)
            return
        
        # Обработка вопроса по документу
        elif state == "document_question":
            doc_context = await redis_client.get_document_context(user.id)
            if doc_context:
                from bot.handlers.document import process_document_request
                language = await user_service.get_user_language(user.id)
                await process_document_request(
                    message=message,
                    user_id=user.id,
                    text=doc_context["content"],
                    images=[],
                    request=text,
                    filename=doc_context["filename"],
                    language=language
                )
                return
        
        # Обработка сообщения в поддержку
        elif state == "support_message":
            from bot.handlers.support import handle_support_message
            await handle_support_message(message, user.id)
            return
    
    # ============================================
    # ОБЫЧНАЯ ГЕНЕРАЦИЯ ТЕКСТА (GPT)
    # ============================================
    
    # Get user settings
    user_settings = await user_service.get_user_settings(user.id)
    language = user_settings.get("language", "ru")
    
    # Always use cometapi with qwen-3-max for text generation
    ai_provider = "cometapi"
    model = settings.default_text_model  # qwen-3-max
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.TEXT
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита текстовых запросов на сегодня ({max_limit}).\n"
                "Лимиты обновятся в полночь UTC.\n\n"
                "💎 <b>Хотите больше запросов?</b>\n"
                "Оформите подписку для увеличения лимитов!",
                reply_markup=get_subscription_keyboard(language)
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily text request limit ({max_limit}).\n"
                "Limits reset at midnight UTC.\n\n"
                "💎 <b>Want more requests?</b>\n"
                "Subscribe to increase your limits!",
                reply_markup=get_subscription_keyboard(language)
            )
        return
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    # Get conversation context
    context = await redis_client.get_context(user.id)
    
    # Build messages for API
    messages = [
        {
            "role": "system",
            "content": (
                "You are a helpful AI assistant. Respond in the same language as the user's message. "
                "Be concise but thorough. Use markdown formatting when appropriate."
            )
        }
    ]
    messages.extend(context)
    messages.append({"role": "user", "content": text})
    
    # Send initial "thinking" message
    if language == "ru":
        thinking_message = await message.answer("💭 Думаю...")
    else:
        thinking_message = await message.answer("💭 Thinking...")
    
    start_time = time.time()
    
    try:
        # Stream the response using unified AI service
        full_response = ""
        last_update_time = time.time()
        token_count = 0
                
        async for chunk, is_complete in ai_service.generate_text_stream(
            messages=messages,
            telegram_id=user.id,
            model=model
        ):
            full_response += chunk
            token_count += 1
            
            current_time = time.time()
            time_since_update = (current_time - last_update_time) * 1000  # ms
            
            # Update message every N tokens or every 500ms
            should_update = (
                token_count >= settings.stream_token_batch_size or
                time_since_update >= settings.stream_update_interval_ms or
                is_complete
            )
            
            if should_update and full_response.strip():
                try:
                    # Truncate for Telegram's 4096 char limit
                    display_text = full_response
                    if len(display_text) > 4000:
                        display_text = display_text[:4000] + "..."
                    
                    # Convert markdown to HTML for reliable rendering
                    html_text = convert_markdown_to_html(display_text)
                    
                    try:
                        await thinking_message.edit_text(
                            html_text,
                            parse_mode="HTML"
                        )
                    except Exception:
                        # If HTML fails, send as plain text
                        await thinking_message.edit_text(display_text)
                    
                    last_update_time = current_time
                    token_count = 0
                    
                    # Small delay to avoid rate limits
                    if not is_complete:
                        await asyncio.sleep(0.05)
                        
                except Exception as e:
                    # Ignore edit errors (e.g., message not modified)
                    if "message is not modified" not in str(e).lower():
                        logger.warning("Failed to update message", error=str(e))
        
        # Final update with complete response
        if full_response.strip():
            try:
                display_text = full_response
                if len(display_text) > 4000:
                    display_text = display_text[:4000] + "\n\n... (ответ обрезан)"
                
                # Convert markdown to HTML for reliable rendering
                html_text = convert_markdown_to_html(display_text)
                
                try:
                    await thinking_message.edit_text(
                        html_text,
                        parse_mode="HTML"
                    )
                except Exception:
                    # If HTML parsing fails, try plain text
                    await thinking_message.edit_text(display_text)
            except Exception:
                pass
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Save to context
        await redis_client.add_to_context(user.id, "user", text)
        await redis_client.add_to_context(user.id, "assistant", full_response)
        
        # Increment usage and record request
        await limit_service.increment_usage(user.id, RequestType.TEXT)
        await limit_service.record_request(
            telegram_id=user.id,
            request_type=RequestType.TEXT,
            prompt=text[:500],
            response_preview=full_response[:500],
            model=model,
            status=RequestStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(
            "Text generation completed",
            user_id=user.id,
            provider=ai_provider,
            model=model,
            duration_ms=duration_ms,
            response_length=len(full_response)
        )
        
    except Exception as e:
        logger.error("Text generation error", user_id=user.id, error=str(e))
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Record failed request
        await limit_service.record_request(
            telegram_id=user.id,
            request_type=RequestType.TEXT,
            prompt=text[:500],
            model=model,
            status=RequestStatus.FAILED,
            error_message=str(e),
            duration_ms=duration_ms
        )
        
        if language == "ru":
            error_text = (
                "❌ Произошла ошибка при генерации ответа.\n"
                "Попробуйте ещё раз или измените запрос."
            )
        else:
            error_text = (
                "❌ An error occurred while generating the response.\n"
                "Please try again or modify your request."
            )
        
        try:
            await thinking_message.edit_text(error_text)
        except Exception:
            await message.answer(error_text)
