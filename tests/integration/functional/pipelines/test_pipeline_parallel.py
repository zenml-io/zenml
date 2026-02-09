#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import os
import pathlib
import platform
import subprocess
import sys
import tempfile
from typing import List, Tuple
from uuid import uuid1

import pytest

from zenml.client import Client

SUBPROCESS_TIMEOUT = 15 * 60  # 15 minutes per subprocess


def _spawn(cmd: List[str]) -> Tuple[subprocess.Popen, str]:
    """Spawn a subprocess with output redirected to a temp file.

    Redirecting to a file instead of subprocess.PIPE avoids the classic
    pipe-buffer deadlock: if the child writes more than ~64 KB to a PIPE
    and the parent is blocked in .wait(), both sides block forever.

    Args:
        cmd: Command to run.

    Returns:
        The Popen handle and the path to the temp log file.
    """
    fd, log_path = tempfile.mkstemp(suffix=".log", prefix="zenml_test_")
    log_fh = os.fdopen(fd, "w")
    proc = subprocess.Popen(cmd, stdout=log_fh, stderr=subprocess.STDOUT)
    log_fh.close()
    return proc, log_path


def _read_tail(log_path: str, max_bytes: int = 20_000) -> str:
    """Read the tail of a log file for failure diagnostics."""
    try:
        size = os.path.getsize(log_path)
        with open(log_path, "r", errors="replace") as f:
            if size > max_bytes:
                f.seek(size - max_bytes)
            return f.read()
    except OSError:
        return "<log file not readable>"


def _wait_and_assert(
    procs: List[Tuple[subprocess.Popen, str]],
    timeout: int = SUBPROCESS_TIMEOUT,
) -> None:
    """Wait for all subprocesses with a timeout, clean up on failure."""
    for idx, (proc, log_path) in enumerate(procs):
        try:
            proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=30)
            tail = _read_tail(log_path)
            pytest.fail(
                f"Subprocess {idx} timed out after {timeout}s.\n"
                f"--- log tail ---\n{tail}"
            )
        finally:
            if proc.returncode is None:
                proc.kill()
                proc.wait()

        if proc.returncode != 0:
            tail = _read_tail(log_path)
            pytest.fail(
                f"Subprocess {idx} failed (exit {proc.returncode}).\n"
                f"--- log tail ---\n{tail}"
            )

    for _, log_path in procs:
        try:
            os.unlink(log_path)
        except OSError:
            pass


class TestArtifactsManagement:
    @pytest.mark.skipif(
        platform.system().lower() == "windows",
        reason="Windows not fully support OS processes.",
    )
    def test_parallel_runs_can_register_same_artifact(
        self, clean_client: Client
    ):
        procs: List[Tuple[subprocess.Popen, str]] = []
        run_prefix = str(uuid1())
        steps_count = 20
        runs_count = 3
        for i in range(runs_count):
            procs.append(
                _spawn(
                    [
                        sys.executable,
                        str(
                            pathlib.Path(__file__).parent.resolve()
                            / "util_parallel_pipeline_script.py"
                        ),
                        run_prefix,
                        str(i),
                        str(steps_count),
                    ]
                )
            )
        _wait_and_assert(procs)

        for i in range(runs_count):
            res = clean_client.get_pipeline_run(f"{run_prefix}_{i}")
            assert res.status == "completed", "some pipeline failed"

        res = clean_client.list_artifact_versions(
            size=1000, artifact="artifact"
        )
        assert len(res.items) == runs_count * steps_count, (
            "not all artifacts are registered"
        )
        assert {r.load() for r in res.items} == {
            100 * i + j for i in range(runs_count) for j in range(steps_count)
        }, "not all artifacts are registered with proper values"
        assert {r.version for r in res.items} == {
            str(i) for i in range(1, runs_count * steps_count + 1)
        }, "not all artifacts are registered with proper unique versions"


@pytest.mark.skipif(
    platform.system().lower() == "windows",
    reason="Windows not fully support OS processes.",
)
def test_parallel_runs_get_different_run_indexes(clean_client: Client):
    procs: List[Tuple[subprocess.Popen, str]] = []
    for _ in range(5):
        procs.append(
            _spawn(
                [
                    sys.executable,
                    str(
                        pathlib.Path(__file__).parent.resolve()
                        / "run_basic_pipeline.py"
                    ),
                ]
            )
        )
    _wait_and_assert(procs)

    runs = clean_client.list_pipeline_runs(size=50)
    assert len(runs) == 5

    run_indexes = {r.index for r in runs}
    assert run_indexes == set(range(1, 6))
