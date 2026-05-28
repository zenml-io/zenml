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
"""Step: build the evaluation matrix from a YAML config file."""

import logging
from pathlib import Path
from typing import List

import yaml

from models.harbor_models import HarborRunSpec

from zenml import step

logger = logging.getLogger(__name__)


def _resolve_config_path(config_path: str) -> Path:
    """Try multiple locations for the config file.

    On local orchestrators the path is relative to cwd. On Kubernetes
    the code is mounted at /app/ or /app/code/.
    """
    candidates = [
        Path(config_path),
        Path(__file__).parent.parent / config_path,
        Path("/app") / config_path,
        Path("/app/code") / config_path,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Config file not found. Tried: {[str(c) for c in candidates]}"
    )


@step
def build_matrix(config_path: str) -> List[HarborRunSpec]:
    """Read a campaign YAML config and build the agent x model matrix.

    Oracle agents (no LLM needed) get model=None and skip the models
    list entirely. Non-oracle agents get one spec per model in the list.

    Args:
        config_path: Path to the campaign YAML config file.

    Returns:
        List of HarborRunSpec, one per (agent, model) combination.
    """
    resolved = _resolve_config_path(config_path)
    logger.info("Loading campaign config from %s", resolved)

    with open(resolved, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    campaign = raw.get("campaign", raw)
    agents: List[str] = campaign.get("agents", [])
    models: List[str] = campaign.get("models", [])
    dataset_path: str = campaign.get("dataset_path", "")
    dataset_ref = campaign.get("dataset_ref")
    env_provider = campaign.get("env_provider")
    n_concurrent = campaign.get("n_concurrent")
    extra_args: List[str] = campaign.get("extra_args", [])

    specs: List[HarborRunSpec] = []

    for agent in agents:
        if agent == "oracle" or not models:
            specs.append(
                HarborRunSpec(
                    agent=agent,
                    model=None,
                    dataset_path=dataset_path,
                    dataset_ref=dataset_ref,
                    env_provider=env_provider,
                    n_concurrent=n_concurrent,
                    extra_args=extra_args,
                    label=agent,
                )
            )
        else:
            for model in models:
                specs.append(
                    HarborRunSpec(
                        agent=agent,
                        model=model,
                        dataset_path=dataset_path,
                        dataset_ref=dataset_ref,
                        env_provider=env_provider,
                        n_concurrent=n_concurrent,
                        extra_args=extra_args,
                        label=f"{agent}/{model}",
                    )
                )

    logger.info("Built evaluation matrix with %d specs: %s",
                len(specs), [s.label for s in specs])
    return specs
