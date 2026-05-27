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
"""ZenML pipeline driving the PydanticAI + Sandbox agent.

Reads the active stack's Sandbox component, lets the PydanticAI agent
loop with a ``run_python`` tool that executes its generated code in the
sandbox, and returns the natural-language answer.
"""

import site
import sys
from pathlib import Path
from typing import Annotated, Any

import zenml
from agent import run_agent

from zenml import pipeline, step
from zenml.config import DockerSettings


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
    containerize) — the settings are simply ignored.

    Args:
        skip_parent_build: If True, never add the parent build even when
            ZenML appears to be an editable install. Useful when the
            target environment has its own preferred image.
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
                # ZenML is installed from a wheel; nothing to do.
                break
        else:
            # Editable install — add a parent build so the image carries
            # the current ZenML source rather than the published wheel.
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


@step
def agent_step(query: str) -> Annotated[str, "agent_answer"]:
    """Runs the PydanticAI agent against the active stack's Sandbox.

    Args:
        query: The natural-language question.

    Returns:
        The agent's answer.
    """
    return run_agent(query)


@pipeline(
    enable_cache=False,
    settings={
        "docker": get_docker_settings(
            requirements="requirements.txt",
        )
    },
)
def sandbox_pydantic_ai_pipeline(
    query: str = (
        "What's the sum of the first 100 prime numbers? "
        "Write Python to compute it."
    ),
) -> str:
    """Single-step pipeline that drives the PydanticAI agent."""
    return agent_step(query=query)


if __name__ == "__main__":
    print("Running PydanticAI + Sandbox pipeline...")
    sandbox_pydantic_ai_pipeline()
    print("Done. Check the ZenML dashboard for the run + log stream.")
