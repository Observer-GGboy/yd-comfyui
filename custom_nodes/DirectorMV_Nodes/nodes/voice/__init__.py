"""
Voice nodes for DirectorMV

Handles voice cloning and text-to-speech synthesis.
"""

from .clone import DMV_VoiceClone
from .tts import DMV_TTS

__all__ = [
    "DMV_VoiceClone",
    "DMV_TTS",
]

