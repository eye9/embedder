#!/usr/bin/env python3
"""
Direct test of authentication system.
"""

import os
import sys
from pathlib import Path

def test_auth():
    """Test authentication configuration."""
    
    # Set the configuration file path
    config_path = Path("batch_processor_config.yaml")
    if config_path.exists():
        os.environ["BATCH_PROCESSOR_CONFIG"] = str(config_path.absolute())
        print(f"Using configuration file: {config_path.absolute()}")
    
    try:
        from batch_processor.config.settings import get_config
        from batch_processor.web.auth import session_manager
        from fastapi.security import HTTPBasicCredentials
        
        # Load configuration
        config = get_config()
        print(f"Auth enabled: {config.auth.enabled}")
        print(f"Configured users: {list(config.auth.users.keys())}")
        
        # Test authentication
        test_credentials = HTTPBasicCredentials(username="admin", password="admin123")
        
        try:
            result = session_manager.authenticate_user(test_credentials)
            print(f"Authentication successful for user: {result}")
            return True
        except Exception as e:
            print(f"Authentication failed: {e}")
            return False
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_auth()
    if success:
        print("\n✅ Authentication test successful!")
    else:
        print("\n❌ Authentication test failed!")
        sys.exit(1)