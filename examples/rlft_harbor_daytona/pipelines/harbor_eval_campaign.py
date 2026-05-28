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
"""Harbor evaluation campaign pipeline with dynamic fan-out.

DAG shape (determined at runtime by the config's agent x model matrix):

    build_matrix
         |
    +---------+---------+
    |         |         |
  run_0     run_1    run_N      <- one per (agent, model) combo
    |         |         |
  parse_0  parse_1  parse_N
    |         |         |
    +---------+---------+
              |
        build_report
"""

from typing import Annotated, Any, Dict, List, Tuple

from steps import build_matrix, build_report, parse_harbor_job, run_harbor_job

from zenml import pipeline
from zenml.config import DockerSettings, PythonPackageInstaller
from zenml.types import HTMLString

from models.harbor_models import CampaignReport

docker_settings = DockerSettings(
    python_package_installer=PythonPackageInstaller.UV,
    requirements="requirements.txt",
)


@pipeline(
    dynamic=True,
    enable_cache=False,
    settings={"docker": docker_settings},
)
def harbor_eval_campaign(
    config_path: str = "configs/dev.yaml",
) -> Tuple[
    Annotated[CampaignReport, "campaign_report"],
    Annotated[HTMLString, "report"],
]:
    """Run Harbor agent evaluations across a configurable agent x model matrix.

    The pipeline reads a YAML config to build the evaluation matrix, then
    dynamically fans out one run_harbor_job + parse_harbor_job pair per
    matrix entry. All results are aggregated into a leaderboard report.

    Args:
        config_path: Path to the campaign YAML config file.

    Returns:
        Tuple of (structured CampaignReport, HTML report visualization).
    """
    matrix = build_matrix(config_path=config_path)

    # .load() materializes the list so we can iterate over it.
    # .chunk(index=idx) creates DAG edges without materializing.
    matrix_data = matrix.load()

    summaries: List[Any] = []
    for idx in range(len(matrix_data)):
        spec = matrix.chunk(index=idx)
        job_dir = run_harbor_job(spec=spec)
        summary = parse_harbor_job(job_dir=job_dir, spec=spec)
        summaries.append(summary)

    return build_report(job_summaries=summaries)
