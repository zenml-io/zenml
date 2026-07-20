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
"""Collect tracked rollout step runs into one queryable table artifact.

The step tier of the rollout record: when the trainer runs with rollout
step tracking active (see ``zenml_pipeline_writing.step_tracking``),
every rollout is a step run of this pipeline run with reward and
sandbox id attached as step metadata. This step reads them back through
the API into the same table shape ``ingest_rollout_traces`` produces
from traces.jsonl, so the lineage report works on either tier. Unlike
the file tier it needs no shared filesystem with the trainer, which is
what makes an isolated trainer step possible. What it does NOT carry:
training step index and policy version (recorded as -1/None) exist
only in prime-rl's trace records.
"""

import json
from typing import Any, Dict, List

import pandas as pd
from typing_extensions import Annotated

from zenml import get_step_context, log_metadata, step
from zenml.client import Client


@step(enable_cache=False)
def collect_rollout_steps(
    expected_min_rollouts: int = 1,
    name_prefix: str = "rollout_",
) -> Annotated[pd.DataFrame, "rollout_table"]:
    """Read the run's tracked rollout step runs into one table.

    Args:
        expected_min_rollouts: Fail below this row count. A partial or
            empty collection must fail loudly — silently under-recording
            is exactly the failure mode this table exists to prevent.
        name_prefix: Name prefix of tracked rollout step runs.

    Returns:
        One row per tracked rollout step run.

    Raises:
        RuntimeError: If fewer rollouts than expected were tracked.
    """
    client = Client()
    run_id = get_step_context().pipeline_run.id

    rows: List[Dict[str, Any]] = []
    page = 1
    while True:
        result = client.list_run_steps(
            pipeline_run_id=run_id,
            name=f"startswith:{name_prefix}",
            page=page,
            size=100,
            hydrate=True,
        )
        for step_run in result.items:
            metadata = step_run.run_metadata
            rows.append(
                {
                    "trace_id": step_run.name.removeprefix(name_prefix),
                    "train_step": -1,
                    "reward": metadata.get("reward"),
                    "rewards_json": json.dumps(
                        {"sandbox_scored": metadata.get("reward")},
                        sort_keys=True,
                    ),
                    "runtime_type": "zenml-sandbox",
                    "runtime_id": metadata.get("sandbox_session_id"),
                    "task_name": metadata.get("task"),
                    "policy_version": None,
                    "infra_error": metadata.get("infra_error"),
                    "step_run_status": step_run.status.value,
                    "timing_start": step_run.start_time.isoformat()
                    if step_run.start_time
                    else None,
                }
            )
        if page >= result.total_pages:
            break
        page += 1

    if len(rows) < expected_min_rollouts:
        raise RuntimeError(
            f"Collected only {len(rows)} tracked rollout step runs "
            f"(expected at least {expected_min_rollouts}). Refusing to "
            "record a partial table as if it were the full run."
        )

    table = pd.DataFrame(rows)
    metadata_dict: Dict[str, Any] = {
        "rollouts.n_collected": len(rows),
        "rollouts.n_with_runtime_id": int(table["runtime_id"].notna().sum()),
        "rollouts.tier": "step",
    }
    reward_series = table["reward"].dropna()
    if not reward_series.empty:
        metadata_dict["rollouts.mean_reward"] = float(reward_series.mean())
    log_metadata(metadata=metadata_dict)
    return table
