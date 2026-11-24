from __future__ import annotations

import logging
import math
import random
import threading
import time
import uuid

import redis

from redis_lock_demo._logging import log_lock_event
from redis_lock_demo.interfaces import DistributedLock
from redis_lock_demo.lua_scripts import EXTEND_SCRIPT, RELEASE_SCRIPT

logger = logging.getLogger(__name__)


class SingleNodeLock(DistributedLock):
    """Redis single-node distributed lock with Lua owner checks and Watchdog renewal."""

    def __init__(
        self,
        client: redis.Redis,
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

        self._client = client
        self._key = key
        self._ttl_ms = ttl_ms
        self._retry_count = retry_count
        self._retry_delay_ms = retry_delay_ms
        self._enable_watchdog = enable_watchdog

        self._release_script = client.register_script(RELEASE_SCRIPT)
        self._extend_script = client.register_script(EXTEND_SCRIPT)

        self._state_lock = threading.Lock()
        self._owner_token: str | None = None
        self._valid: bool = False
        self._deadline_ms: float = 0.0
        self._stop_event: threading.Event | None = None
        self._watchdog_thread: threading.Thread | None = None

    @property
    def key(self) -> str:
        return self._key

    @property
    def owner_token(self) -> str | None:
        with self._state_lock:
            return self._owner_token

    def acquire(self) -> bool:
        acquire_start_ms = time.monotonic() * 1000.0
        with self._state_lock:
            existing_token = self._owner_token
        if existing_token is not None:
            log_lock_event(
                logger,
                logging.WARNING,
                "lock_acquire_failed",
                resource=self._key,
                owner_token=existing_token,
                quorum_count=0,
                elapsed_ms=(time.monotonic() * 1000.0) - acquire_start_ms,
                reason="already_held",
            )
            return False

        token = str(uuid.uuid4())
        for attempt in range(self._retry_count + 1):
            attempt_start_ms = time.monotonic() * 1000.0
            error_name: str | None = None
            try:
                acquired = bool(
                    self._client.set(self._key, token, nx=True, px=self._ttl_ms)
                )
            except redis.RedisError as exc:
                acquired = False
                error_name = type(exc).__name__

            attempt_elapsed_ms = (time.monotonic() * 1000.0) - attempt_start_ms
            if acquired and attempt_elapsed_ms < self._ttl_ms:
                deadline_ms = attempt_start_ms + self._ttl_ms
                stop_event = threading.Event()
                thread: threading.Thread | None = None
                if self._enable_watchdog:
                    thread = threading.Thread(
                        target=self._watchdog_loop,
                        args=(token, stop_event),
                        daemon=True,
                        name=f"watchdog-{self._key}",
                    )

                committed = False
                already_held_on_instance = False
                with self._state_lock:
                    if self._owner_token is not None:
                        already_held_on_instance = True
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
                        "lock_acquired",
                        resource=self._key,
                        owner_token=token,
                        quorum_count=1,
                        elapsed_ms=(time.monotonic() * 1000.0) - acquire_start_ms,
                        attempt=attempt + 1,
                        ttl_ms=self._ttl_ms,
                        watchdog=self._enable_watchdog,
                    )
                    return True

                # Roll back if state was claimed concurrently or TTL elapsed before commit.
                try:
                    self._release_script(keys=[self._key], args=[token])
                except redis.RedisError:
                    pass

                if already_held_on_instance:
                    log_lock_event(
                        logger,
                        logging.WARNING,
                        "lock_acquire_failed",
                        resource=self._key,
                        owner_token=token,
                        quorum_count=0,
                        elapsed_ms=(time.monotonic() * 1000.0) - acquire_start_ms,
                        attempt=attempt + 1,
                        reason="concurrent_instance_acquire",
                    )
                    return False

                error_name = "ttl_elapsed_during_acquire"
                attempt_elapsed_ms = (time.monotonic() * 1000.0) - attempt_start_ms
            elif acquired:
                try:
                    self._release_script(keys=[self._key], args=[token])
                except redis.RedisError:
                    pass
                error_name = "ttl_elapsed_during_acquire"

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
                    logging.WARNING if error_name else logging.DEBUG,
                    "lock_retry",
                    resource=self._key,
                    owner_token=token,
                    quorum_count=0,
                    elapsed_ms=attempt_elapsed_ms,
                    attempt=attempt + 1,
                    retry_delay_ms=round(jitter_ms, 2),
                    error=error_name,
                )
                if jitter_ms > 0:
                    time.sleep(jitter_ms / 1000.0)

        log_lock_event(
            logger,
            logging.WARNING,
            "lock_acquire_failed",
            resource=self._key,
            owner_token=token,
            quorum_count=0,
            elapsed_ms=(time.monotonic() * 1000.0) - acquire_start_ms,
            attempts=self._retry_count + 1,
            reason="retries_exhausted",
        )
        return False

    def extend(self, ttl_ms: int | None = None) -> bool:
        """Extend the lock TTL safely.

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
                "lock_extend_failed",
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
        attempt_start_ms = time.monotonic() * 1000.0
        error_name: str | None = None
        try:
            extended = bool(self._extend_script(keys=[self._key], args=[token, ttl_ms]))
        except redis.RedisError as exc:
            extended = False
            error_name = type(exc).__name__

        elapsed_ms = (time.monotonic() * 1000.0) - attempt_start_ms
        new_deadline_ms = attempt_start_ms + ttl_ms
        within_ttl = (time.monotonic() * 1000.0) < new_deadline_ms
        with self._state_lock:
            if self._owner_token != token:
                outcome = "stale"
            elif extended and within_ttl:
                self._deadline_ms = new_deadline_ms
                outcome = "ok"
            else:
                self._valid = False
                outcome = "failed"

        if outcome == "stale":
            log_lock_event(
                logger,
                logging.DEBUG,
                "lock_extend_stale",
                resource=self._key,
                owner_token=token,
                quorum_count=0,
                elapsed_ms=elapsed_ms,
                source=source,
            )
            return False

        if outcome == "ok":
            event = "watchdog_renewed" if source == "watchdog" else "lock_extended"
            log_lock_event(
                logger,
                logging.INFO,
                event,
                resource=self._key,
                owner_token=token,
                quorum_count=1,
                elapsed_ms=elapsed_ms,
                ttl_ms=ttl_ms,
                source=source,
            )
            return True

        event = "watchdog_failed" if source == "watchdog" else "lock_extend_failed"
        log_lock_event(
            logger,
            logging.WARNING,
            event,
            resource=self._key,
            owner_token=token,
            quorum_count=0,
            elapsed_ms=elapsed_ms,
            ttl_ms=ttl_ms,
            source=source,
            reason=(
                "redis_error"
                if error_name
                else ("ttl_elapsed_during_extend" if extended else "ownership_lost")
            ),
            error=error_name,
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
        with self._state_lock:
            token = self._owner_token
            stop_event = self._stop_event
            thread = self._watchdog_thread
            self._valid = False
            self._owner_token = None
            self._stop_event = None
            self._watchdog_thread = None

        if token is None:
            return False

        if stop_event is not None:
            stop_event.set()
        if thread is not None and thread is not threading.current_thread():
            thread.join(timeout=1.0)

        try:
            released = bool(self._release_script(keys=[self._key], args=[token]))
        except redis.RedisError as exc:
            log_lock_event(
                logger,
                logging.WARNING,
                "lock_release_error",
                resource=self._key,
                owner_token=token,
                quorum_count=0,
                elapsed_ms=(time.monotonic() * 1000.0) - start_ms,
                error=type(exc).__name__,
            )
            return False

        elapsed_ms = (time.monotonic() * 1000.0) - start_ms
        if released:
            log_lock_event(
                logger,
                logging.INFO,
                "lock_released",
                resource=self._key,
                owner_token=token,
                quorum_count=1,
                elapsed_ms=elapsed_ms,
            )
        else:
            log_lock_event(
                logger,
                logging.WARNING,
                "lock_release_stale",
                resource=self._key,
                owner_token=token,
                quorum_count=0,
                elapsed_ms=elapsed_ms,
                reason="token_mismatch_or_expired",
            )
        return released

    def is_valid(self) -> bool:
        with self._state_lock:
            return (
                self._valid
                and self._owner_token is not None
                and (time.monotonic() * 1000.0) < self._deadline_ms
            )
