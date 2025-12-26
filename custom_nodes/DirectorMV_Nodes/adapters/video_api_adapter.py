"""
VideoAPIAdapter - Unified adapter for multiple video generation APIs

Provides unified interface for:
- Kling
- MiniMax/Hailuo
- Vidu
- Runway

Does NOT modify any API node source code.
"""

from typing import Tuple, Optional, Any, Dict, List
import torch
import logging

logger = logging.getLogger("DirectorMV.Adapters")


class VideoAPIAdapter:
    """
    Unified adapter for video generation APIs.
    
    Normalizes inputs/outputs across different providers for consistent
    DirectorMV workflow integration.
    """
    
    PROVIDERS = ["kling", "minimax", "vidu", "runway", "local"]
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": ("STRING", {"default": "", "multiline": True}),
                "provider": (cls.PROVIDERS,),
            },
            "optional": {
                "negative_prompt": ("STRING", {"default": "", "multiline": True}),
                "duration": ("FLOAT", {
                    "default": 5.0,
                    "min": 2.0,
                    "max": 30.0,
                }),
                "aspect_ratio": (["16:9", "9:16", "1:1"],),
                "second_image": ("IMAGE",),  # For start-end frame
                "cfg_scale": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.0,
                }),
            }
        }
    
    RETURN_TYPES = ("DICT", "STRING")
    RETURN_NAMES = ("api_config", "provider")
    FUNCTION = "prepare_api_call"
    CATEGORY = "DirectorMV/Adapters"
    
    def prepare_api_call(
        self,
        image: torch.Tensor,
        prompt: str,
        provider: str,
        negative_prompt: str = "",
        duration: float = 5.0,
        aspect_ratio: str = "16:9",
        second_image: Optional[torch.Tensor] = None,
        cfg_scale: float = 0.7,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Prepare configuration for video API call.
        
        This creates a unified config dict that can be used with
        provider-specific nodes via workflow routing.
        """
        config = {
            "provider": provider,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio,
            "cfg_scale": cfg_scale,
            "has_start_image": True,
            "has_end_image": second_image is not None,
            "image_shape": list(image.shape) if image is not None else None,
        }
        
        # Provider-specific adjustments
        if provider == "kling":
            config["mode"] = "pro" if duration > 5 else "std"
            config["model_name"] = "kling-v2-master"
        elif provider == "minimax":
            config["model"] = "MiniMax-Hailuo-02"
            config["resolution"] = "1080P" if "1080" in aspect_ratio else "768P"
        elif provider == "vidu":
            config["model"] = "viduq1"
        elif provider == "runway":
            config["model"] = "gen4_turbo"
        
        logger.info(f"Prepared {provider} API config: {duration}s, {aspect_ratio}")
        
        return (config, provider)


class VideoResultAdapter:
    """
    Adapt video generation results from different providers.
    
    Normalizes outputs for consistent downstream processing.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "provider": (VideoAPIAdapter.PROVIDERS,),
            },
            "optional": {
                "video": ("VIDEO",),
                "video_id": ("STRING", {"default": ""}),
                "duration": ("STRING", {"default": ""}),
                "error": ("STRING", {"default": ""}),
            }
        }
    
    RETURN_TYPES = ("VIDEO", "BOOLEAN", "FLOAT", "STRING")
    RETURN_NAMES = ("video", "success", "duration", "status")
    FUNCTION = "adapt_result"
    CATEGORY = "DirectorMV/Adapters"
    
    def adapt_result(
        self,
        provider: str,
        video: Optional[Any] = None,
        video_id: str = "",
        duration: str = "",
        error: str = "",
    ) -> Tuple[Any, bool, float, str]:
        """Adapt video generation result."""
        success = video is not None and not error
        
        # Parse duration
        try:
            duration_float = float(duration) if duration else 0.0
        except ValueError:
            duration_float = 0.0
        
        if success:
            status = f"Success: {provider} generated {duration_float}s video"
            if video_id:
                status += f" (id: {video_id})"
        else:
            status = f"Failed: {provider} - {error or 'Unknown error'}"
        
        return (video, success, duration_float, status)


class VideoFallbackRouter:
    """
    Route to fallback provider on failure.
    
    Implements the fallback chain: Kling -> MiniMax -> Vidu -> Local
    """
    
    FALLBACK_CHAIN = ["kling", "minimax", "vidu", "local"]
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "primary_success": ("BOOLEAN",),
                "current_provider": ("STRING",),
            },
            "optional": {
                "api_config": ("DICT",),
            }
        }
    
    RETURN_TYPES = ("BOOLEAN", "STRING", "DICT")
    RETURN_NAMES = ("use_fallback", "next_provider", "updated_config")
    FUNCTION = "route_fallback"
    CATEGORY = "DirectorMV/Adapters"
    
    def route_fallback(
        self,
        primary_success: bool,
        current_provider: str,
        api_config: Optional[Dict] = None,
    ) -> Tuple[bool, str, Dict]:
        """Determine if fallback is needed and which provider to use."""
        if primary_success:
            return (False, current_provider, api_config or {})
        
        # Find next provider in chain
        try:
            current_idx = self.FALLBACK_CHAIN.index(current_provider)
            next_idx = current_idx + 1
        except ValueError:
            next_idx = 0
        
        if next_idx >= len(self.FALLBACK_CHAIN):
            # No more fallbacks
            return (False, "none", api_config or {})
        
        next_provider = self.FALLBACK_CHAIN[next_idx]
        
        # Update config for new provider
        updated_config = (api_config or {}).copy()
        updated_config["provider"] = next_provider
        updated_config["is_fallback"] = True
        updated_config["original_provider"] = current_provider
        
        logger.info(f"Falling back from {current_provider} to {next_provider}")
        
        return (True, next_provider, updated_config)


class DMV_VideoAPIAdapter(VideoAPIAdapter):
    """ComfyUI node wrapper."""
    pass


class DMV_VideoResultAdapter(VideoResultAdapter):
    """ComfyUI node wrapper."""
    pass


class DMV_VideoFallbackRouter(VideoFallbackRouter):
    """ComfyUI node wrapper."""
    pass

