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
"""Entry point demonstrating Hydra + ZenML integration.

This script shows how to use Hydra for configuration management
while leveraging ZenML for orchestration. The pattern is:

- Hydra decides WHAT: search space, model architecture, data paths
- ZenML decides WHERE/WHEN: orchestration, GPU scheduling, caching

Usage:
    python run_hydra.py                                              # Use defaults from conf/config.yaml (simple mode)
    python run_hydra.py sweep.mode=adaptive                          # Run adaptive mode
    python run_hydra.py sweep.n_trials=10                            # Override trial count (simple mode)
    python run_hydra.py sweep.mode=adaptive sweep.n_rounds=5         # Adaptive with 5 rounds
    python run_hydra.py search_space.learning_rate.high=0.5           # Override search space
    python run_hydra.py sweep.max_iter=50 sweep.n_trials=20          # Multiple overrides

Requirements:
    pip install hydra-core omegaconf
"""

import sys

try:
    from hydra import compose, initialize
    from omegaconf import DictConfig, OmegaConf
except ImportError:
    print(
        "❌ Hydra not installed. Install with: pip install hydra-core omegaconf"
    )
    print("   Or uncomment the Hydra section in requirements.txt")
    sys.exit(1)

from typing import Any, Dict

from pipelines.sweep import adaptive_sweep_pipeline, sweep_pipeline


def hydra_config_to_dict(cfg: DictConfig) -> Dict[str, Any]:
    """Convert Hydra DictConfig to plain Python dict.

    Args:
        cfg: Hydra configuration object

    Returns:
        Plain Python dictionary with resolved values
    """
    return OmegaConf.to_container(cfg, resolve=True)  # type: ignore[return-value]


def main() -> None:
    """Run sweep pipeline with Hydra configuration.

    Hydra resolves all configuration from conf/config.yaml and CLI overrides,
    then passes it to the ZenML pipeline for orchestration.
    """
    # Initialize Hydra and load configuration with CLI overrides
    with initialize(config_path="conf", version_base=None):
        cfg = compose(config_name="config", overrides=sys.argv[1:])

    # Convert to plain dict for ZenML
    config = hydra_config_to_dict(cfg)

    print("🔧 Hydra Configuration Resolved:")
    print("=" * 80)
    print(OmegaConf.to_yaml(cfg))
    print("=" * 80)

    # Extract sweep parameters
    sweep_config = config["sweep"]
    search_space = config.get("search_space")
    zenml_config = config.get("zenml_config", {})
    mode = sweep_config.get("mode", "simple")  # Default to simple mode
    enable_cache = zenml_config.get("enable_cache", True)
    settings = zenml_config.get("settings", {})

    print("\n🚀 Running sweep pipeline with Hydra config")
    print(f"   Study: {sweep_config['study_name']}")
    print("   Framework: PyTorch Lightning")
    print(f"   Mode: {mode}")
    print(f"   Cache: {'enabled' if enable_cache else 'disabled'}")

    # Run ZenML pipeline with Hydra-resolved config
    # Hydra decides WHAT (search space, parameters)
    # ZenML decides WHERE/WHEN (orchestration, resources)
    if mode == "simple":
        print(f"   Trials: {sweep_config['n_trials']}")
        print(f"   Max iterations: {sweep_config['max_iter']}\n")

        sweep_pipeline.with_options(enable_cache=enable_cache, settings=settings)(
            study_name=sweep_config["study_name"],
            n_trials=sweep_config["n_trials"],
            max_iter=sweep_config["max_iter"],
            search_space=search_space,
        )

    elif mode == "adaptive":
        print(f"   Rounds: {sweep_config.get('n_rounds', 3)}")
        print(
            f"   Trials per round: {sweep_config.get('trials_per_round', 3)}"
        )
        print(f"   Max iterations: {sweep_config['max_iter']}\n")

        adaptive_sweep_pipeline.with_options(enable_cache=enable_cache, settings=settings)(
            study_name=sweep_config["study_name"],
            n_rounds=sweep_config.get("n_rounds", 3),
            trials_per_round=sweep_config.get("trials_per_round", 3),
            max_iter=sweep_config["max_iter"],
            search_space=search_space,
        )

    else:
        print(f"❌ Unknown mode: {mode}")
        print("   Valid modes: simple, adaptive")
        sys.exit(1)

    print("\n✅ Sweep complete!")
    print("   Configuration was managed by Hydra")
    print("   Orchestration was handled by ZenML")


if __name__ == "__main__":
    main()
