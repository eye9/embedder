#!/usr/bin/env python3
"""
ТНВЭД Embedder API Server

Main entry point for running the ТНВЭД Embedder API server.
"""

import logging
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from api.app import create_app
from utils.config import Config
from utils.logger import setup_logging


def main():
    """Main entry point"""
    try:
        # Load configuration
        try:
            config = Config.from_file("config.yaml")
            print("Configuration loaded from config.yaml")
        except FileNotFoundError:
            config = Config.from_env()
            print("Configuration loaded from environment variables")
        
        # Validate configuration
        config.validate()
        
        # Setup logging
        setup_logging(
            level=config.logging.level,
            log_file=config.logging.file,
            log_format=config.logging.format
        )
        
        logger = logging.getLogger(__name__)
        logger.info("Starting ТНВЭД Embedder API server")
        
        # Create FastAPI app
        app = create_app(config)
        
        # Print startup information
        print(f"ТНВЭД Embedder API Server")
        print(f"Configuration: {config.model.name} on {config.model.device}")
        print(f"Database: {config.database.path}")
        print(f"Server: http://{config.api.host}:{config.api.port}")
        print(f"Authentication: {'Enabled' if config.api.auth.enabled else 'Disabled'}")
        print(f"Rate limiting: {config.api.rate_limit.requests_per_minute} requests/minute")
        print(f"CORS: {'Enabled' if config.api.cors.enabled else 'Disabled'}")
        
        if not config.api.auth.enabled:
            print(f"API Documentation: http://{config.api.host}:{config.api.port}/docs")
        
        return app
        
    except Exception as e:
        print(f"Failed to start API server: {e}")
        logging.error(f"Failed to start API server: {e}", exc_info=True)
        sys.exit(1)


# Create app instance for uvicorn
app = main()


if __name__ == "__main__":
    import uvicorn
    
    # Load config for uvicorn settings
    try:
        config = Config.from_file("config.yaml")
    except FileNotFoundError:
        config = Config.from_env()
    
    # Run with uvicorn
    uvicorn.run(
        "tnved_api:app",
        host=config.api.host,
        port=config.api.port,
        reload=False,  # Set to True for development
        log_level=config.logging.level.lower()
    )