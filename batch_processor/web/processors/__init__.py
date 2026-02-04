"""
Processors for admin upload functionality.

This module contains processors for handling different types of admin uploads
including TNVED codes and URL mappings.
"""

from .tnved_processor import TNVEDUploadProcessor

__all__ = ['TNVEDUploadProcessor']