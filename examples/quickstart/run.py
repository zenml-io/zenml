# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
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
#

import os

import click
from pipelines import (
    english_translation_pipeline,
)

from zenml.logger import get_logger

logger = get_logger(__name__)


@click.command(
    help="""
ZenML Starter project.

Run the ZenML starter project with basic options.

Examples:

  \b
  # Run the training pipeline
    python run.py
"""
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run.",
)
@click.option(
    "--model_type",
    type=click.Choice(["t5-small", "t5-large"], case_sensitive=False),
    default="t5-small",
    help="Choose the model size: t5-small or t5-large.",
)
@click.option(
    "--config_path",
    default="configs/training_local.yaml",
    help="Choose the configuration file.",
)
def main(
    model_type: str,
    config_path: str = "configs/training_local.yaml",
    no_cache: bool = False,
):
    """Main entry point for the pipeline execution.

    This entrypoint is where everything comes together:

      * configuring pipeline with the required parameters
        (some of which may come from command line arguments, but most
        of which comes from the YAML config files)
      * launching the pipeline

    Args:
        model_type: Type of model to use
        config_path: Configuration file to use
        no_cache: If `True` cache will be disabled.
    """
    run_args_train = {}

    pipeline_args = {}
    if no_cache:
        pipeline_args["enable_cache"] = False

    print(f"Using {config_path} to configure the pipeline run.")

    pipeline_args["config_path"] = config_path
    english_translation_pipeline.with_options(**pipeline_args)(
        model_type=model_type, **run_args_train
    )


if __name__ == "__main__":
    main()
