"""
Cache manager with Redis and in-memory cache support.
Handles caching operations with TTL and key generation.
"""

import json
import logging
import redis
from typing import Any, Optional


class CacheManager:
    """
    Cache manager with Redis and in-memory cache support.
    
    @param enabled: Whether caching is enabled
    @param ttl: Cache time to live in seconds
    """
    
    def __init__(self, enabled: bool = True, ttl: int = 300):
        self.enabled = enabled
        self.ttl = ttl
        
        if self.enabled:
            try:
                self.redis_client = redis.Redis(
                    host='localhost',
                    port=6379,
                    db=0,
                    decode_responses=True
                )
                self.redis_client.ping()
                logging.info("Redis connected successfully")
            except Exception as e:
                logging.warning(f"Redis unavailable: {e}, using in-memory cache")
                self.enabled = False
                self.memory_cache = {}
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        @param key: Cache key
        @return: Value from cache or None
        """
        if not self.enabled:
            return self.memory_cache.get(key) if hasattr(self, 'memory_cache') else None
        
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logging.error(f"Error getting from cache: {e}")
        return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache.
        
        @param key: Cache key
        @param value: Value to cache
        @param ttl: Time to live in seconds
        """
        ttl = ttl or self.ttl
        
        if not self.enabled:
            if not hasattr(self, 'memory_cache'):
                self.memory_cache = {}
            self.memory_cache[key] = value
            return
        
        try:
            self.redis_client.setex(key, ttl, json.dumps(value, ensure_ascii=False))
        except Exception as e:
            logging.error(f"Error setting cache: {e}")
    
    def delete(self, key: str):
        """
        Delete value from cache.
        
        @param key: Cache key
        """
        if not self.enabled:
            if hasattr(self, 'memory_cache') and key in self.memory_cache:
                del self.memory_cache[key]
            return
        
        try:
            self.redis_client.delete(key)
        except Exception as e:
            logging.error(f"Error deleting from cache: {e}")
    
    def generate_key(self, prefix: str, **kwargs) -> str:
        """
        Generate cache key based on parameters.
        
        @param prefix: Key prefix
        @param **kwargs: Parameters for key generation
        @return: Generated cache key
        """
        key_parts = [prefix]
        for k, v in sorted(kwargs.items()):
            key_parts.append(f"{k}:{v}")
        return ":".join(key_parts)