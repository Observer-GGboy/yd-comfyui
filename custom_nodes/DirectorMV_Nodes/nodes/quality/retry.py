"""
DMV_RetryController - Control retry logic for failed generations

Implements:
- Configurable retry counts
- Parameter adjustment between retries
- Fallback strategy activation
"""

from typing import Tuple, Dict, Any, Optional, List
import logging
import random

logger = logging.getLogger("DirectorMV.Quality")


class RetryState:
    """Tracks retry state across attempts."""
    
    def __init__(self, max_retries: int = 3):
        self.max_retries = max_retries
        self.current_attempt = 0
        self.history: List[Dict[str, Any]] = []
        self.adjustments: Dict[str, Any] = {}
    
    def record_attempt(self, success: bool, score: float, params: Dict[str, Any]):
        self.history.append({
            "attempt": self.current_attempt,
            "success": success,
            "score": score,
            "params": params.copy(),
        })
        self.current_attempt += 1
    
    def can_retry(self) -> bool:
        return self.current_attempt < self.max_retries
    
    def should_fallback(self) -> bool:
        """Check if we should switch to fallback strategy."""
        return self.current_attempt >= self.max_retries
    
    def get_summary(self) -> str:
        lines = [
            f"Retry State Summary",
            f"===================",
            f"Attempts: {self.current_attempt}/{self.max_retries}",
            f"Can retry: {self.can_retry()}",
            f"Should fallback: {self.should_fallback()}",
            "",
            "History:",
        ]
        for h in self.history:
            status = "✓" if h["success"] else "✗"
            lines.append(f"  {status} Attempt {h['attempt']}: score={h['score']:.3f}")
        
        return "\n".join(lines)


class DMV_RetryController:
    """
    Control retry logic for generation.
    
    Adjusts parameters between retries to improve success rate.
    
    Parameter adjustments per retry:
    - Increase identity strength
    - Reduce creativity/cfg scale
    - Change seed
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "quality_passed": ("BOOLEAN",),
                "quality_score": ("FLOAT",),
            },
            "optional": {
                "max_retries": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 10,
                }),
                "current_attempt": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 10,
                }),
                "identity_strength": ("FLOAT", {
                    "default": 0.8,
                    "min": 0.0,
                    "max": 1.5,
                    "step": 0.05,
                }),
                "cfg_scale": ("FLOAT", {
                    "default": 7.0,
                    "min": 1.0,
                    "max": 20.0,
                    "step": 0.5,
                }),
                "seed": ("INT", {"default": 0}),
                "retry_state": ("RETRY_STATE",),
            }
        }
    
    RETURN_TYPES = ("BOOLEAN", "BOOLEAN", "FLOAT", "FLOAT", "INT", "RETRY_STATE", "STRING")
    RETURN_NAMES = ("should_retry", "should_fallback", "adjusted_identity_strength", "adjusted_cfg", "new_seed", "retry_state", "status")
    FUNCTION = "control_retry"
    CATEGORY = "DirectorMV/Quality"
    
    def control_retry(
        self,
        quality_passed: bool,
        quality_score: float,
        max_retries: int = 3,
        current_attempt: int = 0,
        identity_strength: float = 0.8,
        cfg_scale: float = 7.0,
        seed: int = 0,
        retry_state: Optional[RetryState] = None,
    ) -> Tuple[bool, bool, float, float, int, RetryState, str]:
        """
        Determine retry logic and adjust parameters.
        
        Returns:
            should_retry: Whether to retry generation
            should_fallback: Whether to switch to fallback strategy
            adjusted_identity_strength: Adjusted identity strength
            adjusted_cfg: Adjusted CFG scale
            new_seed: New seed for retry
            retry_state: Updated retry state
            status: Status message
        """
        # Initialize or update retry state
        if retry_state is None:
            retry_state = RetryState(max_retries)
        
        # Record current attempt
        retry_state.record_attempt(
            success=quality_passed,
            score=quality_score,
            params={
                "identity_strength": identity_strength,
                "cfg_scale": cfg_scale,
                "seed": seed,
            }
        )
        
        # If passed, no retry needed
        if quality_passed:
            status = f"Quality passed on attempt {current_attempt + 1}, no retry needed"
            logger.info(status)
            return (False, False, identity_strength, cfg_scale, seed, retry_state, status)
        
        # Check if we can retry
        if not retry_state.can_retry():
            status = f"Max retries ({max_retries}) reached, switching to fallback"
            logger.warning(status)
            return (False, True, identity_strength, cfg_scale, seed, retry_state, status)
        
        # Calculate parameter adjustments
        # Strategy: Each retry increases identity preservation and reduces creativity
        attempt_num = retry_state.current_attempt
        
        # Increase identity strength (up to 1.2)
        adjusted_identity = min(1.2, identity_strength + 0.1 * attempt_num)
        
        # Reduce CFG (more conservative generation)
        adjusted_cfg = max(3.0, cfg_scale - 1.0 * attempt_num)
        
        # Change seed
        new_seed = seed + random.randint(1, 1000000)
        
        status = f"Retry {attempt_num + 1}/{max_retries}: identity={adjusted_identity:.2f}, cfg={adjusted_cfg:.1f}"
        logger.info(status)
        
        return (True, False, adjusted_identity, adjusted_cfg, new_seed, retry_state, status)


class DMV_RetryLoop:
    """
    Helper node for implementing retry loops in workflows.
    
    Works with ComfyUI's loop/iteration system.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "retry_state": ("RETRY_STATE",),
                "should_continue": ("BOOLEAN",),
            },
            "optional": {
                "result": ("*",),  # Any type
            }
        }
    
    RETURN_TYPES = ("BOOLEAN", "INT", "*")
    RETURN_NAMES = ("continue_loop", "iteration", "result_passthrough")
    FUNCTION = "check_loop"
    CATEGORY = "DirectorMV/Quality"
    
    def check_loop(
        self,
        retry_state: RetryState,
        should_continue: bool,
        result = None,
    ) -> Tuple[bool, int, Any]:
        """Check if retry loop should continue."""
        continue_loop = should_continue and retry_state.can_retry()
        iteration = retry_state.current_attempt
        
        return (continue_loop, iteration, result)


class DMV_RetryStateCreate:
    """Create a new retry state object."""
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "max_retries": ("INT", {
                    "default": 3,
                    "min": 1,
                    "max": 10,
                }),
            }
        }
    
    RETURN_TYPES = ("RETRY_STATE",)
    RETURN_NAMES = ("retry_state",)
    FUNCTION = "create_state"
    CATEGORY = "DirectorMV/Quality"
    
    def create_state(self, max_retries: int = 3) -> Tuple[RetryState]:
        return (RetryState(max_retries),)

