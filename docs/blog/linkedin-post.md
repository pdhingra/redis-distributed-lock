Five concert seats left. Fifteen buyers clicked "Buy" at the exact same millisecond.
Without a lock, the demo app sold all 15 tickets and hit -10 seats remaining.

Most tutorials stop at `SET NX PX`. Production breaks right after—expired workers deleting someone else's lock, slow checkouts outliving their TTL, and Redis nodes disappearing mid-sale.

This GitHub repository (https://github.com/pdhingra/redis-distributed-lock) showcases a runnable Python + Docker Compose lab (`TicketInventoryService` on SQLite WAL) that reproduces and verifies every failure mode in `pytest`:

1. **Exact 5/5 bookings + safe release:** Locking serialized 15 concurrent workers into 5 exact seats and 10 clean sold-outs. UUID owner tokens plus an atomic Lua `RELEASE_SCRIPT` stopped an expired worker (500ms after a 300ms TTL) from deleting the next owner's lock.

2. **Watchdog 3x TTL survival:** A daemon heartbeat renewing every `ttl_ms / 3` kept a 1.8s checkout valid on a 600ms lease while blocking competitors mid-task.

3. **3/5 vs. 2/5 Redlock quorum under `docker pause`:** Across 5 independent Redis masters (not Cluster), pausing 2 containers still booked seats on a 3/5 majority. Pausing 3 dropped to 2/5 and rolled back with 0 dangling keys.

Key caveat: lease-based locks still need storage-side fencing tokens to protect against long GC pauses before commit.

Which concurrency bug has bitten your team worst—race conditions, stale expirations, or split failovers?
