"""
Tests for ProductLoader service
"""

import pytest
import tempfile
import pandas as pd
from pathlib import Path

from services.product_loader import ProductLoader, DataLoadError
from services.text_normalizer import TextNormalizer
from services.embedding_generator import EmbeddingGenerator
from utils.config import Config


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
    config = Config()
    normalizer = TextNormalizer()
    embedder = EmbeddingGenerator(config.model.name, config.model.device)
    loader = ProductLoader(temp_db_path, normalizer, embedder, batch_size=10)
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
        config = Config()
        normalizer = TextNormalizer()
        embedder = EmbeddingGenerator(config.model.name, config.model.device)
        
        loader = ProductLoader(temp_db_path, normalizer, embedder)
        
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
        config = Config()
        normalizer = TextNormalizer()
        embedder = EmbeddingGenerator(config.model.name, config.model.device)
        
        with pytest.raises(ValueError, match="batch_size must be positive"):
            ProductLoader(temp_db_path, normalizer, embedder, batch_size=0)
    
    def test_load_from_excel_basic(self, product_loader, sample_excel_file):
        """Test basic Excel loading functionality"""
        count = product_loader.load_from_excel(sample_excel_file, "test_source")
        
        assert count == 3
        assert product_loader.get_record_count() == 3
    
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
        
        # Verify records were stored with unique IDs
        # The first record with code 0901110000 should use the code as ID
        # The second record with same code should get a unique ID like 0901110000_001
        record_count = product_loader.get_record_count()
        assert record_count == 3


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
        
        config = Config()
        normalizer = TextNormalizer()
        embedder = EmbeddingGenerator(config.model.name, config.model.device)
        loader = ProductLoader(temp_db, normalizer, embedder)
        
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