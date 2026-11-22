"""Primary-database pinning for read-replica setups.

When read replicas are configured, reads normally go to a replica. Some code
must read its own writes immediately (replication lag would otherwise return
stale data), so it can *pin* the primary::

    from apps.core.db import use_primary

    with use_primary():
        order = Order.objects.get(pk=pk)

``PrimaryPinningMiddleware`` pins every unsafe HTTP request (POST, PUT, PATCH,
DELETE) automatically. A ``ContextVar`` is used so the flag is isolated per
thread *and* per asyncio task.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar

_pinned: ContextVar[bool] = ContextVar("primary_db_pinned", default=False)


def is_primary_pinned() -> bool:
    return _pinned.get()


@contextmanager
def use_primary() -> Iterator[None]:
    token = _pinned.set(True)
    try:
        yield
    finally:
        _pinned.reset(token)
