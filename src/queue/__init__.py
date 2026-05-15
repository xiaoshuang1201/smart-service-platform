"Celery async task queue for knowledge indexing and log processing"

from __future__ import annotations
from celery import Celery

from src.config import config

celery_app = Celery(
    "smartservice",
    broker=config.celery.broker_url,
    backend=config.celery.result_backend,
)

celery_app.conf.update(
    task_default_queue=config.celery.task_default_queue,
    task_acks_late=config.celery.task_acks_late,
    worker_prefetch_multiplier=config.celery.worker_prefetch_multiplier,
    task_soft_time_limit=config.celery.task_soft_time_limit,
    task_time_limit=config.celery.task_time_limit,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Shanghai",
    enable_utc=True,
    task_track_started=True,
    task_send_sent_event=True,
    worker_max_tasks_per_child=1000,
)
