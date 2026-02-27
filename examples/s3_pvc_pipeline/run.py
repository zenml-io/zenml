#!/usr/bin/env python3
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
"""Entry point for the training pipeline."""

import argparse
from pathlib import Path

import yaml
from pipelines.training import train_pipeline

THIS_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = THIS_DIR / "config" / "config.yaml"


def _get_pipeline_run_name(config_fpath: str | Path) -> str:
    config_fpath = Path(config_fpath)
    if not config_fpath.exists():
        raise FileNotFoundError(f"Config file not found: {config_fpath}")

    with open(config_fpath, "r") as f:
        try:
            config = yaml.safe_load(f)
            data_version = config["parameters"]["data_version"]
            run_name = f"training_{data_version}_{{date}}_{{time}}"
            return run_name
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing YAML file: {e}")


def main() -> None:
    """Run the training pipeline.

    Requires S3 service connector for the load_data step.
    Set S3_SERVICE_CONNECTOR to your ZenML service connector name or ID
    (e.g. export S3_SERVICE_CONNECTOR=aws-s3-connector).

    Configuration is applied in this order (highest precedence first):
    1. Command-line / code overrides (e.g. parameters passed here)
    2. YAML config file (--config)
    3. Pipeline and step defaults in code
    """
    parser = argparse.ArgumentParser(
        description="Run FashionMNIST training pipeline"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=DEFAULT_CONFIG_PATH.as_posix(),
        help="Path to YAML run configuration",
    )
    args = parser.parse_args()

    config_fpath = Path(args.config)
    if not config_fpath.exists():
        raise FileNotFoundError(f"Config file not found: {config_fpath}")

    print("Running FashionMNIST training pipeline\n")

    train_pipeline.with_options(
        run_name=_get_pipeline_run_name(config_fpath),
        config_path=config_fpath.resolve().as_posix(),
    )()

    print("\nPipeline run complete.")


if __name__ == "__main__":
    main()
