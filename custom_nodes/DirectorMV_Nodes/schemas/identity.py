"""
Identity data schemas for DirectorMV
"""

from typing import Optional, Dict, Any
from dataclasses import dataclass, field
import torch


@dataclass
class IdentityToken:
    """
    Represents an extracted identity for a character.
    
    Contains the embedding and metadata needed for identity-preserving generation.
    """
    embedding: torch.Tensor
    source: str = "unknown"  # "pulid", "arcface", "insightface"
    confidence: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        # Ensure embedding is correct shape
        if self.embedding is not None and self.embedding.numel() > 0:
            if self.embedding.dim() > 1:
                self.embedding = self.embedding.flatten()
            if self.embedding.shape[0] > 512:
                self.embedding = self.embedding[:512]
    
    def normalize(self) -> "IdentityToken":
        """Return a new token with normalized embedding."""
        norm = torch.norm(self.embedding)
        if norm > 1e-8:
            normalized = self.embedding / norm
        else:
            normalized = self.embedding
        
        return IdentityToken(
            embedding=normalized,
            source=self.source,
            confidence=self.confidence,
            metadata=self.metadata.copy(),
        )
    
    def similarity(self, other: "IdentityToken") -> float:
        """Compute cosine similarity with another token."""
        a_norm = self.normalize().embedding
        b_norm = other.normalize().embedding
        
        sim = torch.dot(a_norm, b_norm).item()
        return max(0.0, min(1.0, sim))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (embedding stored as list)."""
        return {
            "embedding": self.embedding.tolist(),
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IdentityToken":
        """Create from dictionary."""
        embedding = torch.tensor(data.get("embedding", [0] * 512), dtype=torch.float32)
        return cls(
            embedding=embedding,
            source=data.get("source", "unknown"),
            confidence=data.get("confidence", 0.0),
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def empty(cls) -> "IdentityToken":
        """Create an empty identity token."""
        return cls(
            embedding=torch.zeros(512, dtype=torch.float32),
            source="empty",
            confidence=0.0,
        )


@dataclass
class IdentityConfig:
    """
    Configuration for identity-preserving generation.
    """
    # Thresholds (from plan)
    pass_threshold: float = 0.65
    warn_threshold: float = 0.60
    fail_threshold: float = 0.55
    
    # Generation parameters
    identity_strength: float = 0.8
    preserve_lighting: bool = True
    preserve_expression: bool = False
    
    # Validation settings
    validate_each_frame: bool = False
    validation_interval: int = 24  # Validate every N frames
    max_consecutive_fails: int = 3
    
    # Retry settings
    auto_retry: bool = True
    max_retries: int = 3
    strength_increment: float = 0.1
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pass_threshold": self.pass_threshold,
            "warn_threshold": self.warn_threshold,
            "fail_threshold": self.fail_threshold,
            "identity_strength": self.identity_strength,
            "preserve_lighting": self.preserve_lighting,
            "preserve_expression": self.preserve_expression,
            "validate_each_frame": self.validate_each_frame,
            "validation_interval": self.validation_interval,
            "max_consecutive_fails": self.max_consecutive_fails,
            "auto_retry": self.auto_retry,
            "max_retries": self.max_retries,
            "strength_increment": self.strength_increment,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IdentityConfig":
        """Create from dictionary."""
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
    
    @classmethod
    def strict(cls) -> "IdentityConfig":
        """Create strict configuration for high identity preservation."""
        return cls(
            pass_threshold=0.70,
            fail_threshold=0.60,
            identity_strength=1.0,
            validate_each_frame=True,
            validation_interval=1,
        )
    
    @classmethod
    def relaxed(cls) -> "IdentityConfig":
        """Create relaxed configuration for more creative freedom."""
        return cls(
            pass_threshold=0.55,
            fail_threshold=0.45,
            identity_strength=0.6,
            validate_each_frame=False,
        )

