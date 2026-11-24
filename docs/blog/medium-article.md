# How Fifteen Fans Bought Five Concert Tickets — And How Distributed Locks Stop the Chaos

## From an oversold SQLite checkout to atomic Lua scripts, Watchdog renewals, and a 5-node Redlock quorum

Five front-row concert seats drop at noon. Fifteen fans hit **Buy Now** at the exact same millisecond.

In an unprotected web app, every request checks the database, sees five seats left, pauses briefly to charge a card, and subtracts one. Because all fifteen buyers read `5` before anyone writes `4`, half a second later fifteen confirmation emails go out—and inventory hits `-10`.

Our repository reproduces this in `tests/test_race_condition.py`. Fifteen threads inside `TicketInventoryService` start behind a barrier for five seats with a `100ms` delay, and all fifteen book a seat.

Engineers call this a **race condition**: two clerks glancing at the same chalkboard tally, both seeing "5 left," and both selling the seat before either updates the board.

---

### Step 1: One Buyer at the Booth (`SET NX PX`)

To stop overselling, we need **mutual exclusion**—like a single brass key hanging behind a coffee counter where only the clerk holding it can edit the ledger.

Redis keeps that brass key in shared memory with one command:

```python
# Set only if missing (nx=True), auto-expire in 3,000ms (px=3000)
acquired = client.set(
    "lock:event:show-2026", owner_token, nx=True, px=3000
)
```

Two flags do the work:

- `NX` (**Not eXists**): Grant the lock only if nobody else holds it.
- `PX 3000`: Add a **TTL (time-to-live)**—a self-destructing reservation slip that expires after `3,000` milliseconds.

Without `PX`, a server crashing mid-checkout would keep the key forever and freeze sales. When `SingleNodeLock` protects `TicketInventoryService`, waiting threads retry with **jitter**—a slightly randomized pause (`0.5x` to `1.5x` of `retry_delay_ms`) so shoppers don't knock on the booth door in lockstep.

Under that same 15-thread rush, Redis serializes access cleanly. Five buyers get tickets, ten get a polite "sold out," and `available_seats` stops at `0`.

---

### Step 2: The Trap of Deleting Someone Else's Lock

Expiration saves us from crashed servers, yet introduces a hazard when a worker merely stalls.

Suppose Worker A grabs a `300ms` lock (Watchdog disabled) and freezes for `500ms`. At `300ms`, Redis expires the key, and Worker B acquires it with a new token.

When Worker A wakes up and blindly calls `DEL`, it erases *Worker B's* active lock—letting Worker C walk right in. Checking `GET` then `DEL` in Python still fails because the key can expire between those two network calls.

Instead, we pair a `uuid.uuid4()` **owner token** (like a stamped festival wristband) with an **atomic Lua script**—a sealed card of instructions Redis executes in one uninterrupted breath:

```lua
-- RELEASE_SCRIPT: delete only if our stamped wristband still matches
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
```

In `tests/test_safe_release.py`, Worker A wakes after `500ms` and calls `release()`. Redis compares the mismatched wristband IDs inside that single Lua call, returns `0` (`False`), and keeps Worker B's lock intact across both `SingleNodeLock` and 5-node `Redlock` until Worker B unlocks cleanly.

---

### Step 3: Keeping Slow Checkouts Alive With a Watchdog

Safe release protects Worker B, yet Worker A still lost its reservation over a slow payment. Huge initial TTLs aren't ideal either—if Worker A really crashes, buyers wait minutes.

Enter the **Watchdog**: an automated parking-meter app that drops another quarter in every few minutes while you dine, then stops the instant you leave.

With `enable_watchdog=True`, both `SingleNodeLock` and `Redlock` run a background daemon thread. Every `ttl_ms / 3` milliseconds, it sends `EXTEND_SCRIPT` to refresh the lease—giving the Watchdog two spare chances before expiry if one heartbeat hits a brief hiccup, while Redlock requires a majority to keep renewing.

If renewal fails, the Watchdog flips `lock.is_valid()` to `False` and exits. Right before committing to SQLite—in **WAL (Write-Ahead Log) mode**, a side notebook so readers and writers don't block each other—the service checks that flag:

```python
if lock is not None and not lock.is_valid():
    raise LockLostError(f"Lock lost before committing booking for {event_id!r}")
conn.execute("UPDATE events SET available_seats = available_seats - 1 ...")
```

In `tests/test_watchdog.py`, a `600ms` lock survives a `1.8s` task (`3x` TTL) by renewing every `200ms`, blocking competitors mid-task before releasing cleanly.

---

### Step 4: When the Redis Server Itself Dies (`Redlock`)

A single Redis box is still a single point of failure. If it reboots, checkouts halt.

Standard primary-replica setups don't fix this because Redis replicates asynchronously. A primary can grant a lock, crash before syncing to its replica, and let the promoted replica hand the same key to a second buyer.

Redis Cluster also hashes each key to one shard master. **Redlock** avoids both pitfalls by voting across **five independent Redis masters** (`redis-1`–`redis-5` on ports `6379`–`6383`) with zero replication.

`Redlock.acquire()` fans out `SET NX PX` across all five nodes in parallel via `ThreadPoolExecutor`. By configuring `socket_timeout=0.05` and `Retry(NoBackoff(), 0)` in `create_redlock_clients()`, frozen servers fail in 50ms instead of stalling healthy checkouts.

Two checks decide success:

- **Quorum (3 of 5 masters):** Like a five-judge panel needing three matching stamps, a majority prevents two buyers from claiming consensus simultaneously.
- **Clock drift deduction:** Because server clocks tick at slightly different speeds like cheap wristwatches, Redlock deducts elapsed time plus `drift_ms = int(ttl_ms * 0.01) + 2`, succeeding only if `remaining_ms > 0`.

```text
acquire() ---> parallel SET NX PX to redis-1..5 (50ms timeout)
                   |
     +-------------+-------------+
     | >= 3 votes & time left    | < 3 votes (or time expired)
     v                           v
 Start Watchdog              RELEASE_SCRIPT on ALL 5 nodes
 (must renew >= 3 nodes)     (0 dangling locks, retry w/ jitter)
```

If fewer than three nodes reply, Redlock immediately runs `RELEASE_SCRIPT` across all five masters to wipe partial locks, then retries with random jitter.

Our `tests/test_redlock_quorum.py` chaos suite tests this with `docker pause` (always unpausing in `finally:` and sweeping keys in `tests/conftest.py`):

- **Pause 2 of 5 (`redis-4`, `redis-5`):** A `3/5` quorum holds, booking a seat cleanly in SQLite.
- **Pause 3 of 5 (`redis-3`, `redis-4`, `redis-5`):** Dropping to `2/5` causes `acquire()` to return `False`, raises `LockAcquisitionError`, and leaves **zero dangling `lock:*` keys** on `redis-1` or `redis-2`.

---

### The Honest Caveat: What Distributed Locks Can't See

One edge case remains beyond any lease lock's reach: extreme process pauses.

Suppose Worker A sees `lock.is_valid() == True` and hits a long garbage-collection pause or VM freeze right before SQLite writes. Meanwhile its lock expires, Worker B buys the last seat, and Worker A wakes up and commits stale data.

Fixing that requires a **fencing token**—a rising number, like a numbered deli-counter ticket, enforced by the database so it rejects ticket `#41` after serving `#42`. Our demo uses pre-commit `is_valid()` checks rather than storage-side fencing tokens.

Likewise, `docker-compose.yml` starts Redis with `--appendonly yes` (`appendfsync everysec`), meaning up to one second of locks could vanish during an instant crash. Production Redlock deployments wait `max_ttl` before restarting crashed masters so stale locks expire safely first.

---

### Walkthrough: Run the Chaos Lab Yourself

Spin up all five masters and run the verified chaos suite locally:

```bash
docker compose up -d   # 5 independent redis:7-alpine masters (6379-6383)
uv sync                # Install redis-py >= 5.2.0 and pytest
uv run pytest -v       # Run 4 suites (9 tests) in ~10s
```

Repo map:

- `docker-compose.yml`: Five standalone Redis masters (`6379`–`6383`), no cluster mode or replicas.
- `src/redis_lock_demo/interfaces.py` & `lua_scripts.py`: `DistributedLock` interface and atomic Lua scripts.
- `src/redis_lock_demo/single_node.py` & `redlock.py`: `SingleNodeLock` + Watchdog and 5-node `Redlock` + rollback.
- `src/redis_lock_demo/ticket_inventory.py`: Thin SQLite WAL `TicketInventoryService` consumer.
- `tests/`: `test_race_condition.py`, `test_safe_release.py`, `test_watchdog.py`, and `test_redlock_quorum.py` backed by `docker pause` fixtures in `conftest.py`.

Run `uv run pytest -v -s --log-cli-level=INFO` to watch structured logs (`worker_id`, `owner_token`, `quorum_count`, `elapsed_ms`) stream live as containers freeze and recover.
