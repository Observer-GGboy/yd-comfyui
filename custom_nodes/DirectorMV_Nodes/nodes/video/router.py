"""
DMV_VideoRouter - Route video generation to appropriate backend

Routes between:
- Local generation (HunyuanVideo, Wan2.1)
- API generation (Kling, MiniMax, Vidu, Runway)

Implements fallback strategy on failures.
"""

from typing import Tuple, Dict, Any, Optional, List
import torch
import logging

logger = logging.getLogger("DirectorMV.Video")


class VideoGenerationConfig:
    """Configuration for video generation."""
    
    def __init__(
        self,
        strategy: str = "auto",
        duration: float = 5.0,
        resolution: str = "1080p",
        fps: int = 24,
        quality_tier: str = "standard",
        enable_fallback: bool = True,
    ):
        self.strategy = strategy  # auto, local, api_kling, api_minimax, api_vidu, api_runway
        self.duration = duration
        self.resolution = resolution
        self.fps = fps
        self.quality_tier = quality_tier  # draft, standard, high
        self.enable_fallback = enable_fallback


class DMV_VideoRouter:
    """
    Route video generation to appropriate backend.
    
    Routing Strategy (from plan):
    1. Single person, <=10s -> Local (HunyuanVideo)
    2. Dual person -> Kling Dual Character API
    3. High quality -> Runway Gen4
    4. Fallback: Kling -> MiniMax -> Vidu -> Local
    """
    
    # Fallback chain
    FALLBACK_CHAIN = ["api_kling", "api_minimax", "api_vidu", "local"]
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                }),
            },
            "optional": {
                "strategy": (["auto", "local", "api_kling", "api_minimax", "api_vidu", "api_runway"],),
                "duration": ("FLOAT", {
                    "default": 5.0,
                    "min": 2.0,
                    "max": 30.0,
                    "step": 1.0,
                }),
                "quality_tier": (["draft", "standard", "high"],),
                "is_dual_character": ("BOOLEAN", {"default": False}),
                "second_image": ("IMAGE",),
                "enable_fallback": ("BOOLEAN", {"default": True}),
                "negative_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "DICT")
    RETURN_NAMES = ("selected_strategy", "fallback_chain", "generation_config")
    FUNCTION = "route_generation"
    CATEGORY = "DirectorMV/Video"
    
    def route_generation(
        self,
        image: torch.Tensor,
        prompt: str,
        strategy: str = "auto",
        duration: float = 5.0,
        quality_tier: str = "standard",
        is_dual_character: bool = False,
        second_image: Optional[torch.Tensor] = None,
        enable_fallback: bool = True,
        negative_prompt: str = "",
    ) -> Tuple[str, str, Dict[str, Any]]:
        """
        Determine video generation strategy.
        
        Returns:
            selected_strategy: The chosen generation backend
            fallback_chain: Comma-separated fallback options
            generation_config: Full configuration dict
        """
        selected = strategy
        
        if strategy == "auto":
            if is_dual_character or second_image is not None:
                # Dual character - must use Kling Dual API
                selected = "api_dual_kling"
            elif quality_tier == "high":
                # High quality - prefer Runway
                selected = "api_runway"
            elif quality_tier == "draft" or duration <= 5:
                # Draft or short - use local
                selected = "local"
            else:
                # Standard - use Kling API
                selected = "api_kling"
        
        # Build fallback chain
        if enable_fallback:
            fallback_list = []
            start_idx = 0
            
            # Find starting point in fallback chain
            for i, fb in enumerate(self.FALLBACK_CHAIN):
                if fb == selected or selected.replace("api_dual_", "api_") == fb:
                    start_idx = i + 1
                    break
            
            fallback_list = self.FALLBACK_CHAIN[start_idx:]
            fallback_chain = ",".join(fallback_list)
        else:
            fallback_chain = ""
        
        # Build config
        generation_config = {
            "strategy": selected,
            "duration": duration,
            "quality_tier": quality_tier,
            "is_dual": is_dual_character,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "fallback_enabled": enable_fallback,
            "fallback_chain": fallback_chain.split(",") if fallback_chain else [],
        }
        
        logger.info(f"Video routing: {selected}, fallbacks: {fallback_chain}")
        
        return (selected, fallback_chain, generation_config)


class DMV_VideoRouterExecute:
    """
    Execute video generation based on router decision.
    
    This node connects to actual video generation nodes/APIs.
    It acts as a dispatcher, not a generator itself.
    
    Note: Actual generation happens through existing nodes (Kling, MiniMax, etc.)
    via workflow composition. This node provides the routing logic.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "generation_config": ("DICT",),
                "image": ("IMAGE",),
            },
            "optional": {
                "second_image": ("IMAGE",),
                # These would come from upstream generation nodes
                "local_result": ("VIDEO",),
                "kling_result": ("VIDEO",),
                "minimax_result": ("VIDEO",),
                "vidu_result": ("VIDEO",),
                "runway_result": ("VIDEO",),
            }
        }
    
    RETURN_TYPES = ("VIDEO", "STRING", "BOOLEAN")
    RETURN_NAMES = ("video", "source", "success")
    FUNCTION = "select_result"
    CATEGORY = "DirectorMV/Video"
    
    def select_result(
        self,
        generation_config: Dict[str, Any],
        image: torch.Tensor,
        second_image: Optional[torch.Tensor] = None,
        local_result = None,
        kling_result = None,
        minimax_result = None,
        vidu_result = None,
        runway_result = None,
    ):
        """
        Select the appropriate result based on strategy and availability.
        
        Implements fallback logic if primary strategy fails.
        """
        strategy = generation_config.get("strategy", "local")
        fallback_chain = generation_config.get("fallback_chain", [])
        
        # Map strategies to results
        result_map = {
            "local": local_result,
            "api_kling": kling_result,
            "api_dual_kling": kling_result,
            "api_minimax": minimax_result,
            "api_vidu": vidu_result,
            "api_runway": runway_result,
        }
        
        # Try primary strategy
        result = result_map.get(strategy)
        source = strategy
        
        # Try fallbacks if primary failed
        if result is None and fallback_chain:
            for fallback in fallback_chain:
                result = result_map.get(fallback)
                if result is not None:
                    source = f"{fallback} (fallback)"
                    logger.info(f"Using fallback: {fallback}")
                    break
        
        success = result is not None
        
        if not success:
            logger.error(f"All video generation strategies failed")
            source = "none"
        
        return (result, source, success)

