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
"""Shape A entry point — Harbor owns the job orchestration.

Runs the same evaluation as ``run.py`` but with one Harbor job per
(agent, model) combo (Harbor schedules the trials), instead of one ZenML step
per trial. Same bridge, same Sandbox substrate.

    python run_jobwise.py --config configs/dev.yaml
"""

import argparse
from typing import Optional, Sequence

from pipelines.harbor_eval_campaign_jobwise import harbor_eval_campaign_jobwise


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Run the job-wise (shape A) Harbor evaluation campaign.

    Args:
        argv: Command-line arguments. If None, uses sys.argv.
    """
    parser = argparse.ArgumentParser(
        description="Run Harbor evals with Harbor-owned job orchestration "
        "(shape A): one Harbor job per agent x model combo."
    )
    parser.add_argument(
        "--config",
        "-c",
        default="configs/dev.yaml",
        help="Path to campaign YAML config (default: configs/dev.yaml)",
    )
    args = parser.parse_args(argv)
    harbor_eval_campaign_jobwise(config_path=args.config)


if __name__ == "__main__":
    main()
