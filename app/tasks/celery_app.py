from celery import Celery

from app.config import settings

celery_app = Celery(
    "car_finder",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=[
        "app.tasks.scrape_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Timezone
    timezone="Europe/Warsaw",
    enable_utc=True,
    # Reliability: ack task only after it completes, not when it starts
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    # Fair dispatch: don't pre-fetch multiple tasks per worker
    worker_prefetch_multiplier=1,
    # Result expiry
    result_expires=3600,
    # Beat schedule: run scraper every N seconds
    beat_schedule={
        "scrape-all-sources": {
            "task": "app.tasks.scrape_tasks.dispatch_all_sources",
            "schedule": settings.SCRAPE_INTERVAL_SECONDS,
            "options": {"queue": "celery"},
        }
    },
)
