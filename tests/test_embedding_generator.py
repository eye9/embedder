"""
Tests for EmbeddingGenerator service.
"""

import pytest
import numpy as np
from services.embedding_generator import EmbeddingGenerator


class TestEmbeddingGenerator:
    """Test suite for EmbeddingGenerator class."""
    
    @pytest.fixture
    def generator(self):
        """Create an EmbeddingGenerator instance for testing."""
        # Use CPU for testing to avoid CUDA dependencies
        return EmbeddingGenerator(model_name="ai-forever/FRIDA", device="cpu")
    
    def test_model_initialization(self, generator):
        """Test that model loads successfully."""
        assert generator.model is not None
        assert generator.model_name == "ai-forever/FRIDA"
        assert generator.device == "cpu"
    
    def test_invalid_device_raises_error(self):
        """Test that invalid device raises ValueError."""
        with pytest.raises(ValueError, match="Invalid device"):
            EmbeddingGenerator(device="invalid")
    
    def test_single_text_embedding(self, generator):
        """Test embedding generation for a single text."""
        text = "кофейные зерна"
        embedding = generator.generate(text)
        
        # Should return 1D array for single text
        assert isinstance(embedding, np.ndarray)
        assert embedding.ndim == 1
        assert len(embedding) > 0
    
    def test_batch_text_embeddings(self, generator):
        """Test embedding generation for multiple texts."""
        texts = ["кофе", "чай", "сахар"]
        embeddings = generator.generate(texts)
        
        # Should return 2D array for multiple texts
        assert isinstance(embeddings, np.ndarray)
        assert embeddings.ndim == 2
        assert embeddings.shape[0] == len(texts)
        assert embeddings.shape[1] > 0
    
    def test_embedding_dimension_consistency(self, generator):
        """Test that all embeddings have the same dimension."""
        text1 = "короткий текст"
        text2 = "это более длинный текст с большим количеством слов"
        
        emb1 = generator.generate(text1)
        emb2 = generator.generate(text2)
        
        # Both should have the same dimension
        assert len(emb1) == len(emb2)
    
    def test_batch_size_parameter(self, generator):
        """Test that different batch sizes work correctly."""
        texts = ["текст " + str(i) for i in range(10)]
        
        # Test with different batch sizes
        emb1 = generator.generate(texts, batch_size=2)
        emb2 = generator.generate(texts, batch_size=5)
        
        # Results should have the same shape regardless of batch size
        assert emb1.shape == emb2.shape
    
    def test_empty_text_raises_error(self, generator):
        """Test that empty text raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            generator.generate("")
    
    def test_empty_list_raises_error(self, generator):
        """Test that empty list raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            generator.generate([])
    
    def test_all_empty_texts_raises_error(self, generator):
        """Test that list of all empty texts raises ValueError."""
        with pytest.raises(ValueError, match="empty"):
            generator.generate(["", "   ", ""])
    
    def test_get_embedding_dimension(self, generator):
        """Test getting the embedding dimension."""
        dim = generator.get_embedding_dimension()
        
        assert isinstance(dim, int)
        assert dim > 0
        
        # Verify it matches actual embeddings
        embedding = generator.generate("тест")
        assert len(embedding) == dim
    
    def test_repr(self, generator):
        """Test string representation."""
        repr_str = repr(generator)
        assert "EmbeddingGenerator" in repr_str
        assert "FRIDA" in repr_str
        assert "cpu" in repr_str

