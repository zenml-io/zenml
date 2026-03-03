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

"""Entry point for the LakeFS data versioning example.

Usage:
    # Full pipeline (generate data, validate, train):
    python run.py

    # Quick local iteration with small dataset:
    python run.py --config configs/local.yaml

    # Remote orchestrator with DockerSettings:
    python run.py --config configs/remote.yaml

    # Retrain on a previously validated data snapshot:
    python run.py --lakefs-commit <COMMIT_SHA>

    # Disable ZenML caching:
    python run.py --no-cache
"""

import argparse
import os

from pipelines import training_pipeline
from utils.lakefs_utils import setup_lakefs_repo


def main() -> None:
    """Parse CLI args, set up LakeFS repo, and run the training pipeline."""
    parser = argparse.ArgumentParser(
        description="Run the LakeFS data versioning training pipeline"
    )
    parser.add_argument(
        "--config",
        type=str,
        default=None,
        help="Path to YAML config file (e.g. configs/local.yaml, "
        "configs/remote.yaml)",
    )
    parser.add_argument(
        "--lakefs-commit",
        type=str,
        default=None,
        help="Reuse a specific LakeFS commit SHA instead of generating "
        "new data. Skips ingestion and validation.",
    )
    parser.add_argument(
        "--n-rows",
        type=int,
        default=10000,
        help="Number of synthetic sensor rows to generate (default: 10000)",
    )
    parser.add_argument(
        "--lakefs-repo",
        type=str,
        default="",
        help="LakeFS repository name (default: LAKEFS_REPO env var or "
        "'robot-data')",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable ZenML step caching",
    )
    args = parser.parse_args()

    repo = args.lakefs_repo or os.environ.get("LAKEFS_REPO", "robot-data")

    # Ensure the LakeFS repo exists before running the pipeline
    if not args.lakefs_commit:
        setup_lakefs_repo(repo)

    options = {}
    if args.config:
        options["config_path"] = args.config
    if args.no_cache:
        options["enable_cache"] = False

    pipeline_instance = training_pipeline.with_options(**options)
    pipeline_instance(
        existing_commit=args.lakefs_commit,
        n_rows=args.n_rows,
        lakefs_repo=repo,
    )


if __name__ == "__main__":
    main()
