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

- Hydra decides WHAT: hyperparameters, model config, data settings
- ZenML decides WHERE/WHEN: orchestration, caching, artifact tracking

Usage:
    python run.py                                          # Use defaults from conf/config.yaml
    python run.py training.learning_rate=0.005             # Override learning rate
    python run.py training.max_epochs=50                   # Override epochs
    python run.py training.hidden_dim=64 training.batch_size=128  # Multiple overrides
    python run.py zenml_config.enable_cache=false          # Disable caching

Requirements:
    pip install -r requirements.txt
"""

import sys

try:
    from hydra import compose, initialize
    from omegaconf import DictConfig, OmegaConf
except ImportError:
    print(
        "Hydra not installed. Install with: pip install hydra-core omegaconf"
    )
    print("   Or run: pip install -r requirements.txt")
    sys.exit(1)

from typing import Any, Dict

from pipelines.training import hydra_training_pipeline


def hydra_config_to_dict(cfg: DictConfig) -> Dict[str, Any]:
    """Convert Hydra DictConfig to plain Python dict.

    Args:
        cfg: Hydra configuration object

    Returns:
        Plain Python dictionary with resolved values
    """
    return OmegaConf.to_container(cfg, resolve=True)  # type: ignore[return-value]


def main() -> None:
    """Run the training pipeline with Hydra configuration.

    Hydra resolves all configuration from conf/config.yaml and CLI overrides,
    then passes it to the ZenML pipeline for orchestration.
    """
    with initialize(config_path="conf", version_base=None):
        cfg = compose(config_name="config", overrides=sys.argv[1:])

    config = hydra_config_to_dict(cfg)

    print("Hydra Configuration Resolved:")
    print("=" * 80)
    print(OmegaConf.to_yaml(cfg))
    print("=" * 80)

    training_config = config["training"]
    zenml_config = config.get("zenml_config", {})
    enable_cache = zenml_config.get("enable_cache", True)
    settings = zenml_config.get("settings", {})

    print("\nRunning training pipeline with Hydra config")
    print("   Framework: PyTorch Lightning")
    print(f"   learning_rate: {training_config['learning_rate']}")
    print(f"   batch_size: {training_config['batch_size']}")
    print(f"   hidden_dim: {training_config['hidden_dim']}")
    print(f"   max_epochs: {training_config['max_epochs']}")
    print(f"   Cache: {'enabled' if enable_cache else 'disabled'}\n")

    hydra_training_pipeline.with_options(
        enable_cache=enable_cache,
        settings=settings,
    )(
        learning_rate=training_config["learning_rate"],
        batch_size=training_config["batch_size"],
        hidden_dim=training_config["hidden_dim"],
        max_epochs=training_config["max_epochs"],
    )

    print("\nPipeline complete!")
    print("   Configuration was managed by Hydra")
    print("   Orchestration was handled by ZenML")


if __name__ == "__main__":
    main()
