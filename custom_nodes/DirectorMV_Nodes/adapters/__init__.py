"""
Adapters for DirectorMV

Bridge existing ComfyUI nodes without modification.
These adapters wrap outputs from existing nodes to provide
unified interfaces for DirectorMV workflows.

IMPORTANT: These adapters do NOT modify any existing nodes.
They only transform/wrap outputs from upstream nodes.
"""

from .pulid_adapter import PuLIDOutputAdapter
from .kling_adapter import KlingAPIAdapter
from .liveportrait_adapter import LivePortraitAdapter
from .video_api_adapter import VideoAPIAdapter

__all__ = [
    "PuLIDOutputAdapter",
    "KlingAPIAdapter",
    "LivePortraitAdapter",
    "VideoAPIAdapter",
]

