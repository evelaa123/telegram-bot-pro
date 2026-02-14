"""
Voice message handler.
Handles Whisper and Qwen ASR speech recognition with smart intent routing.
Voice commands can trigger image generation, video, text, presentation, etc.
"""
import io
import re
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.utils.helpers import convert_markdown_to_html, split_text_for_telegram, send_long_message, edit_or_send_long, send_as_file
from bot.keyboards.inline import get_download_keyboard
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


# ============================================
# VOICE INTENT CLASSIFIER
# ============================================

async def classify_voice_intent(text: str, user_id: int) -> dict:
    """
    Classify transcribed voice text into an intent.
    Uses a lightweight AI call to determine what the user wants.
    
    Returns:
        dict with keys: intent (IMAGE|VIDEO|TEXT|PRESENTATION|COMMAND|DOCUMENT), 
                        prompt (cleaned prompt text),
                        command (if COMMAND intent, which command)
    """
    # Quick keyword-based check first (no AI call needed)
    text_lower = text.lower().strip()
    
    # Command patterns
    command_patterns = {
        "new_dialog": [
            "новый диалог", "очисти контекст", "начни заново", "сбрось контекст",
            "new dialog", "clear context", "start over", "reset context"
        ],
        "limits": [
            "мои лимиты", "покажи лимиты", "сколько запросов", "сколько осталось",
            "my limits", "show limits", "how many requests"
        ],
        "help": [
            "помощь", "что ты умеешь", "справка",
            "help", "what can you do"
        ],
        "settings": [
            "настройки", "settings"
        ],
    }
    
    for cmd, patterns in command_patterns.items():
        for pattern in patterns:
            if pattern in text_lower:
                return {"intent": "COMMAND", "prompt": text, "command": cmd}
    
    # Image generation patterns
    image_patterns = [
        r"(?:сгенерируй|нарисуй|создай|сделай|покажи)\s+(?:мне\s+)?(?:картинк|изображени|фото|пикч|арт)",
        r"(?:generate|draw|create|make|show)\s+(?:me\s+)?(?:an?\s+)?(?:image|picture|photo|art)",
        r"(?:нарисуй|сгенерируй|сгенери)\s+",
        r"(?:draw|generate)\s+",
    ]
    for pat in image_patterns:
        if re.search(pat, text_lower):
            # Extract prompt after the trigger phrase
            cleaned = text
            for trigger in ["нарисуй мне", "нарисуй", "сгенерируй мне", "сгенерируй", 
                          "создай картинку", "создай изображение", "сделай картинку",
                          "draw me", "draw", "generate me", "generate", "create image",
                          "make picture"]:
                cleaned = re.sub(rf'(?i)^{re.escape(trigger)}\s*', '', cleaned).strip()
            return {"intent": "IMAGE", "prompt": cleaned if cleaned else text, "command": None}
    
    # Video patterns
    video_patterns = [
        r"(?:создай|сгенерируй|сделай)\s+(?:мне\s+)?видео",
        r"(?:create|generate|make)\s+(?:me\s+)?(?:a\s+)?video",
    ]
    for pat in video_patterns:
        if re.search(pat, text_lower):
            cleaned = text
            for trigger in ["создай видео", "сгенерируй видео", "сделай видео",
                          "create video", "generate video", "make video"]:
                cleaned = re.sub(rf'(?i)^{re.escape(trigger)}\s*', '', cleaned).strip()
            return {"intent": "VIDEO", "prompt": cleaned if cleaned else text, "command": None}
    
    # Presentation patterns
    pres_patterns = [
        r"(?:создай|сделай|сгенерируй)\s+(?:мне\s+)?презентаци",
        r"(?:create|make|generate)\s+(?:me\s+)?(?:a\s+)?presentation",
    ]
    for pat in pres_patterns:
        if re.search(pat, text_lower):
            cleaned = text
            for trigger in ["создай презентацию", "сделай презентацию", "сгенерируй презентацию",
                          "создай мне презентацию", "create presentation", "make presentation",
                          "generate presentation", "create a presentation"]:
                cleaned = re.sub(rf'(?i)^{re.escape(trigger)}\s*', '', cleaned).strip()
            return {"intent": "PRESENTATION", "prompt": cleaned if cleaned else text, "command": None}
    
    # AI classification ONLY for PRESENTATION (not for IMAGE/VIDEO to avoid
    # costly false-positives like accidentally generating an image).
    # For IMAGE and VIDEO, we rely exclusively on keyword patterns above.
    if len(text) < 200:
        try:
            classify_messages = [
                {
                    "role": "system",
                    "content": (
                        "Classify the user's voice command intent. Reply with ONLY one word:\n"
                        "PRESENTATION - user EXPLICITLY wants to create a presentation/slides\n"
                        "TEXT - everything else (questions, explanations, requests)\n"
                        "If unsure, reply TEXT."
                    )
                },
                {"role": "user", "content": text[:200]}
            ]
            result, _ = await ai_service.generate_text(
                messages=classify_messages,
                telegram_id=user_id,
                max_tokens=10,
                temperature=0.1
            )
            intent = result.strip().upper()
            if intent == "PRESENTATION":
                return {"intent": "PRESENTATION", "prompt": text, "command": None}
        except Exception as e:
            logger.warning("Voice intent classification failed", error=str(e))
    
    # Default to TEXT — never accidentally trigger image/video generation
    return {"intent": "TEXT", "prompt": text, "command": None}


async def _route_voice_to_active_state(
    message: Message,
    user_id: int,
    transcribed_text: str,
    state: str,
    language: str
) -> bool:
    """
    If user has an active prompt-waiting state (video_prompt, image_prompt, etc.),
    route the transcribed voice text directly to that handler.
    Returns True if routed, False if state was not a prompt-waiting state.
    """
    if state.startswith("video_prompt:"):
        parts = state.split(":")
        if len(parts) >= 3:
            model = parts[1]
            duration = int(parts[2])
            from bot.handlers.video import queue_video_generation
            await queue_video_generation(message, user_id, transcribed_text, model, duration)
            return True
    
    elif state.startswith("video_remix:"):
        video_id = state.split(":")[1]
        from bot.handlers.video import queue_video_remix
        await queue_video_remix(message, user_id, video_id, transcribed_text)
        return True
    
    elif state.startswith("image_prompt:"):
        size = state.split(":")[1]
        from bot.handlers.image import generate_image
        await generate_image(message, user_id, transcribed_text, size)
        return True
    
    elif state.startswith("animate_photo:"):
        file_id = state.split(":", 1)[1]
        from bot.handlers.video import queue_animate_photo
        prompt = transcribed_text if transcribed_text.strip() not in (".", "") else \
            "Animate this photo with gentle natural motion, subtle camera movement"
        await queue_animate_photo(message, user_id, file_id, prompt)
        return True
    
    elif state.startswith("long_video_prompt:"):
        parts = state.split(":")
        model = parts[1] if len(parts) > 1 else "sora-2"
        from bot.handlers.video import queue_long_video_generation
        await queue_long_video_generation(message, user_id, transcribed_text, model)
        return True
    
    elif state == "document_question":
        doc_context = await redis_client.get_document_context(user_id)
        if doc_context:
            from bot.handlers.document import process_document_request
            await process_document_request(
                message=message,
                user_id=user_id,
                text=doc_context["content"],
                images=[],
                request=transcribed_text,
                filename=doc_context["filename"],
                language=language
            )
            return True
    
    elif state.startswith("photo_edit_chain:"):
        file_id = state.split(":", 1)[1]
        try:
            file = await message.bot.get_file(file_id)
            file_bytes_io = await message.bot.download_file(file.file_path)
            image_data = file_bytes_io.read() if hasattr(file_bytes_io, 'read') else file_bytes_io
            
            from bot.handlers.photo import _handle_photo_edit_from_bytes
            await _handle_photo_edit_from_bytes(
                message=message,
                user_id=user_id,
                image_data=image_data,
                caption=transcribed_text,
                language=language
            )
            return True
        except Exception as e:
            logger.error("Voice chain photo edit error", user_id=user_id, error=str(e))
            await redis_client.clear_user_state(user_id)
    
    return False


async def _route_voice_intent(
    message: Message,
    user_id: int,
    transcribed_text: str,
    language: str
):
    """
    Route transcribed voice text to the appropriate handler based on intent.
    """
    intent_result = await classify_voice_intent(transcribed_text, user_id)
    intent = intent_result["intent"]
    prompt = intent_result["prompt"]
    command = intent_result.get("command")
    
    logger.info(
        "Voice intent classified",
        user_id=user_id,
        intent=intent,
        command=command,
        text_preview=transcribed_text[:50]
    )
    
    if intent == "COMMAND":
        if command == "new_dialog":
            await redis_client.clear_context(user_id)
            await redis_client.clear_document_context(user_id)
            await redis_client.clear_user_state(user_id)
            text = "🔄 Контекст очищен." if language == "ru" else "🔄 Context cleared."
            await message.answer(text)
        elif command == "limits":
            limits_text = await limit_service.get_limits_text(user_id, language)
            await message.answer(limits_text, parse_mode="HTML")
        elif command == "help":
            from bot.handlers.start import cmd_help
            await cmd_help(message)
        elif command == "settings":
            from bot.handlers.settings import show_settings
            await show_settings(message)
        return
    
    elif intent == "IMAGE":
        # Start image generation flow
        has_limit, _, max_limit = await limit_service.check_limit(user_id, RequestType.IMAGE)
        if not has_limit:
            text = f"⚠️ Лимит картинок исчерпан ({max_limit})" if language == "ru" else f"⚠️ Image limit reached ({max_limit})"
            await message.answer(text)
            return
        
        from bot.handlers.image import generate_image
        # Use default size
        await generate_image(message, user_id, prompt, "1024x1024")
        return
    
    elif intent == "VIDEO":
        from bot.keyboards.inline import get_video_model_keyboard
        
        if language == "ru":
            text = (
                f"🎬 <b>Генерация видео</b>\n\n"
                f"📝 Промпт: <i>{prompt[:200]}</i>\n\n"
                "Выберите модель:"
            )
        else:
            text = (
                f"🎬 <b>Video Generation</b>\n\n"
                f"📝 Prompt: <i>{prompt[:200]}</i>\n\n"
                "Choose model:"
            )
        
        # Store prompt for video flow (5 min TTL)
        await redis_client.set_user_state(user_id, f"video_voice_prompt:{prompt[:500]}", ttl=300)
        await message.answer(text, parse_mode="HTML", reply_markup=get_video_model_keyboard(language))
        return
    
    elif intent == "PRESENTATION":
        # Generate presentation directly from voice prompt
        from bot.services.limit_service import limit_service as ls
        has_limit, _, max_limit = await ls.check_limit(user_id, RequestType.PRESENTATION)
        if not has_limit:
            await message.answer(
                f"⚠️ Лимит презентаций исчерпан ({max_limit})" if language == "ru"
                else f"⚠️ Presentation limit reached ({max_limit})"
            )
            return
        
        from bot.services.presentation_service import presentation_service
        progress_msg = await message.answer(
            "📊 Генерирую презентацию..." if language == "ru" else "📊 Generating presentation..."
        )
        try:
            pptx_bytes, info = await presentation_service.generate_presentation(
                topic=prompt,
                slides_count=7,
                style="business",
                include_images=True,
                language=language,
            )
            await limit_service.increment_usage(user_id, RequestType.PRESENTATION)
            from aiogram.types import BufferedInputFile
            filename = f"presentation_{prompt[:30].replace(' ', '_')}.pptx"
            document = BufferedInputFile(pptx_bytes, filename=filename)
            await progress_msg.delete()
            caption = f"✅ <b>Презентация готова!</b>\n📝 {info.get('title', prompt)}"
            await message.answer_document(document, caption=caption, parse_mode="HTML")
        except Exception as e:
            logger.error("Voice presentation generation error", error=str(e), user_id=user_id)
            await progress_msg.edit_text(f"❌ Ошибка: {str(e)[:100]}")
        return
    
    # Default: TEXT — use auto-process
    await _auto_process_transcribed_text(
        message=message,
        user_id=user_id,
        text=transcribed_text,
        language=language
    )


@router.message(F.voice)
async def handle_voice_message(message: Message):
    """Handle voice messages - transcribe with Whisper or Qwen ASR."""
    user = message.from_user
    voice = message.voice
    
    # Get user settings
    user_settings = await user_service.get_user_settings(user.id)
    language = user_settings.get("language", "ru")
    auto_process = user_settings.get("auto_voice_process", False)
    
    # Check file size (25MB limit)
    if voice.file_size and voice.file_size > 25 * 1024 * 1024:
        if language == "ru":
            await message.answer(
                "⚠️ Голосовое сообщение слишком большое.\n"
                "Максимальный размер: 25 MB"
            )
        else:
            await message.answer(
                "⚠️ Voice message is too large.\n"
                "Maximum size: 25 MB"
            )
        return
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.VOICE
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита распознавания голоса на сегодня ({max_limit}).\n"
                "Лимиты обновятся в полночь UTC."
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily voice recognition limit ({max_limit}).\n"
                "Limits reset at midnight UTC."
            )
        return
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    # Send progress message (no provider info shown to user)
    if language == "ru":
        progress_msg = await message.answer("🎤 Распознаю речь...")
    else:
        progress_msg = await message.answer("🎤 Transcribing speech...")
    
    try:
        # Download voice file
        file = await message.bot.get_file(voice.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        
        # Read bytes from BytesIO
        audio_data = file_bytes.read() if hasattr(file_bytes, 'read') else file_bytes
        
        # Transcribe using unified AI service
        text, usage = await ai_service.transcribe_audio(
            audio_data=audio_data,
            filename="voice.ogg",
            language=language if language in ["ru", "en", "zh"] else None,
            telegram_id=user.id
        )
        
        if not text or not text.strip():
            if language == "ru":
                await progress_msg.edit_text(
                    "🤔 Не удалось распознать речь.\n"
                    "Попробуйте записать сообщение ещё раз."
                )
            else:
                await progress_msg.edit_text(
                    "🤔 Could not recognize speech.\n"
                    "Try recording the message again."
                )
            return
        
        # Clean Whisper special tokens and stray HTML-like tags from transcription
        import re as _re
        text = _re.sub(r'<\|[^>]*\|>', '', text)  # Whisper tokens like <|en|>, <|transcribe|>
        text = _re.sub(r'<[a-zA-Z/][^>]{0,30}>', '', text)  # stray HTML tags
        text = text.strip()
        
        if not text:
            if language == "ru":
                await progress_msg.edit_text("🤔 Не удалось распознать речь.")
            else:
                await progress_msg.edit_text("🤔 Could not recognize speech.")
            return
        
        # Format result (without model info)
        model_used = usage.get("model", "unknown")  # For logging only
        
        # Display recognized text as plain text (no markdown conversion)
        # to avoid double-escaping or showing HTML tags to the user
        import html as _html
        escaped_text = _html.escape(text)
        if language == "ru":
            result_text = f"📝 <b>Распознанный текст:</b>\n\n{escaped_text}"
        else:
            result_text = f"📝 <b>Transcribed text:</b>\n\n{escaped_text}"
        
        chunks = split_text_for_telegram(result_text)
        
        # Edit first chunk into progress message
        try:
            await progress_msg.edit_text(chunks[0], parse_mode="HTML")
        except Exception:
            try:
                await progress_msg.edit_text(text[:4000])
            except Exception:
                pass
        
        # Send remaining chunks as new messages
        for chunk in chunks[1:]:
            try:
                await message.answer(chunk, parse_mode="HTML")
            except Exception:
                import re as _re
                plain = _re.sub(r'<[^>]+>', '', chunk)
                await message.answer(plain)
        
        # Increment usage and record
        await limit_service.increment_usage(user.id, RequestType.VOICE)
        await limit_service.record_request(
            telegram_id=user.id,
            request_type=RequestType.VOICE,
            response_preview=text[:500],
            model=model_used,
            cost_usd=float(usage.get("cost_usd", 0)),
            status=RequestStatus.SUCCESS
        )
        
        logger.info(
            "Voice transcribed",
            user_id=user.id,
            model=model_used,
            text_length=len(text)
        )
        
        # ============================================
        # INTENT-AWARE STATE ROUTING
        # Prompt-waiting states (video_prompt, image_prompt, etc.) —
        # user entered via buttons, all text goes as prompt.
        # Passive states (photo_edit_chain, document_question) —
        # check if user starts a new intent; if so, exit state.
        # ============================================
        current_state = await redis_client.get_user_state(user.id)
        
        if current_state and text.strip():
            # Passive states that can intercept unrelated messages
            _passive_states = ("photo_edit_chain:", "document_question")
            _is_passive = any(
                current_state.startswith(ps) if ps.endswith(":") else current_state == ps
                for ps in _passive_states
            )
            
            if _is_passive:
                # Check if user wants something completely different
                from bot.handlers.text import _detect_intent
                _new_intent = _detect_intent(text.strip())
                
                if _new_intent:
                    # User explicitly wants a new action → exit state
                    await redis_client.clear_user_state(user.id)
                    logger.info(
                        f"User {user.id} exited {current_state} due to voice intent: "
                        f"{_new_intent.get('type', '?')}"
                    )
                    # Fall through to voice intent routing below
                else:
                    # No new intent → route to state handler as usual
                    routed = await _route_voice_to_active_state(
                        message=message,
                        user_id=user.id,
                        transcribed_text=text.strip(),
                        state=current_state,
                        language=language
                    )
                    if routed:
                        return
            else:
                # Prompt-waiting states — always route text as prompt
                routed = await _route_voice_to_active_state(
                    message=message,
                    user_id=user.id,
                    transcribed_text=text.strip(),
                    state=current_state,
                    language=language
                )
                if routed:
                    return
        
        # ============================================
        # CHECK REPLY-TO-PHOTO (voice as reply to a photo message)
        # If user replies to a photo with a voice message,
        # treat it as photo edit instruction (like text reply-to-photo).
        # ============================================
        if message.reply_to_message and text.strip():
            reply_msg = message.reply_to_message
            if reply_msg.photo:
                try:
                    photo = reply_msg.photo[-1]
                    file = await message.bot.get_file(photo.file_id)
                    file_bytes_io = await message.bot.download_file(file.file_path)
                    image_data = file_bytes_io.read() if hasattr(file_bytes_io, 'read') else file_bytes_io
                    
                    from bot.handlers.photo import _classify_photo_intent, _handle_photo_edit_from_bytes, _handle_photo_vision
                    intent = await _classify_photo_intent(text.strip(), user.id)
                    
                    if intent == "EDIT":
                        await _handle_photo_edit_from_bytes(
                            message=message,
                            user_id=user.id,
                            image_data=image_data,
                            caption=text.strip(),
                            language=language
                        )
                    else:
                        # Analyze the photo with the voice text as instruction
                        from bot.handlers.document import analyze_document_with_vision
                        analysis_progress = await message.answer(
                            "🔍 Анализирую изображение..." if language == "ru" else "🔍 Analyzing image..."
                        )
                        await analyze_document_with_vision(
                            message=message,
                            progress_msg=analysis_progress,
                            user_id=user.id,
                            filename="photo.jpg",
                            images=[image_data],
                            language=language,
                            caption=text.strip()
                        )
                    return
                except Exception as e:
                    logger.error("Voice reply-to-photo error", user_id=user.id, error=str(e))
                    # Fall through to normal intent routing
        
        # Auto-process with voice intent routing if enabled
        if auto_process and text.strip():
            await _route_voice_intent(
                message=message,
                user_id=user.id,
                transcribed_text=text,
                language=language
            )
        
    except Exception as e:
        logger.error("Voice transcription error", user_id=user.id, error=str(e))
        
        # Record failed request
        await limit_service.record_request(
            telegram_id=user.id,
            request_type=RequestType.VOICE,
            model="unknown",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )
        
        if language == "ru":
            error_text = (
                "❌ Произошла ошибка при распознавании голоса.\n"
                f"Попробуйте ещё раз.\n\n<i>Ошибка: {str(e)[:100]}</i>"
            )
        else:
            error_text = (
                "❌ An error occurred during voice recognition.\n"
                f"Please try again.\n\n<i>Error: {str(e)[:100]}</i>"
            )
        
        try:
            await progress_msg.edit_text(error_text)
        except Exception:
            await message.answer(error_text)


async def _auto_process_transcribed_text(
    message: Message,
    user_id: int,
    text: str,
    language: str
):
    """
    Auto-process transcribed text with AI.
    Uses Responses API with web_search tool (model decides when to search).
    Falls back to streaming chat completions if Responses API fails.
    """
    if language == "ru":
        processing_msg = await message.answer("💭 Обрабатываю ваш запрос...")
    else:
        processing_msg = await message.answer("💭 Processing your request...")
    
    try:
        # Get context
        context = await redis_client.get_context(user_id)
        
        # Build messages
        system_prompt = (
            "You are a helpful AI assistant in a Telegram bot. "
            "Respond in the same language as the user's message. "
            "Be concise but thorough. Use markdown formatting when appropriate.\n\n"
            
            "MEMORY: You DO have conversation memory within this chat session. "
            "The previous messages in this conversation are provided to you as context. "
            "If the user asks whether you remember previous messages — YES, you do, "
            "refer to the conversation history above. "
            "Context is kept for 30 minutes and up to 20 messages.\n\n"
            
            "Do NOT fabricate facts — if unsure about factual claims, say so."
        )
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(context)
        messages.append({"role": "user", "content": text})
        
        # Determine if web search is needed (keyword-based)
        from bot.handlers.text import _should_search_web
        enable_search = _should_search_web(text)
        
        # Try Responses API with web search first
        full_response = ""
        used_search = False
        
        try:
            full_response, search_usage = await ai_service.generate_text_with_search(
                messages=messages,
                telegram_id=user_id,
                enable_search=enable_search,
            )
            used_search = search_usage.get("web_search_used", False)
            
            # Append source links
            sources = search_usage.get("sources", [])
            if sources:
                import html as _html
                source_links = "\n\n---\n🔗 "
                source_links += " | ".join(
                    f'<a href="{_html.escape(s["url"])}">{_html.escape(s.get("title", "Source")[:40])}</a>'
                    for s in sources[:3]
                )
                full_response += source_links
                
        except Exception as search_err:
            logger.warning("Voice auto-process: Responses API failed, falling back to streaming", error=str(search_err))
            # Fallback to streaming
            full_response = ""
            last_update_len = 0
            
            async for chunk, is_complete in ai_service.generate_text_stream(
                messages=messages,
                telegram_id=user_id
            ):
                full_response += chunk
                
                if len(full_response) - last_update_len > 300 or is_complete:
                    try:
                        display_text = full_response[:4000] if len(full_response) > 4000 else full_response
                        if display_text.strip():
                            html_text = convert_markdown_to_html(display_text)
                            try:
                                await processing_msg.edit_text(html_text, parse_mode="HTML")
                            except Exception:
                                await processing_msg.edit_text(display_text)
                            last_update_len = len(full_response)
                    except Exception:
                        pass
        
        # Final update — split long messages
        if full_response.strip():
            # Store for download
            await redis_client.set(f"user:{user_id}:last_response", full_response, ttl=3600)
            
            download_kb = get_download_keyboard(language)
            
            try:
                await edit_or_send_long(
                    thinking_message=processing_msg,
                    original_message=message,
                    text=full_response,
                    reply_markup=download_kb
                )
            except Exception:
                pass
            
            # Save to context
            await redis_client.add_to_context(user_id, "user", text)
            await redis_client.add_to_context(user_id, "assistant", full_response)
            
            # Increment text usage
            await limit_service.increment_usage(user_id, RequestType.TEXT)
            
            logger.info(
                "Auto-processed voice message",
                user_id=user_id,
                response_length=len(full_response),
                web_search_used=used_search
            )
        
    except Exception as e:
        logger.error("Auto-process voice error", user_id=user_id, error=str(e))
        if language == "ru":
            await processing_msg.edit_text(f"❌ Ошибка обработки: {str(e)[:100]}")
        else:
            await processing_msg.edit_text(f"❌ Processing error: {str(e)[:100]}")


@router.message(F.audio)
async def handle_audio_file(message: Message):
    """Handle audio files - transcribe with Whisper or Qwen ASR."""
    user = message.from_user
    audio = message.audio
    
    # Get user settings
    user_settings = await user_service.get_user_settings(user.id)
    language = user_settings.get("language", "ru")
    
    # Check file size
    if audio.file_size and audio.file_size > 25 * 1024 * 1024:
        if language == "ru":
            await message.answer(
                "⚠️ Аудиофайл слишком большой.\n"
                "Максимальный размер: 25 MB"
            )
        else:
            await message.answer(
                "⚠️ Audio file is too large.\n"
                "Maximum size: 25 MB"
            )
        return
    
    # Check supported format
    supported_formats = {'mp3', 'mp4', 'mpeg', 'mpga', 'm4a', 'wav', 'webm', 'ogg', 'flac'}
    
    filename = audio.file_name or "audio.mp3"
    ext = filename.split('.')[-1].lower() if '.' in filename else ''
    
    if ext not in supported_formats:
        if language == "ru":
            await message.answer(
                "⚠️ Неподдерживаемый формат аудио.\n"
                f"Поддерживаются: {', '.join(supported_formats)}"
            )
        else:
            await message.answer(
                "⚠️ Unsupported audio format.\n"
                f"Supported: {', '.join(supported_formats)}"
            )
        return
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.VOICE
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита распознавания голоса на сегодня ({max_limit})."
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily voice recognition limit ({max_limit})."
            )
        return
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    # Send progress message
    if language == "ru":
        progress_msg = await message.answer("🎵 Обрабатываю аудиофайл...")
    else:
        progress_msg = await message.answer("🎵 Processing audio file...")
    
    try:
        # Download file
        file = await message.bot.get_file(audio.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        audio_data = file_bytes.read() if hasattr(file_bytes, 'read') else file_bytes
        
        # Transcribe using unified AI service
        text, usage = await ai_service.transcribe_audio(
            audio_data=audio_data,
            filename=filename,
            telegram_id=user.id
        )
        
        if not text or not text.strip():
            if language == "ru":
                await progress_msg.edit_text(
                    "🤔 Не удалось распознать речь в аудиофайле."
                )
            else:
                await progress_msg.edit_text(
                    "🤔 Could not recognize speech in the audio file."
                )
            return
        
        # Clean Whisper special tokens and stray HTML-like tags
        import re as _re2
        text = _re2.sub(r'<\|[^>]*\|>', '', text)
        text = _re2.sub(r'<[a-zA-Z/][^>]{0,30}>', '', text)
        text = text.strip()
        
        # Format result (without model info)
        if len(text) > 4000:
            # Send as file + first 4000 in message
            await send_as_file(
                message=message,
                text=text,
                filename=f"{filename}_transcription.txt",
                caption="📝 Full transcription" if language != "ru" else "📝 Полная транскрипция"
            )
        
        model_used = usage.get("model", "unknown")  # For logging only
        
        # Display recognized text as plain text (no markdown conversion)
        import html as _html
        escaped_text = _html.escape(text)
        escaped_fname = _html.escape(filename)
        if language == "ru":
            result_text = f"📝 <b>Распознанный текст из {escaped_fname}:</b>\n\n{escaped_text}"
        else:
            result_text = f"📝 <b>Transcribed text from {escaped_fname}:</b>\n\n{escaped_text}"
        
        chunks = split_text_for_telegram(result_text)
        
        try:
            await progress_msg.edit_text(chunks[0], parse_mode="HTML")
        except Exception:
            await progress_msg.edit_text(text[:4000])
        
        for chunk in chunks[1:]:
            try:
                await message.answer(chunk, parse_mode="HTML")
            except Exception:
                import re as _re
                plain = _re.sub(r'<[^>]+>', '', chunk)
                await message.answer(plain[:4000])
        
        # Increment usage and record
        await limit_service.increment_usage(user.id, RequestType.VOICE)
        await limit_service.record_request(
            telegram_id=user.id,
            request_type=RequestType.VOICE,
            response_preview=text[:500],
            model=model_used,
            cost_usd=float(usage.get("cost_usd", 0)),
            status=RequestStatus.SUCCESS
        )
        
        logger.info(
            "Audio transcribed",
            user_id=user.id,
            filename=filename,
            model=model_used,
            text_length=len(text)
        )
        
    except Exception as e:
        logger.error("Audio transcription error", user_id=user.id, error=str(e))
        
        await limit_service.record_request(
            telegram_id=user.id,
            request_type=RequestType.VOICE,
            model="unknown",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )
        
        if language == "ru":
            await progress_msg.edit_text(
                f"❌ Произошла ошибка при обработке аудиофайла.\n\n<i>{str(e)[:100]}</i>"
            )
        else:
            await progress_msg.edit_text(
                f"❌ An error occurred processing the audio file.\n\n<i>{str(e)[:100]}</i>"
            )
