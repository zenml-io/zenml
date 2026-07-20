#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Ingest prime-rl rollout traces into one queryable table artifact.

prime-rl appends one full ``Rollout`` record (a ``verifiers`` ``Trace``
subclass) per rollout at completion to::

    <output_dir>/rollouts/step_{n}/{train,eval}/{all,effective}/traces.jsonl

This is the durable, zero-patching lineage channel — the trainer stays
one opaque step, but every rollout becomes a row. What the file tier
carries: rewards, the runtime/sandbox id, tool definitions, node
timestamps, timings, usage, env name, group id, policy version. What it
does NOT carry (excluded upstream by ``to_record()``): advantages,
tokens, logprobs, masks — those exist only in-process and need
prime-rl's Monitor hook, which has no injection point today.

Rollouts become **rows in one table artifact**, never mapped steps and
never per-rollout artifact versions — both variants re-create the
fan-out failures the RL spike ruled out.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd
from typing_extensions import Annotated

from zenml import log_metadata, step
from zenml.logger import get_logger

logger = get_logger(__name__)


def _flatten_record(
    record: Dict[str, Any], step_index: int, kind: str, subset: str
) -> Dict[str, Any]:
    """Flatten one Rollout record into a table row.

    Args:
        record: The parsed traces.jsonl line.
        step_index: The training step the record belongs to (from the
            directory layout).
        kind: ``train`` or ``eval`` (from the directory layout).
        subset: ``all`` or ``effective`` (from the directory layout).

    Returns:
        One flat row.
    """
    rewards = record.get("rewards") or {}
    runtime = record.get("runtime") or {}
    timing = record.get("timing") or {}
    task = record.get("task") or {}
    task_data = task.get("data") if isinstance(task, dict) else {}
    return {
        "trace_id": record.get("id"),
        "train_step": step_index,
        "kind": kind,
        "subset": subset,
        "env_name": record.get("env_name"),
        "group_id": record.get("group_id"),
        "policy_version": record.get("policy_version"),
        # The scalar most consumers want, plus the full dict for the
        # rest — reward keys are environment-defined.
        "reward": next(iter(rewards.values()), None)
        if len(rewards) == 1
        else rewards.get("reward"),
        "rewards_json": json.dumps(rewards, sort_keys=True),
        "metrics_json": json.dumps(
            record.get("metrics") or {}, sort_keys=True
        ),
        # The lineage join: with ZenMLSandboxRuntime in the loop this is
        # the ZenML sandbox session id that executed the rollout.
        "runtime_type": runtime.get("type"),
        "runtime_id": runtime.get("id"),
        "task_name": (task_data or {}).get("name"),
        "n_nodes": len(record.get("nodes") or []),
        "is_completed": record.get("is_completed"),
        "stop_condition": record.get("stop_condition"),
        "n_errors": len(record.get("errors") or []),
        "infra_error": (record.get("info") or {}).get("infra_error"),
        "timing_start": timing.get("start"),
    }


def _layout_facts(traces_file: Path) -> "tuple[int, str, str]":
    """Derive (train_step, kind, subset) from the trainer's dir layout.

    Args:
        traces_file: A traces.jsonl path.

    Returns:
        The layout facts, with fallbacks (-1, parent names) for files
        outside the ``rollouts/step_N/{kind}/{subset}/`` layout — e.g.
        verifiers' eval outputs, which share the schema but not the
        directory shape.
    """
    subset = traces_file.parent.name
    kind = traces_file.parent.parent.name
    step_dir = traces_file.parent.parent.parent.name
    try:
        step_index = int(step_dir.removeprefix("step_"))
    except ValueError:
        step_index = -1
    return step_index, kind, subset


@step(enable_cache=False)
def ingest_rollout_traces(
    output_dir: str,
    expected_min_rollouts: int = 1,
    traces_glob: str = "rollouts/step_*/*/*/traces.jsonl",
) -> Annotated[pd.DataFrame, "rollout_table"]:
    """Parse every traces.jsonl under an output dir into one table.

    Args:
        output_dir: The prime-rl ``--output-dir`` the trainer step wrote
            (or a verifiers eval output dir). On multi-machine stacks
            this must be shared storage; the trainer and this step
            exchange it by convention because the trainer is a command
            step with no outputs.
        expected_min_rollouts: Fail below this row count. A partial or
            empty ingest must fail loudly — silently under-recording is
            exactly the failure mode this table exists to prevent.
        traces_glob: Glob relative to ``output_dir``. The default
            matches prime-rl's training layout; verifiers eval runs use
            ``**/traces.jsonl`` (same record schema, different layout).

    Returns:
        One row per rollout across all training steps.

    Raises:
        RuntimeError: If no traces files match or fewer rollouts than
            expected were ingested.
    """
    root = Path(output_dir)
    traces_files = sorted(root.glob(traces_glob))
    if not traces_files:
        raise RuntimeError(
            f"No traces.jsonl matches {traces_glob!r} under {root}. "
            "Either the run never produced rollouts or output_dir is "
            "not shared between the producing step and this step."
        )

    rows: List[Dict[str, Any]] = []
    n_bad_lines = 0
    for traces_file in traces_files:
        step_index, kind, subset = _layout_facts(traces_file)
        for line in traces_file.read_text().splitlines():
            if not line.strip():
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                n_bad_lines += 1
                continue
            rows.append(_flatten_record(record, step_index, kind, subset))

    if n_bad_lines:
        logger.warning(
            "Skipped %d unparseable lines in traces.jsonl files "
            "(interrupted writes are expected on killed runs).",
            n_bad_lines,
        )
    if len(rows) < expected_min_rollouts:
        raise RuntimeError(
            f"Ingested only {len(rows)} rollouts from {root} "
            f"(expected at least {expected_min_rollouts}). Refusing to "
            "record a partial table as if it were the full run."
        )

    table = pd.DataFrame(rows)
    n_with_runtime = int(table["runtime_id"].notna().sum())
    metadata: Dict[str, Any] = {
        "rollouts.n_ingested": len(rows),
        "rollouts.n_bad_lines": n_bad_lines,
        "rollouts.n_with_runtime_id": n_with_runtime,
        "rollouts.train_steps": int(table["train_step"].nunique()),
        # Honesty marker: this is the file-tier record. Advantages and
        # tokens are excluded upstream and are NOT in this table.
        "rollouts.tier": "file",
    }
    reward_series = table["reward"].dropna()
    if not reward_series.empty:
        metadata["rollouts.mean_reward"] = float(reward_series.mean())
    log_metadata(metadata=metadata)
    return table
