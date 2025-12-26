"""
Cache management utilities for DirectorMV
"""

import os
import json
import hashlib
import time
from typing import Optional, Any, Dict
from pathlib import Path
import logging

logger = logging.getLogger("DirectorMV.Utils")


def get_temp_dir() -> Path:
    """Get the DirectorMV temporary directory."""
    try:
        import folder_paths
        base_temp = folder_paths.get_temp_directory()
    except ImportError:
        base_temp = os.path.join(os.path.expanduser("~"), ".cache", "comfyui")
    
    dmv_temp = Path(base_temp) / "directormv"
    dmv_temp.mkdir(parents=True, exist_ok=True)
    return dmv_temp


def get_cache_dir() -> Path:
    """Get the DirectorMV cache directory."""
    cache_dir = get_temp_dir() / "cache"
    cache_dir.mkdir(exist_ok=True)
    return cache_dir


def compute_hash(data: Any) -> str:
    """Compute a hash for any data."""
    data_str = str(data)
    return hashlib.md5(data_str.encode()).hexdigest()


class CacheManager:
    """
    General-purpose cache manager for DirectorMV.
    
    Supports:
    - Memory caching with TTL
    - Disk persistence
    - LRU eviction
    """
    
    def __init__(
        self,
        namespace: str = "default",
        max_memory_items: int = 100,
        default_ttl: int = 3600,  # 1 hour
    ):
        self.namespace = namespace
        self.max_memory_items = max_memory_items
        self.default_ttl = default_ttl
        
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._access_times: Dict[str, float] = {}
        
        self.cache_dir = get_cache_dir() / namespace
        self.cache_dir.mkdir(exist_ok=True)
    
    def _get_disk_path(self, key: str) -> Path:
        """Get disk path for a cache key."""
        safe_key = hashlib.md5(key.encode()).hexdigest()
        return self.cache_dir / f"{safe_key}.json"
    
    def _evict_if_needed(self):
        """Evict least recently used items if over limit."""
        while len(self._memory_cache) >= self.max_memory_items:
            # Find oldest item
            oldest_key = min(self._access_times, key=self._access_times.get)
            del self._memory_cache[oldest_key]
            del self._access_times[oldest_key]
            logger.debug(f"Evicted cache item: {oldest_key}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get item from cache.
        
        Checks memory first, then disk.
        """
        # Check memory cache
        if key in self._memory_cache:
            item = self._memory_cache[key]
            
            # Check TTL
            if item.get("expires_at", float("inf")) < time.time():
                self.delete(key)
                return default
            
            self._access_times[key] = time.time()
            return item.get("value", default)
        
        # Check disk cache
        disk_path = self._get_disk_path(key)
        if disk_path.exists():
            try:
                with open(disk_path, "r") as f:
                    item = json.load(f)
                
                # Check TTL
                if item.get("expires_at", float("inf")) < time.time():
                    disk_path.unlink()
                    return default
                
                # Load to memory cache
                self._evict_if_needed()
                self._memory_cache[key] = item
                self._access_times[key] = time.time()
                
                return item.get("value", default)
            except Exception as e:
                logger.warning(f"Failed to load cached item {key}: {e}")
        
        return default
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        persist: bool = False,
    ) -> None:
        """
        Set item in cache.
        
        Args:
            key: Cache key
            value: Value to cache (must be JSON-serializable for persistence)
            ttl: Time-to-live in seconds (None = default TTL)
            persist: Whether to persist to disk
        """
        ttl = ttl or self.default_ttl
        expires_at = time.time() + ttl
        
        item = {
            "value": value,
            "expires_at": expires_at,
            "created_at": time.time(),
        }
        
        # Store in memory
        self._evict_if_needed()
        self._memory_cache[key] = item
        self._access_times[key] = time.time()
        
        # Persist to disk if requested
        if persist:
            disk_path = self._get_disk_path(key)
            try:
                with open(disk_path, "w") as f:
                    json.dump(item, f)
            except Exception as e:
                logger.warning(f"Failed to persist cache item {key}: {e}")
    
    def delete(self, key: str) -> bool:
        """Delete item from cache."""
        deleted = False
        
        if key in self._memory_cache:
            del self._memory_cache[key]
            del self._access_times[key]
            deleted = True
        
        disk_path = self._get_disk_path(key)
        if disk_path.exists():
            disk_path.unlink()
            deleted = True
        
        return deleted
    
    def clear(self) -> int:
        """Clear all cached items. Returns count of deleted items."""
        count = len(self._memory_cache)
        
        self._memory_cache.clear()
        self._access_times.clear()
        
        # Clear disk cache
        for path in self.cache_dir.glob("*.json"):
            path.unlink()
            count += 1
        
        return count
    
    def keys(self) -> list:
        """List all cache keys (memory only)."""
        return list(self._memory_cache.keys())


# Global cache instances
_caches: Dict[str, CacheManager] = {}


def get_cache(namespace: str = "default") -> CacheManager:
    """Get or create a cache manager for a namespace."""
    if namespace not in _caches:
        _caches[namespace] = CacheManager(namespace)
    return _caches[namespace]

