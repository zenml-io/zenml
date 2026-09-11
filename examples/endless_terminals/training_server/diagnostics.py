"""Retain bounded memory and Ray evidence around a GPU worker failure."""

import argparse
import json
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any


def read_tail(path: Path, limit: int = 32768) -> str:
    """Read the final bytes without loading a potentially large log.

    Args:
        path: Diagnostic file.
        limit: Maximum bytes to read.

    Returns:
        Decoded tail or a concise read error.
    """
    try:
        with path.open("rb") as source:
            source.seek(max(0, path.stat().st_size - limit))
            return source.read(limit).decode(errors="replace")
    except OSError as exc:
        return f"unavailable: {type(exc).__name__}"


def process_memory() -> list[dict[str, Any]]:
    """Report the largest resident processes without recording command arguments.

    Returns:
        Up to fifteen process identities and RSS values in KiB.

    Raises:
        OSError: The process filesystem cannot be listed.
    """  # noqa: DOC502 - Path.iterdir propagates OSError.
    processes: list[dict[str, Any]] = []
    for path in Path("/proc").iterdir():
        if not path.name.isdigit():
            continue
        try:
            fields = dict(
                line.split(":", 1)
                for line in (path / "status").read_text().splitlines()
                if ":" in line
            )
            processes.append(
                {
                    "pid": int(path.name),
                    "name": fields.get("Name", "").strip(),
                    "rss_kib": int(fields.get("VmRSS", "0 kB").split()[0]),
                }
            )
        except (OSError, ValueError):
            continue
    return sorted(processes, key=lambda item: item["rss_kib"], reverse=True)[
        :15
    ]


def memory_sample() -> dict[str, Any]:
    """Collect host, container, shared-memory, GPU and process usage.

    Returns:
        JSON-safe measurements with explicit unavailable values.
    """
    result: dict[str, Any] = {
        "timestamp": time.time(),
        "host_meminfo": read_tail(Path("/proc/meminfo")),
        "processes": [],
        "cgroup": {},
    }
    try:
        result["processes"] = process_memory()
    except OSError as exc:
        result["process_query_error"] = type(exc).__name__
    for name in (
        "memory.current",
        "memory.peak",
        "memory.max",
        "memory.events",
        "memory.stat",
        "memory/memory.usage_in_bytes",
        "memory/memory.max_usage_in_bytes",
        "memory/memory.limit_in_bytes",
        "memory/memory.failcnt",
        "memory/memory.oom_control",
    ):
        path = Path("/sys/fs/cgroup") / name
        if path.exists():
            result["cgroup"][name] = read_tail(path)
    try:
        usage = shutil.disk_usage("/dev/shm")
        result["shared_memory"] = {"used": usage.used, "total": usage.total}
    except OSError as exc:
        result["shared_memory_query_error"] = type(exc).__name__
    try:
        gpu = subprocess.run(
            [
                "nvidia-smi",
                "--query-gpu=uuid,memory.used,memory.total",
                "--format=csv,noheader,nounits",
            ],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        result["gpu_memory_mib"] = gpu.stdout[:4096]
        result["gpu_query_exit_code"] = gpu.returncode
    except (OSError, subprocess.TimeoutExpired) as exc:
        result["gpu_query_error"] = type(exc).__name__
    return result


def collect() -> dict[str, Any]:
    """Collect mandatory Ray logs independently of the worker-log budget.

    Returns:
        Current usage, recent telemetry, mandatory Ray logs, and worker tails.
    """
    root = Path("/tmp/ray/session_latest/logs")
    mandatory = [
        root / name
        for name in (
            "raylet.out",
            "raylet.err",
            "gcs_server.out",
            "gcs_server.err",
            "debug_state.txt",
        )
    ]
    logs = {str(path): read_tail(path) for path in mandatory}
    for name in ("runtime-metrics.jsonl", "runtime-metrics.previous.jsonl"):
        path = Path("/checkpoints") / name
        logs[str(path)] = read_tail(path, 131072)
    try:
        workers = [
            path
            for path in root.iterdir()
            if path.is_file()
            and path.name.startswith(
                ("worker-", "python-core-worker-", "python-core-driver-")
            )
        ]
        workers.sort(key=lambda path: path.stat().st_mtime, reverse=True)
        logs.update({str(path): read_tail(path) for path in workers[:20]})
    except OSError as exc:
        logs["worker_listing_error"] = type(exc).__name__
    return {"memory": memory_sample(), "logs": logs}


def monitor(path: Path) -> None:
    """Write periodic samples for at most two hours with bounded disk usage.

    Args:
        path: JSONL output inside the transient checkpoint directory.
    """
    deadline = time.monotonic() + 7200
    while time.monotonic() < deadline:
        try:
            sample = memory_sample()
            if path.exists() and path.stat().st_size > 8 * 1024 * 1024:
                path.replace(path.with_name("runtime-metrics.previous.jsonl"))
            with path.open("a") as output:
                output.write(json.dumps(sample) + "\n")
        except (OSError, ValueError):
            pass
        time.sleep(5)


def main() -> None:
    """Collect one report or start the bounded background monitor."""
    parser = argparse.ArgumentParser(description=__doc__)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--collect", action="store_true")
    choice.add_argument("--monitor", type=Path)
    args = parser.parse_args()
    if args.collect:
        print(json.dumps(collect()))
    else:
        monitor(args.monitor)


if __name__ == "__main__":
    main()
