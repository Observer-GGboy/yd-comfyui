"""
DMV_IdentityCache - Cache and manage identity tokens

Provides persistent caching of identity embeddings per character ID.
Enables consistent identity across multiple workflow runs.
"""

import torch
import os
import json
import hashlib
from typing import Tuple, Optional, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger("DirectorMV.Identity")


class IdentityCacheManager:
    """
    Singleton manager for identity cache.
    
    Caches identity embeddings to disk for persistence across sessions.
    """
    
    _instance: Optional["IdentityCacheManager"] = None
    _cache: Dict[str, torch.Tensor] = {}
    _metadata: Dict[str, Dict[str, Any]] = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize cache directory."""
        # Use ComfyUI's temp directory structure
        import folder_paths
        self.cache_dir = os.path.join(folder_paths.get_temp_directory(), "dmv_identity_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        self._load_metadata()
        logger.info(f"Identity cache initialized at {self.cache_dir}")
    
    def _load_metadata(self):
        """Load cache metadata from disk."""
        meta_path = os.path.join(self.cache_dir, "metadata.json")
        if os.path.exists(meta_path):
            try:
                with open(meta_path, "r") as f:
                    self._metadata = json.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache metadata: {e}")
                self._metadata = {}
    
    def _save_metadata(self):
        """Save cache metadata to disk."""
        meta_path = os.path.join(self.cache_dir, "metadata.json")
        try:
            with open(meta_path, "w") as f:
                json.dump(self._metadata, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cache metadata: {e}")
    
    def _get_cache_path(self, character_id: str) -> str:
        """Get file path for cached embedding."""
        safe_id = hashlib.md5(character_id.encode()).hexdigest()[:16]
        return os.path.join(self.cache_dir, f"{safe_id}.pt")
    
    def get(self, character_id: str) -> Optional[torch.Tensor]:
        """
        Get cached embedding for character.
        
        Args:
            character_id: Unique character identifier
            
        Returns:
            Cached embedding or None if not found
        """
        # Check memory cache first
        if character_id in self._cache:
            logger.debug(f"Cache hit (memory): {character_id}")
            return self._cache[character_id]
        
        # Check disk cache
        cache_path = self._get_cache_path(character_id)
        if os.path.exists(cache_path):
            try:
                embedding = torch.load(cache_path, map_location="cpu")
                self._cache[character_id] = embedding
                logger.debug(f"Cache hit (disk): {character_id}")
                return embedding
            except Exception as e:
                logger.warning(f"Failed to load cached embedding: {e}")
        
        logger.debug(f"Cache miss: {character_id}")
        return None
    
    def set(
        self,
        character_id: str,
        embedding: torch.Tensor,
        source_image_hash: Optional[str] = None,
    ) -> None:
        """
        Cache embedding for character.
        
        Args:
            character_id: Unique character identifier
            embedding: Identity embedding to cache
            source_image_hash: Optional hash of source image for validation
        """
        # Store in memory
        self._cache[character_id] = embedding
        
        # Store on disk
        cache_path = self._get_cache_path(character_id)
        try:
            torch.save(embedding, cache_path)
            
            # Update metadata
            self._metadata[character_id] = {
                "created_at": datetime.now().isoformat(),
                "embedding_shape": list(embedding.shape),
                "source_hash": source_image_hash,
            }
            self._save_metadata()
            
            logger.info(f"Cached identity for: {character_id}")
        except Exception as e:
            logger.warning(f"Failed to save embedding to disk: {e}")
    
    def delete(self, character_id: str) -> bool:
        """
        Delete cached embedding.
        
        Args:
            character_id: Character identifier to delete
            
        Returns:
            True if deleted, False if not found
        """
        # Remove from memory
        if character_id in self._cache:
            del self._cache[character_id]
        
        # Remove from disk
        cache_path = self._get_cache_path(character_id)
        if os.path.exists(cache_path):
            os.remove(cache_path)
        
        # Update metadata
        if character_id in self._metadata:
            del self._metadata[character_id]
            self._save_metadata()
            return True
        
        return False
    
    def list_cached(self) -> list:
        """List all cached character IDs."""
        return list(self._metadata.keys())
    
    def clear_all(self) -> int:
        """Clear all cached embeddings. Returns count of deleted items."""
        count = len(self._metadata)
        self._cache.clear()
        self._metadata.clear()
        
        # Clear disk cache
        for f in os.listdir(self.cache_dir):
            if f.endswith(".pt"):
                os.remove(os.path.join(self.cache_dir, f))
        
        self._save_metadata()
        logger.info(f"Cleared {count} cached identities")
        return count


# Global cache manager instance
_cache_manager: Optional[IdentityCacheManager] = None


def get_cache_manager() -> IdentityCacheManager:
    """Get the global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = IdentityCacheManager()
    return _cache_manager


class DMV_IdentityCache:
    """
    ComfyUI node for caching and retrieving identity embeddings.
    
    Supports two modes:
    1. Store: Cache an embedding with a character ID
    2. Retrieve: Get cached embedding by character ID
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "character_id": ("STRING", {
                    "default": "character_A",
                    "multiline": False,
                }),
                "mode": (["store", "retrieve", "store_or_retrieve"],),
            },
            "optional": {
                "embedding": ("IDENTITY_EMBEDDING",),
            }
        }
    
    RETURN_TYPES = ("IDENTITY_EMBEDDING", "BOOLEAN", "STRING")
    RETURN_NAMES = ("embedding", "cache_hit", "status")
    FUNCTION = "process_cache"
    CATEGORY = "DirectorMV/Identity"
    
    def process_cache(
        self,
        character_id: str,
        mode: str,
        embedding: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, bool, str]:
        """
        Process identity cache operation.
        
        Args:
            character_id: Unique character identifier
            mode: Operation mode (store, retrieve, store_or_retrieve)
            embedding: Embedding to store (required for store mode)
            
        Returns:
            embedding: Retrieved or stored embedding
            cache_hit: Whether embedding was found in cache
            status: Operation status message
        """
        cache = get_cache_manager()
        
        if mode == "store":
            if embedding is None:
                raise ValueError("Embedding required for store mode")
            
            cache.set(character_id, embedding)
            return (embedding, False, f"Stored identity for: {character_id}")
        
        elif mode == "retrieve":
            cached = cache.get(character_id)
            if cached is not None:
                return (cached, True, f"Retrieved identity for: {character_id}")
            else:
                # Return zero embedding on miss
                zero_emb = torch.zeros(512, dtype=torch.float32)
                return (zero_emb, False, f"Cache miss for: {character_id}")
        
        elif mode == "store_or_retrieve":
            # Try to retrieve first
            cached = cache.get(character_id)
            if cached is not None:
                return (cached, True, f"Retrieved cached identity for: {character_id}")
            
            # If not found and embedding provided, store it
            if embedding is not None:
                cache.set(character_id, embedding)
                return (embedding, False, f"Stored new identity for: {character_id}")
            
            # No cache and no embedding
            zero_emb = torch.zeros(512, dtype=torch.float32)
            return (zero_emb, False, f"No cached or input identity for: {character_id}")
        
        else:
            raise ValueError(f"Unknown mode: {mode}")


class DMV_IdentityCacheManager:
    """
    Node for managing the identity cache (list, clear, delete).
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "action": (["list", "clear_all", "delete"],),
            },
            "optional": {
                "character_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "manage_cache"
    CATEGORY = "DirectorMV/Identity"
    
    def manage_cache(
        self,
        action: str,
        character_id: str = "",
    ) -> Tuple[str]:
        """Manage identity cache."""
        cache = get_cache_manager()
        
        if action == "list":
            cached = cache.list_cached()
            result = f"Cached identities ({len(cached)}):\n" + "\n".join(cached)
        
        elif action == "clear_all":
            count = cache.clear_all()
            result = f"Cleared {count} cached identities"
        
        elif action == "delete":
            if not character_id:
                result = "Error: character_id required for delete"
            elif cache.delete(character_id):
                result = f"Deleted identity: {character_id}"
            else:
                result = f"Identity not found: {character_id}"
        
        else:
            result = f"Unknown action: {action}"
        
        return (result,)

