#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Utility functions for the Lightning orchestrator."""

import itertools
import os
import re
import shutil
from typing import List

from zenml.client import Client
from zenml.config import DockerSettings
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)


def sanitize_studio_name(studio_name: str) -> str:
    """Sanitize studio_names so they conform to Kubernetes studio naming convention.

    Args:
        studio_name: Arbitrary input studio_name.

    Returns:
        Sanitized pod name.
    """
    studio_name = re.sub(r"[^a-z0-9-]", "-", studio_name.lower())
    studio_name = re.sub(r"^[-]+", "", studio_name)
    return re.sub(r"[-]+", "-", studio_name)


def gather_requirements(docker_settings: "DockerSettings") -> List[str]:
    """Gather the requirements files."""
    docker_image_builder = PipelineDockerImageBuilder()
    requirements_files = docker_image_builder.gather_requirements_files(
        docker_settings=docker_settings,
        stack=Client().active_stack,
        log=False,
    )

    # Extract and clean the requirements
    requirements = list(
        itertools.chain.from_iterable(
            r[1].strip().split("\n") for r in requirements_files
        )
    )

    # Remove empty items and duplicates
    requirements = sorted(set(filter(None, requirements)))

    return requirements


def download_and_extract_code(code_path: str, extract_dir: str) -> None:
    """Download and extract code.

    Args:
        code_path: Path where the code is uploaded.
        extract_dir: Directory where to code should be extracted to.

    Raises:
        RuntimeError: If the code is stored in an artifact store which is
            not active.
    """
    download_path = os.path.basename(code_path)

    shutil.unpack_archive(filename=download_path, extract_dir=extract_dir)
    os.remove(download_path)
