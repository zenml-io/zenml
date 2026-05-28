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
"""Step: run a single Harbor evaluation job via subprocess."""

import logging
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Annotated

from models.harbor_models import HarborRunSpec
from utils.harbor_cli import build_harbor_command, find_job_dir

from zenml import log_metadata, step

logger = logging.getLogger(__name__)


@step(enable_cache=False)
def run_harbor_job(spec: HarborRunSpec) -> Annotated[Path, "job_dir"]:
    """Execute `harbor run` for a single agent+model combination.

    Creates an isolated temp directory, runs Harbor inside it, then
    returns the path to the job output directory. The built-in
    PathMaterializer archives the entire directory tree as a .tar.gz
    artifact.

    Args:
        spec: The Harbor run specification.

    Returns:
        Path to the Harbor job output directory.
    """
    # Resolve dataset_path to absolute before running in a temp dir,
    # since Harbor needs to find the tasks from wherever cwd is.
    resolved_spec = spec.model_copy()
    dataset_p = Path(spec.dataset_path)
    if not dataset_p.is_absolute():
        candidates = [
            Path(__file__).parent.parent / spec.dataset_path,
            Path("/app") / spec.dataset_path,
            Path("/app/code") / spec.dataset_path,
            dataset_p,
        ]
        for c in candidates:
            if c.exists():
                resolved_spec.dataset_path = str(c.resolve())
                break

    # Debug: check which API keys are visible in this environment
    for k in ("DAYTONA_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        val = os.environ.get(k)
        logger.info("ENV %s = %s", k, f"set ({len(val)} chars)" if val else "NOT SET")

    work_dir = Path(tempfile.mkdtemp(prefix="harbor_"))
    cmd = build_harbor_command(resolved_spec)
    logger.info("Running Harbor: %s (cwd=%s)", " ".join(cmd), work_dir)

    result = subprocess.run(
        cmd,
        cwd=work_dir,
        capture_output=True,
        text=True,
    )

    logger.info("Harbor exit code: %d for %s", result.returncode, spec.label)
    if result.stdout:
        logger.info("Harbor stdout (last 500 chars): %s", result.stdout[-500:])
    if result.stderr:
        # Log first 2000 chars (likely contains the actual error) and last 1000
        stderr = result.stderr
        logger.warning(
            "Harbor stderr (%d chars) FIRST 2000: %s", len(stderr), stderr[:2000]
        )
        if len(stderr) > 2000:
            logger.warning("Harbor stderr LAST 1000: %s", stderr[-1000:])

    job_dir = find_job_dir(work_dir)
    logger.info("Found job directory: %s", job_dir)

    log_metadata(
        metadata={
            "harbor_returncode": result.returncode,
            "agent": spec.agent,
            "model": spec.model or "none",
            "label": spec.label,
            "job_dir_name": job_dir.name,
        }
    )

    return job_dir
