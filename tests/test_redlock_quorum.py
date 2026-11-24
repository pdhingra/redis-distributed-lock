from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractContextManager
import uuid

import pytest
import redis

from redis_lock_demo import LockAcquisitionError, Redlock
from redis_lock_demo.ticket_inventory import TicketInventoryService


def test_redlock_survives_two_paused_nodes_and_books_seats(
    redlock_clients: list[redis.Redis],
    ticket_service: TicketInventoryService,
    pause_containers: Callable[..., AbstractContextManager[list[str]]],
) -> None:
    """Pausing 2/5 nodes (redis-4, redis-5) leaves 3/5 quorum intact for acquire and booking."""
    event_id = f"test-quorum-ok-{uuid.uuid4().hex[:8]}"
    ticket_service.create_event(event_id, total_seats=2)
    key = f"lock:event:{event_id}"

    with pause_containers("redis-4", "redis-5"):
        lock = Redlock(
            redlock_clients,
            key,
            ttl_ms=3000,
            retry_count=2,
            retry_delay_ms=50,
            enable_watchdog=True,
        )
        assert lock.acquire() is True
        try:
            assert lock.is_valid() is True
            token = lock.owner_token
            assert token is not None
            for healthy_client in redlock_clients[:3]:
                assert healthy_client.get(key) == token.encode("utf-8")
        finally:
            assert lock.release() is True

        for healthy_client in redlock_clients[:3]:
            assert healthy_client.get(key) is None

        # Also verify TicketInventoryService books seats cleanly under 3/5 quorum.
        booked = ticket_service.book_seat(
            event_id,
            "user-quorum",
            lock_factory=lambda resource: Redlock(
                redlock_clients,
                resource,
                ttl_ms=3000,
                retry_count=2,
                retry_delay_ms=50,
                enable_watchdog=True,
            ),
            processing_delay_s=0.1,
        )
        assert booked is True
        assert ticket_service.get_available_seats(event_id) == 1
        assert len(ticket_service.get_bookings(event_id)) == 1
        for healthy_client in redlock_clients[:3]:
            assert healthy_client.get(key) is None


def test_redlock_fails_with_three_paused_nodes_and_rolls_back(
    redlock_clients: list[redis.Redis],
    ticket_service: TicketInventoryService,
    pause_containers: Callable[..., AbstractContextManager[list[str]]],
) -> None:
    """Pausing 3/5 nodes (redis-3, redis-4, redis-5) fails quorum and leaves 0 dangling keys."""
    event_id = f"test-quorum-lost-{uuid.uuid4().hex[:8]}"
    ticket_service.create_event(event_id, total_seats=2)
    key = f"lock:event:{event_id}"

    with pause_containers("redis-3", "redis-4", "redis-5"):
        lock = Redlock(
            redlock_clients,
            key,
            ttl_ms=3000,
            retry_count=2,
            retry_delay_ms=50,
            enable_watchdog=True,
        )
        assert lock.acquire() is False
        assert lock.is_valid() is False
        assert lock.owner_token is None

        # Zero dangling keys left on the two surviving nodes (redis-1 and redis-2).
        for surviving_client in redlock_clients[:2]:
            assert surviving_client.get(key) is None
            assert list(surviving_client.scan_iter(match="lock:*")) == []

        # TicketInventoryService refuses to book without quorum and rolls back partial locks.
        with pytest.raises(LockAcquisitionError):
            ticket_service.book_seat(
                event_id,
                "user-no-quorum",
                lock_factory=lambda resource: Redlock(
                    redlock_clients,
                    resource,
                    ttl_ms=3000,
                    retry_count=1,
                    retry_delay_ms=50,
                    enable_watchdog=True,
                ),
                processing_delay_s=0.1,
            )

        assert ticket_service.get_available_seats(event_id) == 2
        assert ticket_service.get_bookings(event_id) == []
        for surviving_client in redlock_clients[:2]:
            assert surviving_client.get(key) is None
            assert list(surviving_client.scan_iter(match="lock:*")) == []
