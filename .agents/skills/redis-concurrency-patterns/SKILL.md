---
name: redis-concurrency-patterns
description: Enforces Redis distributed lock invariants including atomic SET NX PX, Lua owner-checked release/extend scripts, Watchdog renewal threads, and 5-node independent Redlock quorum rules. Use whenever writing or reviewing lock managers or Lua scripts.
---

# Redis Distributed Lock Guardrails
1. **Atomic Acquire:** Always use `SET <key> <uuid_token> NX PX <ttl_ms>`. Never split into `EXISTS` + `SET`.
2. **Owner-Safe Release & Extend:** Always use atomic Lua scripts checking `redis.call("get", KEYS[1]) == ARGV[1]` before `DEL` or `PEXPIRE`.
3. **Watchdog Threading:** Spawn a `threading.Thread(..., daemon=True)` controlled by a `threading.Event` stop flag, renewing every `ttl_ms / 3` ms. Mark `is_valid()` as `False` if renewal fails so zombie workers cannot commit writes.
4. **Redlock Topology:** Target 5 independent Redis masters (never `redis-cli --cluster`). Require `acquired >= 3` and `remaining_time = ttl_ms - elapsed_ms - drift_ms > 0`; execute Lua release across all 5 nodes on partial failure.
