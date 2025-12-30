"""
Celery application configuration for the batch Excel processor.

This module sets up the Celery application with Redis as broker and result backend,
configures task routing, and provides the main Celery app instance.
"""

from celery import Celery
from kombu import Queue
from batch_processor.config.settings import get_config


def create_celery_app() -> Celery:
    """
    Create and configure the Celery application.
    
    Returns:
        Configured Celery application instance
    """
    config = get_config()
    
    # Create Celery app
    celery_app = Celery('batch_processor')
    
    # Configure Celery with settings from config
    celery_app.conf.update(
        broker_url=config.celery.broker_url,
        result_backend=config.celery.result_backend,
        task_serializer=config.celery.task_serializer,
        accept_content=config.celery.accept_content,
        result_serializer=config.celery.result_serializer,
        timezone=config.celery.timezone,
        enable_utc=config.celery.enable_utc,
        worker_prefetch_multiplier=config.celery.worker_prefetch_multiplier,
        task_acks_late=config.celery.task_acks_late,
        worker_max_tasks_per_child=config.celery.worker_max_tasks_per_child,
        
        # Task routing configuration
        task_routes={
            'batch_processor.workers.processing_task.process_excel_file': {
                'queue': 'processing',
                'routing_key': 'processing'
            },
            'batch_processor.workers.cleanup_task.cleanup_expired_files': {
                'queue': 'cleanup',
                'routing_key': 'cleanup'
            }
        },
        
        # Queue configuration
        task_default_queue='default',
        task_queues=(
            Queue('default', routing_key='default'),
            Queue('processing', routing_key='processing'),
            Queue('cleanup', routing_key='cleanup'),
        ),
        
        # Result expiration
        result_expires=3600,  # 1 hour
        
        # Task execution settings
        task_soft_time_limit=1800,  # 30 minutes soft limit
        task_time_limit=2400,       # 40 minutes hard limit
        
        # Worker settings
        worker_disable_rate_limits=True,
        worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
        worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
        
        # Monitoring
        worker_send_task_events=True,
        task_send_sent_event=True,
        
        # Error handling
        task_reject_on_worker_lost=True,
        task_ignore_result=False,
    )
    
    # Auto-discover tasks
    celery_app.autodiscover_tasks([
        'batch_processor.workers.processing_task',
        'batch_processor.workers.cleanup_task'
    ])
    
    return celery_app


# Create the global Celery app instance
celery_app = create_celery_app()


# Celery beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    'cleanup-expired-files': {
        'task': 'batch_processor.workers.cleanup_task.cleanup_expired_files',
        'schedule': 3600.0,  # Run every hour
    },
}


@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery configuration."""
    print(f'Request: {self.request!r}')
    return 'Debug task completed'


if __name__ == '__main__':
    celery_app.start()