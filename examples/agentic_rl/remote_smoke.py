"""Temporary driver: run the smoke tier on the kubernetes_aws stack."""

import sys
from pathlib import Path

EXAMPLE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EXAMPLE_DIR))

from pipelines.eval_pipeline import agentic_rl_eval  # noqa: E402

from zenml.config import DockerSettings  # noqa: E402
from zenml.config.docker_settings import DockerBuildConfig  # noqa: E402

ECR = "339712793861.dkr.ecr.eu-central-1.amazonaws.com"

docker_settings = DockerSettings(
    parent_image=f"{ECR}/zenml-agentic-rl-base:latest",
    target_repository="zenml-agentic-rl-pipeline",
    requirements=[
        "litellm==1.91.3",
        "harbor>=0.18,<0.19",
        "click>=8.0",
        "pandas>=2.0",
    ],
    build_config=DockerBuildConfig(
        build_options={"platform": "linux/amd64"}
    ),
)

agentic_rl_eval.with_options(settings={"docker": docker_settings})(
    tasks=[
        "tasks/const_seven",
        "tasks/const_greeting",
        "tasks/two_step_double",
    ],
    agents=[{"name": "oracle"}, {"name": "nop"}],
    trials_per_cell=1,
    min_mean_reward=0.05,
    max_mean_reward=0.98,
)
