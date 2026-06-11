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
"""Pydantic models for Harbor eval campaign data flow.

These models form the typed contract between pipeline steps:
    HarborRunSpec   -- build_matrix produces, run_harbor_job consumes
    TrialResult     -- parsed from Harbor's per-trial output
    JobSummary      -- parse_harbor_job produces, build_report consumes
    CampaignReport  -- build_report produces (final artifact)
"""

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class HarborRunSpec(BaseModel):
    """Specification for a single Harbor trial.

    Each spec maps to one ZenML ``run_harbor_job`` step — one agent on one
    model against one task — which runs as a single Harbor job inside one
    Sandbox session. The campaign fans out one spec per ``(agent, model,
    task)`` cell of the matrix.
    """

    agent: str = Field(
        description="Harbor agent name, e.g. 'oracle' or 'terminus-2'"
    )
    model: Optional[str] = Field(
        default=None,
        description="LLM model for the agent (None for oracle which needs no model)",
    )
    task_path: str = Field(
        default="",
        description="Path to a Harbor task. For local datasets this is a "
        "directory containing a task.toml, relative to the example root or "
        "absolute (e.g. 'datasets/mini_harbor/add-function'). For registry "
        "tasks (see task_git_url) it is the task's sub-path inside the git "
        "repo (e.g. 'sample/chess-best-move'). Empty when a whole dataset is "
        "handed to Harbor (shape A registry runs)",
    )
    task_name: str = Field(
        description="Task identifier used for grouping and the report matrix, "
        "e.g. 'add-function' or 'chess-best-move'"
    )
    task_git_url: Optional[str] = Field(
        default=None,
        description="Git URL of the repo holding the task, for registry/git "
        "datasets like Terminal Bench. When set, run_harbor_job builds a "
        "git-backed TaskConfig instead of resolving a local path. Example: "
        "'https://github.com/laude-institute/terminal-bench-2-0-sample.git'",
    )
    task_git_commit_id: Optional[str] = Field(
        default=None,
        description="Pinned commit SHA for the git task, ensuring the exact "
        "task version is reproducible. Paired with task_git_url",
    )
    task_ref: Optional[str] = Field(
        default=None,
        description="Optional git ref (branch/tag) for the task, used instead "
        "of a pinned commit when task_git_commit_id is not available",
    )
    dataset_name: Optional[str] = Field(
        default=None,
        description="Harbor registry dataset name handed wholesale to a single "
        "Harbor job (shape A only), e.g. 'terminal-bench'. Harbor expands and "
        "schedules the tasks internally. Unused in shape B, where build_matrix "
        "expands the dataset into one spec per task",
    )
    dataset_version: Optional[str] = Field(
        default=None,
        description="Registry dataset version paired with dataset_name, e.g. "
        "'2.0'. Pins the dataset for reproducibility",
    )
    dataset_n_tasks: Optional[int] = Field(
        default=None,
        description="Cap on the number of tasks Harbor pulls from the dataset "
        "(shape A), applied after any task-name filtering. Handy for demos "
        "that want a slice of a large benchmark",
    )
    env_provider: Optional[str] = Field(
        default=None,
        description="Legacy Harbor environment provider (e.g. 'daytona'). Ignored by "
        "run_harbor_job: trials now execute through the active stack's ZenML Sandbox "
        "component via the ZenMLSandboxEnvironment bridge. Kept for config compatibility",
    )
    label: str = Field(
        default="",
        description="Human-readable label for this trial, e.g. 'oracle/add-function' "
        "or 'terminus-2/gpt-4o/add-function'",
    )


class TrialResult(BaseModel):
    """Result of a single task trial within a Harbor job."""

    trial_id: str = Field(description="Unique trial identifier from Harbor")
    task_name: str = Field(description="Name of the task (directory name)")
    reward: Optional[float] = Field(
        default=None,
        description="Reward value from verifier (typically 0.0 or 1.0)",
    )
    success: Optional[bool] = Field(
        default=None, description="Whether the trial passed (reward >= 1.0)"
    )
    duration_seconds: Optional[float] = Field(
        default=None, description="Wall-clock time for this trial"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if the trial failed to execute",
    )


class JobSummary(BaseModel):
    """Summary of a single Harbor job (one agent+model+task trial)."""

    spec: HarborRunSpec = Field(
        description="The run spec that produced this job"
    )
    job_id: str = Field(default="unknown", description="Harbor job identifier")
    trials: List[TrialResult] = Field(
        default_factory=list, description="Per-trial results"
    )
    total_trials: int = Field(
        default=0, description="Number of trials attempted"
    )
    passed_trials: int = Field(
        default=0, description="Number of trials that passed"
    )
    pass_rate: float = Field(
        default=0.0, description="Fraction of trials that passed (0.0 to 1.0)"
    )
    mean_reward: float = Field(
        default=0.0, description="Mean reward across all trials"
    )


class CampaignReport(BaseModel):
    """Full campaign report aggregating all job summaries."""

    summaries: List[JobSummary] = Field(
        default_factory=list, description="All job summaries in this campaign"
    )
    ranked: List[Dict[str, object]] = Field(
        default_factory=list,
        description="Leaderboard rows sorted by pass_rate descending",
    )
    total_jobs: int = Field(
        default=0, description="Number of jobs in the campaign"
    )
    total_trials: int = Field(
        default=0, description="Total trials across all jobs"
    )
    overall_pass_rate: float = Field(
        default=0.0, description="Weighted pass rate across all jobs"
    )
    failing_tasks: List[str] = Field(
        default_factory=list,
        description="Task names that failed across all agent+model combos",
    )
    matrix_table: List[Dict[str, object]] = Field(
        default_factory=list,
        description="Rows for the agent x task matrix table in the report",
    )
