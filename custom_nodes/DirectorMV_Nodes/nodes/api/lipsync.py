"""
DMV_API_LipSync - Unified Lip Sync node

Abstracts away vendor-specific lip sync APIs.
Supports audio-driven and text-driven lip sync.

Output: video_path (string) for P0.
"""

import os
import time
import httpx
from typing import Tuple, Dict, Any, Optional
from enum import Enum
import logging

from .task_tracker import get_tracker, TaskRecord

logger = logging.getLogger("DirectorMV.API")


class LipSyncProvider(str, Enum):
    AUTO = "auto"
    KLING = "kling"
    LIVEPORTRAIT = "liveportrait"


class LipSyncMode(str, Enum):
    AUDIO = "audio"
    TEXT = "text"


# Provider cost estimates (USD per 10s video)
COST_ESTIMATES = {
    LipSyncProvider.KLING: 0.03,
    LipSyncProvider.LIVEPORTRAIT: 0.0,  # Local
}

# Kling preset voices
KLING_VOICES = {
    "Melody": "girlfriend_4_speech02",
    "Sunny": "genshin_vindi2",
    "Sage": "zhinen_xuesheng",
    "Ace": "AOT",
    "Blossom": "ai_shatang",
}


class DMV_API_LipSync:
    """
    Unified Lip Sync generation.
    
    Supports:
    - Audio-driven: Sync video to provided audio
    - Text-driven: Generate speech and sync
    
    Providers:
    - Kling Lip Sync API (primary)
    - LivePortrait (local fallback)
    
    Output: video_path (string path to synced video file)
    
    Records: task_id, duration, cost, failure reasons via TaskTracker
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "video_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
            },
            "optional": {
                "mode": (["audio", "text"], {
                    "default": "audio",
                }),
                "provider": (["auto", "kling", "liveportrait"], {
                    "default": "auto",
                }),
                "audio_path": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
                "text": ("STRING", {
                    "default": "",
                    "multiline": True,
                }),
                "voice_preset": (["Melody", "Sunny", "Sage", "Ace", "Blossom"], {
                    "default": "Melody",
                }),
                "language": (["en", "zh"], {
                    "default": "en",
                }),
                "enable_fallback": ("BOOLEAN", {
                    "default": True,
                }),
                "api_key_override": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
            }
        }
    
    RETURN_TYPES = ("STRING", "STRING", "FLOAT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("video_path", "task_id", "cost_usd", "status", "success")
    FUNCTION = "sync_lips"
    CATEGORY = "DirectorMV/API"
    
    def sync_lips(
        self,
        video_path: str,
        mode: str = "audio",
        provider: str = "auto",
        audio_path: str = "",
        text: str = "",
        voice_preset: str = "Melody",
        language: str = "en",
        enable_fallback: bool = True,
        api_key_override: str = "",
    ) -> Tuple[str, str, float, str, bool]:
        """
        Apply lip sync to video.
        
        Returns:
            video_path: Path to synced video file (or empty on failure)
            task_id: Unique task ID for tracking
            cost_usd: Actual cost in USD
            status: Status message with details
            success: Whether sync succeeded
        """
        tracker = get_tracker()
        
        # Validate inputs
        if not video_path or not os.path.exists(video_path):
            return ("", "", 0.0, f"Video not found: {video_path}", False)
        
        if mode == "audio" and (not audio_path or not os.path.exists(audio_path)):
            return ("", "", 0.0, f"Audio not found: {audio_path}", False)
        
        if mode == "text" and not text:
            return ("", "", 0.0, "Text is required for text mode", False)
        
        # Determine provider order
        if provider == "auto":
            providers_to_try = [LipSyncProvider.KLING, LipSyncProvider.LIVEPORTRAIT]
        else:
            providers_to_try = [LipSyncProvider(provider)]
            if enable_fallback:
                for p in [LipSyncProvider.KLING, LipSyncProvider.LIVEPORTRAIT]:
                    if p.value != provider and p not in providers_to_try:
                        providers_to_try.append(p)
        
        # Input params for tracking
        input_params = {
            "mode": mode,
            "video_path": os.path.basename(video_path),
            "text_length": len(text) if text else 0,
            "voice_preset": voice_preset if mode == "text" else None,
            "language": language,
        }
        
        # Try each provider
        last_error = ""
        task = None
        
        for p in providers_to_try:
            # Create task
            task = tracker.create_task(
                provider=p.value,
                operation="lipsync",
                input_params=input_params,
            )
            task.estimated_cost_usd = COST_ESTIMATES.get(p, 0.0)
            
            tracker.start_task(task.task_id)
            
            try:
                output_path, provider_task_id = self._sync_with_provider(
                    provider=p,
                    video_path=video_path,
                    mode=mode,
                    audio_path=audio_path,
                    text=text,
                    voice_preset=voice_preset,
                    language=language,
                    api_key=api_key_override,
                )
                
                if output_path and os.path.exists(output_path):
                    # Success
                    cost = COST_ESTIMATES.get(p, 0.0)
                    tracker.complete_task(
                        task_id=task.task_id,
                        output_path=output_path,
                        provider_task_id=provider_task_id,
                        actual_cost_usd=cost,
                    )
                    
                    status = f"Success: {p.value} lip sync complete"
                    logger.info(f"{task.task_id}: {status}")
                    
                    return (output_path, task.task_id, cost, status, True)
                else:
                    raise RuntimeError("No output file generated")
                    
            except Exception as e:
                last_error = str(e)
                tracker.fail_task(
                    task_id=task.task_id,
                    error_message=last_error,
                )
                logger.warning(f"{task.task_id}: Provider {p.value} failed: {last_error}")
                
                if not enable_fallback:
                    break
        
        # All providers failed
        status = f"All providers failed. Last error: {last_error}"
        logger.error(status)
        
        return ("", task.task_id if task else "", 0.0, status, False)
    
    def _sync_with_provider(
        self,
        provider: LipSyncProvider,
        video_path: str,
        mode: str,
        audio_path: str,
        text: str,
        voice_preset: str,
        language: str,
        api_key: str,
    ) -> Tuple[str, str]:
        """
        Call specific provider's lip sync API.
        
        Returns: (output_video_path, provider_task_id)
        """
        if provider == LipSyncProvider.KLING:
            if mode == "audio":
                return self._call_kling_audio(video_path, audio_path, api_key)
            else:
                return self._call_kling_text(video_path, text, voice_preset, 
                                            language, api_key)
        elif provider == LipSyncProvider.LIVEPORTRAIT:
            return self._call_liveportrait(video_path, audio_path)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    def _call_kling_audio(
        self,
        video_path: str,
        audio_path: str,
        api_key: str,
    ) -> Tuple[str, str]:
        """Call Kling Lip Sync API with audio input."""
        api_key = api_key or os.environ.get("KLING_API_KEY", "")
        if not api_key:
            raise ValueError("Kling API key not configured (set KLING_API_KEY env var)")
        
        base_url = "https://api.klingai.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        with httpx.Client(timeout=300) as client:
            # Upload video and audio files
            with open(video_path, "rb") as vf, open(audio_path, "rb") as af:
                files = {
                    "video": (os.path.basename(video_path), vf, "video/mp4"),
                    "audio": (os.path.basename(audio_path), af, "audio/mpeg"),
                }
                
                resp = client.post(
                    f"{base_url}/videos/lip-sync/audio",
                    headers=headers,
                    files=files,
                )
                resp.raise_for_status()
                result = resp.json()
            
            task_id = result.get("data", {}).get("task_id", "")
            
            # Poll for completion
            video_url = self._poll_kling_task(client, base_url, headers, task_id)
            
            # Download result
            output_path = self._download_video(client, video_url, "kling_lipsync", task_id)
            
            return (output_path, task_id)
    
    def _call_kling_text(
        self,
        video_path: str,
        text: str,
        voice_preset: str,
        language: str,
        api_key: str,
    ) -> Tuple[str, str]:
        """Call Kling Lip Sync API with text input."""
        api_key = api_key or os.environ.get("KLING_API_KEY", "")
        if not api_key:
            raise ValueError("Kling API key not configured (set KLING_API_KEY env var)")
        
        base_url = "https://api.klingai.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        voice_id = KLING_VOICES.get(voice_preset, "girlfriend_4_speech02")
        
        with httpx.Client(timeout=300) as client:
            with open(video_path, "rb") as vf:
                files = {
                    "video": (os.path.basename(video_path), vf, "video/mp4"),
                }
                data = {
                    "text": text,
                    "voice_id": voice_id,
                    "voice_language": language,
                }
                
                resp = client.post(
                    f"{base_url}/videos/lip-sync/text",
                    headers=headers,
                    files=files,
                    data=data,
                )
                resp.raise_for_status()
                result = resp.json()
            
            task_id = result.get("data", {}).get("task_id", "")
            
            # Poll for completion
            video_url = self._poll_kling_task(client, base_url, headers, task_id)
            
            # Download result
            output_path = self._download_video(client, video_url, "kling_lipsync", task_id)
            
            return (output_path, task_id)
    
    def _poll_kling_task(
        self,
        client: httpx.Client,
        base_url: str,
        headers: Dict,
        task_id: str,
        max_wait: int = 600,
    ) -> str:
        """Poll Kling lip sync task until completion."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            resp = client.get(
                f"{base_url}/videos/lip-sync/{task_id}",
                headers=headers,
            )
            resp.raise_for_status()
            result = resp.json()
            
            status = result.get("data", {}).get("task_status", "")
            
            if status == "succeed":
                videos = result.get("data", {}).get("task_result", {}).get("videos", [])
                if videos:
                    return videos[0].get("url", "")
                raise RuntimeError("No video URL in successful response")
            
            elif status == "failed":
                error = result.get("data", {}).get("task_status_msg", "Unknown error")
                raise RuntimeError(f"Kling lip sync failed: {error}")
            
            time.sleep(5)
        
        raise TimeoutError(f"Kling lip sync task {task_id} timed out after {max_wait}s")
    
    def _call_liveportrait(
        self,
        video_path: str,
        audio_path: str,
    ) -> Tuple[str, str]:
        """
        Local lip sync using LivePortrait.
        
        Note: Requires ComfyUI-AdvancedLivePortrait to be installed.
        """
        # Would integrate with LivePortrait for local processing
        raise NotImplementedError("LivePortrait lip sync not yet implemented")
    
    def _download_video(
        self,
        client: httpx.Client,
        url: str,
        prefix: str,
        task_id: str,
    ) -> str:
        """Download video from URL to local file."""
        try:
            import folder_paths
            output_dir = folder_paths.get_output_directory()
        except ImportError:
            output_dir = os.path.expanduser("~/comfyui_output")
        
        dmv_output = os.path.join(output_dir, "directormv_videos")
        os.makedirs(dmv_output, exist_ok=True)
        
        filename = f"{prefix}_{task_id}.mp4"
        filepath = os.path.join(dmv_output, filename)
        
        resp = client.get(url)
        resp.raise_for_status()
        
        with open(filepath, "wb") as f:
            f.write(resp.content)
        
        logger.info(f"Downloaded lip sync video to: {filepath}")
        return filepath
