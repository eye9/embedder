#!/usr/bin/env python3
"""
Startup script for the Batch Excel Processor web application.

This script sets the required environment variables and starts the web server.
"""

import os
import sys
from pathlib import Path

def main():
    """Start the batch processor web application."""
    
    # Set the configuration file path
    config_path = Path("batch_processor_config.yaml")
    if config_path.exists():
        os.environ["BATCH_PROCESSOR_CONFIG"] = str(config_path.absolute())
        print(f"Using configuration file: {config_path.absolute()}")
    else:
        print("Warning: batch_processor_config.yaml not found, using default configuration")
    
    # Import and start the application
    try:
        import uvicorn
        from batch_processor.web.app import app
        
        print("Starting Batch Excel Processor web application...")
        print("Access the web interface at: http://localhost:8000")
        print("Login credentials:")
        print("  Username: admin")
        print("  Password: admin123")
        print("\nPress Ctrl+C to stop the server")
        
        # Start the server
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=8000,
            reload=False,
            log_level="info"
        )
        
    except ImportError:
        print("Error: uvicorn not installed. Install with: pip install uvicorn")
        sys.exit(1)
    except Exception as e:
        print(f"Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()