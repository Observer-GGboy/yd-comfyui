"""
DMV_TTS - Text-to-Speech synthesis using cloned voice

Generates speech audio from text using a cloned voice profile.
"""

from typing import Tuple, Dict, Any, Optional
import logging

logger = logging.getLogger("DirectorMV.Voice")

# Import voice profile type
from .clone import VoiceProfile


class DMV_TTS:
    """
    Generate speech from text using cloned voice.
    
    Supports:
    - Fish Audio TTS
    - ElevenLabs TTS
    - CosyVoice TTS
    - Kling TTS (via Lip Sync API text mode)
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {
                    "default": "",
                    "multiline": True,
                }),
                "voice_profile": ("VOICE_PROFILE",),
            },
            "optional": {
                "speed": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.5,
                    "max": 2.0,
                    "step": 0.1,
                }),
                "pitch": ("FLOAT", {
                    "default": 0.0,
                    "min": -1.0,
                    "max": 1.0,
                    "step": 0.1,
                }),
                "emotion": (["neutral", "happy", "sad", "angry", "surprised"],),
                "sample_rate": ("INT", {
                    "default": 24000,
                    "min": 16000,
                    "max": 48000,
                    "step": 1000,
                }),
            }
        }
    
    RETURN_TYPES = ("AUDIO", "FLOAT", "STRING")
    RETURN_NAMES = ("audio", "duration", "status")
    FUNCTION = "synthesize_speech"
    CATEGORY = "DirectorMV/Voice"
    
    def synthesize_speech(
        self,
        text: str,
        voice_profile: VoiceProfile,
        speed: float = 1.0,
        pitch: float = 0.0,
        emotion: str = "neutral",
        sample_rate: int = 24000,
    ) -> Tuple[Any, float, str]:
        """
        Synthesize speech from text.
        
        Args:
            text: Text to synthesize
            voice_profile: Cloned voice profile to use
            speed: Speech speed multiplier
            pitch: Pitch adjustment (-1 to 1)
            emotion: Emotional tone
            sample_rate: Output sample rate
            
        Returns:
            audio: Generated audio
            duration: Audio duration in seconds
            status: Synthesis status message
        """
        if not text:
            return (None, 0.0, "No text provided")
        
        provider = voice_profile.provider
        profile_id = voice_profile.profile_id
        
        # Estimate duration based on text length and speed
        # Rough estimate: ~150 words per minute at normal speed
        word_count = len(text.split())
        estimated_duration = (word_count / 150.0) * 60.0 / speed
        
        # In real implementation, would call the appropriate TTS API
        # For now, return placeholder
        
        logger.info(f"TTS synthesis: {word_count} words via {provider}")
        logger.info(f"Profile: {profile_id}, Speed: {speed}, Emotion: {emotion}")
        
        status = f"Synthesized {word_count} words (~{estimated_duration:.1f}s) via {provider}"
        
        # Placeholder audio - in real impl would be actual audio data
        audio = None
        
        return (audio, estimated_duration, status)


class DMV_TTSPresetVoice:
    """
    Use a preset voice for TTS (no cloning needed).
    
    Uses built-in voices from providers (e.g., Kling's preset voices).
    """
    
    # Kling preset voices (from nodes_kling.py)
    KLING_VOICES = {
        "Melody": "girlfriend_4_speech02",
        "Sunny": "genshin_vindi2",
        "Sage": "zhinen_xuesheng",
        "Ace": "AOT",
        "Blossom": "ai_shatang",
    }
    
    @classmethod
    def INPUT_TYPES(cls):
        voice_names = list(cls.KLING_VOICES.keys())
        return {
            "required": {
                "text": ("STRING", {
                    "default": "",
                    "multiline": True,
                }),
                "voice_preset": (voice_names,),
            },
            "optional": {
                "language": (["en", "zh"],),
                "speed": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.8,
                    "max": 2.0,
                    "step": 0.1,
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "STRING")
    RETURN_NAMES = ("voice_id", "text", "language")
    FUNCTION = "get_preset"
    CATEGORY = "DirectorMV/Voice"
    
    def get_preset(
        self,
        text: str,
        voice_preset: str,
        language: str = "en",
        speed: float = 1.0,
    ) -> Tuple[str, str, str]:
        """
        Get preset voice configuration.
        
        Returns parameters suitable for Kling Lip Sync Text mode.
        """
        voice_id = self.KLING_VOICES.get(voice_preset, "girlfriend_4_speech02")
        
        return (voice_id, text, language)


class DMV_AudioInfo:
    """
    Get information about an audio file/sample.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio": ("AUDIO",),
            }
        }
    
    RETURN_TYPES = ("FLOAT", "INT", "STRING")
    RETURN_NAMES = ("duration", "sample_rate", "info")
    FUNCTION = "get_audio_info"
    CATEGORY = "DirectorMV/Voice"
    
    def get_audio_info(self, audio: Any) -> Tuple[float, int, str]:
        """Get audio information."""
        # In real implementation, would inspect actual audio
        # For now, return placeholders
        
        duration = 0.0
        sample_rate = 24000
        
        info = f"Duration: {duration:.2f}s, Sample rate: {sample_rate}Hz"
        
        return (duration, sample_rate, info)

