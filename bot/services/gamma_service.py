"""
Gamma API service for presentation generation.
Creates presentations using Gamma's AI-powered API.
https://developers.gamma.app/
"""
import aiohttp
import asyncio
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal

from config import settings
import structlog

logger = structlog.get_logger()


class GammaService:
    """
    Service for interacting with Gamma API.
    Creates presentations, documents, and more using AI.
    """
    
    BASE_URL = "https://public-api.gamma.app/v1.0"
    
    # Language mapping for Gamma API
    LANGUAGE_MAP = {
        "ru": "ru",
        "en": "en",
        "de": "de",
        "fr": "fr",
        "es": "es",
        "it": "it",
        "pt": "pt",
        "zh": "zh",
        "ja": "ja",
        "ko": "ko",
    }
    
    def __init__(self):
        self._api_key: Optional[str] = None
    
    @property
    def api_key(self) -> str:
        """Get API key from settings."""
        if self._api_key:
            return self._api_key
        return getattr(settings, 'gamma_api_key', '') or ''
    
    def set_api_key(self, key: str):
        """Set API key (for runtime updates)."""
        self._api_key = key
        logger.info("Gamma API key updated")
    
    def is_configured(self) -> bool:
        """Check if Gamma API is configured."""
        return bool(self.api_key and len(self.api_key) > 10)
    
    async def generate_presentation(
        self,
        topic: str,
        slides_count: int = 10,
        style: str = "business",
        language: str = "ru",
        include_images: bool = True,
        additional_instructions: str = None,
        progress_callback=None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate a presentation using Gamma API.
        
        Args:
            topic: Presentation topic/content
            slides_count: Number of slides (cards) to generate
            style: Style hint (business, creative, educational, etc.)
            language: Output language code
            include_images: Whether to include AI-generated images
            additional_instructions: Extra instructions for generation
            progress_callback: Async callback for progress updates
            
        Returns:
            Tuple of (result_dict, usage_info)
            result_dict contains: gammaUrl, pptxUrl (if exported), status
        """
        if not self.is_configured():
            raise ValueError("Gamma API key is not configured")
        
        # Map style to tone
        style_to_tone = {
            "business": "professional, formal",
            "creative": "creative, engaging, dynamic",
            "educational": "educational, clear, informative",
            "modern": "modern, minimalist, sleek",
        }
        tone = style_to_tone.get(style, "professional")
        
        # Build request payload
        payload = {
            "inputText": topic,
            "textMode": "generate",
            "format": "presentation",
            "numCards": min(max(slides_count, 3), 60),  # Gamma limits: 1-60 for Pro
            "cardSplit": "auto",
            "textOptions": {
                "amount": "medium",
                "tone": tone,
                "language": self.LANGUAGE_MAP.get(language, "en")
            },
            "cardOptions": {
                "dimensions": "16x9"
            },
            "exportAs": "pptx"  # Auto-export to PPTX
        }
        
        # Add image options
        if include_images:
            payload["imageOptions"] = {
                "source": "aiGenerated",
                "model": "flux-1-pro",
                "style": "professional, high quality"
            }
        else:
            payload["imageOptions"] = {
                "source": "noImages"
            }
        
        # Add additional instructions
        if additional_instructions:
            payload["additionalInstructions"] = additional_instructions
        
        try:
            if progress_callback:
                await progress_callback({
                    "step": "generating",
                    "message": "Gamma создаёт презентацию..." if language == "ru" else "Gamma is creating presentation...",
                    "progress": 10
                })
            
            # Start generation
            generation_id = await self._start_generation(payload)
            
            if progress_callback:
                await progress_callback({
                    "step": "processing",
                    "message": "Обработка..." if language == "ru" else "Processing...",
                    "progress": 30
                })
            
            # Poll for completion
            result = await self._wait_for_completion(
                generation_id, 
                language=language,
                progress_callback=progress_callback
            )
            
            if progress_callback:
                await progress_callback({
                    "step": "complete",
                    "message": "Готово!" if language == "ru" else "Complete!",
                    "progress": 100
                })
            
            usage_info = {
                "provider": "gamma",
                "credits_used": result.get("credits", {}).get("deducted", 0),
                "credits_remaining": result.get("credits", {}).get("remaining", 0),
            }
            
            return result, usage_info
            
        except Exception as e:
            logger.error("Gamma generation failed", error=str(e))
            raise
    
    async def _start_generation(self, payload: Dict[str, Any]) -> str:
        """Start a generation and return generation ID."""
        headers = {
            "Content-Type": "application/json",
            "X-API-KEY": self.api_key
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.BASE_URL}/generations",
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("Gamma API error", status=response.status, error=error_text)
                    raise Exception(f"Gamma API error: {error_text}")
                
                result = await response.json()
                generation_id = result.get("generationId")
                
                if not generation_id:
                    raise Exception("No generation ID returned from Gamma")
                
                logger.info("Gamma generation started", generation_id=generation_id)
                return generation_id
    
    async def _wait_for_completion(
        self,
        generation_id: str,
        timeout: int = 300,
        poll_interval: int = 5,
        language: str = "ru",
        progress_callback=None
    ) -> Dict[str, Any]:
        """Poll for generation completion."""
        headers = {
            "X-API-KEY": self.api_key,
            "Accept": "application/json"
        }
        
        start_time = asyncio.get_event_loop().time()
        progress = 30
        
        async with aiohttp.ClientSession() as session:
            while True:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed > timeout:
                    raise TimeoutError(f"Gamma generation timed out after {timeout}s")
                
                async with session.get(
                    f"{self.BASE_URL}/generations/{generation_id}",
                    headers=headers
                ) as response:
                    if response.status == 404:
                        raise Exception(f"Generation not found: {generation_id}")
                    
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Gamma status check failed: {error_text}")
                    
                    result = await response.json()
                    status = result.get("status")
                    
                    logger.info("Gamma generation status", 
                              generation_id=generation_id, 
                              status=status,
                              elapsed=f"{elapsed:.1f}s")
                    
                    if status == "completed":
                        return result
                    
                    if status == "failed":
                        raise Exception(f"Gamma generation failed: {result.get('message', 'Unknown error')}")
                    
                    # Update progress
                    if progress_callback:
                        progress = min(90, progress + 5)
                        await progress_callback({
                            "step": "processing",
                            "message": f"Gamma обрабатывает ({int(elapsed)}с)..." if language == "ru" else f"Gamma processing ({int(elapsed)}s)...",
                            "progress": progress
                        })
                    
                    await asyncio.sleep(poll_interval)
    
    async def download_pptx(self, pptx_url: str) -> bytes:
        """Download PPTX file from Gamma URL."""
        async with aiohttp.ClientSession() as session:
            async with session.get(pptx_url) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download PPTX: {response.status}")
                return await response.read()


# Global service instance
gamma_service = GammaService()
