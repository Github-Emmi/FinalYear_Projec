"""Celery app initialization for distributed tasks.

This module intentionally imports task modules at import time so unit tests can
assert task registration without starting a worker process.
"""

from __future__ import annotations

import ssl

from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "lms_worker",
    broker=settings.resolved_celery_broker,
    backend=settings.resolved_celery_backend,
    include=[
        "app.tasks.grading_tasks",
        "app.tasks.email_tasks",
        "app.tasks.notification_tasks",
    ],
)

celery_app.conf.task_routes = {
    "app.tasks.grading_tasks.*": {"queue": "grading"},
    "app.tasks.email_tasks.*": {"queue": "email"},
    "app.tasks.notification_tasks.*": {"queue": "notifications"},
}

# Render's managed Redis uses TLS (rediss://) with a certificate that may not
# be in the system trust store.  Pass ssl_cert_reqs=CERT_NONE so both the
# broker and result-backend connections succeed without cert verification.
_tls_url = settings.resolved_celery_broker.startswith("rediss://")
_ssl_opts: dict = (
    {"ssl_cert_reqs": ssl.CERT_NONE} if _tls_url else {}
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_use_ssl=_ssl_opts or None,
    redis_backend_use_ssl=_ssl_opts or None,
    broker_connection_retry_on_startup=True,
)

# Import task modules so @celery_app.task decorators register tasks on this app.
# These imports must stay at the bottom to avoid circular import issues.
from app.tasks import email_tasks as _email_tasks  # noqa: F401
from app.tasks import grading_tasks as _grading_tasks  # noqa: F401
from app.tasks import notification_tasks as _notification_tasks  # noqa: F401
