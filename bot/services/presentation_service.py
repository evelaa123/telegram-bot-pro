"""
Presentation generation service.
Creates presentations using Gamma API.
Gamma handles ALL design aspects: colors, fonts, layouts, images.
"""
from typing import Optional, Dict, Any, Tuple
from decimal import Decimal

from bot.services.gamma_service import gamma_service
from config import settings
import structlog

logger = structlog.get_logger()


class PresentationService:
    """
    Service for generating PowerPoint presentations.
    Uses Gamma API which handles all design decisions.
    """
    
    def __init__(self):
        self.gamma = gamma_service
    
    async def generate_presentation(
        self,
        topic: str,
        slides_count: int = 10,
        style: str = "business",
        include_images: bool = True,
        language: str = "ru",
        progress_callback=None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Generate a complete presentation using Gamma API.
        
        Args:
            topic: Presentation topic
            slides_count: Number of slides (3-60)
            style: Visual style hint (business, creative, educational, modern)
            include_images: Whether to generate images for slides
            language: Output language
            progress_callback: Async callback for progress updates
            
        Returns:
            Tuple of (pptx_bytes, generation_info)
        """
        slides_count = max(3, min(60, slides_count))
        
        if not self.gamma.is_configured():
            raise ValueError(
                "Gamma API is not configured. "
                "Please set GAMMA_API_KEY in environment variables."
            )
        
        try:
            # Generate using Gamma
            result, usage = await self.gamma.generate_presentation(
                topic=topic,
                slides_count=slides_count,
                style=style,
                language=language,
                include_images=include_images,
                progress_callback=progress_callback
            )
            
            # Get URLs from result
            gamma_url = result.get("gammaUrl")
            pptx_url = result.get("pptxUrl")
            
            if not pptx_url:
                # If no PPTX URL, we can still return the Gamma URL
                logger.warning("No PPTX URL in Gamma response, only web URL available")
                
                # Return empty bytes but with URL info
                return b"", {
                    "title": topic,
                    "slides_count": slides_count,
                    "gamma_url": gamma_url,
                    "pptx_url": None,
                    "usage": {
                        "provider": "gamma",
                        "credits_used": usage.get("credits_used", 0),
                        "credits_remaining": usage.get("credits_remaining", 0),
                        "total_cost_usd": Decimal("0")  # Gamma uses credits, not direct billing
                    }
                }
            
            # Download PPTX
            if progress_callback:
                await progress_callback({
                    "step": "downloading",
                    "message": "Скачивание PPTX..." if language == "ru" else "Downloading PPTX...",
                    "progress": 95
                })
            
            pptx_bytes = await self.gamma.download_pptx(pptx_url)
            
            return pptx_bytes, {
                "title": topic,
                "slides_count": slides_count,
                "gamma_url": gamma_url,
                "pptx_url": pptx_url,
                "usage": {
                    "provider": "gamma",
                    "credits_used": usage.get("credits_used", 0),
                    "credits_remaining": usage.get("credits_remaining", 0),
                    "total_cost_usd": Decimal("0")
                }
            }
            
        except Exception as e:
            logger.error("Presentation generation failed", error=str(e), topic=topic)
            raise
    
    async def generate_presentation_from_text(
        self,
        text: str,
        title: str = None,
        style: str = "business",
        include_images: bool = True,
        language: str = "ru",
        progress_callback=None
    ) -> Tuple[bytes, Dict[str, Any]]:
        """
        Generate presentation from existing text content.
        
        Args:
            text: Text content to convert to presentation
            title: Optional presentation title
            style: Visual style
            include_images: Whether to generate images
            language: Output language
            progress_callback: Progress callback
            
        Returns:
            Tuple of (pptx_bytes, generation_info)
        """
        # Combine title and text as input
        if title:
            full_text = f"# {title}\n\n{text}"
        else:
            full_text = text
        
        # Estimate slides from text length (roughly 1 slide per 500 chars)
        estimated_slides = max(3, min(20, len(text) // 500 + 2))
        
        return await self.generate_presentation(
            topic=full_text,
            slides_count=estimated_slides,
            style=style,
            include_images=include_images,
            language=language,
            progress_callback=progress_callback
        )


# Global service instance
presentation_service = PresentationService()
