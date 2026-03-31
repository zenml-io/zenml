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
"""Entry point for Optuna hyperparameter tuning example."""

import argparse

from pipelines.sweep import adaptive_sweep_pipeline, sweep_pipeline


def main() -> None:
    """Run the hyperparameter sweep pipeline.

    Usage:
        python run.py                                   # Simple sweep with default config
        python run.py simple                             # Explicit simple mode
        python run.py adaptive                           # Adaptive multi-round sweep
        python run.py --config config/my_config.yaml     # Custom config file
        python run.py --no-cache                         # Disable caching
        python run.py adaptive --no-cache                # Adaptive without cache
    """
    default_configs = {
        "simple": "config/simple.yaml",
        "adaptive": "config/adaptive.yaml",
    }

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
        "--config",
        default=None,
        help="Path to YAML config file (defaults to config/simple.yaml or config/adaptive.yaml)",
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable pipeline caching",
    )
    args = parser.parse_args()

    config_path = args.config or default_configs[args.mode]
    enable_cache = not args.no_cache

    if args.mode == "simple":
        print("🚀 Running simple parallel sweep pipeline")
        print(f"   Config: {config_path}")
        print(f"   Cache: {'enabled' if enable_cache else 'disabled'}\n")

        sweep_pipeline.with_options(
            config_path=config_path,
            enable_cache=enable_cache,
        )()

    elif args.mode == "adaptive":
        print("🚀 Running adaptive multi-round sweep pipeline")
        print(f"   Config: {config_path}")
        print(f"   Cache: {'enabled' if enable_cache else 'disabled'}\n")

        adaptive_sweep_pipeline.with_options(
            config_path=config_path,
            enable_cache=enable_cache,
        )()

    print("\n✅ Sweep submitted! Check the ZenML dashboard to see the DAG.")


if __name__ == "__main__":
    main()
