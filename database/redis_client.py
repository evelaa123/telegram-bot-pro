"""
Redis client for caching and session management.
"""
import json
from typing import Optional, Any, List, Dict
from datetime import timedelta
import redis.asyncio as redis

from config import settings


class RedisClient:
    """
    Async Redis client wrapper.
    Provides typed methods for common operations.
    """
    
    def __init__(self):
        self._pool: Optional[redis.ConnectionPool] = None
        self._client: Optional[redis.Redis] = None
    
    async def connect(self) -> None:
        """Initialize Redis connection pool."""
        self._pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True
        )
        self._client = redis.Redis(connection_pool=self._pool)
    
    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.close()
        if self._pool:
            await self._pool.disconnect()
    
    @property
    def client(self) -> redis.Redis:
        """Get Redis client instance."""
        if not self._client:
            raise RuntimeError("Redis client not initialized. Call connect() first.")
        return self._client
    
    # =====================================
    # Subscription Cache
    # =====================================
    
    async def get_subscription_status(self, telegram_id: int) -> Optional[bool]:
        """
        Get cached subscription status.
        Returns None if not cached.
        """
        key = f"user:{telegram_id}:subscription"
        value = await self.client.get(key)
        if value is None:
            return None
        return value == "subscribed"
    
    async def set_subscription_status(
        self, 
        telegram_id: int, 
        is_subscribed: bool,
        ttl: int = None
    ) -> None:
        """Cache subscription status."""
        key = f"user:{telegram_id}:subscription"
        value = "subscribed" if is_subscribed else "not_subscribed"
        ttl = ttl or settings.subscription_cache_ttl
        await self.client.setex(key, ttl, value)
    
    async def invalidate_subscription(self, telegram_id: int) -> None:
        """Invalidate cached subscription status."""
        key = f"user:{telegram_id}:subscription"
        await self.client.delete(key)
    
    # =====================================
    # Dialog Context
    # =====================================
    
    async def get_context(self, telegram_id: int) -> List[Dict[str, str]]:
        """
        Get conversation context for user.
        Returns list of message dicts with 'role' and 'content'.
        """
        key = f"user:{telegram_id}:context"
        value = await self.client.get(key)
        if value is None:
            return []
        return json.loads(value)
    
    async def add_to_context(
        self, 
        telegram_id: int, 
        role: str, 
        content: str,
        max_messages: int = None
    ) -> None:
        """
        Add message to conversation context.
        Keeps only last max_messages.
        """
        key = f"user:{telegram_id}:context"
        max_messages = max_messages or settings.max_context_messages
        
        context = await self.get_context(telegram_id)
        context.append({"role": role, "content": content})
        
        # Keep only last N messages
        if len(context) > max_messages:
            context = context[-max_messages:]
        
        await self.client.setex(
            key, 
            settings.context_ttl_seconds,
            json.dumps(context, ensure_ascii=False)
        )
    
    async def clear_context(self, telegram_id: int) -> None:
        """Clear conversation context."""
        key = f"user:{telegram_id}:context"
        await self.client.delete(key)
    
    # =====================================
    # User State (FSM)
    # =====================================
    
    async def get_user_state(self, telegram_id: int) -> Optional[str]:
        """Get current user state/mode."""
        key = f"user:{telegram_id}:state"
        return await self.client.get(key)
    
    async def set_user_state(
        self, 
        telegram_id: int, 
        state: str,
        ttl: int = 3600
    ) -> None:
        """Set user state/mode."""
        key = f"user:{telegram_id}:state"
        await self.client.setex(key, ttl, state)
    
    async def clear_user_state(self, telegram_id: int) -> None:
        """Clear user state."""
        key = f"user:{telegram_id}:state"
        await self.client.delete(key)
    
    # =====================================
    # User Settings Cache
    # =====================================
    
    async def get_user_settings(self, telegram_id: int) -> Optional[Dict[str, Any]]:
        """Get cached user settings."""
        key = f"user:{telegram_id}:settings"
        value = await self.client.get(key)
        if value is None:
            return None
        return json.loads(value)
    
    async def set_user_settings(
        self, 
        telegram_id: int, 
        user_settings: Dict[str, Any],
        ttl: int = 3600
    ) -> None:
        """Cache user settings."""
        key = f"user:{telegram_id}:settings"
        await self.client.setex(
            key, 
            ttl,
            json.dumps(user_settings, ensure_ascii=False)
        )
    
    async def invalidate_user_settings(self, telegram_id: int) -> None:
        """Invalidate cached user settings."""
        key = f"user:{telegram_id}:settings"
        await self.client.delete(key)
    
    # =====================================
    # Rate Limiting
    # =====================================
    
    async def check_rate_limit(
        self, 
        key: str, 
        limit: int, 
        window_seconds: int
    ) -> bool:
        """
        Check if rate limit is exceeded.
        Uses sliding window counter.
        Returns True if within limit, False if exceeded.
        """
        import time
        
        now = time.time()
        window_start = now - window_seconds
        
        pipe = self.client.pipeline()
        # Remove old entries
        pipe.zremrangebyscore(key, 0, window_start)
        # Count current entries
        pipe.zcard(key)
        # Add current request
        pipe.zadd(key, {str(now): now})
        # Set expiry
        pipe.expire(key, window_seconds)
        
        results = await pipe.execute()
        count = results[1]
        
        return count < limit
    
    # =====================================
    # Document Context
    # =====================================
    
    async def set_document_context(
        self, 
        telegram_id: int, 
        content: str,
        filename: str,
        ttl: int = 1800
    ) -> None:
        """Store document content for follow-up questions."""
        key = f"user:{telegram_id}:document"
        data = {
            "content": content,
            "filename": filename
        }
        await self.client.setex(
            key,
            ttl,
            json.dumps(data, ensure_ascii=False)
        )
    
    async def get_document_context(self, telegram_id: int) -> Optional[Dict[str, str]]:
        """Get stored document context."""
        key = f"user:{telegram_id}:document"
        value = await self.client.get(key)
        if value is None:
            return None
        return json.loads(value)
    
    async def clear_document_context(self, telegram_id: int) -> None:
        """Clear document context."""
        key = f"user:{telegram_id}:document"
        await self.client.delete(key)
    
    # =====================================
    # Video Generation State
    # =====================================
    
    async def store_video_ids(
        self, 
        telegram_id: int, 
        video_id: str,
        max_videos: int = 5
    ) -> None:
        """Store video ID for potential remix."""
        key = f"user:{telegram_id}:videos"
        
        # Get existing list
        videos_json = await self.client.get(key)
        videos = json.loads(videos_json) if videos_json else []
        
        # Add new video
        videos.append(video_id)
        
        # Keep only last N
        if len(videos) > max_videos:
            videos = videos[-max_videos:]
        
        # Store with TTL of 24 hours
        await self.client.setex(
            key,
            86400,
            json.dumps(videos)
        )
    
    async def get_last_video_id(self, telegram_id: int) -> Optional[str]:
        """Get last generated video ID."""
        key = f"user:{telegram_id}:videos"
        videos_json = await self.client.get(key)
        if not videos_json:
            return None
        videos = json.loads(videos_json)
        return videos[-1] if videos else None
    
    # =====================================
    # Generic Methods
    # =====================================
    
    async def get(self, key: str) -> Optional[str]:
        """Get value by key."""
        return await self.client.get(key)
    
    async def set(
        self, 
        key: str, 
        value: str, 
        ttl: Optional[int] = None
    ) -> None:
        """Set value with optional TTL."""
        if ttl:
            await self.client.setex(key, ttl, value)
        else:
            await self.client.set(key, value)
    
    async def delete(self, key: str) -> None:
        """Delete key."""
        await self.client.delete(key)
    
    async def exists(self, key: str) -> bool:
        """Check if key exists."""
        return await self.client.exists(key) > 0


# Global Redis client instance
redis_client = RedisClient()
