from __future__ import annotations

from collections.abc import Callable, Sequence
from concurrent.futures import ThreadPoolExecutor
import logging
import math
import random
import threading
import time
import uuid

import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from redis_lock_demo._logging import current_worker_id, log_lock_event
from redis_lock_demo.interfaces import DistributedLock
from redis_lock_demo.lua_scripts import EXTEND_SCRIPT, RELEASE_SCRIPT

logger = logging.getLogger(__name__)

DEFAULT_REDIS_PORTS: tuple[int, ...] = (6379, 6380, 6381, 6382, 6383)
DEFAULT_SOCKET_TIMEOUT_S: float = 0.05


def create_redlock_clients(
    endpoints: Sequence[tuple[str, int]] | None = None,
    socket_timeout: float = DEFAULT_SOCKET_TIMEOUT_S,
) -> list[redis.Redis]:
    """Create independent Redis clients with strict socket timeouts for Redlock."""
    targets = (
        list(endpoints)
        if endpoints is not None
        else [("127.0.0.1", port) for port in DEFAULT_REDIS_PORTS]
    )
    return [
        redis.Redis(
            host=host,
            port=port,
            socket_timeout=socket_timeout,
            socket_connect_timeout=socket_timeout,
            retry=Retry(NoBackoff(), 0),
        )
        for host, port in targets
    ]


class Redlock(DistributedLock):
    """Multi-master Redlock implementation with quorum voting and Watchdog renewal."""

    def __init__(
        self,
        clients: Sequence[redis.Redis] | None,
        key: str,
        ttl_ms: int = 3000,
        retry_count: int = 15,
        retry_delay_ms: int = 100,
        enable_watchdog: bool = True,
    ) -> None:
        if not key:
            raise ValueError("key must be non-empty")
        if ttl_ms <= 0:
            raise ValueError("ttl_ms must be positive")
        if retry_count < 0:
            raise ValueError("retry_count must be non-negative")
        if retry_delay_ms < 0:
            raise ValueError("retry_delay_ms must be non-negative")

        resolved_clients = (
            list(clients) if clients is not None else create_redlock_clients()
        )
        if not resolved_clients:
            raise ValueError("Redlock requires at least one Redis client")

        self._clients = resolved_clients
        self._owns_clients = clients is None
        if clients is not None:
            for idx, client in enumerate(self._clients):
                if isinstance(client, redis.Redis):
                    sock_timeout = client.get_connection_kwargs().get("socket_timeout")
                    retry = client.get_retry()
                    retries = retry.get_retries() if retry is not None else 0
                    if sock_timeout is None or sock_timeout > 0.25 or retries > 0:
                        log_lock_event(
                            logger,
                            logging.WARNING,
                            "redlock_client_config_warning",
                            resource=key,
                            node_index=idx,
                            socket_timeout=sock_timeout,
                            client_retries=retries,
                            recommendation="use create_redlock_clients() or socket_timeout=0.05 with Retry(NoBackoff(), 0)",
                        )
        self._key = key
        self._ttl_ms = ttl_ms
        self._retry_count = retry_count
        self._retry_delay_ms = retry_delay_ms
        self._enable_watchdog = enable_watchdog
        self._quorum = (len(self._clients) // 2) + 1

        self._release_scripts = [
            client.register_script(RELEASE_SCRIPT) for client in self._clients
        ]
        self._extend_scripts = [
            client.register_script(EXTEND_SCRIPT) for client in self._clients
        ]

        self._state_lock = threading.Lock()
        self._owner_token: str | None = None
        self._valid: bool = False
        self._deadline_ms: float = 0.0
        self._stop_event: threading.Event | None = None
        self._watchdog_thread: threading.Thread | None = None
        self._active_ops: int = 0
        self._closed: bool = False

    @property
    def key(self) -> str:
        return self._key

    @property
    def quorum(self) -> int:
        return self._quorum

    @property
    def owner_token(self) -> str | None:
        with self._state_lock:
            return self._owner_token

    def _run_on_all_nodes(self, fn: Callable[[int], bool]) -> int:
        with ThreadPoolExecutor(max_workers=len(self._clients)) as executor:
            results = list(executor.map(fn, range(len(self._clients))))
        return sum(1 for ok in results if ok)

    def _release_all_nodes(self, token: str, worker_id: str | None = None) -> int:
        caller_worker = worker_id or current_worker_id()

        def _release_node(idx: int) -> bool:
            try:
                return bool(
                    self._release_scripts[idx](keys=[self._key], args=[token])
                )
            except redis.RedisError as exc:
                log_lock_event(
                    logger,
                    logging.DEBUG,
                    "redlock_node_error",
                    resource=self._key,
                    worker_id=caller_worker,
                    owner_token=token,
                    node_index=idx,
                    op="release",
                    error=type(exc).__name__,
                )
                return False

        return self._run_on_all_nodes(_release_node)

    def _close_owned_clients_locked(self) -> None:
        """Close internally created Redis pools when no operations are active."""
        for client in self._clients:
            client.close()

    def _finish_op(self) -> None:
        with self._state_lock:
            self._active_ops -= 1
            if (
                self._owns_clients
                and self._active_ops == 0
                and self._owner_token is None
            ):
                self._close_owned_clients_locked()

    def close(self) -> None:
        """Release any held lock and close internally created Redis client pools."""
        with self._state_lock:
            self._closed = True
        self.release()
        with self._state_lock:
            if (
                self._owns_clients
                and self._active_ops == 0
                and self._owner_token is None
            ):
                self._close_owned_clients_locked()

    def acquire(self) -> bool:
        acquire_start_ms = time.monotonic() * 1000.0
        caller_worker = current_worker_id()
        with self._state_lock:
            if self._closed:
                log_lock_event(
                    logger,
                    logging.WARNING,
                    "redlock_acquire_failed",
                    resource=self._key,
                    worker_id=caller_worker,
                    quorum_count=0,
                    elapsed_ms=(time.monotonic() * 1000.0) - acquire_start_ms,
                    reason="closed",
                )
                return False
            existing_token = self._owner_token
            if existing_token is not None:
                log_lock_event(
                    logger,
                    logging.WARNING,
                    "redlock_acquire_failed",
                    resource=self._key,
                    worker_id=caller_worker,
                    owner_token=existing_token,
                    quorum_count=0,
                    elapsed_ms=(time.monotonic() * 1000.0) - acquire_start_ms,
                    reason="already_held",
                )
                return False
            self._active_ops += 1

        token = str(uuid.uuid4())
        drift_ms = int(self._ttl_ms * 0.01) + 2
        total_nodes = len(self._clients)

        def _acquire_node(idx: int) -> bool:
            try:
                return bool(
                    self._clients[idx].set(
                        self._key, token, nx=True, px=self._ttl_ms
                    )
                )
            except redis.RedisError as exc:
                log_lock_event(
                    logger,
                    logging.DEBUG,
                    "redlock_node_error",
                    resource=self._key,
                    worker_id=caller_worker,
                    owner_token=token,
                    node_index=idx,
                    op="acquire",
                    error=type(exc).__name__,
                )
                return False

        try:
            for attempt in range(self._retry_count + 1):
                start_ms = time.monotonic() * 1000.0
                acquired_count = self._run_on_all_nodes(_acquire_node)
                elapsed_ms = (time.monotonic() * 1000.0) - start_ms
                remaining_ms = self._ttl_ms - elapsed_ms - drift_ms

                if acquired_count >= self._quorum and remaining_ms > 0:
                    deadline_ms = start_ms + self._ttl_ms - drift_ms
                    stop_event = threading.Event()
                    thread: threading.Thread | None = None
                    if self._enable_watchdog:
                        thread = threading.Thread(
                            target=self._watchdog_loop,
                            args=(token, stop_event),
                            daemon=True,
                            name=f"redlock-watchdog-{self._key}",
                        )

                    committed = False
                    aborted_reason: str | None = None
                    with self._state_lock:
                        if self._closed:
                            aborted_reason = "closed"
                        elif self._owner_token is not None:
                            aborted_reason = "concurrent_instance_acquire"
                        elif (time.monotonic() * 1000.0) < deadline_ms:
                            self._owner_token = token
                            self._valid = True
                            self._deadline_ms = deadline_ms
                            self._stop_event = stop_event
                            self._watchdog_thread = thread
                            if thread is not None:
                                thread.start()
                            committed = True

                    if committed:
                        log_lock_event(
                            logger,
                            logging.INFO,
                            "redlock_acquired",
                            resource=self._key,
                            worker_id=caller_worker,
                            owner_token=token,
                            quorum_count=acquired_count,
                            elapsed_ms=(time.monotonic() * 1000.0) - acquire_start_ms,
                            attempt=attempt + 1,
                            attempt_elapsed_ms=round(elapsed_ms, 2),
                            remaining_ms=round(remaining_ms, 2),
                            quorum_required=self._quorum,
                            total_nodes=total_nodes,
                            ttl_ms=self._ttl_ms,
                            watchdog=self._enable_watchdog,
                        )
                        return True

                    if aborted_reason is not None:
                        self._release_all_nodes(token, worker_id=caller_worker)
                        log_lock_event(
                            logger,
                            logging.WARNING,
                            "redlock_acquire_failed",
                            resource=self._key,
                            worker_id=caller_worker,
                            owner_token=token,
                            quorum_count=acquired_count,
                            elapsed_ms=(time.monotonic() * 1000.0) - acquire_start_ms,
                            attempt=attempt + 1,
                            reason=aborted_reason,
                        )
                        return False

                    remaining_ms = deadline_ms - (time.monotonic() * 1000.0)

                # Roll back partial locks across all N nodes immediately.
                rolled_back = self._release_all_nodes(token, worker_id=caller_worker)
                rollback_level = (
                    logging.WARNING
                    if (acquired_count > 0 or rolled_back > 0)
                    else logging.DEBUG
                )
                log_lock_event(
                    logger,
                    rollback_level,
                    "redlock_quorum_rollback",
                    resource=self._key,
                    worker_id=caller_worker,
                    owner_token=token,
                    quorum_count=acquired_count,
                    elapsed_ms=elapsed_ms,
                    attempt=attempt + 1,
                    quorum_required=self._quorum,
                    total_nodes=total_nodes,
                    rolled_back_count=rolled_back,
                    remaining_ms=round(remaining_ms, 2),
                    reason=(
                        "expired_after_drift"
                        if acquired_count >= self._quorum
                        else "quorum_not_reached"
                    ),
                )

                if attempt < self._retry_count:
                    jitter_ms = (
                        random.uniform(
                            self._retry_delay_ms * 0.5, self._retry_delay_ms * 1.5
                        )
                        if self._retry_delay_ms > 0
                        else 0.0
                    )
                    log_lock_event(
                        logger,
                        logging.DEBUG,
                        "redlock_retry",
                        resource=self._key,
                        worker_id=caller_worker,
                        owner_token=token,
                        quorum_count=acquired_count,
                        elapsed_ms=elapsed_ms,
                        attempt=attempt + 1,
                        retry_delay_ms=round(jitter_ms, 2),
                    )
                    if jitter_ms > 0:
                        time.sleep(jitter_ms / 1000.0)

            log_lock_event(
                logger,
                logging.WARNING,
                "redlock_acquire_failed",
                resource=self._key,
                worker_id=caller_worker,
                owner_token=token,
                quorum_count=0,
                elapsed_ms=(time.monotonic() * 1000.0) - acquire_start_ms,
                attempts=self._retry_count + 1,
                quorum_required=self._quorum,
                total_nodes=total_nodes,
                reason="retries_exhausted",
            )
            return False
        finally:
            self._finish_op()

    def extend(self, ttl_ms: int | None = None) -> bool:
        """Extend the lock TTL across a quorum of Redis nodes.

        When ``enable_watchdog=True``, the watchdog continues probing at
        ``configured_ttl_ms / 3`` intervals and preserves any longer manual
        deadline (never shrinking an active extension below its remaining TTL),
        while shorter custom TTLs remain subject to the configured wake cycle.
        """
        if ttl_ms is not None and ttl_ms <= 0:
            raise ValueError("ttl_ms must be positive")

        with self._state_lock:
            token = self._owner_token
            valid = self._valid

        if token is None or not valid:
            log_lock_event(
                logger,
                logging.WARNING,
                "redlock_extend_failed",
                resource=self._key,
                owner_token=token,
                quorum_count=0,
                elapsed_ms=0.0,
                reason="not_held_or_invalid",
            )
            return False

        target_ttl_ms = ttl_ms if ttl_ms is not None else self._ttl_ms
        return self._extend_with_token(token, target_ttl_ms, source="manual")

    def _extend_with_token(
        self, token: str, ttl_ms: int, source: str = "manual"
    ) -> bool:
        drift_ms = int(ttl_ms * 0.01) + 2
        caller_worker = current_worker_id()

        with self._state_lock:
            if self._closed or self._owner_token != token:
                log_lock_event(
                    logger,
                    logging.DEBUG,
                    "redlock_extend_stale",
                    resource=self._key,
                    worker_id=caller_worker,
                    owner_token=token,
                    quorum_count=0,
                    elapsed_ms=0.0,
                    source=source,
                )
                return False
            self._active_ops += 1

        def _extend_node(idx: int) -> bool:
            try:
                return bool(
                    self._extend_scripts[idx](keys=[self._key], args=[token, ttl_ms])
                )
            except redis.RedisError as exc:
                log_lock_event(
                    logger,
                    logging.DEBUG,
                    "redlock_node_error",
                    resource=self._key,
                    worker_id=caller_worker,
                    owner_token=token,
                    node_index=idx,
                    op="extend",
                    error=type(exc).__name__,
                )
                return False

        try:
            start_ms = time.monotonic() * 1000.0
            extended_count = self._run_on_all_nodes(_extend_node)
            elapsed_ms = (time.monotonic() * 1000.0) - start_ms
            new_deadline_ms = start_ms + ttl_ms - drift_ms
            remaining_ms = new_deadline_ms - (time.monotonic() * 1000.0)
            quorum_ok = extended_count >= self._quorum and remaining_ms > 0

            with self._state_lock:
                if self._owner_token != token:
                    outcome = "stale"
                elif quorum_ok:
                    self._deadline_ms = new_deadline_ms
                    outcome = "ok"
                else:
                    self._valid = False
                    outcome = "failed"
        finally:
            self._finish_op()

        if outcome == "stale":
            log_lock_event(
                logger,
                logging.DEBUG,
                "redlock_extend_stale",
                resource=self._key,
                worker_id=caller_worker,
                owner_token=token,
                quorum_count=extended_count,
                elapsed_ms=elapsed_ms,
                source=source,
            )
            return False

        if outcome == "ok":
            event = (
                "redlock_watchdog_renewed"
                if source == "watchdog"
                else "redlock_extended"
            )
            log_lock_event(
                logger,
                logging.INFO,
                event,
                resource=self._key,
                worker_id=caller_worker,
                owner_token=token,
                quorum_count=extended_count,
                elapsed_ms=elapsed_ms,
                quorum_required=self._quorum,
                total_nodes=len(self._clients),
                remaining_ms=round(remaining_ms, 2),
                ttl_ms=ttl_ms,
                source=source,
            )
            return True

        event = (
            "redlock_watchdog_failed"
            if source == "watchdog"
            else "redlock_extend_failed"
        )
        log_lock_event(
            logger,
            logging.WARNING,
            event,
            resource=self._key,
            worker_id=caller_worker,
            owner_token=token,
            quorum_count=extended_count,
            elapsed_ms=elapsed_ms,
            quorum_required=self._quorum,
            total_nodes=len(self._clients),
            remaining_ms=round(remaining_ms, 2),
            ttl_ms=ttl_ms,
            source=source,
            reason=(
                "expired_after_drift"
                if extended_count >= self._quorum
                else "quorum_not_reached"
            ),
        )
        return False

    def _watchdog_loop(self, token: str, stop_event: threading.Event) -> None:
        interval_s = (self._ttl_ms / 3.0) / 1000.0
        while not stop_event.wait(timeout=interval_s):
            with self._state_lock:
                remaining_ms = self._deadline_ms - (time.monotonic() * 1000.0)
            target_ttl_ms = max(self._ttl_ms, math.ceil(remaining_ms))
            if not self._extend_with_token(token, target_ttl_ms, source="watchdog"):
                break

    def release(self) -> bool:
        start_ms = time.monotonic() * 1000.0
        caller_worker = current_worker_id()
        with self._state_lock:
            token = self._owner_token
            stop_event = self._stop_event
            thread = self._watchdog_thread
            self._valid = False
            self._owner_token = None
            self._stop_event = None
            self._watchdog_thread = None
            if token is not None:
                self._active_ops += 1

        if token is None:
            return False

        try:
            if stop_event is not None:
                stop_event.set()
            if thread is not None and thread is not threading.current_thread():
                thread.join(timeout=1.0)

            released_count = self._release_all_nodes(token, worker_id=caller_worker)
        finally:
            self._finish_op()

        elapsed_ms = (time.monotonic() * 1000.0) - start_ms
        quorum_released = released_count >= self._quorum
        log_lock_event(
            logger,
            logging.INFO if quorum_released else logging.WARNING,
            "redlock_released" if quorum_released else "redlock_release_incomplete",
            resource=self._key,
            worker_id=caller_worker,
            owner_token=token,
            quorum_count=released_count,
            elapsed_ms=elapsed_ms,
            quorum_required=self._quorum,
            total_nodes=len(self._clients),
        )
        return quorum_released

    def is_valid(self) -> bool:
        with self._state_lock:
            return (
                self._valid
                and self._owner_token is not None
                and (time.monotonic() * 1000.0) < self._deadline_ms
            )
