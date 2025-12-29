"""
Unified API nodes for DirectorMV

Abstracts away specific providers (Kling, MiniMax, Runway, etc.)
Workflows use DMV_API_* nodes instead of vendor-specific nodes.

Note: Third-party nodes (Kling, MiniMax, etc.) remain in the environment
but are NOT used in DirectorMV main workflows.

Features:
- Multi-provider support (MiniMax, Kling, Runway, Vidu, Local)
- Test modes (test_connect, test_create, test_poll, test_download)
- Structured API logging to JSONL files
- Cost tracking and estimation
"""

import logging

from .task_tracker import DMV_TaskTracker, TaskRecord, get_tracker
from .api_logger import APILogger, get_api_logger

logger = logging.getLogger("DirectorMV.API")


def _build_disabled_node(node_name: str, error: Exception):
    message = f"{node_name} disabled: missing optional dependency ({error})"

    class DisabledNode:
        @classmethod
        def INPUT_TYPES(cls):
            return {
                "required": {
                    "error": ("STRING", {
                        "default": message,
                        "multiline": True,
                        "tooltip": "Install the missing dependency to enable this node.",
                    }),
                }
            }

        RETURN_TYPES = ("STRING",)
        RETURN_NAMES = ("error",)
        FUNCTION = "run"
        CATEGORY = "DirectorMV/API"

        def run(self, error: str):
            raise RuntimeError(error)

    DisabledNode.__name__ = node_name
    return DisabledNode


try:
    from .image2video import DMV_API_Image2Video
except Exception as exc:
    logger.warning("DMV_API_Image2Video import failed: %s", exc)
    DMV_API_Image2Video = _build_disabled_node("DMV_API_Image2Video", exc)

try:
    from .lipsync import DMV_API_LipSync
except Exception as exc:
    logger.warning("DMV_API_LipSync import failed: %s", exc)
    DMV_API_LipSync = _build_disabled_node("DMV_API_LipSync", exc)

__all__ = [
    "DMV_API_Image2Video",
    "DMV_API_LipSync",
    "DMV_TaskTracker",
    "TaskRecord",
    "get_tracker",
    "APILogger",
    "get_api_logger",
]

