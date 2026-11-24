from __future__ import annotations

from abc import ABC, abstractmethod
from types import TracebackType
from typing import Self


class LockAcquisitionError(RuntimeError):
    """Raised when a distributed lock cannot be acquired."""


class LockLostError(RuntimeError):
    """Raised when an acquired lock loses validity before work commits."""


class DistributedLock(ABC):
    """Unified interface for distributed locks supporting context-manager usage."""

    @property
    @abstractmethod
    def key(self) -> str:
        """Redis key identifying the protected resource."""

    @abstractmethod
    def acquire(self) -> bool:
        """Attempt to acquire the lock, returning True on success."""

    @abstractmethod
    def release(self) -> bool:
        """Release the lock safely if still owned by this instance."""

    @abstractmethod
    def extend(self, ttl_ms: int | None = None) -> bool:
        """Extend the lock TTL safely if still owned by this instance."""

    @abstractmethod
    def is_valid(self) -> bool:
        """Return True if the lock is currently held and still valid."""

    def __enter__(self) -> Self:
        if not self.acquire():
            raise LockAcquisitionError(f"Failed to acquire distributed lock for {self.key!r}")
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        self.release()
