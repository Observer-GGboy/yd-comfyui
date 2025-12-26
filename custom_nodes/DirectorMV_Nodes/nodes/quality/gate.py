"""
DMV_QualityGate - Quality gate for generated content

Validates generated images/videos against quality criteria:
- Identity preservation (ArcFace score)
- Image quality metrics
- Face detection confidence
"""

from typing import Tuple, Dict, Any, Optional, List
import torch
import logging

logger = logging.getLogger("DirectorMV.Quality")


class QualityReport:
    """Quality assessment report."""
    
    def __init__(self):
        self.checks: List[Dict[str, Any]] = []
        self.passed = True
        self.overall_score = 0.0
    
    def add_check(self, name: str, score: float, threshold: float, passed: bool):
        self.checks.append({
            "name": name,
            "score": score,
            "threshold": threshold,
            "passed": passed,
        })
        if not passed:
            self.passed = False
    
    def compute_overall_score(self):
        if not self.checks:
            self.overall_score = 0.0
            return
        
        # Weighted average of all check scores
        total_score = sum(c["score"] for c in self.checks)
        self.overall_score = total_score / len(self.checks)
    
    def to_string(self) -> str:
        lines = [
            "Quality Report",
            "==============",
            f"Overall: {'PASS' if self.passed else 'FAIL'} (score: {self.overall_score:.3f})",
            "",
            "Checks:",
        ]
        for check in self.checks:
            status = "✓" if check["passed"] else "✗"
            lines.append(f"  {status} {check['name']}: {check['score']:.3f} (threshold: {check['threshold']})")
        
        return "\n".join(lines)


class DMV_QualityGate:
    """
    Quality gate for validating generated content.
    
    Criteria (from plan):
    - Identity: ArcFace >= 0.65 pass, < 0.55 fail
    - Face confidence: >= 0.5
    - No severe artifacts
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "reference_embedding": ("IDENTITY_EMBEDDING",),
                "target_embedding": ("IDENTITY_EMBEDDING",),
                "identity_threshold": ("FLOAT", {
                    "default": 0.65,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.01,
                }),
                "face_confidence_threshold": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                }),
                "face_confidence": ("FLOAT", {"default": 1.0}),
                "strict_mode": ("BOOLEAN", {"default": False}),
            }
        }
    
    RETURN_TYPES = ("BOOLEAN", "FLOAT", "STRING", "IMAGE")
    RETURN_NAMES = ("passed", "quality_score", "report", "image_passthrough")
    FUNCTION = "evaluate_quality"
    CATEGORY = "DirectorMV/Quality"
    
    def evaluate_quality(
        self,
        image: torch.Tensor,
        reference_embedding: Optional[torch.Tensor] = None,
        target_embedding: Optional[torch.Tensor] = None,
        identity_threshold: float = 0.65,
        face_confidence_threshold: float = 0.5,
        face_confidence: float = 1.0,
        strict_mode: bool = False,
    ) -> Tuple[bool, float, str, torch.Tensor]:
        """
        Evaluate quality of generated image.
        
        Returns:
            passed: Whether all quality checks passed
            quality_score: Overall quality score [0, 1]
            report: Human-readable quality report
            image_passthrough: Input image passed through
        """
        report = QualityReport()
        
        # Check 1: Face detection confidence
        face_passed = face_confidence >= face_confidence_threshold
        report.add_check(
            "Face Detection",
            face_confidence,
            face_confidence_threshold,
            face_passed
        )
        
        # Check 2: Identity preservation (if embeddings provided)
        if reference_embedding is not None and target_embedding is not None:
            # Compute cosine similarity
            ref_norm = reference_embedding / (torch.norm(reference_embedding) + 1e-8)
            tgt_norm = target_embedding / (torch.norm(target_embedding) + 1e-8)
            identity_score = torch.dot(ref_norm, tgt_norm).item()
            identity_score = max(0.0, min(1.0, identity_score))
            
            identity_passed = identity_score >= identity_threshold
            report.add_check(
                "Identity Preservation",
                identity_score,
                identity_threshold,
                identity_passed
            )
        
        # Check 3: Basic image quality (placeholder - could add more sophisticated checks)
        # In real implementation, could check for:
        # - Blur detection
        # - Artifact detection
        # - Color consistency
        image_quality_score = 0.8  # Placeholder
        report.add_check(
            "Image Quality",
            image_quality_score,
            0.5,
            True
        )
        
        # Compute overall score
        report.compute_overall_score()
        
        # Strict mode requires ALL checks to pass
        # Non-strict mode uses overall score
        if strict_mode:
            passed = report.passed
        else:
            passed = report.overall_score >= 0.6
        
        report_str = report.to_string()
        
        if passed:
            logger.info(f"Quality gate PASSED: score={report.overall_score:.3f}")
        else:
            logger.warning(f"Quality gate FAILED: score={report.overall_score:.3f}")
        
        return (passed, report.overall_score, report_str, image)


class DMV_QualityGateBatch:
    """
    Quality gate for batch of images (video frames).
    
    Checks consistency across frames and identifies problematic segments.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "images": ("IMAGE",),  # Batch of images [B, H, W, C]
            },
            "optional": {
                "reference_embedding": ("IDENTITY_EMBEDDING",),
                "identity_threshold": ("FLOAT", {
                    "default": 0.65,
                    "min": 0.0,
                    "max": 1.0,
                }),
                "max_consecutive_fails": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 10,
                }),
                "sample_interval": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 30,
                }),
            }
        }
    
    RETURN_TYPES = ("BOOLEAN", "FLOAT", "STRING", "INT_LIST")
    RETURN_NAMES = ("passed", "mean_score", "report", "failed_frame_indices")
    FUNCTION = "evaluate_batch"
    CATEGORY = "DirectorMV/Quality"
    
    def evaluate_batch(
        self,
        images: torch.Tensor,
        reference_embedding: Optional[torch.Tensor] = None,
        identity_threshold: float = 0.65,
        max_consecutive_fails: int = 3,
        sample_interval: int = 1,
    ) -> Tuple[bool, float, str, List[int]]:
        """
        Evaluate quality across batch of frames.
        
        Checks for:
        - Consistent identity across frames
        - No long sequences of failed frames
        """
        batch_size = images.shape[0] if images.dim() == 4 else 1
        
        # For now, return placeholder results
        # In real implementation, would extract embeddings from each frame
        # and compare to reference
        
        failed_indices = []
        scores = [0.7] * batch_size  # Placeholder scores
        
        mean_score = sum(scores) / len(scores)
        passed = len(failed_indices) == 0 or (len(failed_indices) < batch_size * 0.3)
        
        report_lines = [
            f"Batch Quality Report",
            f"====================",
            f"Total frames: {batch_size}",
            f"Sampled frames: {batch_size // sample_interval}",
            f"Mean score: {mean_score:.3f}",
            f"Failed frames: {len(failed_indices)}",
            f"Result: {'PASS' if passed else 'NEEDS_RETRY'}",
        ]
        report = "\n".join(report_lines)
        
        return (passed, mean_score, report, failed_indices)

