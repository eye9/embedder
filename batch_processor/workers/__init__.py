"""
Background task workers for the batch Excel processor.

This package contains Celery workers for processing Excel files,
tracking progress, and managing cleanup tasks.
"""

from .celery_app import celery_app

__all__ = ['celery_app']