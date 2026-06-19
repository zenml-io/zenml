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

"""Run the Baseten robot policy example.

Examples:
    # Run everything locally (no Baseten, no GPU) for a quick smoke test:
    python run.py --local

    # Run the training step on Baseten H100 (requires a stack with the
    # baseten step operator + a remote artifact store and container registry):
    python run.py --step-operator baseten_operator
"""

import site
import sys
from pathlib import Path
from typing import Any, Optional

import click
from pipelines import robot_policy_pipeline

import zenml
from zenml import Model
from zenml.config import DockerSettings, ResourceSettings
from zenml.integrations.baseten.flavors import BasetenStepOperatorSettings


def _get_docker_settings(**kwargs: Any) -> DockerSettings:
    """Build DockerSettings that bake the *current* zenml into the image.

    NOTE: Temporary. While the Baseten step operator lives on a development
    branch (not yet a released zenml), the image Baseten runs must contain that
    exact branch checkout rather than a PyPI release. When running from an
    editable/dev install this points the build at ``zenml-dev.Dockerfile`` so
    the local source is copied in. Once the operator ships in a released zenml
    this whole helper can be dropped in favor of a plain ``DockerSettings``.
    """
    settings_kwargs: dict = {
        "build_config": {"build_options": {"platform": "linux/amd64"}},
        "python_package_installer": "uv",
    }

    for path in site.getsitepackages() + [site.getusersitepackages()]:
        if Path(path).resolve() in Path(zenml.__file__).resolve().parents:
            break  # regular (non-editable) install: nothing special to do
    else:
        # Editable install: copy the local zenml checkout into the image.
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
                            "PYTHON_VERSION": f"{sys.version_info.major}.{sys.version_info.minor}"
                        },
                    }
                },
                "prevent_build_reuse": True,
            }
        )

    settings_kwargs.update(kwargs)
    return DockerSettings(**settings_kwargs)


@click.command()
@click.option(
    "--step-operator",
    default=None,
    help="Name of the Baseten step operator to run the training step on. "
    "Omit (or use --local) to run the step in the orchestrator environment.",
)
@click.option(
    "--local",
    is_flag=True,
    default=False,
    help="Force fully local execution (ignores --step-operator).",
)
@click.option("--epochs", default=50, help="Training epochs.")
@click.option(
    "--accelerator", default="H100", help="Baseten accelerator type."
)
def main(
    step_operator: Optional[str], local: bool, epochs: int, accelerator: str
) -> None:
    """Configure and launch the robot policy pipeline."""
    model = Model(
        name="reaching_policy",
        description="Behavior-cloning policy for a 2D reaching task.",
        tags=["robotics", "behavior-cloning", "baseten"],
    )

    train_step_settings: dict = {}
    if step_operator and not local:
        # Run only the training step on Baseten; request a single H100 GPU.
        train_step_settings = {
            "step_operator": step_operator,
            "settings": {
                "step_operator": BasetenStepOperatorSettings(
                    accelerator=accelerator,
                    enable_cache=True,  # reuse downloaded weights across runs
                ),
                "resources": ResourceSettings(gpu_count=1),
                "docker": _get_docker_settings(
                    requirements=["torch", "numpy", "pandas"],
                ),
            },
        }

    pipeline = robot_policy_pipeline.with_options(
        model=model,
        steps={"train_policy": train_step_settings}
        if train_step_settings
        else {},
    )
    pipeline(epochs=epochs)


if __name__ == "__main__":
    main()
