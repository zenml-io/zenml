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
"""verifiers-native eval as a pipeline: `uv run eval` + trace ingest.

The eval runs as a CommandStep in the prime-rl checkout's environment
(where verifiers lives), which sidesteps two problems at once: the
pipeline venv never needs verifiers installed, and verifiers'
signal-handler installation (which dies in ZenML's worker threads)
never runs inside a ZenML step process.

verifiers writes the same per-rollout ``traces.jsonl`` schema prime-rl
does, so the same ingest step turns the eval into the same rollout
table — one ingester, both channels.
"""

from typing import Optional

from steps.ingest_rollout_traces import ingest_rollout_traces

from zenml import pipeline
from zenml.steps import CommandStep


@pipeline(dynamic=True)
def agentic_rl_verifiers_eval(
    prime_rl_dir: str,
    eval_config: str,
    output_dir: str,
    model: Optional[str] = None,
    expected_min_rollouts: int = 1,
) -> None:
    """Run a verifiers v1 eval and ingest its traces.

    Args:
        prime_rl_dir: Path to a prime-rl checkout (verifiers lives in
            its environment as a vendored submodule).
        eval_config: verifiers eval TOML (model, [taskset] id,
            [harness]) — see `uv run eval @ config.toml` upstream docs.
        output_dir: Directory the eval writes its run outputs into;
            passed to ingest, so it must be readable by later steps.
        model: Optional model override forwarded to the eval CLI.
        expected_min_rollouts: Ingest fails below this rollout count.
    """
    command = [
        "uv",
        "run",
        "--project",
        prime_rl_dir,
        "eval",
        "@",
        eval_config,
        "--output-dir",
        output_dir,
        # Never push eval runs to the Prime Intellect platform from a
        # pipeline — egress must be a deliberate user decision.
        "--no-push",
    ]
    if model:
        command += ["--model", model]

    run_verifiers_eval = CommandStep(
        command=command, name="run_verifiers_eval"
    )
    run_verifiers_eval()

    ingest_rollout_traces(
        output_dir=output_dir,
        expected_min_rollouts=expected_min_rollouts,
        traces_glob="**/traces.jsonl",
    )
