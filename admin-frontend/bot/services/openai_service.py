"""
OpenAI API integration service.
Handles all interactions with OpenAI APIs: GPT, DALL-E, Whisper, Sora.
"""
import asyncio
import io
from typing import Optional, AsyncGenerator, Dict, Any, List, Tuple
from decimal import Decimal
import aiohttp
from openai import AsyncOpenAI

from config import settings
import structlog

logger = structlog.get_logger()


class OpenAIService:
    """
    Service for interacting with OpenAI APIs.
    """
    
    # Pricing per 1K tokens (as of 2024)
    PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
        "dall-e-3": {
            "1024x1024": 0.04,
            "1792x1024": 0.08,
            "1024x1792": 0.08
        },
        "whisper-1": 0.006,  # per minute
        "sora-2": {"per_second": 0.05},  # estimated
        "sora-2-pro": {"per_second": 0.10}  # estimated
    }
    
    def __init__(self):
        self.client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            timeout=settings.openai_timeout
        )
    
    # =========================================
    # Text Generation (GPT)
    # =========================================
    
    async def generate_text_stream(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> AsyncGenerator[Tuple[str, bool], None]:
        """
        Generate text with streaming response.
        
        Yields tuples of (text_chunk, is_complete).
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            model: GPT model to use
            max_tokens: Maximum tokens to generate
            temperature: Creativity parameter (0-2)
            
        Yields:
            Tuple of (chunk_text, is_complete_flag)
        """
        model = model or settings.default_gpt_model
        
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
            logger.error("GPT streaming error", error=str(e))
            raise
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: str = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate text without streaming.
        
        Returns:
            Tuple of (response_text, usage_info)
        """
        model = model or settings.default_gpt_model
        
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
                "model": model
            }
            
            # Calculate cost
            pricing = self.PRICING.get(model, self.PRICING["gpt-4o-mini"])
            cost = (
                (usage["input_tokens"] / 1000) * pricing["input"] +
                (usage["output_tokens"] / 1000) * pricing["output"]
            )
            usage["cost_usd"] = Decimal(str(round(cost, 6)))
            
            return content, usage
            
        except Exception as e:
            logger.error("GPT generation error", error=str(e))
            raise
    
    # =========================================
    # Image Generation (DALL-E 3)
    # =========================================
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024x1024",
        style: str = "vivid",
        quality: str = "standard"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate image with DALL-E 3.
        
        Args:
            prompt: Image description
            size: Image size (1024x1024, 1792x1024, 1024x1792)
            style: Style (vivid, natural)
            quality: Quality (standard, hd)
            
        Returns:
            Tuple of (image_url, usage_info)
        """
        try:
            response = await self.client.images.generate(
                model="dall-e-3",
                prompt=prompt,
                size=size,
                style=style,
                quality=quality,
                n=1
            )
            
            image_url = response.data[0].url
            revised_prompt = response.data[0].revised_prompt
            
            # Calculate cost
            cost = self.PRICING["dall-e-3"].get(size, 0.04)
            if quality == "hd":
                cost *= 2
            
            usage = {
                "model": "dall-e-3",
                "size": size,
                "style": style,
                "quality": quality,
                "revised_prompt": revised_prompt,
                "cost_usd": Decimal(str(cost))
            }
            
            return image_url, usage
            
        except Exception as e:
            logger.error("DALL-E generation error", error=str(e))
            raise
    
    async def download_image(self, url: str) -> bytes:
        """Download image from URL."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    return await response.read()
                raise Exception(f"Failed to download image: {response.status}")
    
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
            
            response = await self.client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language
            )
            
            text = response.text
            
            # Estimate duration for cost calculation (rough estimate)
            # Assuming ~10 bytes per ms for OGG
            duration_minutes = len(audio_data) / (10 * 60 * 1000)
            cost = duration_minutes * self.PRICING["whisper-1"]
            
            usage = {
                "model": "whisper-1",
                "duration_minutes": round(duration_minutes, 2),
                "cost_usd": Decimal(str(round(cost, 6)))
            }
            
            return text, usage
            
        except Exception as e:
            logger.error("Whisper transcription error", error=str(e))
            raise
    
    # =========================================
    # Video Generation (Sora)
    # =========================================
        
    async def create_video(
        self,
        prompt: str,
        model: str = "sora-2",
        duration: int = 4,
        size: str = "1280x720"
    ) -> Dict[str, Any]:
        """
        Create video generation task with Sora.
        
        Args:
            prompt: Video description
            model: sora-2 or sora-2-pro
            duration: Duration in seconds (4, 8, or 12)
            size: Resolution (720x1280, 1280x720, 1024x1792, 1792x1024)
            
        Returns:
            Video task info with video_id
        """
        try:
            # Map duration to valid Sora values (must be string: '4', '8', or '12')
            duration_map = {
                4: "4",
                5: "4",   # Round down to 4
                8: "8",
                10: "8",  # Round down to 8
                12: "12",
            }
            sora_seconds = duration_map.get(duration, "4")
            
            # ИСПРАВЛЕНО: параметр называется 'seconds' (строка), не 'duration'
            video = await self.client.videos.create(
                model=model,
                prompt=prompt,
                size=size,
                seconds=sora_seconds
            )
            
            return {
                "video_id": video.id,
                "status": video.status,
                "model": model,
                "duration": int(sora_seconds),
                "size": size
            }
            
        except Exception as e:
            logger.error("Sora video creation error", error=str(e))
            raise

    
    async def get_video_status(self, video_id: str) -> Dict[str, Any]:
        """
        Check video generation status.
        
        Returns:
            Video info with status and progress
        """
        try:
            video = await self.client.videos.retrieve(video_id)
            
            # Извлекаем сообщение об ошибке из объекта error
            error_message = None
            if hasattr(video, 'error') and video.error:
                if isinstance(video.error, dict):
                    error_message = video.error.get('message')
                elif hasattr(video.error, 'message'):
                    error_message = video.error.message
            
            return {
                "video_id": video.id,
                "status": video.status,
                "progress": getattr(video, 'progress', 0),
                "error_message": error_message
            }
            
        except Exception as e:
            logger.error("Sora status check error", error=str(e))
            raise
    
    async def download_video(self, video_id: str) -> bytes:
        """
        Download completed video.
        
        Returns:
            Video file bytes
        """
        try:
            response = await self.client.videos.download_content(video_id)
            video_bytes = await response.read()
            return video_bytes
            
        except Exception as e:
            logger.error("Sora video download error", error=str(e))
            raise
    
    async def wait_for_video(
        self,
        video_id: str,
        poll_interval: int = 10,
        timeout: int = 600,
        progress_callback=None
    ) -> Dict[str, Any]:
        """
        Wait for video generation to complete.
        
        Args:
            video_id: Video task ID
            poll_interval: Seconds between status checks
            timeout: Maximum wait time in seconds
            progress_callback: Async callback for progress updates
            
        Returns:
            Final video info
        """
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
    
    async def create_video_with_reference(
        self,
        prompt: str,
        image_data: bytes,
        model: str = "sora-2",
        duration: int = 4
    ) -> Dict[str, Any]:
        """
        Create video with reference image as first frame.
        
        Args:
            prompt: Video description
            image_data: Reference image bytes
            model: Sora model
            duration: Duration in seconds (4, 8, or 12)
            
        Returns:
            Video task info
        """
        try:
            duration_map = {4: "4", 5: "4", 8: "8", 10: "8", 12: "12"}
            sora_seconds = duration_map.get(duration, "4")
            
            image_file = io.BytesIO(image_data)
            image_file.name = "reference.jpg"
            
            video = await self.client.videos.create(
                model=model,
                prompt=prompt,
                size="1280x720",
                seconds=sora_seconds,
                input_reference=image_file
            )
            
            return {
                "video_id": video.id,
                "status": video.status,
                "model": model,
                "duration": int(sora_seconds)
            }
            
        except Exception as e:
            logger.error("Sora video with reference error", error=str(e))
            raise
    
    async def remix_video(
        self,
        video_id: str,
        change_prompt: str
    ) -> Dict[str, Any]:
        """
        Remix existing video with changes.
        
        Args:
            video_id: Original video ID
            change_prompt: Description of changes
            
        Returns:
            New video task info
        """
        try:
            # ИСПРАВЛЕНО: video_id передаётся первым позиционным аргументом
            remixed = await self.client.videos.remix(
                video_id,
                prompt=change_prompt
            )
            
            return {
                "video_id": remixed.id,
                "status": remixed.status,
                "original_video_id": video_id
            }
            
        except Exception as e:
            logger.error("Sora video remix error", error=str(e))
            raise
    
    # =========================================
    # Vision (GPT-4o Vision)
    # =========================================
    
    async def analyze_image(
        self,
        image_url: str = None,
        image_data: bytes = None,
        prompt: str = "Describe this image in detail.",
        model: str = "gpt-4o"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze image with GPT-4o Vision.
        
        Args:
            image_url: URL of image to analyze
            image_data: Or raw image bytes
            prompt: Analysis prompt
            model: Model to use
            
        Returns:
            Tuple of (analysis_text, usage_info)
        """
        import base64
        
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
            usage = {
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
                "model": model,
                "cost_usd": Decimal(str(round(
                    (response.usage.prompt_tokens / 1000) * 0.005 +
                    (response.usage.completion_tokens / 1000) * 0.015,
                    6
                )))
            }
            
            return text, usage
            
        except Exception as e:
            logger.error("Vision analysis error", error=str(e))
            raise
    
    async def analyze_document_images(
        self,
        images: List[bytes],
        prompt: str,
        model: str = "gpt-4o"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze multiple document page images.
        
        Args:
            images: List of page images as bytes
            prompt: Analysis prompt
            model: Model to use
            
        Returns:
            Tuple of (analysis_text, usage_info)
        """
        import base64
        
        try:
            content = [{"type": "text", "text": prompt}]
            
            for i, image_data in enumerate(images):
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
                "cost_usd": Decimal(str(round(
                    (response.usage.prompt_tokens / 1000) * 0.005 +
                    (response.usage.completion_tokens / 1000) * 0.015,
                    6
                )))
            }
            
            return text, usage
            
        except Exception as e:
            logger.error("Document vision analysis error", error=str(e))
            raise


# Global service instance
openai_service = OpenAIService()
