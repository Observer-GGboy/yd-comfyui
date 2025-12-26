"""
Video utility functions for DirectorMV
"""

from typing import Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger("DirectorMV.Utils")


def estimate_duration(
    word_count: int = 0,
    text: str = "",
    words_per_minute: float = 150.0,
    speed_factor: float = 1.0,
) -> float:
    """
    Estimate audio/video duration from text.
    
    Args:
        word_count: Number of words (if known)
        text: Text content (used if word_count not provided)
        words_per_minute: Average speaking rate
        speed_factor: Speed multiplier
        
    Returns:
        Estimated duration in seconds
    """
    if word_count == 0 and text:
        word_count = len(text.split())
    
    if word_count == 0:
        return 0.0
    
    minutes = word_count / words_per_minute
    seconds = minutes * 60.0
    
    # Apply speed factor
    seconds = seconds / speed_factor
    
    return max(1.0, seconds)  # Minimum 1 second


def get_video_info(video: Any) -> Dict[str, Any]:
    """
    Get information about a video.
    
    Note: Actual implementation depends on video format.
    This provides a basic interface.
    """
    info = {
        "duration": 0.0,
        "width": 0,
        "height": 0,
        "fps": 24.0,
        "frame_count": 0,
        "has_audio": False,
    }
    
    if video is None:
        return info
    
    # Try to extract info based on video type
    if hasattr(video, 'duration'):
        info["duration"] = float(video.duration)
    
    if hasattr(video, 'width'):
        info["width"] = int(video.width)
    
    if hasattr(video, 'height'):
        info["height"] = int(video.height)
    
    if hasattr(video, 'fps'):
        info["fps"] = float(video.fps)
    
    if hasattr(video, 'frame_count'):
        info["frame_count"] = int(video.frame_count)
    elif info["duration"] > 0 and info["fps"] > 0:
        info["frame_count"] = int(info["duration"] * info["fps"])
    
    return info


def calculate_transition_frames(
    transition_type: str,
    transition_duration: float,
    fps: float = 24.0,
) -> Tuple[int, str]:
    """
    Calculate number of frames for a transition.
    
    Args:
        transition_type: Type of transition (cut, fade, dissolve, etc.)
        transition_duration: Duration in seconds
        fps: Frames per second
        
    Returns:
        Tuple of (frame_count, transition_method)
    """
    if transition_type == "cut":
        return (0, "cut")
    
    frame_count = int(transition_duration * fps)
    
    # Determine implementation method
    if transition_type == "fade":
        method = "opacity_blend"
    elif transition_type == "dissolve":
        method = "cross_dissolve"
    elif transition_type == "wipe":
        method = "wipe_mask"
    else:
        method = "cut"
        frame_count = 0
    
    return (frame_count, method)


def validate_aspect_ratio(
    aspect_ratio: str,
    valid_ratios: Optional[list] = None,
) -> Tuple[int, int, bool]:
    """
    Validate and parse aspect ratio string.
    
    Args:
        aspect_ratio: Aspect ratio string (e.g., "16:9")
        valid_ratios: List of valid ratios (None = any valid format)
        
    Returns:
        Tuple of (width_ratio, height_ratio, is_valid)
    """
    valid_ratios = valid_ratios or ["16:9", "9:16", "1:1", "4:3", "3:4"]
    
    try:
        parts = aspect_ratio.split(":")
        if len(parts) != 2:
            return (16, 9, False)
        
        w = int(parts[0])
        h = int(parts[1])
        
        is_valid = aspect_ratio in valid_ratios or valid_ratios is None
        
        return (w, h, is_valid)
    except (ValueError, IndexError):
        return (16, 9, False)


def calculate_dimensions(
    aspect_ratio: str,
    target_resolution: str = "1080p",
) -> Tuple[int, int]:
    """
    Calculate video dimensions from aspect ratio and resolution.
    
    Args:
        aspect_ratio: Aspect ratio string (e.g., "16:9")
        target_resolution: Target resolution (e.g., "1080p", "720p")
        
    Returns:
        Tuple of (width, height)
    """
    resolution_map = {
        "4k": 2160,
        "1080p": 1080,
        "720p": 720,
        "480p": 480,
    }
    
    target_height = resolution_map.get(target_resolution.lower(), 1080)
    
    w_ratio, h_ratio, _ = validate_aspect_ratio(aspect_ratio)
    
    # Calculate dimensions maintaining aspect ratio
    if w_ratio >= h_ratio:
        # Landscape or square
        height = target_height
        width = int(height * w_ratio / h_ratio)
    else:
        # Portrait
        width = target_height
        height = int(width * h_ratio / w_ratio)
    
    # Ensure dimensions are divisible by 8 (for most video codecs)
    width = (width // 8) * 8
    height = (height // 8) * 8
    
    return (width, height)

