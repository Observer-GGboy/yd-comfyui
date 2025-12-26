"""
ArcFace utility functions for identity comparison
"""

import torch
from typing import Union, Optional
import numpy as np


def normalize_embedding(embedding: Union[torch.Tensor, np.ndarray]) -> torch.Tensor:
    """
    Normalize embedding to unit vector.
    
    Args:
        embedding: Input embedding (torch.Tensor or numpy.ndarray)
        
    Returns:
        Normalized embedding as torch.Tensor
    """
    if isinstance(embedding, np.ndarray):
        embedding = torch.from_numpy(embedding).float()
    
    norm = torch.norm(embedding)
    if norm > 1e-8:
        return embedding / norm
    return embedding


def compute_similarity(
    embedding_a: Union[torch.Tensor, np.ndarray],
    embedding_b: Union[torch.Tensor, np.ndarray],
) -> float:
    """
    Compute cosine similarity between two embeddings.
    
    Args:
        embedding_a: First embedding
        embedding_b: Second embedding
        
    Returns:
        Cosine similarity in range [0, 1]
    """
    a_norm = normalize_embedding(embedding_a)
    b_norm = normalize_embedding(embedding_b)
    
    similarity = torch.dot(a_norm.flatten(), b_norm.flatten()).item()
    
    # Clamp to valid range
    return max(0.0, min(1.0, similarity))


def batch_compute_similarity(
    reference: Union[torch.Tensor, np.ndarray],
    targets: list,
) -> list:
    """
    Compute similarity between reference and multiple targets.
    
    Args:
        reference: Reference embedding
        targets: List of target embeddings
        
    Returns:
        List of similarity scores
    """
    ref_norm = normalize_embedding(reference)
    
    similarities = []
    for target in targets:
        tgt_norm = normalize_embedding(target)
        sim = torch.dot(ref_norm.flatten(), tgt_norm.flatten()).item()
        similarities.append(max(0.0, min(1.0, sim)))
    
    return similarities


def is_identity_match(
    embedding_a: Union[torch.Tensor, np.ndarray],
    embedding_b: Union[torch.Tensor, np.ndarray],
    threshold: float = 0.65,
) -> bool:
    """
    Check if two embeddings represent the same identity.
    
    Args:
        embedding_a: First embedding
        embedding_b: Second embedding
        threshold: Similarity threshold for match
        
    Returns:
        True if embeddings match (similarity >= threshold)
    """
    similarity = compute_similarity(embedding_a, embedding_b)
    return similarity >= threshold


def find_best_match(
    query: Union[torch.Tensor, np.ndarray],
    candidates: list,
    min_threshold: float = 0.5,
) -> tuple:
    """
    Find the best matching candidate for a query embedding.
    
    Args:
        query: Query embedding
        candidates: List of candidate embeddings
        min_threshold: Minimum similarity to consider a match
        
    Returns:
        Tuple of (best_index, best_similarity) or (-1, 0.0) if no match
    """
    if not candidates:
        return (-1, 0.0)
    
    similarities = batch_compute_similarity(query, candidates)
    
    best_idx = np.argmax(similarities)
    best_sim = similarities[best_idx]
    
    if best_sim >= min_threshold:
        return (best_idx, best_sim)
    
    return (-1, 0.0)

