from __future__ import annotations

import logging
import threading
from typing import Any


def current_worker_id(user_id: str | None = None) -> str:
    """Return a concise worker identifier from thread name and optional user ID."""
    thread = threading.current_thread()
    thread_label = thread.name or f"thread-{threading.get_ident()}"
    return f"{user_id}@{thread_label}" if user_id else thread_label


def short_token(token: str | None) -> str:
    """Return a non-sensitive 8-char prefix of the owner token for log correlation."""
    return token[:8] if token else "-"


def log_lock_event(
    logger: logging.Logger,
    level: int,
    event: str,
    *,
    resource: str,
    worker_id: str | None = None,
    owner_token: str | None = None,
    quorum_count: int | None = None,
    elapsed_ms: float | None = None,
    **fields: Any,
) -> None:
    """Emit a thread-safe structured key=value log record."""
    if not logger.isEnabledFor(level):
        return

    resolved_worker = worker_id or current_worker_id()
    token_prefix = short_token(owner_token)
    quorum_val = quorum_count if quorum_count is not None else "-"
    rounded_elapsed = round(elapsed_ms, 2) if elapsed_ms is not None else None
    elapsed_val = f"{rounded_elapsed:.2f}" if rounded_elapsed is not None else "-"

    parts = [
        f"event={event}",
        f"worker_id={resolved_worker}",
        f"resource={resource}",
        f"owner_token={token_prefix}",
        f"quorum_count={quorum_val}",
        f"elapsed_ms={elapsed_val}",
    ]
    extra: dict[str, Any] = {
        "event": event,
        "worker_id": resolved_worker,
        "resource": resource,
        "owner_token": token_prefix,
        "quorum_count": quorum_count,
        "elapsed_ms": rounded_elapsed,
    }
    for key, value in fields.items():
        if value is not None:
            parts.append(f"{key}={value}")
            extra[key] = value

    logger.log(level, " ".join(parts), extra=extra)
