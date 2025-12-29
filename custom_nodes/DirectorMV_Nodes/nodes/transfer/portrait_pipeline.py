"""
Portrait pipeline helper nodes for DirectorMV.

These nodes are lightweight glue for image-first styling workflows.
They do not perform heavy processing themselves; they standardize inputs,
mask handling, and status messaging for downstream nodes.
"""

from typing import Optional, Tuple
import json
import os
import time
import torch
import httpx

from ..api.api_logger import get_api_logger


class DMV_PreflightPortrait:
    """
    Pass-through preflight node for portrait workflows.

    Accepts optional masks and returns them with a status string.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "hair_mask": ("MASK",),
                "face_mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "MASK", "STRING")
    RETURN_NAMES = ("image", "hair_mask", "face_mask", "status")
    FUNCTION = "preflight"
    CATEGORY = "DirectorMV/Portrait"

    def preflight(
        self,
        image: torch.Tensor,
        hair_mask: Optional[torch.Tensor] = None,
        face_mask: Optional[torch.Tensor] = None,
    ) -> Tuple[torch.Tensor, torch.Tensor, torch.Tensor, str]:
        if hair_mask is None:
            hair_mask = torch.zeros_like(image[:, :, :, 0:1])
        if face_mask is None:
            face_mask = torch.zeros_like(image[:, :, :, 0:1])

        height = image.shape[1]
        width = image.shape[2]
        status = f"Preflight OK | size={width}x{height}"
        return (image, hair_mask, face_mask, status)


class DMV_ApplyHairTransfer:
    """
    Prepare hair transfer mask and config for inpaint + reference workflows.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "target_image": ("IMAGE",),
                "hair_reference": ("IMAGE",),
                "hair_mask": ("MASK",),
            },
            "optional": {
                "face_mask": ("MASK",),
                "preserve_face": ("BOOLEAN", {"default": True}),
            },
        }

    RETURN_TYPES = ("IMAGE", "MASK", "STRING")
    RETURN_NAMES = ("image", "hair_mask", "config")
    FUNCTION = "apply"
    CATEGORY = "DirectorMV/Portrait"

    def apply(
        self,
        target_image: torch.Tensor,
        hair_reference: torch.Tensor,
        hair_mask: torch.Tensor,
        face_mask: Optional[torch.Tensor] = None,
        preserve_face: bool = True,
    ) -> Tuple[torch.Tensor, torch.Tensor, str]:
        if preserve_face and face_mask is not None:
            hair_mask = torch.clamp(hair_mask - face_mask, 0.0, 1.0)

        config = {
            "type": "hair_transfer",
            "preserve_face": preserve_face,
            "has_face_mask": face_mask is not None,
        }
        return (target_image, hair_mask, json.dumps(config, indent=2))


class DMV_ExtractHairPatch:
    """
    Extract a hair-only reference patch using a provided hair mask.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
                "hair_mask": ("MASK",),
            },
        }

    RETURN_TYPES = ("IMAGE",)
    RETURN_NAMES = ("hair_patch",)
    FUNCTION = "extract"
    CATEGORY = "DirectorMV/Portrait"

    def extract(self, image: torch.Tensor, hair_mask: torch.Tensor) -> Tuple[torch.Tensor]:
        if hair_mask.shape[0] != image.shape[0]:
            hair_mask = hair_mask[0].unsqueeze(0).repeat(image.shape[0], 1, 1, 1)
        mask = hair_mask.clamp(0.0, 1.0)
        hair_patch = image * mask
        return (hair_patch,)


class DMV_ApplyOutfitTransfer:
    """
    Prepare VTON inputs for downstream Kling Virtual Try-On node.

    This node does not call the API directly. It provides a run_mode
    flag and status string for workflow control.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "person_image": ("IMAGE",),
                "clothing_image": ("IMAGE",),
            },
            "optional": {
                "run_mode": (["prod_full", "test_connect"], {"default": "prod_full"}),
                "provider": (["kling"], {"default": "kling"}),
                "model_name": ("STRING", {"default": "kolors-virtual-try-on-v1"}),
            },
        }

    RETURN_TYPES = ("IMAGE", "IMAGE", "STRING", "INT", "STRING", "BOOLEAN")
    RETURN_NAMES = ("person_image", "clothing_image", "status", "select_index", "run_mode", "vton_called")
    FUNCTION = "apply"
    CATEGORY = "DirectorMV/Portrait"

    def apply(
        self,
        person_image: torch.Tensor,
        clothing_image: torch.Tensor,
        run_mode: str = "prod_full",
        provider: str = "kling",
        model_name: str = "kolors-virtual-try-on-v1",
    ) -> Tuple[torch.Tensor, torch.Tensor, str, int, str, bool]:
        vton_called = run_mode == "prod_full" and provider == "kling"

        if run_mode == "test_connect" and provider == "kling":
            status = self._kling_test_connect(model_name)
            select_index = 1
        else:
            status = f"VTON ready | provider={provider} | model={model_name} | run_mode={run_mode}"
            select_index = 2
        self._log_vton_route(provider, model_name, run_mode, select_index, vton_called)
        return (person_image, clothing_image, status, select_index, run_mode, vton_called)

    def _log_vton_route(
        self,
        provider: str,
        model_name: str,
        run_mode: str,
        select_index: int,
        vton_called: bool,
    ) -> None:
        api_logger = get_api_logger()
        api_logger.log_request(
            provider=provider,
            model=model_name,
            run_mode=run_mode,
            operation="dmv_vton_route",
            request_url="dmv://vton_route",
            request_method="LOCAL",
            http_status=None,
            response_body=None,
            response_time_ms=None,
            extra={
                "vton_called": vton_called,
                "select_index": select_index,
                "run_mode": run_mode,
            },
        )

    def _kling_test_connect(self, model_name: str) -> str:
        api_key = os.environ.get("KLING_API_KEY", "")
        if not api_key:
            return "TEST_CONNECT_FAIL | KLING_API_KEY not set"

        url = "https://api.klingai.com/v1/videos/image2video"
        headers = {"Authorization": f"Bearer {api_key}"}
        start = time.time()

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(url, headers=headers)

            ok = resp.status_code in (200, 400, 405)
            api_logger = get_api_logger()
            api_logger.log_request(
                provider="kling",
                model=model_name,
                run_mode="test_connect",
                operation="kling_vton_test_connect",
                request_url=url,
                request_method="GET",
                request_headers=headers,
                http_status=resp.status_code,
                response_body=resp.text,
                response_time_ms=(time.time() - start) * 1000.0,
            )

            if ok:
                return "TEST_CONNECT_OK | Kling API auth verified"
            return f"TEST_CONNECT_FAIL | HTTP {resp.status_code}"
        except Exception as exc:
            api_logger = get_api_logger()
            api_logger.log_request(
                provider="kling",
                model=model_name,
                run_mode="test_connect",
                operation="kling_vton_test_connect",
                request_url=url,
                request_method="GET",
                request_headers=headers,
                http_status=None,
                response_body=None,
                response_time_ms=(time.time() - start) * 1000.0,
                error=str(exc),
            )
            return f"TEST_CONNECT_FAIL | {str(exc)[:200]}"


class DMV_VtonStatusText:
    """
    Format a readable VTON status string for UI display.
    """

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "run_mode": ("STRING",),
                "select_index": ("INT",),
            },
            "optional": {
                "vton_called": ("BOOLEAN", {"default": False}),
            },
        }

    RETURN_TYPES = ("STRING", "BOOLEAN")
    RETURN_NAMES = ("text", "vton_called")
    FUNCTION = "format"
    CATEGORY = "DirectorMV/Portrait"

    def format(
        self,
        run_mode: str,
        select_index: int,
        vton_called: bool = False,
    ) -> Tuple[str, bool]:
        executed = vton_called or (run_mode != "test_connect" and int(select_index) == 2)
        if run_mode == "test_connect" or int(select_index) == 1:
            route_text = "TEST_CONNECT: bypass Kling"
        else:
            route_text = "PROD_FULL: execute Kling"

        text = (
            f"run_mode={run_mode} | select_index={select_index} | "
            f"Kling VTON executed? {'yes' if executed else 'no'} | {route_text}"
        )
        return (text, executed)
