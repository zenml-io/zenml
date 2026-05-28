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
"""Step: parse Harbor job output into a structured JobSummary."""

import json
import logging
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

from models.harbor_models import HarborRunSpec, JobSummary, TrialResult

from zenml import step

logger = logging.getLogger(__name__)


def _read_reward(trial_dir: Path) -> Optional[float]:
    """Read the reward value from a trial's verifier output."""
    reward_file = trial_dir / "verifier" / "reward.txt"
    if not reward_file.exists():
        reward_file = trial_dir / "logs" / "verifier" / "reward.txt"
    if not reward_file.exists():
        return None
    try:
        return float(reward_file.read_text().strip())
    except (ValueError, OSError):
        return None


def _compute_duration(data: dict) -> Optional[float]:
    """Compute wall-clock seconds from Harbor's started_at/finished_at."""
    from datetime import datetime

    started = data.get("started_at")
    finished = data.get("finished_at")
    if not started or not finished:
        return None
    try:
        fmt = "%Y-%m-%dT%H:%M:%S.%f"
        dt = datetime.strptime(finished, fmt) - datetime.strptime(started, fmt)
        return dt.total_seconds()
    except (ValueError, TypeError):
        return None


def _parse_trial(trial_dir: Path) -> TrialResult:
    """Parse a single trial directory into a TrialResult.

    Harbor's result.json has this structure:
        task_name: str
        verifier_result.rewards.reward: float
        exception_info: dict | null
        started_at / finished_at: ISO timestamps
    """
    trial_id = trial_dir.name
    task_name = trial_id

    result_file = trial_dir / "result.json"
    if result_file.exists():
        try:
            data = json.loads(result_file.read_text())
            task_name = data.get("task_name", trial_id)

            # Reward lives in verifier_result.rewards.reward
            reward = None
            verifier = data.get("verifier_result") or {}
            rewards_dict = verifier.get("rewards") or {}
            if "reward" in rewards_dict:
                reward = float(rewards_dict["reward"])

            duration = _compute_duration(data)

            error = None
            exc_info = data.get("exception_info")
            if exc_info:
                error = str(exc_info)

            return TrialResult(
                trial_id=trial_id,
                task_name=task_name,
                reward=reward,
                success=reward is not None and reward >= 1.0,
                duration_seconds=duration,
                error=error,
            )
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to parse %s: %s", result_file, exc)

    # Fallback: read reward directly from verifier/reward.txt
    reward = _read_reward(trial_dir)
    return TrialResult(
        trial_id=trial_id,
        task_name=task_name,
        reward=reward,
        success=reward is not None and reward >= 1.0,
        duration_seconds=None,
        error=None,
    )


def _find_trial_dirs(job_dir: Path) -> List[Path]:
    """Find trial subdirectories inside a job directory.

    Harbor stores trials as subdirectories of the job dir. We look
    for directories that contain either result.json or a verifier/
    subdirectory.
    """
    if not job_dir.is_dir():
        return []

    trials = []
    for child in sorted(job_dir.iterdir()):
        if not child.is_dir():
            continue
        has_result = (child / "result.json").exists()
        has_verifier = (child / "verifier").is_dir() or (
            child / "logs" / "verifier"
        ).is_dir()
        if has_result or has_verifier:
            trials.append(child)
    return trials


@step
def parse_harbor_job(
    job_dir: Path, spec: HarborRunSpec
) -> Annotated[Dict[str, Any], "job_summary"]:
    """Parse Harbor job output into a structured summary dict.

    Returns a dict (via JobSummary.model_dump()) rather than a Pydantic
    model directly, because ZenML's dynamic pipeline list collection
    uses the built-in JSON materializer for Dict types. The downstream
    build_report step reconstructs JobSummary objects from these dicts.

    Args:
        job_dir: Path to the Harbor job output directory.
        spec: The original run spec (for labeling).

    Returns:
        A dict representation of JobSummary.
    """
    logger.info("Parsing job dir: %s for %s", job_dir, spec.label)

    job_id = job_dir.name
    trial_dirs = _find_trial_dirs(job_dir)
    trials = [_parse_trial(td) for td in trial_dirs]

    total = len(trials)
    passed = sum(1 for t in trials if t.success)
    rewards = [t.reward for t in trials if t.reward is not None]
    mean_reward = sum(rewards) / len(rewards) if rewards else 0.0
    pass_rate = passed / total if total > 0 else 0.0

    stderr_file = job_dir / "stderr.log"
    stderr_tail = ""
    if stderr_file.exists():
        try:
            lines = stderr_file.read_text().splitlines()
            stderr_tail = "\n".join(lines[-20:])
        except OSError:
            pass

    returncode_file = job_dir / "returncode"
    harbor_returncode = -1
    if returncode_file.exists():
        try:
            harbor_returncode = int(returncode_file.read_text().strip())
        except (ValueError, OSError):
            pass

    summary = JobSummary(
        spec=spec,
        job_id=job_id,
        trials=trials,
        total_trials=total,
        passed_trials=passed,
        pass_rate=pass_rate,
        mean_reward=mean_reward,
        harbor_returncode=harbor_returncode,
        stderr_tail=stderr_tail,
    )

    logger.info(
        "Job %s: %d/%d passed (%.1f%%), mean_reward=%.2f",
        spec.label, passed, total, pass_rate * 100, mean_reward,
    )
    return summary.model_dump()
