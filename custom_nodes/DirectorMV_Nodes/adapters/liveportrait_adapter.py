"""
LivePortraitAdapter - Adapter for AdvancedLivePortrait node outputs

Wraps LivePortrait for expression-driven animation.
Does NOT modify AdvancedLivePortrait source code.
"""

from typing import Tuple, Optional, Any, Dict
import torch
import logging

logger = logging.getLogger("DirectorMV.Adapters")


class LivePortraitAdapter:
    """
    Adapter for AdvancedLivePortrait node.
    
    Provides:
    - Expression transfer preparation
    - Lip sync coordination
    - Output normalization
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "source_image": ("IMAGE",),
            },
            "optional": {
                "driving_video": ("VIDEO",),
                "driving_audio": ("AUDIO",),
                "expression_params": ("DICT",),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "VIDEO", "DICT")
    RETURN_NAMES = ("prepared_source", "driving_video", "expression_config")
    FUNCTION = "prepare_liveportrait"
    CATEGORY = "DirectorMV/Adapters"
    
    def prepare_liveportrait(
        self,
        source_image: torch.Tensor,
        driving_video: Optional[Any] = None,
        driving_audio: Optional[Any] = None,
        expression_params: Optional[Dict] = None,
    ) -> Tuple[torch.Tensor, Any, Dict]:
        """
        Prepare inputs for LivePortrait.
        
        LivePortrait expects:
        - Source image with clear face
        - Driving video OR expression parameters
        """
        # Build expression config
        config = expression_params or {}
        
        if driving_audio is not None:
            config["mode"] = "audio_driven"
            config["has_audio"] = True
        elif driving_video is not None:
            config["mode"] = "video_driven"
            config["has_video"] = True
        else:
            config["mode"] = "expression_params"
        
        logger.debug(f"LivePortrait prepared: mode={config.get('mode')}")
        
        return (source_image, driving_video, config)


class LivePortraitExpressionAdapter:
    """
    Adapter for LivePortrait expression editing.
    
    Converts high-level expression descriptions to LivePortrait parameters.
    """
    
    # Expression parameter mappings
    EXPRESSION_PRESETS = {
        "neutral": {"smile": 0.0, "blink": 0.0, "eyebrow": 0.0},
        "happy": {"smile": 0.7, "blink": 0.2, "eyebrow": 0.3},
        "sad": {"smile": -0.3, "blink": 0.3, "eyebrow": -0.4},
        "surprised": {"smile": 0.2, "blink": -0.3, "eyebrow": 0.6},
        "angry": {"smile": -0.4, "blink": 0.1, "eyebrow": -0.5},
        "speaking": {"smile": 0.1, "blink": 0.2, "eyebrow": 0.1},
    }
    
    @classmethod
    def INPUT_TYPES(cls):
        expressions = list(cls.EXPRESSION_PRESETS.keys())
        return {
            "required": {
                "expression": (expressions,),
            },
            "optional": {
                "intensity": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.1,
                }),
                "custom_smile": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0}),
                "custom_blink": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0}),
                "custom_eyebrow": ("FLOAT", {"default": 0.0, "min": -1.0, "max": 1.0}),
            }
        }
    
    RETURN_TYPES = ("DICT", "STRING")
    RETURN_NAMES = ("expression_params", "expression_name")
    FUNCTION = "create_expression"
    CATEGORY = "DirectorMV/Adapters"
    
    def create_expression(
        self,
        expression: str,
        intensity: float = 1.0,
        custom_smile: float = 0.0,
        custom_blink: float = 0.0,
        custom_eyebrow: float = 0.0,
    ) -> Tuple[Dict, str]:
        """
        Create expression parameters for LivePortrait.
        
        Args:
            expression: Preset expression name
            intensity: Expression intensity multiplier
            custom_*: Custom overrides for specific parameters
        """
        # Start with preset
        preset = self.EXPRESSION_PRESETS.get(expression, self.EXPRESSION_PRESETS["neutral"])
        
        # Apply intensity
        params = {k: v * intensity for k, v in preset.items()}
        
        # Apply custom overrides (only if non-zero)
        if custom_smile != 0.0:
            params["smile"] = custom_smile
        if custom_blink != 0.0:
            params["blink"] = custom_blink
        if custom_eyebrow != 0.0:
            params["eyebrow"] = custom_eyebrow
        
        # Clamp values
        params = {k: max(-1.0, min(1.0, v)) for k, v in params.items()}
        
        return (params, expression)


class DMV_LivePortraitAdapter(LivePortraitAdapter):
    """ComfyUI node wrapper."""
    pass


class DMV_LivePortraitExpressionAdapter(LivePortraitExpressionAdapter):
    """ComfyUI node wrapper."""
    pass

