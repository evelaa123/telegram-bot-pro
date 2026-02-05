"""
GigaChat API service for presentations and text generation.
Uses Sber GigaChat API for creating presentation structures.
"""
import asyncio
import aiohttp
import uuid
import base64
from typing import Optional, Dict, Any, List, Tuple
from decimal import Decimal
from datetime import datetime, timedelta

from config import settings
import structlog

logger = structlog.get_logger()


class GigaChatService:
    """
    Service for interacting with GigaChat API.
    Used primarily for presentation generation with Russian language support.
    """
    
    # API URLs
    AUTH_URL = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
    API_URL = "https://gigachat.devices.sberbank.ru/api/v1"
    
    # Available models
    MODELS = {
        "gigachat": "GigaChat",
        "gigachat-plus": "GigaChat-Plus",
        "gigachat-pro": "GigaChat-Pro",
        "gigachat-2-max": "GigaChat-2-Max"
    }
    
    # Pricing per 1K tokens (RUB)
    PRICING = {
        "GigaChat": {"input": 0.05, "output": 0.1},
        "GigaChat-Plus": {"input": 0.1, "output": 0.2},
        "GigaChat-Pro": {"input": 0.5, "output": 1.0},
        "GigaChat-2-Max": {"input": 1.95, "output": 1.95}
    }
    
    def __init__(self):
        self._access_token: Optional[str] = None
        self._token_expires_at: Optional[datetime] = None
    
    def is_configured(self) -> bool:
        """Check if GigaChat is configured."""
        credentials = getattr(settings, 'gigachat_credentials', None)
        return bool(credentials and len(credentials) > 10)
    
    async def _get_access_token(self) -> str:
        """Get or refresh access token."""
        # Check if current token is still valid
        if self._access_token and self._token_expires_at:
            if datetime.now() < self._token_expires_at - timedelta(minutes=1):
                return self._access_token
        
        credentials = getattr(settings, 'gigachat_credentials', '')
        scope = getattr(settings, 'gigachat_scope', 'GIGACHAT_API_PERS')
        
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded',
            'Accept': 'application/json',
            'RqUID': str(uuid.uuid4()),
            'Authorization': f'Basic {credentials}'
        }
        
        data = {'scope': scope}
        
        async with aiohttp.ClientSession() as session:
            async with session.post(
                self.AUTH_URL,
                headers=headers,
                data=data,
                ssl=False  # GigaChat may have certificate issues
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("GigaChat auth failed", status=response.status, error=error_text)
                    raise Exception(f"GigaChat authentication failed: {error_text}")
                
                result = await response.json()
                self._access_token = result['access_token']
                # expires_at is a Unix timestamp (milliseconds)
                expires_at_ms = result.get('expires_at', 0)
                if expires_at_ms > 1000000000000:  # Timestamp in milliseconds
                    self._token_expires_at = datetime.fromtimestamp(expires_at_ms / 1000) - timedelta(minutes=1)
                else:  # Fallback: treat as seconds from now
                    self._token_expires_at = datetime.now() + timedelta(minutes=29)
                
                logger.info("GigaChat token obtained", expires_at=self._token_expires_at)
                return self._access_token
    
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Dict = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Make authenticated request to GigaChat API."""
        token = await self._get_access_token()
        
        headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {token}'
        }
        if json_data:
            headers['Content-Type'] = 'application/json'
        
        url = f"{self.API_URL}/{endpoint}"
        
        async with aiohttp.ClientSession() as session:
            async with session.request(
                method,
                url,
                headers=headers,
                json=json_data,
                ssl=False,
                **kwargs
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error("GigaChat request failed", 
                               status=response.status, 
                               endpoint=endpoint,
                               error=error_text)
                    raise Exception(f"GigaChat request failed: {error_text}")
                
                return await response.json()
    
    async def generate_text(
        self,
        messages: List[Dict[str, str]],
        model: str = "GigaChat",
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate text using GigaChat.
        
        Returns:
            Tuple of (response_text, usage_info)
        """
        try:
            data = {
                "model": model,
                "messages": messages,
                "max_tokens": max_tokens,
                "temperature": temperature
            }
            
            result = await self._make_request("POST", "chat/completions", data)
            
            content = result['choices'][0]['message']['content']
            usage = result.get('usage', {})
            
            usage_info = {
                "input_tokens": usage.get('prompt_tokens', 0),
                "output_tokens": usage.get('completion_tokens', 0),
                "total_tokens": usage.get('total_tokens', 0),
                "model": model,
                "provider": "gigachat"
            }
            
            # Calculate cost (in RUB)
            pricing = self.PRICING.get(model, self.PRICING["GigaChat"])
            cost_rub = (
                (usage_info["input_tokens"] / 1000) * pricing["input"] +
                (usage_info["output_tokens"] / 1000) * pricing["output"]
            )
            usage_info["cost_rub"] = Decimal(str(round(cost_rub, 4)))
            
            return content, usage_info
            
        except Exception as e:
            logger.error("GigaChat generation error", error=str(e))
            raise
    
    async def generate_image_prompt(
        self,
        description: str,
        model: str = "GigaChat"
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Generate image using GigaChat's built-in text2image.
        
        Returns:
            Tuple of (image_id, usage_info)
        """
        try:
            messages = [
                {"role": "user", "content": f"Нарисуй {description}"}
            ]
            
            data = {
                "model": model,
                "messages": messages,
                "function_call": "auto"
            }
            
            result = await self._make_request("POST", "chat/completions", data)
            
            content = result['choices'][0]['message']['content']
            usage = result.get('usage', {})
            
            # Extract image ID from response (format: <img src="uuid" .../>)
            import re
            img_match = re.search(r'<img src="([^"]+)"', content)
            image_id = img_match.group(1) if img_match else None
            
            usage_info = {
                "input_tokens": usage.get('prompt_tokens', 0),
                "output_tokens": usage.get('completion_tokens', 0),
                "model": model,
                "image_id": image_id,
                "provider": "gigachat"
            }
            
            return image_id, usage_info
            
        except Exception as e:
            logger.error("GigaChat image generation error", error=str(e))
            raise
    
    async def download_image(self, file_id: str) -> bytes:
        """Download generated image by file ID."""
        token = await self._get_access_token()
        
        url = f"{self.API_URL}/files/{file_id}/content"
        headers = {
            'Accept': 'application/jpg',
            'Authorization': f'Bearer {token}'
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, ssl=False) as response:
                if response.status != 200:
                    raise Exception(f"Failed to download image: {response.status}")
                return await response.read()
    
    # =========================================
    # Presentation Generation
    # =========================================
    
    async def generate_presentation_structure(
        self,
        topic: str,
        slides_count: int = 5,
        style: str = "business",
        language: str = "ru"
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate presentation structure using GigaChat.
        
        Args:
            topic: Presentation topic
            slides_count: Number of slides
            style: Presentation style (business, creative, educational)
            language: Output language
            
        Returns:
            Tuple of (presentation_structure, usage_info)
        """
        style_descriptions = {
            "business": "деловом, профессиональном стиле",
            "creative": "креативном, ярком стиле",
            "educational": "образовательном, наглядном стиле"
        }
        style_desc = style_descriptions.get(style, style_descriptions["business"])
        
        system_prompt = f"""Ты — эксперт по созданию презентаций. Твоя задача — создать структуру презентации в {style_desc}.

Верни результат СТРОГО в JSON формате:
{{
    "title": "Название презентации",
    "slides": [
        {{
            "slide_number": 1,
            "title": "Заголовок слайда",
            "content": ["Пункт 1", "Пункт 2", "Пункт 3"],
            "notes": "Заметки докладчика",
            "image_prompt": "Описание изображения для слайда на английском языке"
        }}
    ],
    "summary": "Краткое описание презентации"
}}

Требования:
- Первый слайд — титульный (только название)
- Последний слайд — заключение/вопросы
- Каждый слайд должен иметь 3-5 пунктов содержания
- image_prompt должен быть на АНГЛИЙСКОМ языке для генерации изображений
- Используй профессиональный язык
- Количество слайдов: {slides_count}"""

        user_prompt = f"Создай презентацию на тему: {topic}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        content, usage = await self.generate_text(
            messages,
            model="GigaChat-2-Max",
            max_tokens=4096,
            temperature=0.7
        )
        
        # Parse JSON from response
        import json
        try:
            # Try to extract JSON from the response
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                structure = json.loads(json_str)
            else:
                raise ValueError("No JSON found in response")
        except json.JSONDecodeError as e:
            logger.error("Failed to parse presentation structure", error=str(e), content=content)
            # Create fallback structure
            structure = {
                "title": topic,
                "slides": [
                    {
                        "slide_number": 1,
                        "title": topic,
                        "content": [],
                        "notes": "",
                        "image_prompt": f"Title slide for {topic}"
                    }
                ],
                "summary": topic
            }
        
        return structure, usage
    
    async def enhance_slide_content(
        self,
        slide_title: str,
        slide_content: List[str],
        presentation_topic: str
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Enhance and expand slide content.
        
        Returns:
            Tuple of (enhanced_content, usage_info)
        """
        messages = [
            {
                "role": "system",
                "content": """Ты — эксперт по созданию презентаций. Расширь и улучши содержание слайда.
                
Верни результат в JSON:
{
    "title": "Улучшенный заголовок",
    "content": ["Расширенный пункт 1", "Расширенный пункт 2", ...],
    "notes": "Подробные заметки для докладчика"
}"""
            },
            {
                "role": "user",
                "content": f"""Тема презентации: {presentation_topic}
Заголовок слайда: {slide_title}
Текущее содержание: {', '.join(slide_content)}

Расширь и улучши содержание этого слайда."""
            }
        ]
        
        content, usage = await self.generate_text(
            messages,
            model="GigaChat",
            max_tokens=2048,
            temperature=0.5
        )
        
        import json
        try:
            json_start = content.find('{')
            json_end = content.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                enhanced = json.loads(content[json_start:json_end])
            else:
                enhanced = {
                    "title": slide_title,
                    "content": slide_content,
                    "notes": ""
                }
        except json.JSONDecodeError:
            enhanced = {
                "title": slide_title,
                "content": slide_content,
                "notes": ""
            }
        
        return enhanced, usage


# Global service instance
gigachat_service = GigaChatService()
