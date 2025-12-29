#!/usr/bin/env python3
"""
Start ТНВЭД Embedder API Server

Simple script to start the API server with proper configuration.
"""

import sys
import logging
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import uvicorn
from utils.config import Config
from utils.logger import setup_logging


def main():
    """Start the API server"""
    try:
        # Load configuration
        try:
            config = Config.from_file("config.yaml")
            print("✓ Configuration loaded from config.yaml")
        except FileNotFoundError:
            print("⚠ config.yaml not found, using environment variables")
            config = Config.from_env()
        
        # Validate configuration
        config.validate()
        print("✓ Configuration validated")
        
        # Setup logging
        setup_logging(
            level=config.logging.level,
            log_file=config.logging.file,
            format_string=config.logging.format
        )
        print("✓ Logging configured")
        
        # Print startup information
        print("\n" + "="*50)
        print("🚀 ТНВЭД Embedder API Server")
        print("="*50)
        print(f"Model: {config.model.name}")
        print(f"Device: {config.model.device}")
        print(f"Database: {config.database.path}")
        print(f"Server: http://{config.api.host}:{config.api.port}")
        print(f"Authentication: {'🔒 Enabled' if config.api.auth.enabled else '🔓 Disabled'}")
        print(f"Rate limiting: {config.api.rate_limit.requests_per_minute} requests/minute")
        print(f"CORS: {'✓ Enabled' if config.api.cors.enabled else '✗ Disabled'}")
        
        if not config.api.auth.enabled:
            print(f"📚 API Documentation: http://{config.api.host}:{config.api.port}/docs")
        
        print("="*50)
        print("Starting server...")
        
        # Start server
        uvicorn.run(
            "tnved_api:app",
            host=config.api.host,
            port=config.api.port,
            reload=False,
            log_level=config.logging.level.lower(),
            access_log=True
        )
        
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        logging.error(f"Failed to start server: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()