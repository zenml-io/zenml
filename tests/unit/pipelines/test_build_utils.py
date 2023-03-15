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
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from unittest.mock import ANY
from uuid import uuid4

import pytest

from zenml.config import DockerSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.models import PipelineBuildResponseModel
from zenml.models.pipeline_deployment_models import PipelineDeploymentBaseModel
from zenml.pipelines import build_utils
from zenml.stack import Stack
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)


def test_build_is_skipped_when_not_required(mocker):
    """Tests that no build is performed when the stack doesn't require it."""
    mocker.patch.object(Stack, "get_docker_builds", return_value=[])
    mock_build_docker_image = mocker.patch.object(
        PipelineDockerImageBuilder,
        "build_docker_image",
        return_value="image_name",
    )

    deployment = PipelineDeploymentBaseModel(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
    )

    assert build_utils.create_pipeline_build(deployment=deployment) is None
    mock_build_docker_image.assert_not_called()


def test_stack_with_container_registry_creates_non_local_build(
    clean_client, mocker, remote_container_registry
):
    """Tests that building for a stack with container registry creates a
    non-local build."""
    build_config = BuildConfiguration(key="key", settings=DockerSettings())
    mocker.patch.object(
        Stack, "get_docker_builds", return_value=[build_config]
    )
    mocker.patch.object(
        Stack,
        "container_registry",
        new_callable=mocker.PropertyMock,
        return_value=remote_container_registry,
    )

    mocker.patch.object(
        PipelineDockerImageBuilder,
        "build_docker_image",
        return_value="image_name",
    )

    deployment = PipelineDeploymentBaseModel(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
    )

    build = build_utils.create_pipeline_build(deployment=deployment)
    assert build.is_local is False


def test_build_uses_correct_settings(clean_client, mocker, empty_pipeline):
    """Tests that the build settings and pipeline ID get correctly forwarded."""
    build_config = BuildConfiguration(
        key="key",
        settings=DockerSettings(),
        step_name="step_name",
        entrypoint="entrypoint",
        extra_files={"key": "value"},
    )
    mocker.patch.object(
        Stack, "get_docker_builds", return_value=[build_config]
    )
    mock_build_docker_image = mocker.patch.object(
        PipelineDockerImageBuilder,
        "build_docker_image",
        return_value="image_name",
    )

    deployment = PipelineDeploymentBaseModel(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
    )

    pipeline_instance = empty_pipeline()
    pipeline_id = pipeline_instance.register().id
    build = build_utils.create_pipeline_build(
        deployment=deployment, pipeline_id=pipeline_id
    )

    mock_build_docker_image.assert_called_with(
        docker_settings=build_config.settings,
        tag="pipeline-step_name-key",
        stack=ANY,
        entrypoint=build_config.entrypoint,
        extra_files=build_config.extra_files,
        include_files=True,
        download_files=False,
        code_repository=None,
    )
    assert build.pipeline.id == pipeline_id
    assert build.is_local is True
    assert len(build.images) == 1
    image = build.images["step_name.key"]
    assert image.image == "image_name"
    assert image.settings_checksum == build_config.compute_settings_checksum(
        stack=clean_client.active_stack
    )


def test_building_with_identical_keys_and_settings(clean_client, mocker):
    """Tests that two build configurations with identical keys and identical
    settings don't lead to two builds."""
    build_config_1 = BuildConfiguration(key="key", settings=DockerSettings())
    build_config_2 = BuildConfiguration(key="key", settings=DockerSettings())

    mocker.patch.object(
        Stack,
        "get_docker_builds",
        return_value=[build_config_1, build_config_2],
    )
    mock_build_docker_image = mocker.patch.object(
        PipelineDockerImageBuilder,
        "build_docker_image",
        return_value="image_name",
    )

    deployment = PipelineDeploymentBaseModel(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
    )

    build = build_utils.create_pipeline_build(deployment=deployment)
    assert len(build.images) == 1
    assert build.images["key"].image == "image_name"

    mock_build_docker_image.assert_called_once()


def test_building_with_identical_keys_and_different_settings(
    clean_client, mocker
):
    """Tests that two build configurations with identical keys and different
    settings lead to an error."""
    build_config_1 = BuildConfiguration(key="key", settings=DockerSettings())
    build_config_2 = BuildConfiguration(
        key="key", settings=DockerSettings(requirements=["requirement"])
    )

    mocker.patch.object(
        Stack,
        "get_docker_builds",
        return_value=[build_config_1, build_config_2],
    )
    mocker.patch.object(
        PipelineDockerImageBuilder,
        "build_docker_image",
        return_value="image_name",
    )

    deployment = PipelineDeploymentBaseModel(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
    )

    with pytest.raises(RuntimeError):
        build_utils.create_pipeline_build(deployment=deployment)


def test_building_with_different_keys_and_identical_settings(
    clean_client, mocker
):
    """Tests that two build configurations with different keys and identical
    settings don't lead to two builds."""
    build_config_1 = BuildConfiguration(key="key1", settings=DockerSettings())
    build_config_2 = BuildConfiguration(key="key2", settings=DockerSettings())

    mocker.patch.object(
        Stack,
        "get_docker_builds",
        return_value=[build_config_1, build_config_2],
    )
    mock_build_docker_image = mocker.patch.object(
        PipelineDockerImageBuilder,
        "build_docker_image",
        return_value="image_name",
    )

    deployment = PipelineDeploymentBaseModel(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
    )

    build = build_utils.create_pipeline_build(deployment=deployment)
    assert len(build.images) == 2
    assert build.images["key1"].image == "image_name"
    assert build.images["key2"].image == "image_name"

    mock_build_docker_image.assert_called_once()


def test_custom_build_validation(
    mocker,
    sample_deployment_response_model,
):
    """Tests the build validation performed by the stack."""
    mocker.patch.object(Stack, "get_docker_builds", return_value=[])

    assert sample_deployment_response_model.build is None

    mocker.patch.object(
        Stack,
        "get_docker_builds",
        return_value=[
            BuildConfiguration(key="key", settings=DockerSettings())
        ],
    )

    incorrect_build = PipelineBuildResponseModel(
        id=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
        user=sample_deployment_response_model.user,
        workspace=sample_deployment_response_model.workspace,
        images={"wrong_key": {"image": "docker_image_name"}},
        is_local=False,
        contains_code=True,
    )

    with pytest.raises(RuntimeError):
        # Image key missing
        build_utils.verify_custom_build(
            build=incorrect_build,
            deployment=sample_deployment_response_model,
            pipeline_version_hash="",
        )

    correct_build = PipelineBuildResponseModel.parse_obj(
        {
            **incorrect_build.dict(),
            "images": {"key": {"image": "docker_image_name"}},
        }
    )

    with does_not_raise():
        # All keys present
        build_utils.verify_custom_build(
            build=correct_build,
            deployment=sample_deployment_response_model,
            pipeline_version_hash="",
        )
