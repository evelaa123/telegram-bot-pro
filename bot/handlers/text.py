"""
Text message handler.
Handles GPT text generation with streaming.
"""
import asyncio
import re
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.inline import get_subscription_keyboard, get_download_keyboard
from bot.utils.helpers import convert_markdown_to_html, split_text_for_telegram, edit_or_send_long, send_as_docx
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from config import settings
import html as _html
import structlog

logger = structlog.get_logger()
router = Router()


def _should_search_web(text: str) -> bool:
    """
    Determine if the user's message requires a web search.
    Only return True for queries that genuinely need real-time / up-to-date info.
    This prevents the model from searching on greetings, casual talk, general knowledge.
    """
    text_lower = text.lower().strip()
    
    # Too short messages are almost never search-worthy
    if len(text_lower) < 5:
        return False
    
    # Russian keywords that indicate a need for current/real-time data
    ru_search_triggers = [
        "новости", "новость", "погода", "курс", "валют", "цена", "стоимость",
        "сколько стоит", "какой курс", "какая погода", "что случилось",
        "что произошло", "последние события", "сегодня", "вчера",
        "актуальн", "свежие", "текущ", "прямо сейчас",
        "найди", "найти", "загугли", "погугли", "поищи", "ищи в интернете",
        "что нового", "расписание", "результат матча", "счёт", "счет",
        "когда выйдет", "когда выходит", "дата выхода", "релиз",
        "где купить", "где находится", "адрес", "как доехать",
        "рецепт", "инструкция по",
    ]
    
    # English keywords
    en_search_triggers = [
        "news", "weather", "price", "cost", "exchange rate", "stock",
        "what happened", "latest", "current", "today", "yesterday",
        "search for", "google", "look up", "find me", "find info",
        "score", "match result", "release date", "when does",
        "where to buy", "where is", "address", "how to get to",
        "recipe for", "instructions for",
    ]
    
    # Question patterns that imply factual lookup
    question_patterns = [
        r"(?:кто|что|где|когда|сколько|какой|какая|какое|какие)\s+(?:такое|такой|такая|такие)?\s*\w+\?",
        r"(?:who|what|where|when|how much|how many)\s+\w+.*\?",
    ]
    
    for trigger in ru_search_triggers + en_search_triggers:
        if trigger in text_lower:
            return True
    
    for pattern in question_patterns:
        if re.search(pattern, text_lower):
            # Only search if the question seems factual (not conversational)
            conversational = [
                "как дела", "как ты", "что умеешь", "кто ты", "как тебя зовут",
                "how are you", "what can you do", "who are you", "what is your name",
                "что ты", "как мне", "помоги", "объясни",
            ]
            if not any(c in text_lower for c in conversational):
                return True
    
    return False


def _detect_intent(text: str) -> dict | None:
    """
    Detect if the user explicitly wants to generate media or execute a command.
    Mirrors the voice classifier — everything you can do by voice, you can do by text.
    
    Returns:
        {"type": "IMAGE"|"VIDEO"|"PRESENTATION"|"COMMAND", "prompt": "...", "command": "..."}
        or None if this is a regular text message for GPT.
    """
    text_lower = text.lower().strip()
    
    # --- COMMAND patterns (natural language shortcuts) ---
    command_patterns = {
        "new_dialog": [
            "новый диалог", "очисти контекст", "начни заново", "сбрось контекст",
            "new dialog", "clear context", "start over", "reset context",
        ],
        "limits": [
            "мои лимиты", "покажи лимиты", "сколько запросов", "сколько осталось",
            "my limits", "show limits", "how many requests",
        ],
        "help": [
            "что ты умеешь", "справка",
            "what can you do",
        ],
        "settings": [
            "открой настройки", "покажи настройки",
            "open settings", "show settings",
        ],
    }
    for cmd, patterns in command_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                return {"type": "COMMAND", "prompt": text, "command": cmd}
    
    # --- VIDEO patterns (check BEFORE image — "generate video" must not match image) ---
    video_patterns = [
        r"(?:создай|сгенерируй|сделай)\s+(?:мне\s+)?видео",
        r"(?:create|generate|make)\s+(?:me\s+)?(?:a\s+)?video",
    ]
    for pat in video_patterns:
        if re.search(pat, text_lower):
            cleaned = text
            for trigger in [
                "создай мне видео", "создай видео", "сгенерируй мне видео",
                "сгенерируй видео", "сделай мне видео", "сделай видео",
                "create me a video", "create a video", "create video",
                "generate me a video", "generate a video", "generate video",
                "make me a video", "make a video", "make video",
            ]:
                cleaned = re.sub(rf'(?i)^{re.escape(trigger)}\s*', '', cleaned).strip()
            return {"type": "VIDEO", "prompt": cleaned if cleaned else text}
    
    # --- PRESENTATION patterns (check BEFORE image — "создай презентацию" must not match image) ---
    pres_patterns = [
        r"(?:создай|сделай|сгенерируй)\s+(?:мне\s+)?презентаци",
        r"(?:create|make|generate)\s+(?:me\s+)?(?:a\s+)?presentation",
    ]
    for pat in pres_patterns:
        if re.search(pat, text_lower):
            cleaned = text
            for trigger in [
                "создай мне презентацию", "создай презентацию",
                "сделай мне презентацию", "сделай презентацию",
                "сгенерируй мне презентацию", "сгенерируй презентацию",
                "create me a presentation", "create a presentation", "create presentation",
                "make me a presentation", "make a presentation", "make presentation",
                "generate me a presentation", "generate a presentation", "generate presentation",
            ]:
                cleaned = re.sub(rf'(?i)^{re.escape(trigger)}\s*', '', cleaned).strip()
            return {"type": "PRESENTATION", "prompt": cleaned if cleaned else text}
    
    # --- IMAGE patterns (last — catch-all for "draw X", "generate X") ---
    image_patterns = [
        r"(?:сгенерируй|нарисуй|создай|сделай|покажи)\s+(?:мне\s+)?(?:картинк\w*|изображени\w*|фото\w*|пикч\w*|арт\w*)",
        r"(?:сгенери(?:руй)?|нарисуй)\s+",
        r"(?:generate|draw|create|make)\s+(?:me\s+)?(?:an?\s+)?(?:image|picture|photo|art|illustration)",
        r"(?:draw|generate)\s+(?:me\s+)?(?:a\s+)?",
    ]
    for pat in image_patterns:
        if re.search(pat, text_lower):
            cleaned = text
            for trigger in [
                "нарисуй мне", "нарисуй", "сгенерируй мне картинку", "сгенерируй картинку",
                "сгенерируй мне изображение", "сгенерируй изображение",
                "сгенерируй мне фото", "сгенерируй фото",
                "сгенерируй мне", "сгенерируй", "сгенери мне", "сгенери",
                "создай картинку", "создай изображение", "сделай картинку", "сделай фото",
                "покажи мне", "покажи",
                "создай мне", "создай", "сделай мне", "сделай",
                "draw me a", "draw me an", "draw me", "draw a", "draw an", "draw",
                "generate me a", "generate me an", "generate me",
                "generate a", "generate an", "generate",
                "create image", "create a", "create an", "create",
                "make picture", "make a", "make an", "make",
            ]:
                cleaned = re.sub(rf'(?i)^{re.escape(trigger)}\s*', '', cleaned).strip()
            return {"type": "IMAGE", "prompt": cleaned if cleaned else text}
    
    return None


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
        
        # ---- Intent-aware state routing ----
        # Before routing to any active state, detect if the user is starting
        # a COMPLETELY NEW intent (command, image, video, presentation).
        # If so, clear the active state and process the new intent.
        # This prevents bugs like: user is in photo_edit_chain, says
        # "создай картинку кота" → bot tries to edit the photo instead.
        _new_intent = _detect_intent(text)
        _is_slash_command = text.startswith("/")
        
        # If user typed a slash command or an explicit new intent,
        # exit the current state and fall through to normal routing.
        if _is_slash_command or _new_intent:
            await redis_client.clear_user_state(user.id)
            logger.info(
                f"User {user.id} exited {state} state due to new intent: "
                f"{'/' if _is_slash_command else _new_intent.get('type', '?')}"
            )
            # Fall through — the code below will handle intent routing or GPT
        else:
            # No explicit new intent → route to the active state handler
            
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
            
            # Обработка цепочки редактирования фото
            # (state is now ONLY set by the "Edit Again" button)
            elif state.startswith("photo_edit_chain:"):
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
    # DETECT EXPLICIT INTENTS: image / video / presentation / commands
    # Before sending to GPT, check if user wants to generate media
    # or execute a command via natural language.
    # Everything available via voice is available via text too.
    # ============================================
    _intent = _detect_intent(text)
    
    if _intent:
        user_settings = await user_service.get_user_settings(user.id)
        language = user_settings.get("language", "ru")
        
        if _intent["type"] == "COMMAND":
            cmd = _intent.get("command")
            if cmd == "new_dialog":
                await redis_client.clear_context(user.id)
                await redis_client.clear_document_context(user.id)
                await redis_client.clear_user_state(user.id)
                txt = "🔄 Контекст очищен. Начнём заново!" if language == "ru" else "🔄 Context cleared. Let's start fresh!"
                await message.answer(txt)
                return
            elif cmd == "limits":
                limits_text = await limit_service.get_limits_text(user.id, language)
                await message.answer(limits_text, parse_mode="HTML")
                return
            elif cmd == "help":
                from bot.handlers.start import cmd_help
                await cmd_help(message)
                return
            elif cmd == "settings":
                from bot.handlers.settings import show_settings
                await show_settings(message)
                return
        
        elif _intent["type"] == "IMAGE":
            has_limit, _, max_limit = await limit_service.check_limit(user.id, RequestType.IMAGE)
            if not has_limit:
                txt = f"⚠️ Лимит картинок исчерпан ({max_limit})" if language == "ru" else f"⚠️ Image limit reached ({max_limit})"
                await message.answer(txt)
                return
            from bot.handlers.image import generate_image
            await generate_image(message, user.id, _intent["prompt"], "1024x1024")
            return
        
        elif _intent["type"] == "VIDEO":
            from bot.keyboards.inline import get_video_model_keyboard
            if language == "ru":
                txt = (
                    f"🎬 <b>Генерация видео</b>\n\n"
                    f"📝 Промпт: <i>{_intent['prompt'][:200]}</i>\n\n"
                    "Выберите модель:"
                )
            else:
                txt = (
                    f"🎬 <b>Video Generation</b>\n\n"
                    f"📝 Prompt: <i>{_intent['prompt'][:200]}</i>\n\n"
                    "Choose model:"
                )
            await redis_client.set_user_state(user.id, f"video_voice_prompt:{_intent['prompt'][:500]}", ttl=300)
            await message.answer(txt, parse_mode="HTML", reply_markup=get_video_model_keyboard(language))
            return
        
        elif _intent["type"] == "PRESENTATION":
            has_limit, _, max_limit = await limit_service.check_limit(user.id, RequestType.PRESENTATION)
            if not has_limit:
                txt = f"⚠️ Лимит презентаций исчерпан ({max_limit})" if language == "ru" else f"⚠️ Presentation limit reached ({max_limit})"
                await message.answer(txt)
                return
            
            from bot.services.presentation_service import presentation_service
            progress_msg = await message.answer(
                "📊 Генерирую презентацию..." if language == "ru" else "📊 Generating presentation..."
            )
            try:
                pptx_bytes, info = await presentation_service.generate_presentation(
                    topic=_intent["prompt"],
                    slides_count=7,
                    style="business",
                    include_images=True,
                    language=language,
                )
                await limit_service.increment_usage(user.id, RequestType.PRESENTATION)
                from aiogram.types import BufferedInputFile
                filename = f"presentation_{_intent['prompt'][:30].replace(' ', '_')}.pptx"
                document = BufferedInputFile(pptx_bytes, filename=filename)
                await progress_msg.delete()
                caption = f"✅ <b>Презентация готова!</b>\n📝 {info.get('title', _intent['prompt'])}"
                await message.answer_document(document, caption=caption, parse_mode="HTML")
            except Exception as e:
                logger.error("Text presentation generation error", error=str(e), user_id=user.id)
                err_txt = f"❌ Ошибка генерации: {str(e)[:100]}" if language == "ru" else f"❌ Generation error: {str(e)[:100]}"
                await progress_msg.edit_text(err_txt)
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
        
        "Do NOT fabricate facts — if unsure about factual claims, say so."
    )
    messages = [{"role": "system", "content": system_prompt}]
    messages.extend(context)
    messages.append({"role": "user", "content": text})
    
    # ============================================
    # DETERMINE IF WEB SEARCH IS NEEDED
    # Only enable web_search tool when the query actually needs real-time data.
    # This prevents the model from searching on "Привет" or general questions.
    # ============================================
    enable_search = _should_search_web(text)
    
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
                enable_search=enable_search,
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
    """Send last AI response as a beautifully formatted Word document."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    last_response = await redis_client.get(f"user:{user.id}:last_response")
    
    if not last_response:
        no_data = "Нет ответа для скачивания." if language == "ru" else "No response to download."
        await callback.answer(no_data, show_alert=True)
        return
    
    await callback.answer()
    
    # Always send as a formatted Word document
    await send_as_docx(
        message=callback.message,
        text=last_response,
        filename="response.docx",
        caption="📥 Ответ ИИ" if language == "ru" else "📥 AI Response"
    )
