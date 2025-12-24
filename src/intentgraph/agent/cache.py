"""
Caching mechanism for AI Coding Agent.

Provides intelligent caching to reduce redundant LLM calls and improve performance.
"""

import hashlib
import json
import pickle
from pathlib import Path
from typing import Any, Optional, Dict
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict


@dataclass
class CacheEntry:
    """Cache entry with metadata."""
    key: str
    value: Any
    created_at: datetime
    expires_at: Optional[datetime] = None
    hit_count: int = 0
    metadata: Dict[str, Any] = None


class CacheManager:
    """
    Cache manager for LLM responses and analysis results.
    
    Features:
    - In-memory caching with TTL
    - Disk persistence
    - Cache invalidation
    - Hit rate tracking
    """

    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        ttl_seconds: int = 3600,
        max_memory_items: int = 1000
    ):
        """
        Initialize cache manager.
        
        Args:
            cache_dir: Directory for persistent cache (None = memory only)
            ttl_seconds: Time-to-live for cache entries
            max_memory_items: Maximum items in memory cache
        """
        self.cache_dir = cache_dir
        self.ttl_seconds = ttl_seconds
        self.max_memory_items = max_memory_items
        
        # In-memory cache
        self._memory_cache: Dict[str, CacheEntry] = {}
        
        # Statistics
        self._hits = 0
        self._misses = 0
        
        # Create cache directory if needed
        if cache_dir:
            cache_dir.mkdir(parents=True, exist_ok=True)

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found/expired
        """
        # Check memory cache first
        if key in self._memory_cache:
            entry = self._memory_cache[key]
            
            # Check expiration
            if entry.expires_at and datetime.now() > entry.expires_at:
                del self._memory_cache[key]
                self._misses += 1
                return None
            
            # Update hit count
            entry.hit_count += 1
            self._hits += 1
            return entry.value
        
        # Check disk cache
        if self.cache_dir:
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                try:
                    with open(cache_file, 'rb') as f:
                        entry = pickle.load(f)
                    
                    # Check expiration
                    if entry.expires_at and datetime.now() > entry.expires_at:
                        cache_file.unlink()
                        self._misses += 1
                        return None
                    
                    # Load into memory cache
                    self._memory_cache[key] = entry
                    entry.hit_count += 1
                    self._hits += 1
                    return entry.value
                except:
                    pass
        
        self._misses += 1
        return None

    def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        """
        Set value in cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Custom TTL (overrides default)
            metadata: Additional metadata
        """
        ttl = ttl_seconds if ttl_seconds is not None else self.ttl_seconds
        expires_at = datetime.now() + timedelta(seconds=ttl) if ttl > 0 else None
        
        entry = CacheEntry(
            key=key,
            value=value,
            created_at=datetime.now(),
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        # Store in memory
        self._memory_cache[key] = entry
        
        # Evict old entries if needed
        if len(self._memory_cache) > self.max_memory_items:
            self._evict_lru()
        
        # Store on disk
        if self.cache_dir:
            cache_file = self._get_cache_file(key)
            try:
                with open(cache_file, 'wb') as f:
                    pickle.dump(entry, f)
            except:
                pass

    def invalidate(self, key: str):
        """Invalidate cache entry."""
        # Remove from memory
        if key in self._memory_cache:
            del self._memory_cache[key]
        
        # Remove from disk
        if self.cache_dir:
            cache_file = self._get_cache_file(key)
            if cache_file.exists():
                cache_file.unlink()

    def clear(self):
        """Clear all cache."""
        self._memory_cache.clear()
        
        if self.cache_dir:
            for cache_file in self.cache_dir.glob("*.cache"):
                cache_file.unlink()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "memory_items": len(self._memory_cache),
            "total_requests": total_requests
        }

    def _get_cache_file(self, key: str) -> Path:
        """Get cache file path for key."""
        key_hash = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{key_hash}.cache"

    def _evict_lru(self):
        """Evict least recently used entries."""
        # Sort by hit count (ascending)
        sorted_entries = sorted(
            self._memory_cache.items(),
            key=lambda x: x[1].hit_count
        )
        
        # Remove bottom 10%
        num_to_remove = max(1, len(sorted_entries) // 10)
        for key, _ in sorted_entries[:num_to_remove]:
            del self._memory_cache[key]

    @staticmethod
    def generate_key(prefix: str, *args, **kwargs) -> str:
        """Generate cache key from arguments."""
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
        key_str = ":".join(key_parts)
        return hashlib.md5(key_str.encode()).hexdigest()

