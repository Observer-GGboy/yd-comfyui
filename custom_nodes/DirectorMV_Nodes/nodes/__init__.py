"""
DirectorMV Nodes - All custom node definitions

Node naming convention: DMV_ prefix (DirectorMV)
"""

from .identity import (
    DMV_IdentityValidator,
    DMV_IdentityCache,
    DMV_IdentityExtractor,
)
from .storyboard import (
    DMV_StoryboardParser,
    DMV_ShotScheduler,
    DMV_CharacterRouter,
)
from .video import (
    DMV_VideoRouter,
    DMV_VideoComposer,
)
from .quality import (
    DMV_QualityGate,
    DMV_RetryController,
)
from .voice import (
    DMV_VoiceClone,
    DMV_TTS,
)
from .transfer import (
    DMV_AttributeTransfer,
    DMV_HairstyleTransfer,
    DMV_ClothingTransfer,
    DMV_ExpressionTransfer,
    DMV_BackgroundTransfer,
)
from .api import (
    DMV_API_Image2Video,
    DMV_API_LipSync,
    DMV_TaskTracker,
)

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
    # API nodes (unified provider abstraction)
    "DMV_API_Image2Video": "DMV API Image2Video",
    "DMV_API_LipSync": "DMV API LipSync",
    "DMV_TaskTracker": "DMV Task Tracker",
}

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
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
    # API (unified provider abstraction)
    "DMV_API_Image2Video",
    "DMV_API_LipSync",
    "DMV_TaskTracker",
]

