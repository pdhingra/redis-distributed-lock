from __future__ import annotations

import time
import uuid

import redis

from redis_lock_demo import Redlock, SingleNodeLock


def test_single_node_expired_worker_cannot_delete_new_owners_lock(
    redis_single: redis.Redis,
) -> None:
    """Worker A's late release() after TTL expiry returns False and leaves Worker B's key intact."""
    key = f"lock:test:safe-release-single:{uuid.uuid4().hex[:8]}"
    worker_a = SingleNodeLock(
        redis_single,
        key,
        ttl_ms=300,
        retry_count=0,
        enable_watchdog=False,
    )
    worker_b = SingleNodeLock(
        redis_single,
        key,
        ttl_ms=3000,
        retry_count=0,
        enable_watchdog=False,
    )

    assert worker_a.acquire() is True
    token_a = worker_a.owner_token
    assert token_a is not None

    # Let Worker A's lock expire naturally (500ms > 300ms TTL).
    time.sleep(0.5)
    assert worker_a.is_valid() is False

    # Worker B legitimately acquires the expired key with a fresh owner token.
    assert worker_b.acquire() is True
    token_b = worker_b.owner_token
    assert token_b is not None
    assert token_b != token_a

    # Worker A wakes up and attempts release(): must fail and preserve Worker B's key.
    assert worker_a.release() is False
    assert redis_single.get(key) == token_b.encode("utf-8")
    assert worker_b.is_valid() is True

    # Worker B can still release its own lock cleanly.
    assert worker_b.release() is True
    assert redis_single.get(key) is None


def test_redlock_expired_worker_cannot_delete_new_owners_lock(
    redlock_clients: list[redis.Redis],
) -> None:
    """Redlock late release() after TTL expiry returns False and leaves Worker B's quorum intact."""
    key = f"lock:test:safe-release-redlock:{uuid.uuid4().hex[:8]}"
    worker_a = Redlock(
        redlock_clients,
        key,
        ttl_ms=300,
        retry_count=0,
        enable_watchdog=False,
    )
    worker_b = Redlock(
        redlock_clients,
        key,
        ttl_ms=3000,
        retry_count=0,
        enable_watchdog=False,
    )

    assert worker_a.acquire() is True
    token_a = worker_a.owner_token
    assert token_a is not None

    time.sleep(0.5)
    assert worker_a.is_valid() is False

    assert worker_b.acquire() is True
    token_b = worker_b.owner_token
    assert token_b is not None
    assert token_b != token_a

    assert worker_a.release() is False
    for client in redlock_clients:
        assert client.get(key) == token_b.encode("utf-8")
    assert worker_b.is_valid() is True

    assert worker_b.release() is True
    for client in redlock_clients:
        assert client.get(key) is None
