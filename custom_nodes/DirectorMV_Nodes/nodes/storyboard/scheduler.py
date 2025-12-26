"""
DMV_ShotScheduler - Schedule shots from storyboard for optimal generation

Groups scenes by character to minimize identity switches.
Determines generation strategy (local vs API, single vs dual).
"""

from typing import Tuple, List, Dict, Any, Optional
import logging
from .parser import Storyboard, StoryboardScene

logger = logging.getLogger("DirectorMV.Storyboard")


class Shot:
    """Represents a single shot to be generated."""
    
    def __init__(
        self,
        shot_id: str,
        scene: StoryboardScene,
        generation_strategy: str,
        priority: int = 0,
    ):
        self.shot_id = shot_id
        self.scene = scene
        self.generation_strategy = generation_strategy  # "local", "api_kling", "api_dual"
        self.priority = priority
        self.status = "pending"  # pending, generating, completed, failed
        self.result = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "scene_id": self.scene.scene_id,
            "duration": self.scene.duration,
            "characters": self.scene.characters,
            "layout": self.scene.layout,
            "prompt": self.scene.prompt,
            "strategy": self.generation_strategy,
            "priority": self.priority,
            "status": self.status,
        }


class ShotSchedule:
    """Complete schedule of shots to generate."""
    
    def __init__(self):
        self.shots: List[Shot] = []
        self.generation_order: List[str] = []  # Shot IDs in generation order
    
    def add_shot(self, shot: Shot):
        self.shots.append(shot)
    
    def get_pending_shots(self) -> List[Shot]:
        return [s for s in self.shots if s.status == "pending"]
    
    def get_shot_by_id(self, shot_id: str) -> Optional[Shot]:
        for shot in self.shots:
            if shot.shot_id == shot_id:
                return shot
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "shots": [s.to_dict() for s in self.shots],
            "generation_order": self.generation_order,
            "total_shots": len(self.shots),
            "pending": len(self.get_pending_shots()),
        }


class DMV_ShotScheduler:
    """
    Schedule shots from storyboard for generation.
    
    Optimization strategies:
    1. Group by character to minimize identity context switches
    2. Prioritize dual-character scenes (use Kling Dual API)
    3. Order single-character scenes by character
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "storyboard": ("STORYBOARD",),
            },
            "optional": {
                "prefer_local": ("BOOLEAN", {"default": True}),
                "max_api_duration": ("FLOAT", {
                    "default": 10.0,
                    "min": 5.0,
                    "max": 30.0,
                    "step": 5.0,
                }),
                "group_by_character": ("BOOLEAN", {"default": True}),
            }
        }
    
    RETURN_TYPES = ("SHOT_SCHEDULE", "STRING", "INT")
    RETURN_NAMES = ("schedule", "schedule_json", "total_shots")
    FUNCTION = "schedule_shots"
    CATEGORY = "DirectorMV/Storyboard"
    
    def schedule_shots(
        self,
        storyboard: Storyboard,
        prefer_local: bool = True,
        max_api_duration: float = 10.0,
        group_by_character: bool = True,
    ) -> Tuple[ShotSchedule, str, int]:
        """
        Create shot schedule from storyboard.
        
        Args:
            storyboard: Parsed storyboard
            prefer_local: Prefer local generation when possible
            max_api_duration: Max duration for single API call
            group_by_character: Group shots by character for efficiency
            
        Returns:
            schedule: ShotSchedule object
            schedule_json: JSON representation
            total_shots: Total number of shots
        """
        schedule = ShotSchedule()
        
        # Categorize scenes
        dual_scenes = []
        single_a_scenes = []
        single_b_scenes = []
        
        for scene in storyboard.scenes:
            if scene.layout == "same_frame" and len(scene.characters) >= 2:
                dual_scenes.append(scene)
            elif scene.layout == "single_A" or (scene.characters and "A" in scene.characters[0].upper()):
                single_a_scenes.append(scene)
            else:
                single_b_scenes.append(scene)
        
        # Determine generation strategies and create shots
        shot_idx = 0
        
        # Dual character scenes - must use API (Kling Dual Character)
        for scene in dual_scenes:
            shot = Shot(
                shot_id=f"shot_{shot_idx:03d}",
                scene=scene,
                generation_strategy="api_dual",
                priority=0,  # Highest priority - most complex
            )
            schedule.add_shot(shot)
            shot_idx += 1
        
        # Single character scenes
        for scenes, char_label in [(single_a_scenes, "A"), (single_b_scenes, "B")]:
            for scene in scenes:
                # Determine strategy based on duration and preference
                if prefer_local and scene.duration <= 10:
                    strategy = "local"
                elif scene.duration <= max_api_duration:
                    strategy = "api_single"
                else:
                    # Long duration - need to split or use video extend
                    strategy = "api_extend"
                
                shot = Shot(
                    shot_id=f"shot_{shot_idx:03d}",
                    scene=scene,
                    generation_strategy=strategy,
                    priority=1 if char_label == "A" else 2,
                )
                schedule.add_shot(shot)
                shot_idx += 1
        
        # Determine generation order
        if group_by_character:
            # Generate all shots for one character, then the other
            # This minimizes identity context switches
            order = []
            
            # Dual scenes first (need both characters loaded anyway)
            order.extend([s.shot_id for s in schedule.shots if s.generation_strategy == "api_dual"])
            
            # Then single A
            order.extend([s.shot_id for s in schedule.shots 
                         if s.generation_strategy != "api_dual" and s.priority == 1])
            
            # Then single B
            order.extend([s.shot_id for s in schedule.shots 
                         if s.generation_strategy != "api_dual" and s.priority == 2])
            
            schedule.generation_order = order
        else:
            # Original scene order
            schedule.generation_order = [s.shot_id for s in schedule.shots]
        
        import json
        schedule_json = json.dumps(schedule.to_dict(), indent=2, ensure_ascii=False)
        
        logger.info(f"Scheduled {len(schedule.shots)} shots")
        logger.info(f"  Dual: {len(dual_scenes)}, Single A: {len(single_a_scenes)}, Single B: {len(single_b_scenes)}")
        
        return (schedule, schedule_json, len(schedule.shots))


class DMV_ShotIterator:
    """
    Iterate through shots in a schedule.
    
    Used in loops to process shots one by one.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "schedule": ("SHOT_SCHEDULE",),
                "current_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 1000,
                }),
            }
        }
    
    RETURN_TYPES = ("SHOT", "STRING", "STRING", "FLOAT", "BOOLEAN")
    RETURN_NAMES = ("shot", "shot_id", "prompt", "duration", "has_more")
    FUNCTION = "get_shot"
    CATEGORY = "DirectorMV/Storyboard"
    
    def get_shot(
        self,
        schedule: ShotSchedule,
        current_index: int,
    ) -> Tuple[Shot, str, str, float, bool]:
        """Get shot at current index."""
        if current_index >= len(schedule.generation_order):
            # Return dummy shot when exhausted
            dummy_scene = StoryboardScene("dummy", 0, [], "none", "")
            dummy_shot = Shot("dummy", dummy_scene, "none")
            return (dummy_shot, "", "", 0.0, False)
        
        shot_id = schedule.generation_order[current_index]
        shot = schedule.get_shot_by_id(shot_id)
        
        has_more = current_index < len(schedule.generation_order) - 1
        
        return (
            shot,
            shot.shot_id,
            shot.scene.prompt,
            shot.scene.duration,
            has_more,
        )

