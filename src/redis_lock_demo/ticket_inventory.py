from __future__ import annotations

from collections.abc import Callable
from contextlib import closing
import logging
from pathlib import Path
import sqlite3
import time
import uuid

from redis_lock_demo._logging import current_worker_id, log_lock_event
from redis_lock_demo.interfaces import DistributedLock, LockAcquisitionError, LockLostError

logger = logging.getLogger(__name__)


class TicketInventoryService:
    """Thin SQLite WAL ticket booking service demonstrating distributed lock protection."""

    def __init__(self, db_path: str | Path) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as conn, conn:
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, total_seats INT NOT NULL, available_seats INT NOT NULL)")
            conn.execute("CREATE TABLE IF NOT EXISTS bookings (booking_id TEXT PRIMARY KEY, event_id TEXT NOT NULL, user_id TEXT NOT NULL)")

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path, timeout=30.0)
        conn.execute("PRAGMA busy_timeout = 30000;")
        return conn

    def create_event(self, event_id: str, total_seats: int) -> None:
        if total_seats < 0:
            raise ValueError("total_seats must be non-negative")
        with closing(self._connect()) as conn, conn:
            conn.execute("DELETE FROM bookings WHERE event_id = ?", (event_id,))
            conn.execute("INSERT OR REPLACE INTO events (event_id, total_seats, available_seats) VALUES (?, ?, ?)", (event_id, total_seats, total_seats))

    def get_available_seats(self, event_id: str) -> int:
        with closing(self._connect()) as conn:
            row = conn.execute("SELECT available_seats FROM events WHERE event_id = ?", (event_id,)).fetchone()
        if row is None:
            raise KeyError(f"Unknown event: {event_id!r}")
        return int(row[0])

    def get_bookings(self, event_id: str) -> list[dict[str, str]]:
        with closing(self._connect()) as conn:
            rows = conn.execute("SELECT booking_id, event_id, user_id FROM bookings WHERE event_id = ?", (event_id,)).fetchall()
        return [{"booking_id": r[0], "event_id": r[1], "user_id": r[2]} for r in rows]

    def book_seat(
        self,
        event_id: str,
        user_id: str,
        lock_factory: Callable[[str], DistributedLock] | None = None,
        processing_delay_s: float = 0.1,
    ) -> bool:
        """Book one seat; raises LockAcquisitionError or LockLostError on lock failure."""
        start_ms = time.monotonic() * 1000.0
        resource = f"lock:event:{event_id}"
        worker_id = current_worker_id(user_id)
        lock = lock_factory(resource) if lock_factory else None
        lock_mode = type(lock).__name__ if lock is not None else "unprotected"
        if lock is not None and not lock.acquire():
            log_lock_event(logger, logging.WARNING, "booking_lock_failed", resource=resource, worker_id=worker_id, quorum_count=0, elapsed_ms=(time.monotonic() * 1000.0) - start_ms, lock_mode=lock_mode)
            raise LockAcquisitionError(f"Failed to acquire lock for event {event_id!r}")
        token = getattr(lock, "owner_token", None) if lock is not None else None
        quorum_required = getattr(lock, "quorum", None) if lock is not None else None
        try:
            with closing(self._connect()) as conn, conn:
                row = conn.execute("SELECT available_seats FROM events WHERE event_id = ?", (event_id,)).fetchone()
                if row is None:
                    log_lock_event(logger, logging.WARNING, "booking_event_not_found", resource=resource, worker_id=worker_id, owner_token=token, elapsed_ms=(time.monotonic() * 1000.0) - start_ms, lock_mode=lock_mode, quorum_required=quorum_required)
                    raise KeyError(f"Unknown event: {event_id!r}")
                if row[0] <= 0:
                    log_lock_event(logger, logging.INFO, "booking_sold_out", resource=resource, worker_id=worker_id, owner_token=token, elapsed_ms=(time.monotonic() * 1000.0) - start_ms, lock_mode=lock_mode, quorum_required=quorum_required)
                    return False
                if processing_delay_s > 0:
                    time.sleep(processing_delay_s)
                if lock is not None and not lock.is_valid():
                    log_lock_event(logger, logging.WARNING, "booking_lock_lost", resource=resource, worker_id=worker_id, owner_token=token, elapsed_ms=(time.monotonic() * 1000.0) - start_ms, lock_mode=lock_mode, quorum_required=quorum_required)
                    raise LockLostError(f"Lock lost before committing booking for {event_id!r}")
                conn.execute("UPDATE events SET available_seats = available_seats - 1 WHERE event_id = ?", (event_id,))
                conn.execute("INSERT INTO bookings (booking_id, event_id, user_id) VALUES (?, ?, ?)", (str(uuid.uuid4()), event_id, user_id))
            log_lock_event(logger, logging.INFO, "booking_confirmed", resource=resource, worker_id=worker_id, owner_token=token, elapsed_ms=(time.monotonic() * 1000.0) - start_ms, lock_mode=lock_mode, quorum_required=quorum_required)
            return True
        finally:
            if lock is not None:
                lock.release()
