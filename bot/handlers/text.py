"""
Text message handler.
Handles GPT text generation with streaming.
"""
import asyncio
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.inline import get_subscription_keyboard, get_download_keyboard
from bot.utils.helpers import convert_markdown_to_html, split_text_for_telegram, edit_or_send_long, send_as_file, send_as_docx
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from config import settings
import html as _html
import structlog

logger = structlog.get_logger()
router = Router()


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
        "💬 Текст и документы", "💬 Text & Documents",
        "💬 Текст", "💬 Text",  # backward compat
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
        
        # Common exit patterns — if user types a command/question
        # instead of a prompt, clear the state and fall through
        _text_lower = text.lower().strip()
        _exit_patterns = [
            "лимит", "настрой", "помощ", "подпис", "поддерж",
            "limit", "setting", "help", "subscri", "support",
            "какие у меня", "мои лимиты", "новый диалог",
            "my limits", "new dialog",
        ]
        _wants_exit = text.startswith("/") or any(p in _text_lower for p in _exit_patterns)
        
        # Обработка промпта для видео
        if state.startswith("video_prompt:"):
            if _wants_exit:
                await redis_client.clear_user_state(user.id)
                logger.info(f"User {user.id} exited video_prompt state")
            else:
                parts = state.split(":")
                if len(parts) >= 3:
                    model = parts[1]
                    duration = int(parts[2])
                    from bot.handlers.video import queue_video_generation
                    await queue_video_generation(message, user.id, text, model, duration)
                    return
        
        # Обработка ремикса видео
        elif state.startswith("video_remix:"):
            if _wants_exit:
                await redis_client.clear_user_state(user.id)
                logger.info(f"User {user.id} exited video_remix state")
            else:
                video_id = state.split(":")[1]
                from bot.handlers.video import queue_video_remix
                await queue_video_remix(message, user.id, video_id, text)
                return
        
        # Обработка промпта для изображения
        elif state.startswith("image_prompt:"):
            if _wants_exit:
                await redis_client.clear_user_state(user.id)
                logger.info(f"User {user.id} exited image_prompt state")
            else:
                size = state.split(":")[1]
                from bot.handlers.image import generate_image
                await generate_image(message, user.id, text, size)
                return
        
        # Обработка оживления фото (image-to-video)
        elif state.startswith("animate_photo:"):
            if _wants_exit:
                await redis_client.clear_user_state(user.id)
                logger.info(f"User {user.id} exited animate_photo state")
            else:
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
            if _wants_exit:
                await redis_client.clear_user_state(user.id)
                logger.info(f"User {user.id} exited long_video_prompt state")
            else:
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
        
        # Обработка цепочки редактирования фото
        elif state.startswith("photo_edit_chain:"):
            if _wants_exit:
                await redis_client.clear_user_state(user.id)
                logger.info(f"User {user.id} exited photo_edit_chain state")
            else:
                file_id = state.split(":", 1)[1]
                language = await user_service.get_user_language(user.id)
                try:
                    # Download the photo by file_id and edit it
                    file = await message.bot.get_file(file_id)
                    file_bytes_io = await message.bot.download_file(file.file_path)
                    image_data = file_bytes_io.read() if hasattr(file_bytes_io, 'read') else file_bytes_io
                    
                    from bot.handlers.photo import _handle_photo_edit_from_bytes
                    await _handle_photo_edit_from_bytes(
                        message=message,
                        user_id=user.id,
                        image_data=image_data,
                        caption=text,
                        language=language
                    )
                except Exception as e:
                    logger.error("Chain photo edit error", user_id=user.id, error=str(e))
                    await redis_client.clear_user_state(user.id)
                    if language == "ru":
                        await message.answer("❌ Не удалось отредактировать фото. Отправьте фото заново.")
                    else:
                        await message.answer("❌ Failed to edit photo. Please send the photo again.")
                return
        
        # Обработка сообщения в поддержку
        elif state == "support_message":
            from bot.handlers.support import handle_support_message
            await handle_support_message(message, user.id)
            return
    
    # ============================================
    # REPLY-TO-DOCUMENT/PHOTO В ЛИЧНЫХ ЧАТАХ
    # Позволяет пользователю ответить на сообщение бота с документом/фото
    # и дать инструкцию (например "суммаризируй" для docx)
    # ============================================
    if message.reply_to_message and message.chat.type == "private":
        reply_msg = message.reply_to_message
        
        # User replies to a message containing a document
        if reply_msg.document:
            language = await user_service.get_user_language(user.id)
            
            # Check if we have stored document context
            doc_context = await redis_client.get_document_context(user.id)
            
            if doc_context:
                # Use stored context
                from bot.handlers.document import process_document_request
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
            else:
                # Re-download and process the document
                from bot.handlers.document import handle_document
                from bot.services.document_service import document_service
                
                doc = reply_msg.document
                filename = doc.file_name or "document"
                
                if document_service.is_supported(filename):
                    try:
                        file = await message.bot.get_file(doc.file_id)
                        file_bytes_io = await message.bot.download_file(file.file_path)
                        file_data = file_bytes_io.read() if hasattr(file_bytes_io, 'read') else file_bytes_io
                        
                        doc_text, metadata, images = await document_service.process_document(
                            file_data=file_data,
                            filename=filename,
                        )
                        
                        if doc_text:
                            await redis_client.set_document_context(
                                user.id,
                                content=doc_text[:50000],
                                filename=filename
                            )
                        
                        from bot.handlers.document import process_document_request
                        await process_document_request(
                            message=message,
                            user_id=user.id,
                            text=doc_text or "",
                            images=images or [],
                            request=text,
                            filename=filename,
                            language=language
                        )
                        return
                    except Exception as e:
                        logger.error("Reply-to-document processing error", error=str(e))
        
        # User replies to a message containing a photo
        if reply_msg.photo:
            language = await user_service.get_user_language(user.id)
            photo = reply_msg.photo[-1]
            
            try:
                file = await message.bot.get_file(photo.file_id)
                file_bytes_io = await message.bot.download_file(file.file_path)
                image_data = file_bytes_io.read() if hasattr(file_bytes_io, 'read') else file_bytes_io
                
                # Check if this is an edit instruction (keyword + AI fallback)
                from bot.handlers.photo import _classify_photo_intent
                
                intent = await _classify_photo_intent(text, user.id)
                
                if intent == "EDIT":
                    # Route to image editing
                    from bot.handlers.photo import _handle_photo_edit_from_bytes
                    await _handle_photo_edit_from_bytes(
                        message=message,
                        user_id=user.id,
                        image_data=image_data,
                        caption=text,
                        language=language
                    )
                    return
                
                # Otherwise analyze with vision
                from bot.handlers.document import analyze_document_with_vision
                
                progress_msg = await message.answer(
                    "🔍 Анализирую изображение..." if language == "ru" else "🔍 Analyzing image..."
                )
                
                await analyze_document_with_vision(
                    message=message,
                    progress_msg=progress_msg,
                    user_id=user.id,
                    filename="photo.jpg",
                    images=[image_data],
                    language=language,
                    caption=text  # User's reply text becomes the instruction
                )
                return
            except Exception as e:
                logger.error("Reply-to-photo processing error", error=str(e))
    
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
    system_prompt = (
        "You are a helpful AI assistant in a Telegram bot. "
        "Respond in the same language as the user's message. "
        "Be concise but thorough. Use markdown formatting when appropriate.\n\n"
        
        "MEMORY: You DO have conversation memory within this chat session. "
        "The previous messages in this conversation are provided to you as context. "
        "If the user asks whether you remember previous messages — YES, you do, "
        "refer to the conversation history above. "
        "Context is kept for 30 minutes and up to 20 messages. "
        "After /new command or 30 min of inactivity, context resets.\n\n"
        
        "WEB SEARCH: You have a web_search tool. Use it ONLY when the user asks about:\n"
        "- Current events, news, prices, weather, exchange rates\n"
        "- Real-time data, sports scores, stock prices\n"
        "- Specific facts you are uncertain about\n"
        "- Questions that explicitly need up-to-date information\n"
        "Do NOT use web search for:\n"
        "- Greetings, casual conversation, jokes, small talk\n"
        "- General knowledge questions you can answer confidently\n"
        "- Creative tasks (writing, brainstorming, coding)\n"
        "- Questions about the conversation itself\n"
        "Do NOT fabricate facts — if truly unsure about factual claims, search first."
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(context)
    messages.append({"role": "user", "content": text})
    
    # Send initial "thinking" message
    if language == "ru":
        thinking_message = await message.answer("💭 Думаю...")
    else:
        thinking_message = await message.answer("💭 Thinking...")
    
    start_time = time.time()
    
    try:
        # ============================================
        # PRIMARY PATH: Responses API with web_search tool
        # The model autonomously decides when to search.
        # ============================================
        try:
            full_response, search_usage = await ai_service.generate_text_with_search(
                messages=messages,
                telegram_id=user.id,
                model=model,
                enable_search=True,
            )
            
            # Update thinking message to show search was used
            web_search_used = search_usage.get("web_search_used", False)
            if web_search_used:
                try:
                    if language == "ru":
                        await thinking_message.edit_text("🔍 Ищу информацию...")
                    else:
                        await thinking_message.edit_text("🔍 Searching for info...")
                except Exception:
                    pass
            
            # Append source links if search was used
            sources = search_usage.get("sources", [])
            if sources:
                source_links = "\n\n---\n🔗 "
                source_links += " | ".join(
                    f'<a href="{_html.escape(s["url"])}">{_html.escape(s.get("title", "Source")[:40])}</a>'
                    for s in sources[:3]
                )
                full_response += source_links
            
            # Display result
            if full_response.strip():
                await redis_client.set(f"user:{user.id}:last_response", full_response, ttl=3600)
                download_kb = get_download_keyboard(language)
                
                try:
                    await edit_or_send_long(
                        thinking_message=thinking_message,
                        original_message=message,
                        text=full_response,
                        reply_markup=download_kb
                    )
                except Exception:
                    pass
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Save to context
            await redis_client.add_to_context(user.id, "user", text)
            await redis_client.add_to_context(user.id, "assistant", full_response)
            
            # Increment usage
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
                model=model,
                duration_ms=duration_ms,
                web_search_used=web_search_used,
                response_length=len(full_response)
            )
            return
            
        except Exception as search_err:
            logger.warning("Responses API failed, falling back to streaming", error=str(search_err))
            # Update thinking message and fall through to streaming
            try:
                if language == "ru":
                    await thinking_message.edit_text("💭 Думаю...")
                else:
                    await thinking_message.edit_text("💭 Thinking...")
            except Exception:
                pass
        
        # ============================================
        # FALLBACK: Standard streaming path (no web search)
        # Used only if Responses API fails.
        # ============================================
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
        
        # Final update with complete response — split into multiple messages if needed
        if full_response.strip():
            # Store last response in Redis for download button
            await redis_client.set(f"user:{user.id}:last_response", full_response, ttl=3600)
            
            download_kb = get_download_keyboard(language)
            
            try:
                await edit_or_send_long(
                    thinking_message=thinking_message,
                    original_message=message,
                    text=full_response,
                    reply_markup=download_kb
                )
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
            "Text generation completed (streaming fallback)",
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


# ============================================
# DOWNLOAD RESPONSE AS FILE
# ============================================

@router.callback_query(F.data.startswith("text:download"))
async def callback_download_response(callback: CallbackQuery):
    """Send last AI response as a downloadable file (.docx or .txt)."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    last_response = await redis_client.get(f"user:{user.id}:last_response")
    
    if not last_response:
        no_data = "Нет ответа для скачивания." if language == "ru" else "No response to download."
        await callback.answer(no_data, show_alert=True)
        return
    
    await callback.answer()
    
    # Determine format from callback data
    # text:download:docx  or  text:download:txt  or  text:download (legacy = docx)
    parts = callback.data.split(":")
    fmt = parts[2] if len(parts) > 2 else "docx"
    
    if fmt == "txt":
        await send_as_file(
            message=callback.message,
            text=last_response,
            filename="response.txt",
            caption="📥 Ответ ИИ (.txt)" if language == "ru" else "📥 AI Response (.txt)"
        )
    else:
        # Default: formatted Word document
        await send_as_docx(
            message=callback.message,
            text=last_response,
            filename="response.docx",
            caption="📥 Ответ ИИ (.docx)" if language == "ru" else "📥 AI Response (.docx)"
        )
