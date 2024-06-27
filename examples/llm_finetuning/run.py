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
from typing import Optional

import click
from pipelines.train import llm_peft_full_finetune


@click.command(
    help="""
ZenML LLM Finetuning project CLI v0.2.0.

Run the ZenML LLM Finetuning project LLM PEFT finetuning pipelines.

Examples:

  \b
  # Run the pipeline
    python run.py
  
  \b
  # Run the pipeline with custom config
    python run.py --config custom_finetune.yaml
"""
)
@click.option(
    "--config",
    type=str,
    default="default_finetune.yaml",
    help="Path to the YAML config file.",
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run.",
)
def main(
    config: Optional[str] = None,
    no_cache: bool = False,
):
    """Main entry point for the pipeline execution.

    Args:
        no_cache: If `True` cache will be disabled.
    """
    config_folder = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "configs",
    )
    pipeline_args = {"enable_cache": not no_cache}
    if not config:
        raise RuntimeError("Config file is required to run a pipeline.")

    if config in os.listdir(config_folder):
        pipeline_args["config_path"] = os.path.join(config_folder, config)
    else:
        pipeline_args["config_path"] = config

    llm_peft_full_finetune.with_options(**pipeline_args)()


if __name__ == "__main__":
    main()
