"""
CometAPI service for AI operations.
Uses OpenAI-compatible API with CometAPI as provider.
Supports Qwen-3-Max for text/image/video, Whisper for audio.
"""
import asyncio
import io
import base64
from typing import Optional, AsyncGenerator, Dict, Any, List, Tuple
from decimal import Decimal
import aiohttp
from openai import AsyncOpenAI

from config import settings
from bot.services.usage_tracking_service import usage_tracking_service
import structlog

logger = structlog.get_logger()


class CometAPIService:
    """
    Service for interacting with CometAPI.
    Provides unified access to Qwen-3-Max, image generation, video generation, and Whisper.
    """
    
    @property
    def BASE_URL(self) -> str:
        """Get CometAPI base URL from settings (supports runtime changes via admin panel)."""
        # First check if there's a cached base URL from DB settings
        if hasattr(self, '_cached_base_url') and self._cached_base_url:
            return self._cached_base_url
        return getattr(settings, 'cometapi_base_url', 'https://api.cometapi.com/v1')
    
    def set_base_url(self, url: str):
        """Set cached base URL (called when admin updates settings)."""
        self._cached_base_url = url
        self.reset_client()  # Force client reset to use new URL
        logger.info("CometAPI base URL updated", base_url=url)
    
    # Model names in CometAPI
    MODELS = {
        "text": "qwen-3-max",  # Qwen 3 Max for text generation
        "image": "dall-e-3",   # DALL-E 3 through CometAPI
        "video": "sora-2",     # Sora 2 (4/8/12 sec)
        "whisper": "whisper-1",  # Whisper for speech recognition
    }
    
    # Video models configuration
    # sora-2: durations 4, 8, 12 seconds
    # sora-2-pro: durations 4, 8, 12 seconds (higher quality)
    VIDEO_MODELS = {
        "sora-2": {
            "durations": [4, 8, 12],
            "per_second": 0.05
        },
        "sora-2-pro": {
            "durations": [4, 8, 12],
            "per_second": 0.10
        }
    }
    
    # Pricing estimates (per 1K tokens or per request)
    PRICING = {
        "qwen-3-max": {"input": 0.002, "output": 0.008},
        "qwen3-max-2026-01-23": {"input": 0.002, "output": 0.008},
        "qwen3-vl-30b-a3b": {"input": 0.00012, "output": 0.00048},
        "qwen3-vl-235b-a22b": {"input": 0.00024, "output": 0.00096},
        "dall-e-3": {
            "1024x1024": 0.04,
            "1792x1024": 0.08,
            "1024x1792": 0.08
        },
        "whisper-1": 0.006,
        "sora-2": {"per_second": 0.05},
        "sora-2-pro": {"per_second": 0.10}
    }
    
    def __init__(self):
        self._client = None
        self._api_key = None
        self._base_url = None
    
    @property
    def client(self) -> AsyncOpenAI:
        """Get or create OpenAI client configured for CometAPI."""
        api_key = getattr(settings, 'cometapi_api_key', None) or settings.openai_api_key
        base_url = self.BASE_URL
        
        # Recreate client if API key or base URL changed
        if self._client is None or self._api_key != api_key or self._base_url != base_url:
            self._api_key = api_key
            self._base_url = base_url
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=base_url,
                timeout=settings.openai_timeout
            )
            logger.info("CometAPI client created/updated", base_url=base_url)
        
        return self._client
    
    def reset_client(self):
        """Force reset the client to pick up new settings."""
        self._client = None
        self._api_key = None
        self._base_url = None
        logger.info("CometAPI client reset")
    
    def is_configured(self) -> bool:
        """Check if CometAPI is configured."""
        api_key = getattr(settings, 'cometapi_api_key', None)
        return bool(api_key and len(api_key) > 10)
    
    # =========================================
    # Text Generation (Qwen-3-Max)
    # =========================================
    
    async def generate_text_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[Tuple[str, bool], None]:
        """
        Generate text with streaming response using Qwen-3-Max.
        
        Yields tuples of (text_chunk, is_complete).
        """
        model = model or self.MODELS["text"]
        
        try:
            stream = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                stream=True
            )
            
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    is_complete = chunk.choices[0].finish_reason is not None
                    yield content, is_complete
                elif chunk.choices and chunk.choices[0].finish_reason:
                    yield "", True
                    
        except Exception as e:
            error_msg = str(e) or f"{type(e).__name__}: (no details)"
            logger.error("CometAPI text streaming error", error=error_msg, model=model, error_type=type(e).__name__)
            raise
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate text without streaming using Qwen-3-Max.
        
        Returns:
            Tuple of (response_text, usage_info)
        """
        model = model or self.MODELS["text"]
        
        try:
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            content = response.choices[0].message.content
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
                "model": model,
                "provider": "cometapi"
            }
            
            # Calculate cost
            pricing = self.PRICING.get(model, self.PRICING["qwen-3-max"])
            cost = (
                (usage["input_tokens"] / 1000) * pricing["input"] +
                (usage["output_tokens"] / 1000) * pricing["output"]
            )
            usage["cost_usd"] = Decimal(str(round(cost, 6)))
            
            # Log API usage for tracking
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model,
                    endpoint="chat",
                    input_tokens=usage["input_tokens"],
                    output_tokens=usage["output_tokens"],
                    cost_usd=usage["cost_usd"],
                    success=True
                )
            except Exception as log_error:
                logger.warning("Failed to log API usage", error=str(log_error))
            
            return content, usage
            
        except Exception as e:
            logger.error("CometAPI text generation error", error=str(e), model=model)
            # Log failed call
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model,
                    endpoint="chat",
                    success=False,
                    error_message=str(e)
                )
            except Exception:
                pass
            raise
    
    # =========================================
    # Image Generation
    # =========================================
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "vivid",
        quality: str = "standard",
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate image using DALL-E 3 through CometAPI.
        
        Args:
            prompt: Image description
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            style: Style (vivid, natural)
            quality: Quality (standard, hd)
            
        Returns:
            Tuple of (image_url, usage_info)
        """
        model = model or self.MODELS["image"]
        
        try:
            response = await self.client.images.generate(
                model=model,
                prompt=prompt,
                size=size,
                style=style,
                quality=quality,
                n=1
            )
            
            # Check if response contains data
            if not response or not response.data or len(response.data) == 0:
                raise Exception("No image data returned from API")
            
            image_data = response.data[0]
            image_url = image_data.url
            
            if not image_url:
                # Check for base64 data
                if hasattr(image_data, 'b64_json') and image_data.b64_json:
                    # Handle base64 response - will need to decode on download
                    image_url = f"data:image/png;base64,{image_data.b64_json}"
                else:
                    raise Exception("No image URL or base64 data returned")
            
            revised_prompt = getattr(image_data, 'revised_prompt', prompt) or prompt
            
            # Calculate cost
            cost = self.PRICING["dall-e-3"].get(size, 0.04)
            if quality == "hd":
                cost *= 2
            
            usage = {
                "model": model,
                "size": size,
                "style": style,
                "quality": quality,
                "revised_prompt": revised_prompt,
                "cost_usd": Decimal(str(cost)),
                "provider": "cometapi"
            }
            
            # Log API usage
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model,
                    endpoint="image",
                    cost_usd=usage["cost_usd"],
                    success=True
                )
            except Exception as log_error:
                logger.warning("Failed to log API usage", error=str(log_error))
            
            return image_url, usage
            
        except Exception as e:
            logger.error("CometAPI image generation error", error=str(e))
            # Log failed call
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model or self.MODELS["image"],
                    endpoint="image",
                    success=False,
                    error_message=str(e)
                )
            except Exception:
                pass
            raise
    
    async def download_image(self, url: str) -> bytes:
        """Download image from URL or decode base64 data."""
        # Check if it's base64 data URI
        if url.startswith("data:image"):
            # Extract base64 data after the comma
            try:
                base64_data = url.split(",", 1)[1]
                return base64.b64decode(base64_data)
            except Exception as e:
                raise Exception(f"Failed to decode base64 image: {str(e)}")
        
        # Regular URL download
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    return await response.read()
                raise Exception(f"Failed to download image: HTTP {response.status}")
    
    # =========================================
    # Video Generation (CometAPI Official Format)
    # =========================================
    
    async def create_video(
        self,
        prompt: str,
        model: str = "sora-2",
        duration: int = 4,
        size: str = "720x1280",
        input_reference: bytes = None
    ) -> Dict[str, Any]:
        """
        Create video generation task using CometAPI.
        
        Supported models:
        - sora-2: Fast mode (4/8/12 seconds)
        - sora-2-pro: High quality (4/8/12 seconds)
        
        Args:
            prompt: Video description
            model: sora-2 or sora-2-pro
            duration: Duration in seconds (4, 8, or 12)
            size: Resolution (720x1280, 1280x720, 1024x1792, 1792x1024)
            input_reference: Optional reference image bytes
            
        Returns:
            Video task info with video_id
        """
        # Ensure model is valid
        if model not in self.VIDEO_MODELS:
            model = "sora-2"
        
        # Validate duration for the selected model
        valid_durations = self.VIDEO_MODELS[model]["durations"]
        if duration not in valid_durations:
            # Map to nearest valid duration
            if duration <= 4:
                duration = 4
            elif duration <= 8:
                duration = 8
            else:
                duration = 12
        
        api_key = getattr(settings, 'cometapi_api_key', None) or settings.openai_api_key
        
        try:
            # Use multipart/form-data as per CometAPI docs
            form_data = aiohttp.FormData()
            form_data.add_field('prompt', prompt)
            form_data.add_field('model', model)
            form_data.add_field('seconds', str(duration))
            form_data.add_field('size', size)
            
            # Add reference image if provided
            if input_reference:
                form_data.add_field(
                    'input_reference',
                    input_reference,
                    filename='reference.png',
                    content_type='image/png'
                )
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/videos",
                    data=form_data,
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"CometAPI video creation failed: {response.status} - {error_text}")
                    
                    data = await response.json()
            
            result = {
                "video_id": data.get("id"),
                "status": data.get("status", "queued"),
                "model": model,
                "duration": duration,
                "size": size,
                "provider": "cometapi"
            }
            
            # Calculate cost (per second pricing)
            pricing = self.PRICING.get(model, self.PRICING["sora-2"])
            cost = duration * pricing.get("per_second", 0.05)
            
            # Log API usage
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model,
                    endpoint="video",
                    cost_usd=Decimal(str(round(cost, 4))),
                    success=True
                )
            except Exception as log_error:
                logger.warning("Failed to log API usage", error=str(log_error))
            
            logger.info("Video creation started", video_id=result["video_id"], model=model, duration=duration)
            return result
            
        except Exception as e:
            logger.error("CometAPI video creation error", error=str(e))
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model,
                    endpoint="video",
                    success=False,
                    error_message=str(e)
                )
            except Exception:
                pass
            raise
    
    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """Check video generation status via API."""
        api_key = getattr(settings, 'cometapi_api_key', None) or settings.openai_api_key
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/videos/{video_id}",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Failed to get video status: {response.status} - {error_text}")
                    
                    data = await response.json()
            
            error_message = None
            if data.get("error"):
                error_message = data["error"].get("message") if isinstance(data["error"], dict) else str(data["error"])
            
            return {
                "video_id": data.get("id"),
                "status": data.get("status"),
                "progress": data.get("progress", 0),
                "error_message": error_message,
                "output_url": data.get("video_url") or data.get("url") or data.get("result_url")
            }
            
        except Exception as e:
            logger.error("CometAPI video status error", error=str(e))
            raise
    
    async def download_video(self, video_id: str) -> bytes:
        """Download completed video by video_id."""
        api_key = getattr(settings, 'cometapi_api_key', None) or settings.openai_api_key
        
        try:
            # First get video status to find the output URL
            status = await self.get_video_status(video_id)
            
            if status.get("status") != "completed":
                raise Exception(f"Video not ready. Status: {status.get('status')}")
            
            output_url = status.get("output_url")
            
            if output_url:
                # Download from output URL
                async with aiohttp.ClientSession() as session:
                    async with session.get(
                        output_url,
                        timeout=aiohttp.ClientTimeout(total=300)
                    ) as response:
                        if response.status != 200:
                            raise Exception(f"Failed to download video: {response.status}")
                        return await response.read()
            
            # Fallback: try download endpoint
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self.BASE_URL}/videos/{video_id}/download",
                    headers={"Authorization": f"Bearer {api_key}"},
                    timeout=aiohttp.ClientTimeout(total=300)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"Failed to download video: {response.status}")
                    return await response.read()
                    
        except Exception as e:
            logger.error("CometAPI video download error", error=str(e))
            raise
    
    async def wait_for_video(
        self,
        video_id: str,
        poll_interval: int = 10,
        timeout: int = 600,
        progress_callback=None
    ) -> Dict[str, Any]:
        """Wait for video generation to complete."""
        elapsed = 0
        
        while elapsed < timeout:
            status = await self.get_video_status(video_id)
            
            if progress_callback:
                await progress_callback(status)
            
            if status["status"] == "completed":
                return status
            elif status["status"] == "failed":
                raise Exception(
                    f"Video generation failed: {status.get('error_message', 'Unknown error')}"
                )
            
            await asyncio.sleep(poll_interval)
            elapsed += poll_interval
        
        raise Exception("Video generation timed out")
    
    # =========================================
    # Speech Recognition (Whisper)
    # =========================================
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.ogg",
        language: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe audio to text using Whisper.
        
        Args:
            audio_data: Audio file bytes
            filename: Original filename for format detection
            language: Optional language hint
            
        Returns:
            Tuple of (transcribed_text, usage_info)
        """
        try:
            # Create file-like object
            audio_file = io.BytesIO(audio_data)
            audio_file.name = filename
            
            kwargs = {
                "model": self.MODELS["whisper"],
                "file": audio_file,
            }
            if language:
                kwargs["language"] = language
            
            response = await self.client.audio.transcriptions.create(**kwargs)
            
            text = response.text
            
            # Estimate duration for cost calculation
            duration_minutes = len(audio_data) / (10 * 60 * 1000)
            cost = duration_minutes * self.PRICING["whisper-1"]
            
            usage = {
                "model": self.MODELS["whisper"],
                "duration_minutes": round(duration_minutes, 2),
                "cost_usd": Decimal(str(round(cost, 6))),
                "provider": "cometapi"
            }
            
            # Log API usage
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=self.MODELS["whisper"],
                    endpoint="audio",
                    cost_usd=usage["cost_usd"],
                    success=True
                )
            except Exception as log_error:
                logger.warning("Failed to log API usage", error=str(log_error))
            
            return text, usage
            
        except Exception as e:
            logger.error("CometAPI transcription error", error=str(e))
            # Log failed call
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=self.MODELS["whisper"],
                    endpoint="audio",
                    success=False,
                    error_message=str(e)
                )
            except Exception:
                pass
            raise
    
    # =========================================
    # Image Editing (GPT-Image-1 via chat.completions)
    # =========================================
    
    async def edit_image(
        self,
        image_data: bytes,
        prompt: str,
        model: str = "gpt-image-1",
        size: str = "auto",
        quality: str = "auto"
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Edit an image using GPT-Image-1 via CometAPI chat.completions.
        
        Sends the image + text instruction, gets back an edited image.
        
        Args:
            image_data: Original image bytes
            prompt: Edit instruction (e.g. "Add a dent to the car on the logo")
            model: Model to use (gpt-image-1, gpt-image-1.5)
            size: Output size (auto, 1024x1024, 1536x1024, 1024x1536)
            quality: Quality (auto, low, medium, high)
            
        Returns:
            Tuple of (edited_image_bytes, usage_info)
        """
        try:
            base64_image = base64.b64encode(image_data).decode('utf-8')
            
            # Use the images.edit endpoint (OpenAI-compatible)
            # CometAPI proxies this as OpenAI-compatible API
            import io as _io
            image_file = _io.BytesIO(image_data)
            image_file.name = "input.png"
            
            response = await self.client.images.edit(
                model=model,
                image=image_file,
                prompt=prompt,
                size=size,
                quality=quality,
                n=1
            )
            
            if not response or not response.data:
                raise Exception("No image data returned from edit API")
            
            result_data = response.data[0]
            
            # GPT-image models return base64 by default
            if hasattr(result_data, 'b64_json') and result_data.b64_json:
                edited_bytes = base64.b64decode(result_data.b64_json)
            elif hasattr(result_data, 'url') and result_data.url:
                edited_bytes = await self.download_image(result_data.url)
            else:
                raise Exception("No image URL or base64 data in edit response")
            
            # Cost estimate for gpt-image-1
            cost = 0.02  # Rough estimate per edit
            
            usage = {
                "model": model,
                "size": size,
                "quality": quality,
                "cost_usd": Decimal(str(cost)),
                "provider": "cometapi"
            }
            
            # If response has usage info, use it
            if hasattr(response, 'usage') and response.usage:
                u = response.usage
                input_tokens = getattr(u, 'input_tokens', 0) or getattr(u, 'prompt_tokens', 0) or 0
                output_tokens = getattr(u, 'output_tokens', 0) or getattr(u, 'completion_tokens', 0) or 0
                usage["input_tokens"] = input_tokens
                usage["output_tokens"] = output_tokens
                # Recalculate cost from tokens if available
                if input_tokens or output_tokens:
                    cost = (input_tokens / 1_000_000) * 8.0 + (output_tokens / 1_000_000) * 32.0
                    usage["cost_usd"] = Decimal(str(round(cost, 6)))
            
            # Log API usage
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model,
                    endpoint="image_edit",
                    cost_usd=usage["cost_usd"],
                    success=True
                )
            except Exception as log_error:
                logger.warning("Failed to log API usage", error=str(log_error))
            
            logger.info(
                "Image edit completed",
                model=model,
                result_size=len(edited_bytes)
            )
            
            return edited_bytes, usage
            
        except Exception as e:
            logger.error("CometAPI image edit error", error=str(e), model=model)
            # Log failed call
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model,
                    endpoint="image_edit",
                    success=False,
                    error_message=str(e)
                )
            except Exception:
                pass
            raise
    
    # =========================================
    # Vision (Image Analysis)
    # =========================================
    
    async def analyze_image(
        self,
        image_url: str = None,
        image_data: bytes = None,
        prompt: str = "Describe this image in detail.",
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze image using vision model.
        """
        model = model or self.MODELS["text"]
        
        try:
            content = [{"type": "text", "text": prompt}]
            
            if image_url:
                content.append({
                    "type": "image_url",
                    "image_url": {"url": image_url}
                })
            elif image_data:
                base64_image = base64.b64encode(image_data).decode('utf-8')
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}"
                    }
                })
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                max_tokens=4096
            )
            
            text = response.choices[0].message.content
            
            # Get pricing for the actual model used
            pricing = self.PRICING.get(model, {"input": 0.002, "output": 0.008})
            cost = (
                (response.usage.prompt_tokens / 1000) * pricing["input"] +
                (response.usage.completion_tokens / 1000) * pricing["output"]
            )
            
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "model": model,
                "provider": "cometapi",
                "cost_usd": Decimal(str(round(cost, 6)))
            }
            
            return text, usage
            
        except Exception as e:
            logger.error("CometAPI vision analysis error", error=str(e), model=model)
            raise    
    async def analyze_document_images(
        self,
        images: List[bytes],
        prompt: str,
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """Analyze multiple document page images."""
        model = model or self.MODELS["text"]
        
        try:
            content = [{"type": "text", "text": prompt}]
            
            for image_data in images:
                base64_image = base64.b64encode(image_data).decode('utf-8')
                content.append({
                    "type": "image_url",
                    "image_url": {
                        "url": f"data:image/jpeg;base64,{base64_image}",
                        "detail": "high"
                    }
                })
            
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                max_tokens=4096
            )
            
            text = response.choices[0].message.content
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "model": model,
                "images_count": len(images),
                "provider": "cometapi",
                "cost_usd": Decimal(str(round(
                    (response.usage.prompt_tokens / 1000) * 0.002 +
                    (response.usage.completion_tokens / 1000) * 0.008,
                    6
                )))
            }
            
            return text, usage
            
        except Exception as e:
            logger.error("CometAPI document analysis error", error=str(e))
            raise
    
    # =========================================
    # Text Generation with Web Search (Responses API)
    # =========================================
    
    async def generate_text_with_search(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        enable_search: bool = True,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate text using Responses API with optional web search.
        
        Uses /v1/responses endpoint which supports built-in tools
        like web_search. The model automatically decides when to search.
        
        Args:
            messages: Conversation messages (system + user + assistant)
            model: Model name (default: qwen3-max-2026-01-23)
            max_tokens: Max output tokens
            temperature: Creativity
            enable_search: Whether to enable web_search tool
            
        Returns:
            Tuple of (response_text, usage_info)
        """
        model = model or "qwen3-max-2026-01-23"
        api_key = getattr(settings, 'cometapi_api_key', None) or settings.openai_api_key
        
        try:
            # Build the input for Responses API
            # Convert chat messages format to Responses API format
            input_items = []
            for msg in messages:
                role = msg["role"]
                content = msg["content"]
                if role == "system":
                    # System messages become instructions in Responses API
                    continue
                input_items.append({
                    "role": role,
                    "content": content
                })
            
            # Extract system message as instructions
            instructions = None
            for msg in messages:
                if msg["role"] == "system":
                    instructions = msg["content"]
                    break
            
            # Build request body
            body = {
                "model": model,
                "input": input_items,
                "temperature": temperature,
            }
            
            if instructions:
                body["instructions"] = instructions
            
            if max_tokens:
                body["max_output_tokens"] = max_tokens
            
            if enable_search:
                body["tools"] = [{"type": "web_search"}]
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.BASE_URL}/responses",
                    json=body,
                    headers={
                        "Authorization": f"Bearer {api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.warning(
                            "Responses API failed, falling back to chat completions",
                            status=response.status,
                            error=error_text[:200]
                        )
                        # Fall back to regular chat completions (no search)
                        return await self.generate_text(
                            messages=messages,
                            model=model,
                            max_tokens=max_tokens,
                            temperature=temperature
                        )
                    
                    data = await response.json()
            
            # Extract text from response
            output_text = ""
            sources = []
            
            # Responses API returns output array
            output = data.get("output", [])
            if isinstance(output, list):
                for item in output:
                    if isinstance(item, dict):
                        item_type = item.get("type", "")
                        if item_type == "message":
                            # Extract text from message content
                            content_list = item.get("content", [])
                            for c in content_list:
                                if isinstance(c, dict) and c.get("type") == "output_text":
                                    output_text += c.get("text", "")
                                    # Extract source annotations
                                    annotations = c.get("annotations", [])
                                    for ann in annotations:
                                        if isinstance(ann, dict) and ann.get("type") == "url_citation":
                                            sources.append({
                                                "url": ann.get("url", ""),
                                                "title": ann.get("title", "")
                                            })
                        elif item_type == "web_search_call":
                            logger.info("Web search was invoked by model")
            elif isinstance(output, str):
                output_text = output
            
            # Fallback: check output_text field directly
            if not output_text:
                output_text = data.get("output_text", "")
            
            if not output_text:
                # Last resort: try to get from choices (chat completions format)
                choices = data.get("choices", [])
                if choices and isinstance(choices[0], dict):
                    msg = choices[0].get("message", {})
                    output_text = msg.get("content", "")
            
            if not output_text:
                raise Exception("No text in Responses API output")
            
            # Parse usage
            usage_data = data.get("usage", {})
            input_tokens = usage_data.get("input_tokens", 0) or usage_data.get("prompt_tokens", 0) or 0
            output_tokens = usage_data.get("output_tokens", 0) or usage_data.get("completion_tokens", 0) or 0
            
            # Calculate cost
            pricing = self.PRICING.get(model, self.PRICING["qwen-3-max"])
            cost = (
                (input_tokens / 1000) * pricing.get("input", 0.002) +
                (output_tokens / 1000) * pricing.get("output", 0.008)
            )
            
            usage = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "total_tokens": input_tokens + output_tokens,
                "model": model,
                "provider": "cometapi",
                "cost_usd": Decimal(str(round(cost, 6))),
                "web_search_used": bool(sources),
                "sources": sources[:5] if sources else [],
            }
            
            # Log API usage
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model,
                    endpoint="responses",
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=usage["cost_usd"],
                    success=True
                )
            except Exception as log_error:
                logger.warning("Failed to log API usage", error=str(log_error))
            
            return output_text, usage
            
        except Exception as e:
            if "falling back" not in str(e).lower():
                logger.error("CometAPI Responses API error", error=str(e), model=model)
            # Log failed call
            try:
                await usage_tracking_service.log_api_call(
                    provider="cometapi",
                    model=model,
                    endpoint="responses",
                    success=False,
                    error_message=str(e)
                )
            except Exception:
                pass
            raise

    # =========================================
    # Meeting Protocol Generation
    # =========================================
    
    async def generate_meeting_protocol(
        self,
        transcription: str,
        language: str = "ru"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate meeting protocol from transcription.
        
        Args:
            transcription: Transcribed audio text
            language: Output language
            
        Returns:
            Tuple of (protocol_text, usage_info)
        """
        if language == "ru":
            system_prompt = """Ты — профессиональный секретарь, который создаёт протоколы совещаний.
На основе транскрипции создай структурированный протокол совещания в следующем формате:

# ПРОТОКОЛ СОВЕЩАНИЯ

**Дата:** [если указана в тексте]
**Участники:** [если упомянуты]

## Повестка дня
[Основные темы обсуждения]

## Обсуждение
[Краткое изложение ключевых моментов обсуждения]

## Решения и поручения
[Список принятых решений с ответственными лицами, если указаны]

## Итоги
[Краткие выводы]

Если какая-то информация отсутствует в транскрипции, не придумывай её, а укажи [не указано]."""
        else:
            system_prompt = """You are a professional secretary who creates meeting protocols.
Based on the transcription, create a structured meeting protocol in the following format:

# MEETING PROTOCOL

**Date:** [if mentioned in text]
**Participants:** [if mentioned]

## Agenda
[Main discussion topics]

## Discussion
[Brief summary of key discussion points]

## Decisions and Action Items
[List of decisions with responsible persons if indicated]

## Summary
[Brief conclusions]

If any information is missing from the transcription, don't make it up, indicate [not specified]."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Создай протокол на основе этой транскрипции:\n\n{transcription}"}
        ]
        
        return await self.generate_text(messages, max_tokens=4096, temperature=0.3)


# Global service instance
cometapi_service = CometAPIService()
