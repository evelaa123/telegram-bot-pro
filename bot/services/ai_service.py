"""
Unified AI service that routes requests to the appropriate provider.
Uses CometAPI as the main provider (Qwen-3-Max, DALL-E, Sora, Whisper).
GigaChat is used for presentations.
"""
from typing import Optional, AsyncGenerator, Dict, Any, List, Tuple, Literal
from decimal import Decimal

from bot.services.cometapi_service import cometapi_service, CometAPIService
from bot.services.openai_service import openai_service, OpenAIService
from bot.services.qwen_service import qwen_service, QwenService, get_qwen_service
from config import settings
import structlog

logger = structlog.get_logger()

AIProvider = Literal["cometapi", "openai", "qwen"]


class AIService:
    """
    Unified AI service that routes to CometAPI as main provider.
    Fixed models per TZ:
    - Text: Qwen-3-Max (via CometAPI)
    - Images: DALL-E 3 (via CometAPI)
    - Video: Sora 2 (via CometAPI)
    - Voice: Whisper (via CometAPI)
    - Presentations: GigaChat (direct)
    """
    
    # Fixed models (no user selection)
    MODELS = {
        "text": "qwen-3-max",
        "vision": "qwen-3-max",
        "image": "dall-e-3",
        "video": "sora-2",
        "voice": "whisper-1",
    }
    
    # Provider-specific model mappings (for backwards compatibility)
    PROVIDER_MODELS = {
        "cometapi": {
            "text": ["qwen-3-max"],
            "vision": ["qwen-3-max"],
            "image": ["dall-e-3"],
            "video": ["sora-2", "sora-2-pro"],
            "voice": ["whisper-1"],
        },
        "openai": {
            "text": ["gpt-4o", "gpt-4o-mini"],
            "vision": ["gpt-4o"],
            "image": ["dall-e-3"],
            "video": ["sora-2", "sora-2-pro"],
            "voice": ["whisper-1"],
            "tts": ["tts-1", "tts-1-hd"],
        },
        "qwen": {
            "text": ["qwen-turbo", "qwen-plus", "qwen-max", "qwen-max-longcontext"],
            "vision": ["qwen-vl-plus", "qwen-vl-max"],
            "image": ["wanx-v1", "wanx2.1-t2i-turbo", "wanx2.1-t2i-plus"],
            "video": [],
            "voice": ["paraformer-realtime-v2", "paraformer-v2"],
            "tts": ["cosyvoice-v1", "sambert-zhichu-v1"],
        }
    }
    
    # Default models per provider
    DEFAULT_MODELS = {
        "cometapi": {
            "text": "qwen-3-max",
            "vision": "qwen-3-max",
            "image": "dall-e-3",
            "video": "sora-2",
            "voice": "whisper-1",
        },
        "openai": {
            "text": "gpt-4o-mini",
            "vision": "gpt-4o",
            "image": "dall-e-3",
            "video": "sora-2",
            "voice": "whisper-1",
        },
        "qwen": {
            "text": "qwen-plus",
            "vision": "qwen-vl-plus",
            "image": "wanx-v1",
            "voice": "paraformer-realtime-v2",
        }
    }
    
    def __init__(self):
        self.cometapi = cometapi_service
        self.openai = openai_service
        self._qwen = None
    
    @property
    def qwen(self) -> QwenService:
        """Get Qwen service - lazy load to allow dynamic API key updates."""
        if self._qwen is None:
            self._qwen = qwen_service
        return self._qwen
    
    def refresh_qwen_service(self):
        """Force refresh of Qwen service to reload API key."""
        self._qwen = QwenService()
    
    def get_default_provider(self) -> AIProvider:
        """Get the default AI provider."""
        if self.cometapi.is_configured():
            return "cometapi"
        return "openai"
    
    async def get_provider_for_user(
        self, 
        telegram_id: int, 
        task_type: str = "text"
    ) -> Tuple[AIProvider, str]:
        """
        Get the appropriate provider and model for a user.
        Fixed models per TZ - no user selection.
        
        Args:
            telegram_id: User's Telegram ID
            task_type: Type of task (text, vision, image, video, voice)
            
        Returns:
            Tuple of (provider_name, model_name)
        """
        # Use CometAPI as main provider with fixed models
        if self.cometapi.is_configured():
            provider = "cometapi"
            model = self.MODELS.get(task_type, self.DEFAULT_MODELS["cometapi"].get(task_type))
        else:
            # Fallback to OpenAI if CometAPI not configured
            provider = "openai"
            model = self.DEFAULT_MODELS["openai"].get(task_type, "gpt-4o-mini")
        
        logger.debug(f"Provider for {task_type}: {provider}/{model}")
        return provider, model
    
    def get_service(self, provider: AIProvider):
        """Get the service instance for a provider."""
        if provider == "cometapi":
            return self.cometapi
        if provider == "qwen":
            return self.qwen
        return self.openai
    
    # =========================================
    # Text Generation
    # =========================================
    
    async def generate_text_stream(
        self,
        messages: List[Dict[str, str]],
        telegram_id: int = None,
        provider: AIProvider = None,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[Tuple[str, bool], None]:
        """
        Generate text with streaming, using CometAPI as main provider.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            telegram_id: User's Telegram ID (for auto provider selection)
            provider: Override provider selection
            model: Override model selection
            max_tokens: Maximum tokens to generate
            temperature: Creativity parameter
            
        Yields:
            Tuple of (chunk_text, is_complete_flag)
        """
        if not provider and telegram_id:
            provider, model = await self.get_provider_for_user(telegram_id, "text")
        elif not provider:
            provider = self.get_default_provider()
        
        if not model:
            model = self.DEFAULT_MODELS.get(provider, self.DEFAULT_MODELS["cometapi"])["text"]
        
        logger.info(f"Text generation using {provider}/{model}")
        
        service = self.get_service(provider)
        
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
        provider: AIProvider = None,
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate text without streaming.
        
        Returns:
            Tuple of (response_text, usage_info)
        """
        if not provider and telegram_id:
            provider, model = await self.get_provider_for_user(telegram_id, "text")
        elif not provider:
            provider = self.get_default_provider()
        
        if not model:
            model = self.DEFAULT_MODELS.get(provider, self.DEFAULT_MODELS["cometapi"])["text"]
        
        logger.info(f"Text generation using {provider}/{model}")
        
        service = self.get_service(provider)
        return await service.generate_text(
            messages=messages,
            model=model,
            max_tokens=max_tokens,
            temperature=temperature
        )
    
    # =========================================
    # Vision (Image Analysis)
    # =========================================
    
    async def analyze_image(
        self,
        image_url: str = None,
        image_data: bytes = None,
        prompt: str = "Describe this image in detail.",
        telegram_id: int = None,
        provider: AIProvider = None,
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze image using appropriate provider.
        
        Returns:
            Tuple of (analysis_text, usage_info)
        """
        if not provider and telegram_id:
            provider, model = await self.get_provider_for_user(telegram_id, "vision")
        elif not provider:
            provider = "openai"
        
        if not model:
            model = self.DEFAULT_MODELS[provider]["vision"]
        
        logger.info(f"Image analysis using {provider}/{model}")
        
        if provider == "qwen":
            return await self.qwen.analyze_image(
                image_url=image_url,
                image_data=image_data,
                prompt=prompt,
                model=model
            )
        else:
            return await self.openai.analyze_image(
                image_url=image_url,
                image_data=image_data,
                prompt=prompt,
                model=model
            )
    
    async def analyze_document_images(
        self,
        images: List[bytes],
        prompt: str,
        telegram_id: int = None,
        provider: AIProvider = None,
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze multiple document page images.
        
        Returns:
            Tuple of (analysis_text, usage_info)
        """
        if not provider and telegram_id:
            provider, model = await self.get_provider_for_user(telegram_id, "vision")
        elif not provider:
            provider = "openai"
        
        if not model:
            model = self.DEFAULT_MODELS[provider]["vision"]
        
        logger.info(f"Document analysis using {provider}/{model}")
        
        if provider == "qwen":
            return await self.qwen.analyze_document_images(
                images=images,
                prompt=prompt,
                model=model
            )
        else:
            return await self.openai.analyze_document_images(
                images=images,
                prompt=prompt,
                model=model
            )
    
    # =========================================
    # Image Generation
    # =========================================
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "vivid",
        quality: str = "standard",
        telegram_id: int = None,
        provider: AIProvider = None,
        model: str = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate image using appropriate provider.
        
        Args:
            prompt: Image description
            size: Image size
            style: Style (OpenAI: vivid/natural, Qwen: various presets)
            quality: Quality level
            telegram_id: User ID for provider selection
            provider: Override provider
            model: Override model
            
        Returns:
            Tuple of (image_url, usage_info)
        """
        if not provider and telegram_id:
            provider, model = await self.get_provider_for_user(telegram_id, "image")
        elif not provider:
            provider = "openai"
        
        logger.info(f"Image generation using {provider}")
        
        if provider == "qwen" and self.qwen.is_configured():
            # Convert size format for Qwen (1024x1024 -> 1024*1024)
            qwen_size = size.replace("x", "*")
            
            # Map OpenAI styles to Qwen styles
            style_map = {
                "vivid": "<auto>",
                "natural": "<photography>",
            }
            qwen_style = style_map.get(style, "<auto>")
            
            return await self.qwen.generate_image(
                prompt=prompt,
                size=qwen_size,
                model=model or settings.default_qwen_image_model,
                style=qwen_style,
            )
        else:
            # Use OpenAI DALL-E 3
            return await self.openai.generate_image(
                prompt=prompt,
                size=size,
                style=style,
                quality=quality
            )
    
    async def download_image(self, url: str, provider: AIProvider = "openai") -> bytes:
        """Download image from URL using appropriate service."""
        if provider == "qwen":
            return await self.qwen.download_image(url)
        return await self.openai.download_image(url)
    
    # =========================================
    # Video Generation (OpenAI only)
    # =========================================
    
    async def create_video(
        self,
        prompt: str,
        model: str = "sora-2",
        duration: int = 5,
        size: str = "1280x720"
    ) -> Dict[str, Any]:
        """
        Create video - always uses OpenAI Sora.
        Qwen doesn't have public video generation API.
        """
        return await self.openai.create_video(
            prompt=prompt,
            model=model,
            duration=duration,
            size=size
        )
    
    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """Check video generation status."""
        return await self.openai.get_video_status(video_id)
    
    async def download_video(self, video_id: str) -> bytes:
        """Download completed video."""
        return await self.openai.download_video(video_id)
    
    async def wait_for_video(
        self,
        video_id: str,
        poll_interval: int = 10,
        timeout: int = 600,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Wait for video generation to complete."""
        return await self.openai.wait_for_video(
            video_id=video_id,
            poll_interval=poll_interval,
            timeout=timeout,
            progress_callback=progress_callback
        )
    
    # =========================================
    # Speech Recognition
    # =========================================
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.ogg",
        language: str = None,
        telegram_id: int = None,
        provider: AIProvider = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe audio using appropriate provider.
        
        Returns:
            Tuple of (transcribed_text, usage_info)
        """
        if not provider and telegram_id:
            provider, _ = await self.get_provider_for_user(telegram_id, "voice")
        elif not provider:
            provider = "openai"
        
        logger.info(f"Audio transcription using {provider}")
        
        if provider == "qwen" and self.qwen.is_configured():
            return await self.qwen.transcribe_audio(
                audio_data=audio_data,
                filename=filename,
                language=language
            )
        else:
            return await self.openai.transcribe_audio(
                audio_data=audio_data,
                filename=filename,
                language=language
            )
    
    # =========================================
    # Text-to-Speech
    # =========================================
    
    async def synthesize_speech(
        self,
        text: str,
        voice: str = None,
        telegram_id: int = None,
        provider: AIProvider = None,
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Convert text to speech using appropriate provider.
        
        Returns:
            Tuple of (audio_bytes, usage_info)
        """
        if not provider and telegram_id:
            provider, _ = await self.get_provider_for_user(telegram_id, "tts")
        elif not provider:
            provider = "openai"
        
        logger.info(f"Text-to-speech using {provider}")
        
        if provider == "qwen" and self.qwen.is_configured():
            # Qwen voices: longxiaochun, longxiaoxia, etc.
            qwen_voice = voice or "longxiaochun"
            return await self.qwen.synthesize_speech(
                text=text,
                voice=qwen_voice
            )
        else:
            # OpenAI TTS
            # TODO: Implement OpenAI TTS if needed
            raise NotImplementedError("OpenAI TTS not implemented yet")
    
    # =========================================
    # Utility Methods
    # =========================================
    
    def get_available_models(self, provider: AIProvider, task_type: str) -> List[str]:
        """Get available models for a provider and task type."""
        return self.PROVIDER_MODELS.get(provider, {}).get(task_type, [])
    
    def is_provider_available(self, provider: AIProvider, task_type: str) -> bool:
        """Check if a provider supports a specific task type."""
        models = self.get_available_models(provider, task_type)
        if not models:
            return False
        if provider == "qwen":
            return self.qwen.is_configured()
        return True
    
    def get_provider_status(self) -> Dict[str, Dict[str, Any]]:
        """Get status of all providers."""
        qwen_configured = self.qwen.is_configured()
        
        return {
            "openai": {
                "configured": True,
                "capabilities": ["text", "vision", "image", "video", "voice"]
            },
            "qwen": {
                "configured": qwen_configured,
                "capabilities": ["text", "vision", "image", "voice", "tts"] if qwen_configured else []
            }
        }


# Global service instance
ai_service = AIService()
