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
"""ZenML pipeline: plan -> fan-out subagents -> reduce.

A planner LLM decomposes the user's goal into three independent
subtasks. Each subtask runs in its own ZenML step via ``step.map()``,
which gives each subagent a fresh ``SandboxSession`` (isolated /tmp,
own log source, own step metadata, independently cacheable). A reducer
LLM stitches the subagent outputs into a single coherent answer.
"""

from typing import Annotated, Optional

from agent import (
    DEFAULT_QUERY,
    plan_subtasks,
    run_agent_in_session,
    synthesize,
)

from zenml import pipeline, step, unmapped
from zenml.client import Client
from zenml.config import DockerSettings
from zenml.logger import get_logger
from zenml.sandboxes import BaseSandbox, SandboxSnapshot

logger = get_logger(__name__)

_PYTHON_DEPS = "numpy scipy"


def _active_sandbox() -> BaseSandbox:
    """Fetches the Sandbox component from the active stack.

    Returns:
        The active stack's sandbox component.

    Raises:
        RuntimeError: If the active stack has no sandbox component.
    """
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError("No Sandbox component in the active stack.")
    return sandbox


@step
def prep_step() -> Annotated[Optional[SandboxSnapshot], "scientific_snapshot"]:
    """Install scientific deps once and snapshot, where the flavor allows.

    Snapshots are an optional sandbox capability (Modal implements them
    today). On flavors without them, this step probes cheaply — before
    paying for the dependency install — and returns ``None``, in which
    case each subagent installs its own deps in a fresh session.

    Returns:
        The snapshot with the scientific stack pre-installed, or ``None``
        if the active flavor does not support snapshots.

    Raises:
        RuntimeError: If the install fails.
    """
    # Plain try/finally, no context manager: a failed destroy() keeps the
    # handle open for retry, but __exit__ would close it anyway.
    session = _active_sandbox().create_session()
    try:
        try:
            # Capability probe on the still-empty session, so a flavor
            # without snapshots doesn't pay for the install below.
            session.create_snapshot()
        except NotImplementedError:
            logger.warning(
                "The active sandbox flavor does not support snapshots; "
                "each subagent will install its dependencies in a fresh "
                "session instead."
            )
            return None
        out = session.exec(
            [
                "bash",
                "-lc",
                f"pip install --quiet --no-cache-dir {_PYTHON_DEPS}",
            ]
        ).collect()
        if out.exit_code != 0:
            raise RuntimeError(
                f"Failed to install deps (exit {out.exit_code}): {out.stderr}"
            )
        return session.create_snapshot()
    finally:
        session.destroy()


@step(enable_cache=False)
def planner_step(query: str) -> Annotated[list[str], "subtasks"]:
    """Asks a planner LLM to decompose the user goal into N subtasks.

    Args:
        query: The user's natural-language goal.

    Returns:
        Self-contained subtask descriptions, one per intended subagent.
    """
    return plan_subtasks(query)


@step(enable_cache=False)
def subagent_step(
    snapshot: Optional[SandboxSnapshot], subtask: str
) -> Annotated[str, "subagent_answer"]:
    """Run the agent on one subtask in its own sandbox session.

    Restores the shared snapshot where available; otherwise boots a
    fresh session and installs the scientific deps first.

    Args:
        snapshot: Shared snapshot with scientific deps pre-installed,
            or ``None`` on flavors without snapshot support.
        subtask: The subtask description for this subagent.

    Returns:
        The subagent's final natural-language answer.

    Raises:
        RuntimeError: If the fallback dependency install fails.
    """
    sandbox = _active_sandbox()
    if snapshot is None:
        session = sandbox.create_session()
    else:
        session = sandbox.restore(snapshot)
    try:
        if snapshot is None:
            out = session.exec(
                [
                    "bash",
                    "-lc",
                    f"pip install --quiet --no-cache-dir {_PYTHON_DEPS}",
                ]
            ).collect()
            if out.exit_code != 0:
                raise RuntimeError(
                    f"Failed to install deps (exit {out.exit_code}): "
                    f"{out.stderr}"
                )
        return run_agent_in_session(session, subtask)
    finally:
        session.destroy()


@step(enable_cache=False)
def reducer_step(
    query: str, parts: list[str]
) -> Annotated[str, "final_answer"]:
    """Synthesizes per-subagent answers into a single response.

    Args:
        query: The original user goal.
        parts: Per-subagent answers, gathered from the fan-out.

    Returns:
        A single coherent final answer.
    """
    return synthesize(query, parts)


# LLM-dependent steps disable caching individually so the expensive
# prep_step snapshot can still be reused across runs via the cache.
@pipeline(
    dynamic=True,
    settings={
        "docker": DockerSettings(
            python_package_installer="uv",
            requirements="requirements.txt",
        ),
    },
)
def sandbox_pydantic_ai_pipeline(query: str = DEFAULT_QUERY) -> str:
    """Prep -> plan -> fan-out subagents -> reduce.

    Args:
        query: The natural-language goal for the agent.

    Returns:
        The reducer's final synthesized answer.
    """
    snapshot = prep_step()
    subtasks = planner_step(query=query)
    parts = subagent_step.map(snapshot=unmapped(snapshot), subtask=subtasks)
    return reducer_step(query=query, parts=parts)


if __name__ == "__main__":
    print("Running PydanticAI + Sandbox fan-out pipeline...")
    sandbox_pydantic_ai_pipeline()
    print("Done. Check the ZenML dashboard for the run + log stream.")
