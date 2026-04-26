"""Celery app initialization for distributed tasks.

This module intentionally imports task modules at import time so unit tests can
assert task registration without starting a worker process.
"""

from __future__ import annotations

import ssl

from celery import Celery

from app.core.config import get_settings

settings = get_settings()


def _tls_url(url: str) -> str:
    """Append ssl_cert_reqs=none to rediss:// URLs if not already present.

    Celery's Redis backend requires this query parameter to be embedded in the
    URL itself when using TLS; broker_use_ssl/redis_backend_use_ssl alone are
    not sufficient for newer Celery/redis-py versions.
    """
    if url.startswith("rediss://") and "ssl_cert_reqs" not in url:
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}ssl_cert_reqs=none"
    return url


_broker_url = _tls_url(settings.resolved_celery_broker)
_backend_url = _tls_url(settings.resolved_celery_backend)

celery_app = Celery(
    "lms_worker",
    broker=_broker_url,
    backend=_backend_url,
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

celery_app.conf.update(
    # Explicitly set the TLS-safe URLs here so they take precedence over any
    # CELERY_BROKER_URL / CELERY_RESULT_BACKEND env vars that Celery reads
    # automatically (env-var values bypass the Celery() constructor).
    broker_url=_broker_url,
    result_backend=_backend_url,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    broker_connection_retry_on_startup=True,
)

# Import task modules so @celery_app.task decorators register tasks on this app.
# These imports must stay at the bottom to avoid circular import issues.
from app.tasks import email_tasks as _email_tasks  # noqa: F401
from app.tasks import grading_tasks as _grading_tasks  # noqa: F401
from app.tasks import notification_tasks as _notification_tasks  # noqa: F401
