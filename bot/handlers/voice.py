"""
Voice message handler.
Handles Whisper and Qwen ASR speech recognition.
"""
import io
from aiogram import Router, F
from aiogram.types import Message
from aiogram.enums import ChatAction

from bot.services.ai_service import ai_service
from bot.services.user_service import user_service
from bot.services.limit_service import limit_service
from database.redis_client import redis_client
from database.models import RequestType, RequestStatus
from config import settings
import structlog

logger = structlog.get_logger()
router = Router()


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
    
    # Send progress message
    if language == "ru":
        progress_msg = await message.answer("🎤 Распознаю речь (Whisper)...")
    else:
        progress_msg = await message.answer("🎤 Transcribing speech (Whisper)...")
    
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
        
        # Format result
        model_used = usage.get("model", "unknown")
        if language == "ru":
            result_text = f"📝 <b>Распознанный текст ({model_used}):</b>\n\n{text}"
        else:
            result_text = f"📝 <b>Transcribed text ({model_used}):</b>\n\n{text}"
        
        await progress_msg.edit_text(result_text)
        
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
        
        # Auto-process with GPT if enabled
        if auto_process and text.strip():
            await _auto_process_transcribed_text(
                message=message,
                user_id=user.id,
                text=text,
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
    Separate function to handle the GPT response generation.
    """
    if language == "ru":
        processing_msg = await message.answer("💭 Обрабатываю ваш запрос...")
    else:
        processing_msg = await message.answer("💭 Processing your request...")
    
    try:
        # Get context
        context = await redis_client.get_context(user_id)
        
        # Build messages
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
        
        # Stream response
        full_response = ""
        last_update_len = 0
        
        async for chunk, is_complete in ai_service.generate_text_stream(
            messages=messages,
            telegram_id=user_id
        ):
            full_response += chunk
            
            # Update message every ~300 chars or on completion
            if len(full_response) - last_update_len > 300 or is_complete:
                try:
                    display_text = full_response[:4000] if len(full_response) > 4000 else full_response
                    if display_text.strip():
                        await processing_msg.edit_text(display_text)
                        last_update_len = len(full_response)
                except Exception:
                    pass
        
        # Final update
        if full_response.strip():
            try:
                display_text = full_response[:4000]
                if len(full_response) > 4000:
                    display_text += "\n\n... (ответ обрезан)"
                await processing_msg.edit_text(display_text)
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
                response_length=len(full_response)
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
        
        # Format result
        if len(text) > 4000:
            text = text[:4000] + "\n\n... (текст обрезан)"
        
        model_used = usage.get("model", "unknown")
        if language == "ru":
            result_text = f"📝 <b>Распознанный текст из {filename} ({model_used}):</b>\n\n{text}"
        else:
            result_text = f"📝 <b>Transcribed text from {filename} ({model_used}):</b>\n\n{text}"
        
        await progress_msg.edit_text(result_text)
        
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
