# Chaos & Concurrency Test Report

- **Status:** `PASSED`
- **Generated:** `2026-11-24 05:44:15 UTC`
- **Duration:** `9.83s`
- **Environment:** Python `3.14.3`, pytest `9.2.0`
- **Companion Reports:** `reports/junit.xml` (JUnit XML), `reports/test-report.html` (HTML)

## Summary

| Total | Passed | Failed | Errors | Skipped |
| :---: | :---: | :---: | :---: | :---: |
| 9 | 9 | 0 | 0 | 0 |

## Test Results

| Suite | Test | Status | Setup (s) | Call (s) | Teardown (s) | Total (s) |
| :--- | :--- | :---: | :---: | :---: | :---: | :---: |
| `tests/test_race_condition.py` | `test_unprotected_booking_oversells` | `PASSED` | 0.539 | 0.171 | 0.000 | 0.710 |
| `tests/test_race_condition.py` | `test_single_node_lock_prevents_overselling` | `PASSED` | 0.007 | 0.831 | 0.001 | 0.839 |
| `tests/test_race_condition.py` | `test_redlock_prevents_overselling` | `PASSED` | 0.012 | 0.858 | 0.004 | 0.874 |
| `tests/test_redlock_quorum.py` | `test_redlock_survives_two_paused_nodes_and_books_seats` | `PASSED` | 0.021 | 0.713 | 0.003 | 0.737 |
| `tests/test_redlock_quorum.py` | `test_redlock_fails_with_three_paused_nodes_and_rolls_back` | `PASSED` | 0.006 | 1.256 | 0.004 | 1.266 |
| `tests/test_safe_release.py` | `test_single_node_expired_worker_cannot_delete_new_owners_lock` | `PASSED` | 0.001 | 0.512 | 0.006 | 0.518 |
| `tests/test_safe_release.py` | `test_redlock_expired_worker_cannot_delete_new_owners_lock` | `PASSED` | 0.013 | 0.517 | 0.003 | 0.533 |
| `tests/test_watchdog.py` | `test_single_node_watchdog_extends_ttl_for_long_task` | `PASSED` | 0.002 | 1.889 | 0.002 | 1.894 |
| `tests/test_watchdog.py` | `test_redlock_watchdog_extends_ttl_for_long_task` | `PASSED` | 0.013 | 1.914 | 0.500 | 2.427 |

## Structured Concurrency Log Excerpts

<details>
<summary><code>tests/test_race_condition.py::test_unprotected_booking_oversells</code> (15 log lines)</summary>

```text
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-13@ThreadPoolExecutor-0_13 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=104.77 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-14@ThreadPoolExecutor-0_14 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=105.67 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-3@ThreadPoolExecutor-0_3 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=106.00 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-4@ThreadPoolExecutor-0_4 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=106.28 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-11@ThreadPoolExecutor-0_11 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=106.77 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-10@ThreadPoolExecutor-0_10 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=107.29 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-2@ThreadPoolExecutor-0_2 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=108.11 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-6@ThreadPoolExecutor-0_6 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=109.35 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-8@ThreadPoolExecutor-0_8 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=113.48 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-0@ThreadPoolExecutor-0_0 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=114.20 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-5@ThreadPoolExecutor-0_5 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=115.66 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-1@ThreadPoolExecutor-0_1 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=126.95 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-12@ThreadPoolExecutor-0_12 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=128.09 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-9@ThreadPoolExecutor-0_9 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=145.12 lock_mode=unprotected
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-7@ThreadPoolExecutor-0_7 resource=lock:event:test-unprotected-d6313dc8 owner_token=- quorum_count=- elapsed_ms=166.86 lock_mode=unprotected
```

</details>

<details>
<summary><code>tests/test_race_condition.py::test_single_node_lock_prevents_overselling</code> (45 log lines)</summary>

```text
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=ThreadPoolExecutor-1_2 resource=lock:event:test-single-975079dd owner_token=257ca1a1 quorum_count=1 elapsed_ms=1.96 attempt=1 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-2@ThreadPoolExecutor-1_2 resource=lock:event:test-single-975079dd owner_token=257ca1a1 quorum_count=- elapsed_ms=113.90 lock_mode=SingleNodeLock
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=ThreadPoolExecutor-1_2 resource=lock:event:test-single-975079dd owner_token=257ca1a1 quorum_count=1 elapsed_ms=2.66
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=ThreadPoolExecutor-1_12 resource=lock:event:test-single-975079dd owner_token=522821a0 quorum_count=1 elapsed_ms=117.15 attempt=2 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-12@ThreadPoolExecutor-1_12 resource=lock:event:test-single-975079dd owner_token=522821a0 quorum_count=- elapsed_ms=224.57 lock_mode=SingleNodeLock
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=ThreadPoolExecutor-1_12 resource=lock:event:test-single-975079dd owner_token=522821a0 quorum_count=1 elapsed_ms=2.63
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=ThreadPoolExecutor-1_3 resource=lock:event:test-single-975079dd owner_token=44a8da6d quorum_count=1 elapsed_ms=233.32 attempt=3 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-3@ThreadPoolExecutor-1_3 resource=lock:event:test-single-975079dd owner_token=44a8da6d quorum_count=- elapsed_ms=345.48 lock_mode=SingleNodeLock
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=ThreadPoolExecutor-1_3 resource=lock:event:test-single-975079dd owner_token=44a8da6d quorum_count=1 elapsed_ms=1.37
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=ThreadPoolExecutor-1_11 resource=lock:event:test-single-975079dd owner_token=23ed9e5c quorum_count=1 elapsed_ms=366.59 attempt=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-11@ThreadPoolExecutor-1_11 resource=lock:event:test-single-975079dd owner_token=23ed9e5c quorum_count=- elapsed_ms=473.55 lock_mode=SingleNodeLock
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=ThreadPoolExecutor-1_11 resource=lock:event:test-single-975079dd owner_token=23ed9e5c quorum_count=1 elapsed_ms=1.00
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=ThreadPoolExecutor-1_13 resource=lock:event:test-single-975079dd owner_token=66b308ef quorum_count=1 elapsed_ms=483.34 attempt=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-13@ThreadPoolExecutor-1_13 resource=lock:event:test-single-975079dd owner_token=66b308ef quorum_count=- elapsed_ms=594.58 lock_mode=SingleNodeLock
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=ThreadPoolExecutor-1_13 resource=lock:event:test-single-975079dd owner_token=66b308ef quorum_count=1 elapsed_ms=2.43
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=ThreadPoolExecutor-1_0 resource=lock:event:test-single-975079dd owner_token=d3b1dfd1 quorum_count=1 elapsed_ms=599.30 attempt=6 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_sold_out worker_id=user-0@ThreadPoolExecutor-1_0 resource=lock:event:test-single-975079dd owner_token=d3b1dfd1 quorum_count=- elapsed_ms=601.51 lock_mode=SingleNodeLock
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=ThreadPoolExecutor-1_0 resource=lock:event:test-single-975079dd owner_token=d3b1dfd1 quorum_count=1 elapsed_ms=1.12
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=ThreadPoolExecutor-1_1 resource=lock:event:test-single-975079dd owner_token=7b534ff8 quorum_count=1 elapsed_ms=612.17 attempt=6 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_sold_out worker_id=user-1@ThreadPoolExecutor-1_1 resource=lock:event:test-single-975079dd owner_token=7b534ff8 quorum_count=- elapsed_ms=614.39 lock_mode=SingleNodeLock
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=ThreadPoolExecutor-1_1 resource=lock:event:test-single-975079dd owner_token=7b534ff8 quorum_count=1 elapsed_ms=1.48
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=ThreadPoolExecutor-1_8 resource=lock:event:test-single-975079dd owner_token=f1e825aa quorum_count=1 elapsed_ms=635.27 attempt=7 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_sold_out worker_id=user-8@ThreadPoolExecutor-1_8 resource=lock:event:test-single-975079dd owner_token=f1e825aa quorum_count=- elapsed_ms=637.95 lock_mode=SingleNodeLock
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=ThreadPoolExecutor-1_8 resource=lock:event:test-single-975079dd owner_token=f1e825aa quorum_count=1 elapsed_ms=2.24
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=ThreadPoolExecutor-1_10 resource=lock:event:test-single-975079dd owner_token=f668c8df quorum_count=1 elapsed_ms=644.53 attempt=8 ttl_ms=3000 watchdog=True
... (20 additional log lines omitted)
```

</details>

<details>
<summary><code>tests/test_race_condition.py::test_redlock_prevents_overselling</code> (45 log lines)</summary>

```text
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=ThreadPoolExecutor-2_0 resource=lock:event:test-redlock-011e119e owner_token=9c43ab80 quorum_count=5 elapsed_ms=3.92 attempt=1 attempt_elapsed_ms=3.75 remaining_ms=2964.25 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-0@ThreadPoolExecutor-2_0 resource=lock:event:test-redlock-011e119e owner_token=9c43ab80 quorum_count=- elapsed_ms=108.06 lock_mode=Redlock quorum_required=3
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=ThreadPoolExecutor-2_0 resource=lock:event:test-redlock-011e119e owner_token=9c43ab80 quorum_count=5 elapsed_ms=3.09 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=ThreadPoolExecutor-2_1 resource=lock:event:test-redlock-011e119e owner_token=cc70f817 quorum_count=5 elapsed_ms=123.49 attempt=2 attempt_elapsed_ms=2.77 remaining_ms=2965.23 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-1@ThreadPoolExecutor-2_1 resource=lock:event:test-redlock-011e119e owner_token=cc70f817 quorum_count=- elapsed_ms=228.44 lock_mode=Redlock quorum_required=3
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=ThreadPoolExecutor-2_1 resource=lock:event:test-redlock-011e119e owner_token=cc70f817 quorum_count=5 elapsed_ms=1.38 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=ThreadPoolExecutor-2_8 resource=lock:event:test-redlock-011e119e owner_token=b91b965d quorum_count=5 elapsed_ms=232.94 attempt=4 attempt_elapsed_ms=1.03 remaining_ms=2966.97 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-8@ThreadPoolExecutor-2_8 resource=lock:event:test-redlock-011e119e owner_token=b91b965d quorum_count=- elapsed_ms=338.62 lock_mode=Redlock quorum_required=3
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=ThreadPoolExecutor-2_8 resource=lock:event:test-redlock-011e119e owner_token=b91b965d quorum_count=5 elapsed_ms=1.51 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=ThreadPoolExecutor-2_9 resource=lock:event:test-redlock-011e119e owner_token=9c7d6d60 quorum_count=5 elapsed_ms=343.76 attempt=4 attempt_elapsed_ms=1.67 remaining_ms=2966.33 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-9@ThreadPoolExecutor-2_9 resource=lock:event:test-redlock-011e119e owner_token=9c7d6d60 quorum_count=- elapsed_ms=451.50 lock_mode=Redlock quorum_required=3
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=ThreadPoolExecutor-2_9 resource=lock:event:test-redlock-011e119e owner_token=9c7d6d60 quorum_count=5 elapsed_ms=1.18 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=ThreadPoolExecutor-2_10 resource=lock:event:test-redlock-011e119e owner_token=ecc152dc quorum_count=5 elapsed_ms=473.65 attempt=6 attempt_elapsed_ms=5.62 remaining_ms=2962.38 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-10@ThreadPoolExecutor-2_10 resource=lock:event:test-redlock-011e119e owner_token=ecc152dc quorum_count=- elapsed_ms=581.86 lock_mode=Redlock quorum_required=3
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=ThreadPoolExecutor-2_10 resource=lock:event:test-redlock-011e119e owner_token=ecc152dc quorum_count=5 elapsed_ms=1.22 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=ThreadPoolExecutor-2_12 resource=lock:event:test-redlock-011e119e owner_token=ff6e2c04 quorum_count=5 elapsed_ms=601.59 attempt=6 attempt_elapsed_ms=1.3 remaining_ms=2966.7 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_sold_out worker_id=user-12@ThreadPoolExecutor-2_12 resource=lock:event:test-redlock-011e119e owner_token=ff6e2c04 quorum_count=- elapsed_ms=602.51 lock_mode=Redlock quorum_required=3
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=ThreadPoolExecutor-2_12 resource=lock:event:test-redlock-011e119e owner_token=ff6e2c04 quorum_count=5 elapsed_ms=2.43 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=ThreadPoolExecutor-2_6 resource=lock:event:test-redlock-011e119e owner_token=a5c98909 quorum_count=5 elapsed_ms=606.20 attempt=7 attempt_elapsed_ms=2.33 remaining_ms=2965.67 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_sold_out worker_id=user-6@ThreadPoolExecutor-2_6 resource=lock:event:test-redlock-011e119e owner_token=a5c98909 quorum_count=- elapsed_ms=607.02 lock_mode=Redlock quorum_required=3
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=ThreadPoolExecutor-2_6 resource=lock:event:test-redlock-011e119e owner_token=a5c98909 quorum_count=5 elapsed_ms=1.91 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=ThreadPoolExecutor-2_4 resource=lock:event:test-redlock-011e119e owner_token=28a13a2f quorum_count=5 elapsed_ms=609.36 attempt=7 attempt_elapsed_ms=1.56 remaining_ms=2966.44 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_sold_out worker_id=user-4@ThreadPoolExecutor-2_4 resource=lock:event:test-redlock-011e119e owner_token=28a13a2f quorum_count=- elapsed_ms=610.16 lock_mode=Redlock quorum_required=3
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=ThreadPoolExecutor-2_4 resource=lock:event:test-redlock-011e119e owner_token=28a13a2f quorum_count=5 elapsed_ms=0.99 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=ThreadPoolExecutor-2_13 resource=lock:event:test-redlock-011e119e owner_token=0176a83f quorum_count=5 elapsed_ms=633.00 attempt=7 attempt_elapsed_ms=3.29 remaining_ms=2964.71 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
... (20 additional log lines omitted)
```

</details>

<details>
<summary><code>tests/test_redlock_quorum.py::test_redlock_survives_two_paused_nodes_and_books_seats</code> (5 log lines)</summary>

```text
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=MainThread resource=lock:event:test-quorum-ok-77d750d9 owner_token=daead261 quorum_count=3 elapsed_ms=52.28 attempt=1 attempt_elapsed_ms=52.18 remaining_ms=2915.82 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=MainThread resource=lock:event:test-quorum-ok-77d750d9 owner_token=daead261 quorum_count=3 elapsed_ms=52.33 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=MainThread resource=lock:event:test-quorum-ok-77d750d9 owner_token=59c953e1 quorum_count=3 elapsed_ms=52.54 attempt=1 attempt_elapsed_ms=52.42 remaining_ms=2915.58 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=True
INFO     redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_confirmed worker_id=user-quorum@MainThread resource=lock:event:test-quorum-ok-77d750d9 owner_token=59c953e1 quorum_count=- elapsed_ms=162.23 lock_mode=Redlock quorum_required=3
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=MainThread resource=lock:event:test-quorum-ok-77d750d9 owner_token=59c953e1 quorum_count=3 elapsed_ms=54.10 quorum_required=3 total_nodes=5
```

</details>

<details>
<summary><code>tests/test_redlock_quorum.py::test_redlock_fails_with_three_paused_nodes_and_rolls_back</code> (8 log lines)</summary>

```text
WARNING  redis_lock_demo.redlock:_logging.py:63 event=redlock_quorum_rollback worker_id=MainThread resource=lock:event:test-quorum-lost-aa7c6702 owner_token=dd74244b quorum_count=2 elapsed_ms=51.99 attempt=1 quorum_required=3 total_nodes=5 rolled_back_count=2 remaining_ms=2916.01 reason=quorum_not_reached
WARNING  redis_lock_demo.redlock:_logging.py:63 event=redlock_quorum_rollback worker_id=MainThread resource=lock:event:test-quorum-lost-aa7c6702 owner_token=dd74244b quorum_count=2 elapsed_ms=53.66 attempt=2 quorum_required=3 total_nodes=5 rolled_back_count=2 remaining_ms=2914.34 reason=quorum_not_reached
WARNING  redis_lock_demo.redlock:_logging.py:63 event=redlock_quorum_rollback worker_id=MainThread resource=lock:event:test-quorum-lost-aa7c6702 owner_token=dd74244b quorum_count=2 elapsed_ms=55.94 attempt=3 quorum_required=3 total_nodes=5 rolled_back_count=2 remaining_ms=2912.06 reason=quorum_not_reached
WARNING  redis_lock_demo.redlock:_logging.py:63 event=redlock_acquire_failed worker_id=MainThread resource=lock:event:test-quorum-lost-aa7c6702 owner_token=dd74244b quorum_count=0 elapsed_ms=425.00 attempts=3 quorum_required=3 total_nodes=5 reason=retries_exhausted
WARNING  redis_lock_demo.redlock:_logging.py:63 event=redlock_quorum_rollback worker_id=MainThread resource=lock:event:test-quorum-lost-aa7c6702 owner_token=37d2aa4c quorum_count=2 elapsed_ms=53.91 attempt=1 quorum_required=3 total_nodes=5 rolled_back_count=2 remaining_ms=2914.09 reason=quorum_not_reached
WARNING  redis_lock_demo.redlock:_logging.py:63 event=redlock_quorum_rollback worker_id=MainThread resource=lock:event:test-quorum-lost-aa7c6702 owner_token=37d2aa4c quorum_count=2 elapsed_ms=55.17 attempt=2 quorum_required=3 total_nodes=5 rolled_back_count=2 remaining_ms=2912.83 reason=quorum_not_reached
WARNING  redis_lock_demo.redlock:_logging.py:63 event=redlock_acquire_failed worker_id=MainThread resource=lock:event:test-quorum-lost-aa7c6702 owner_token=37d2aa4c quorum_count=0 elapsed_ms=291.97 attempts=2 quorum_required=3 total_nodes=5 reason=retries_exhausted
WARNING  redis_lock_demo.ticket_inventory:_logging.py:63 event=booking_lock_failed worker_id=user-no-quorum@MainThread resource=lock:event:test-quorum-lost-aa7c6702 owner_token=- quorum_count=0 elapsed_ms=292.25 lock_mode=Redlock
```

</details>

<details>
<summary><code>tests/test_safe_release.py::test_single_node_expired_worker_cannot_delete_new_owners_lock</code> (4 log lines)</summary>

```text
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=MainThread resource=lock:test:safe-release-single:7f304e52 owner_token=8f8f10d2 quorum_count=1 elapsed_ms=0.17 attempt=1 ttl_ms=300 watchdog=False
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=MainThread resource=lock:test:safe-release-single:7f304e52 owner_token=a6cf0fb8 quorum_count=1 elapsed_ms=2.77 attempt=1 ttl_ms=3000 watchdog=False
WARNING  redis_lock_demo.single_node:_logging.py:63 event=lock_release_stale worker_id=MainThread resource=lock:test:safe-release-single:7f304e52 owner_token=8f8f10d2 quorum_count=0 elapsed_ms=1.79 reason=token_mismatch_or_expired
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=MainThread resource=lock:test:safe-release-single:7f304e52 owner_token=a6cf0fb8 quorum_count=1 elapsed_ms=1.34
```

</details>

<details>
<summary><code>tests/test_safe_release.py::test_redlock_expired_worker_cannot_delete_new_owners_lock</code> (4 log lines)</summary>

```text
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=MainThread resource=lock:test:safe-release-redlock:e43f4c77 owner_token=06017ffa quorum_count=5 elapsed_ms=2.13 attempt=1 attempt_elapsed_ms=2.1 remaining_ms=292.9 quorum_required=3 total_nodes=5 ttl_ms=300 watchdog=False
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=MainThread resource=lock:test:safe-release-redlock:e43f4c77 owner_token=90b81a36 quorum_count=5 elapsed_ms=3.57 attempt=1 attempt_elapsed_ms=3.49 remaining_ms=2964.51 quorum_required=3 total_nodes=5 ttl_ms=3000 watchdog=False
WARNING  redis_lock_demo.redlock:_logging.py:63 event=redlock_release_incomplete worker_id=MainThread resource=lock:test:safe-release-redlock:e43f4c77 owner_token=06017ffa quorum_count=0 elapsed_ms=1.51 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=MainThread resource=lock:test:safe-release-redlock:e43f4c77 owner_token=90b81a36 quorum_count=5 elapsed_ms=1.25 quorum_required=3 total_nodes=5
```

</details>

<details>
<summary><code>tests/test_watchdog.py::test_single_node_watchdog_extends_ttl_for_long_task</code> (14 log lines)</summary>

```text
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=MainThread resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=0.48 attempt=1 ttl_ms=600 watchdog=True
INFO     redis_lock_demo.single_node:_logging.py:63 event=watchdog_renewed worker_id=watchdog-lock:test:watchdog-single:96c85324 resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=1.22 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.single_node:_logging.py:63 event=watchdog_renewed worker_id=watchdog-lock:test:watchdog-single:96c85324 resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=2.58 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.single_node:_logging.py:63 event=watchdog_renewed worker_id=watchdog-lock:test:watchdog-single:96c85324 resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=6.89 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.single_node:_logging.py:63 event=watchdog_renewed worker_id=watchdog-lock:test:watchdog-single:96c85324 resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=2.78 ttl_ms=600 source=watchdog
WARNING  redis_lock_demo.single_node:_logging.py:63 event=lock_acquire_failed worker_id=MainThread resource=lock:test:watchdog-single:96c85324 owner_token=3eeb78c4 quorum_count=0 elapsed_ms=73.06 attempts=2 reason=retries_exhausted
INFO     redis_lock_demo.single_node:_logging.py:63 event=watchdog_renewed worker_id=watchdog-lock:test:watchdog-single:96c85324 resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=1.14 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.single_node:_logging.py:63 event=watchdog_renewed worker_id=watchdog-lock:test:watchdog-single:96c85324 resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=3.02 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.single_node:_logging.py:63 event=watchdog_renewed worker_id=watchdog-lock:test:watchdog-single:96c85324 resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=2.87 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.single_node:_logging.py:63 event=watchdog_renewed worker_id=watchdog-lock:test:watchdog-single:96c85324 resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=2.98 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.single_node:_logging.py:63 event=watchdog_renewed worker_id=watchdog-lock:test:watchdog-single:96c85324 resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=2.70 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=MainThread resource=lock:test:watchdog-single:96c85324 owner_token=54cc3985 quorum_count=1 elapsed_ms=2.11
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_acquired worker_id=MainThread resource=lock:test:watchdog-single:96c85324 owner_token=aa3fd1ae quorum_count=1 elapsed_ms=1.44 attempt=1 ttl_ms=600 watchdog=False
INFO     redis_lock_demo.single_node:_logging.py:63 event=lock_released worker_id=MainThread resource=lock:test:watchdog-single:96c85324 owner_token=aa3fd1ae quorum_count=1 elapsed_ms=1.52
```

</details>

<details>
<summary><code>tests/test_watchdog.py::test_redlock_watchdog_extends_ttl_for_long_task</code> (14 log lines)</summary>

```text
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=MainThread resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=1.87 attempt=1 attempt_elapsed_ms=1.77 remaining_ms=590.23 quorum_required=3 total_nodes=5 ttl_ms=600 watchdog=True
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_watchdog_renewed worker_id=redlock-watchdog-lock:test:watchdog-redlock:b07c62a4 resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=6.57 quorum_required=3 total_nodes=5 remaining_ms=585.43 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_watchdog_renewed worker_id=redlock-watchdog-lock:test:watchdog-redlock:b07c62a4 resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=2.66 quorum_required=3 total_nodes=5 remaining_ms=589.33 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_watchdog_renewed worker_id=redlock-watchdog-lock:test:watchdog-redlock:b07c62a4 resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=6.64 quorum_required=3 total_nodes=5 remaining_ms=585.36 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_watchdog_renewed worker_id=redlock-watchdog-lock:test:watchdog-redlock:b07c62a4 resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=3.55 quorum_required=3 total_nodes=5 remaining_ms=588.45 ttl_ms=600 source=watchdog
WARNING  redis_lock_demo.redlock:_logging.py:63 event=redlock_acquire_failed worker_id=MainThread resource=lock:test:watchdog-redlock:b07c62a4 owner_token=015b8d14 quorum_count=0 elapsed_ms=81.64 attempts=2 quorum_required=3 total_nodes=5 reason=retries_exhausted
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_watchdog_renewed worker_id=redlock-watchdog-lock:test:watchdog-redlock:b07c62a4 resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=2.85 quorum_required=3 total_nodes=5 remaining_ms=589.15 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_watchdog_renewed worker_id=redlock-watchdog-lock:test:watchdog-redlock:b07c62a4 resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=6.15 quorum_required=3 total_nodes=5 remaining_ms=585.85 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_watchdog_renewed worker_id=redlock-watchdog-lock:test:watchdog-redlock:b07c62a4 resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=2.39 quorum_required=3 total_nodes=5 remaining_ms=589.61 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_watchdog_renewed worker_id=redlock-watchdog-lock:test:watchdog-redlock:b07c62a4 resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=6.35 quorum_required=3 total_nodes=5 remaining_ms=585.65 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_watchdog_renewed worker_id=redlock-watchdog-lock:test:watchdog-redlock:b07c62a4 resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=2.71 quorum_required=3 total_nodes=5 remaining_ms=589.29 ttl_ms=600 source=watchdog
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=MainThread resource=lock:test:watchdog-redlock:b07c62a4 owner_token=28943282 quorum_count=5 elapsed_ms=4.22 quorum_required=3 total_nodes=5
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_acquired worker_id=MainThread resource=lock:test:watchdog-redlock:b07c62a4 owner_token=bac9e63b quorum_count=5 elapsed_ms=2.61 attempt=1 attempt_elapsed_ms=2.52 remaining_ms=589.48 quorum_required=3 total_nodes=5 ttl_ms=600 watchdog=False
INFO     redis_lock_demo.redlock:_logging.py:63 event=redlock_released worker_id=MainThread resource=lock:test:watchdog-redlock:b07c62a4 owner_token=bac9e63b quorum_count=5 elapsed_ms=1.69 quorum_required=3 total_nodes=5
```

</details>
