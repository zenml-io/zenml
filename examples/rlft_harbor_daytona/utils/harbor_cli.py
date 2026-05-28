# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Utilities for building and locating Harbor CLI invocations."""

import shutil
import sys
from pathlib import Path
from typing import List

from models.harbor_models import HarborRunSpec


def _find_harbor_binary() -> str:
    """Find the harbor CLI binary.

    Tries shutil.which first (works if harbor is on PATH), then
    falls back to looking next to the current Python interpreter
    (same venv).
    """
    found = shutil.which("harbor")
    if found:
        return found

    venv_bin = Path(sys.executable).parent / "harbor"
    if venv_bin.exists():
        return str(venv_bin)

    return "harbor"


def build_harbor_command(spec: HarborRunSpec) -> List[str]:
    """Build the `harbor run` CLI argument list from a run spec.

    Resolves the harbor binary from PATH or the current Python
    environment's bin directory.

    Args:
        spec: The Harbor run specification.

    Returns:
        List of CLI arguments suitable for subprocess.run().
    """
    harbor_bin = _find_harbor_binary()
    cmd = [harbor_bin, "run", "-a", spec.agent]

    if spec.model:
        cmd.extend(["-m", spec.model])

    if spec.dataset_path:
        cmd.extend(["-p", spec.dataset_path])

    if spec.dataset_ref:
        cmd.extend(["-d", spec.dataset_ref])

    if spec.env_provider:
        cmd.extend(["-e", spec.env_provider])

    if spec.n_concurrent is not None:
        cmd.extend(["-n", str(spec.n_concurrent)])

    cmd.append("--debug")

    cmd.extend(spec.extra_args)

    return cmd


def find_job_dir(work_dir: Path) -> Path:
    """Find the most recently created Harbor job directory.

    Harbor writes job output to `<work_dir>/jobs/<job-id>/`. When
    multiple runs exist, we pick the newest by directory mtime.

    Args:
        work_dir: The working directory where Harbor was invoked.

    Returns:
        Path to the most recent job directory.

    Raises:
        FileNotFoundError: If no job directories are found.
    """
    jobs_root = work_dir / "jobs"
    if not jobs_root.is_dir():
        raise FileNotFoundError(
            f"No 'jobs/' directory found in {work_dir}. "
            f"Harbor may not have run successfully."
        )

    job_dirs = sorted(
        [d for d in jobs_root.iterdir() if d.is_dir()],
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )

    if not job_dirs:
        raise FileNotFoundError(
            f"No job subdirectories found in {jobs_root}. "
            f"Harbor may not have produced output."
        )

    return job_dirs[0]
