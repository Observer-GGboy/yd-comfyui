"""
Video utility functions for DirectorMV
"""

from typing import Tuple, Dict, Any, Optional, List
import os
import sys
import shutil
import subprocess
import logging

logger = logging.getLogger("DirectorMV.Utils")


# =============================================================================
# FFmpeg Resolver (Backward-Compatible)
# =============================================================================

class FFmpegResolver:
    """
    Resolve an FFmpeg executable path without relying on system env changes.
    """

    ENV_VAR = "DMV_FFMPEG_PATH"

    def __init__(self) -> None:
        self.search_log: List[str] = []

    def resolve(self) -> Tuple[Optional[str], str]:
        """
        Resolve ffmpeg executable path.

        Returns:
            (path, source) where source is "env_var", "local", or "path".
        """
        # 1) Environment variable override
        env_path = os.environ.get(self.ENV_VAR, "").strip()
        if env_path:
            candidate = self._normalize_candidate(env_path)
            if candidate:
                self.search_log.append(f"env_var:{candidate} (exists)")
                return candidate, "env_var"
            self.search_log.append(f"env_var:{env_path} (missing)")

        # 2) Known local locations (relative to ComfyUI root)
        for candidate in self._local_candidates():
            if os.path.isfile(candidate):
                self.search_log.append(f"local:{candidate} (exists)")
                return candidate, "local"
            self.search_log.append(f"local:{candidate} (missing)")

        # 3) PATH lookup
        which = shutil.which("ffmpeg")
        if which:
            self.search_log.append(f"path:{which} (found)")
            return which, "path"
        self.search_log.append("path:ffmpeg (not found)")

        return None, ""

    def _normalize_candidate(self, path_value: str) -> Optional[str]:
        """Normalize env var input into a usable ffmpeg path."""
        if not path_value:
            return None

        candidate = path_value
        if os.path.isdir(candidate):
            candidate = os.path.join(candidate, "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg")

        if os.path.isfile(candidate):
            return candidate
        return None

    def _local_candidates(self) -> List[str]:
        """Candidate ffmpeg paths relative to ComfyUI root."""
        script_dir = os.path.dirname(os.path.abspath(__file__))
        director_nodes_dir = os.path.dirname(script_dir)
        custom_nodes_dir = os.path.dirname(director_nodes_dir)
        comfyui_dir = os.path.dirname(custom_nodes_dir)

        exe_name = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
        return [
            os.path.join(comfyui_dir, "ffmpeg", exe_name),
            os.path.join(comfyui_dir, "ffmpeg", "bin", exe_name),
            os.path.join(comfyui_dir, "tools", "ffmpeg", "bin", exe_name),
            os.path.join(comfyui_dir, "bin", exe_name),
            os.path.join(comfyui_dir, exe_name),
            os.path.join(director_nodes_dir, "ffmpeg", exe_name),
        ]


def _get_ffmpeg_version(ffmpeg_path: str) -> str:
    """Return the ffmpeg version string, or empty string on failure."""
    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            capture_output=True,
            text=True,
            timeout=5,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        if result.stdout:
            return result.stdout.splitlines()[0].strip()
    except Exception:
        return ""
    return ""


def get_ffmpeg_path() -> str:
    """
    Get a usable ffmpeg path or raise a RuntimeError.
    """
    resolver = FFmpegResolver()
    path, source = resolver.resolve()
    if path:
        return path

    log_tail = "; ".join(resolver.search_log[-5:])
    raise RuntimeError(
        "FFmpeg not found. Set DMV_FFMPEG_PATH or install ffmpeg. "
        f"Search log: {log_tail}"
    )


def check_ffmpeg() -> Dict[str, Any]:
    """
    Check FFmpeg availability and version.
    """
    resolver = FFmpegResolver()
    path, source = resolver.resolve()
    result: Dict[str, Any] = {
        "found": False,
        "path": "",
        "version": "",
        "source": "",
        "error": "",
        "install_instructions": [],
        "search_log": resolver.search_log,
    }

    if path:
        result["found"] = True
        result["path"] = path
        result["version"] = _get_ffmpeg_version(path)
        result["source"] = source
        return result

    if sys.platform == "win32":
        result["install_instructions"] = [
            "Install via winget: winget install Gyan.FFmpeg",
            "Or set DMV_FFMPEG_PATH to your ffmpeg.exe",
        ]
    elif sys.platform == "darwin":
        result["install_instructions"] = [
            "Install via brew: brew install ffmpeg",
            "Or set DMV_FFMPEG_PATH to your ffmpeg binary",
        ]
    else:
        result["install_instructions"] = [
            "Install via package manager (e.g., sudo apt install ffmpeg)",
            "Or set DMV_FFMPEG_PATH to your ffmpeg binary",
        ]

    result["error"] = "ffmpeg not found"
    return result


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

