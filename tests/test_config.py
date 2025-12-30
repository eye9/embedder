"""
Tests for configuration management
"""

import os
import pytest
import tempfile
from pathlib import Path
from utils.config import Config


def test_config_defaults():
    """Test that Config initializes with correct default values"""
    config = Config()
    
    assert config.model.name == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
    assert config.model.device == "cuda"
    assert config.database.path == "./chroma_db"
    assert config.database.collection_name == "tnved"
    assert config.processing.batch_size == 100
    assert config.search.default_top_k == 5
    assert config.logging.level == "INFO"


def test_config_from_file():
    """Test loading configuration from YAML file"""
    yaml_content = """
model:
  name: "test-model"
  device: "cuda"

database:
  path: "./test_db"
  collection_name: "test_collection"

processing:
  batch_size: 50

search:
  default_top_k: 10

logging:
  level: "DEBUG"
  file: "test.log"
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name
    
    try:
        config = Config.from_file(temp_path)
        
        assert config.model.name == "test-model"
        assert config.model.device == "cuda"
        assert config.database.path == "./test_db"
        assert config.database.collection_name == "test_collection"
        assert config.processing.batch_size == 50
        assert config.search.default_top_k == 10
        assert config.logging.level == "DEBUG"
        assert config.logging.file == "test.log"
    finally:
        os.unlink(temp_path)


def test_config_from_file_not_found():
    """Test that loading from non-existent file raises FileNotFoundError"""
    with pytest.raises(FileNotFoundError):
        Config.from_file("nonexistent.yaml")


def test_config_from_env():
    """Test loading configuration from environment variables"""
    # Set environment variables
    os.environ["TNVED_MODEL_NAME"] = "env-model"
    os.environ["TNVED_MODEL_DEVICE"] = "cuda"
    os.environ["TNVED_DATABASE_PATH"] = "./env_db"
    os.environ["TNVED_BATCH_SIZE"] = "200"
    os.environ["TNVED_DEFAULT_TOP_K"] = "3"
    os.environ["TNVED_LOG_LEVEL"] = "WARNING"
    
    try:
        config = Config.from_env()
        
        assert config.model.name == "env-model"
        assert config.model.device == "cuda"
        assert config.database.path == "./env_db"
        assert config.processing.batch_size == 200
        assert config.search.default_top_k == 3
        assert config.logging.level == "WARNING"
    finally:
        # Clean up environment variables
        for key in ["TNVED_MODEL_NAME", "TNVED_MODEL_DEVICE", "TNVED_DATABASE_PATH",
                    "TNVED_BATCH_SIZE", "TNVED_DEFAULT_TOP_K", "TNVED_LOG_LEVEL"]:
            os.environ.pop(key, None)


def test_config_validation_valid():
    """Test that valid configuration passes validation"""
    config = Config()
    config.validate()  # Should not raise


def test_config_validation_invalid_device():
    """Test that invalid device fails validation"""
    config = Config()
    config.model.device = "invalid"
    
    with pytest.raises(ValueError, match="Invalid device"):
        config.validate()


def test_config_validation_invalid_batch_size():
    """Test that invalid batch size fails validation"""
    config = Config()
    config.processing.batch_size = -1
    
    with pytest.raises(ValueError, match="Invalid batch_size"):
        config.validate()


def test_config_validation_invalid_top_k():
    """Test that invalid top_k fails validation"""
    config = Config()
    config.search.default_top_k = 0
    
    with pytest.raises(ValueError, match="Invalid default_top_k"):
        config.validate()


def test_config_validation_invalid_log_level():
    """Test that invalid log level fails validation"""
    config = Config()
    config.logging.level = "INVALID"
    
    with pytest.raises(ValueError, match="Invalid log level"):
        config.validate()


def test_config_from_file_partial():
    """Test that partial configuration file uses defaults for missing values"""
    yaml_content = """
model:
  name: "partial-model"

processing:
  batch_size: 75
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name
    
    try:
        config = Config.from_file(temp_path)
        
        # Specified values
        assert config.model.name == "partial-model"
        assert config.processing.batch_size == 75
        
        # Default values
        assert config.model.device == "cuda"
        assert config.database.path == "./chroma_db"
        assert config.search.default_top_k == 5
    finally:
        os.unlink(temp_path)


def test_config_from_empty_file():
    """Test that empty configuration file uses all defaults"""
    yaml_content = ""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(yaml_content)
        temp_path = f.name
    
    try:
        config = Config.from_file(temp_path)
        
        # All should be defaults
        assert config.model.name == "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        assert config.database.path == "./chroma_db"
        assert config.processing.batch_size == 100
    finally:
        os.unlink(temp_path)
