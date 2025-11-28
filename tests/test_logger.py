"""
Tests for logging configuration
"""

import logging
import tempfile
import os
from pathlib import Path
from utils.logger import setup_logging, get_logger


def test_setup_logging_console_only():
    """Test that logging can be set up with console output only"""
    setup_logging(level="INFO")
    logger = get_logger(__name__)
    
    assert logger.level == logging.NOTSET  # Logger inherits from root
    assert logging.getLogger().level == logging.INFO


def test_setup_logging_with_file():
    """Test that logging can be set up with file output"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "test.log")
        setup_logging(level="DEBUG", log_file=log_file)
        
        logger = get_logger(__name__)
        logger.info("Test message")
        
        # Close all handlers to release file locks on Windows
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        # Verify log file was created and contains message
        assert Path(log_file).exists()
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Test message" in content


def test_get_logger():
    """Test that get_logger returns a logger instance"""
    logger = get_logger("test_module")
    
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_module"


def test_logging_levels():
    """Test that different logging levels work correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "test.log")
        
        # Set up with WARNING level
        setup_logging(level="WARNING", log_file=log_file)
        logger = get_logger(__name__)
        
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Close all handlers to release file locks on Windows
        for handler in logging.getLogger().handlers[:]:
            handler.close()
            logging.getLogger().removeHandler(handler)
        
        # Only WARNING and ERROR should be in the log
        with open(log_file, 'r') as f:
            content = f.read()
            assert "Debug message" not in content
            assert "Info message" not in content
            assert "Warning message" in content
            assert "Error message" in content
