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
"""Entry point for Optuna hyperparameter sweep examples."""

import argparse

from pipelines.sweep import adaptive_sweep_pipeline, sweep_pipeline

STUDY_NAME = "fashion_mnist_sweep"


def main() -> None:
    """Run the hyperparameter sweep pipeline.

    Usage:
        python run.py                          # Simple parallel sweep (default)
        python run.py simple                   # Explicit simple mode
        python run.py adaptive                 # Adaptive multi-round sweep
        python run.py --no-cache               # Disable caching
        python run.py adaptive --no-cache      # Adaptive without cache
    """
    parser = argparse.ArgumentParser(
        description="Run Optuna hyperparameter sweep with ZenML"
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="simple",
        choices=["simple", "adaptive"],
        help="Sweep mode (default: simple)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable pipeline caching",
    )
    args = parser.parse_args()

    enable_cache = not args.no_cache

    if args.mode == "simple":
        print("🚀 Running simple parallel sweep pipeline")
        print(f"   Study: {STUDY_NAME}")
        print("   Framework: PyTorch Lightning")
        print("   Mode: All trials in parallel")
        print(f"   Cache: {'enabled' if enable_cache else 'disabled'}\n")

        sweep_pipeline.with_options(enable_cache=enable_cache, config_path="conf/config_zenml.yaml")(
            study_name=STUDY_NAME,
            n_trials=5,
            max_iter=10,
        )

    elif args.mode == "adaptive":
        print("🚀 Running adaptive multi-round sweep pipeline")
        print(f"   Study: {STUDY_NAME}")
        print("   Framework: PyTorch Lightning")
        print("   Mode: Batched rounds with adaptive sampling")
        print(f"   Cache: {'enabled' if enable_cache else 'disabled'}\n")

        adaptive_sweep_pipeline.with_options(enable_cache=enable_cache)(
            study_name=STUDY_NAME,
            n_rounds=3,
            trials_per_round=2,
            max_iter=10,
        )

    print("\n✅ Sweep submitted! Check the ZenML dashboard to see the DAG.")


if __name__ == "__main__":
    main()
