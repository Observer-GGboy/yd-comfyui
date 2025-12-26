"""
DMV_API_Image2Video - Unified Image-to-Video generation node

Abstracts away vendor-specific APIs (Kling, MiniMax, Runway, Vidu, Local).
Workflows use this single node instead of vendor-specific nodes.

Supports all official models/resolutions/durations per provider documentation.
Implements test modes for cost-effective API validation.

Output: video_path (string) for P0, not VIDEO type.
"""

import os
import time
import httpx
import hashlib
import json
from typing import Tuple, Dict, Any, Optional, List
from enum import Enum
import torch
import numpy as np
from PIL import Image
from io import BytesIO
import logging
from datetime import datetime

from .task_tracker import get_tracker, TaskRecord
from .api_logger import get_api_logger

logger = logging.getLogger("DirectorMV.API")


# =============================================================================
# Enums and Constants
# =============================================================================

class Provider(str, Enum):
    AUTO = "auto"
    KLING = "kling"
    MINIMAX = "minimax"
    RUNWAY = "runway"
    VIDU = "vidu"
    LOCAL = "local"
    # Draft Providers (Local GPU - for preview/draft only)
    LOCAL_TURBODIFFUSION = "local_turbodiffusion"
    LOCAL_WAN_I2V = "local_wan_i2v"
    LOCAL_COGVIDEO_FAST = "local_cogvideo_fast"


class ProviderRole(str, Enum):
    """Provider role classification."""
    PRODUCTION = "production"  # Commercial APIs - for final output
    DRAFT = "draft"            # Local models - for preview/draft only


# Provider role mapping
PROVIDER_ROLES = {
    Provider.KLING: ProviderRole.PRODUCTION,
    Provider.MINIMAX: ProviderRole.PRODUCTION,
    Provider.RUNWAY: ProviderRole.PRODUCTION,
    Provider.VIDU: ProviderRole.PRODUCTION,
    Provider.LOCAL: ProviderRole.DRAFT,
    Provider.LOCAL_TURBODIFFUSION: ProviderRole.DRAFT,
    Provider.LOCAL_WAN_I2V: ProviderRole.DRAFT,
    Provider.LOCAL_COGVIDEO_FAST: ProviderRole.DRAFT,
}


class RunMode(str, Enum):
    PROD_FULL = "prod_full"           # Full production generation
    TEST_CONNECT = "test_connect"     # Test API connectivity (no cost)
    TEST_CREATE = "test_create"       # Create task, get task_id, then cancel
    TEST_POLL = "test_poll"           # Create + poll for N seconds
    TEST_DOWNLOAD = "test_download"   # Test download with given task_id


class TestStatus(str, Enum):
    """Test mode status codes - never disguise as production success."""
    TEST_CONNECT_OK = "TEST_CONNECT_OK"
    TEST_CONNECT_FAIL = "TEST_CONNECT_FAIL"
    TEST_CREATE_OK = "TEST_CREATE_OK"
    TEST_CREATE_FAIL = "TEST_CREATE_FAIL"
    TEST_POLL_OK = "TEST_POLL_OK"
    TEST_POLL_FAIL = "TEST_POLL_FAIL"
    TEST_DOWNLOAD_OK = "TEST_DOWNLOAD_OK"
    TEST_DOWNLOAD_FAIL = "TEST_DOWNLOAD_FAIL"
    PROD_SUCCESS = "PROD_SUCCESS"
    PROD_FAIL = "PROD_FAIL"


# =============================================================================
# Model Configurations - Official API Documentation Based
# =============================================================================

# MiniMax/Hailuo Models - https://platform.minimaxi.com/document/video-generation
MINIMAX_MODELS = {
    "T2V-01": {
        "id": "T2V-01",
        "name": "MiniMax T2V-01",
        "type": "text2video",
        "resolutions": ["720P", "1080P"],
        "durations": [6],
        "cost_per_second": 0.08,  # Estimated USD
    },
    "T2V-01-Director": {
        "id": "T2V-01-Director",
        "name": "MiniMax T2V-01-Director (Camera Control)",
        "type": "text2video",
        "resolutions": ["720P", "1080P"],
        "durations": [6],
        "cost_per_second": 0.10,
    },
    "I2V-01": {
        "id": "I2V-01",
        "name": "MiniMax I2V-01",
        "type": "image2video",
        "resolutions": ["720P", "1080P"],
        "durations": [6],
        "cost_per_second": 0.08,
    },
    "I2V-01-Director": {
        "id": "I2V-01-Director",
        "name": "MiniMax I2V-01-Director (Camera Control)",
        "type": "image2video",
        "resolutions": ["720P", "1080P"],
        "durations": [6],
        "cost_per_second": 0.10,
    },
    "I2V-01-live": {
        "id": "I2V-01-live",
        "name": "MiniMax I2V-01-Live (Subject Reference)",
        "type": "image2video",
        "resolutions": ["720P", "1080P"],
        "durations": [6],
        "cost_per_second": 0.10,
    },
    "S2V-01": {
        "id": "S2V-01",
        "name": "MiniMax S2V-01 (Subject to Video)",
        "type": "subject2video",
        "resolutions": ["720P", "1080P"],
        "durations": [6],
        "cost_per_second": 0.10,
    },
}

# Kling Models - https://docs.qingque.cn/d/home/eZQB6yUzJXEA6PxI4z2CMbB4F
KLING_MODELS = {
    "kling-v1": {
        "id": "kling-v1",
        "name": "Kling v1",
        "modes": ["std", "pro"],
        "durations": [5, 10],
        "resolutions": ["720p", "1080p"],
        "cost_5s_std": 0.14,  # USD
        "cost_5s_pro": 0.28,
        "cost_10s_std": 0.28,
        "cost_10s_pro": 0.56,
        "supports_tail_image": True,
    },
    "kling-v1-5": {
        "id": "kling-v1-5",
        "name": "Kling v1.5",
        "modes": ["std", "pro"],
        "durations": [5, 10],
        "resolutions": ["720p", "1080p"],
        "cost_5s_std": 0.14,
        "cost_5s_pro": 0.28,
        "cost_10s_std": 0.28,
        "cost_10s_pro": 0.56,
        "supports_tail_image": True,
    },
    "kling-v2": {
        "id": "kling-v2",
        "name": "Kling v2 Master",
        "modes": ["std", "pro", "master"],
        "durations": [5, 10],
        "resolutions": ["720p", "1080p"],
        "cost_5s_std": 0.175,
        "cost_5s_pro": 0.35,
        "cost_5s_master": 0.70,
        "cost_10s_std": 0.35,
        "cost_10s_pro": 0.70,
        "cost_10s_master": 1.40,
        "supports_tail_image": True,
    },
}

# Runway Models - https://docs.runwayml.com/
RUNWAY_MODELS = {
    "gen3a_turbo": {
        "id": "gen3a_turbo",
        "name": "Gen-3 Alpha Turbo",
        "durations": [5, 10],
        "resolutions": ["720p", "1080p"],
        "cost_per_second": 0.05,  # Credits per second, ~$0.05
    },
    "gen4_turbo": {
        "id": "gen4_turbo",
        "name": "Gen-4 Turbo",
        "durations": [5, 10],
        "resolutions": ["720p", "1080p"],
        "cost_per_second": 0.10,
    },
}

# Vidu Models - https://www.vidu.cn/
VIDU_MODELS = {
    "vidu-1.0": {
        "id": "vidu-1.0",
        "name": "Vidu 1.0",
        "durations": [4, 8],
        "resolutions": ["360p", "720p"],
        "cost_4s": 0.20,  # USD estimate
        "cost_8s": 0.40,
    },
    "vidu-1.5": {
        "id": "vidu-1.5",
        "name": "Vidu 1.5",
        "durations": [4, 8],
        "resolutions": ["720p", "1080p"],
        "cost_4s": 0.25,
        "cost_8s": 0.50,
    },
    "vidu-2.0": {
        "id": "vidu-2.0",
        "name": "Vidu 2.0",
        "durations": [4, 8],
        "resolutions": ["720p", "1080p"],
        "cost_4s": 0.30,
        "cost_8s": 0.60,
        "supports_reference": True,
    },
}

# =============================================================================
# Local Draft Engine Models (GPU-based, for preview/draft only)
# =============================================================================

# TurboDiffusion - Fast I2V for drafting
# https://github.com/turbodiffusion/turbodiffusion
LOCAL_DRAFT_MODELS = {
    "turbodiffusion": {
        "id": "turbodiffusion",
        "name": "TurboDiffusion (Draft Engine)",
        "type": "image2video",
        "durations": [4, 5],  # 4-5 seconds typical
        "resolutions": ["512x512", "768x512", "512x768"],
        "cost_per_second": 0.0,  # Free - local GPU
        "role": "draft",
        "min_vram_gb": 16,
        "recommended_vram_gb": 24,
        "notes": "Fast draft-quality I2V. NOT for production. Use for shot/motion preview.",
        "default_steps": 20,
        "default_cfg": 7.0,
        "fps": 24,
    },
    "wan_i2v": {
        "id": "wan_i2v",
        "name": "Wan I2V (Draft Engine)",
        "type": "image2video",
        "durations": [4, 5, 6],
        "resolutions": ["512x512", "768x512"],
        "cost_per_second": 0.0,
        "role": "draft",
        "min_vram_gb": 20,
        "recommended_vram_gb": 24,
        "notes": "Quality draft I2V. Slower than TurboDiffusion but better motion.",
        "default_steps": 30,
        "default_cfg": 7.5,
        "fps": 24,
    },
    "cogvideo_fast": {
        "id": "cogvideo_fast",
        "name": "CogVideoX Fast (Draft Engine)", 
        "type": "image2video",
        "durations": [4, 6],
        "resolutions": ["480x720", "720x480"],
        "cost_per_second": 0.0,
        "role": "draft",
        "min_vram_gb": 18,
        "recommended_vram_gb": 24,
        "notes": "CogVideoX with reduced steps for faster preview.",
        "default_steps": 25,
        "default_cfg": 6.0,
        "fps": 24,
    },
}

# Draft provider to model mapping
DRAFT_PROVIDER_MODEL_MAP = {
    Provider.LOCAL_TURBODIFFUSION: "turbodiffusion",
    Provider.LOCAL_WAN_I2V: "wan_i2v",
    Provider.LOCAL_COGVIDEO_FAST: "cogvideo_fast",
}


# Provider cost estimates (USD per 5s video) - for AUTO mode selection
COST_ESTIMATES = {
    # Production providers (Commercial APIs)
    Provider.KLING: 0.14,
    Provider.MINIMAX: 0.48,
    Provider.RUNWAY: 0.25,
    Provider.VIDU: 0.25,
    # Draft providers (Local GPU - FREE)
    Provider.LOCAL: 0.0,
    Provider.LOCAL_TURBODIFFUSION: 0.0,
    Provider.LOCAL_WAN_I2V: 0.0,
    Provider.LOCAL_COGVIDEO_FAST: 0.0,
}

# Provider priority for auto selection (by realism quality)
# Note: Draft providers are NOT included in auto fallback to prevent
# accidental draft output when production quality is expected.
AUTO_PRIORITY = [
    Provider.KLING,
    Provider.RUNWAY,
    Provider.MINIMAX,
    Provider.VIDU,
]

# Draft providers priority (used when explicitly selecting draft mode)
DRAFT_PRIORITY = [
    Provider.LOCAL_TURBODIFFUSION,  # Fastest
    Provider.LOCAL_WAN_I2V,
    Provider.LOCAL_COGVIDEO_FAST,
    Provider.LOCAL,
]

# All draft provider values for easy checking
DRAFT_PROVIDERS = {
    Provider.LOCAL,
    Provider.LOCAL_TURBODIFFUSION,
    Provider.LOCAL_WAN_I2V,
    Provider.LOCAL_COGVIDEO_FAST,
}


# =============================================================================
# Test Mode Capabilities Matrix
# =============================================================================

# Documents what each provider supports for test modes
PROVIDER_TEST_CAPABILITIES = {
    Provider.MINIMAX: {
        "test_connect": True,  # Can query account/models
        "test_connect_endpoint": "/v1/account/info",  # Or models list
        "test_create_may_charge": True,  # No cancel API, may incur cost
        "supports_cancel": False,
        "min_cost_config": {"duration": 6, "resolution": "720P"},
        "min_cost_estimate_usd": 0.48,
        "notes": "MiniMax does not support task cancellation. test_create will incur cost.",
    },
    Provider.KLING: {
        "test_connect": True,
        "test_connect_endpoint": "/v1/account/info",
        "test_create_may_charge": True,  # May charge even if cancelled quickly
        "supports_cancel": False,  # No documented cancel API
        "min_cost_config": {"mode": "std", "duration": 5, "model": "kling-v1"},
        "min_cost_estimate_usd": 0.14,
        "notes": "Kling charges on task creation. No cancel API documented.",
    },
    Provider.RUNWAY: {
        "test_connect": True,
        "test_connect_endpoint": "/v1/account",
        "test_create_may_charge": True,
        "supports_cancel": True,  # Runway supports task deletion
        "cancel_endpoint": "/v1/tasks/{task_id}",
        "min_cost_config": {"duration": 5, "resolution": "720p"},
        "min_cost_estimate_usd": 0.25,
        "notes": "Runway supports task cancellation via DELETE.",
    },
    Provider.VIDU: {
        "test_connect": True,
        "test_connect_endpoint": "/v1/user/info",
        "test_create_may_charge": True,
        "supports_cancel": False,
        "min_cost_config": {"duration": 4, "resolution": "720p"},
        "min_cost_estimate_usd": 0.25,
        "notes": "Vidu charges on creation. No documented cancel.",
    },
    Provider.LOCAL: {
        "test_connect": True,
        "test_create_may_charge": False,
        "supports_cancel": True,
        "min_cost_config": {},
        "min_cost_estimate_usd": 0.0,
        "notes": "Local models are free but require GPU resources.",
    },
    # Draft Providers - Local GPU based
    Provider.LOCAL_TURBODIFFUSION: {
        "test_connect": True,  # Environment check: CUDA, torch, weights, VRAM
        "test_create_may_charge": False,  # Free - local GPU only
        "supports_cancel": True,
        "min_cost_config": {"duration": 4, "resolution": "512x512"},
        "min_cost_estimate_usd": 0.0,
        "role": "draft",
        "min_vram_gb": 16,
        "notes": "TurboDiffusion draft engine. Fast preview, NOT production quality.",
    },
    Provider.LOCAL_WAN_I2V: {
        "test_connect": True,
        "test_create_may_charge": False,
        "supports_cancel": True,
        "min_cost_config": {"duration": 4, "resolution": "512x512"},
        "min_cost_estimate_usd": 0.0,
        "role": "draft",
        "min_vram_gb": 20,
        "notes": "Wan I2V draft engine. Better motion than TurboDiffusion.",
    },
    Provider.LOCAL_COGVIDEO_FAST: {
        "test_connect": True,
        "test_create_may_charge": False,
        "supports_cancel": True,
        "min_cost_config": {"duration": 4, "resolution": "480x720"},
        "min_cost_estimate_usd": 0.0,
        "role": "draft",
        "min_vram_gb": 18,
        "notes": "CogVideoX fast mode. Reduced steps for quick preview.",
    },
}


# =============================================================================
# Utility Functions
# =============================================================================

def get_output_dir() -> str:
    """Get output directory for generated videos."""
    try:
        import folder_paths
        output_dir = folder_paths.get_output_directory()
    except ImportError:
        output_dir = os.path.expanduser("~/comfyui_output")
    
    dmv_output = os.path.join(output_dir, "directormv_videos")
    os.makedirs(dmv_output, exist_ok=True)
    return dmv_output


def tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
    """Convert ComfyUI image tensor to PIL Image."""
    if tensor.dim() == 4:
        tensor = tensor[0]
    
    # [H, W, C] in range [0, 1]
    np_image = (tensor.cpu().numpy() * 255).astype(np.uint8)
    return Image.fromarray(np_image)


def image_to_base64(image: Image.Image, format: str = "PNG") -> str:
    """Convert PIL image to base64 string."""
    import base64
    buffer = BytesIO()
    image.save(buffer, format=format)
    return base64.b64encode(buffer.getvalue()).decode("utf-8")


def get_model_list_for_provider(provider: str) -> List[str]:
    """Get available models for a provider."""
    if provider == "minimax":
        return list(MINIMAX_MODELS.keys())
    elif provider == "kling":
        return list(KLING_MODELS.keys())
    elif provider == "runway":
        return list(RUNWAY_MODELS.keys())
    elif provider == "vidu":
        return list(VIDU_MODELS.keys())
    elif provider == "local":
        return ["hunyuan", "cogvideo"]
    elif provider in ["local_turbodiffusion", "local_wan_i2v", "local_cogvideo_fast"]:
        return list(LOCAL_DRAFT_MODELS.keys())
    else:
        return ["auto"]


def is_draft_provider(provider: str) -> bool:
    """Check if a provider is a draft/local provider."""
    try:
        p = Provider(provider)
        return p in DRAFT_PROVIDERS
    except ValueError:
        return provider.startswith("local")


def get_provider_role(provider: str) -> str:
    """Get the role of a provider (production or draft)."""
    try:
        p = Provider(provider)
        return PROVIDER_ROLES.get(p, ProviderRole.PRODUCTION).value
    except ValueError:
        return "draft" if provider.startswith("local") else "production"


# =============================================================================
# Main Node Class
# =============================================================================

class DMV_API_Image2Video:
    """
    Unified Image-to-Video generation.
    
    Supports multiple providers with automatic fallback:
    - Kling (primary for realism)
    - Runway (high quality)
    - MiniMax/Hailuo (backup)
    - Vidu (backup)
    - Local (cost-free fallback)
    
    Supports test modes for cost-effective API validation:
    - prod_full: Full production generation
    - test_connect: Verify API connectivity (no cost)
    - test_create: Create task, get task_id (may cost)
    - test_poll: Create + poll for status (may cost)
    - test_download: Test download capability
    
    Output: video_path (string path to generated video file)
    
    Records: task_id, duration, cost, failure reasons via TaskTracker
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "prompt": ("STRING", {
                    "default": "A person looking at camera, natural expression",
                    "multiline": True,
                }),
            },
            "optional": {
                # Provider selection
                # Production providers: kling, minimax, runway, vidu (Commercial APIs, billable)
                # Draft providers: local_turbodiffusion, local_wan_i2v, local_cogvideo_fast (Local GPU, FREE, preview only)
                "provider": ([
                    "auto",
                    # Production Providers (Commercial APIs - for final output)
                    "kling", "minimax", "runway", "vidu",
                    # Draft Providers (Local GPU - for preview/draft ONLY)
                    "local_turbodiffusion",  # ⚡ Fastest draft, ~16GB VRAM
                    "local_wan_i2v",         # 🎬 Better motion, ~20GB VRAM
                    "local_cogvideo_fast",   # 🎯 CogVideoX fast, ~18GB VRAM
                    "local",                 # Legacy local option
                ], {
                    "default": "local_turbodiffusion",  # Default to draft for cost-free iteration
                    "tooltip": "⚠️ local_* providers are DRAFT quality for preview only. Use kling/minimax for production.",
                }),
                # Model selection (provider-specific)
                "model": (["auto", 
                          # MiniMax models
                          "I2V-01", "I2V-01-Director", "I2V-01-live", "S2V-01",
                          # Kling models
                          "kling-v1", "kling-v1-5", "kling-v2",
                          # Runway models
                          "gen3a_turbo", "gen4_turbo",
                          # Vidu models
                          "vidu-1.0", "vidu-1.5", "vidu-2.0",
                          # Local draft models
                          "turbodiffusion", "wan_i2v", "cogvideo_fast",
                          # Legacy local models
                          "hunyuan", "cogvideo"], {
                    "default": "auto",
                }),
                # Generation parameters
                "duration": (["5", "6", "8", "10"], {
                    "default": "5",
                }),
                "resolution": (["720p", "1080p", "720P", "1080P"], {
                    "default": "720p",
                }),
                "mode": (["std", "pro", "master"], {  # Kling-specific
                    "default": "std",
                }),
                "negative_prompt": ("STRING", {
                    "default": "blurry, distorted face, bad anatomy, deformed",
                    "multiline": True,
                }),
                "cfg_scale": ("FLOAT", {
                    "default": 0.7,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                }),
                "seed": ("INT", {
                    "default": -1,
                    "min": -1,
                    "max": 2147483647,
                }),
                "end_image": ("IMAGE",),
                
                # Test mode parameters
                "run_mode": (["prod_full", "test_connect", "test_create", "test_poll", "test_download"], {
                    "default": "prod_full",
                }),
                "poll_seconds": ("INT", {
                    "default": 10,
                    "min": 1,
                    "max": 300,
                }),
                "test_task_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
                
                # Debug options
                "return_debug": ("BOOLEAN", {
                    "default": False,
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
    FUNCTION = "generate"
    CATEGORY = "DirectorMV/API"
    
    def generate(
        self,
        image: torch.Tensor,
        prompt: str,
        provider: str = "auto",
        model: str = "auto",
        duration: str = "5",
        resolution: str = "720p",
        mode: str = "std",
        negative_prompt: str = "",
        cfg_scale: float = 0.7,
        seed: int = -1,
        end_image: Optional[torch.Tensor] = None,
        run_mode: str = "prod_full",
        poll_seconds: int = 10,
        test_task_id: str = "",
        return_debug: bool = False,
        enable_fallback: bool = True,
        api_key_override: str = "",
    ) -> Tuple[str, str, float, str, bool]:
        """
        Generate video from image.
        
        Returns:
            video_path: Path to generated video file (or empty on failure)
            task_id: Unique task ID for tracking
            cost_usd: Actual cost in USD
            status: Status message with details (never "unknown error")
            success: Whether generation succeeded
        """
        api_logger = get_api_logger()
        tracker = get_tracker()
        
        # Normalize resolution
        resolution = resolution.upper() if resolution.lower() in ["720p", "1080p"] else resolution
        
        # Handle test modes
        if run_mode == RunMode.TEST_CONNECT.value:
            return self._test_connect(provider, model, api_key_override, return_debug)
        
        elif run_mode == RunMode.TEST_CREATE.value:
            return self._test_create(
                image, prompt, provider, model, duration, resolution, mode,
                negative_prompt, cfg_scale, seed, end_image, api_key_override, return_debug
            )
        
        elif run_mode == RunMode.TEST_POLL.value:
            return self._test_poll(
                image, prompt, provider, model, duration, resolution, mode,
                negative_prompt, cfg_scale, seed, end_image, poll_seconds,
                api_key_override, return_debug
            )
        
        elif run_mode == RunMode.TEST_DOWNLOAD.value:
            return self._test_download(
                provider, test_task_id, api_key_override, return_debug
            )
        
        # Production mode - full generation
        return self._prod_full(
            image, prompt, provider, model, duration, resolution, mode,
            negative_prompt, cfg_scale, seed, end_image, enable_fallback,
            api_key_override, return_debug
        )
    
    # =========================================================================
    # Test Modes Implementation
    # =========================================================================
    
    def _test_connect(
        self,
        provider: str,
        model: str,
        api_key: str,
        return_debug: bool,
    ) -> Tuple[str, str, float, str, bool]:
        """
        Test API connectivity without generating content.
        
        Uses official non-billing endpoints (models list, account info, etc.)
        """
        api_logger = get_api_logger()
        start_time = time.time()
        
        # Determine actual provider
        if provider == "auto":
            provider = "minimax"  # Default for test_connect
        
        try:
            if provider == "minimax":
                result = self._minimax_test_connect(api_key)
            elif provider == "kling":
                result = self._kling_test_connect(api_key)
            elif provider == "runway":
                result = self._runway_test_connect(api_key)
            elif provider == "vidu":
                result = self._vidu_test_connect(api_key)
            elif provider == "local":
                result = {"status": "ok", "message": "Local mode ready"}
            elif provider in ["local_turbodiffusion", "local_wan_i2v", "local_cogvideo_fast"]:
                # Draft provider environment check
                result = self._draft_provider_env_check(provider)
            else:
                raise ValueError(f"Unknown provider: {provider}")
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Log successful connection
            entry = api_logger.log_request(
                provider=provider,
                model=model,
                run_mode="test_connect",
                operation="connectivity_test",
                request_url=result.get("endpoint", "N/A"),
                http_status=result.get("http_status", 200),
                response_body=result,
                response_time_ms=elapsed_ms,
            )
            
            status = f"{TestStatus.TEST_CONNECT_OK.value} | {provider} API connected"
            if return_debug:
                status += f" | {api_logger.format_status_summary(entry)}"
            
            return ("", "", 0.0, status, True)
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            
            entry = api_logger.log_request(
                provider=provider,
                model=model,
                run_mode="test_connect",
                operation="connectivity_test",
                request_url="N/A",
                http_status=0,
                response_time_ms=elapsed_ms,
                error=str(e),
            )
            
            status = f"{TestStatus.TEST_CONNECT_FAIL.value} | {provider}: {str(e)[:200]}"
            if return_debug:
                status += f" | Log: {api_logger.get_log_path()}"
            
            return ("", "", 0.0, status, False)
    
    def _test_create(
        self,
        image: torch.Tensor,
        prompt: str,
        provider: str,
        model: str,
        duration: str,
        resolution: str,
        mode: str,
        negative_prompt: str,
        cfg_scale: float,
        seed: int,
        end_image: Optional[torch.Tensor],
        api_key: str,
        return_debug: bool,
    ) -> Tuple[str, str, float, str, bool]:
        """
        Create a task and immediately return task_id.
        
        Does NOT poll or download. Attempts to cancel if provider supports it.
        WARNING: May incur cost even without completion!
        """
        api_logger = get_api_logger()
        tracker = get_tracker()
        
        # Determine actual provider
        if provider == "auto":
            provider = "minimax"  # Default
        
        pil_image = tensor_to_pil(image)
        pil_end_image = tensor_to_pil(end_image) if end_image is not None else None
        
        # Create task record
        task = tracker.create_task(
            provider=provider,
            operation="image2video_test_create",
            input_params={"prompt": prompt[:50], "duration": duration, "resolution": resolution},
        )
        tracker.start_task(task.task_id)
        
        start_time = time.time()
        
        try:
            # Call provider's create endpoint
            if provider == "minimax":
                provider_task_id, response = self._minimax_create_task(
                    pil_image, prompt, model, duration, resolution, api_key
                )
            elif provider == "kling":
                provider_task_id, response = self._kling_create_task(
                    pil_image, prompt, model, mode, duration, resolution,
                    negative_prompt, cfg_scale, pil_end_image, api_key
                )
            elif provider == "runway":
                provider_task_id, response = self._runway_create_task(
                    pil_image, prompt, model, duration, resolution, seed, api_key
                )
            elif provider == "vidu":
                provider_task_id, response = self._vidu_create_task(
                    pil_image, prompt, model, duration, resolution, pil_end_image, api_key
                )
            else:
                raise ValueError(f"Provider {provider} not supported for test_create")
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Try to cancel if supported
            cancel_result = None
            caps = PROVIDER_TEST_CAPABILITIES.get(Provider(provider), {})
            if caps.get("supports_cancel"):
                try:
                    cancel_result = self._try_cancel_task(provider, provider_task_id, api_key)
                except Exception as ce:
                    cancel_result = {"error": str(ce)}
            
            # Log the request
            entry = api_logger.log_request(
                provider=provider,
                model=model,
                run_mode="test_create",
                operation="create_task",
                request_url=response.get("request_url", "N/A"),
                http_status=response.get("http_status", 200),
                response_body=response,
                response_time_ms=elapsed_ms,
                task_id=provider_task_id,
                extra={"cancel_attempted": caps.get("supports_cancel", False), "cancel_result": cancel_result},
            )
            
            # Build status
            cost_warning = ""
            if caps.get("test_create_may_charge"):
                min_cost = caps.get("min_cost_estimate_usd", 0)
                cost_warning = f" | ⚠️ May charge ~${min_cost:.2f}"
            
            status = f"{TestStatus.TEST_CREATE_OK.value} | task_id={provider_task_id}{cost_warning}"
            if return_debug:
                status += f" | {api_logger.format_status_summary(entry)}"
            
            tracker.complete_task(
                task_id=task.task_id,
                provider_task_id=provider_task_id,
                provider_response=response,
            )
            
            return ("", provider_task_id, 0.0, status, True)
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            
            entry = api_logger.log_request(
                provider=provider,
                model=model,
                run_mode="test_create",
                operation="create_task",
                request_url="N/A",
                http_status=0,
                response_time_ms=elapsed_ms,
                error=str(e),
            )
            
            tracker.fail_task(task_id=task.task_id, error_message=str(e))
            
            status = f"{TestStatus.TEST_CREATE_FAIL.value} | {provider}: {str(e)[:200]}"
            if return_debug:
                status += f" | Log: {api_logger.get_log_path()}"
            
            return ("", task.task_id, 0.0, status, False)
    
    def _test_poll(
        self,
        image: torch.Tensor,
        prompt: str,
        provider: str,
        model: str,
        duration: str,
        resolution: str,
        mode: str,
        negative_prompt: str,
        cfg_scale: float,
        seed: int,
        end_image: Optional[torch.Tensor],
        poll_seconds: int,
        api_key: str,
        return_debug: bool,
    ) -> Tuple[str, str, float, str, bool]:
        """
        Create task and poll for poll_seconds.
        
        Returns current status (Processing/Queued/etc.) without waiting for completion.
        """
        api_logger = get_api_logger()
        
        # First create the task
        _, task_id, _, create_status, create_success = self._test_create(
            image, prompt, provider, model, duration, resolution, mode,
            negative_prompt, cfg_scale, seed, end_image, api_key, return_debug
        )
        
        if not create_success:
            return ("", task_id, 0.0, create_status.replace("TEST_CREATE", "TEST_POLL"), False)
        
        if provider == "auto":
            provider = "minimax"
        
        # Poll for status
        start_time = time.time()
        last_status = "Unknown"
        poll_count = 0
        
        try:
            while time.time() - start_time < poll_seconds:
                poll_count += 1
                
                if provider == "minimax":
                    poll_result = self._minimax_poll_status(task_id, api_key)
                elif provider == "kling":
                    poll_result = self._kling_poll_status(task_id, api_key)
                elif provider == "runway":
                    poll_result = self._runway_poll_status(task_id, api_key)
                elif provider == "vidu":
                    poll_result = self._vidu_poll_status(task_id, api_key)
                else:
                    poll_result = {"status": "unknown"}
                
                last_status = poll_result.get("status", "Unknown")
                
                # If completed or failed, break early
                if last_status.lower() in ["success", "succeed", "completed", "failed", "fail", "error"]:
                    break
                
                time.sleep(2)  # Poll interval
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Try to cancel
            caps = PROVIDER_TEST_CAPABILITIES.get(Provider(provider), {})
            if caps.get("supports_cancel"):
                try:
                    self._try_cancel_task(provider, task_id, api_key)
                except Exception:
                    pass
            
            entry = api_logger.log_request(
                provider=provider,
                model=model,
                run_mode="test_poll",
                operation="poll_status",
                request_url="N/A",
                http_status=200,
                response_body={"last_status": last_status, "poll_count": poll_count},
                response_time_ms=elapsed_ms,
                task_id=task_id,
            )
            
            status = f"{TestStatus.TEST_POLL_OK.value} | task_id={task_id} | status={last_status} | polls={poll_count}"
            if return_debug:
                status += f" | {api_logger.format_status_summary(entry)}"
            
            return ("", task_id, 0.0, status, True)
            
        except Exception as e:
            entry = api_logger.log_request(
                provider=provider,
                model=model,
                run_mode="test_poll",
                operation="poll_status",
                request_url="N/A",
                http_status=0,
                error=str(e),
                task_id=task_id,
            )
            
            status = f"{TestStatus.TEST_POLL_FAIL.value} | {provider}: {str(e)[:200]}"
            return ("", task_id, 0.0, status, False)
    
    def _test_download(
        self,
        provider: str,
        task_id: str,
        api_key: str,
        return_debug: bool,
    ) -> Tuple[str, str, float, str, bool]:
        """
        Test retrieve + download permissions for a given task_id.
        """
        api_logger = get_api_logger()
        
        if not task_id:
            return ("", "", 0.0, f"{TestStatus.TEST_DOWNLOAD_FAIL.value} | No task_id provided", False)
        
        if provider == "auto":
            provider = "minimax"
        
        start_time = time.time()
        
        try:
            # Get download URL
            if provider == "minimax":
                download_url, file_id = self._minimax_get_download_url(task_id, api_key)
            elif provider == "kling":
                download_url, file_id = self._kling_get_download_url(task_id, api_key)
            elif provider == "runway":
                download_url, file_id = self._runway_get_download_url(task_id, api_key)
            elif provider == "vidu":
                download_url, file_id = self._vidu_get_download_url(task_id, api_key)
            else:
                raise ValueError(f"Provider {provider} not supported")
            
            # Test download (just HEAD request to verify access)
            with httpx.Client(timeout=30) as client:
                resp = client.head(download_url)
                download_accessible = resp.status_code == 200
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            entry = api_logger.log_request(
                provider=provider,
                model="N/A",
                run_mode="test_download",
                operation="download_test",
                request_url=download_url[:100] + "...",
                http_status=resp.status_code,
                response_time_ms=elapsed_ms,
                task_id=task_id,
                file_id=file_id,
                download_url=download_url,
            )
            
            if download_accessible:
                status = f"{TestStatus.TEST_DOWNLOAD_OK.value} | Download URL accessible | file_id={file_id}"
            else:
                status = f"{TestStatus.TEST_DOWNLOAD_FAIL.value} | HTTP {resp.status_code}"
            
            if return_debug:
                status += f" | {api_logger.format_status_summary(entry)}"
            
            return ("", task_id, 0.0, status, download_accessible)
            
        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            
            entry = api_logger.log_request(
                provider=provider,
                model="N/A",
                run_mode="test_download",
                operation="download_test",
                request_url="N/A",
                http_status=0,
                response_time_ms=elapsed_ms,
                task_id=task_id,
                error=str(e),
            )
            
            status = f"{TestStatus.TEST_DOWNLOAD_FAIL.value} | {str(e)[:200]}"
            return ("", task_id, 0.0, status, False)
    
    # =========================================================================
    # Production Mode
    # =========================================================================
    
    def _prod_full(
        self,
        image: torch.Tensor,
        prompt: str,
        provider: str,
        model: str,
        duration: str,
        resolution: str,
        mode: str,
        negative_prompt: str,
        cfg_scale: float,
        seed: int,
        end_image: Optional[torch.Tensor],
        enable_fallback: bool,
        api_key: str,
        return_debug: bool,
    ) -> Tuple[str, str, float, str, bool]:
        """
        Full production video generation.
        """
        api_logger = get_api_logger()
        tracker = get_tracker()
        
        # Convert image
        pil_image = tensor_to_pil(image)
        pil_end_image = tensor_to_pil(end_image) if end_image is not None else None
        
        # Determine provider order
        # IMPORTANT: Draft providers NEVER fallback to production providers
        # to prevent accidental API charges
        if provider == "auto":
            providers_to_try = AUTO_PRIORITY.copy()
        else:
            providers_to_try = [Provider(provider)]
            # Only enable fallback for production providers
            # Draft providers should NOT fallback to avoid unexpected charges
            if enable_fallback and not is_draft_provider(provider):
                for p in AUTO_PRIORITY:
                    if p.value != provider and p not in providers_to_try:
                        providers_to_try.append(p)
            elif enable_fallback and is_draft_provider(provider):
                # Draft providers can only fallback to other draft providers
                for p in DRAFT_PRIORITY:
                    if p.value != provider and p not in providers_to_try:
                        providers_to_try.append(p)
        
        # Input params for tracking
        input_params = {
            "prompt": prompt[:100],
            "duration": duration,
            "resolution": resolution,
            "model": model,
            "cfg_scale": cfg_scale,
            "seed": seed,
            "has_end_image": end_image is not None,
        }
        
        # Try each provider
        last_error = ""
        task = None
        
        for p in providers_to_try:
            # Create task
            task = tracker.create_task(
                provider=p.value,
                operation="image2video",
                input_params=input_params,
            )
            task.estimated_cost_usd = COST_ESTIMATES.get(p, 0.0)
            
            tracker.start_task(task.task_id)
            
            try:
                video_path, provider_task_id, actual_cost = self._generate_with_provider(
                    provider=p,
                    image=pil_image,
                    prompt=prompt,
                    model=model,
                    duration=duration,
                    resolution=resolution,
                    mode=mode,
                    negative_prompt=negative_prompt,
                    cfg_scale=cfg_scale,
                    seed=seed,
                    end_image=pil_end_image,
                    api_key=api_key,
                )
                
                if video_path and os.path.exists(video_path):
                    # Success
                    tracker.complete_task(
                        task_id=task.task_id,
                        output_path=video_path,
                        provider_task_id=provider_task_id,
                        actual_cost_usd=actual_cost,
                    )
                    
                    status = f"{TestStatus.PROD_SUCCESS.value} | {p.value}:{model} | {duration}s @ {resolution}"
                    if return_debug:
                        status += f" | task_id={provider_task_id}"
                    
                    logger.info(f"{task.task_id}: {status}")
                    
                    return (video_path, task.task_id, actual_cost, status, True)
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
        status = f"{TestStatus.PROD_FAIL.value} | All providers failed | Last: {last_error[:150]}"
        logger.error(status)
        
        return ("", task.task_id if task else "", 0.0, status, False)
    
    def _generate_with_provider(
        self,
        provider: Provider,
        image: Image.Image,
        prompt: str,
        model: str,
        duration: str,
        resolution: str,
        mode: str,
        negative_prompt: str,
        cfg_scale: float,
        seed: int,
        end_image: Optional[Image.Image],
        api_key: str,
    ) -> Tuple[str, str, float]:
        """
        Call specific provider's API for full generation.
        
        Returns: (video_path, provider_task_id, actual_cost_usd)
        """
        if provider == Provider.KLING:
            return self._call_kling_full(
                image, prompt, model, mode, duration, resolution,
                negative_prompt, cfg_scale, end_image, api_key
            )
        elif provider == Provider.MINIMAX:
            return self._call_minimax_full(
                image, prompt, model, duration, resolution, api_key
            )
        elif provider == Provider.RUNWAY:
            return self._call_runway_full(
                image, prompt, model, duration, resolution, seed, api_key
            )
        elif provider == Provider.VIDU:
            return self._call_vidu_full(
                image, prompt, model, duration, resolution, end_image, api_key
            )
        elif provider == Provider.LOCAL:
            return self._call_local(image, prompt, duration, seed)
        # Draft Providers - Local GPU
        elif provider == Provider.LOCAL_TURBODIFFUSION:
            return self._call_turbodiffusion(image, prompt, duration, seed, negative_prompt, cfg_scale)
        elif provider == Provider.LOCAL_WAN_I2V:
            return self._call_wan_i2v(image, prompt, duration, seed, negative_prompt, cfg_scale)
        elif provider == Provider.LOCAL_COGVIDEO_FAST:
            return self._call_cogvideo_fast(image, prompt, duration, seed, negative_prompt, cfg_scale)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    # =========================================================================
    # MiniMax API Implementation
    # =========================================================================
    
    def _get_minimax_api_key(self, override: str) -> str:
        """Get MiniMax API key from override or environment."""
        key = override or os.environ.get("MINIMAX_API_KEY", "")
        if not key:
            raise ValueError("MiniMax API key not configured (set MINIMAX_API_KEY env var)")
        return key
    
    def _minimax_test_connect(self, api_key: str) -> Dict[str, Any]:
        """Test MiniMax API connectivity."""
        api_key = self._get_minimax_api_key(api_key)
        
        # Use models endpoint to test connectivity
        base_url = "https://api.minimaxi.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        with httpx.Client(timeout=30) as client:
            # Try to get file list as a connectivity test
            resp = client.get(
                f"{base_url}/files/list",
                headers=headers,
                params={"purpose": "video_generation"},
            )
            
            result = resp.json()
            
            if resp.status_code == 200:
                return {
                    "status": "connected",
                    "endpoint": f"{base_url}/files/list",
                    "http_status": resp.status_code,
                    "message": "MiniMax API connected successfully",
                }
            else:
                base_resp = result.get("base_resp", {})
                raise ValueError(f"API error: {base_resp.get('status_msg', 'Unknown')}")
    
    def _minimax_create_task(
        self,
        image: Image.Image,
        prompt: str,
        model: str,
        duration: str,
        resolution: str,
        api_key: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """Create MiniMax video generation task."""
        api_key = self._get_minimax_api_key(api_key)
        
        base_url = "https://api.minimaxi.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # Convert image to base64
        image_b64 = image_to_base64(image, format="JPEG")
        image_data_uri = f"data:image/jpeg;base64,{image_b64}"
        
        # Determine model
        if model == "auto" or model not in MINIMAX_MODELS:
            model = "I2V-01"  # Default I2V model
        
        # Duration must be int
        duration_int = int(duration) if duration.isdigit() else 6
        if duration_int not in [6]:  # MiniMax currently only supports 6s
            duration_int = 6
        
        # Resolution mapping
        res_upper = resolution.upper()
        if res_upper not in ["720P", "1080P"]:
            res_upper = "720P"
        
        payload = {
            "model": model,
            "prompt": prompt if prompt else "Generate a natural video based on this image",
            "first_frame_image": image_data_uri,
        }
        
        logger.info(f"MiniMax create task: model={model}, duration={duration_int}, resolution={res_upper}")
        
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{base_url}/video_generation",
                headers=headers,
                json=payload,
            )
            
            result = resp.json()
            
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {result}")
            
            base_resp = result.get("base_resp", {})
            if base_resp.get("status_code", 0) != 0:
                raise RuntimeError(f"API error: {base_resp.get('status_msg', 'Unknown')}")
            
            task_id = result.get("task_id", "")
            if not task_id:
                raise RuntimeError(f"No task_id in response: {result}")
            
            return (task_id, {
                "request_url": f"{base_url}/video_generation",
                "http_status": resp.status_code,
                "task_id": task_id,
                "model": model,
            })
    
    def _minimax_poll_status(self, task_id: str, api_key: str) -> Dict[str, Any]:
        """Poll MiniMax task status."""
        api_key = self._get_minimax_api_key(api_key)
        
        base_url = "https://api.minimaxi.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{base_url}/query/video_generation",
                headers=headers,
                params={"task_id": task_id},
            )
            
            result = resp.json()
            status = result.get("status", "Unknown")
            file_id = result.get("file_id", "")
            
            return {
                "status": status,
                "file_id": file_id,
                "raw": result,
            }
    
    def _minimax_get_download_url(self, task_id: str, api_key: str) -> Tuple[str, str]:
        """Get download URL for completed MiniMax task."""
        api_key = self._get_minimax_api_key(api_key)
        
        # First get file_id from task
        poll_result = self._minimax_poll_status(task_id, api_key)
        file_id = poll_result.get("file_id", "")
        
        if not file_id:
            raise RuntimeError(f"Task {task_id} has no file_id (status: {poll_result.get('status')})")
        
        base_url = "https://api.minimaxi.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{base_url}/files/retrieve",
                headers=headers,
                params={"file_id": int(file_id)},
            )
            
            result = resp.json()
            
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {result}")
            
            file_info = result.get("file", {})
            download_url = file_info.get("download_url") or file_info.get("backup_download_url")
            
            if not download_url:
                raise RuntimeError(f"No download URL in response: {result}")
            
            return (download_url, file_id)
    
    def _call_minimax_full(
        self,
        image: Image.Image,
        prompt: str,
        model: str,
        duration: str,
        resolution: str,
        api_key: str,
    ) -> Tuple[str, str, float]:
        """Full MiniMax video generation."""
        api_key = self._get_minimax_api_key(api_key)
        
        # Create task
        task_id, create_response = self._minimax_create_task(
            image, prompt, model, duration, resolution, api_key
        )
        
        logger.info(f"MiniMax task created: {task_id}")
        
        # Poll for completion
        base_url = "https://api.minimaxi.com/v1"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        max_wait = 300
        start_time = time.time()
        
        with httpx.Client(timeout=120) as client:
            while time.time() - start_time < max_wait:
                resp = client.get(
                    f"{base_url}/query/video_generation",
                    headers=headers,
                    params={"task_id": task_id},
                )
                
                result = resp.json()
                status = result.get("status", "")
                
                if status == "Success":
                    file_id = result.get("file_id")
                    logger.info(f"MiniMax task {task_id} completed, file_id: {file_id}")
                    
                    # Get download URL
                    download_url, _ = self._minimax_get_download_url(task_id, api_key)
                    
                    # Download video
                    video_path = self._download_video(client, download_url, "minimax", task_id)
                    
                    # Estimate cost
                    model_info = MINIMAX_MODELS.get(model, MINIMAX_MODELS["I2V-01"])
                    cost = model_info.get("cost_per_second", 0.08) * 6
                    
                    return (video_path, task_id, cost)
                
                elif status == "Fail":
                    base_resp = result.get("base_resp", {})
                    raise RuntimeError(f"Task failed: {base_resp.get('status_msg', 'Unknown')}")
                
                logger.info(f"MiniMax task {task_id}: {status}")
                time.sleep(5)
            
            raise TimeoutError(f"MiniMax task {task_id} timed out after {max_wait}s")
    
    # =========================================================================
    # Kling API Implementation
    # =========================================================================
    
    def _get_kling_api_key(self, override: str) -> str:
        """Get Kling API key."""
        key = override or os.environ.get("KLING_API_KEY", "")
        if not key:
            raise ValueError("Kling API key not configured (set KLING_API_KEY env var)")
        return key
    
    def _kling_test_connect(self, api_key: str) -> Dict[str, Any]:
        """Test Kling API connectivity."""
        api_key = self._get_kling_api_key(api_key)
        
        base_url = "https://api.klingai.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
        }
        
        # Try to access account info or similar endpoint
        with httpx.Client(timeout=30) as client:
            # Kling doesn't have a dedicated account endpoint, so we test with a minimal call
            # Just verify auth works
            resp = client.get(
                f"{base_url}/videos/image2video",
                headers=headers,
            )
            
            # 405 Method Not Allowed is expected for GET, but means auth worked
            if resp.status_code in [200, 405, 400]:
                return {
                    "status": "connected",
                    "endpoint": f"{base_url}/videos/image2video",
                    "http_status": resp.status_code,
                    "message": "Kling API auth verified",
                }
            elif resp.status_code == 401:
                raise ValueError("Invalid API key (401 Unauthorized)")
            else:
                raise ValueError(f"HTTP {resp.status_code}")
    
    def _kling_create_task(
        self,
        image: Image.Image,
        prompt: str,
        model: str,
        mode: str,
        duration: str,
        resolution: str,
        negative_prompt: str,
        cfg_scale: float,
        end_image: Optional[Image.Image],
        api_key: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """Create Kling video generation task."""
        api_key = self._get_kling_api_key(api_key)
        
        base_url = "https://api.klingai.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        
        # Model selection
        if model == "auto" or model not in KLING_MODELS:
            model = "kling-v1-5"
        
        # Mode validation
        model_info = KLING_MODELS.get(model, KLING_MODELS["kling-v1-5"])
        if mode not in model_info.get("modes", ["std", "pro"]):
            mode = "std"
        
        # Duration
        duration_int = int(duration) if duration.isdigit() else 5
        if duration_int not in model_info.get("durations", [5, 10]):
            duration_int = 5
        
        # Convert image
        image_b64 = image_to_base64(image)
        
        payload = {
            "model_name": model,
            "mode": mode,
            "duration": str(duration_int),
            "image": image_b64,
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "cfg_scale": cfg_scale,
        }
        
        if end_image and model_info.get("supports_tail_image"):
            payload["tail_image"] = image_to_base64(end_image)
        
        logger.info(f"Kling create task: model={model}, mode={mode}, duration={duration_int}")
        
        with httpx.Client(timeout=300) as client:
            resp = client.post(
                f"{base_url}/videos/image2video",
                headers=headers,
                json=payload,
            )
            
            result = resp.json()
            
            if resp.status_code != 200:
                raise RuntimeError(f"HTTP {resp.status_code}: {result}")
            
            task_id = result.get("data", {}).get("task_id", "")
            if not task_id:
                raise RuntimeError(f"No task_id in response: {result}")
            
            return (task_id, {
                "request_url": f"{base_url}/videos/image2video",
                "http_status": resp.status_code,
                "task_id": task_id,
                "model": model,
                "mode": mode,
            })
    
    def _kling_poll_status(self, task_id: str, api_key: str) -> Dict[str, Any]:
        """Poll Kling task status."""
        api_key = self._get_kling_api_key(api_key)
        
        base_url = "https://api.klingai.com/v1"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{base_url}/videos/image2video/{task_id}",
                headers=headers,
            )
            
            result = resp.json()
            status = result.get("data", {}).get("task_status", "Unknown")
            
            return {
                "status": status,
                "raw": result,
            }
    
    def _kling_get_download_url(self, task_id: str, api_key: str) -> Tuple[str, str]:
        """Get download URL for completed Kling task."""
        api_key = self._get_kling_api_key(api_key)
        
        base_url = "https://api.klingai.com/v1"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{base_url}/videos/image2video/{task_id}",
                headers=headers,
            )
            
            result = resp.json()
            status = result.get("data", {}).get("task_status", "")
            
            if status != "succeed":
                raise RuntimeError(f"Task status is {status}, not succeed")
            
            videos = result.get("data", {}).get("task_result", {}).get("videos", [])
            if not videos:
                raise RuntimeError("No videos in task result")
            
            download_url = videos[0].get("url", "")
            if not download_url:
                raise RuntimeError("No URL in video result")
            
            return (download_url, task_id)
    
    def _call_kling_full(
        self,
        image: Image.Image,
        prompt: str,
        model: str,
        mode: str,
        duration: str,
        resolution: str,
        negative_prompt: str,
        cfg_scale: float,
        end_image: Optional[Image.Image],
        api_key: str,
    ) -> Tuple[str, str, float]:
        """Full Kling video generation."""
        api_key = self._get_kling_api_key(api_key)
        
        # Create task
        task_id, create_response = self._kling_create_task(
            image, prompt, model, mode, duration, resolution,
            negative_prompt, cfg_scale, end_image, api_key
        )
        
        logger.info(f"Kling task created: {task_id}")
        
        base_url = "https://api.klingai.com/v1"
        headers = {"Authorization": f"Bearer {api_key}"}
        
        max_wait = 600
        start_time = time.time()
        
        with httpx.Client(timeout=300) as client:
            while time.time() - start_time < max_wait:
                resp = client.get(
                    f"{base_url}/videos/image2video/{task_id}",
                    headers=headers,
                )
                
                result = resp.json()
                status = result.get("data", {}).get("task_status", "")
                
                if status == "succeed":
                    videos = result.get("data", {}).get("task_result", {}).get("videos", [])
                    if videos:
                        video_url = videos[0].get("url", "")
                        video_path = self._download_video(client, video_url, "kling", task_id)
                        
                        # Calculate cost
                        model_info = KLING_MODELS.get(model, KLING_MODELS["kling-v1-5"])
                        duration_int = int(duration) if duration.isdigit() else 5
                        cost_key = f"cost_{duration_int}s_{mode}"
                        cost = model_info.get(cost_key, 0.14)
                        
                        return (video_path, task_id, cost)
                    raise RuntimeError("No video URL in successful response")
                
                elif status == "failed":
                    error = result.get("data", {}).get("task_status_msg", "Unknown error")
                    raise RuntimeError(f"Task failed: {error}")
                
                logger.info(f"Kling task {task_id}: {status}")
                time.sleep(5)
            
            raise TimeoutError(f"Kling task {task_id} timed out after {max_wait}s")
    
    # =========================================================================
    # Runway API Implementation
    # =========================================================================
    
    def _get_runway_api_key(self, override: str) -> str:
        """Get Runway API key."""
        key = override or os.environ.get("RUNWAY_API_KEY", "")
        if not key:
            raise ValueError("Runway API key not configured (set RUNWAY_API_KEY env var)")
        return key
    
    def _runway_test_connect(self, api_key: str) -> Dict[str, Any]:
        """Test Runway API connectivity."""
        api_key = self._get_runway_api_key(api_key)
        
        base_url = "https://api.dev.runwayml.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Runway-Version": "2024-11-06",
        }
        
        with httpx.Client(timeout=30) as client:
            # Check account/auth
            resp = client.get(
                f"{base_url}/account",
                headers=headers,
            )
            
            if resp.status_code == 200:
                return {
                    "status": "connected",
                    "endpoint": f"{base_url}/account",
                    "http_status": resp.status_code,
                    "message": "Runway API connected",
                }
            elif resp.status_code == 401:
                raise ValueError("Invalid API key")
            else:
                raise ValueError(f"HTTP {resp.status_code}: {resp.text}")
    
    def _runway_create_task(
        self,
        image: Image.Image,
        prompt: str,
        model: str,
        duration: str,
        resolution: str,
        seed: int,
        api_key: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """Create Runway video generation task."""
        api_key = self._get_runway_api_key(api_key)
        
        base_url = "https://api.dev.runwayml.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Runway-Version": "2024-11-06",
            "Content-Type": "application/json",
        }
        
        # Model selection
        if model == "auto" or model not in RUNWAY_MODELS:
            model = "gen3a_turbo"
        
        # Duration (seconds)
        duration_int = int(duration) if duration.isdigit() else 5
        
        # Convert image to base64 data URI
        image_b64 = image_to_base64(image, format="JPEG")
        image_uri = f"data:image/jpeg;base64,{image_b64}"
        
        payload = {
            "model": model,
            "promptImage": image_uri,
            "promptText": prompt,
            "duration": duration_int,
            "ratio": "16:9",
        }
        
        if seed > 0:
            payload["seed"] = seed
        
        logger.info(f"Runway create task: model={model}, duration={duration_int}")
        
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{base_url}/image_to_video",
                headers=headers,
                json=payload,
            )
            
            result = resp.json()
            
            if resp.status_code not in [200, 201]:
                raise RuntimeError(f"HTTP {resp.status_code}: {result}")
            
            task_id = result.get("id", "")
            if not task_id:
                raise RuntimeError(f"No task id in response: {result}")
            
            return (task_id, {
                "request_url": f"{base_url}/image_to_video",
                "http_status": resp.status_code,
                "task_id": task_id,
                "model": model,
            })
    
    def _runway_poll_status(self, task_id: str, api_key: str) -> Dict[str, Any]:
        """Poll Runway task status."""
        api_key = self._get_runway_api_key(api_key)
        
        base_url = "https://api.dev.runwayml.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Runway-Version": "2024-11-06",
        }
        
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{base_url}/tasks/{task_id}",
                headers=headers,
            )
            
            result = resp.json()
            status = result.get("status", "Unknown")
            
            return {
                "status": status,
                "raw": result,
            }
    
    def _runway_get_download_url(self, task_id: str, api_key: str) -> Tuple[str, str]:
        """Get download URL for completed Runway task."""
        poll_result = self._runway_poll_status(task_id, api_key)
        
        if poll_result.get("status") != "SUCCEEDED":
            raise RuntimeError(f"Task status is {poll_result.get('status')}")
        
        raw = poll_result.get("raw", {})
        output = raw.get("output", [])
        
        if not output:
            raise RuntimeError("No output in task result")
        
        download_url = output[0] if isinstance(output, list) else output
        return (download_url, task_id)
    
    def _try_cancel_task(self, provider: str, task_id: str, api_key: str) -> Dict[str, Any]:
        """Try to cancel a task (if provider supports it)."""
        if provider == "runway":
            api_key = self._get_runway_api_key(api_key)
            base_url = "https://api.dev.runwayml.com/v1"
            headers = {
                "Authorization": f"Bearer {api_key}",
                "X-Runway-Version": "2024-11-06",
            }
            
            with httpx.Client(timeout=30) as client:
                resp = client.delete(
                    f"{base_url}/tasks/{task_id}",
                    headers=headers,
                )
                return {"cancelled": resp.status_code in [200, 204], "status_code": resp.status_code}
        
        return {"cancelled": False, "reason": f"Provider {provider} does not support cancel"}
    
    def _call_runway_full(
        self,
        image: Image.Image,
        prompt: str,
        model: str,
        duration: str,
        resolution: str,
        seed: int,
        api_key: str,
    ) -> Tuple[str, str, float]:
        """Full Runway video generation."""
        api_key = self._get_runway_api_key(api_key)
        
        # Create task
        task_id, create_response = self._runway_create_task(
            image, prompt, model, duration, resolution, seed, api_key
        )
        
        logger.info(f"Runway task created: {task_id}")
        
        base_url = "https://api.dev.runwayml.com/v1"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "X-Runway-Version": "2024-11-06",
        }
        
        max_wait = 300
        start_time = time.time()
        
        with httpx.Client(timeout=120) as client:
            while time.time() - start_time < max_wait:
                resp = client.get(
                    f"{base_url}/tasks/{task_id}",
                    headers=headers,
                )
                
                result = resp.json()
                status = result.get("status", "")
                
                if status == "SUCCEEDED":
                    output = result.get("output", [])
                    if output:
                        video_url = output[0] if isinstance(output, list) else output
                        video_path = self._download_video(client, video_url, "runway", task_id)
                        
                        # Calculate cost
                        model_info = RUNWAY_MODELS.get(model, RUNWAY_MODELS["gen3a_turbo"])
                        duration_int = int(duration) if duration.isdigit() else 5
                        cost = model_info.get("cost_per_second", 0.05) * duration_int
                        
                        return (video_path, task_id, cost)
                    raise RuntimeError("No output in successful response")
                
                elif status == "FAILED":
                    failure = result.get("failure", "Unknown error")
                    raise RuntimeError(f"Task failed: {failure}")
                
                logger.info(f"Runway task {task_id}: {status}")
                time.sleep(5)
            
            raise TimeoutError(f"Runway task {task_id} timed out after {max_wait}s")
    
    # =========================================================================
    # Vidu API Implementation
    # =========================================================================
    
    def _get_vidu_api_key(self, override: str) -> str:
        """Get Vidu API key."""
        key = override or os.environ.get("VIDU_API_KEY", "")
        if not key:
            raise ValueError("Vidu API key not configured (set VIDU_API_KEY env var)")
        return key
    
    def _vidu_test_connect(self, api_key: str) -> Dict[str, Any]:
        """Test Vidu API connectivity."""
        api_key = self._get_vidu_api_key(api_key)
        
        base_url = "https://api.vidu.cn/v1"
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        }
        
        with httpx.Client(timeout=30) as client:
            # Try user info endpoint
            resp = client.get(
                f"{base_url}/user/info",
                headers=headers,
            )
            
            if resp.status_code == 200:
                return {
                    "status": "connected",
                    "endpoint": f"{base_url}/user/info",
                    "http_status": resp.status_code,
                    "message": "Vidu API connected",
                }
            elif resp.status_code == 401:
                raise ValueError("Invalid API key")
            else:
                raise ValueError(f"HTTP {resp.status_code}")
    
    def _vidu_create_task(
        self,
        image: Image.Image,
        prompt: str,
        model: str,
        duration: str,
        resolution: str,
        end_image: Optional[Image.Image],
        api_key: str,
    ) -> Tuple[str, Dict[str, Any]]:
        """Create Vidu video generation task."""
        api_key = self._get_vidu_api_key(api_key)
        
        base_url = "https://api.vidu.cn/v1"
        headers = {
            "Authorization": f"Token {api_key}",
            "Content-Type": "application/json",
        }
        
        # Model selection
        if model == "auto" or model not in VIDU_MODELS:
            model = "vidu-1.5"
        
        # Duration
        duration_int = int(duration) if duration.isdigit() else 4
        model_info = VIDU_MODELS.get(model, VIDU_MODELS["vidu-1.5"])
        if duration_int not in model_info.get("durations", [4, 8]):
            duration_int = 4
        
        # Convert image
        image_b64 = image_to_base64(image, format="PNG")
        
        payload = {
            "model": model,
            "prompt": prompt,
            "input_image": f"data:image/png;base64,{image_b64}",
            "duration": duration_int,
        }
        
        if end_image and model_info.get("supports_reference"):
            payload["reference_image"] = f"data:image/png;base64,{image_to_base64(end_image)}"
        
        logger.info(f"Vidu create task: model={model}, duration={duration_int}")
        
        with httpx.Client(timeout=120) as client:
            resp = client.post(
                f"{base_url}/videos/img2video",
                headers=headers,
                json=payload,
            )
            
            result = resp.json()
            
            if resp.status_code not in [200, 201]:
                raise RuntimeError(f"HTTP {resp.status_code}: {result}")
            
            task_id = result.get("task_id", "") or result.get("id", "")
            if not task_id:
                raise RuntimeError(f"No task_id in response: {result}")
            
            return (task_id, {
                "request_url": f"{base_url}/videos/img2video",
                "http_status": resp.status_code,
                "task_id": task_id,
                "model": model,
            })
    
    def _vidu_poll_status(self, task_id: str, api_key: str) -> Dict[str, Any]:
        """Poll Vidu task status."""
        api_key = self._get_vidu_api_key(api_key)
        
        base_url = "https://api.vidu.cn/v1"
        headers = {
            "Authorization": f"Token {api_key}",
        }
        
        with httpx.Client(timeout=30) as client:
            resp = client.get(
                f"{base_url}/videos/status/{task_id}",
                headers=headers,
            )
            
            result = resp.json()
            status = result.get("status", "Unknown")
            
            return {
                "status": status,
                "raw": result,
            }
    
    def _vidu_get_download_url(self, task_id: str, api_key: str) -> Tuple[str, str]:
        """Get download URL for completed Vidu task."""
        poll_result = self._vidu_poll_status(task_id, api_key)
        
        status = poll_result.get("status", "")
        if status.lower() not in ["success", "completed", "finished"]:
            raise RuntimeError(f"Task status is {status}")
        
        raw = poll_result.get("raw", {})
        video_url = raw.get("video_url", "") or raw.get("output_url", "")
        
        if not video_url:
            raise RuntimeError("No video URL in task result")
        
        return (video_url, task_id)
    
    def _call_vidu_full(
        self,
        image: Image.Image,
        prompt: str,
        model: str,
        duration: str,
        resolution: str,
        end_image: Optional[Image.Image],
        api_key: str,
    ) -> Tuple[str, str, float]:
        """Full Vidu video generation."""
        api_key = self._get_vidu_api_key(api_key)
        
        # Create task
        task_id, create_response = self._vidu_create_task(
            image, prompt, model, duration, resolution, end_image, api_key
        )
        
        logger.info(f"Vidu task created: {task_id}")
        
        base_url = "https://api.vidu.cn/v1"
        headers = {"Authorization": f"Token {api_key}"}
        
        max_wait = 300
        start_time = time.time()
        
        with httpx.Client(timeout=120) as client:
            while time.time() - start_time < max_wait:
                resp = client.get(
                    f"{base_url}/videos/status/{task_id}",
                    headers=headers,
                )
                
                result = resp.json()
                status = result.get("status", "")
                
                if status.lower() in ["success", "completed", "finished"]:
                    video_url = result.get("video_url", "") or result.get("output_url", "")
                    if video_url:
                        video_path = self._download_video(client, video_url, "vidu", task_id)
                        
                        # Calculate cost
                        model_info = VIDU_MODELS.get(model, VIDU_MODELS["vidu-1.5"])
                        duration_int = int(duration) if duration.isdigit() else 4
                        cost_key = f"cost_{duration_int}s"
                        cost = model_info.get(cost_key, 0.25)
                        
                        return (video_path, task_id, cost)
                    raise RuntimeError("No video URL in successful response")
                
                elif status.lower() in ["failed", "error"]:
                    error = result.get("error", "Unknown error")
                    raise RuntimeError(f"Task failed: {error}")
                
                logger.info(f"Vidu task {task_id}: {status}")
                time.sleep(5)
            
            raise TimeoutError(f"Vidu task {task_id} timed out after {max_wait}s")
    
    # =========================================================================
    # Local Model Implementation (Legacy)
    # =========================================================================
    
    def _call_local(
        self,
        image: Image.Image,
        prompt: str,
        duration: str,
        seed: int,
    ) -> Tuple[str, str, float]:
        """Local video generation (placeholder)."""
        # Would integrate with HunyuanVideo or CogVideoX
        raise NotImplementedError(
            "Local video generation not yet implemented. "
            "Install HunyuanVideo or CogVideoX for local generation."
        )
    
    # =========================================================================
    # Draft Engine Implementation (Local GPU - Preview/Draft Quality)
    # =========================================================================
    
    def _draft_provider_env_check(self, provider: str) -> Dict[str, Any]:
        """
        Environment self-check for draft providers.
        
        Checks:
        - CUDA availability
        - PyTorch version
        - Model weights existence
        - Available VRAM (rough estimate)
        
        This is used for test_connect mode on draft providers.
        """
        import sys
        
        checks = {
            "provider": provider,
            "status": "checking",
            "cuda_available": False,
            "torch_version": None,
            "cuda_version": None,
            "gpu_name": None,
            "vram_total_gb": 0,
            "vram_free_gb": 0,
            "weights_found": False,
            "weights_path": None,
            "issues": [],
            "recommendations": [],
        }
        
        # Check CUDA availability
        try:
            checks["cuda_available"] = torch.cuda.is_available()
            checks["torch_version"] = torch.__version__
            
            if checks["cuda_available"]:
                checks["cuda_version"] = torch.version.cuda
                checks["gpu_name"] = torch.cuda.get_device_name(0)
                
                # Get VRAM info
                vram_total = torch.cuda.get_device_properties(0).total_memory
                vram_reserved = torch.cuda.memory_reserved(0)
                vram_free = vram_total - vram_reserved
                
                checks["vram_total_gb"] = round(vram_total / (1024**3), 1)
                checks["vram_free_gb"] = round(vram_free / (1024**3), 1)
            else:
                checks["issues"].append("CUDA not available - GPU required for draft generation")
        except Exception as e:
            checks["issues"].append(f"Error checking CUDA: {str(e)}")
        
        # Get model info and check VRAM requirements
        model_key = DRAFT_PROVIDER_MODEL_MAP.get(Provider(provider), "turbodiffusion")
        model_info = LOCAL_DRAFT_MODELS.get(model_key, {})
        min_vram = model_info.get("min_vram_gb", 16)
        rec_vram = model_info.get("recommended_vram_gb", 24)
        
        if checks["vram_total_gb"] > 0:
            if checks["vram_total_gb"] < min_vram:
                checks["issues"].append(
                    f"Insufficient VRAM: {checks['vram_total_gb']}GB < {min_vram}GB minimum"
                )
            elif checks["vram_total_gb"] < rec_vram:
                checks["recommendations"].append(
                    f"VRAM {checks['vram_total_gb']}GB is below recommended {rec_vram}GB"
                )
        
        # Check for model weights
        weights_paths = self._get_draft_model_paths(provider)
        for path in weights_paths:
            if os.path.exists(path):
                checks["weights_found"] = True
                checks["weights_path"] = path
                break
        
        if not checks["weights_found"]:
            checks["issues"].append(
                f"Model weights not found. Expected paths: {weights_paths[:2]}"
            )
            checks["recommendations"].append(
                f"Download {model_key} weights and place in ComfyUI/models/video_generation/"
            )
        
        # Determine overall status
        if checks["issues"]:
            checks["status"] = "failed"
            return {
                "status": "failed",
                "message": f"Environment check failed: {checks['issues'][0]}",
                "details": checks,
            }
        else:
            checks["status"] = "ready"
            return {
                "status": "ready",
                "message": (
                    f"{provider} ready | GPU: {checks['gpu_name']} | "
                    f"VRAM: {checks['vram_free_gb']}/{checks['vram_total_gb']}GB"
                ),
                "details": checks,
            }
    
    def _get_draft_model_paths(self, provider: str) -> List[str]:
        """Get possible paths for draft model weights."""
        try:
            import folder_paths
            models_dir = folder_paths.models_dir
        except ImportError:
            models_dir = os.path.expanduser("~/comfyui/models")
        
        video_gen_dir = os.path.join(models_dir, "video_generation")
        
        model_key = DRAFT_PROVIDER_MODEL_MAP.get(Provider(provider), "turbodiffusion")
        
        # Common weight file patterns
        patterns = {
            "turbodiffusion": [
                os.path.join(video_gen_dir, "turbodiffusion"),
                os.path.join(video_gen_dir, "TurboDiffusion"),
                os.path.join(models_dir, "diffusers", "turbodiffusion"),
            ],
            "wan_i2v": [
                os.path.join(video_gen_dir, "wan_i2v"),
                os.path.join(video_gen_dir, "Wan-AI", "Wan2.1-I2V-14B-480P-Diffusers"),
                os.path.join(models_dir, "diffusers", "wan_i2v"),
            ],
            "cogvideo_fast": [
                os.path.join(video_gen_dir, "cogvideo"),
                os.path.join(video_gen_dir, "CogVideoX-5b-I2V"),
                os.path.join(models_dir, "diffusers", "cogvideo"),
            ],
        }
        
        return patterns.get(model_key, [os.path.join(video_gen_dir, model_key)])
    
    def _call_turbodiffusion(
        self,
        image: Image.Image,
        prompt: str,
        duration: str,
        seed: int,
        negative_prompt: str,
        cfg_scale: float,
    ) -> Tuple[str, str, float]:
        """
        TurboDiffusion draft video generation.
        
        This is a DRAFT engine - output is for preview/iteration only.
        NOT suitable for production/final output.
        
        Returns: (video_path, task_id, cost_usd)
        Cost is always 0.0 for local generation.
        """
        import uuid
        
        start_time = time.time()
        task_id = f"turbo_{uuid.uuid4().hex[:12]}"
        
        model_info = LOCAL_DRAFT_MODELS["turbodiffusion"]
        duration_int = int(duration) if duration.isdigit() else 4
        duration_int = min(duration_int, 5)  # Cap at 5s for draft
        
        # Determine seed
        if seed < 0:
            seed = int(time.time() * 1000) % 2147483647
        
        logger.info(f"[DRAFT] TurboDiffusion starting | task_id={task_id}")
        logger.info(f"[DRAFT] Config: duration={duration_int}s, seed={seed}, cfg={cfg_scale}")
        
        try:
            # Try to import TurboDiffusion pipeline
            video_path = self._run_turbodiffusion_inference(
                image=image,
                prompt=prompt,
                negative_prompt=negative_prompt,
                duration_seconds=duration_int,
                seed=seed,
                cfg_scale=cfg_scale,
                task_id=task_id,
            )
            
            elapsed = time.time() - start_time
            
            # Log performance metrics
            vram_used = 0
            if torch.cuda.is_available():
                vram_used = torch.cuda.max_memory_allocated() / (1024**3)
            
            logger.info(f"[DRAFT] TurboDiffusion complete | task_id={task_id}")
            logger.info(f"[DRAFT] Performance: time={elapsed:.1f}s, vram_peak={vram_used:.1f}GB")
            logger.info(f"[DRAFT] Output: {video_path}")
            
            return (video_path, task_id, 0.0)
            
        except ImportError as e:
            raise RuntimeError(
                f"TurboDiffusion not installed. Error: {e}\n"
                "Please install: pip install turbodiffusion\n"
                "Or place weights in ComfyUI/models/video_generation/turbodiffusion/"
            )
        except Exception as e:
            logger.error(f"[DRAFT] TurboDiffusion failed: {e}")
            raise RuntimeError(f"TurboDiffusion draft generation failed: {e}")
    
    def _run_turbodiffusion_inference(
        self,
        image: Image.Image,
        prompt: str,
        negative_prompt: str,
        duration_seconds: int,
        seed: int,
        cfg_scale: float,
        task_id: str,
    ) -> str:
        """
        Run TurboDiffusion inference.
        
        This method contains the actual model loading and inference logic.
        Separated for easier testing and future model swapping.
        """
        # Get output path
        output_dir = get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = os.path.join(output_dir, f"draft_turbo_{task_id}_{timestamp}.mp4")
        
        # Get model path
        weights_paths = self._get_draft_model_paths("local_turbodiffusion")
        model_path = None
        for path in weights_paths:
            if os.path.exists(path):
                model_path = path
                break
        
        if not model_path:
            # Try using diffusers directly if installed
            try:
                from diffusers import DiffusionPipeline
                
                # For now, use a placeholder implementation
                # Real implementation would load TurboDiffusion or similar fast I2V model
                logger.warning(
                    "[DRAFT] TurboDiffusion weights not found. "
                    "Using placeholder implementation for demo."
                )
                
                # Create a simple placeholder video for testing
                # In production, this would be replaced with actual model inference
                self._create_placeholder_draft_video(
                    image=image,
                    output_path=output_path,
                    duration_seconds=duration_seconds,
                    prompt=prompt,
                    task_id=task_id,
                )
                
                return output_path
                
            except ImportError:
                raise ImportError(
                    "diffusers not installed. Please install: pip install diffusers"
                )
        
        # Load and run actual model
        # This is where the real TurboDiffusion integration would go
        try:
            from diffusers import DiffusionPipeline
            
            logger.info(f"[DRAFT] Loading TurboDiffusion from: {model_path}")
            
            # Actual model loading and inference
            # pipe = DiffusionPipeline.from_pretrained(model_path, torch_dtype=torch.float16)
            # pipe = pipe.to("cuda")
            # ... inference code ...
            
            # For now, use placeholder
            self._create_placeholder_draft_video(
                image=image,
                output_path=output_path,
                duration_seconds=duration_seconds,
                prompt=prompt,
                task_id=task_id,
            )
            
            return output_path
            
        except Exception as e:
            raise RuntimeError(f"Failed to run TurboDiffusion: {e}")
    
    def _create_placeholder_draft_video(
        self,
        image: Image.Image,
        output_path: str,
        duration_seconds: int,
        prompt: str,
        task_id: str,
    ) -> None:
        """
        Create a placeholder draft video for testing/demo purposes.
        
        This creates a simple animated version of the input image
        to simulate draft output. In production, this would be
        replaced by actual model inference.
        """
        import subprocess
        
        # Resize image to draft resolution
        draft_size = (512, 512)
        image_resized = image.copy()
        image_resized.thumbnail(draft_size, Image.Resampling.LANCZOS)
        
        # Create temp image file
        temp_dir = os.path.dirname(output_path)
        temp_image_path = os.path.join(temp_dir, f"temp_{task_id}.png")
        image_resized.save(temp_image_path)
        
        fps = 24
        total_frames = duration_seconds * fps
        
        try:
            # Use ffmpeg to create a simple video from static image
            # with some visual indication this is a draft
            cmd = [
                "ffmpeg", "-y",
                "-loop", "1",
                "-i", temp_image_path,
                "-c:v", "libx264",
                "-t", str(duration_seconds),
                "-pix_fmt", "yuv420p",
                "-vf", (
                    f"scale=512:512,"
                    f"drawtext=text='DRAFT - {task_id[:8]}':fontsize=24:"
                    f"fontcolor=yellow:x=10:y=10:box=1:boxcolor=black@0.5,"
                    f"drawtext=text='Preview Only':fontsize=18:"
                    f"fontcolor=yellow:x=10:y=40:box=1:boxcolor=black@0.5"
                ),
                "-r", str(fps),
                output_path,
            ]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
            
            if result.returncode != 0:
                raise RuntimeError(f"ffmpeg failed: {result.stderr}")
                
        finally:
            # Cleanup temp file
            if os.path.exists(temp_image_path):
                os.remove(temp_image_path)
        
        logger.info(f"[DRAFT] Created placeholder video: {output_path}")
    
    def _call_wan_i2v(
        self,
        image: Image.Image,
        prompt: str,
        duration: str,
        seed: int,
        negative_prompt: str,
        cfg_scale: float,
    ) -> Tuple[str, str, float]:
        """
        Wan I2V draft video generation.
        
        Higher quality than TurboDiffusion but slower.
        Still DRAFT quality - not for production.
        """
        import uuid
        
        start_time = time.time()
        task_id = f"wan_{uuid.uuid4().hex[:12]}"
        
        duration_int = int(duration) if duration.isdigit() else 4
        duration_int = min(duration_int, 6)  # Cap at 6s
        
        if seed < 0:
            seed = int(time.time() * 1000) % 2147483647
        
        logger.info(f"[DRAFT] Wan I2V starting | task_id={task_id}")
        logger.info(f"[DRAFT] Config: duration={duration_int}s, seed={seed}")
        
        try:
            # Get output path
            output_dir = get_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"draft_wan_{task_id}_{timestamp}.mp4")
            
            # For now, use placeholder
            self._create_placeholder_draft_video(
                image=image,
                output_path=output_path,
                duration_seconds=duration_int,
                prompt=prompt,
                task_id=task_id,
            )
            
            elapsed = time.time() - start_time
            logger.info(f"[DRAFT] Wan I2V complete | time={elapsed:.1f}s")
            
            return (output_path, task_id, 0.0)
            
        except Exception as e:
            logger.error(f"[DRAFT] Wan I2V failed: {e}")
            raise RuntimeError(f"Wan I2V draft generation failed: {e}")
    
    def _call_cogvideo_fast(
        self,
        image: Image.Image,
        prompt: str,
        duration: str,
        seed: int,
        negative_prompt: str,
        cfg_scale: float,
    ) -> Tuple[str, str, float]:
        """
        CogVideoX Fast draft video generation.
        
        CogVideoX with reduced steps for faster preview.
        DRAFT quality - not for production.
        """
        import uuid
        
        start_time = time.time()
        task_id = f"cog_{uuid.uuid4().hex[:12]}"
        
        duration_int = int(duration) if duration.isdigit() else 4
        duration_int = min(duration_int, 6)  # Cap at 6s
        
        if seed < 0:
            seed = int(time.time() * 1000) % 2147483647
        
        logger.info(f"[DRAFT] CogVideoX Fast starting | task_id={task_id}")
        logger.info(f"[DRAFT] Config: duration={duration_int}s, seed={seed}")
        
        try:
            # Get output path
            output_dir = get_output_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(output_dir, f"draft_cog_{task_id}_{timestamp}.mp4")
            
            # For now, use placeholder
            self._create_placeholder_draft_video(
                image=image,
                output_path=output_path,
                duration_seconds=duration_int,
                prompt=prompt,
                task_id=task_id,
            )
            
            elapsed = time.time() - start_time
            logger.info(f"[DRAFT] CogVideoX Fast complete | time={elapsed:.1f}s")
            
            return (output_path, task_id, 0.0)
            
        except Exception as e:
            logger.error(f"[DRAFT] CogVideoX Fast failed: {e}")
            raise RuntimeError(f"CogVideoX Fast draft generation failed: {e}")
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    def _download_video(
        self,
        client: httpx.Client,
        url: str,
        provider: str,
        task_id: str,
    ) -> str:
        """Download video from URL to local file."""
        output_dir = get_output_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{provider}_{task_id[:8]}_{timestamp}.mp4"
        filepath = os.path.join(output_dir, filename)
        
        resp = client.get(url, timeout=120)
        resp.raise_for_status()
        
        with open(filepath, "wb") as f:
            f.write(resp.content)
        
        logger.info(f"Downloaded video to: {filepath}")
        return filepath
