"""
DirectorMV Nodes - All custom node definitions

Node naming convention: DMV_ prefix (DirectorMV)
"""

import logging

logger = logging.getLogger("DirectorMV.Nodes")


def _build_disabled_node(node_name: str, error: Exception, category: str):
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
        CATEGORY = category

        def run(self, error: str):
            raise RuntimeError(error)

    DisabledNode.__name__ = node_name
    return DisabledNode


try:
    from .identity import (
        DMV_IdentityValidator,
        DMV_IdentityCache,
        DMV_IdentityExtractor,
    )
except Exception as exc:
    logger.warning("DirectorMV identity nodes import failed: %s", exc)
    DMV_IdentityValidator = _build_disabled_node("DMV_IdentityValidator", exc, "DirectorMV/Identity")
    DMV_IdentityCache = _build_disabled_node("DMV_IdentityCache", exc, "DirectorMV/Identity")
    DMV_IdentityExtractor = _build_disabled_node("DMV_IdentityExtractor", exc, "DirectorMV/Identity")

try:
    from .storyboard import (
        DMV_StoryboardParser,
        DMV_ShotScheduler,
        DMV_CharacterRouter,
    )
except Exception as exc:
    logger.warning("DirectorMV storyboard nodes import failed: %s", exc)
    DMV_StoryboardParser = _build_disabled_node("DMV_StoryboardParser", exc, "DirectorMV/Storyboard")
    DMV_ShotScheduler = _build_disabled_node("DMV_ShotScheduler", exc, "DirectorMV/Storyboard")
    DMV_CharacterRouter = _build_disabled_node("DMV_CharacterRouter", exc, "DirectorMV/Storyboard")

try:
    from .video import (
        DMV_VideoRouter,
        DMV_VideoComposer,
    )
except Exception as exc:
    logger.warning("DirectorMV video nodes import failed: %s", exc)
    DMV_VideoRouter = _build_disabled_node("DMV_VideoRouter", exc, "DirectorMV/Video")
    DMV_VideoComposer = _build_disabled_node("DMV_VideoComposer", exc, "DirectorMV/Video")

try:
    from .quality import (
        DMV_QualityGate,
        DMV_RetryController,
    )
except Exception as exc:
    logger.warning("DirectorMV quality nodes import failed: %s", exc)
    DMV_QualityGate = _build_disabled_node("DMV_QualityGate", exc, "DirectorMV/Quality")
    DMV_RetryController = _build_disabled_node("DMV_RetryController", exc, "DirectorMV/Quality")

try:
    from .voice import (
        DMV_VoiceClone,
        DMV_TTS,
    )
except Exception as exc:
    logger.warning("DirectorMV voice nodes import failed: %s", exc)
    DMV_VoiceClone = _build_disabled_node("DMV_VoiceClone", exc, "DirectorMV/Voice")
    DMV_TTS = _build_disabled_node("DMV_TTS", exc, "DirectorMV/Voice")

try:
    from .transfer import (
        DMV_AttributeTransfer,
        DMV_HairstyleTransfer,
        DMV_ClothingTransfer,
        DMV_ExpressionTransfer,
        DMV_BackgroundTransfer,
        DMV_PreflightPortrait,
        DMV_ApplyHairTransfer,
        DMV_ApplyOutfitTransfer,
        DMV_ExtractHairPatch,
        DMV_VtonStatusText,
    )
except Exception as exc:
    logger.warning("DirectorMV transfer nodes import failed: %s", exc)
    DMV_AttributeTransfer = _build_disabled_node("DMV_AttributeTransfer", exc, "DirectorMV/Transfer")
    DMV_HairstyleTransfer = _build_disabled_node("DMV_HairstyleTransfer", exc, "DirectorMV/Transfer")
    DMV_ClothingTransfer = _build_disabled_node("DMV_ClothingTransfer", exc, "DirectorMV/Transfer")
    DMV_ExpressionTransfer = _build_disabled_node("DMV_ExpressionTransfer", exc, "DirectorMV/Transfer")
    DMV_BackgroundTransfer = _build_disabled_node("DMV_BackgroundTransfer", exc, "DirectorMV/Transfer")
    DMV_PreflightPortrait = _build_disabled_node("DMV_PreflightPortrait", exc, "DirectorMV/Portrait")
    DMV_ApplyHairTransfer = _build_disabled_node("DMV_ApplyHairTransfer", exc, "DirectorMV/Portrait")
    DMV_ApplyOutfitTransfer = _build_disabled_node("DMV_ApplyOutfitTransfer", exc, "DirectorMV/Portrait")
    DMV_ExtractHairPatch = _build_disabled_node("DMV_ExtractHairPatch", exc, "DirectorMV/Portrait")
    DMV_VtonStatusText = _build_disabled_node("DMV_VtonStatusText", exc, "DirectorMV/Portrait")

try:
    from .api import (
        DMV_API_Image2Video,
        DMV_API_LipSync,
        DMV_TaskTracker,
    )
except Exception as exc:
    logger.warning("DirectorMV API nodes import failed: %s", exc)
    DMV_API_Image2Video = _build_disabled_node("DMV_API_Image2Video", exc, "DirectorMV/API")
    DMV_API_LipSync = _build_disabled_node("DMV_API_LipSync", exc, "DirectorMV/API")
    DMV_TaskTracker = _build_disabled_node("DMV_TaskTracker", exc, "DirectorMV/API")

try:
    from .api.config_nodes import (
        CONFIG_NODE_CLASS_MAPPINGS,
        CONFIG_NODE_DISPLAY_NAME_MAPPINGS,
    )
except Exception as exc:
    logger.warning("DirectorMV config nodes import failed: %s", exc)
    CONFIG_NODE_CLASS_MAPPINGS = {}
    CONFIG_NODE_DISPLAY_NAME_MAPPINGS = {}

# ComfyUI Node Registration
NODE_CLASS_MAPPINGS = {
    # Identity nodes
    "DMV_IdentityValidator": DMV_IdentityValidator,
    "DMV_IdentityCache": DMV_IdentityCache,
    "DMV_IdentityExtractor": DMV_IdentityExtractor,
    # Storyboard nodes
    "DMV_StoryboardParser": DMV_StoryboardParser,
    "DMV_ShotScheduler": DMV_ShotScheduler,
    "DMV_CharacterRouter": DMV_CharacterRouter,
    # Video nodes
    "DMV_VideoRouter": DMV_VideoRouter,
    "DMV_VideoComposer": DMV_VideoComposer,
    # Quality nodes
    "DMV_QualityGate": DMV_QualityGate,
    "DMV_RetryController": DMV_RetryController,
    # Voice nodes
    "DMV_VoiceClone": DMV_VoiceClone,
    "DMV_TTS": DMV_TTS,
    # Transfer nodes
    "DMV_AttributeTransfer": DMV_AttributeTransfer,
    "DMV_HairstyleTransfer": DMV_HairstyleTransfer,
    "DMV_ClothingTransfer": DMV_ClothingTransfer,
    "DMV_ExpressionTransfer": DMV_ExpressionTransfer,
    "DMV_BackgroundTransfer": DMV_BackgroundTransfer,
    # Portrait pipeline nodes
    "DMV_PreflightPortrait": DMV_PreflightPortrait,
    "DMV_ApplyHairTransfer": DMV_ApplyHairTransfer,
    "DMV_ApplyOutfitTransfer": DMV_ApplyOutfitTransfer,
    "DMV_ExtractHairPatch": DMV_ExtractHairPatch,
    "DMV_VtonStatusText": DMV_VtonStatusText,
    # API nodes (unified provider abstraction)
    "DMV_API_Image2Video": DMV_API_Image2Video,
    "DMV_API_LipSync": DMV_API_LipSync,
    "DMV_TaskTracker": DMV_TaskTracker,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    # Identity nodes
    "DMV_IdentityValidator": "DMV Identity Validator",
    "DMV_IdentityCache": "DMV Identity Cache",
    "DMV_IdentityExtractor": "DMV Identity Extractor",
    # Storyboard nodes
    "DMV_StoryboardParser": "DMV Storyboard Parser",
    "DMV_ShotScheduler": "DMV Shot Scheduler",
    "DMV_CharacterRouter": "DMV Character Router",
    # Video nodes
    "DMV_VideoRouter": "DMV Video Router",
    "DMV_VideoComposer": "DMV Video Composer",
    # Quality nodes
    "DMV_QualityGate": "DMV Quality Gate",
    "DMV_RetryController": "DMV Retry Controller",
    # Voice nodes
    "DMV_VoiceClone": "DMV Voice Clone",
    "DMV_TTS": "DMV TTS",
    # Transfer nodes
    "DMV_AttributeTransfer": "DMV Attribute Transfer",
    "DMV_HairstyleTransfer": "DMV Hairstyle Transfer",
    "DMV_ClothingTransfer": "DMV Clothing Transfer",
    "DMV_ExpressionTransfer": "DMV Expression Transfer",
    "DMV_BackgroundTransfer": "DMV Background Transfer",
    "DMV_PreflightPortrait": "DMV Preflight Portrait",
    "DMV_ApplyHairTransfer": "DMV Apply Hair Transfer",
    "DMV_ApplyOutfitTransfer": "DMV Apply Outfit Transfer",
    "DMV_ExtractHairPatch": "DMV Extract Hair Patch",
    "DMV_VtonStatusText": "DMV VTON Status Text",
    # API nodes (unified provider abstraction)
    "DMV_API_Image2Video": "DMV API Image2Video",
    "DMV_API_LipSync": "DMV API LipSync",
    "DMV_TaskTracker": "DMV Task Tracker",
}

NODE_CLASS_MAPPINGS.update(CONFIG_NODE_CLASS_MAPPINGS)
NODE_DISPLAY_NAME_MAPPINGS.update(CONFIG_NODE_DISPLAY_NAME_MAPPINGS)

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "CONFIG_NODE_CLASS_MAPPINGS",
    "CONFIG_NODE_DISPLAY_NAME_MAPPINGS",
    # Identity
    "DMV_IdentityValidator",
    "DMV_IdentityCache",
    "DMV_IdentityExtractor",
    # Storyboard
    "DMV_StoryboardParser",
    "DMV_ShotScheduler",
    "DMV_CharacterRouter",
    # Video
    "DMV_VideoRouter",
    "DMV_VideoComposer",
    # Quality
    "DMV_QualityGate",
    "DMV_RetryController",
    # Voice
    "DMV_VoiceClone",
    "DMV_TTS",
    # Transfer
    "DMV_AttributeTransfer",
    "DMV_HairstyleTransfer",
    "DMV_ClothingTransfer",
    "DMV_ExpressionTransfer",
    "DMV_BackgroundTransfer",
    "DMV_PreflightPortrait",
    "DMV_ApplyHairTransfer",
    "DMV_ApplyOutfitTransfer",
    "DMV_ExtractHairPatch",
    "DMV_VtonStatusText",
    # API (unified provider abstraction)
    "DMV_API_Image2Video",
    "DMV_API_LipSync",
    "DMV_TaskTracker",
]

