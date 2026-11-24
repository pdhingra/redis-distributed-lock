from __future__ import annotations

import time
import uuid

import redis

from redis_lock_demo import Redlock, SingleNodeLock


def test_single_node_watchdog_extends_ttl_for_long_task(
    redis_single: redis.Redis,
) -> None:
    """Lock with ttl_ms=600 and watchdog stays valid across a 1.8s (3x TTL) task."""
    key = f"lock:test:watchdog-single:{uuid.uuid4().hex[:8]}"
    lock = SingleNodeLock(
        redis_single,
        key,
        ttl_ms=600,
        retry_count=0,
        enable_watchdog=True,
    )
    competitor = SingleNodeLock(
        redis_single,
        key,
        ttl_ms=600,
        retry_count=1,
        retry_delay_ms=50,
        enable_watchdog=False,
    )

    assert lock.acquire() is True
    try:
        # Sleep past initial 600ms TTL (1.5x TTL = 0.9s) and verify watchdog kept lock alive.
        time.sleep(0.9)
        assert lock.is_valid() is True
        assert redis_single.pttl(key) > 0
        assert competitor.acquire() is False

        # Complete full 1.8s (3x initial TTL) critical section.
        time.sleep(0.9)
        assert lock.is_valid() is True
        assert redis_single.pttl(key) > 0
    finally:
        assert lock.release() is True

    assert lock.is_valid() is False
    assert redis_single.get(key) is None

    # After release, competing worker can acquire cleanly.
    assert competitor.acquire() is True
    assert competitor.release() is True


def test_redlock_watchdog_extends_ttl_for_long_task(
    redlock_clients: list[redis.Redis],
) -> None:
    """Redlock with ttl_ms=600 and watchdog stays valid across a 1.8s (3x TTL) task."""
    key = f"lock:test:watchdog-redlock:{uuid.uuid4().hex[:8]}"
    lock = Redlock(
        redlock_clients,
        key,
        ttl_ms=600,
        retry_count=0,
        enable_watchdog=True,
    )
    competitor = Redlock(
        redlock_clients,
        key,
        ttl_ms=600,
        retry_count=1,
        retry_delay_ms=50,
        enable_watchdog=False,
    )

    assert lock.acquire() is True
    try:
        time.sleep(0.9)
        assert lock.is_valid() is True
        assert competitor.acquire() is False

        time.sleep(0.9)
        assert lock.is_valid() is True
        alive_nodes = sum(1 for c in redlock_clients if c.pttl(key) > 0)
        assert alive_nodes >= lock.quorum
    finally:
        assert lock.release() is True

    assert lock.is_valid() is False
    for client in redlock_clients:
        assert client.get(key) is None

    assert competitor.acquire() is True
    assert competitor.release() is True
