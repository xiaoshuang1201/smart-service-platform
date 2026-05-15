#!/usr/bin/env python3
"Celery worker entry point — 异步任务消费者"

import sys
from src.queue import celery_app

if __name__ == "__main__":
    argv = [
        "worker",
        "--loglevel=info",
        "--concurrency=4",
        "--queues=smartservice",
        "--hostname=smartservice-worker@%h",
    ]
    celery_app.worker_main(argv)
