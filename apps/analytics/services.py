import logging

from django.db import connection

from .models import Event

logger = logging.getLogger(__name__)


def track(name: str, **payload) -> Event | None:
    """Record an event for the tenant of the current connection.

    Analytics may live in another database, so it cannot share the caller's
    transaction. It is best-effort: a failure is logged, never raised, so it
    can't break the user's request.
    """
    try:
        return Event.objects.create(
            tenant_schema=connection.schema_name, name=name, payload=payload
        )
    except Exception:
        logger.exception("Could not record analytics event %s", name)
        return None
