"""
DMV_StoryboardParser - Parse storyboard scripts into structured shot lists

Supports multiple input formats:
- JSON structured scripts
- YAML structured scripts
- Simple text descriptions (with predefined templates)
"""

import json
import re
from typing import Tuple, Dict, Any, List, Optional
import logging

logger = logging.getLogger("DirectorMV.Storyboard")

# Try to import yaml
try:
    import yaml
    YAML_AVAILABLE = True
except ImportError:
    YAML_AVAILABLE = False


class StoryboardScene:
    """Represents a single scene in the storyboard."""
    
    def __init__(
        self,
        scene_id: str,
        duration: float,
        characters: List[str],
        layout: str,
        prompt: str,
        reference_image: Optional[str] = None,
        camera: Optional[Dict[str, str]] = None,
        audio: Optional[Dict[str, Any]] = None,
    ):
        self.scene_id = scene_id
        self.duration = duration
        self.characters = characters
        self.layout = layout  # "same_frame", "split", "single_A", "single_B"
        self.prompt = prompt
        self.reference_image = reference_image
        self.camera = camera or {"movement": "static", "angle": "medium_shot"}
        self.audio = audio
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.scene_id,
            "duration": self.duration,
            "characters": self.characters,
            "layout": self.layout,
            "prompt": self.prompt,
            "reference_image": self.reference_image,
            "camera": self.camera,
            "audio": self.audio,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoryboardScene":
        return cls(
            scene_id=data.get("id", "scene_unknown"),
            duration=data.get("duration", 5.0),
            characters=data.get("characters", []),
            layout=data.get("layout", "single_A"),
            prompt=data.get("prompt", ""),
            reference_image=data.get("reference_image"),
            camera=data.get("camera"),
            audio=data.get("audio"),
        )


class Storyboard:
    """Complete storyboard with scenes and transitions."""
    
    def __init__(self):
        self.scenes: List[StoryboardScene] = []
        self.transitions: List[Dict[str, Any]] = []
        self.metadata: Dict[str, Any] = {}
    
    def add_scene(self, scene: StoryboardScene):
        self.scenes.append(scene)
    
    def add_transition(self, from_scene: str, to_scene: str, 
                       transition_type: str = "cut", duration: float = 0):
        self.transitions.append({
            "from": from_scene,
            "to": to_scene,
            "type": transition_type,
            "duration": duration,
        })
    
    def total_duration(self) -> float:
        return sum(s.duration for s in self.scenes)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "scenes": [s.to_dict() for s in self.scenes],
            "transitions": self.transitions,
            "metadata": self.metadata,
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Storyboard":
        sb = cls()
        sb.metadata = data.get("metadata", {})
        
        for scene_data in data.get("scenes", []):
            sb.add_scene(StoryboardScene.from_dict(scene_data))
        
        sb.transitions = data.get("transitions", [])
        return sb


class DMV_StoryboardParser:
    """
    Parse storyboard scripts into structured format.
    
    Supports:
    - JSON format
    - YAML format
    - Simple text with template matching
    """
    
    @classmethod
    def INPUT_TYPES(cls):
        formats = ["auto", "json", "text"]
        if YAML_AVAILABLE:
            formats.insert(2, "yaml")
        
        return {
            "required": {
                "script": ("STRING", {
                    "default": "",
                    "multiline": True,
                }),
                "format": (formats,),
            },
            "optional": {
                "default_duration": ("FLOAT", {
                    "default": 5.0,
                    "min": 1.0,
                    "max": 30.0,
                    "step": 0.5,
                }),
                "character_a_name": ("STRING", {"default": "A"}),
                "character_b_name": ("STRING", {"default": "B"}),
            }
        }
    
    RETURN_TYPES = ("STORYBOARD", "STRING", "INT", "FLOAT")
    RETURN_NAMES = ("storyboard", "json_output", "scene_count", "total_duration")
    FUNCTION = "parse_storyboard"
    CATEGORY = "DirectorMV/Storyboard"
    
    def parse_storyboard(
        self,
        script: str,
        format: str,
        default_duration: float = 5.0,
        character_a_name: str = "A",
        character_b_name: str = "B",
    ) -> Tuple[Storyboard, str, int, float]:
        """
        Parse storyboard script.
        
        Args:
            script: Raw storyboard script
            format: Input format (auto, json, yaml, text)
            default_duration: Default scene duration
            character_a_name: Name for character A
            character_b_name: Name for character B
            
        Returns:
            storyboard: Parsed Storyboard object
            json_output: JSON string representation
            scene_count: Number of scenes
            total_duration: Total duration in seconds
        """
        script = script.strip()
        
        if not script:
            # Return empty storyboard
            sb = Storyboard()
            return (sb, sb.to_json(), 0, 0.0)
        
        # Auto-detect format
        if format == "auto":
            if script.startswith("{"):
                format = "json"
            elif YAML_AVAILABLE and (script.startswith("scenes:") or script.startswith("---")):
                format = "yaml"
            else:
                format = "text"
        
        # Parse based on format
        if format == "json":
            storyboard = self._parse_json(script)
        elif format == "yaml" and YAML_AVAILABLE:
            storyboard = self._parse_yaml(script)
        else:
            storyboard = self._parse_text(script, default_duration, 
                                          character_a_name, character_b_name)
        
        json_output = storyboard.to_json()
        scene_count = len(storyboard.scenes)
        total_duration = storyboard.total_duration()
        
        logger.info(f"Parsed storyboard: {scene_count} scenes, {total_duration}s total")
        
        return (storyboard, json_output, scene_count, total_duration)
    
    def _parse_json(self, script: str) -> Storyboard:
        """Parse JSON format storyboard."""
        try:
            data = json.loads(script)
            return Storyboard.from_dict(data)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            raise ValueError(f"Invalid JSON: {e}")
    
    def _parse_yaml(self, script: str) -> Storyboard:
        """Parse YAML format storyboard."""
        try:
            data = yaml.safe_load(script)
            return Storyboard.from_dict(data)
        except yaml.YAMLError as e:
            logger.error(f"YAML parse error: {e}")
            raise ValueError(f"Invalid YAML: {e}")
    
    def _parse_text(
        self,
        script: str,
        default_duration: float,
        char_a: str,
        char_b: str,
    ) -> Storyboard:
        """
        Parse simple text format.
        
        Expected format (one scene per line):
        [duration]s [characters] - description
        
        Examples:
        5s A - Character A walks into frame
        5s A,B - Both characters talking
        3s B - Close up on B's face
        """
        storyboard = Storyboard()
        lines = [l.strip() for l in script.split("\n") if l.strip()]
        
        scene_pattern = re.compile(
            r"^(?:(\d+(?:\.\d+)?)\s*s\s+)?([A-Za-z,\s]+)\s*[-:]\s*(.+)$"
        )
        
        for i, line in enumerate(lines):
            # Skip comments
            if line.startswith("#") or line.startswith("//"):
                continue
            
            match = scene_pattern.match(line)
            if match:
                duration_str, chars_str, prompt = match.groups()
                
                duration = float(duration_str) if duration_str else default_duration
                
                # Parse characters
                chars = [c.strip().upper() for c in chars_str.split(",")]
                characters = []
                for c in chars:
                    if c == "A" or c == char_a.upper():
                        characters.append(char_a)
                    elif c == "B" or c == char_b.upper():
                        characters.append(char_b)
                
                # Determine layout
                if len(characters) == 2:
                    layout = "same_frame"
                elif characters and characters[0] == char_a:
                    layout = "single_A"
                else:
                    layout = "single_B"
                
                scene = StoryboardScene(
                    scene_id=f"scene_{i+1}",
                    duration=duration,
                    characters=characters,
                    layout=layout,
                    prompt=prompt.strip(),
                )
                storyboard.add_scene(scene)
            else:
                # Treat as simple prompt for single character
                scene = StoryboardScene(
                    scene_id=f"scene_{i+1}",
                    duration=default_duration,
                    characters=[char_a],
                    layout="single_A",
                    prompt=line,
                )
                storyboard.add_scene(scene)
        
        # Add default cut transitions between scenes
        for i in range(len(storyboard.scenes) - 1):
            storyboard.add_transition(
                storyboard.scenes[i].scene_id,
                storyboard.scenes[i+1].scene_id,
                "cut",
                0,
            )
        
        return storyboard

