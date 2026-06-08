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

A planner LLM decomposes the user's goal into ``N`` independent
subtasks. Each subtask runs in its own ZenML step via ``step.map()``,
which gives each subagent a fresh ``SandboxSession`` (isolated /tmp,
own log source, own step metadata, independently cacheable). A reducer
LLM stitches the subagent outputs into a single coherent answer.
"""

import site
import sys
from pathlib import Path
from typing import Annotated, Any

from agent import (
    _DEFAULT_QUERY,
    plan_subtasks,
    run_agent_in_session,
    synthesize,
)

import zenml
from zenml import pipeline, step, unmapped
from zenml.client import Client
from zenml.config import DockerSettings
from zenml.integrations.modal.flavors import ModalSandboxSettings
from zenml.sandboxes import SandboxSnapshot


def get_docker_settings(
    skip_parent_build: bool = False, **kwargs: Any
) -> DockerSettings:
    """Build DockerSettings that work with an editable ZenML install.

    Args:
        skip_parent_build: If True, never add the parent build even when
            ZenML appears to be an editable install.
        **kwargs: Extra DockerSettings fields to merge in.

    Returns:
        A DockerSettings configured for this example.
    """
    settings_kwargs: dict = {
        "build_config": {
            "build_options": {
                "platform": "linux/amd64",
            }
        },
        "python_package_installer": "uv",
    }

    if not skip_parent_build:
        for path in site.getsitepackages() + [site.getusersitepackages()]:
            if Path(path).resolve() in Path(zenml.__file__).resolve().parents:
                break
        else:
            zenml_git_root = Path(zenml.__file__).parents[2]
            settings_kwargs.update(
                {
                    "dockerfile": str(
                        zenml_git_root / "docker" / "zenml-dev.Dockerfile"
                    ),
                    "build_context_root": str(zenml_git_root),
                    "parent_image_build_config": {
                        "build_options": {
                            "platform": "linux/amd64",
                            "buildargs": {
                                "PYTHON_VERSION": (
                                    f"{sys.version_info.major}."
                                    f"{sys.version_info.minor}"
                                )
                            },
                        }
                    },
                    "prevent_build_reuse": True,
                }
            )

    settings_kwargs.update(kwargs)
    settings_kwargs.setdefault("allow_download_from_artifact_store", False)
    settings_kwargs.setdefault("allow_download_from_code_repository", False)

    return DockerSettings(**settings_kwargs)


# Per-step sandbox settings. Lift Modal's 5-minute timeout so a slow
# OpenAI tool-use loop doesn't terminate the sandbox mid-exec. Sandbox
# stdout/stderr automatically lands in a per-session ``sandbox:<id>``
# log source on the active step -- no opt-in needed.
_AGENT_SANDBOX_SETTINGS = ModalSandboxSettings(timeout_seconds=900)


_PYTHON_DEPS = "numpy scipy"


@step(settings={"sandbox": _AGENT_SANDBOX_SETTINGS})
def prep_step() -> Annotated[SandboxSnapshot, "scientific_image"]:
    """Boot a sandbox, install scientific deps, return a snapshot.

    Returns:
        The sandbox snapshot with the scientific stack pre-installed.
    """
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError("No Sandbox component in the active stack.")

    with sandbox.create_session() as session:
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


@step
def planner_step(query: str) -> Annotated[list[str], "subtasks"]:
    """Asks a planner LLM to decompose the user goal into N subtasks.

    Args:
        query: The user's natural-language goal.

    Returns:
        Self-contained subtask descriptions, one per intended subagent.
    """
    return plan_subtasks(query)


@step(settings={"sandbox": _AGENT_SANDBOX_SETTINGS})
def subagent_step(
    snapshot: SandboxSnapshot, subtask: str
) -> Annotated[str, "subagent_answer"]:
    """Restore from the shared snapshot and run the agent on one subtask.

    Args:
        snapshot: Shared snapshot with scientific deps pre-installed.
        subtask: The subtask description for this subagent.

    Returns:
        The subagent's final natural-language answer.
    """
    sandbox = Client().active_stack.sandbox
    if sandbox is None:
        raise RuntimeError("No Sandbox component in the active stack.")
    with sandbox.restore(snapshot) as session:
        return run_agent_in_session(session, subtask)


@step
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


@pipeline(
    dynamic=True,
    enable_cache=False,
    settings={
        "docker": get_docker_settings(requirements="requirements.txt"),
    },
)
def sandbox_pydantic_ai_pipeline(query: str = _DEFAULT_QUERY) -> str:
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
