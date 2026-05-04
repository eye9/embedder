"""
Tests for ProductLoader service
"""

import pytest
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path

from services.product_loader import ProductLoader, SourceAlreadyExistsError


class DummyNormalizer:
    """Lightweight normalizer for product loader tests."""

    def normalize(self, text):
        return str(text).lower()


class DummyEmbedder:
    """Deterministic embedder that avoids loading external ML models in tests."""

    def generate(self, texts, batch_size=100, prefix=""):
        return np.array([[float(i), 0.0, 0.0] for i, _ in enumerate(texts, start=1)])


@pytest.fixture
def temp_db_path():
    """Create temporary database path for testing"""
    import time
    import gc
    
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    
    # Force garbage collection to release any ChromaDB connections
    gc.collect()
    time.sleep(0.1)  # Brief pause to allow file handles to close
    
    # Try to clean up, but don't fail if it doesn't work on Windows
    try:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)
    except:
        pass


@pytest.fixture
def product_loader(temp_db_path):
    """Create ProductLoader instance for testing"""
    loader = ProductLoader(temp_db_path, DummyNormalizer(), DummyEmbedder(), batch_size=10)
    yield loader
    # Ensure proper cleanup
    if hasattr(loader, 'db_manager') and hasattr(loader.db_manager, 'client'):
        try:
            loader.db_manager.client.reset()
        except:
            pass


@pytest.fixture
def sample_excel_file():
    """Create sample Excel file for testing"""
    temp_file = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file_obj:
            temp_file = temp_file_obj.name
            # Create sample data
            data = {
                'Code': ['0901110000', '0901110000', '0902000000'],
                'TextEx': ['Кофе арабика зерновой 1кг', 'Кофе арабика молотый 500г', 'Чай черный листовой'],
                'SourceID': ['декларация_001', 'декларация_002', 'декларация_003']
            }
            df = pd.DataFrame(data)
            df.to_excel(temp_file, index=False)
        
        yield temp_file
        
    finally:
        # Clean up
        if temp_file:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except:
                pass


class TestProductLoader:
    """Test cases for ProductLoader"""
    
    def test_initialization(self, temp_db_path):
        """Test ProductLoader initialization"""
        loader = ProductLoader(temp_db_path, DummyNormalizer(), DummyEmbedder())
        
        try:
            assert loader.batch_size == 100
            assert loader.get_record_count() == 0
        finally:
            # Ensure proper cleanup
            if hasattr(loader, 'db_manager') and hasattr(loader.db_manager, 'client'):
                try:
                    loader.db_manager.client.reset()
                except:
                    pass
    
    def test_initialization_invalid_batch_size(self, temp_db_path):
        """Test ProductLoader initialization with invalid batch size"""
        with pytest.raises(ValueError, match="batch_size must be positive"):
            ProductLoader(temp_db_path, DummyNormalizer(), DummyEmbedder(), batch_size=0)
    
    def test_load_from_excel_basic(self, product_loader, sample_excel_file):
        """Test basic Excel loading functionality"""
        count = product_loader.load_from_excel(sample_excel_file, "test_source")
        
        assert count == 3
        assert product_loader.get_record_count() == 3

        results = product_loader.db_manager.collection.get(include=["metadatas"])
        metadatas_by_id = dict(zip(results["ids"], results["metadatas"]))

        assert set(results["ids"]) == {
            "product:0901110000:test_source:2",
            "product:0901110000:test_source:3",
            "product:0902000000:test_source:4",
        }
        assert metadatas_by_id["product:0901110000:test_source:2"]["source_id"] == "декларация_001"
        assert metadatas_by_id["product:0901110000:test_source:3"]["source_id"] == "декларация_002"
        assert metadatas_by_id["product:0901110000:test_source:2"]["excel_row_number"] == 2
    
    def test_load_from_excel_missing_file(self, product_loader):
        """Test loading from non-existent file"""
        with pytest.raises(FileNotFoundError):
            product_loader.load_from_excel("nonexistent.xlsx", "test_source")
    
    def test_load_from_excel_empty_source_name(self, product_loader, sample_excel_file):
        """Test loading with empty source name"""
        with pytest.raises(ValueError, match="source_name cannot be empty"):
            product_loader.load_from_excel(sample_excel_file, "")
    
    def test_validate_source_information(self, product_loader):
        """Test source information validation"""
        # Valid cases
        assert product_loader.validate_source_information("valid_source") == True
        assert product_loader.validate_source_information("valid_source", "valid_id") == True
        
        # Invalid cases
        assert product_loader.validate_source_information("") == False
        assert product_loader.validate_source_information("   ") == False
        assert product_loader.validate_source_information("valid_source", "") == False
    
    def test_duplicate_handling(self, product_loader, sample_excel_file):
        """Test that duplicate codes get unique IDs"""
        # Load the sample file which has duplicate codes
        count = product_loader.load_from_excel(sample_excel_file, "test_source")
        
        assert count == 3
        
        results = product_loader.db_manager.collection.get(include=["metadatas"])
        assert len(set(results["ids"])) == 3
        assert "product:0901110000:test_source:2" in results["ids"]
        assert "product:0901110000:test_source:3" in results["ids"]

    def test_duplicate_source_requires_replace_existing(self, product_loader, sample_excel_file):
        """Test repeated source_name loads require explicit replacement."""
        product_loader.load_from_excel(sample_excel_file, "test_source")

        with pytest.raises(SourceAlreadyExistsError, match="already has 3 records"):
            product_loader.load_from_excel(sample_excel_file, "test_source")

        assert product_loader.get_record_count() == 3

    def test_replace_existing_replaces_only_same_product_source(self, product_loader, sample_excel_file):
        """Test replacement deletes only product records for the selected source."""
        product_loader.load_from_excel(sample_excel_file, "test_source")
        product_loader.load_from_excel(sample_excel_file, "other_source")
        product_loader.db_manager.add_batch(
            ids=["0901110000"],
            embeddings=[[0.0, 1.0, 0.0]],
            metadatas=[{"description": "Reference coffee", "code": "0901110000"}],
            documents=["reference coffee"],
            source_type="reference"
        )

        replacement_file = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as temp_file_obj:
                replacement_file = temp_file_obj.name
                pd.DataFrame({
                    "Code": ["0903000000"],
                    "TextEx": ["Мате"],
                    "SourceID": ["декларация_new"]
                }).to_excel(replacement_file, index=False)

            count = product_loader.load_from_excel(
                replacement_file,
                "test_source",
                replace_existing=True
            )

            assert count == 1
            assert product_loader.count_product_records_by_source("test_source") == 1
            assert product_loader.count_product_records_by_source("other_source") == 3
            assert product_loader.get_statistics_by_source_type()["reference"] == 1
            assert product_loader.get_record_count() == 5
        finally:
            if replacement_file:
                Path(replacement_file).unlink(missing_ok=True)

    def test_product_id_supports_more_than_9999_rows(self, product_loader):
        """Test product ID generation has no 9999 suffix limit."""
        product_id = product_loader._generate_product_id("9505900000", "2026m3", 10001)

        assert product_id == "product:9505900000:2026m3:10001"


def test_excel_format_compatibility():
    """Test that ProductLoader can read the same Excel format as TNVEDLoader"""
    import time
    import gc
    import shutil
    
    temp_file = None
    temp_db = None
    loader = None
    
    try:
        # Create temp file
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as temp_file_obj:
            temp_file = temp_file_obj.name
            # Create Excel file with same format as TNVEDLoader expects
            data = {
                'Code': ['0901110000', '0902000000'],
                'TextEx': ['КОФЕ НЕЖАРЕНЫЙ НЕОСВОБОЖДЕННЫЙ ОТ КОФЕИНА', 'ЧАЙ']
            }
            df = pd.DataFrame(data)
            df.to_excel(temp_file, index=False)
        
        # Create temp db directory
        temp_db = tempfile.mkdtemp()
        
        loader = ProductLoader(temp_db, DummyNormalizer(), DummyEmbedder())
        
        # Should load successfully with same format
        count = loader.load_from_excel(temp_file, "test_source")
        assert count == 2
        
    finally:
        # Cleanup ChromaDB connection
        if loader and hasattr(loader, 'db_manager') and hasattr(loader.db_manager, 'client'):
            try:
                loader.db_manager.client.reset()
            except:
                pass
        
        # Force cleanup
        loader = None
        gc.collect()
        time.sleep(0.1)
        
        # Cleanup temp file
        if temp_file:
            try:
                Path(temp_file).unlink(missing_ok=True)
            except:
                pass
        
        # Cleanup temp db
        if temp_db:
            try:
                shutil.rmtree(temp_db, ignore_errors=True)
            except:
                pass
