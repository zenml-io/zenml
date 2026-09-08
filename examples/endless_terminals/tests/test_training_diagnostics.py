"""Check bounded diagnostic evidence without requiring Linux, Ray, or a GPU."""

import os
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from training_server import diagnostics


def redirect_paths(
    monkeypatch: pytest.MonkeyPatch, roots: dict[str, Path]
) -> None:
    """Redirect diagnostic filesystem roots into controlled fixtures.

    Args:
        monkeypatch: Scoped replacement helper.
        roots: Absolute runtime roots and their temporary replacements.
    """
    monkeypatch.setattr(
        diagnostics, "Path", lambda value: roots.get(str(value), Path(value))
    )


def test_collection_keeps_mandatory_logs_when_worker_budget_is_full(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Retain Raylet and GCS tails even with more recent workers than the cap.

    Args:
        tmp_path: Diagnostic filesystem fixture.
        monkeypatch: Scoped filesystem and memory replacements.
    """
    logs = tmp_path / "logs"
    logs.mkdir()
    checkpoints = tmp_path / "checkpoints"
    checkpoints.mkdir()
    redirect_paths(
        monkeypatch,
        {"/tmp/ray/session_latest/logs": logs, "/checkpoints": checkpoints},
    )
    monkeypatch.setattr(diagnostics, "memory_sample", lambda: {"cgroup": {}})
    mandatory = [
        "raylet.out",
        "raylet.err",
        "gcs_server.out",
        "gcs_server.err",
        "debug_state.txt",
    ]
    for name in mandatory:
        path = logs / name
        path.write_text("old-prefix\n" + "m" * 32768)
        os.utime(path, (1, 1))
    for index in range(25):
        path = logs / f"worker-{index:02d}.out"
        path.write_text("old-prefix\n" + "w" * 32768)
        os.utime(path, (100 + index, 100 + index))
    (logs / "irrelevant.log").write_text("not collected")
    (logs / "worker-directory").mkdir()
    for name in ("runtime-metrics.jsonl", "runtime-metrics.previous.jsonl"):
        (checkpoints / name).write_text("old-prefix\n" + "t" * 131072)

    result = diagnostics.collect()
    collected = result["logs"]
    assert result["memory"] == {"cgroup": {}}
    assert set(collected) == {
        *(str(logs / name) for name in mandatory),
        *(str(logs / f"worker-{index:02d}.out") for index in range(5, 25)),
        str(checkpoints / "runtime-metrics.jsonl"),
        str(checkpoints / "runtime-metrics.previous.jsonl"),
    }
    assert all(
        collected[str(logs / name)] == "m" * 32768 for name in mandatory
    )
    assert (
        sum(len(value) for value in collected.values())
        == 25 * 32768 + 2 * 131072
    )


def test_missing_ray_directory_still_returns_memory_and_explicit_missing_logs(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Missing Ray files must not discard the memory evidence or required names.

    Args:
        tmp_path: Empty diagnostic filesystem.
        monkeypatch: Scoped diagnostic dependencies.
    """
    logs = tmp_path / "absent-logs"
    redirect_paths(
        monkeypatch,
        {"/tmp/ray/session_latest/logs": logs, "/checkpoints": tmp_path},
    )
    monkeypatch.setattr(
        diagnostics, "memory_sample", lambda: {"timestamp": 123}
    )
    result = diagnostics.collect()
    assert result["memory"] == {"timestamp": 123}
    assert (
        result["logs"][str(logs / "raylet.out")]
        == "unavailable: FileNotFoundError"
    )
    assert (
        result["logs"][str(logs / "gcs_server.err")]
        == "unavailable: FileNotFoundError"
    )
    assert result["logs"]["worker_listing_error"] == "FileNotFoundError"


@pytest.mark.parametrize(
    "files",
    [
        {
            "memory.current": "12345\n",
            "memory.max": "max\n",
            "memory.events": "low 0\noom 2\noom_kill 1\n",
        },
        {
            "memory/memory.usage_in_bytes": "54321\n",
            "memory/memory.failcnt": "2\n",
            "memory/memory.oom_control": "oom_kill_disable 0\nunder_oom 0\noom_kill 1\n",
        },
    ],
)
def test_memory_sample_retains_v1_and_v2_cgroup_counters(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, files: dict[str, str]
) -> None:
    """Preserve raw cgroup counters, including unlimited and OOM values.

    Args:
        tmp_path: Cgroup filesystem fixture.
        monkeypatch: Scoped process and GPU replacements.
        files: Either cgroup v1 or cgroup v2 kernel-file contents.
    """
    for name, value in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value)
    meminfo = tmp_path / "meminfo"
    meminfo.write_text("MemAvailable: 123 kB\n")
    redirect_paths(
        monkeypatch, {"/sys/fs/cgroup": tmp_path, "/proc/meminfo": meminfo}
    )
    monkeypatch.setattr(diagnostics, "process_memory", lambda: [])
    monkeypatch.setattr(
        shutil,
        "disk_usage",
        lambda _: SimpleNamespace(used=5, total=10),
    )
    gpu = SimpleNamespace(stdout="GPU-123, 100, 200\n", returncode=0)
    calls: list[dict[str, Any]] = []

    def query(command: list[str], **kwargs: Any) -> Any:
        calls.append({"command": command, **kwargs})
        return gpu

    monkeypatch.setattr(subprocess, "run", query)
    result = diagnostics.memory_sample()
    assert result["cgroup"] == files
    assert result["host_meminfo"] == "MemAvailable: 123 kB\n"
    assert result["shared_memory"] == {"used": 5, "total": 10}
    assert result["gpu_memory_mib"] == gpu.stdout
    assert calls[0]["timeout"] == 3


@pytest.mark.parametrize(
    "error", [FileNotFoundError(), subprocess.TimeoutExpired("nvidia-smi", 3)]
)
def test_gpu_query_failure_preserves_other_memory_evidence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, error: Exception
) -> None:
    """Keep container evidence when the GPU CLI is absent or hangs.

    Args:
        tmp_path: Empty cgroup filesystem.
        monkeypatch: Scoped host and GPU dependencies.
        error: Failure raised by the GPU query.
    """
    redirect_paths(monkeypatch, {"/sys/fs/cgroup": tmp_path})
    monkeypatch.setattr(
        diagnostics, "process_memory", lambda: [{"pid": 42, "rss_kib": 100}]
    )
    monkeypatch.setattr(
        shutil,
        "disk_usage",
        lambda _: SimpleNamespace(used=0, total=10),
    )

    def query(*args: Any, **kwargs: Any) -> None:
        raise error

    monkeypatch.setattr(subprocess, "run", query)
    result = diagnostics.memory_sample()
    assert result["gpu_query_error"] == type(error).__name__
    assert result["processes"] == [{"pid": 42, "rss_kib": 100}]
    assert result["shared_memory"] == {"used": 0, "total": 10}


def test_process_memory_limits_largest_residents_and_omits_arguments(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Ignore malformed or vanished processes and report only top resident sizes.

    Args:
        tmp_path: Fake proc filesystem.
        monkeypatch: Scoped proc root replacement.
    """
    for pid in range(1, 21):
        directory = tmp_path / str(pid)
        directory.mkdir()
        (directory / "status").write_text(
            f"Name:\tworker-{pid}\nVmRSS:\t{pid * 100} kB\n"
        )
        (directory / "cmdline").write_text("secret-in-process-arguments")
    (tmp_path / "21").mkdir()
    (tmp_path / "22").mkdir()
    (tmp_path / "22/status").write_text(
        "Name: malformed\nVmRSS: not-an-integer kB\n"
    )
    (tmp_path / "self").mkdir()
    redirect_paths(monkeypatch, {"/proc": tmp_path})
    result = diagnostics.process_memory()
    assert [item["pid"] for item in result] == list(range(20, 5, -1))
    assert result[0] == {"pid": 20, "name": "worker-20", "rss_kib": 2000}
    assert all(set(item) == {"pid", "name", "rss_kib"} for item in result)


def test_read_tail_decodes_partial_utf8_without_failing(
    tmp_path: Path,
) -> None:
    """A byte boundary inside a multibyte character must not break collection.

    Args:
        tmp_path: Diagnostic log fixture.
    """
    log = tmp_path / "log"
    log.write_bytes(b"old data" + "é!".encode())
    assert diagnostics.read_tail(log, 2) == "\ufffd!"


@pytest.mark.parametrize("unavailable", ["proc", "shared_memory", "both"])
def test_collect_preserves_ray_logs_when_memory_filesystems_are_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, unavailable: str
) -> None:
    """Report missing memory sources while retaining other usage and Ray evidence.

    Args:
        tmp_path: Runtime filesystem fixture.
        monkeypatch: Scoped filesystem and GPU dependencies.
        unavailable: Which memory filesystem should fail.
    """
    logs = tmp_path / "logs"
    logs.mkdir()
    (logs / "raylet.err").write_text("Raylet failure details\n")
    (logs / "gcs_server.out").write_text("GCS connection details\n")
    cgroup = tmp_path / "cgroup"
    cgroup.mkdir()
    (cgroup / "memory.events").write_text("oom 1\noom_kill 1\n")
    proc = tmp_path / "proc"
    if unavailable == "shared_memory":
        (proc / "42").mkdir(parents=True)
        (proc / "42/status").write_text("Name: worker\nVmRSS: 100 kB\n")
        (proc / "meminfo").write_text("MemAvailable: 123 kB\n")
    redirect_paths(
        monkeypatch,
        {
            "/proc": proc,
            "/proc/meminfo": proc / "meminfo",
            "/sys/fs/cgroup": cgroup,
            "/tmp/ray/session_latest/logs": logs,
            "/checkpoints": tmp_path,
        },
    )

    def disk_usage(path: str) -> SimpleNamespace:
        if unavailable in {"shared_memory", "both"}:
            raise PermissionError("shared memory is inaccessible")
        return SimpleNamespace(used=5, total=10)

    monkeypatch.setattr(shutil, "disk_usage", disk_usage)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(
            stdout="GPU-123, 10, 20\n", returncode=0
        ),
    )
    result = diagnostics.collect()
    assert (
        result["logs"][str(logs / "raylet.err")] == "Raylet failure details\n"
    )
    assert (
        result["logs"][str(logs / "gcs_server.out")]
        == "GCS connection details\n"
    )
    memory = result["memory"]
    assert memory["cgroup"]["memory.events"] == "oom 1\noom_kill 1\n"
    assert memory["gpu_memory_mib"] == "GPU-123, 10, 20\n"
    if unavailable in {"proc", "both"}:
        assert memory["process_query_error"] == "FileNotFoundError"
        assert memory["processes"] == []
        assert memory["host_meminfo"] == "unavailable: FileNotFoundError"
    else:
        assert memory["processes"] == [
            {"pid": 42, "name": "worker", "rss_kib": 100}
        ]
        assert "process_query_error" not in memory
    if unavailable in {"shared_memory", "both"}:
        assert memory["shared_memory_query_error"] == "PermissionError"
        assert "shared_memory" not in memory
    else:
        assert memory["shared_memory"] == {"used": 5, "total": 10}
        assert "shared_memory_query_error" not in memory
