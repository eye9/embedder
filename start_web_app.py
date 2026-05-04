#!/usr/bin/env python3
"""
Startup script for the Batch Excel Processor web application.

This script starts the FastAPI web application with proper configuration
for development and production environments.
"""

import uvicorn
import logging
from pathlib import Path

from batch_processor.config.settings import get_config, set_config, BatchProcessorConfig
from batch_processor.web.app import app


def setup_logging():
    """Configure logging for the application."""
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler('logs/batch_processor.log')
        ]
    )


def main():
    """Main entry point for the web application."""
    setup_logging()
    logger = logging.getLogger(__name__)
    
    try:
        # Load configuration
        config_path = Path("batch_processor_config.yaml")
        if config_path.exists():
            logger.info(f"Loading configuration from {config_path}")
            config = BatchProcessorConfig.from_yaml(str(config_path))
        else:
            logger.info("Using configuration from environment variables")
            config = BatchProcessorConfig.from_env()
        
        # Set global configuration
        set_config(config)
        
        # Create temp directory if it doesn't exist
        temp_dir = Path(config.files.temp_dir)
        temp_dir.mkdir(exist_ok=True)
        logger.info(f"Temp directory: {temp_dir}")
        
        # Log configuration
        logger.info(f"Starting web server on {config.web.host}:{config.web.port}")
        logger.info(f"Debug mode: {config.web.debug}")
        logger.info(f"Authentication enabled: {config.auth.enabled}")
        logger.info(f"Redis URL: {config.redis.url}")
        
        # Start the server
        uvicorn.run(
            app,
            host=config.web.host,
            port=config.web.port,
            reload=config.web.reload,
            log_level=config.web.log_level
        )
        
    except Exception as e:
        logger.error(f"Failed to start web application: {e}")
        raise


if __name__ == "__main__":
    main()
