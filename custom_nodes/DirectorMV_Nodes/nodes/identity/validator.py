"""
DMV_IdentityValidator - Validate identity consistency between images

Computes ArcFace similarity between reference and target embeddings.
Used to validate that generated images maintain identity consistency.
"""

import torch
import numpy as np
from typing import Tuple, Dict, Any
import logging

logger = logging.getLogger("DirectorMV.Identity")


class DMV_IdentityValidator:
    """
    Validate identity consistency by comparing embeddings.
    
    Computes cosine similarity between reference and target identity embeddings.
    Returns pass/fail status based on configurable threshold.
    
    Acceptance Criteria (from plan):
    - ArcFace similarity >= 0.65 for pass
    - ArcFace similarity < 0.55 for 3+ consecutive frames = must retry
    """
    
    # Default thresholds from plan
    PASS_THRESHOLD = 0.65
    WARN_THRESHOLD = 0.60
    FAIL_THRESHOLD = 0.55
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_embedding": ("IDENTITY_EMBEDDING",),
                "target_embedding": ("IDENTITY_EMBEDDING",),
            },
            "optional": {
                "pass_threshold": ("FLOAT", {
                    "default": 0.65,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "display": "slider",
                }),
                "fail_threshold": ("FLOAT", {
                    "default": 0.55,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                    "display": "slider",
                }),
            }
        }
    
    RETURN_TYPES = ("FLOAT", "BOOLEAN", "STRING")
    RETURN_NAMES = ("similarity", "passed", "status")
    FUNCTION = "validate_identity"
    CATEGORY = "DirectorMV/Identity"
    
    def validate_identity(
        self,
        reference_embedding: torch.Tensor,
        target_embedding: torch.Tensor,
        pass_threshold: float = 0.65,
        fail_threshold: float = 0.55,
    ) -> Tuple[float, bool, str]:
        """
        Validate identity by computing cosine similarity.
        
        Args:
            reference_embedding: Reference identity embedding [512]
            target_embedding: Target identity embedding to validate [512]
            pass_threshold: Similarity threshold for passing
            fail_threshold: Similarity threshold below which is definite fail
            
        Returns:
            similarity: Cosine similarity score [0, 1]
            passed: Whether validation passed
            status: Human-readable status string
        """
        # Ensure embeddings are normalized
        ref_norm = reference_embedding / (torch.norm(reference_embedding) + 1e-8)
        tgt_norm = target_embedding / (torch.norm(target_embedding) + 1e-8)
        
        # Compute cosine similarity
        similarity = torch.dot(ref_norm, tgt_norm).item()
        
        # Clamp to valid range
        similarity = max(0.0, min(1.0, similarity))
        
        # Determine status
        if similarity >= pass_threshold:
            passed = True
            status = f"PASS: Identity match {similarity:.3f} >= {pass_threshold}"
            logger.info(status)
        elif similarity >= fail_threshold:
            passed = False
            status = f"WARN: Identity marginal {similarity:.3f} (threshold: {pass_threshold})"
            logger.warning(status)
        else:
            passed = False
            status = f"FAIL: Identity mismatch {similarity:.3f} < {fail_threshold}"
            logger.error(status)
        
        return (similarity, passed, status)


class DMV_IdentityBatchValidator:
    """
    Validate identity across a batch of images/frames.
    
    Useful for checking consistency across video frames.
    Reports statistics and identifies frames that need regeneration.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "reference_embedding": ("IDENTITY_EMBEDDING",),
                "target_embeddings": ("IDENTITY_EMBEDDING_LIST",),
            },
            "optional": {
                "pass_threshold": ("FLOAT", {
                    "default": 0.65,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                }),
                "max_consecutive_fails": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 10,
                }),
            }
        }
    
    RETURN_TYPES = ("FLOAT", "FLOAT", "BOOLEAN", "STRING", "INT_LIST")
    RETURN_NAMES = ("mean_similarity", "min_similarity", "all_passed", "report", "failed_indices")
    FUNCTION = "validate_batch"
    CATEGORY = "DirectorMV/Identity"
    
    def validate_batch(
        self,
        reference_embedding: torch.Tensor,
        target_embeddings: list,
        pass_threshold: float = 0.65,
        max_consecutive_fails: int = 3,
    ) -> Tuple[float, float, bool, str, list]:
        """
        Validate identity across multiple frames/images.
        
        Returns statistics and identifies problematic frames.
        """
        ref_norm = reference_embedding / (torch.norm(reference_embedding) + 1e-8)
        
        similarities = []
        failed_indices = []
        consecutive_fails = 0
        has_critical_fail = False
        
        for i, tgt in enumerate(target_embeddings):
            tgt_norm = tgt / (torch.norm(tgt) + 1e-8)
            sim = torch.dot(ref_norm, tgt_norm).item()
            sim = max(0.0, min(1.0, sim))
            similarities.append(sim)
            
            if sim < pass_threshold:
                failed_indices.append(i)
                consecutive_fails += 1
                if consecutive_fails >= max_consecutive_fails:
                    has_critical_fail = True
            else:
                consecutive_fails = 0
        
        mean_sim = np.mean(similarities)
        min_sim = np.min(similarities)
        all_passed = len(failed_indices) == 0
        
        # Build report
        report_lines = [
            f"Batch Identity Validation Report",
            f"================================",
            f"Total frames: {len(target_embeddings)}",
            f"Mean similarity: {mean_sim:.3f}",
            f"Min similarity: {min_sim:.3f}",
            f"Failed frames: {len(failed_indices)}",
            f"Failed indices: {failed_indices[:10]}{'...' if len(failed_indices) > 10 else ''}",
            f"Critical consecutive fail: {has_critical_fail}",
            f"Overall: {'PASS' if all_passed else 'NEEDS_RETRY'}",
        ]
        report = "\n".join(report_lines)
        
        return (mean_sim, min_sim, all_passed, report, failed_indices)

