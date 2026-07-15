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
"""HTML lineage report: the receipts the training run leaves behind."""

import html
from typing import Any, Dict, Optional

import pandas as pd
from typing_extensions import Annotated

from zenml import step
from zenml.types import HTMLString


def _table_rows(pairs: Dict[str, Any]) -> str:
    """Render key/value pairs as HTML table rows.

    Args:
        pairs: The key/value pairs.

    Returns:
        Concatenated ``<tr>`` rows.
    """
    return "".join(
        f"<tr><td>{html.escape(str(key))}</td>"
        f"<td><code>{html.escape(str(value))}</code></td></tr>"
        for key, value in pairs.items()
    )


@step
def build_lineage_report(
    rollout_table: pd.DataFrame,
    gate_verdict: Dict[str, Any],
    checkpoint_dir: Optional[str] = None,
) -> Annotated[HTMLString, "agentic_rl_report"]:
    """Render the run's lineage: gate, rollouts, sandbox join, weights.

    The centerpiece is the walk the RL spike found missing everywhere:
    reward -> runtime (sandbox session) id -> the environment that
    produced it, next to the checkpoint the run emitted. One sample
    rollout is walked explicitly so the join is demonstrated, not
    claimed.

    Args:
        rollout_table: The ingested per-rollout table.
        gate_verdict: The gate step's verdict dict.
        checkpoint_dir: The HF-format weights directory the trainer
            emitted (``<output_dir>/weights/step_N``), if any.

    Returns:
        The rendered HTML report.
    """
    reward_series = rollout_table["reward"].dropna()
    summary = {
        "rollouts ingested": len(rollout_table),
        "training steps": rollout_table["train_step"].nunique(),
        "mean reward": f"{reward_series.mean():.4f}"
        if not reward_series.empty
        else "n/a",
        "rollouts with sandbox id": int(
            rollout_table["runtime_id"].notna().sum()
        ),
        "infra errors recorded": int(
            rollout_table["infra_error"].notna().sum()
        ),
        "checkpoint": checkpoint_dir or "none recorded",
        "lineage tier": "file (rewards + sandbox ids; advantages/tokens "
        "need the prime-rl Monitor hook)",
    }

    sample_walk = "<p>No completed rollout with a reward to walk.</p>"
    scored = rollout_table.dropna(subset=["reward"])
    if not scored.empty:
        sample = scored.iloc[0]
        sample_walk = (
            "<ol>"
            f"<li>reward <code>{sample['reward']}</code> "
            f"(trace <code>{html.escape(str(sample['trace_id']))}</code>)</li>"
            f"<li>executed in runtime <code>"
            f"{html.escape(str(sample['runtime_type']))}:"
            f"{html.escape(str(sample['runtime_id']))}</code> — with the "
            "ZenML runtime in the loop this is the sandbox session id</li>"
            f"<li>task <code>{html.escape(str(sample['task_name']))}</code>, "
            f"policy version <code>{sample['policy_version']}</code></li>"
            f"<li>checkpoint <code>"
            f"{html.escape(str(checkpoint_dir or 'n/a'))}</code></li>"
            "</ol>"
        )

    per_step = ""
    if not scored.empty:
        grouped = scored.groupby("train_step")["reward"].agg(["count", "mean"])
        per_step = "".join(
            f"<tr><td>{index}</td><td>{row['count']:.0f}</td>"
            f"<td>{row['mean']:.4f}</td></tr>"
            for index, row in grouped.iterrows()
        )
        per_step = (
            "<h3>Reward by training step</h3>"
            "<table><tr><th>step</th><th>rollouts</th><th>mean reward"
            f"</th></tr>{per_step}</table>"
        )

    body = f"""
<style>
  .zenml-rl-report {{ font-family: sans-serif; max-width: 60rem; }}
  .zenml-rl-report table {{ border-collapse: collapse; }}
  .zenml-rl-report td, .zenml-rl-report th {{
    border: 1px solid #8884; padding: 0.3rem 0.6rem; text-align: left;
  }}
</style>
<div class="zenml-rl-report">
  <h2>Agentic RL run report</h2>
  <h3>Gate</h3>
  <table>{_table_rows(gate_verdict)}</table>
  <h3>Training rollouts</h3>
  <table>{_table_rows(summary)}</table>
  {per_step}
  <h3>The lineage walk (one sample rollout)</h3>
  {sample_walk}
</div>
"""
    return HTMLString(body)
