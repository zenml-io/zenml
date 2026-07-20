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
"""The ZenML pipeline-writing taskset (verifiers v1).

One task = one record of the RL spike's ``tasks.jsonl``: the model
writes a ZenML pipeline, the reward runs the spike's ``score_pipeline``
verifier inside the runtime. It is byte-identical to the scorer this
example's Harbor eval campaign uses, so rewards are comparable across
the training and eval channels.

Failure forensics contract: a crashed scorer is recorded as
``infra_error`` in the trace info and surfaced as the ``infra_error``
metric — never silently conflated with a genuine 0.0 reward.
"""

import asyncio
import json
import re
import shlex
from pathlib import Path
from typing import Any, Dict, List

import verifiers.v1 as vf

from zenml_pipeline_writing import step_tracking
from zenml_pipeline_writing.runtime import (  # noqa: F401 - re-export
    ZenMLSandboxRuntime,
)

# The scorer baked into the task image (see
# examples/agentic_rl/docker/Dockerfile) — the same image the Harbor
# eval campaign pins in task.toml.
SCORER_PATH = "/opt/zenml-scorer/score_pipeline.py"

_TASKS_JSONL = Path(__file__).resolve().parent / "tasks.jsonl"

_FENCE_RE = re.compile(r"```(?:python)?\n(.*?)```", re.DOTALL)

INSTRUCTION_SUFFIX = (
    "\n\nReply with a single fenced Python code block containing the "
    "complete program. Use ZenML's @step and @pipeline(dynamic=True) "
    "decorators, include exactly one pipeline invocation under "
    'if __name__ == "__main__":, and never call .run().'
)


def strip_markdown_fences(text: str) -> str:
    """Extract program source from a fenced completion.

    Args:
        text: The raw model completion.

    Returns:
        The fenced code if present, otherwise the text unchanged.
    """
    match = _FENCE_RE.search(text)
    return match.group(1) if match else text


class PipelineWritingData(vf.TaskData):
    """One tasks.jsonl record."""

    spec_json: str
    difficulty: int


class PipelineWritingTask(vf.Task[PipelineWritingData]):
    """Write-a-ZenML-pipeline task scored inside the runtime sandbox."""

    @vf.reward
    async def sandbox_scored(
        self, trace: vf.Trace, runtime: vf.Runtime
    ) -> float:
        """Score the completion and record the reward on the rollout's step run.

        Args:
            trace: The finished rollout trace (the last reply is the
                completion).
            runtime: The runtime the rollout ran in — with the ZenML
                runtime selected this is a ZenML sandbox session.

        Returns:
            The verifier's 0-1 reward.
        """
        reward = await self._run_scorer(trace=trace, runtime=runtime)
        if (
            isinstance(runtime, ZenMLSandboxRuntime)
            and runtime.step_run_id is not None
        ):
            metadata: Dict[str, Any] = {
                "task": self.data.name,
                "reward": reward,
            }
            if infra_error := trace.info.get("infra_error"):
                metadata["infra_error"] = infra_error
            await asyncio.to_thread(
                step_tracking.log_rollout_metadata,
                step_run_id=runtime.step_run_id,
                metadata=metadata,
            )
        return reward

    async def _run_scorer(self, trace: vf.Trace, runtime: vf.Runtime) -> float:
        """Score the completion with the spike's verifier, in-sandbox.

        Args:
            trace: The finished rollout trace (the last reply is the
                completion).
            runtime: The runtime the rollout ran in — with the ZenML
                runtime selected this is a ZenML sandbox session.

        Returns:
            The verifier's 0-1 reward; 0.0 with ``infra_error`` state
            recorded when the harness (not the completion) broke.
        """
        try:
            program = strip_markdown_fences(trace.last_reply or "")
            await runtime.write("/app/pipeline.py", program.encode())
            await runtime.write("/app/spec.json", self.data.spec_json.encode())
            result = await runtime.run(
                [
                    "python",
                    SCORER_PATH,
                    "/app/pipeline.py",
                    "/app/spec.json",
                    "/app/reward.json",
                ],
                {},
            )
            if result.exit_code != 0:
                trace.info["infra_error"] = (
                    f"scorer exited {result.exit_code}: "
                    f"{(result.stderr or result.stdout)[-800:]}"
                )
                return 0.0
            reward_data = json.loads(
                (await runtime.read("/app/reward.json")).decode()
            )
        except Exception as e:
            # A reward function must never let a harness failure decay
            # into a bare 0.0 — record the root cause where the trace
            # record (and the ingest table) can see it.
            trace.info["infra_error"] = f"{type(e).__name__}: {e}"
            return 0.0
        trace.info["scorer_result"] = reward_data
        return float(reward_data.get("reward", 0.0))

    @vf.metric
    async def infra_error(self, trace: vf.Trace) -> float:
        """Whether the harness (not the model) broke this rollout.

        Args:
            trace: The finished rollout trace.

        Returns:
            1.0 when an infra error was recorded, else 0.0.
        """
        return 1.0 if trace.info.get("infra_error") else 0.0


class PipelineWritingConfig(vf.TasksetConfig):
    """Taskset configuration."""

    max_difficulty: int = 4
    """Only tasks at or below this difficulty are loaded."""


class PipelineWritingTaskset(
    vf.Taskset[PipelineWritingTask, PipelineWritingConfig]
):
    """All tasks.jsonl records as verifiers tasks."""

    def load(self) -> List[PipelineWritingTask]:
        """Load the task list.

        Returns:
            One task per tasks.jsonl record within the difficulty cap.
        """
        tasks: List[PipelineWritingTask] = []
        for index, line in enumerate(_TASKS_JSONL.read_text().splitlines()):
            if not line.strip():
                continue
            record: Dict[str, Any] = json.loads(line)
            if record["difficulty"] > self.config.max_difficulty:
                continue
            tasks.append(
                PipelineWritingTask(
                    PipelineWritingData(
                        idx=index,
                        name=record["id"],
                        prompt=record["prompt"] + INSTRUCTION_SUFFIX,
                        spec_json=json.dumps(record["spec"]),
                        difficulty=record["difficulty"],
                    ),
                    self.config.task,
                )
            )
        return tasks
