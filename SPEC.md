# Specification: Redis Distributed Lock & Ticket Inventory Demo

## 1. Overview & Goal
Build a clean, runnable Python reference repository demonstrating distributed concurrency control using Redis (`redis-py`) on a single developer machine (macOS / Apple Silicon via Docker Compose). The project showcases:
1. **Single-Node Distributed Lock** with atomic acquisition (`SET NX PX`), safe owner-token release/extension via Lua scripts, and a **Watchdog** background renewal thread.
2. **Redlock Algorithm** across **5 independent standalone Redis master nodes** (quorum = 3, clock-drift deduction, and multi-node rollback on partial acquisition failure) combined with Watchdog renewal.
3. **Thin Consumer Integration (`TicketInventoryService`)**: A minimal (~60–80 lines) SQLite-backed ticket booking service demonstrating how application code consumes a unified `DistributedLock` interface to prevent overselling under heavy concurrency.
4. **Automated Chaos & Concurrency `pytest` Suite**: Deterministic tests proving race-condition prevention, Watchdog TTL extension, safe owner-token release, and Redlock fault tolerance via Docker container pause/unpause.
5. **Storytelling Blog Content (`docs/blog/`)**: Accessible Medium article and LinkedIn post translating the implementation and test outcomes into a clear narrative for technical and non-technical readers.

---

## 2. Infrastructure (`docker-compose.yml`)
- Spin up **5 completely independent Redis master instances** (`redis-1` through `redis-5`) using `redis:7-alpine`.
- **Important:** Do NOT use Redis Cluster mode (`--cluster-enabled`). Redlock requires independent masters with zero replication or slot sharding.
- Expose host ports `6379`, `6380`, `6381`, `6382`, and `6383` mapped to container port `6379`.
- Enable AOF persistence (`redis-server --appendonly yes`) and lightweight healthchecks (`redis-cli ping`).

---

## 3. Repository Structure
```text
redis-distributed-lock-demo/
├── AGENTS.md
├── SPEC.md
├── README.md
├── docker-compose.yml
├── pyproject.toml
├── docs/
│   └── blog/
│       ├── medium-article.md
│       └── linkedin-post.md
├── .agents/
│   ├── skills/
│   │   ├── redis-concurrency-patterns/SKILL.md
│   │   └── uv-pytest-docker-workflow/SKILL.md
│   └── agents/
│       ├── lock-implementer.md
│       ├── senior-code-reviewer.md
│       ├── chaos-qa-engineer.md
│       ├── observability-instrumentor.md
│       ├── docs-and-diagrams-writer.md
│       └── blog-storyteller.md
├── src/
│   └── redis_lock_demo/
│       ├── __init__.py
│       ├── interfaces.py         # DistributedLock Protocol / ABC & custom exceptions
│       ├── lua_scripts.py        # Atomic RELEASE and EXTEND Lua scripts
│       ├── single_node.py        # SingleNodeLock + Watchdog thread
│       ├── redlock.py            # Redlock multi-master quorum + Watchdog thread
│       └── ticket_inventory.py   # Thin TicketInventoryService consumer (SQLite WAL)
└── tests/
    ├── conftest.py               # Redis clients, cleanup, and Docker pause/unpause fixtures
    ├── test_race_condition.py    # Overselling without lock vs. exact booking with lock
    ├── test_watchdog.py          # Long task > initial TTL stays protected via auto-renewal
    ├── test_safe_release.py      # Slow expired worker cannot delete new owner's lock
    └── test_redlock_quorum.py    # 2/5 paused nodes succeeds (3/5 quorum); 3/5 paused rolls back
```

---

## 4. Technical Requirements

### 4.1 Unified Lock Interface (`interfaces.py`)
- Define `DistributedLock` (ABC or `Protocol`) supporting context manager usage (`with lock:`):
  - `acquire() -> bool`
  - `release() -> bool`
  - `extend(ttl_ms: int | None = None) -> bool`
  - `is_valid() -> bool` (returns `False` if lock was released or Watchdog renewal failed)
- Define `LockAcquisitionError` and `LockLostError`.

### 4.2 Lua Scripts (`lua_scripts.py`)
- **Atomic Release (`RELEASE_SCRIPT`):**
  ```lua
  if redis.call("get", KEYS[1]) == ARGV[1] then
      return redis.call("del", KEYS[1])
  else
      return 0
  end
  ```
- **Atomic Extend (`EXTEND_SCRIPT`):**
  ```lua
  if redis.call("get", KEYS[1]) == ARGV[1] then
      return redis.call("pexpire", KEYS[1], ARGV[2])
  else
      return 0
  end
  ```

### 4.3 Single-Node Lock + Watchdog (`single_node.py`)
- Generate a cryptographically unique `owner_token` (`str(uuid.uuid4())`) per lock acquisition.
- Acquire via `client.set(key, owner_token, nx=True, px=ttl_ms)` with configurable `retry_count` and jittered `retry_delay_ms`.
- **Watchdog Thread:**
  - When `enable_watchdog=True`, spawn a daemon `threading.Thread` controlled by a `threading.Event` stop flag.
  - Sleep `ttl_ms / 3` ms between renewals; execute `EXTEND_SCRIPT`.
  - If `EXTEND_SCRIPT` returns `0` or raises a Redis error, mark internal validity flag `False` and terminate the watchdog thread cleanly.
  - On `release()`, signal the `threading.Event`, join the thread briefly, and execute `RELEASE_SCRIPT`.

### 4.4 Redlock Manager (`redlock.py`)
- Accept a list of $N$ independent `redis.Redis` clients (default 5 nodes, strict `socket_timeout=0.05` per node).
- Quorum = `(N // 2) + 1`.
- **Acquisition Algorithm:**
  1. Record `start_ms = time.monotonic() * 1000`.
  2. Attempt `SET key token NX PX ttl_ms` across all $N$ nodes (using `ThreadPoolExecutor(max_workers=N)` or bounded sequential loop).
  3. Compute `drift_ms = int(ttl_ms * 0.01) + 2`.
  4. Compute `elapsed_ms = (time.monotonic() * 1000) - start_ms`.
  5. Compute `remaining_ms = ttl_ms - elapsed_ms - drift_ms`.
  6. If `acquired_count >= quorum` and `remaining_ms > 0`: start Watchdog (if enabled, renewing across all nodes and requiring quorum renewal to stay valid) and return `True`.
  7. Otherwise: immediately execute `RELEASE_SCRIPT` on **all** $N$ nodes to clean up partial locks, retry with random jitter up to `retry_count`, and return `False` if exhausted.
- **Release:** Stop Watchdog and run `RELEASE_SCRIPT` across all $N$ nodes.

### 4.5 Thin Ticket Inventory Consumer (`ticket_inventory.py`)
- Minimal SQLite (`sqlite3`, WAL mode) store managing `events(event_id TEXT PRIMARY KEY, total_seats INT, available_seats INT)` and `bookings(booking_id TEXT PRIMARY KEY, event_id TEXT, user_id TEXT)`.
- `book_seat(event_id, user_id, lock_factory=None, processing_delay_s=0.1)`:
  - When `lock_factory` is provided, acquire `lock_factory(f"lock:event:{event_id}")`, verify `lock.is_valid()` before committing the SQLite update, and release in `finally`.
  - When `lock_factory=None`, run unprotected to demonstrate race-condition overselling.

---

## 5. Acceptance Criteria & Test Scenarios (`uv run pytest -v`)
1. `test_race_condition.py`: 15 concurrent workers try to book 5 available seats (`processing_delay_s=0.1`). Without lock: `available_seats < 0` or `len(bookings) > 5` (oversold). With `SingleNodeLock` and `Redlock`: `available_seats == 0` and `len(bookings) == 5`.
2. `test_watchdog.py`: Lock acquired with `ttl_ms=600` and `enable_watchdog=True`; task sleeps `1.8s` (`3x` TTL). Competing worker fails to acquire mid-task, `lock.is_valid()` stays `True`, and lock releases cleanly afterward.
3. `test_safe_release.py`: Worker A acquires lock (`ttl_ms=300`, `enable_watchdog=False`), sleeps `500ms` (lock expires), Worker B acquires same key, Worker A calls `release()` -> returns `False` and Worker B's key remains intact in Redis.
4. `test_redlock_quorum.py`:
   - Pause 2 containers (`redis-4`, `redis-5`): `Redlock` still acquires (3/5 quorum) and books seats.
   - Pause a 3rd container (`redis-3`): `Redlock` fails acquisition (`False`) and leaves 0 dangling keys on `redis-1` and `redis-2`.
   - Always unpause containers in `finally`.
