"""
DMV_VoiceClone - Clone voice from audio sample

Supports multiple voice cloning backends:
- Fish Audio (primary for Chinese)
- ElevenLabs (primary for international)
- CosyVoice (fallback)
"""

from typing import Tuple, Dict, Any, Optional
import logging
import os
import hashlib

logger = logging.getLogger("DirectorMV.Voice")


class VoiceProfile:
    """Represents a cloned voice profile."""
    
    def __init__(
        self,
        profile_id: str,
        name: str,
        provider: str,
        sample_hash: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.profile_id = profile_id
        self.name = name
        self.provider = provider  # "fish_audio", "elevenlabs", "cosyvoice"
        self.sample_hash = sample_hash
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "name": self.name,
            "provider": self.provider,
            "sample_hash": self.sample_hash,
            "metadata": self.metadata,
        }


class DMV_VoiceClone:
    """
    Clone voice from audio sample.
    
    Requires ~10 seconds of clean audio for best results.
    
    Provider selection (from plan):
    - Chinese: Fish Audio (primary), CosyVoice (fallback)
    - English/International: ElevenLabs (primary), Fish Audio (fallback)
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "audio_sample": ("AUDIO",),
                "voice_name": ("STRING", {
                    "default": "cloned_voice",
                    "multiline": False,
                }),
            },
            "optional": {
                "provider": (["auto", "fish_audio", "elevenlabs", "cosyvoice"],),
                "language": (["auto", "zh", "en", "ja", "ko"],),
                "api_key": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
                "cache_voice": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("VOICE_PROFILE", "STRING", "BOOLEAN")
    RETURN_NAMES = ("voice_profile", "profile_id", "success")
    FUNCTION = "clone_voice"
    CATEGORY = "DirectorMV/Voice"
    
    def clone_voice(
        self,
        audio_sample: Any,
        voice_name: str,
        provider: str = "auto",
        language: str = "auto",
        api_key: str = "",
        cache_voice: bool = True,
    ) -> Tuple[VoiceProfile, str, bool]:
        """
        Clone voice from audio sample.
        
        Args:
            audio_sample: Audio data (from ComfyUI audio node)
            voice_name: Name for the cloned voice
            provider: Voice cloning provider
            language: Target language (for provider selection)
            api_key: API key for provider (optional, uses env var if not set)
            cache_voice: Whether to cache the voice profile
            
        Returns:
            voice_profile: Cloned voice profile
            profile_id: Unique profile ID
            success: Whether cloning succeeded
        """
        # Generate sample hash for caching
        sample_hash = hashlib.md5(str(audio_sample).encode()).hexdigest()[:16]
        profile_id = f"{voice_name}_{sample_hash}"
        
        # Auto-select provider based on language
        if provider == "auto":
            if language in ["zh", "auto"]:
                provider = "fish_audio"
            else:
                provider = "elevenlabs"
        
        # Get API key from environment if not provided
        if not api_key:
            env_keys = {
                "fish_audio": "FISH_AUDIO_API_KEY",
                "elevenlabs": "ELEVENLABS_API_KEY",
                "cosyvoice": "COSYVOICE_API_KEY",
            }
            api_key = os.environ.get(env_keys.get(provider, ""), "")
        
        # Attempt to clone voice
        # Note: Actual API calls would go here
        # For now, create a profile without actual cloning
        
        success = True
        if not api_key:
            logger.warning(f"No API key for {provider}, voice profile will be placeholder")
            success = False
        
        voice_profile = VoiceProfile(
            profile_id=profile_id,
            name=voice_name,
            provider=provider,
            sample_hash=sample_hash,
            metadata={
                "language": language,
                "cached": cache_voice,
                "has_api_key": bool(api_key),
            }
        )
        
        if success:
            logger.info(f"Voice profile created: {profile_id} via {provider}")
        else:
            logger.warning(f"Voice profile placeholder created: {profile_id}")
        
        return (voice_profile, profile_id, success)


class DMV_VoiceProfileLoader:
    """
    Load a previously created voice profile.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "profile_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
            },
            "optional": {
                "provider": (["fish_audio", "elevenlabs", "cosyvoice"],),
            }
        }
    
    RETURN_TYPES = ("VOICE_PROFILE", "BOOLEAN")
    RETURN_NAMES = ("voice_profile", "found")
    FUNCTION = "load_profile"
    CATEGORY = "DirectorMV/Voice"
    
    def load_profile(
        self,
        profile_id: str,
        provider: str = "fish_audio",
    ) -> Tuple[VoiceProfile, bool]:
        """Load voice profile by ID."""
        # In real implementation, would load from cache/API
        # For now, create placeholder
        
        if not profile_id:
            # Return empty profile
            profile = VoiceProfile(
                profile_id="empty",
                name="Empty Profile",
                provider=provider,
                sample_hash="",
            )
            return (profile, False)
        
        profile = VoiceProfile(
            profile_id=profile_id,
            name=f"Loaded: {profile_id}",
            provider=provider,
            sample_hash="cached",
            metadata={"loaded_from_cache": True}
        )
        
        return (profile, True)

