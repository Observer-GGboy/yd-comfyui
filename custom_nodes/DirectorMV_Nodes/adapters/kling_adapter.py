"""
KlingAPIAdapter - Unified adapter for Kling API nodes

Wraps Kling API outputs and provides fallback logic.
Does NOT modify Kling node source code.
"""

from typing import Tuple, Optional, Any, Dict
import logging

logger = logging.getLogger("DirectorMV.Adapters")


class KlingAPIAdapter:
    """
    Adapter for Kling API node outputs.
    
    Provides:
    - Unified interface for different Kling node types
    - Error handling and status extraction
    - Fallback preparation when Kling fails
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {},
            "optional": {
                "video_output": ("VIDEO",),
                "video_id": ("STRING", {"default": ""}),
                "duration": ("STRING", {"default": "5"}),
                "error_message": ("STRING", {"default": ""}),
            }
        }
    
    RETURN_TYPES = ("VIDEO", "BOOLEAN", "STRING", "FLOAT")
    RETURN_NAMES = ("video", "success", "video_id", "duration")
    FUNCTION = "adapt_kling_output"
    CATEGORY = "DirectorMV/Adapters"
    
    def adapt_kling_output(
        self,
        video_output: Optional[Any] = None,
        video_id: str = "",
        duration: str = "5",
        error_message: str = "",
    ) -> Tuple[Any, bool, str, float]:
        """
        Adapt Kling node output.
        
        Args:
            video_output: Video from Kling node
            video_id: Video ID returned by Kling
            duration: Duration string from Kling
            error_message: Any error message
            
        Returns:
            video: Video output (or None if failed)
            success: Whether generation succeeded
            video_id: Cleaned video ID
            duration: Parsed duration as float
        """
        success = video_output is not None and not error_message
        
        # Parse duration
        try:
            duration_float = float(duration)
        except (ValueError, TypeError):
            duration_float = 5.0
        
        if not success:
            logger.warning(f"Kling generation failed: {error_message or 'No video output'}")
        else:
            logger.info(f"Kling generation succeeded: {video_id}, {duration_float}s")
        
        return (video_output, success, video_id, duration_float)


class KlingDualCharacterAdapter:
    """
    Adapter specifically for Kling Dual Character API.
    
    Handles the specific input/output format for dual-person video generation.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image_a": ("IMAGE",),
                "image_b": ("IMAGE",),
            },
            "optional": {
                "effect_scene": (["hug", "kiss", "heart_gesture", "face_swap"],),
                "duration": (["5", "10"],),
            }
        }
    
    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING", "STRING")
    RETURN_NAMES = ("image_left", "image_right", "effect_scene", "duration")
    FUNCTION = "prepare_dual_input"
    CATEGORY = "DirectorMV/Adapters"
    
    def prepare_dual_input(
        self,
        image_a: Any,
        image_b: Any,
        effect_scene: str = "hug",
        duration: str = "5",
    ) -> Tuple[Any, Any, str, str]:
        """
        Prepare inputs for Kling Dual Character node.
        
        Kling expects: image_left, image_right for dual character effects.
        """
        return (image_a, image_b, effect_scene, duration)


class KlingLipSyncAdapter:
    """
    Adapter for Kling Lip Sync API.
    
    Prepares inputs for both audio-driven and text-driven lip sync.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video": ("VIDEO",),
            },
            "optional": {
                "audio": ("AUDIO",),
                "text": ("STRING", {"default": "", "multiline": True}),
                "voice_preset": ("STRING", {"default": "Melody"}),
                "mode": (["audio", "text"],),
            }
        }
    
    RETURN_TYPES = ("VIDEO", "AUDIO", "STRING", "STRING", "STRING")
    RETURN_NAMES = ("video", "audio", "text", "voice_preset", "mode")
    FUNCTION = "prepare_lipsync_input"
    CATEGORY = "DirectorMV/Adapters"
    
    def prepare_lipsync_input(
        self,
        video: Any,
        audio: Optional[Any] = None,
        text: str = "",
        voice_preset: str = "Melody",
        mode: str = "audio",
    ) -> Tuple[Any, Any, str, str, str]:
        """
        Prepare inputs for Kling Lip Sync.
        
        Determines appropriate mode based on inputs.
        """
        # Auto-determine mode if both audio and text provided
        if mode == "audio" and audio is None and text:
            mode = "text"
        elif mode == "text" and not text and audio is not None:
            mode = "audio"
        
        return (video, audio, text, voice_preset, mode)


class DMV_KlingAPIAdapter(KlingAPIAdapter):
    """ComfyUI node wrapper."""
    pass


class DMV_KlingDualCharacterAdapter(KlingDualCharacterAdapter):
    """ComfyUI node wrapper."""
    pass


class DMV_KlingLipSyncAdapter(KlingLipSyncAdapter):
    """ComfyUI node wrapper."""
    pass

