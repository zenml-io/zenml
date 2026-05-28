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
"""Harbor Eval Campaign — CLI entry point.

Launches the Harbor evaluation campaign pipeline with a given config. Every
trial runs on the Sandbox component of your active stack: each matrix cell
runs Harbor programmatically through the ZenMLSandboxEnvironment bridge, so
results land as ZenML artifacts with full lineage and the dashboard view.
"""

import argparse
import os
from typing import Any, Dict, Optional, Sequence

from pipelines.harbor_eval_campaign import harbor_eval_campaign


def _collect_runtime_env_vars() -> Dict[str, str]:
    """Collect API keys from the local environment to forward to remote pods.

    Forwarding OPENAI/ANTHROPIC keys lets non-oracle agents reach their LLM
    providers from inside the Sandbox. The oracle agent needs none.

    Returns:
        Dict of env var name → value for keys that are set locally.
    """
    env_vars: Dict[str, str] = {}
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY"):
        val = os.environ.get(key)
        if val:
            env_vars[key] = val
    return env_vars


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Run the Harbor evaluation campaign pipeline.

    Args:
        argv: Command-line arguments. If None, uses sys.argv.
    """
    parser = argparse.ArgumentParser(
        description="Run Harbor agent evaluations across an agent x model matrix"
    )
    parser.add_argument(
        "--config",
        "-c",
        default="configs/dev.yaml",
        help="Path to campaign YAML config file (default: configs/dev.yaml)",
    )
    parser.add_argument(
        "--forward-env",
        action="store_true",
        help="Forward local API keys (OPENAI, ANTHROPIC) to remote pods",
    )
    args = parser.parse_args(argv)

    extra_settings: Dict[str, Any] = {}
    if args.forward_env:
        runtime_env = _collect_runtime_env_vars()
        if runtime_env:
            extra_settings["docker"] = {"runtime_environment": runtime_env}

    if extra_settings:
        harbor_eval_campaign.with_options(
            settings=extra_settings,
        )(config_path=args.config)
    else:
        harbor_eval_campaign(config_path=args.config)


if __name__ == "__main__":
    main()
