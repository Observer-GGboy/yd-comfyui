"""
DMV_CharacterRouter - Route processing based on character in scene

Routes workflow to appropriate character-specific processing pipelines.
"""

from typing import Tuple, List, Any, Optional
import torch
import logging
from .parser import Storyboard, StoryboardScene
from .scheduler import Shot, ShotSchedule

logger = logging.getLogger("DirectorMV.Storyboard")


class DMV_CharacterRouter:
    """
    Route processing based on characters in the current shot.
    
    Outputs:
    - Which characters are involved
    - Whether it's a dual-character scene
    - Character-specific data (embeddings, images)
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "shot": ("SHOT",),
            },
            "optional": {
                "character_a_embedding": ("IDENTITY_EMBEDDING",),
                "character_b_embedding": ("IDENTITY_EMBEDDING",),
                "character_a_image": ("IMAGE",),
                "character_b_image": ("IMAGE",),
            }
        }
    
    RETURN_TYPES = ("BOOLEAN", "BOOLEAN", "BOOLEAN", "IDENTITY_EMBEDDING", "IDENTITY_EMBEDDING", "IMAGE", "IMAGE", "STRING")
    RETURN_NAMES = ("is_dual", "has_a", "has_b", "active_embedding_a", "active_embedding_b", "active_image_a", "active_image_b", "layout")
    FUNCTION = "route_characters"
    CATEGORY = "DirectorMV/Storyboard"
    
    def route_characters(
        self,
        shot: Shot,
        character_a_embedding: Optional[torch.Tensor] = None,
        character_b_embedding: Optional[torch.Tensor] = None,
        character_a_image: Optional[torch.Tensor] = None,
        character_b_image: Optional[torch.Tensor] = None,
    ) -> Tuple[bool, bool, bool, Any, Any, Any, Any, str]:
        """
        Route based on characters in shot.
        
        Returns flags and data for active characters.
        """
        characters = [c.upper() for c in shot.scene.characters]
        
        has_a = "A" in characters or any("A" in c for c in characters)
        has_b = "B" in characters or any("B" in c for c in characters)
        is_dual = has_a and has_b
        
        layout = shot.scene.layout
        
        # Pass through embeddings/images only for active characters
        active_emb_a = character_a_embedding if has_a else None
        active_emb_b = character_b_embedding if has_b else None
        active_img_a = character_a_image if has_a else None
        active_img_b = character_b_image if has_b else None
        
        # Create zero tensors for None values to maintain type consistency
        if active_emb_a is None:
            active_emb_a = torch.zeros(512, dtype=torch.float32)
        if active_emb_b is None:
            active_emb_b = torch.zeros(512, dtype=torch.float32)
        
        logger.info(f"Routing shot {shot.shot_id}: is_dual={is_dual}, has_a={has_a}, has_b={has_b}")
        
        return (is_dual, has_a, has_b, active_emb_a, active_emb_b, active_img_a, active_img_b, layout)


class DMV_SceneSelector:
    """
    Select a specific scene from storyboard by index or ID.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "storyboard": ("STORYBOARD",),
            },
            "optional": {
                "scene_index": ("INT", {
                    "default": 0,
                    "min": 0,
                    "max": 100,
                }),
                "scene_id": ("STRING", {"default": ""}),
            }
        }
    
    RETURN_TYPES = ("SCENE", "STRING", "FLOAT", "STRING", "STRING")
    RETURN_NAMES = ("scene", "scene_id", "duration", "prompt", "layout")
    FUNCTION = "select_scene"
    CATEGORY = "DirectorMV/Storyboard"
    
    def select_scene(
        self,
        storyboard: Storyboard,
        scene_index: int = 0,
        scene_id: str = "",
    ) -> Tuple[StoryboardScene, str, float, str, str]:
        """Select a scene from storyboard."""
        scene = None
        
        # Try by ID first
        if scene_id:
            for s in storyboard.scenes:
                if s.scene_id == scene_id:
                    scene = s
                    break
        
        # Fall back to index
        if scene is None and scene_index < len(storyboard.scenes):
            scene = storyboard.scenes[scene_index]
        
        if scene is None:
            # Return dummy scene
            scene = StoryboardScene("none", 0, [], "none", "No scene found")
        
        return (scene, scene.scene_id, scene.duration, scene.prompt, scene.layout)


class DMV_StoryboardInfo:
    """
    Get information about a storyboard.
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "storyboard": ("STORYBOARD",),
            }
        }
    
    RETURN_TYPES = ("INT", "FLOAT", "STRING", "STRING")
    RETURN_NAMES = ("scene_count", "total_duration", "character_list", "summary")
    FUNCTION = "get_info"
    CATEGORY = "DirectorMV/Storyboard"
    
    def get_info(
        self,
        storyboard: Storyboard,
    ) -> Tuple[int, float, str, str]:
        """Get storyboard information."""
        scene_count = len(storyboard.scenes)
        total_duration = storyboard.total_duration()
        
        # Collect all unique characters
        all_chars = set()
        for scene in storyboard.scenes:
            all_chars.update(scene.characters)
        character_list = ", ".join(sorted(all_chars))
        
        # Build summary
        layout_counts = {}
        for scene in storyboard.scenes:
            layout_counts[scene.layout] = layout_counts.get(scene.layout, 0) + 1
        
        summary_lines = [
            f"Storyboard Summary",
            f"==================",
            f"Total scenes: {scene_count}",
            f"Total duration: {total_duration:.1f}s",
            f"Characters: {character_list}",
            f"",
            f"Scene breakdown by layout:",
        ]
        for layout, count in layout_counts.items():
            summary_lines.append(f"  {layout}: {count}")
        
        summary = "\n".join(summary_lines)
        
        return (scene_count, total_duration, character_list, summary)

