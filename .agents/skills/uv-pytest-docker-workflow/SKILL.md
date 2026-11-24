---
name: uv-pytest-docker-workflow
description: Runs Python commands, dependency management, and Docker-backed pytest suites using uv. Use when scaffolding the project, managing packages, or running integration tests.
---

# Tooling & Execution Rules
- Manage dependencies and run tests exclusively with `uv` (`uv init`, `uv add`, `uv run pytest -v`). Never use `pip` or global `python`.
- Ensure the 5 Docker Compose Redis services (`redis-1`..`redis-5`) are running (`docker compose up -d && docker compose ps`) before executing integration tests.
- In Docker fault-injection fixtures (`docker pause` / `docker unpause`), always wrap `yield` in a `try...finally` block so paused containers are guaranteed to unpause even when a test fails.
