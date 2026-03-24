#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""CLI entrypoint for the ZenML + KAI-Scheduler GPU demo."""

import os

import click

from zenml.logger import get_logger

logger = get_logger(__name__)

_CONFIGS_DIR = os.path.join(os.path.dirname(__file__), "configs")

_CONFIG_CHOICES = [
    "kai_demo.yaml",
    "kai_demo_preemption.yaml",
    "kai_demo_gpu_sharing.yaml",
    "kai_demo_local.yaml",
]


@click.command(
    help=(
        "Run the ZenML + KAI-Scheduler GPU benchmark pipeline.\n\n"
        "The pipeline runs two steps:\n"
        "  1. cuda_matrix_benchmark — CUDA matmul GFLOPS benchmark\n"
        "  2. pytorch_cnn_train     — minimal CNN training on synthetic data\n\n"
        "Configs in the 'configs/' directory control which scheduler, queue,\n"
        "GPU settings, and resource requests are used."
    )
)
@click.option(
    "--config",
    "-c",
    type=click.Choice(_CONFIG_CHOICES),
    default="kai_demo.yaml",
    show_default=True,
    help="YAML config file to use (from the configs/ directory).",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching and force all steps to re-run.",
)
def main(config: str, no_cache: bool) -> None:
    """Run the KAI-Scheduler GPU benchmark pipeline.

    Args:
        config: Config filename (relative to configs/).
        no_cache: When True, disables step caching.
    """
    from pipelines.gpu_benchmark import kai_gpu_benchmark_pipeline

    config_path = os.path.join(_CONFIGS_DIR, config)
    if not os.path.exists(config_path):
        raise click.ClickException(
            f"Config file not found: {config_path}. "
            f"Available configs: {', '.join(_CONFIG_CHOICES)}"
        )

    logger.info("Running pipeline with config: %s", config_path)
    logger.info("Caching: %s", "disabled" if no_cache else "enabled")

    kai_gpu_benchmark_pipeline.with_options(
        config_path=config_path,
        enable_cache=not no_cache,
    )()


if __name__ == "__main__":
    main()
