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

from zenml.constants import DEPLOYER_DOCKER_IMAGE_KEY
from zenml.deployers.containerized_deployer import ContainerizedDeployer


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
