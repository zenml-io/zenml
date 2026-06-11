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
"""Shape A campaign: Harbor owns job orchestration, ZenML wraps the job.

DAG (one branch per agent x model combo; Harbor runs all tasks inside each):

    build_combos
         |
    +---------+---------+
    |         |         |
  job_0     job_1    job_N      <- one Harbor job per (agent, model)
    |         |         |       (Harbor schedules N trials inside each)
  parse_0  parse_1  parse_N
    |         |         |
    +---------+---------+
              |
       build_report_jobwise

Contrast with ``harbor_eval_campaign`` (shape B), which fans out one ZenML step
per trial. Same Sandbox bridge + dev image; only the orchestration shape moves.
"""

from typing import Annotated, Tuple

from models.harbor_models import CampaignReport
from steps.build_report_jobwise import build_report_jobwise
from steps.parse_harbor_job import parse_harbor_job
from steps.run_harbor_job_jobwise import build_combos, run_harbor_job_jobwise

from pipelines.harbor_eval_campaign import docker_settings
from zenml import pipeline
from zenml.types import HTMLString


@pipeline(
    dynamic=True,
    enable_cache=False,
    settings={"docker": docker_settings},
)
def harbor_eval_campaign_jobwise(
    config_path: str = "configs/dev.yaml",
) -> Tuple[
    Annotated[CampaignReport, "campaign_report"],
    Annotated[HTMLString, "report"],
]:
    """Run one Harbor job per (agent, model); Harbor orchestrates the trials.

    Args:
        config_path: Path to the campaign YAML config file.

    Returns:
        Tuple of (structured CampaignReport, HTML report visualization).
    """
    combos = build_combos(config_path=config_path)
    job_dirs = run_harbor_job_jobwise.map(spec=combos)
    summaries = parse_harbor_job.map(job_dir=job_dirs, spec=combos)
    return build_report_jobwise(job_summaries=summaries)
