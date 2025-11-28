"""
Embedding generation service using FRIDA model.

This module provides embedding generation functionality using the ai-forever/FRIDA
model from HuggingFace for Russian text embeddings.
"""

import logging
from typing import List, Union
import numpy as np
import torch
from sentence_transformers import SentenceTransformer


logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """
    Generates vector embeddings for Russian text using the FRIDA model.
    
    The FRIDA (ai-forever/FRIDA) model is specifically designed for Russian
    language embeddings and provides high-quality semantic representations.
    
    Features:
    - Batch processing for efficient embedding generation
    - Automatic device management (CPU/GPU)
    - Model caching to avoid reloading
    - Consistent embedding dimensions
    
    Attributes:
        model_name: Name of the HuggingFace model
        device: Device to run the model on ('cpu' or 'cuda')
        model: Loaded SentenceTransformer model
    """
    
    def __init__(self, model_name: str = "ai-forever/FRIDA", device: str = "cpu"):
        """
        Initialize the embedding generator with FRIDA model.
        
        Args:
            model_name: HuggingFace model identifier (default: ai-forever/FRIDA)
            device: Device to run model on - 'cpu' or 'cuda' (default: 'cpu')
            
        Raises:
            ValueError: If device is not 'cpu' or 'cuda'
            RuntimeError: If CUDA is requested but not available
        """
        # Validate device
        if device not in ("cpu", "cuda"):
            raise ValueError(f"Invalid device: {device}. Must be 'cpu' or 'cuda'")
        
        # Check CUDA availability
        if device == "cuda" and not torch.cuda.is_available():
            logger.warning("CUDA requested but not available. Falling back to CPU.")
            device = "cpu"
        
        self.model_name = model_name
        self.device = device
        
        logger.info(f"Loading embedding model: {model_name} on device: {device}")
        
        # Load the model from HuggingFace
        try:
            self.model = SentenceTransformer(model_name, device=device)
            logger.info(f"Successfully loaded model {model_name}")
        except Exception as e:
            logger.error(f"Failed to load model {model_name}: {e}")
            raise
    
    def generate(self, texts: Union[str, List[str]], batch_size: int = 32) -> np.ndarray:
        """
        Generate embeddings for one or more texts.
        
        This method processes texts in batches for efficiency and returns
        consistent vector representations. The same input text will always
        produce the same embedding (deterministic).
        
        Args:
            texts: Single text string or list of text strings to embed
            batch_size: Number of texts to process in each batch (default: 32)
            
        Returns:
            numpy array of embeddings with shape:
            - (embedding_dim,) for single text input
            - (n_texts, embedding_dim) for list input
            
        Raises:
            ValueError: If texts is empty or contains only empty strings
            
        Examples:
            >>> generator = EmbeddingGenerator()
            >>> embedding = generator.generate("кофейные зерна")
            >>> embedding.shape
            (312,)
            >>> embeddings = generator.generate(["кофе", "чай", "сахар"])
            >>> embeddings.shape
            (3, 312)
        """
        # Handle single string input
        if isinstance(texts, str):
            if not texts.strip():
                raise ValueError("Cannot generate embedding for empty text")
            texts = [texts]
            return_single = True
        else:
            return_single = False
        
        # Validate input
        if not texts:
            raise ValueError("Cannot generate embeddings for empty list")
        
        # Filter out empty texts and track indices
        non_empty_texts = []
        non_empty_indices = []
        for i, text in enumerate(texts):
            if text and text.strip():
                non_empty_texts.append(text)
                non_empty_indices.append(i)
        
        if not non_empty_texts:
            raise ValueError("All input texts are empty")
        
        logger.debug(f"Generating embeddings for {len(non_empty_texts)} texts with batch_size={batch_size}")
        
        # Generate embeddings using the model
        try:
            embeddings = self.model.encode(
                non_empty_texts,
                batch_size=batch_size,
                show_progress_bar=False,
                convert_to_numpy=True,
                normalize_embeddings=False  # Keep raw embeddings
            )
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {e}")
            raise
        
        # If we filtered out empty texts, we need to handle the full array
        if len(non_empty_texts) < len(texts):
            # Create full array with zeros for empty texts
            embedding_dim = embeddings.shape[1]
            full_embeddings = np.zeros((len(texts), embedding_dim), dtype=embeddings.dtype)
            for i, idx in enumerate(non_empty_indices):
                full_embeddings[idx] = embeddings[i]
            embeddings = full_embeddings
        
        logger.debug(f"Generated embeddings with shape: {embeddings.shape}")
        
        # Return single embedding if input was a single string
        if return_single:
            return embeddings[0]
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings produced by this model.
        
        Returns:
            Integer dimension of embedding vectors
            
        Examples:
            >>> generator = EmbeddingGenerator()
            >>> generator.get_embedding_dimension()
            312
        """
        return self.model.get_sentence_embedding_dimension()
    
    def __repr__(self) -> str:
        """String representation of the generator."""
        return f"EmbeddingGenerator(model='{self.model_name}', device='{self.device}')"

