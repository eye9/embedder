"""
Tests for ChromaDBManager
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from services.chroma_manager import ChromaDBManager
from models.search_result import SearchResult


@pytest.fixture
def temp_db_path():
    """Create a temporary directory for ChromaDB"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def chroma_manager(temp_db_path):
    """Create a ChromaDBManager instance with temporary storage"""
    return ChromaDBManager(db_path=temp_db_path, collection_name="test_tnved")


def test_initialization(temp_db_path):
    """Test ChromaDB manager initialization"""
    manager = ChromaDBManager(db_path=temp_db_path, collection_name="test_collection")
    
    assert manager.db_path == temp_db_path
    assert manager.collection_name == "test_collection"
    assert manager.count() == 0


def test_add_batch(chroma_manager):
    """Test adding a batch of records"""
    ids = ["0901110000", "0901120000"]
    embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    metadatas = [
        {"description": "Coffee beans"},
        {"description": "Tea leaves"}
    ]
    documents = ["coffee beans", "tea leaves"]
    
    chroma_manager.add_batch(ids, embeddings, metadatas, documents)
    
    assert chroma_manager.count() == 2


def test_add_batch_upsert(chroma_manager):
    """Test that adding duplicate IDs updates existing records"""
    ids = ["0901110000"]
    embeddings = [[0.1, 0.2, 0.3]]
    metadatas = [{"description": "Coffee beans"}]
    documents = ["coffee beans"]
    
    # Add first time
    chroma_manager.add_batch(ids, embeddings, metadatas, documents)
    assert chroma_manager.count() == 1
    
    # Add again with updated data
    updated_metadatas = [{"description": "Coffee beans updated"}]
    updated_documents = ["coffee beans updated"]
    chroma_manager.add_batch(ids, embeddings, updated_metadatas, updated_documents)
    
    # Count should still be 1 (upsert, not insert)
    assert chroma_manager.count() == 1
    
    # Verify the data was updated
    result = chroma_manager.get_by_code("0901110000")
    assert result is not None
    assert result["metadata"]["description"] == "Coffee beans updated"


def test_add_batch_validation(chroma_manager):
    """Test that add_batch validates input lengths"""
    ids = ["0901110000", "0901120000"]
    embeddings = [[0.1, 0.2, 0.3]]  # Wrong length
    metadatas = [{"description": "Coffee"}]
    documents = ["coffee"]
    
    with pytest.raises(ValueError, match="All input lists must have the same length"):
        chroma_manager.add_batch(ids, embeddings, metadatas, documents)


def test_add_batch_empty(chroma_manager):
    """Test that add_batch handles empty lists gracefully"""
    chroma_manager.add_batch([], [], [], [])
    assert chroma_manager.count() == 0


def test_query(chroma_manager):
    """Test similarity search query"""
    # Add some test data
    ids = ["0901110000", "0901120000", "0901130000"]
    embeddings = [
        [1.0, 0.0, 0.0],
        [0.0, 1.0, 0.0],
        [0.0, 0.0, 1.0]
    ]
    metadatas = [
        {"description": "Coffee beans"},
        {"description": "Tea leaves"},
        {"description": "Cocoa beans"}
    ]
    documents = ["coffee beans", "tea leaves", "cocoa beans"]
    
    chroma_manager.add_batch(ids, embeddings, metadatas, documents)
    
    # Query with a vector similar to the first embedding
    query_embedding = [0.9, 0.1, 0.0]
    results = chroma_manager.query(query_embedding, n_results=2)
    
    assert len(results["ids"][0]) == 2
    assert "0901110000" in results["ids"][0]


def test_query_empty_collection(chroma_manager):
    """Test querying an empty collection"""
    query_embedding = [1.0, 0.0, 0.0]
    results = chroma_manager.query(query_embedding, n_results=5)
    
    assert len(results["ids"][0]) == 0


def test_query_validation(chroma_manager):
    """Test that query validates n_results parameter"""
    query_embedding = [1.0, 0.0, 0.0]
    
    with pytest.raises(ValueError, match="n_results must be positive"):
        chroma_manager.query(query_embedding, n_results=0)
    
    with pytest.raises(ValueError, match="n_results must be positive"):
        chroma_manager.query(query_embedding, n_results=-1)


def test_get_by_code(chroma_manager):
    """Test retrieving a specific record by code"""
    ids = ["0901110000"]
    embeddings = [[0.1, 0.2, 0.3]]
    metadatas = [{"description": "Coffee beans"}]
    documents = ["coffee beans"]
    
    chroma_manager.add_batch(ids, embeddings, metadatas, documents)
    
    result = chroma_manager.get_by_code("0901110000")
    
    assert result is not None
    assert result["id"] == "0901110000"
    assert result["metadata"]["description"] == "Coffee beans"
    assert result["document"] == "coffee beans"


def test_get_by_code_not_found(chroma_manager):
    """Test retrieving a non-existent code"""
    result = chroma_manager.get_by_code("9999999999")
    assert result is None


def test_count(chroma_manager):
    """Test counting records"""
    assert chroma_manager.count() == 0
    
    ids = ["0901110000", "0901120000"]
    embeddings = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    metadatas = [{"description": "Coffee"}, {"description": "Tea"}]
    documents = ["coffee", "tea"]
    
    chroma_manager.add_batch(ids, embeddings, metadatas, documents)
    
    assert chroma_manager.count() == 2


def test_to_search_results(chroma_manager):
    """Test converting ChromaDB results to SearchResult objects"""
    # Add test data
    ids = ["0901110000", "0901120000"]
    embeddings = [[1.0, 0.0], [0.0, 1.0]]
    metadatas = [
        {"description": "Coffee beans"},
        {"description": "Tea leaves"}
    ]
    documents = ["coffee beans", "tea leaves"]
    
    chroma_manager.add_batch(ids, embeddings, metadatas, documents)
    
    # Query
    query_embedding = [1.0, 0.0]
    query_results = chroma_manager.query(query_embedding, n_results=2)
    
    # Convert to SearchResult objects
    search_results = chroma_manager.to_search_results(query_results)
    
    assert len(search_results) == 2
    assert all(isinstance(r, SearchResult) for r in search_results)
    assert all(0.0 <= r.similarity_score <= 1.0 for r in search_results)
    assert search_results[0].code in ["0901110000", "0901120000"]


def test_reset(chroma_manager):
    """Test resetting the collection"""
    # Add some data
    ids = ["0901110000"]
    embeddings = [[0.1, 0.2, 0.3]]
    metadatas = [{"description": "Coffee"}]
    documents = ["coffee"]
    
    chroma_manager.add_batch(ids, embeddings, metadatas, documents)
    assert chroma_manager.count() == 1
    
    # Reset
    chroma_manager.reset()
    
    # Collection should be empty
    assert chroma_manager.count() == 0
