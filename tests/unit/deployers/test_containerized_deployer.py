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

from unittest.mock import MagicMock, patch

import pytest

from zenml.constants import DEPLOYER_DOCKER_IMAGE_KEY
from zenml.deployers.containerized_deployer import ContainerizedDeployer
from zenml.deployers.exceptions import DeployerError


def _snapshot_with_image(image: str) -> MagicMock:
    snapshot = MagicMock()
    snapshot.build.images = {DEPLOYER_DOCKER_IMAGE_KEY: MagicMock(image=image)}
    return snapshot


def test_get_image_reads_from_snapshot_build():
    """The serving image is read from the deployment's snapshot build."""
    deployment = MagicMock()
    snapshot = _snapshot_with_image("my-deployer-image")

    with patch("zenml.client.Client") as mock_client:
        mock_client.return_value.get_snapshot.return_value = snapshot
        assert (
            ContainerizedDeployer.get_image(deployment) == "my-deployer-image"
        )


def test_get_image_raises_without_build():
    """get_image raises when the snapshot has no build."""
    deployment = MagicMock()
    snapshot = MagicMock()
    snapshot.build = None

    with patch("zenml.client.Client") as mock_client:
        mock_client.return_value.get_snapshot.return_value = snapshot
        with pytest.raises(RuntimeError):
            ContainerizedDeployer.get_image(deployment)


def test_get_image_raises_without_deployer_image():
    """get_image raises when the build has no deployer image."""
    deployment = MagicMock()
    snapshot = MagicMock()
    snapshot.build.images = {}

    with patch("zenml.client.Client") as mock_client:
        mock_client.return_value.get_snapshot.return_value = snapshot
        with pytest.raises(RuntimeError):
            ContainerizedDeployer.get_image(deployment)


def _deployer_with_checksum(checksum: str) -> MagicMock:
    build_config = MagicMock()
    build_config.compute_settings_checksum.return_value = checksum
    deployer = MagicMock()
    deployer.get_docker_builds.return_value = [build_config]
    deployer.name = "docker"
    return deployer


def test_validate_skips_when_no_image_required():
    """A deployer that needs no image accepts any snapshot."""
    deployer = MagicMock()
    deployer.get_docker_builds.return_value = []

    assert (
        ContainerizedDeployer._validate_snapshot_deployable(
            deployer, snapshot=MagicMock(), stack=MagicMock()
        )
        is None
    )


def test_validate_rejects_snapshot_without_serving_image():
    """A snapshot with no serving image is not deployable."""
    deployer = _deployer_with_checksum("whatever")
    snapshot = MagicMock(build=None)

    with pytest.raises(
        DeployerError, match="does not contain a serving image"
    ):
        ContainerizedDeployer._validate_snapshot_deployable(
            deployer, snapshot=snapshot, stack=MagicMock()
        )


def test_validate_rejects_image_built_for_a_different_deployer():
    """A serving image whose checksum differs is rejected."""
    deployer = _deployer_with_checksum("expected")
    snapshot = MagicMock(code_reference=None)
    snapshot.build.images = {DEPLOYER_DOCKER_IMAGE_KEY: MagicMock()}
    snapshot.build.get_settings_checksum.return_value = "different"

    with pytest.raises(DeployerError, match="not built for the deployer"):
        ContainerizedDeployer._validate_snapshot_deployable(
            deployer, snapshot=snapshot, stack=MagicMock()
        )


def test_validate_accepts_matching_serving_image():
    """A serving image whose checksum matches is accepted."""
    deployer = _deployer_with_checksum("match")
    snapshot = MagicMock(code_reference=None)
    snapshot.build.images = {DEPLOYER_DOCKER_IMAGE_KEY: MagicMock()}
    snapshot.build.get_settings_checksum.return_value = "match"

    assert (
        ContainerizedDeployer._validate_snapshot_deployable(
            deployer, snapshot=snapshot, stack=MagicMock()
        )
        is None
    )
