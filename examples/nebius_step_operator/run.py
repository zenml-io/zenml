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
"""CPU preparation, one Nebius GPU step, and CPU artifact consumption."""

from zenml import pipeline, step
from zenml.config import DockerSettings
from zenml.config.docker_settings import DockerBuildConfig
from zenml.integrations.nebius.flavors import NebiusStepOperatorSettings


@step
def prepare() -> list[list[float]]:
    """Prepare a small input artifact.

    Returns:
        Two rows to score.
    """
    return [[1.0, 2.0], [3.0, 4.0]]


@step(
    step_operator="nebius-gpu",
    settings={
        "step_operator": NebiusStepOperatorSettings(
            platform="gpu-l40s-a",
            preset="1gpu-8vcpu-32gb",
            timeout_seconds=3600,
        ),
        "docker": DockerSettings(
            dockerfile="Dockerfile",
            environment={"UV_SYSTEM_PYTHON": "1"},
            build_context_root=".",
            parent_image_build_config=DockerBuildConfig(
                dockerignore=".dockerignore",
                build_options={"platform": "linux/amd64"},
            ),
            build_config=DockerBuildConfig(
                build_options={"platform": "linux/amd64"},
            ),
        ),
    },
)
def score_on_gpu(rows: list[list[float]]) -> list[float]:
    """Load the input artifact and compute on the Job's GPU.

    Args:
        rows: Input rows loaded by ZenML's materializer.

    Returns:
        The sum of squares of each row.
    """
    import torch

    tensor = torch.tensor(rows, device="cuda")
    return tensor.square().sum(dim=1).cpu().tolist()


@step
def summarize(scores: list[float]) -> None:
    """Consume the remote step's output artifact locally.

    Args:
        scores: Scores loaded from the remote artifact store.

    Raises:
        ValueError: If the GPU result differs from the expected result.
    """
    if scores != [5.0, 25.0]:
        raise ValueError(f"Unexpected scores: {scores}")
    print(scores)


@pipeline
def scoring_pipeline() -> None:
    """Run the CPU → GPU → CPU artifact round-trip."""
    summarize(score_on_gpu(prepare()))


if __name__ == "__main__":
    scoring_pipeline()
