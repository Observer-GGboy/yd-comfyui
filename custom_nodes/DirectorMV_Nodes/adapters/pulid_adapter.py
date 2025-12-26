"""
PuLIDOutputAdapter - Adapter for PuLID node outputs

Wraps PuLID outputs to provide unified interface for DirectorMV.
Does NOT modify PuLID source code.
"""

from typing import Tuple, Optional, Any
import torch
import logging

logger = logging.getLogger("DirectorMV.Adapters")


class PuLIDOutputAdapter:
    """
    Adapter for PuLID node outputs.
    
    Extracts and transforms PuLID outputs into DirectorMV-compatible formats.
    
    Usage:
    1. Connect PuLID node output to this adapter
    2. Use adapter outputs in DirectorMV nodes
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "pulid_embedding": ("CONDITIONING",),  # PuLID outputs conditioning
            },
            "optional": {
                "extract_mode": (["full", "face_only", "normalized"],),
            }
        }
    
    RETURN_TYPES = ("IDENTITY_EMBEDDING", "CONDITIONING")
    RETURN_NAMES = ("identity_embedding", "conditioning_passthrough")
    FUNCTION = "adapt_pulid_output"
    CATEGORY = "DirectorMV/Adapters"
    
    @staticmethod
    def extract_embedding(pulid_output: Any) -> torch.Tensor:
        """
        Extract identity embedding from PuLID output.
        
        PuLID outputs conditioning tensors. This extracts the
        face identity component.
        """
        # PuLID conditioning structure varies by version
        # This handles common patterns
        
        if isinstance(pulid_output, torch.Tensor):
            # Direct tensor output
            embedding = pulid_output
        elif isinstance(pulid_output, (list, tuple)):
            # List/tuple of tensors - take first
            if len(pulid_output) > 0:
                embedding = pulid_output[0]
                if isinstance(embedding, (list, tuple)):
                    embedding = embedding[0]
            else:
                embedding = torch.zeros(512)
        elif hasattr(pulid_output, 'get'):
            # Dict-like structure
            embedding = pulid_output.get('embedding', torch.zeros(512))
        else:
            # Unknown format - return zeros
            logger.warning(f"Unknown PuLID output format: {type(pulid_output)}")
            embedding = torch.zeros(512)
        
        # Ensure correct shape
        if embedding.dim() > 1:
            embedding = embedding.flatten()[:512]
        
        if embedding.shape[0] < 512:
            # Pad if necessary
            padded = torch.zeros(512)
            padded[:embedding.shape[0]] = embedding
            embedding = padded
        elif embedding.shape[0] > 512:
            # Truncate
            embedding = embedding[:512]
        
        return embedding
    
    @staticmethod
    def to_identity_token(pulid_output: Any) -> "IdentityToken":
        """Convert PuLID output to DirectorMV IdentityToken format."""
        from ..schemas.identity import IdentityToken
        
        embedding = PuLIDOutputAdapter.extract_embedding(pulid_output)
        
        return IdentityToken(
            embedding=embedding,
            source="pulid",
            confidence=0.9,  # PuLID generally reliable
        )
    
    def adapt_pulid_output(
        self,
        pulid_embedding: Any,
        extract_mode: str = "full",
    ) -> Tuple[torch.Tensor, Any]:
        """
        Adapt PuLID output for DirectorMV use.
        
        Args:
            pulid_embedding: Output from PuLID node (conditioning)
            extract_mode: How to extract the embedding
            
        Returns:
            identity_embedding: Extracted identity embedding
            conditioning_passthrough: Original conditioning for downstream use
        """
        embedding = self.extract_embedding(pulid_embedding)
        
        if extract_mode == "normalized":
            embedding = embedding / (torch.norm(embedding) + 1e-8)
        
        logger.debug(f"Adapted PuLID output: shape={embedding.shape}")
        
        return (embedding, pulid_embedding)


class DMV_PuLIDOutputAdapter(PuLIDOutputAdapter):
    """ComfyUI node wrapper for PuLIDOutputAdapter."""
    pass

