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

import site
import sys
from pathlib import Path
from typing import Annotated, Tuple

from models.harbor_models import CampaignReport
from steps import build_matrix, build_report, parse_harbor_job, run_harbor_job

import zenml
from zenml import pipeline
from zenml.config import DockerSettings, PythonPackageInstaller
from zenml.types import HTMLString


def _docker_settings() -> DockerSettings:
    """Docker settings for remote (containerized) runs.

    The Sandbox component is unreleased, so a stock image built from PyPI
    ``zenml`` would lack ``zenml.sandboxes`` and the bridge would fail to
    import in the pod. When ZenML is an editable/branch checkout we therefore
    build the parent image from the repo's ``docker/zenml-dev.Dockerfile`` so
    the branch ZenML (Sandbox component included) is baked in. The example's
    own deps go on top; the stack's integration deps (modal, s3, aws,
    kubernetes) are added automatically via ``install_stack_requirements``.

    Returns:
        DockerSettings suitable for the active install (editable or released).
    """
    common = {
        "python_package_installer": PythonPackageInstaller.UV,
        # zenml comes from the parent image — do NOT list it here, or PyPI
        # zenml would overwrite the branch build and drop the Sandbox component.
        "requirements": ["harbor>=0.8.0", "pyyaml>=6.0"],
        "build_config": {"build_options": {"platform": "linux/amd64"}},
    }
    zenml_root = Path(zenml.__file__).resolve().parents[2]
    dev_dockerfile = zenml_root / "docker" / "zenml-dev.Dockerfile"
    is_editable = not any(
        Path(p).resolve() in Path(zenml.__file__).resolve().parents
        for p in site.getsitepackages()
    )
    if is_editable and dev_dockerfile.exists():
        py = f"{sys.version_info.major}.{sys.version_info.minor}"
        return DockerSettings(
            dockerfile=str(dev_dockerfile),
            build_context_root=str(zenml_root),
            parent_image_build_config={
                "build_options": {
                    "platform": "linux/amd64",
                    "buildargs": {"PYTHON_VERSION": py},
                }
            },
            prevent_build_reuse=False,
            **common,
        )
    return DockerSettings(**common)


docker_settings = _docker_settings()


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

    # .map fans out one step per item in the matrix list without
    # materializing it on the client. run_harbor_job runs per spec; its
    # results are zipped 1:1 back against the same matrix so parse_harbor_job
    # sees each job_dir alongside the spec that produced it.
    job_dirs = run_harbor_job.map(spec=matrix)
    summaries = parse_harbor_job.map(job_dir=job_dirs, spec=matrix)

    return build_report(job_summaries=summaries)
