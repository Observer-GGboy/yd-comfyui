"""
Storyboard data schemas for DirectorMV
"""

from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class SceneLayout(str, Enum):
    """Layout options for a scene."""
    SAME_FRAME = "same_frame"
    SINGLE_A = "single_A"
    SINGLE_B = "single_B"
    SPLIT = "split"
    OVERLAY = "overlay"


class TransitionType(str, Enum):
    """Transition types between scenes."""
    CUT = "cut"
    FADE = "fade"
    DISSOLVE = "dissolve"
    WIPE = "wipe"


class CameraMovement(str, Enum):
    """Camera movement options."""
    STATIC = "static"
    PAN_LEFT = "pan_left"
    PAN_RIGHT = "pan_right"
    TILT_UP = "tilt_up"
    TILT_DOWN = "tilt_down"
    ZOOM_IN = "zoom_in"
    ZOOM_OUT = "zoom_out"
    TRACKING = "tracking"


class CameraAngle(str, Enum):
    """Camera angle options."""
    CLOSE_UP = "close_up"
    MEDIUM_SHOT = "medium_shot"
    FULL_SHOT = "full_shot"
    WIDE_SHOT = "wide_shot"
    OVER_SHOULDER = "over_shoulder"


@dataclass
class CameraConfig:
    """Camera configuration for a scene."""
    movement: CameraMovement = CameraMovement.STATIC
    angle: CameraAngle = CameraAngle.MEDIUM_SHOT
    movement_intensity: float = 0.5
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "movement": self.movement.value,
            "angle": self.angle.value,
            "movement_intensity": self.movement_intensity,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CameraConfig":
        return cls(
            movement=CameraMovement(data.get("movement", "static")),
            angle=CameraAngle(data.get("angle", "medium_shot")),
            movement_intensity=data.get("movement_intensity", 0.5),
        )


@dataclass
class AudioConfig:
    """Audio configuration for a scene."""
    has_dialogue: bool = False
    dialogue_text: str = ""
    speaker: str = ""
    background_music: bool = False
    sound_effects: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "has_dialogue": self.has_dialogue,
            "dialogue_text": self.dialogue_text,
            "speaker": self.speaker,
            "background_music": self.background_music,
            "sound_effects": self.sound_effects,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AudioConfig":
        return cls(
            has_dialogue=data.get("has_dialogue", False),
            dialogue_text=data.get("dialogue_text", ""),
            speaker=data.get("speaker", ""),
            background_music=data.get("background_music", False),
            sound_effects=data.get("sound_effects", []),
        )


@dataclass
class SceneSchema:
    """Schema for a single scene in the storyboard."""
    scene_id: str
    duration: float
    characters: List[str]
    layout: SceneLayout
    prompt: str
    reference_image: Optional[str] = None
    camera: CameraConfig = field(default_factory=CameraConfig)
    audio: AudioConfig = field(default_factory=AudioConfig)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.scene_id,
            "duration": self.duration,
            "characters": self.characters,
            "layout": self.layout.value if isinstance(self.layout, SceneLayout) else self.layout,
            "prompt": self.prompt,
            "reference_image": self.reference_image,
            "camera": self.camera.to_dict() if isinstance(self.camera, CameraConfig) else self.camera,
            "audio": self.audio.to_dict() if isinstance(self.audio, AudioConfig) else self.audio,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SceneSchema":
        return cls(
            scene_id=data.get("id", "scene_unknown"),
            duration=data.get("duration", 5.0),
            characters=data.get("characters", []),
            layout=SceneLayout(data.get("layout", "single_A")) if isinstance(data.get("layout"), str) else data.get("layout", SceneLayout.SINGLE_A),
            prompt=data.get("prompt", ""),
            reference_image=data.get("reference_image"),
            camera=CameraConfig.from_dict(data.get("camera", {})),
            audio=AudioConfig.from_dict(data.get("audio", {})),
            metadata=data.get("metadata", {}),
        )


@dataclass
class TransitionSchema:
    """Schema for a transition between scenes."""
    from_scene: str
    to_scene: str
    transition_type: TransitionType = TransitionType.CUT
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "from": self.from_scene,
            "to": self.to_scene,
            "type": self.transition_type.value,
            "duration": self.duration,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TransitionSchema":
        return cls(
            from_scene=data.get("from", ""),
            to_scene=data.get("to", ""),
            transition_type=TransitionType(data.get("type", "cut")),
            duration=data.get("duration", 0.0),
        )


@dataclass
class StoryboardSchema:
    """Complete storyboard schema."""
    title: str = "Untitled MV"
    scenes: List[SceneSchema] = field(default_factory=list)
    transitions: List[TransitionSchema] = field(default_factory=list)
    characters: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def total_duration(self) -> float:
        """Calculate total duration of all scenes."""
        return sum(s.duration for s in self.scenes)
    
    def scene_count(self) -> int:
        """Get number of scenes."""
        return len(self.scenes)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "scenes": [s.to_dict() for s in self.scenes],
            "transitions": [t.to_dict() for t in self.transitions],
            "characters": self.characters,
            "metadata": self.metadata,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StoryboardSchema":
        return cls(
            title=data.get("title", "Untitled MV"),
            scenes=[SceneSchema.from_dict(s) for s in data.get("scenes", [])],
            transitions=[TransitionSchema.from_dict(t) for t in data.get("transitions", [])],
            characters=data.get("characters", {}),
            metadata=data.get("metadata", {}),
        )
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        import json
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False)
    
    @classmethod
    def from_json(cls, json_str: str) -> "StoryboardSchema":
        """Create from JSON string."""
        import json
        data = json.loads(json_str)
        return cls.from_dict(data)

