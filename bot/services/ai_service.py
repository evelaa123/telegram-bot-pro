"""
Unified AI service that routes requests to the appropriate provider.
Uses CometAPI as the main provider for all AI operations.
GigaChat is used for presentations (separate API).
"""
from typing import Optional, AsyncGenerator, Dict, Any, List, Tuple, Literal
from decimal import Decimal

from bot.services.cometapi_service import cometapi_service, CometAPIService
from bot.services.openai_service import openai_service, OpenAIService
from config import settings
import structlog

logger = structlog.get_logger()

AIProvider = Literal["cometapi", "openai"]


class AIService:
    """
    Unified AI service that routes ALL requests to CometAPI.
    
    Models are configurable via admin panel:
    - Text: default qwen3-max-2026-01-23 (via CometAPI)
    - Vision: default qwen3-max-2026-01-23 (via CometAPI)
    - Images: default dall-e-3 (via CometAPI)
    - Video: default sora-2 (via CometAPI)
    - Voice: default whisper-1 (via CometAPI)
    - Presentations: GigaChat (direct API, separate)
    """
    
    def __init__(self):
        self.cometapi = cometapi_service
        self.openai = openai_service  # Fallback only
    
    def get_models(self) -> Dict[str, str]:
        """Get current model configuration from settings."""
        return {
            "text": getattr(settings, 'default_text_model', 'qwen3-max-2026-01-23'),
            "vision": getattr(settings, 'default_vision_model', 'qwen3-vl-30b-a3b'),
            "image": getattr(settings, 'default_image_model', 'qwen-image'),
            "video": getattr(settings, 'default_video_model', 'sora-2'),
            "voice": getattr(settings, 'default_whisper_model', 'whisper-1'),
        }
    
    @property
    def MODELS(self) -> Dict[str, str]:
        """Backward compatibility property for MODELS."""
        return self.get_models()
    
    def is_configured(self) -> bool:
        """Check if main provider (CometAPI) is configured."""
        return self.cometapi.is_configured()
    
    def get_default_provider(self) -> AIProvider:
        """Get the default AI provider - always CometAPI if configured."""
        if self.cometapi.is_configured():
            return "cometapi"
        return "openai"
    
    def get_service(self, provider: AIProvider = None):
        """Get the service instance for a provider."""
        if provider == "openai":
            return self.openai
        return self.cometapi
    
    # =========================================
    # Text Generation (CometAPI / qwen3-max-2026-01-23)
    # =========================================
    
    async def generate_text_stream(
        self,
        messages: List[Dict[str, str]],
        telegram_id: int = None,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[Tuple[str, bool], None]:
        """
        Generate text with streaming using CometAPI (qwen3-max-2026-01-23).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            telegram_id: User's Telegram ID (for logging)
            model: Override model (default: qwen3-max-2026-01-23)
            max_tokens: Maximum tokens to generate
            temperature: Creativity parameter
            
        Yields:
            Tuple of (chunk_text, is_complete_flag)
        """
        model = model or self.MODELS["text"]
        
        # Use CometAPI if configured, otherwise fall back to OpenAI
        if self.cometapi.is_configured():
            service = self.cometapi
            logger.info(f"Text generation using CometAPI/{model}", user_id=telegram_id)
        else:
            service = self.openai
            model = "gpt-4o-mini"  # Fallback model
            logger.info(f"Text generation using OpenAI/{model} (fallback)", user_id=telegram_id)
        
        async for chunk, is_complete in service.generate_text_stream(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        ):
            yield chunk, is_complete
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        telegram_id: int = None,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate text without streaming using CometAPI (qwen3-max-2026-01-23).
        
        Returns:
            Tuple of (response_text, usage_info)
        """
        model = model or self.MODELS["text"]
        
        if self.cometapi.is_configured():
            service = self.cometapi
            logger.info(f"Text generation using CometAPI/{model}", user_id=telegram_id)
        else:
            service = self.openai
            model = "gpt-4o-mini"
            logger.info(f"Text generation using OpenAI/{model} (fallback)", user_id=telegram_id)
        
        return await service.generate_text(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    # =========================================
    # Vision (Image Analysis via CometAPI)
    # =========================================
    
    async def analyze_image(
        self,
        image_url: str = None,
        image_data: bytes = None,
        prompt: str = "Describe this image in detail.",
        telegram_id: int = None,
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze image using CometAPI (qwen3-max-2026-01-23 vision).
        
        Returns:
            Tuple of (analysis_text, usage_info)
        """
        model = model or self.MODELS["vision"]
        
        if self.cometapi.is_configured():
            logger.info(f"Image analysis using CometAPI/{model}", user_id=telegram_id)
            return await self.cometapi.analyze_image(
                image_url=image_url,
                image_data=image_data,
                prompt=prompt,
                model=model
            )
        else:
            logger.info("Image analysis using OpenAI/gpt-4o (fallback)", user_id=telegram_id)
            return await self.openai.analyze_image(
                image_url=image_url,
                image_data=image_data,
                prompt=prompt,
                model="gpt-4o"
            )
    
    async def analyze_document_images(
        self,
        images: List[bytes],
        prompt: str,
        telegram_id: int = None,
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze multiple document page images via CometAPI.
        
        Returns:
            Tuple of (analysis_text, usage_info)
        """
        model = model or self.MODELS["vision"]
        
        if self.cometapi.is_configured():
            logger.info(f"Document analysis using CometAPI/{model}", user_id=telegram_id)
            return await self.cometapi.analyze_document_images(
                images=images,
                prompt=prompt,
                model=model
            )
        else:
            logger.info("Document analysis using OpenAI/gpt-4o (fallback)", user_id=telegram_id)
            return await self.openai.analyze_document_images(
                images=images,
                prompt=prompt,
                model="gpt-4o"
            )
    
    # =========================================
    # Image Generation (CometAPI / DALL-E 3)
    # =========================================
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "vivid",
        quality: str = "standard",
        telegram_id: int = None,
        model: str = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate image using CometAPI (DALL-E 3).
        
        Args:
            prompt: Image description
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            style: Style (vivid, natural)
            quality: Quality level (standard, hd)
            telegram_id: User ID for logging
            model: Override model (default: dall-e-3)
            
        Returns:
            Tuple of (image_url, usage_info)
        """
        model = model or self.MODELS["image"]
        
        if self.cometapi.is_configured():
            logger.info(f"Image generation using CometAPI/{model}", user_id=telegram_id, size=size)
            return await self.cometapi.generate_image(
                prompt=prompt,
                size=size,
                style=style,
                quality=quality,
                model=model
            )
        else:
            logger.info("Image generation using OpenAI/dall-e-3 (fallback)", user_id=telegram_id)
            return await self.openai.generate_image(
                prompt=prompt,
                size=size,
                style=style,
                quality=quality
            )
    
    async def download_image(self, url: str) -> bytes:
        """Download image from URL."""
        if self.cometapi.is_configured():
            return await self.cometapi.download_image(url)
        return await self.openai.download_image(url)
    
    # =========================================
    # Video Generation (CometAPI / Sora)
    # =========================================
    
    async def create_video(
        self,
        prompt: str,
        model: str = None,
        duration: int = 4,
        size: str = "1280x720",
        telegram_id: int = None,
        input_reference: bytes = None
    ) -> Dict[str, Any]:
        """
        Create video using CometAPI Official Format (Sora 2).
        
        Args:
            prompt: Video description
            model: sora-2 or sora-2-pro (default: sora-2)
            duration: Duration in seconds (4, 8, or 12)
            size: Resolution
            telegram_id: User ID for logging
            input_reference: Optional reference image bytes for image-to-video animation
            
        Returns:
            Video task info with video_id
        """
        model = model or self.MODELS["video"]
        
        if self.cometapi.is_configured():
            logger.info(
                f"Video creation using CometAPI/{model}",
                user_id=telegram_id,
                duration=duration,
                has_reference=input_reference is not None
            )
            return await self.cometapi.create_video(
                prompt=prompt,
                model=model,
                duration=duration,
                size=size,
                input_reference=input_reference
            )
        else:
            logger.info(f"Video creation using OpenAI/{model} (fallback)", user_id=telegram_id)
            return await self.openai.create_video(
                prompt=prompt,
                model=model,
                duration=duration,
                size=size
            )
    
    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """Check video generation status."""
        if self.cometapi.is_configured():
            return await self.cometapi.get_video_status(video_id)
        return await self.openai.get_video_status(video_id)
    
    async def download_video(self, video_id: str) -> bytes:
        """Download completed video."""
        if self.cometapi.is_configured():
            return await self.cometapi.download_video(video_id)
        return await self.openai.download_video(video_id)
    
    async def wait_for_video(
        self,
        video_id: str,
        poll_interval: int = 10,
        timeout: int = 600,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Wait for video generation to complete."""
        if self.cometapi.is_configured():
            return await self.cometapi.wait_for_video(
                video_id=video_id,
                poll_interval=poll_interval,
                timeout=timeout,
                progress_callback=progress_callback
            )
        return await self.openai.wait_for_video(
            video_id=video_id,
            poll_interval=poll_interval,
            timeout=timeout,
            progress_callback=progress_callback
        )
    
    # =========================================
    # Speech Recognition (CometAPI / Whisper)
    # =========================================
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.ogg",
        language: str = None,
        telegram_id: int = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe audio using CometAPI (Whisper).
        
        Returns:
            Tuple of (transcribed_text, usage_info)
        """
        if self.cometapi.is_configured():
            logger.info(f"Audio transcription using CometAPI/whisper-1", user_id=telegram_id)
            return await self.cometapi.transcribe_audio(
                audio_data=audio_data,
                filename=filename,
                language=language
            )
        else:
            logger.info("Audio transcription using OpenAI/whisper-1 (fallback)", user_id=telegram_id)
            return await self.openai.transcribe_audio(
                audio_data=audio_data,
                filename=filename,
                language=language
            )
    
    # =========================================
    # Meeting Protocol Generation
    # =========================================
    
    async def generate_meeting_protocol(
        self,
        transcription: str,
        language: str = "ru",
        telegram_id: int = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate meeting protocol from transcription using CometAPI.
        
        Returns:
            Tuple of (protocol_text, usage_info)
        """
        if self.cometapi.is_configured():
            logger.info("Meeting protocol generation using CometAPI", user_id=telegram_id)
            return await self.cometapi.generate_meeting_protocol(
                transcription=transcription,
                language=language
            )
        else:
            # Fallback: use OpenAI for meeting protocol
            logger.info("Meeting protocol generation using OpenAI (fallback)", user_id=telegram_id)
            
            if language == "ru":
                system_prompt = """Ты — профессиональный секретарь, который создаёт протоколы совещаний.
На основе транскрипции создай структурированный протокол совещания."""
            else:
                system_prompt = """You are a professional secretary who creates meeting protocols.
Based on the transcription, create a structured meeting protocol."""
            
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Создай протокол на основе этой транскрипции:\n\n{transcription}"}
            ]
            
            return await self.openai.generate_text(messages, max_tokens=4096, temperature=0.3)
    
    # =========================================
    # Utility Methods
    # =========================================
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of AI providers."""
        return {
            "cometapi": {
                "configured": self.cometapi.is_configured(),
                "is_primary": True,
                "capabilities": ["text", "vision", "image", "video", "voice"]
            },
            "openai": {
                "configured": True,  # Always available as fallback
                "is_primary": False,
                "capabilities": ["text", "vision", "image", "video", "voice"]
            }
        }
    
    def is_provider_available(self, provider: str, task_type: str) -> bool:
        """Check if provider supports a task type."""
        if provider == "cometapi":
            return self.cometapi.is_configured()
        return True  # OpenAI always available


# Global service instance
ai_service = AIService()
