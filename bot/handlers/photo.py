"""
Photo message handler.
Handles photo messages sent by users.
Supports photo analysis (Vision), photo editing (GPT-Image-1),
and multi-photo (media group) processing.
"""
import asyncio
import io
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.enums import ChatAction
from database.models import RequestType, RequestStatus
from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.inline import get_subscription_keyboard, get_photo_actions_keyboard, get_photo_edit_actions_keyboard, get_download_keyboard
from bot.utils.helpers import convert_markdown_to_html, split_text_for_telegram
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from bot.handlers.support import save_support_message
from config import settings
import structlog
import time

logger = structlog.get_logger()
router = Router()

# Media group collector: {media_group_id: {"messages": [...], "task": asyncio.Task}}
_media_groups: dict = {}
_media_group_lock = asyncio.Lock()


@router.message(F.photo)
async def handle_photo_message(message: Message):
    """
    Handle photo messages.
    - If media_group_id: collect into group and process together
    - If user is in support_message state: save photo to support
    - Otherwise: analyze photo with AI Vision
    """
    user = message.from_user
    
    # Check user state FIRST
    state = await redis_client.get_user_state(user.id)
    
    if state == "support_message":
        await handle_support_photo(message, user.id)
        return
    
    if state and state.startswith("animate_photo_wait"):
        await handle_animate_new_photo(message, user.id)
        return
    
    # Check for media group (multiple photos sent at once)
    if message.media_group_id:
        await _collect_media_group(message)
        return
    
    # Single photo — analyze/edit as before
    await handle_photo_analysis(message, user.id)


async def _collect_media_group(message: Message):
    """Collect messages from a media group, then process them all together."""
    mg_id = message.media_group_id
    
    async with _media_group_lock:
        if mg_id not in _media_groups:
            _media_groups[mg_id] = {"messages": [], "task": None}
        
        _media_groups[mg_id]["messages"].append(message)
        
        # Cancel previous delayed task if exists
        if _media_groups[mg_id]["task"]:
            _media_groups[mg_id]["task"].cancel()
        
        # Schedule processing after 0.6s of no new photos
        _media_groups[mg_id]["task"] = asyncio.create_task(
            _process_media_group_delayed(mg_id)
        )


async def _process_media_group_delayed(mg_id: str):
    """Wait for all photos in a media group, then process."""
    await asyncio.sleep(0.6)
    
    async with _media_group_lock:
        group_data = _media_groups.pop(mg_id, None)
    
    if not group_data or not group_data["messages"]:
        return
    
    messages = group_data["messages"]
    # Sort by message_id to maintain order
    messages.sort(key=lambda m: m.message_id)
    
    first_msg = messages[0]
    user_id = first_msg.from_user.id
    # Caption is usually only on the first message
    caption = None
    for m in messages:
        if m.caption:
            caption = m.caption
            break
    
    language = await user_service.get_user_language(user_id)
    
    # Check limits
    has_limit, _, max_limit = await limit_service.check_limit(user_id, RequestType.IMAGE)
    if not has_limit:
        if language == "ru":
            await first_msg.answer(f"⚠️ Лимит запросов исчерпан ({max_limit}).")
        else:
            await first_msg.answer(f"⚠️ Request limit reached ({max_limit}).")
        return
    
    if language == "ru":
        status_msg = await first_msg.answer(
            f"🔍 Анализирую {len(messages)} фото..."
        )
    else:
        status_msg = await first_msg.answer(
            f"🔍 Analyzing {len(messages)} photos..."
        )
    
    start_time = time.time()
    
    try:
        # Download all photos
        images_data = []
        for msg in messages:
            photo = msg.photo[-1]
            file = await msg.bot.get_file(photo.file_id)
            file_bytes = await msg.bot.download_file(file.file_path)
            data = file_bytes.read() if hasattr(file_bytes, 'read') else file_bytes
            images_data.append(data)
        
        prompt = caption or (
            "Опиши подробно все изображения" if language == "ru"
            else "Describe all images in detail"
        )
        
        # Analyze all images together using vision
        result, usage = await ai_service.analyze_document_images(
            images=images_data,
            prompt=prompt,
            telegram_id=user_id
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Store for download
        await redis_client.set(f"user:{user_id}:last_response", result, ttl=3600)
        
        # Save last photo file_id
        last_photo = messages[-1].photo[-1]
        await redis_client.client.set(
            f"user:{user_id}:last_photo_file_id",
            last_photo.file_id,
            ex=3600
        )
        
        html_result = convert_markdown_to_html(result)
        chunks = split_text_for_telegram(html_result)
        
        download_kb = get_download_keyboard(language)
        photo_kb = get_photo_actions_keyboard(language=language)
        
        if len(chunks) == 1:
            try:
                await status_msg.edit_text(chunks[0], parse_mode="HTML", reply_markup=photo_kb)
            except Exception:
                import re as _re
                plain = _re.sub(r'<[^>]+>', '', chunks[0])
                await status_msg.edit_text(plain, reply_markup=photo_kb)
        else:
            try:
                await status_msg.edit_text(chunks[0], parse_mode="HTML", reply_markup=photo_kb)
            except Exception:
                import re as _re
                plain = _re.sub(r'<[^>]+>', '', chunks[0])
                await status_msg.edit_text(plain, reply_markup=photo_kb)
            
            for i, chunk in enumerate(chunks[1:]):
                is_last = (i == len(chunks) - 2)
                markup = download_kb if is_last else None
                try:
                    await first_msg.answer(chunk, parse_mode="HTML", reply_markup=markup)
                except Exception:
                    import re as _re
                    plain = _re.sub(r'<[^>]+>', '', chunk)
                    await first_msg.answer(plain, reply_markup=markup)
        
        # Save to context
        context_user_msg = f"[Пользователь отправил {len(messages)} фото]"
        if caption:
            context_user_msg += f" с подписью: {caption}"
        await redis_client.add_to_context(user_id, "user", context_user_msg)
        await redis_client.add_to_context(user_id, "assistant", result)
        
        model_used = usage.get("model", "vision")
        await limit_service.increment_usage(user_id, RequestType.IMAGE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500],
            response_preview=result[:500],
            model=model_used,
            status=RequestStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(
            "Media group analysis completed",
            user_id=user_id,
            photo_count=len(messages),
            duration_ms=duration_ms
        )
        
    except Exception as e:
        logger.error("Media group analysis error", user_id=user_id, error=str(e))
        duration_ms = int((time.time() - start_time) * 1000)
        
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=(caption or "multi-photo")[:500],
            model="vision",
            status=RequestStatus.FAILED,
            error_message=str(e),
            duration_ms=duration_ms
        )
        
        if language == "ru":
            await status_msg.edit_text("❌ Ошибка при анализе фото. Попробуйте ещё раз.")
        else:
            await status_msg.edit_text("❌ Error analyzing photos. Please try again.")


async def handle_support_photo(message: Message, user_id: int):
    """
    Handle photo sent in support mode.
    Save photo file_id to support message.
    """
    language = await user_service.get_user_language(user_id)
    
    try:
        # Get the best quality photo (last in array)
        photo = message.photo[-1]
        file_id = photo.file_id
        
        # Build message text with photo marker
        caption = message.caption or ""
        message_text = f"[PHOTO:{file_id}]"
        if caption:
            message_text = f"{caption}\n{message_text}"
        
        # Save the message
        msg_id = await save_support_message(
            user_telegram_id=user_id,
            message_text=message_text,
            is_from_user=True
        )
        
        # Clear user state
        await redis_client.clear_user_state(user_id)
        
        if language == "ru":
            await message.answer(
                "✅ <b>Фото отправлено!</b>\n\n"
                "Наша команда поддержки рассмотрит ваше обращение и ответит вам в ближайшее время.\n\n"
                "💡 Используйте /support чтобы отправить ещё одно сообщение."
            )
        else:
            await message.answer(
                "✅ <b>Photo sent!</b>\n\n"
                "Our support team will review your request and respond shortly.\n\n"
                "💡 Use /support to send another message."
            )
        
        logger.info(
            "Support photo received",
            user_id=user_id,
            message_id=msg_id,
            file_id=file_id,
            has_caption=bool(caption)
        )
        
    except Exception as e:
        logger.error("Failed to save support photo", error=str(e), user_id=user_id)
        
        if language == "ru":
            await message.answer(
                "❌ Произошла ошибка при отправке фото. Попробуйте позже."
            )
        else:
            await message.answer(
                "❌ An error occurred while sending your photo. Please try again later."
            )


async def handle_photo_analysis(message: Message, user_id: int):
    """
    Handle photo: either edit it (if caption is an edit instruction)
    or analyze with AI Vision.
    """
    language = await user_service.get_user_language(user_id)
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user_id, RequestType.IMAGE
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита запросов на сегодня ({max_limit}).\n"
                "Лимиты обновятся в полночь UTC.\n\n"
                "💎 <b>Хотите больше запросов?</b>\n"
                "Оформите подписку для увеличения лимитов!",
                reply_markup=get_subscription_keyboard(language)
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily request limit ({max_limit}).\n"
                "Limits reset at midnight UTC.\n\n"
                "💎 <b>Want more requests?</b>\n"
                "Subscribe to increase your limits!",
                reply_markup=get_subscription_keyboard(language)
            )
        return
    
    caption = message.caption
    
    # Detect if this is an edit instruction or analysis request
    if caption and await _classify_photo_intent(caption, user_id) == "EDIT":
        await _handle_photo_edit(message, user_id, caption, language)
    else:
        await _handle_photo_vision(message, user_id, caption, language)


def _is_edit_instruction(caption: str) -> bool:
    """
    Determine if a photo caption is an image edit instruction
    (vs. a question/analysis request).
    
    Edit instructions = user wants the image to be MODIFIED and returned.
    Analysis requests = user wants a text DESCRIPTION of the image.
    """
    if not caption:
        return False
    
    text = caption.lower().strip()
    
    # Explicit analysis/question patterns -> NOT edit
    _analysis_patterns = [
        "что ", "что?", "опиши", "расскаж", "объясн", "перевед", "переведи",
        "прочитай", "извлек", "найди текст", "распозна", "сколько",
        "какой", "какая", "какое", "какие", "кто ", "где ", "зачем",
        "почему", "когда", "what ", "who ", "where ", "when ", "why ",
        "how ", "describe", "explain", "translate", "read", "extract",
        "find text", "recognize", "how many", "which", "analyze", "анализ",
        "tell me", "скажи", "расскажи",
    ]
    for p in _analysis_patterns:
        if text.startswith(p) or f" {p}" in text:
            return False
    
    # Explicit edit patterns -> IS edit
    _edit_patterns = [
        # Russian action verbs (imperative) for editing
        "добав", "убер", "удал", "замен", "измен", "сдела", "нарисуй",
        "поменяй", "перекрас", "покрас", "увеличь", "уменьш", "обрежь",
        "поверни", "отзеркаль", "размой", "осветл", "затемн", "исправ",
        "помни", "помять", "вмятин", "подпиши", "напиши",
        "поставь", "вставь", "перемест", "сдвинь", "переверн",
        "растян", "сожм", "обведи", "выдели", "стер", "закрас",
        "зафотошоп", "отфотошоп", "ретуш", "отретуш",
        "ярче", "темнее", "светлее", "контрастн", "насыщенн",
        "размытее", "четче", "резче",
        # Russian "пусть" / "чтобы" patterns — transformative intent
        "пусть ", "чтобы ",
        # English action verbs for editing
        "add ", "remove ", "delete ", "replace ", "change ", "make ",
        "draw ", "paint ", "color ", "resize ", "crop ", "rotate ",
        "flip ", "blur ", "brighten", "darken", "fix ", "put ",
        "insert ", "move ", "shift ", "stretch ", "squeeze", "dent",
        "outline", "highlight", "erase ", "retouch", "edit ",
        "photoshop", "write ", "place ", "brighter", "darker",
    ]
    for p in _edit_patterns:
        if text.startswith(p) or f" {p}" in f" {text}":
            return True
    
    return False


async def _classify_photo_intent(caption: str, user_id: int) -> str:
    """
    Classify photo caption intent: EDIT or ANALYZE.
    
    1. First try fast keyword-based classification.
    2. If ambiguous (no keywords matched), use AI to classify.
    
    Returns: "EDIT" or "ANALYZE"
    """
    if not caption or not caption.strip():
        return "ANALYZE"
    
    text = caption.lower().strip()
    
    # Fast path: keyword-based
    if _is_edit_instruction(caption):
        return "EDIT"
    
    # Check for explicit analysis patterns (already checked in _is_edit_instruction
    # but double-check here for the negative case)
    _clear_analysis = [
        "что ", "что?", "опиши", "расскаж", "объясн",
        "какой", "какая", "какое", "какие", "кто ", "где ",
        "what ", "who ", "where ", "describe", "explain", "analyze",
    ]
    for p in _clear_analysis:
        if text.startswith(p) or f" {p}" in text:
            return "ANALYZE"
    
    # Ambiguous: use AI classifier (fast, small prompt)
    try:
        classify_messages = [
            {
                "role": "system",
                "content": (
                    "You classify user messages about photos. "
                    "EDIT = user wants to MODIFY/CHANGE the image (add, remove, transform, dent, brighten, etc). "
                    "ANALYZE = user wants to DESCRIBE, READ, or ASK about the image. "
                    "Reply with exactly one word: EDIT or ANALYZE"
                )
            },
            {
                "role": "user",
                "content": f"Caption: {caption}"
            }
        ]
        
        result, _ = await ai_service.generate_text(
            messages=classify_messages,
            telegram_id=user_id,
            max_tokens=5,
            temperature=0.0
        )
        
        result = result.strip().upper()
        if "EDIT" in result:
            logger.info("AI classified photo intent as EDIT", caption=caption[:50], user_id=user_id)
            return "EDIT"
        
    except Exception as e:
        logger.warning("AI photo intent classification failed", error=str(e))
    
    return "ANALYZE"


async def _handle_photo_edit(message: Message, user_id: int, caption: str, language: str):
    """
    Edit a photo based on caption instruction using GPT-Image-1.
    Returns the edited image to the user.
    """
    photo = message.photo[-1]
    
    if language == "ru":
        status_msg = await message.answer("🎨 Редактирую изображение...")
    else:
        status_msg = await message.answer("🎨 Editing image...")
    
    # Show upload photo action
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
    
    # Animate progress
    animation_task = asyncio.create_task(
        _animate_edit_progress(status_msg, language)
    )
    
    start_time = time.time()
    
    try:
        # Download the original photo
        file = await message.bot.get_file(photo.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        
        import io
        image_data = io.BytesIO(file_bytes.read()).getvalue()
        
        # Edit with GPT-Image-1
        edited_bytes, usage = await ai_service.edit_image(
            image_data=image_data,
            prompt=caption,
            telegram_id=user_id
        )
        
        animation_task.cancel()
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Delete progress message
        try:
            await status_msg.delete()
        except Exception:
            pass
        
        # Send edited photo
        edited_photo = BufferedInputFile(edited_bytes, filename="edited_image.png")
        
        if language == "ru":
            edit_caption = f"✏️ <b>Отредактировано:</b>\n<i>{caption[:500]}</i>"
        else:
            edit_caption = f"✏️ <b>Edited:</b>\n<i>{caption[:500]}</i>"
        
        sent_msg = await message.answer_photo(
            photo=edited_photo,
            caption=edit_caption,
            reply_markup=get_photo_edit_actions_keyboard(language=language)
        )
        
        # Save to context for follow-ups (rich description for recall)
        context_user_msg = f"[Пользователь отправил фото с инструкцией для редактирования: {caption}]"
        await redis_client.add_to_context(user_id, "user", context_user_msg)
        await redis_client.add_to_context(
            user_id, "assistant",
            f"[✅ Бот успешно отредактировал изображение по инструкции: {caption}]"
        )
        
        # Save the SENT photo's file_id for animate/chain-edit
        if sent_msg.photo:
            sent_file_id = sent_msg.photo[-1].file_id
        else:
            sent_file_id = photo.file_id
        
        await redis_client.client.set(
            f"user:{user_id}:last_photo_file_id",
            sent_file_id,
            ex=3600
        )
        
        # Set chain-edit state so next text/voice continues editing this photo
        await redis_client.set_user_state(user_id, f"photo_edit_chain:{sent_file_id}")
        
        # Record usage
        model_used = usage.get("model", "gpt-image-1")
        await limit_service.increment_usage(user_id, RequestType.IMAGE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=caption[:500],
            model=model_used,
            cost_usd=float(usage.get("cost_usd", 0)),
            status=RequestStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(
            "Photo edit completed",
            user_id=user_id,
            duration_ms=duration_ms,
            edit_instruction=caption[:100]
        )
        
    except Exception as e:
        animation_task.cancel()
        logger.error("Photo edit error", user_id=user_id, error=str(e))
        
        # Save failure to context
        await redis_client.add_to_context(
            user_id, "user",
            f"[Пользователь отправил фото с инструкцией: {caption}]"
        )
        await redis_client.add_to_context(
            user_id, "assistant",
            f"[❌ Редактирование изображения не удалось: {str(e)[:100]}]"
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=caption[:500],
            model="gpt-image-1",
            status=RequestStatus.FAILED,
            error_message=str(e),
            duration_ms=duration_ms
        )
        
        # Fallback: if editing fails, try analysis instead
        if language == "ru":
            error_text = (
                "❌ Не удалось отредактировать изображение.\n"
                f"<i>Ошибка: {str(e)[:200]}</i>\n\n"
                "🔍 Попробую проанализировать вместо этого..."
            )
        else:
            error_text = (
                "❌ Failed to edit the image.\n"
                f"<i>Error: {str(e)[:200]}</i>\n\n"
                "🔍 Trying to analyze instead..."
            )
        
        try:
            await status_msg.edit_text(error_text)
        except Exception:
            await message.answer(error_text)
        
        # Fallback to analysis
        await _handle_photo_vision(message, user_id, caption, language)


async def _animate_edit_progress(message: Message, language: str):
    """Animate progress for image editing."""
    base_text = "🎨 Редактирую изображение" if language == "ru" else "🎨 Editing image"
    dots = [".", "..", "..."]
    i = 0
    try:
        while True:
            try:
                await message.edit_text(f"{base_text}{dots[i % 3]}")
            except Exception:
                pass
            i += 1
            await asyncio.sleep(1.5)
    except asyncio.CancelledError:
        pass


async def _handle_photo_edit_from_bytes(
    message: Message,
    user_id: int,
    image_data: bytes,
    caption: str,
    language: str
):
    """
    Edit a photo from raw bytes (used when replying to a photo message).
    Similar to _handle_photo_edit but accepts pre-downloaded image bytes.
    """
    if language == "ru":
        status_msg = await message.answer("🎨 Редактирую изображение...")
    else:
        status_msg = await message.answer("🎨 Editing image...")
    
    await message.bot.send_chat_action(message.chat.id, ChatAction.UPLOAD_PHOTO)
    
    animation_task = asyncio.create_task(
        _animate_edit_progress(status_msg, language)
    )
    
    start_time = time.time()
    
    try:
        edited_bytes, usage = await ai_service.edit_image(
            image_data=image_data,
            prompt=caption,
            telegram_id=user_id
        )
        
        animation_task.cancel()
        duration_ms = int((time.time() - start_time) * 1000)
        
        try:
            await status_msg.delete()
        except Exception:
            pass
        
        edited_photo = BufferedInputFile(edited_bytes, filename="edited_image.png")
        
        if language == "ru":
            edit_caption = f"✏️ <b>Отредактировано:</b>\n<i>{caption[:500]}</i>"
        else:
            edit_caption = f"✏️ <b>Edited:</b>\n<i>{caption[:500]}</i>"
        
        sent_msg = await message.answer_photo(
            photo=edited_photo,
            caption=edit_caption,
            reply_markup=get_photo_edit_actions_keyboard(language=language)
        )
        
        # Save the sent photo's file_id for animate/chain-edit
        if sent_msg.photo:
            sent_file_id = sent_msg.photo[-1].file_id
            await redis_client.client.set(
                f"user:{user_id}:last_photo_file_id",
                sent_file_id,
                ex=3600
            )
        else:
            sent_file_id = ""
        
        # Set chain-edit state so next text/voice continues editing this photo
        if sent_file_id:
            await redis_client.set_user_state(user_id, f"photo_edit_chain:{sent_file_id}")
        
        # Save to context (rich description for recall)
        context_user_msg = f"[Пользователь ответил на фото с инструкцией для редактирования: {caption}]"
        await redis_client.add_to_context(user_id, "user", context_user_msg)
        await redis_client.add_to_context(
            user_id, "assistant",
            f"[✅ Бот успешно отредактировал изображение по инструкции: {caption}]"
        )
        
        model_used = usage.get("model", "gpt-image-1")
        await limit_service.increment_usage(user_id, RequestType.IMAGE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=caption[:500],
            model=model_used,
            cost_usd=float(usage.get("cost_usd", 0)),
            status=RequestStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(
            "Reply-to-photo edit completed",
            user_id=user_id,
            duration_ms=duration_ms
        )
        
    except Exception as e:
        animation_task.cancel()
        logger.error("Reply-to-photo edit error", user_id=user_id, error=str(e))
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=caption[:500],
            model="gpt-image-1",
            status=RequestStatus.FAILED,
            error_message=str(e),
            duration_ms=duration_ms
        )
        
        if language == "ru":
            error_text = (
                "❌ Не удалось отредактировать изображение.\n"
                f"<i>Ошибка: {str(e)[:200]}</i>\n\n"
                "Попробуйте другую инструкцию."
            )
        else:
            error_text = (
                "❌ Failed to edit the image.\n"
                f"<i>Error: {str(e)[:200]}</i>\n\n"
                "Try a different instruction."
            )
        
        try:
            await status_msg.edit_text(error_text)
        except Exception:
            await message.answer(error_text)


async def _handle_photo_vision(message: Message, user_id: int, caption: str, language: str):
    """
    Analyze photo with AI Vision (original analysis flow).
    """
    photo = message.photo[-1]
    
    # Get caption as prompt or use default
    if caption:
        prompt = caption
    else:
        prompt = "Опиши что изображено на фото подробно" if language == "ru" else "Describe what is shown in the photo in detail"
    
    if language == "ru":
        status_msg = await message.answer("🔍 Анализирую изображение...")
    else:
        status_msg = await message.answer("🔍 Analyzing image...")
    
    start_time = time.time()
    
    try:
        # Download the photo
        file = await message.bot.get_file(photo.file_id)
        file_bytes = await message.bot.download_file(file.file_path)
        
        # Read bytes
        import io
        image_data = io.BytesIO(file_bytes.read()).getvalue()
        
        # Analyze with AI Vision
        result, usage = await ai_service.analyze_image(
            image_data=image_data,
            prompt=prompt,
            telegram_id=user_id
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Update status message with result
        # Store for download button
        await redis_client.set(f"user:{user_id}:last_response", result, ttl=3600)
        
        html_result = convert_markdown_to_html(result)
        chunks = split_text_for_telegram(html_result)
        
        # Save file_id to Redis for animate button (avoids 64-byte callback_data limit)
        await redis_client.client.set(
            f"user:{user_id}:last_photo_file_id",
            photo.file_id,
            ex=3600
        )
        
        # First chunk gets animate button, last chunk gets download
        from aiogram.utils.keyboard import InlineKeyboardBuilder
        from aiogram.types import InlineKeyboardButton
        
        if len(chunks) == 1:
            # Combine photo actions + download in one keyboard
            photo_kb = get_photo_actions_keyboard(language=language)
            await status_msg.edit_text(
                chunks[0],
                parse_mode="HTML",
                reply_markup=photo_kb
            )
        else:
            # First chunk with photo actions
            photo_kb = get_photo_actions_keyboard(language=language)
            try:
                await status_msg.edit_text(chunks[0], parse_mode="HTML", reply_markup=photo_kb)
            except Exception:
                import re as _re
                plain = _re.sub(r'<[^>]+>', '', chunks[0])
                await status_msg.edit_text(plain, reply_markup=photo_kb)
            
            # Remaining chunks, download button on last
            download_kb = get_download_keyboard(language)
            for i, chunk in enumerate(chunks[1:]):
                is_last = (i == len(chunks) - 2)
                markup = download_kb if is_last else None
                try:
                    await message.answer(chunk, parse_mode="HTML", reply_markup=markup)
                except Exception:
                    import re as _re
                    plain = _re.sub(r'<[^>]+>', '', chunk)
                    await message.answer(plain, reply_markup=markup)
        
        # Get actual model used from usage info
        model_used = usage.get("model", "vision")
        
        # Save photo caption + analysis result to conversation context
        # so user can reference the photo in future messages
        context_user_msg = f"[Пользователь отправил фото]"
        if caption:
            context_user_msg += f" с подписью: {caption}"
        await redis_client.add_to_context(user_id, "user", context_user_msg)
        await redis_client.add_to_context(user_id, "assistant", result)
        
        # Increment usage and record request
        await limit_service.increment_usage(user_id, RequestType.IMAGE)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500],
            response_preview=result[:500],
            model=model_used,
            status=RequestStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(
            "Photo analysis completed",
            user_id=user_id,
            duration_ms=duration_ms,
            result_length=len(result)
        )
        
    except Exception as e:
        logger.error("Photo analysis error", user_id=user_id, error=str(e))
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Record failed request
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.IMAGE,
            prompt=prompt[:500] if prompt else "photo analysis",
            model="vision",
            status=RequestStatus.FAILED,
            error_message=str(e),
            duration_ms=duration_ms
        )
        
        if language == "ru":
            error_text = (
                "❌ Произошла ошибка при анализе изображения.\n"
                "Попробуйте ещё раз или отправьте другое фото."
            )
        else:
            error_text = (
                "❌ An error occurred while analyzing the image.\n"
                "Please try again or send a different photo."
            )
        
        try:
            await status_msg.edit_text(error_text)
        except Exception:
            await message.answer(error_text)


async def handle_animate_new_photo(message: Message, user_id: int):
    """
    Handle photo sent when user is in 'animate_photo_wait' state.
    User wants to animate this specific photo.
    """
    language = await user_service.get_user_language(user_id)
    
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Set state to animate_photo with this file_id, ask for prompt
    await redis_client.set_user_state(user_id, f"animate_photo:{file_id}")
    
    if language == "ru":
        await message.answer(
            "🎞 <b>Оживление фото</b>\n\n"
            "Опишите, как должно двигаться/оживать изображение.\n\n"
            "<i>Например: \u00abКамера медленно приближается, волосы развеваются на ветру\u00bb</i>\n\n"
            "Или отправьте просто точку (.) для автоматического оживления."
        )
    else:
        await message.answer(
            "🎞 <b>Animate Photo</b>\n\n"
            "Describe how the image should move/animate.\n\n"
            "<i>Example: 'Camera slowly zooms in, hair blowing in the wind'</i>\n\n"
            "Or send just a dot (.) for automatic animation."
        )


@router.callback_query(F.data == "photo:animate")
async def callback_photo_animate(callback: CallbackQuery):
    """Handle animate photo button from photo analysis result."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    # Check premium
    from bot.services.subscription_service import subscription_service
    is_premium = await subscription_service.check_premium(user.id)
    
    if not is_premium:
        if language == "ru":
            await callback.answer("💎 Оживление фото доступно только для премиум-подписчиков!", show_alert=True)
        else:
            await callback.answer("💎 Animate photo is available for premium subscribers only!", show_alert=True)
        return
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.VIDEO_ANIMATE
    )
    
    if not has_limit:
        if language == "ru":
            await callback.answer(f"⚠️ Лимит оживления фото исчерпан ({max_limit})", show_alert=True)
        else:
            await callback.answer(f"⚠️ Animate photo limit reached ({max_limit})", show_alert=True)
        return
    
    # Get file_id from Redis (saved during photo analysis)
    file_id = await redis_client.client.get(f"user:{user.id}:last_photo_file_id")
    
    if not file_id:
        if language == "ru":
            await callback.answer("Фото не найдено. Отправьте фото заново.", show_alert=True)
        else:
            await callback.answer("Photo not found. Send photo again.", show_alert=True)
        return
    
    file_id = file_id.decode() if isinstance(file_id, bytes) else file_id
    
    await redis_client.set_user_state(user.id, f"animate_photo:{file_id}")
    
    if language == "ru":
        await callback.message.answer(
            "🎞 <b>Оживление фото</b>\n\n"
            "Опишите, как должно двигаться/оживать изображение.\n\n"
            "<i>Например: «Камера медленно приближается, волосы развеваются на ветру»</i>\n\n"
            "Или отправьте точку (.) для автоматического оживления."
        )
    else:
        await callback.message.answer(
            "🎞 <b>Animate Photo</b>\n\n"
            "Describe how the image should move/animate.\n\n"
            "<i>Example: 'Camera slowly zooms in, hair blowing in the wind'</i>\n\n"
            "Or send a dot (.) for automatic animation."
        )
    
    await callback.answer()


@router.callback_query(F.data == "photo:edit_again")
async def callback_photo_edit_again(callback: CallbackQuery):
    """Handle 'Edit Again' button — enter chain-edit mode for the last edited photo."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    # Get last edited photo file_id
    file_id = await redis_client.client.get(f"user:{user.id}:last_photo_file_id")
    
    if not file_id:
        if language == "ru":
            await callback.answer("Фото не найдено. Отправьте фото заново.", show_alert=True)
        else:
            await callback.answer("Photo not found. Send a photo again.", show_alert=True)
        return
    
    file_id = file_id.decode() if isinstance(file_id, bytes) else file_id
    
    # Set chain-edit state
    await redis_client.set_user_state(user.id, f"photo_edit_chain:{file_id}")
    
    if language == "ru":
        await callback.message.answer(
            "✏️ <b>Редактирование фото</b>\n\n"
            "Напишите или скажите голосом, что изменить на фото.\n\n"
            "<i>Например: «Добавь тень», «Сделай ярче», «Убери фон»</i>"
        )
    else:
        await callback.message.answer(
            "✏️ <b>Photo Editing</b>\n\n"
            "Type or say what to change in the photo.\n\n"
            "<i>Example: 'Add shadow', 'Make brighter', 'Remove background'</i>"
        )
    
    await callback.answer()
