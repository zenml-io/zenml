#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Unit tests for the containerized deployer."""

from unittest.mock import MagicMock

import pytest

from zenml.config import DockerSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.constants import DEPLOYER_DOCKER_IMAGE_KEY
from zenml.deployers.containerized_deployer import ContainerizedDeployer
from zenml.deployers.exceptions import DeployerError


def test_get_image_reads_from_deployment_build():
    """The deployer image is read from the build attached to the deployment."""
    deployment = MagicMock()
    deployment.build.images = {
        DEPLOYER_DOCKER_IMAGE_KEY: MagicMock(image="my-deployer-image")
    }

    assert ContainerizedDeployer.get_image(deployment) == "my-deployer-image"


def test_get_image_raises_without_build():
    """get_image raises when the deployment has no build."""
    deployment = MagicMock()
    deployment.build = None

    with pytest.raises(RuntimeError):
        ContainerizedDeployer.get_image(deployment)


def test_get_image_raises_without_deployer_image():
    """get_image raises when the build has no deployer image."""
    deployment = MagicMock()
    deployment.build.images = {}

    with pytest.raises(RuntimeError):
        ContainerizedDeployer.get_image(deployment)


def _deployer_builds(**docker_flags):
    return [
        BuildConfiguration(
            key=DEPLOYER_DOCKER_IMAGE_KEY,
            settings=DockerSettings(**docker_flags),
        )
    ]


def test_prepare_build_refuses_bake_without_local_code():
    """An existing snapshot that must bake code can't deploy without local code."""
    deployer = MagicMock()
    deployer.get_docker_builds.return_value = _deployer_builds(
        allow_download_from_artifact_store=False,
        allow_download_from_code_repository=False,
        allow_including_files_in_images=True,
    )
    snapshot = MagicMock(code_path=None, code_reference=None)

    with pytest.raises(DeployerError, match="no local code"):
        ContainerizedDeployer._prepare_deployment_build(
            deployer,
            snapshot=snapshot,
            stack=MagicMock(),
            local_code_available=False,
        )


def test_prepare_build_refuses_code_free_image_without_code_source():
    """A code-free deployer image needs the snapshot to carry downloadable code."""
    deployer = MagicMock()
    deployer.get_docker_builds.return_value = _deployer_builds()
    snapshot = MagicMock(code_path=None, code_reference=None)

    with pytest.raises(DeployerError, match="no code to download"):
        ContainerizedDeployer._prepare_deployment_build(
            deployer,
            snapshot=snapshot,
            stack=MagicMock(),
            local_code_available=False,
        )
