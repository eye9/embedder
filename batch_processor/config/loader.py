"""
Configuration loader utilities for the batch processor.

This module provides utilities for loading and managing configuration
from various sources including files, environment variables, and defaults.
"""

import os
import logging
from pathlib import Path
from typing import Optional

from .settings import BatchProcessorConfig, load_config


logger = logging.getLogger(__name__)


class ConfigLoader:
    """Configuration loader with multiple source support."""
    
    DEFAULT_CONFIG_PATHS = [
        "batch_processor_config.yaml",
        "config/batch_processor.yaml",
        "/etc/batch_processor/config.yaml",
        os.path.expanduser("~/.batch_processor/config.yaml")
    ]
    
    def __init__(self):
        self._config: Optional[BatchProcessorConfig] = None
    
    def load(self, config_path: Optional[str] = None) -> BatchProcessorConfig:
        """
        Load configuration from the specified path or auto-discover.
        
        Args:
            config_path: Explicit path to configuration file
            
        Returns:
            BatchProcessorConfig instance
        """
        if config_path:
            if not Path(config_path).exists():
                raise FileNotFoundError(f"Configuration file not found: {config_path}")
            logger.info(f"Loading configuration from: {config_path}")
            self._config = load_config(config_path)
        else:
            # Try to auto-discover configuration file
            discovered_path = self._discover_config_file()
            if discovered_path:
                logger.info(f"Auto-discovered configuration file: {discovered_path}")
                self._config = load_config(discovered_path)
            else:
                logger.info("No configuration file found, using environment variables and defaults")
                self._config = load_config()
        
        return self._config
    
    def _discover_config_file(self) -> Optional[str]:
        """
        Auto-discover configuration file from default locations.
        
        Returns:
            Path to configuration file if found, None otherwise
        """
        for path in self.DEFAULT_CONFIG_PATHS:
            if Path(path).exists():
                return path
        return None
    
    def reload(self, config_path: Optional[str] = None) -> BatchProcessorConfig:
        """
        Reload configuration, useful for development or configuration updates.
        
        Args:
            config_path: Explicit path to configuration file
            
        Returns:
            BatchProcessorConfig instance
        """
        logger.info("Reloading configuration")
        return self.load(config_path)
    
    @property
    def config(self) -> BatchProcessorConfig:
        """Get the current configuration, loading if necessary."""
        if self._config is None:
            self.load()
        return self._config


# Global configuration loader instance
config_loader = ConfigLoader()


def get_config_loader() -> ConfigLoader:
    """Get the global configuration loader instance."""
    return config_loader