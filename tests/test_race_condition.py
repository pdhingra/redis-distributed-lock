from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
import threading
import uuid

import redis

from redis_lock_demo import Redlock, SingleNodeLock
from redis_lock_demo.interfaces import DistributedLock
from redis_lock_demo.ticket_inventory import TicketInventoryService


def _run_concurrent_bookings(
    service: TicketInventoryService,
    event_id: str,
    *,
    num_workers: int,
    total_seats: int,
    lock_factory: Callable[[str], DistributedLock] | None,
    processing_delay_s: float = 0.1,
) -> list[bool]:
    service.create_event(event_id, total_seats)
    barrier = threading.Barrier(num_workers)

    def _worker(worker_idx: int) -> bool:
        barrier.wait(timeout=5.0)
        return service.book_seat(
            event_id,
            f"user-{worker_idx}",
            lock_factory=lock_factory,
            processing_delay_s=processing_delay_s,
        )

    with ThreadPoolExecutor(max_workers=num_workers) as executor:
        return list(executor.map(_worker, range(num_workers)))


def test_unprotected_booking_oversells(ticket_service: TicketInventoryService) -> None:
    """Without a distributed lock, 15 concurrent workers oversell 5 seats."""
    event_id = f"test-unprotected-{uuid.uuid4().hex[:8]}"
    results = _run_concurrent_bookings(
        ticket_service,
        event_id,
        num_workers=15,
        total_seats=5,
        lock_factory=None,
        processing_delay_s=0.1,
    )

    available = ticket_service.get_available_seats(event_id)
    bookings = ticket_service.get_bookings(event_id)
    assert sum(1 for ok in results if ok) > 5
    assert available < 0
    assert len(bookings) > 5


def test_single_node_lock_prevents_overselling(
    ticket_service: TicketInventoryService,
    redis_single: redis.Redis,
) -> None:
    """With SingleNodeLock, 15 concurrent workers book exactly 5 of 5 seats."""
    event_id = f"test-single-{uuid.uuid4().hex[:8]}"
    results = _run_concurrent_bookings(
        ticket_service,
        event_id,
        num_workers=15,
        total_seats=5,
        lock_factory=lambda key: SingleNodeLock(
            redis_single,
            key,
            ttl_ms=3000,
            retry_count=50,
            retry_delay_ms=100,
            enable_watchdog=True,
        ),
        processing_delay_s=0.1,
    )

    available = ticket_service.get_available_seats(event_id)
    bookings = ticket_service.get_bookings(event_id)
    assert sum(1 for ok in results if ok) == 5
    assert sum(1 for ok in results if not ok) == 10
    assert available == 0
    assert len(bookings) == 5
    assert redis_single.get(f"lock:event:{event_id}") is None


def test_redlock_prevents_overselling(
    ticket_service: TicketInventoryService,
    redlock_clients: list[redis.Redis],
) -> None:
    """With 5-node Redlock, 15 concurrent workers book exactly 5 of 5 seats."""
    event_id = f"test-redlock-{uuid.uuid4().hex[:8]}"
    results = _run_concurrent_bookings(
        ticket_service,
        event_id,
        num_workers=15,
        total_seats=5,
        lock_factory=lambda key: Redlock(
            redlock_clients,
            key,
            ttl_ms=3000,
            retry_count=50,
            retry_delay_ms=100,
            enable_watchdog=True,
        ),
        processing_delay_s=0.1,
    )

    available = ticket_service.get_available_seats(event_id)
    bookings = ticket_service.get_bookings(event_id)
    assert sum(1 for ok in results if ok) == 5
    assert sum(1 for ok in results if not ok) == 10
    assert available == 0
    assert len(bookings) == 5
    for client in redlock_clients:
        assert client.get(f"lock:event:{event_id}") is None
