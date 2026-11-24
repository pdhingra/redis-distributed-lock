from __future__ import annotations

from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager, contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import platform
import subprocess
import time
from typing import Any

import pytest
import redis
from redis.backoff import NoBackoff
from redis.retry import Retry

from redis_lock_demo import DEFAULT_REDIS_PORTS, DEFAULT_SOCKET_TIMEOUT_S, create_redlock_clients
from redis_lock_demo.ticket_inventory import TicketInventoryService

REPO_ROOT = Path(__file__).resolve().parent.parent
REDIS_SERVICES: tuple[tuple[str, int], ...] = tuple(
    (f"redis-{idx}", port) for idx, port in enumerate(DEFAULT_REDIS_PORTS, start=1)
)
SERVICE_TO_PORT: dict[str, int] = dict(REDIS_SERVICES)


def _run_docker(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["docker", *args],
        cwd=REPO_ROOT,
        check=check,
        capture_output=True,
        text=True,
    )


def _resolve_container_id(service_name: str, port: int) -> str:
    """Locate container ID via compose service first, then standalone name/port."""
    compose_res = _run_docker(["compose", "ps", "-q", service_name], check=False)
    cid = compose_res.stdout.strip()
    if cid:
        return cid.splitlines()[0].strip()

    name_res = _run_docker(["ps", "-q", "--filter", f"name=^/{service_name}$"], check=False)
    cid = name_res.stdout.strip()
    if cid:
        return cid.splitlines()[0].strip()

    port_res = _run_docker(["ps", "-q", "--filter", f"publish={port}"], check=False)
    cid = port_res.stdout.strip()
    if cid:
        return cid.splitlines()[0].strip()

    raise RuntimeError(f"Could not locate running Docker container for {service_name} (port {port})")


def _is_container_paused(container_id: str) -> bool:
    res = _run_docker(["inspect", "-f", "{{.State.Paused}}", container_id], check=False)
    return res.returncode == 0 and res.stdout.strip().lower() == "true"


def _unpause_container(container_id: str) -> None:
    if _is_container_paused(container_id):
        _run_docker(["unpause", container_id], check=True)


def _ping_port(port: int, timeout_s: float = 0.2) -> bool:
    client = redis.Redis(
        host="127.0.0.1",
        port=port,
        socket_timeout=timeout_s,
        socket_connect_timeout=timeout_s,
        retry=Retry(NoBackoff(), 0),
    )
    try:
        return bool(client.ping())
    except redis.RedisError:
        return False
    finally:
        client.close()


def _wait_for_redis_ready(port: int, timeout_s: float = 10.0) -> None:
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        if _ping_port(port):
            return
        time.sleep(0.05)
    raise TimeoutError(f"Redis on 127.0.0.1:{port} did not become ready within {timeout_s}s")


def _cleanup_lock_keys(clients: list[redis.Redis]) -> None:
    for client in clients:
        try:
            keys = list(client.scan_iter(match="lock:*", count=100))
            if keys:
                client.delete(*keys)
        except redis.RedisError:
            pass


@pytest.fixture(scope="session", autouse=True)
def ensure_redis_cluster_ready() -> Iterator[None]:
    """Ensure 5 independent Redis nodes on 6379-6383 are unpaused and healthy."""
    # Unpause any previously paused target containers if they exist.
    for service_name, port in REDIS_SERVICES:
        try:
            cid = _resolve_container_id(service_name, port)
        except RuntimeError:
            cid = ""
        if cid:
            _unpause_container(cid)

    if not all(_ping_port(port) for _, port in REDIS_SERVICES):
        _run_docker(["compose", "up", "-d"], check=True)

    for _, port in REDIS_SERVICES:
        _wait_for_redis_ready(port, timeout_s=15.0)

    try:
        yield
    finally:
        for service_name, port in REDIS_SERVICES:
            try:
                cid = _resolve_container_id(service_name, port)
            except RuntimeError:
                continue
            _unpause_container(cid)
            _wait_for_redis_ready(port, timeout_s=10.0)


@pytest.fixture
def redis_single(ensure_redis_cluster_ready: None) -> Iterator[redis.Redis]:
    """Single standalone Redis client on 127.0.0.1:6379 with isolated key cleanup."""
    client = redis.Redis(
        host="127.0.0.1",
        port=DEFAULT_REDIS_PORTS[0],
        socket_timeout=0.5,
        socket_connect_timeout=0.5,
        retry=Retry(NoBackoff(), 0),
    )
    _cleanup_lock_keys([client])
    try:
        yield client
    finally:
        _cleanup_lock_keys([client])
        client.close()


@pytest.fixture
def redlock_clients(ensure_redis_cluster_ready: None) -> Iterator[list[redis.Redis]]:
    """5 independent Redis clients with strict socket_timeout=0.05 and key cleanup."""
    clients = create_redlock_clients(socket_timeout=DEFAULT_SOCKET_TIMEOUT_S)
    _cleanup_lock_keys(clients)
    try:
        yield clients
    finally:
        _cleanup_lock_keys(clients)
        for client in clients:
            client.close()


@pytest.fixture
def ticket_service(tmp_path: Path) -> TicketInventoryService:
    """Fresh SQLite WAL TicketInventoryService per test."""
    return TicketInventoryService(tmp_path / "tickets.db")


@pytest.fixture
def pause_containers(
    ensure_redis_cluster_ready: None,
) -> Iterator[Callable[..., AbstractContextManager[list[str]]]]:
    """Pause/unpause named Redis Docker containers, guaranteeing unpause in finally."""
    active_paused: list[tuple[str, str]] = []

    @contextmanager
    def _pause(*service_names: str) -> Iterator[list[str]]:
        newly_paused: list[tuple[str, str]] = []
        try:
            for name in service_names:
                if name not in SERVICE_TO_PORT:
                    raise ValueError(f"Unknown Redis service: {name!r}")
                cid = _resolve_container_id(name, SERVICE_TO_PORT[name])
                if not _is_container_paused(cid):
                    _run_docker(["pause", cid], check=True)
                    newly_paused.append((name, cid))
                    active_paused.append((name, cid))
            yield [cid for _, cid in newly_paused]
        finally:
            for name, cid in reversed(newly_paused):
                _unpause_container(cid)
                if (name, cid) in active_paused:
                    active_paused.remove((name, cid))
            for name, _ in reversed(newly_paused):
                _wait_for_redis_ready(SERVICE_TO_PORT[name], timeout_s=10.0)

    try:
        yield _pause
    finally:
        for name, cid in reversed(list(active_paused)):
            _unpause_container(cid)
            _wait_for_redis_ready(SERVICE_TO_PORT[name], timeout_s=10.0)


@dataclass
class _MarkdownTestEntry:
    nodeid: str
    outcome: str = "passed"
    setup_s: float = 0.0
    call_s: float = 0.0
    teardown_s: float = 0.0
    log_lines: list[str] = field(default_factory=list)
    failure_detail: str = ""

    @property
    def total_s(self) -> float:
        return self.setup_s + self.call_s + self.teardown_s


class _MarkdownReportPlugin:
    def __init__(self, output_path: Path) -> None:
        self._output_path = output_path
        self._start_monotonic = time.monotonic()
        self._entries: dict[str, _MarkdownTestEntry] = {}

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        entry = self._entries.setdefault(report.nodeid, _MarkdownTestEntry(nodeid=report.nodeid))
        if report.when == "setup":
            entry.setup_s = report.duration
            if report.failed:
                entry.outcome = "error"
                entry.failure_detail = report.longreprtext
            elif report.skipped:
                entry.outcome = "skipped"
        elif report.when == "call":
            entry.call_s = report.duration
            if report.failed:
                entry.outcome = "failed"
                entry.failure_detail = report.longreprtext
            elif report.skipped:
                entry.outcome = "skipped"
            else:
                entry.outcome = "passed"
        elif report.when == "teardown":
            entry.teardown_s = report.duration
            if report.failed:
                entry.outcome = "error"
                if report.longreprtext:
                    entry.failure_detail = (
                        f"{entry.failure_detail}\n\n{report.longreprtext}".strip()
                    )

        caplog_text = getattr(report, "caplog", "")
        if caplog_text:
            for line in caplog_text.splitlines():
                stripped = line.strip()
                if stripped and stripped not in entry.log_lines:
                    entry.log_lines.append(stripped)

    def pytest_sessionfinish(self, session: pytest.Session, exitstatus: int | pytest.ExitCode) -> None:
        elapsed_s = time.monotonic() - self._start_monotonic
        entries = list(self._entries.values())
        passed = sum(1 for e in entries if e.outcome == "passed")
        failed = sum(1 for e in entries if e.outcome == "failed")
        errors = sum(1 for e in entries if e.outcome == "error")
        skipped = sum(1 for e in entries if e.outcome == "skipped")
        total = len(entries)
        status_label = "PASSED" if int(exitstatus) == 0 else f"FAILED (exit {int(exitstatus)})"
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

        lines: list[str] = [
            "# Chaos & Concurrency Test Report",
            "",
            f"- **Status:** `{status_label}`",
            f"- **Generated:** `{generated_at}`",
            f"- **Duration:** `{elapsed_s:.2f}s`",
            f"- **Environment:** Python `{platform.python_version()}`, pytest `{pytest.__version__}`",
            "- **Companion Reports:** `reports/junit.xml` (JUnit XML), `reports/test-report.html` (HTML)",
            "",
            "## Summary",
            "",
            "| Total | Passed | Failed | Errors | Skipped |",
            "| :---: | :---: | :---: | :---: | :---: |",
            f"| {total} | {passed} | {failed} | {errors} | {skipped} |",
            "",
            "## Test Results",
            "",
            "| Suite | Test | Status | Setup (s) | Call (s) | Teardown (s) | Total (s) |",
            "| :--- | :--- | :---: | :---: | :---: | :---: | :---: |",
        ]

        for entry in entries:
            suite, _, test_name = entry.nodeid.partition("::")
            safe_suite = suite.replace("|", "\\|")
            safe_test = (test_name or entry.nodeid).replace("|", "\\|")
            lines.append(
                f"| `{safe_suite}` | `{safe_test}` | `{entry.outcome.upper()}` "
                f"| {entry.setup_s:.3f} | {entry.call_s:.3f} | {entry.teardown_s:.3f} | {entry.total_s:.3f} |"
            )

        failures = [e for e in entries if e.failure_detail]
        if failures:
            lines.extend(["", "## Failure Details", ""])
            for entry in failures:
                lines.extend([
                    f"### `{entry.nodeid}`",
                    "",
                    "```text",
                    entry.failure_detail,
                    "```",
                    "",
                ])

        entries_with_logs = [e for e in entries if e.log_lines]
        if entries_with_logs:
            lines.extend(["", "## Structured Concurrency Log Excerpts", ""])
            for entry in entries_with_logs:
                max_lines = 25
                shown = entry.log_lines[:max_lines]
                omitted = len(entry.log_lines) - len(shown)
                lines.extend([
                    "<details>",
                    f"<summary><code>{entry.nodeid}</code> ({len(entry.log_lines)} log lines)</summary>",
                    "",
                    "```text",
                    *shown,
                    *(
                        [f"... ({omitted} additional log lines omitted)"]
                        if omitted > 0
                        else []
                    ),
                    "```",
                    "",
                    "</details>",
                    "",
                ])

        self._output_path.parent.mkdir(parents=True, exist_ok=True)
        self._output_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--md-report",
        action="store",
        default=None,
        help="Path to write a Markdown test summary report.",
    )


def pytest_configure(config: pytest.Config) -> None:
    md_report = config.getoption("--md-report", default=None)
    if md_report:
        output_path = Path(md_report)
        if not output_path.is_absolute():
            output_path = Path(config.rootpath) / output_path
        plugin: Any = _MarkdownReportPlugin(output_path)
        config.pluginmanager.register(plugin, name="markdown_report_plugin")
