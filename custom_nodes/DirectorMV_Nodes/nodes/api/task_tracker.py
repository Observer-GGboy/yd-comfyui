"""
Task tracking for API calls

Records task_id, duration, cost, failure reasons for all API operations.
"""

import time
import json
import os
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger("DirectorMV.API")


@dataclass
class TaskRecord:
    """Record of a single API task."""
    task_id: str
    provider: str
    operation: str  # "image2video", "lipsync", etc.
    status: str  # "pending", "running", "success", "failed"
    
    # Timing
    started_at: str = ""
    completed_at: str = ""
    duration_seconds: float = 0.0
    
    # Cost tracking
    estimated_cost_usd: float = 0.0
    actual_cost_usd: float = 0.0
    
    # Input/Output
    input_params: Dict[str, Any] = field(default_factory=dict)
    output_path: str = ""
    
    # Error handling
    error_message: str = ""
    retry_count: int = 0
    
    # Provider-specific
    provider_task_id: str = ""  # e.g., Kling's internal task ID
    provider_response: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)


class TaskTracker:
    """
    Singleton tracker for all API tasks.
    
    Persists task history to disk for debugging and cost analysis.
    """
    
    _instance: Optional["TaskTracker"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        self.tasks: Dict[str, TaskRecord] = {}
        self._task_counter = 0
        
        # Setup log directory
        try:
            import folder_paths
            base_dir = folder_paths.get_temp_directory()
        except ImportError:
            base_dir = os.path.expanduser("~/.cache/comfyui")
        
        self.log_dir = Path(base_dir) / "directormv" / "api_logs"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        
        # Current session log file
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_log = self.log_dir / f"session_{timestamp}.jsonl"
        
        logger.info(f"TaskTracker initialized, logging to {self.log_dir}")
    
    def generate_task_id(self, provider: str, operation: str) -> str:
        """Generate unique task ID."""
        self._task_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"dmv_{provider}_{operation}_{timestamp}_{self._task_counter:04d}"
    
    def create_task(
        self,
        provider: str,
        operation: str,
        input_params: Optional[Dict[str, Any]] = None,
    ) -> TaskRecord:
        """Create and register a new task."""
        task_id = self.generate_task_id(provider, operation)
        
        task = TaskRecord(
            task_id=task_id,
            provider=provider,
            operation=operation,
            status="pending",
            started_at=datetime.now().isoformat(),
            input_params=input_params or {},
        )
        
        self.tasks[task_id] = task
        logger.info(f"Task created: {task_id}")
        
        return task
    
    def start_task(self, task_id: str) -> None:
        """Mark task as running."""
        if task_id in self.tasks:
            self.tasks[task_id].status = "running"
            self.tasks[task_id].started_at = datetime.now().isoformat()
    
    def complete_task(
        self,
        task_id: str,
        output_path: str = "",
        provider_task_id: str = "",
        provider_response: Optional[Dict] = None,
        actual_cost_usd: float = 0.0,
    ) -> None:
        """Mark task as successfully completed."""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.status = "success"
        task.completed_at = datetime.now().isoformat()
        task.output_path = output_path
        task.provider_task_id = provider_task_id
        task.provider_response = provider_response or {}
        task.actual_cost_usd = actual_cost_usd
        
        # Calculate duration
        if task.started_at:
            start = datetime.fromisoformat(task.started_at)
            end = datetime.fromisoformat(task.completed_at)
            task.duration_seconds = (end - start).total_seconds()
        
        self._persist_task(task)
        logger.info(f"Task completed: {task_id}, duration: {task.duration_seconds:.1f}s")
    
    def fail_task(
        self,
        task_id: str,
        error_message: str,
        provider_response: Optional[Dict] = None,
    ) -> None:
        """Mark task as failed."""
        if task_id not in self.tasks:
            return
        
        task = self.tasks[task_id]
        task.status = "failed"
        task.completed_at = datetime.now().isoformat()
        task.error_message = error_message
        task.provider_response = provider_response or {}
        
        # Calculate duration
        if task.started_at:
            start = datetime.fromisoformat(task.started_at)
            end = datetime.fromisoformat(task.completed_at)
            task.duration_seconds = (end - start).total_seconds()
        
        self._persist_task(task)
        logger.error(f"Task failed: {task_id}, error: {error_message}")
    
    def increment_retry(self, task_id: str) -> int:
        """Increment retry count and return new count."""
        if task_id in self.tasks:
            self.tasks[task_id].retry_count += 1
            return self.tasks[task_id].retry_count
        return 0
    
    def get_task(self, task_id: str) -> Optional[TaskRecord]:
        """Get task by ID."""
        return self.tasks.get(task_id)
    
    def _persist_task(self, task: TaskRecord) -> None:
        """Append task to session log file."""
        try:
            with open(self.session_log, "a", encoding="utf-8") as f:
                f.write(task.to_json() + "\n")
        except Exception as e:
            logger.warning(f"Failed to persist task: {e}")
    
    def get_session_summary(self) -> Dict[str, Any]:
        """Get summary of current session."""
        total = len(self.tasks)
        success = sum(1 for t in self.tasks.values() if t.status == "success")
        failed = sum(1 for t in self.tasks.values() if t.status == "failed")
        total_cost = sum(t.actual_cost_usd for t in self.tasks.values())
        total_duration = sum(t.duration_seconds for t in self.tasks.values())
        
        by_provider: Dict[str, Dict[str, Any]] = {}
        for t in self.tasks.values():
            if t.provider not in by_provider:
                by_provider[t.provider] = {"count": 0, "success": 0, "cost": 0.0}
            by_provider[t.provider]["count"] += 1
            if t.status == "success":
                by_provider[t.provider]["success"] += 1
            by_provider[t.provider]["cost"] += t.actual_cost_usd
        
        return {
            "total_tasks": total,
            "success": success,
            "failed": failed,
            "total_cost_usd": total_cost,
            "total_duration_seconds": total_duration,
            "by_provider": by_provider,
        }


# Global tracker instance
_tracker: Optional[TaskTracker] = None


def get_tracker() -> TaskTracker:
    """Get the global task tracker."""
    global _tracker
    if _tracker is None:
        _tracker = TaskTracker()
    return _tracker


class DMV_TaskTracker:
    """
    ComfyUI node for viewing task tracking information.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "action": (["get_summary", "get_task", "list_recent"],),
            },
            "optional": {
                "task_id": ("STRING", {
                    "default": "",
                    "multiline": False,
                }),
                "limit": ("INT", {
                    "default": 10,
                    "min": 1,
                    "max": 100,
                }),
            }
        }
    
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "track"
    CATEGORY = "DirectorMV/API"
    
    def track(
        self,
        action: str,
        task_id: str = "",
        limit: int = 10,
    ) -> tuple:
        tracker = get_tracker()
        
        if action == "get_summary":
            summary = tracker.get_session_summary()
            result = json.dumps(summary, indent=2, ensure_ascii=False)
        
        elif action == "get_task":
            task = tracker.get_task(task_id)
            if task:
                result = task.to_json()
            else:
                result = f"Task not found: {task_id}"
        
        elif action == "list_recent":
            tasks = list(tracker.tasks.values())[-limit:]
            result = json.dumps(
                [t.to_dict() for t in tasks],
                indent=2,
                ensure_ascii=False
            )
        
        else:
            result = f"Unknown action: {action}"
        
        return (result,)
