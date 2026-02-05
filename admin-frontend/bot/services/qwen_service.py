"""
Qwen (Alibaba Cloud) API integration service.
Handles all interactions with Qwen APIs via DashScope.
Supports: Text, Vision, Image Generation, ASR, TTS.
"""
import asyncio
import io
import base64
from typing import Optional, AsyncGenerator, Dict, Any, List, Tuple
from decimal import Decimal
import aiohttp
import json

import structlog

logger = structlog.get_logger()


def get_qwen_api_key() -> Optional[str]:
    """Get Qwen API key from environment (re-reads .env each time)."""
    import os
    from dotenv import load_dotenv
    
    # Reload .env to get latest values
    load_dotenv(override=True)
    return os.getenv("QWEN_API_KEY", "")


class QwenService:
    """
    Service for interacting with Qwen APIs via DashScope.
    Supports text generation, vision, image generation, ASR, and TTS.
    """
    
    # DashScope API base URL
    BASE_URL = "https://dashscope.aliyuncs.com/api/v1"
    
    # Available models by category
    MODELS = {
        "text": [
            "qwen-turbo",
            "qwen-plus", 
            "qwen-max",
            "qwen-max-longcontext",
            "qwen3-235b-a22b",
        ],
        "vision": [
            "qwen-vl-plus",
            "qwen-vl-max",
            "qwen2.5-vl-72b-instruct",
        ],
        "image": [
            "wanx-v1",
            "wanx2.1-t2i-turbo",
            "wanx2.1-t2i-plus",
        ],
        "asr": [
            "paraformer-realtime-v2",
            "paraformer-v2",
        ],
        "tts": [
            "cosyvoice-v1",
            "sambert-zhichu-v1",
        ],
    }
    
    # Pricing per 1K tokens / per item (approximate, may vary)
    PRICING = {
        # Text models
        "qwen-turbo": {"input": 0.0003, "output": 0.0006},
        "qwen-plus": {"input": 0.0008, "output": 0.002},
        "qwen-max": {"input": 0.004, "output": 0.012},
        "qwen-max-longcontext": {"input": 0.004, "output": 0.012},
        # Vision models
        "qwen-vl-plus": {"input": 0.002, "output": 0.002},
        "qwen-vl-max": {"input": 0.005, "output": 0.005},
        # Image generation
        "wanx-v1": {"per_image": 0.02},
        "wanx2.1-t2i-turbo": {"per_image": 0.008},
        "wanx2.1-t2i-plus": {"per_image": 0.025},
        # ASR (per minute)
        "paraformer-realtime-v2": {"per_minute": 0.01},
        # TTS (per 1K characters)
        "cosyvoice-v1": {"per_1k_chars": 0.02},
    }
    
    def __init__(self, api_key: str = None):
        """Initialize with optional API key override."""
        self._api_key_override = api_key
    
    @property
    def api_key(self) -> Optional[str]:
        """Get API key - supports dynamic updates from .env."""
        if self._api_key_override:
            return self._api_key_override
        return get_qwen_api_key()
    
    def is_configured(self) -> bool:
        """Check if service is properly configured with valid API key."""
        key = self.api_key
        return bool(key and len(key) > 10)
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers."""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
    
    def _get_stream_headers(self) -> Dict[str, str]:
        """Get request headers for streaming."""
        headers = self._get_headers()
        headers["X-DashScope-SSE"] = "enable"
        return headers
    
    def _get_async_headers(self) -> Dict[str, str]:
        """Get headers for async task submission."""
        headers = self._get_headers()
        headers["X-DashScope-Async"] = "enable"
        return headers
    
    # =========================================
    # Text Generation (Qwen)
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
        """
        if not self.is_configured():
            raise ValueError("Qwen API key not configured")
        
        from config import settings
        model = model or settings.default_qwen_model
        
        url = f"{self.BASE_URL}/services/aigc/text-generation/generation"
        
        payload = {
            "model": model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "result_format": "message",
                "incremental_output": True
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_stream_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Qwen API error", status=response.status, error=error_text)
                        raise Exception(f"Qwen API error: {response.status} - {error_text}")
                    
                    async for line in response.content:
                        line = line.decode('utf-8').strip()
                        
                        if not line:
                            continue
                        
                        if line.startswith("data:"):
                            line = line[5:].strip()
                        
                        if line == "[DONE]":
                            yield "", True
                            break
                        
                        try:
                            data = json.loads(line)
                            
                            if "output" in data:
                                output = data["output"]
                                
                                if "code" in output and output["code"] != "":
                                    raise Exception(f"Qwen error: {output.get('message', 'Unknown error')}")
                                
                                if "choices" in output:
                                    for choice in output["choices"]:
                                        if "message" in choice and "content" in choice["message"]:
                                            content = choice["message"]["content"]
                                            if content:
                                                finish_reason = choice.get("finish_reason")
                                                is_complete = finish_reason is not None and finish_reason != ""
                                                yield content, is_complete
                                elif "text" in output:
                                    text = output["text"]
                                    if text:
                                        yield text, False
                                        
                        except json.JSONDecodeError:
                            continue
                            
        except Exception as e:
            logger.error("Qwen streaming error", error=str(e))
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
        if not self.is_configured():
            raise ValueError("Qwen API key not configured")
        
        from config import settings
        model = model or settings.default_qwen_model
        
        url = f"{self.BASE_URL}/services/aigc/text-generation/generation"
        
        payload = {
            "model": model,
            "input": {
                "messages": messages
            },
            "parameters": {
                "max_tokens": max_tokens,
                "temperature": temperature,
                "result_format": "message"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Qwen API error", status=response.status, error=error_text)
                        raise Exception(f"Qwen API error: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    if "output" not in data:
                        raise Exception("Invalid response from Qwen API")
                    
                    output = data["output"]
                    
                    if "code" in output and output["code"]:
                        raise Exception(f"Qwen error: {output.get('message', 'Unknown error')}")
                    
                    content = ""
                    if "choices" in output:
                        content = output["choices"][0]["message"]["content"]
                    elif "text" in output:
                        content = output["text"]
                    
                    usage_data = data.get("usage", {})
                    input_tokens = usage_data.get("input_tokens", 0)
                    output_tokens = usage_data.get("output_tokens", 0)
                    
                    pricing = self.PRICING.get(model, self.PRICING["qwen-plus"])
                    cost = (
                        (input_tokens / 1000) * pricing.get("input", 0.001) +
                        (output_tokens / 1000) * pricing.get("output", 0.002)
                    )
                    
                    usage = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "total_tokens": input_tokens + output_tokens,
                        "model": model,
                        "cost_usd": Decimal(str(round(cost, 6)))
                    }
                    
                    return content, usage
                    
        except Exception as e:
            logger.error("Qwen generation error", error=str(e))
            raise
    
    # =========================================
    # Vision (Qwen-VL)
    # =========================================
    
    async def analyze_image(
        self,
        image_url: str = None,
        image_data: bytes = None,
        prompt: str = "Describe this image in detail.",
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze image with Qwen-VL.
        
        Args:
            image_url: URL of image to analyze
            image_data: Or raw image bytes
            prompt: Analysis prompt
            model: Model to use
            
        Returns:
            Tuple of (analysis_text, usage_info)
        """
        if not self.is_configured():
            raise ValueError("Qwen API key not configured")
        
        from config import settings
        model = model or settings.default_qwen_vl_model
        
        url = f"{self.BASE_URL}/services/aigc/multimodal-generation/generation"
        
        content = []
        
        if image_url:
            content.append({"image": image_url})
        elif image_data:
            base64_image = base64.b64encode(image_data).decode('utf-8')
            content.append({"image": f"data:image/jpeg;base64,{base64_image}"})
        
        content.append({"text": prompt})
        
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            },
            "parameters": {
                "max_tokens": 4096
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Qwen VL API error", status=response.status, error=error_text)
                        raise Exception(f"Qwen VL API error: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    if "output" not in data:
                        raise Exception("Invalid response from Qwen VL API")
                    
                    output = data["output"]
                    
                    content_text = ""
                    if "choices" in output:
                        choice = output["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            msg_content = choice["message"]["content"]
                            if isinstance(msg_content, list):
                                for item in msg_content:
                                    if isinstance(item, dict) and "text" in item:
                                        content_text += item["text"]
                                    elif isinstance(item, str):
                                        content_text += item
                            else:
                                content_text = str(msg_content)
                    
                    usage_data = data.get("usage", {})
                    input_tokens = usage_data.get("input_tokens", 0)
                    output_tokens = usage_data.get("output_tokens", 0)
                    
                    pricing = self.PRICING.get(model, self.PRICING["qwen-vl-plus"])
                    cost = (
                        (input_tokens / 1000) * pricing.get("input", 0.002) +
                        (output_tokens / 1000) * pricing.get("output", 0.002)
                    )
                    
                    usage = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "model": model,
                        "cost_usd": Decimal(str(round(cost, 6)))
                    }
                    
                    return content_text, usage
                    
        except Exception as e:
            logger.error("Qwen VL analysis error", error=str(e))
            raise
    
    async def analyze_document_images(
        self,
        images: List[bytes],
        prompt: str,
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Analyze multiple document page images.
        """
        if not self.is_configured():
            raise ValueError("Qwen API key not configured")
        
        from config import settings
        model = model or settings.default_qwen_vl_model
        
        url = f"{self.BASE_URL}/services/aigc/multimodal-generation/generation"
        
        content = []
        
        for i, image_data in enumerate(images):
            base64_image = base64.b64encode(image_data).decode('utf-8')
            content.append({"image": f"data:image/jpeg;base64,{base64_image}"})
        
        content.append({"text": prompt})
        
        payload = {
            "model": model,
            "input": {
                "messages": [
                    {
                        "role": "user",
                        "content": content
                    }
                ]
            },
            "parameters": {
                "max_tokens": 4096
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Qwen VL API error: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    if "output" not in data:
                        raise Exception("Invalid response from Qwen VL API")
                    
                    output = data["output"]
                    
                    content_text = ""
                    if "choices" in output:
                        choice = output["choices"][0]
                        if "message" in choice and "content" in choice["message"]:
                            msg_content = choice["message"]["content"]
                            if isinstance(msg_content, list):
                                for item in msg_content:
                                    if isinstance(item, dict) and "text" in item:
                                        content_text += item["text"]
                            else:
                                content_text = str(msg_content)
                    
                    usage_data = data.get("usage", {})
                    input_tokens = usage_data.get("input_tokens", 0)
                    output_tokens = usage_data.get("output_tokens", 0)
                    
                    pricing = self.PRICING.get(model, self.PRICING["qwen-vl-plus"])
                    cost = (
                        (input_tokens / 1000) * pricing.get("input", 0.002) +
                        (output_tokens / 1000) * pricing.get("output", 0.002)
                    )
                    
                    usage = {
                        "input_tokens": input_tokens,
                        "output_tokens": output_tokens,
                        "model": model,
                        "images_count": len(images),
                        "cost_usd": Decimal(str(round(cost, 6)))
                    }
                    
                    return content_text, usage
                    
        except Exception as e:
            logger.error("Qwen VL document analysis error", error=str(e))
            raise
    
    # =========================================
    # Image Generation (Wanx / Tongyi Wanxiang)
    # =========================================
    
    async def generate_image(
        self,
        prompt: str,
        size: str = "1024*1024",
        model: str = None,
        n: int = 1,
        style: str = None,
        negative_prompt: str = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate image with Wanx (Tongyi Wanxiang).
        
        Args:
            prompt: Image description
            size: Image size (1024*1024, 720*1280, 1280*720)
            model: Model to use (wanx-v1, wanx2.1-t2i-turbo, wanx2.1-t2i-plus)
            n: Number of images to generate (1-4)
            style: Optional style preset ("<auto>", "<3d cartoon>", "<anime>", "<oil painting>", "<watercolor>", "<sketch>", "<chinese painting>", "<flat illustration>")
            negative_prompt: Things to avoid in the image
            
        Returns:
            Tuple of (image_url, usage_info)
        """
        if not self.is_configured():
            raise ValueError("Qwen API key not configured")
        
        from config import settings
        model = model or settings.default_qwen_image_model
        
        url = f"{self.BASE_URL}/services/aigc/text2image/image-synthesis"
        
        # Convert size format if needed (1024x1024 -> 1024*1024)
        size = size.replace("x", "*")
        
        payload = {
            "model": model,
            "input": {
                "prompt": prompt,
            },
            "parameters": {
                "size": size,
                "n": min(n, 4),  # Max 4 images
            }
        }
        
        if style:
            payload["parameters"]["style"] = style
        
        if negative_prompt:
            payload["input"]["negative_prompt"] = negative_prompt
        
        try:
            async with aiohttp.ClientSession() as session:
                # Submit task (async by default for image generation)
                async with session.post(
                    url,
                    headers=self._get_async_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=30)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Qwen Image API error", status=response.status, error=error_text)
                        raise Exception(f"Qwen Image API error: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    # Get task ID for async polling
                    task_id = data.get("output", {}).get("task_id")
                    
                    if not task_id:
                        # Maybe sync response?
                        results = data.get("output", {}).get("results", [])
                        if results:
                            image_url = results[0].get("url")
                            if image_url:
                                pricing = self.PRICING.get(model, self.PRICING["wanx-v1"])
                                cost = pricing.get("per_image", 0.02) * n
                                
                                usage = {
                                    "model": model,
                                    "size": size,
                                    "n": n,
                                    "cost_usd": Decimal(str(round(cost, 6)))
                                }
                                return image_url, usage
                        
                        raise Exception(f"No task_id in response: {data}")
                    
                    # Poll for result
                    image_url = await self._wait_for_image_task(session, task_id)
                    
                    pricing = self.PRICING.get(model, self.PRICING["wanx-v1"])
                    cost = pricing.get("per_image", 0.02) * n
                    
                    usage = {
                        "model": model,
                        "size": size,
                        "n": n,
                        "task_id": task_id,
                        "cost_usd": Decimal(str(round(cost, 6)))
                    }
                    
                    return image_url, usage
                    
        except Exception as e:
            logger.error("Qwen image generation error", error=str(e))
            raise
    
    async def _wait_for_image_task(
        self, 
        session: aiohttp.ClientSession, 
        task_id: str,
        max_attempts: int = 120,
        poll_interval: int = 2
    ) -> str:
        """Poll for async image generation task result."""
        url = f"{self.BASE_URL}/tasks/{task_id}"
        
        for attempt in range(max_attempts):
            async with session.get(
                url,
                headers=self._get_headers(),
                timeout=aiohttp.ClientTimeout(total=30)
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"Task status check failed: {error_text}")
                
                data = await response.json()
                status = data.get("output", {}).get("task_status")
                
                logger.debug(f"Image task {task_id} status: {status}")
                
                if status == "SUCCEEDED":
                    results = data.get("output", {}).get("results", [])
                    if results:
                        return results[0].get("url")
                    raise Exception("No image in completed task")
                
                elif status == "FAILED":
                    error_msg = data.get("output", {}).get("message", "Unknown error")
                    error_code = data.get("output", {}).get("code", "")
                    raise Exception(f"Image generation failed: {error_code} - {error_msg}")
                
                elif status in ["PENDING", "RUNNING"]:
                    await asyncio.sleep(poll_interval)
                    continue
                
                else:
                    raise Exception(f"Unknown task status: {status}")
        
        raise Exception("Image generation timed out")
    
    async def download_image(self, url: str) -> bytes:
        """Download image from URL."""
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=60)) as response:
                if response.status == 200:
                    return await response.read()
                raise Exception(f"Failed to download image: {response.status}")
    
    # =========================================
    # Speech Recognition (ASR)
    # =========================================
    
    async def transcribe_audio(
        self,
        audio_data: bytes,
        filename: str = "audio.wav",
        language: str = None,
        model: str = None
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Transcribe audio to text using Qwen ASR.
        
        Args:
            audio_data: Audio file bytes
            filename: Original filename for format detection
            language: Language hint (zh, en, ja, ko, etc.)
            model: ASR model to use
            
        Returns:
            Tuple of (transcribed_text, usage_info)
        """
        if not self.is_configured():
            raise ValueError("Qwen API key not configured")
        
        from config import settings
        model = model or settings.default_qwen_asr_model
        
        url = f"{self.BASE_URL}/services/audio/asr/transcription"
        
        # Encode audio as base64
        audio_base64 = base64.b64encode(audio_data).decode('utf-8')
        
        # Detect format from filename
        ext = filename.split('.')[-1].lower()
        format_map = {
            'wav': 'wav',
            'mp3': 'mp3',
            'ogg': 'ogg',
            'flac': 'flac',
            'm4a': 'm4a',
            'webm': 'webm',
        }
        audio_format = format_map.get(ext, 'wav')
        
        payload = {
            "model": model,
            "input": {
                "audio": f"data:audio/{audio_format};base64,{audio_base64}"
            },
            "parameters": {
                "sample_rate": 16000,
                "format": audio_format,
            }
        }
        
        if language:
            payload["parameters"]["language"] = language
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Qwen ASR API error", status=response.status, error=error_text)
                        raise Exception(f"Qwen ASR API error: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    if "output" not in data:
                        raise Exception("Invalid response from Qwen ASR API")
                    
                    output = data["output"]
                    
                    # Extract transcription
                    text = ""
                    if "text" in output:
                        text = output["text"]
                    elif "sentence" in output:
                        sentences = output["sentence"]
                        text = " ".join(s.get("text", "") for s in sentences)
                    
                    # Estimate duration for cost (rough estimate)
                    duration_minutes = len(audio_data) / (16000 * 2 * 60)  # Assuming 16kHz mono 16-bit
                    
                    pricing = self.PRICING.get(model, {"per_minute": 0.01})
                    cost = duration_minutes * pricing.get("per_minute", 0.01)
                    
                    usage = {
                        "model": model,
                        "duration_minutes": round(duration_minutes, 2),
                        "cost_usd": Decimal(str(round(cost, 6)))
                    }
                    
                    return text, usage
                    
        except Exception as e:
            logger.error("Qwen ASR error", error=str(e))
            raise
    
    # =========================================
    # Text-to-Speech (TTS)
    # =========================================
    
    async def synthesize_speech(
        self,
        text: str,
        voice: str = "longxiaochun",
        model: str = None,
        sample_rate: int = 24000
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Convert text to speech using Qwen TTS.
        
        Args:
            text: Text to convert
            voice: Voice ID (longxiaochun, longxiaoxia, etc.)
            model: TTS model to use
            sample_rate: Audio sample rate
            
        Returns:
            Tuple of (audio_bytes, usage_info)
        """
        if not self.is_configured():
            raise ValueError("Qwen API key not configured")
        
        from config import settings
        model = model or settings.default_qwen_tts_model
        
        url = f"{self.BASE_URL}/services/audio/tts/synthesis"
        
        payload = {
            "model": model,
            "input": {
                "text": text
            },
            "parameters": {
                "voice": voice,
                "sample_rate": sample_rate,
                "format": "wav"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    headers=self._get_headers(),
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error("Qwen TTS API error", status=response.status, error=error_text)
                        raise Exception(f"Qwen TTS API error: {response.status} - {error_text}")
                    
                    data = await response.json()
                    
                    if "output" not in data:
                        raise Exception("Invalid response from Qwen TTS API")
                    
                    output = data["output"]
                    
                    # Get audio data
                    audio_base64 = output.get("audio")
                    if not audio_base64:
                        raise Exception("No audio in response")
                    
                    audio_bytes = base64.b64decode(audio_base64)
                    
                    # Calculate cost
                    char_count = len(text)
                    pricing = self.PRICING.get(model, {"per_1k_chars": 0.02})
                    cost = (char_count / 1000) * pricing.get("per_1k_chars", 0.02)
                    
                    usage = {
                        "model": model,
                        "voice": voice,
                        "characters": char_count,
                        "cost_usd": Decimal(str(round(cost, 6)))
                    }
                    
                    return audio_bytes, usage
                    
        except Exception as e:
            logger.error("Qwen TTS error", error=str(e))
            raise


# Global service instance
qwen_service = QwenService()


def get_qwen_service(api_key: str = None) -> QwenService:
    """Get Qwen service instance with optional custom API key."""
    if api_key:
        return QwenService(api_key=api_key)
    return qwen_service
