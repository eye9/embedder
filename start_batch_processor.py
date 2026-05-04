#!/usr/bin/env python3
"""
Startup script for the Batch Excel Processor.

This script provides a convenient way to start the batch processor
with proper configuration loading and environment setup.
"""

import sys
import logging
import argparse
from pathlib import Path

# Add the project root to Python path
sys.path.insert(0, str(Path(__file__).parent))

from batch_processor.config.loader import get_config_loader


def setup_logging(log_level: str = "INFO"):
    """Set up logging configuration."""
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('logs/batch_processor.log')
        ]
    )


def start_web_server(config_path: str = None, host: str = None, port: int = None):
    """Start the web server."""
    import uvicorn
    from batch_processor.web.app import create_app
    
    # Load configuration
    config_loader = get_config_loader()
    config = config_loader.load(config_path)
    
    # Override with command line arguments
    if host:
        config.web.host = host
    if port:
        config.web.port = port
    
    # Create FastAPI app
    app = create_app(config)
    
    # Start server
    uvicorn.run(
        app,
        host=config.web.host,
        port=config.web.port,
        log_level=config.web.log_level,
        reload=config.web.reload
    )


def start_worker(config_path: str = None):
    """Start a Celery worker."""
    import subprocess
    
    # Load configuration
    config_loader = get_config_loader()
    config = config_loader.load(config_path)
    
    # Start Celery worker
    cmd = [
        "celery", "-A", "batch_processor.workers.celery_app",
        "worker", "--loglevel=info"
    ]
    
    subprocess.run(cmd)


def start_beat(config_path: str = None):
    """Start Celery beat scheduler."""
    import subprocess
    
    # Load configuration
    config_loader = get_config_loader()
    config = config_loader.load(config_path)
    
    # Start Celery beat
    cmd = [
        "celery", "-A", "batch_processor.workers.celery_app",
        "beat", "--loglevel=info"
    ]
    
    subprocess.run(cmd)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Batch Excel Processor")
    parser.add_argument(
        "command",
        choices=["web", "worker", "beat"],
        help="Component to start"
    )
    parser.add_argument(
        "--config",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--host",
        help="Host to bind web server to"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port to bind web server to"
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level)
    
    # Start the requested component
    if args.command == "web":
        start_web_server(args.config, args.host, args.port)
    elif args.command == "worker":
        start_worker(args.config)
    elif args.command == "beat":
        start_beat(args.config)


if __name__ == "__main__":
    main()
