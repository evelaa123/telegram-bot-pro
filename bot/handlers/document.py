"""
Document processing handler.
Handles various document formats with GPT-4o Vision.
"""
import asyncio
import time
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.enums import ChatAction

from bot.services.openai_service import openai_service
from bot.services.document_service import document_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from bot.keyboards.inline import get_document_actions_keyboard
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


@router.message(F.document)
async def handle_document(message: Message):
    """Handle document uploads."""
    
    # В группах документы обрабатываются иначе (или игнорируются)
    if message.chat.type in ("group", "supergroup"):
        return
    
    user = message.from_user
    doc = message.document
    
    # Get user settings
    user_settings = await user_service.get_user_settings(user.id)
    language = user_settings.get("language", "ru")
    
    # Check if format is supported
    filename = doc.file_name or "document"
    
    if not document_service.is_supported(filename):
        ext = filename.split('.')[-1] if '.' in filename else 'unknown'
        if language == "ru":
            await message.answer(
                f"⚠️ Формат файла .{ext} не поддерживается.\n\n"
                "Поддерживаемые форматы:\n"
                "• PDF, Word (DOCX), Excel (XLSX), PowerPoint (PPTX)\n"
                "• Текст (TXT, MD, CSV, JSON, XML)\n"
                "• Изображения (JPG, PNG, WEBP, GIF)"
            )
        else:
            await message.answer(
                f"⚠️ File format .{ext} is not supported.\n\n"
                "Supported formats:\n"
                "• PDF, Word (DOCX), Excel (XLSX), PowerPoint (PPTX)\n"
                "• Text (TXT, MD, CSV, JSON, XML)\n"
                "• Images (JPG, PNG, WEBP, GIF)"
            )
        return
    
    # Check file size
    max_size = settings.max_file_size_mb * 1024 * 1024
    if doc.file_size and doc.file_size > max_size:
        if language == "ru":
            await message.answer(
                f"⚠️ Файл слишком большой.\n"
                f"Максимальный размер: {settings.max_file_size_mb} MB"
            )
        else:
            await message.answer(
                f"⚠️ File is too large.\n"
                f"Maximum size: {settings.max_file_size_mb} MB"
            )
        return
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.DOCUMENT
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита обработки документов на сегодня ({max_limit})."
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily document processing limit ({max_limit})."
            )
        return
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    # Send progress message
    if language == "ru":
        progress_msg = await message.answer(f"📄 Обрабатываю файл <b>{filename}</b>...")
    else:
        progress_msg = await message.answer(f"📄 Processing file <b>{filename}</b>...")
    
    try:
        # Download file
        file = await message.bot.get_file(doc.file_id)
        file_bytes_io = await message.bot.download_file(file.file_path)
        file_data = file_bytes_io.read() if hasattr(file_bytes_io, 'read') else file_bytes_io
        
        # Process document
        text, metadata, images = await document_service.process_document(
            file_data=file_data,
            filename=filename,
            max_pages=settings.max_pdf_pages,
            max_rows=settings.max_excel_rows,
            max_slides=settings.max_ppt_slides
        )
        
        # Store document context for follow-up questions
        if text:
            await redis_client.set_document_context(
                user.id,
                content=text[:50000],  # Limit stored content
                filename=filename
            )
        
        # If it's an image, analyze directly
        if metadata.get("type") == "image" and images:
            await analyze_document_with_vision(
                message=message,
                progress_msg=progress_msg,
                user_id=user.id,
                filename=filename,
                images=images,
                language=language,
                caption=message.caption
            )
            return
        
        # Show document info and ask what to do
        if language == "ru":
            info_parts = [f"📄 <b>Документ загружен: {filename}</b>\n"]
            
            if metadata.get("type") == "pdf":
                info_parts.append(f"📑 Страниц: {metadata.get('processed_pages', '?')}")
                if metadata.get("image_pages"):
                    info_parts.append(f"🖼 Страниц-изображений: {metadata.get('image_pages')}")
            elif metadata.get("type") == "xlsx":
                info_parts.append(f"📊 Листов: {metadata.get('sheets', '?')}")
                info_parts.append(f"📋 Строк: {metadata.get('total_rows', '?')}")
            elif metadata.get("type") == "pptx":
                info_parts.append(f"🎯 Слайдов: {metadata.get('processed_slides', '?')}")
            elif metadata.get("type") == "docx":
                info_parts.append(f"📝 Абзацев: {metadata.get('paragraphs', '?')}")
                if metadata.get("tables"):
                    info_parts.append(f"📋 Таблиц: {metadata.get('tables')}")
            
            if metadata.get("warning"):
                info_parts.append(f"\n⚠️ {metadata.get('warning')}")
            
            info_parts.append("\n\nЧто сделать с документом?")
            info_text = "\n".join(info_parts)
        else:
            info_parts = [f"📄 <b>Document loaded: {filename}</b>\n"]
            
            if metadata.get("type") == "pdf":
                info_parts.append(f"📑 Pages: {metadata.get('processed_pages', '?')}")
            elif metadata.get("type") == "xlsx":
                info_parts.append(f"📊 Sheets: {metadata.get('sheets', '?')}")
                info_parts.append(f"📋 Rows: {metadata.get('total_rows', '?')}")
            elif metadata.get("type") == "pptx":
                info_parts.append(f"🎯 Slides: {metadata.get('processed_slides', '?')}")
            elif metadata.get("type") == "docx":
                info_parts.append(f"📝 Paragraphs: {metadata.get('paragraphs', '?')}")
            
            if metadata.get("warning"):
                info_parts.append(f"\n⚠️ {metadata.get('warning')}")
            
            info_parts.append("\n\nWhat would you like to do with the document?")
            info_text = "\n".join(info_parts)
        
        # If caption provided, process immediately
        if message.caption and message.caption.strip():
            await progress_msg.delete()
            await process_document_request(
                message=message,
                user_id=user.id,
                text=text,
                images=images,
                request=message.caption,
                filename=filename,
                language=language
            )
        else:
            await progress_msg.edit_text(
                info_text,
                reply_markup=get_document_actions_keyboard(language)
            )
        
        logger.info(
            "Document processed",
            user_id=user.id,
            filename=filename,
            type=metadata.get("type"),
            has_images=bool(images)
        )
        
    except Exception as e:
        logger.error("Document processing error", user_id=user.id, error=str(e))
        
        if language == "ru":
            await progress_msg.edit_text(
                "❌ Произошла ошибка при обработке документа.\n"
                "Проверьте, что файл не повреждён, и попробуйте ещё раз."
            )
        else:
            await progress_msg.edit_text(
                "❌ An error occurred processing the document.\n"
                "Check that the file is not corrupted and try again."
            )


@router.message(F.photo)
async def handle_photo(message: Message):
    """Handle photo uploads - analyze with GPT-4o Vision."""
    
    # В группах фото обрабатывает channel_comments.py
    if message.chat.type in ("group", "supergroup"):
        return
    
    user = message.from_user
    
    # Get the largest photo
    photo = message.photo[-1]
    
    # Get user settings
    user_settings = await user_service.get_user_settings(user.id)
    language = user_settings.get("language", "ru")
    
    # Check limits
    has_limit, current, max_limit = await limit_service.check_limit(
        user.id, RequestType.DOCUMENT
    )
    
    if not has_limit:
        if language == "ru":
            await message.answer(
                f"⚠️ Вы достигли лимита обработки документов на сегодня ({max_limit})."
            )
        else:
            await message.answer(
                f"⚠️ You've reached your daily document processing limit ({max_limit})."
            )
        return
    
    # Show typing indicator
    await message.bot.send_chat_action(message.chat.id, ChatAction.TYPING)
    
    if language == "ru":
        progress_msg = await message.answer("🖼 Анализирую изображение...")
    else:
        progress_msg = await message.answer("🖼 Analyzing image...")
    
    try:
        # Download photo
        file = await message.bot.get_file(photo.file_id)
        file_bytes_io = await message.bot.download_file(file.file_path)
        image_data = file_bytes_io.read() if hasattr(file_bytes_io, 'read') else file_bytes_io
        
        await analyze_document_with_vision(
            message=message,
            progress_msg=progress_msg,
            user_id=user.id,
            filename="photo.jpg",
            images=[image_data],
            language=language,
            caption=message.caption
        )
        
    except Exception as e:
        logger.error("Photo analysis error", user_id=user.id, error=str(e))
        
        if language == "ru":
            await progress_msg.edit_text(
                "❌ Произошла ошибка при анализе изображения."
            )
        else:
            await progress_msg.edit_text(
                "❌ An error occurred analyzing the image."
            )


async def analyze_document_with_vision(
    message: Message,
    progress_msg: Message,
    user_id: int,
    filename: str,
    images: list,
    language: str,
    caption: str = None
):
    """
    Analyze document images with GPT-4o Vision.
    """
    # Determine prompt based on caption or default
    if caption and caption.strip():
        prompt = caption
    else:
        if language == "ru":
            prompt = (
                "Проанализируй это изображение. "
                "Опиши его содержимое подробно. "
                "Если это документ, извлеки и структурируй текст."
            )
        else:
            prompt = (
                "Analyze this image. "
                "Describe its contents in detail. "
                "If it's a document, extract and structure the text."
            )
    
    start_time = time.time()
    
    try:
        if len(images) == 1:
            # Single image analysis
            result, usage = await openai_service.analyze_image(
                image_data=images[0],
                prompt=prompt
            )
        else:
            # Multiple images (PDF pages)
            result, usage = await openai_service.analyze_document_images(
                images=images[:10],  # Limit to 10 images
                prompt=prompt
            )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Truncate result if needed
        if len(result) > 4000:
            result = result[:4000] + "\n\n... (ответ обрезан)"
        
        await progress_msg.edit_text(result)
        
        # Store in document context for follow-up
        await redis_client.set_document_context(
            user_id,
            content=result,
            filename=filename
        )
        
        # Increment usage and record
        await limit_service.increment_usage(user_id, RequestType.DOCUMENT)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.DOCUMENT,
            prompt=prompt[:500],
            response_preview=result[:500],
            model="gpt-4o",
            cost_usd=float(usage.get("cost_usd", 0)),
            status=RequestStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(
            "Image analyzed",
            user_id=user_id,
            images_count=len(images),
            duration_ms=duration_ms
        )
        
    except Exception as e:
        logger.error("Vision analysis error", user_id=user_id, error=str(e))
        
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.DOCUMENT,
            prompt=prompt[:500],
            model="gpt-4o",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )
        
        raise


@router.callback_query(F.data == "document:summarize")
async def callback_document_summarize(callback: CallbackQuery):
    """Handle document summarization request."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    doc_context = await redis_client.get_document_context(user.id)
    
    if not doc_context:
        if language == "ru":
            await callback.answer("Документ не найден. Загрузите файл снова.", show_alert=True)
        else:
            await callback.answer("Document not found. Upload the file again.", show_alert=True)
        return
    
    await callback.answer("Summarizing...")
    
    if language == "ru":
        request = "Суммаризируй этот документ. Выдели ключевые пункты и главные выводы."
    else:
        request = "Summarize this document. Highlight key points and main conclusions."
    
    await process_document_request(
        message=callback.message,
        user_id=user.id,
        text=doc_context["content"],
        images=[],
        request=request,
        filename=doc_context["filename"],
        language=language
    )


@router.callback_query(F.data == "document:question")
async def callback_document_question(callback: CallbackQuery):
    """Handle document question request."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    doc_context = await redis_client.get_document_context(user.id)
    
    if not doc_context:
        if language == "ru":
            await callback.answer("Документ не найден. Загрузите файл снова.", show_alert=True)
        else:
            await callback.answer("Document not found. Upload the file again.", show_alert=True)
        return
    
    # Set state to await question
    await redis_client.set_user_state(user.id, "document_question")
    
    if language == "ru":
        await callback.message.edit_text(
            f"📄 Документ: <b>{doc_context['filename']}</b>\n\n"
            "❓ Задайте ваш вопрос по документу:"
        )
    else:
        await callback.message.edit_text(
            f"📄 Document: <b>{doc_context['filename']}</b>\n\n"
            "❓ Ask your question about the document:"
        )
    
    await callback.answer()


@router.callback_query(F.data == "document:translate")
async def callback_document_translate(callback: CallbackQuery):
    """Handle document translation request."""
    user = callback.from_user
    language = await user_service.get_user_language(user.id)
    
    doc_context = await redis_client.get_document_context(user.id)
    
    if not doc_context:
        if language == "ru":
            await callback.answer("Документ не найден. Загрузите файл снова.", show_alert=True)
        else:
            await callback.answer("Document not found. Upload the file again.", show_alert=True)
        return
    
    await callback.answer("Translating...")
    
    if language == "ru":
        request = "Переведи этот документ на русский язык, сохраняя структуру."
    else:
        request = "Translate this document to English, preserving the structure."
    
    await process_document_request(
        message=callback.message,
        user_id=user.id,
        text=doc_context["content"],
        images=[],
        request=request,
        filename=doc_context["filename"],
        language=language
    )


async def process_document_request(
    message: Message,
    user_id: int,
    text: str,
    images: list,
    request: str,
    filename: str,
    language: str
):
    """
    Process user request about document.
    """
    if language == "ru":
        progress_msg = await message.answer("💭 Обрабатываю запрос...")
    else:
        progress_msg = await message.answer("💭 Processing request...")
    
    start_time = time.time()
    
    try:
        # Build messages
        system_prompt = (
            "You are a document analysis assistant. "
            "Answer questions about the provided document content. "
            "Be accurate and cite specific parts when relevant. "
            f"Respond in {'Russian' if language == 'ru' else 'English'}."
        )
        
        # Limit document text
        doc_text = text[:30000] if text else ""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Document content:\n\n{doc_text}\n\nUser request: {request}"}
        ]
        
        # Generate response
        response, usage = await openai_service.generate_text(
            messages=messages,
            model="gpt-4o"
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Truncate if needed
        if len(response) > 4000:
            response = response[:4000] + "\n\n... (ответ обрезан)"
        
        await progress_msg.edit_text(response)
        
        # Increment usage and record
        await limit_service.increment_usage(user_id, RequestType.DOCUMENT)
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.DOCUMENT,
            prompt=request[:500],
            response_preview=response[:500],
            model="gpt-4o",
            tokens_input=usage.get("input_tokens"),
            tokens_output=usage.get("output_tokens"),
            cost_usd=float(usage.get("cost_usd", 0)),
            status=RequestStatus.SUCCESS,
            duration_ms=duration_ms
        )
        
        logger.info(
            "Document request processed",
            user_id=user_id,
            filename=filename,
            request_preview=request[:100]
        )
        
    except Exception as e:
        logger.error("Document request error", user_id=user_id, error=str(e))
        
        await limit_service.record_request(
            telegram_id=user_id,
            request_type=RequestType.DOCUMENT,
            prompt=request[:500],
            model="gpt-4o",
            status=RequestStatus.FAILED,
            error_message=str(e)
        )
        
        if language == "ru":
            await progress_msg.edit_text(
                "❌ Произошла ошибка при обработке запроса."
            )
        else:
            await progress_msg.edit_text(
                "❌ An error occurred processing the request."
            )
