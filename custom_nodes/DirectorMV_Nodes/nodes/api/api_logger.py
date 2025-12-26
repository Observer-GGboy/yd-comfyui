"""
API Logger - Structured HTTP request/response logging

Logs all API calls to JSONL files for debugging and observability.
Located at: ComfyUI/temp/directormv/api_logs/*.jsonl
"""

import json
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger("DirectorMV.API")


class APILogger:
    """
    Structured API call logger.
    
    Logs every HTTP request/response to JSONL files with:
    - provider / model / run_mode
    - request_url
    - http_status
    - response body (truncated ≤ 2KB, keys masked)
    - request_id / trace_id
    - task_id / file_id / download_url
    """
    
    _instance: Optional["APILogger"] = None
    
    # Keys to mask in logs (API keys, tokens, etc.)
    SENSITIVE_KEYS = [
        "api_key", "apikey", "key", "token", "secret", 
        "password", "authorization", "bearer", "access_token"
    ]
    
    MAX_RESPONSE_SIZE = 2048  # 2KB max for response body
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize log directory and file."""
        try:
            import folder_paths
            base_dir = folder_paths.get_temp_directory()
        except ImportError:
            base_dir = os.path.expanduser("~/.cache/comfyui/temp")
        
        self.log_dir = Path(base_dir) / "directormv" / "api_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create session log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"api_{timestamp}.jsonl"
        
        logger.info(f"APILogger initialized: {self.log_file}")
    
    def _mask_sensitive_data(self, data: Any, depth: int = 0) -> Any:
        """Recursively mask sensitive keys in data."""
        if depth > 10:  # Prevent infinite recursion
            return "[TRUNCATED]"
        
        if isinstance(data, dict):
            masked = {}
            for key, value in data.items():
                key_lower = key.lower()
                if any(s in key_lower for s in self.SENSITIVE_KEYS):
                    if isinstance(value, str) and len(value) > 8:
                        masked[key] = value[:4] + "****" + value[-4:]
                    else:
                        masked[key] = "****"
                else:
                    masked[key] = self._mask_sensitive_data(value, depth + 1)
            return masked
        
        elif isinstance(data, list):
            return [self._mask_sensitive_data(item, depth + 1) for item in data[:20]]  # Limit list items
        
        elif isinstance(data, str):
            # Mask URLs containing sensitive data
            if len(data) > 500:
                return data[:500] + "...[TRUNCATED]"
            return data
        
        return data
    
    def _truncate_response(self, response: Any) -> str:
        """Truncate response to max size."""
        if response is None:
            return ""
        
        if isinstance(response, dict):
            response_str = json.dumps(response, ensure_ascii=False)
        elif isinstance(response, str):
            response_str = response
        else:
            response_str = str(response)
        
        if len(response_str) > self.MAX_RESPONSE_SIZE:
            return response_str[:self.MAX_RESPONSE_SIZE] + "...[TRUNCATED]"
        
        return response_str
    
    def log_request(
        self,
        provider: str,
        model: str,
        run_mode: str,
        operation: str,
        request_url: str,
        request_method: str = "POST",
        request_headers: Optional[Dict] = None,
        request_body: Optional[Dict] = None,
        http_status: Optional[int] = None,
        response_body: Optional[Any] = None,
        response_time_ms: Optional[float] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        task_id: Optional[str] = None,
        file_id: Optional[str] = None,
        download_url: Optional[str] = None,
        error: Optional[str] = None,
        extra: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Log an API request/response.
        
        Returns the log entry for use in status messages.
        """
        # Build log entry
        entry = {
            "timestamp": datetime.now().isoformat(),
            "provider": provider,
            "model": model,
            "run_mode": run_mode,
            "operation": operation,
            "request_url": request_url,
            "request_method": request_method,
            "http_status": http_status,
            "response_time_ms": response_time_ms,
        }
        
        # Add masked headers (if present)
        if request_headers:
            entry["request_headers"] = self._mask_sensitive_data(request_headers)
        
        # Add masked request body (if present, truncated)
        if request_body:
            masked_body = self._mask_sensitive_data(request_body)
            entry["request_body"] = self._truncate_response(masked_body)
        
        # Add masked response body (truncated)
        if response_body:
            masked_response = self._mask_sensitive_data(response_body)
            entry["response_body"] = self._truncate_response(masked_response)
        
        # Add IDs
        if request_id:
            entry["request_id"] = request_id
        if trace_id:
            entry["trace_id"] = trace_id
        if task_id:
            entry["task_id"] = task_id
        if file_id:
            entry["file_id"] = file_id
        if download_url:
            # Mask download URL params
            if "?" in download_url:
                base, params = download_url.split("?", 1)
                entry["download_url"] = base + "?[PARAMS_MASKED]"
            else:
                entry["download_url"] = download_url
        
        # Add error
        if error:
            entry["error"] = error[:500] if len(error) > 500 else error
        
        # Add extra data
        if extra:
            entry["extra"] = self._mask_sensitive_data(extra)
        
        # Write to log file
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write API log: {e}")
        
        return entry
    
    def format_status_summary(self, entry: Dict[str, Any]) -> str:
        """
        Format a log entry as a human-readable status summary.
        
        Used for node status output - never returns 'unknown error'.
        """
        parts = []
        
        # Basic info
        provider = entry.get("provider", "unknown")
        model = entry.get("model", "default")
        run_mode = entry.get("run_mode", "prod_full")
        parts.append(f"[{provider.upper()}:{model}] mode={run_mode}")
        
        # HTTP status
        http_status = entry.get("http_status")
        if http_status:
            status_text = "OK" if 200 <= http_status < 300 else f"HTTP_{http_status}"
            parts.append(f"status={status_text}")
        
        # Response time
        response_time = entry.get("response_time_ms")
        if response_time:
            parts.append(f"time={response_time:.0f}ms")
        
        # Task/File IDs
        task_id = entry.get("task_id")
        if task_id:
            parts.append(f"task_id={task_id[:16]}...")
        
        file_id = entry.get("file_id")
        if file_id:
            parts.append(f"file_id={file_id}")
        
        # Error
        error = entry.get("error")
        if error:
            # Extract key error info
            error_short = error[:100] if len(error) > 100 else error
            parts.append(f"error={error_short}")
        
        # API-level error from response
        response = entry.get("response_body")
        if response and isinstance(response, str):
            try:
                resp_dict = json.loads(response)
                base_resp = resp_dict.get("base_resp", {})
                if base_resp.get("status_code", 0) != 0:
                    parts.append(f"api_error={base_resp.get('status_msg', 'API error')}")
            except (json.JSONDecodeError, TypeError):
                pass
        
        return " | ".join(parts)
    
    def get_log_path(self) -> str:
        """Get the current log file path."""
        return str(self.log_file)


# Global logger instance
_api_logger: Optional[APILogger] = None


def get_api_logger() -> APILogger:
    """Get the global API logger."""
    global _api_logger
    if _api_logger is None:
        _api_logger = APILogger()
    return _api_logger

