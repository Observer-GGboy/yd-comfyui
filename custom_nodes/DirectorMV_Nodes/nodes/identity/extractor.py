"""
DMV_IdentityExtractor - Extract identity embeddings from face images

Uses InsightFace/ArcFace for identity embedding extraction.
This node works standalone and can be connected to PuLID workflow outputs.
"""

import torch
import numpy as np
from typing import Tuple, Optional
import logging

logger = logging.getLogger("DirectorMV.Identity")

# Try to import insightface for ArcFace
try:
    from insightface.app import FaceAnalysis
    INSIGHTFACE_AVAILABLE = True
except ImportError:
    INSIGHTFACE_AVAILABLE = False
    logger.warning("InsightFace not available. Identity extraction will be limited.")


class DMV_IdentityExtractor:
    """
    Extract identity embedding from a face image using ArcFace.
    
    This is a standalone node that can work with any face image input.
    For best results, use with properly cropped/aligned face images.
    """
    
    _face_analyzer: Optional["FaceAnalysis"] = None
    
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "image": ("IMAGE",),
            },
            "optional": {
                "detection_threshold": ("FLOAT", {
                    "default": 0.5,
                    "min": 0.1,
                    "max": 1.0,
                    "step": 0.05,
                    "display": "slider",
                }),
            }
        }
    
    RETURN_TYPES = ("IDENTITY_EMBEDDING", "FLOAT", "IMAGE")
    RETURN_NAMES = ("embedding", "confidence", "face_crop")
    FUNCTION = "extract_identity"
    CATEGORY = "DirectorMV/Identity"
    
    @classmethod
    def get_face_analyzer(cls) -> Optional["FaceAnalysis"]:
        """Lazy load face analyzer."""
        if not INSIGHTFACE_AVAILABLE:
            return None
        
        if cls._face_analyzer is None:
            try:
                cls._face_analyzer = FaceAnalysis(
                    name="buffalo_l",
                    providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
                )
                cls._face_analyzer.prepare(ctx_id=0, det_size=(640, 640))
                logger.info("FaceAnalysis initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize FaceAnalysis: {e}")
                return None
        
        return cls._face_analyzer
    
    def extract_identity(
        self,
        image: torch.Tensor,
        detection_threshold: float = 0.5,
    ) -> Tuple[torch.Tensor, float, torch.Tensor]:
        """
        Extract identity embedding from image.
        
        Args:
            image: Input image tensor [B, H, W, C] in range [0, 1]
            detection_threshold: Face detection confidence threshold
            
        Returns:
            embedding: Identity embedding tensor [512]
            confidence: Detection confidence score
            face_crop: Cropped face region
        """
        # Convert to numpy for insightface
        if image.dim() == 4:
            img_np = image[0].cpu().numpy()
        else:
            img_np = image.cpu().numpy()
        
        # Convert from [0,1] float to [0,255] uint8
        img_np = (img_np * 255).astype(np.uint8)
        
        # Convert RGB to BGR for insightface
        img_bgr = img_np[:, :, ::-1].copy()
        
        analyzer = self.get_face_analyzer()
        
        if analyzer is None:
            # Fallback: return zero embedding if insightface not available
            logger.warning("InsightFace not available, returning zero embedding")
            embedding = torch.zeros(512, dtype=torch.float32)
            return (embedding, 0.0, image)
        
        # Detect faces
        faces = analyzer.get(img_bgr)
        
        if len(faces) == 0:
            logger.warning("No face detected in image")
            embedding = torch.zeros(512, dtype=torch.float32)
            return (embedding, 0.0, image)
        
        # Get the face with highest detection score
        face = max(faces, key=lambda x: x.det_score)
        
        if face.det_score < detection_threshold:
            logger.warning(f"Face detection score {face.det_score:.3f} below threshold {detection_threshold}")
        
        # Extract embedding
        embedding = torch.from_numpy(face.embedding).float()
        
        # Normalize embedding
        embedding = embedding / (torch.norm(embedding) + 1e-8)
        
        # Crop face region
        bbox = face.bbox.astype(int)
        x1, y1, x2, y2 = bbox
        
        # Ensure valid crop bounds
        h, w = img_np.shape[:2]
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(w, x2), min(h, y2)
        
        face_crop = img_np[y1:y2, x1:x2]
        face_crop_tensor = torch.from_numpy(face_crop).float() / 255.0
        face_crop_tensor = face_crop_tensor.unsqueeze(0)  # Add batch dim
        
        confidence = float(face.det_score)
        
        logger.info(f"Identity extracted with confidence {confidence:.3f}")
        
        return (embedding, confidence, face_crop_tensor)


# Alias for backward compatibility
IdentityExtractor = DMV_IdentityExtractor

