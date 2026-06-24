# app/workers/celery_app.py
"""
Celery configuration.

Celery handles the heavy background processing (PDF extraction,
OCR, table extraction) so the API doesn't time out waiting for
a 200-page PDF to be processed.

Redis is used as both the message broker and result backend.
"""

from celery import Celery
from app.core.config import settings

# Create the Celery app
celery_app = Celery(
    "finsight",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    # Tasks expire after 1 hour if not picked up
    task_soft_time_limit=3600,

    # Kill task if it runs more than 2 hours
    task_time_limit=7200,

    # Retry failed tasks up to 3 times
    task_max_retries=3,

    # Serialize tasks as JSON (readable, debuggable)
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Store results for 24 hours
    result_expires=86400,

    # Don't prefetch multiple tasks (each PDF is heavy)
    worker_prefetch_multiplier=1,
)

# Auto-discover tasks in the workers module
celery_app.autodiscover_tasks(["app.workers"])
