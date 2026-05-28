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

from agent import _DEFAULT_QUERY, plan_subtasks, run_agent, synthesize

import zenml
from zenml import pipeline, step
from zenml.config import DockerSettings
from zenml.sandboxes import BaseSandboxSettings


def get_docker_settings(
    skip_parent_build: bool = False, **kwargs: Any
) -> DockerSettings:
    """Builds ``DockerSettings`` that work with an editable ZenML install.

    When this example runs against a containerized orchestrator (e.g. the
    Kubernetes stack), the step image needs to include the current ZenML
    source. If ZenML is installed editable from a git checkout (the dev
    workflow), we bake a parent build that copies the editable tree into
    the image. Otherwise we use the published wheel and just install the
    example's requirements on top.

    Harmless when running on the ``default`` orchestrator (which doesn't
    containerize) -- the settings are simply ignored.

    Args:
        skip_parent_build: If True, never add the parent build even when
            ZenML appears to be an editable install.
        **kwargs: Extra ``DockerSettings`` fields to merge in.

    Returns:
        A ``DockerSettings`` configured for this example.
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
# OpenAI tool-use loop doesn't terminate the sandbox mid-exec, and opt
# into log forwarding so each subagent's stdout surfaces as a
# ``sandbox:<id>`` source in its own step's log stream.
_AGENT_SANDBOX_SETTINGS = BaseSandboxSettings(
    forward_logs_to_step=True,
    timeout_seconds=900,
)


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
def subagent_step(subtask: str) -> Annotated[str, "subagent_answer"]:
    """Runs one subagent in a fresh Sandbox session.

    Each fanned-out instance gets its own ZenML step run -- its own
    artifact, its own ``sandbox:<id>`` log source, and its own
    ``sandbox.<id>.*`` step metadata entries. Isolation is automatic
    because ``run_agent`` calls ``sandbox.create_session()``.

    Args:
        subtask: The subtask description produced by the planner.

    Returns:
        The subagent's final natural-language answer.
    """
    return run_agent(subtask)


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
    """Planner -> fan-out subagents -> reducer.

    Each subagent step holds its own Sandbox session and its own agent
    loop; the same ``run_agent`` function runs in every fanned-out
    instance unchanged.

    Args:
        query: The natural-language goal for the agent.

    Returns:
        The reducer's final synthesized answer.
    """
    subtasks = planner_step(query=query)
    parts = subagent_step.map(subtask=subtasks)
    return reducer_step(query=query, parts=parts)


if __name__ == "__main__":
    print("Running PydanticAI + Sandbox fan-out pipeline...")
    sandbox_pydantic_ai_pipeline()
    print("Done. Check the ZenML dashboard for the run + log stream.")
