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
import sys
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from typing import Optional
from unittest.mock import ANY
from uuid import UUID, uuid4

import pytest

import zenml
from tests.unit.conftest_new import empty_pipeline  # noqa
from zenml.client import Client
from zenml.code_repositories import BaseCodeRepository, LocalRepositoryContext
from zenml.config import DockerSettings
from zenml.config.build_configuration import BuildConfiguration
from zenml.config.source import Source
from zenml.models import (
    CodeRepositoryResponse,
    CodeRepositoryResponseBody,
    CodeRepositoryResponseMetadata,
    Page,
    PipelineBuildResponse,
    PipelineBuildResponseBody,
    PipelineBuildResponseMetadata,
    PipelineDeploymentBase,
    PipelineDeploymentResponse,
)
from zenml.new.pipelines import build_utils
from zenml.stack import Stack
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)


class StubCodeRepository(BaseCodeRepository):
    def __init__(
        self, id: UUID = uuid4(), config=None, local_context=None
    ) -> None:
        config = config or {}
        super().__init__(id, config)
        self._local_context = local_context

    def login(self) -> None:
        pass

    def download_files(
        self, commit: str, directory: str, repo_sub_directory: Optional[str]
    ) -> None:
        pass

    def get_local_context(
        self, path: str
    ) -> Optional["LocalRepositoryContext"]:
        return self._local_context


class StubLocalRepositoryContext(LocalRepositoryContext):
    def __init__(
        self,
        code_repository_id: UUID = uuid4(),
        root: str = ".",
        is_dirty: bool = False,
        has_local_changes: bool = False,
        commit: str = "",
    ) -> None:
        super().__init__(code_repository_id=code_repository_id)
        self._root = root
        self._is_dirty = is_dirty
        self._has_local_changes = has_local_changes
        self._commit = commit

    @property
    def root(self) -> str:
        return self._root

    @property
    def is_dirty(self) -> bool:
        return self._is_dirty

    @property
    def has_local_changes(self) -> bool:
        return self._has_local_changes

    @property
    def current_commit(self) -> str:
        return self._commit


def test_build_is_skipped_when_not_required(mocker):
    """Tests that no build is performed when the stack doesn't require it."""
    mocker.patch.object(Stack, "get_docker_builds", return_value=[])
    mock_build_docker_image = mocker.patch.object(
        PipelineDockerImageBuilder,
        "build_docker_image",
        return_value=("image_name", "", ""),
    )

    deployment = PipelineDeploymentBase(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
        client_version="0.12.3",
        server_version="0.12.3",
    )

    assert build_utils.create_pipeline_build(deployment=deployment) is None
    mock_build_docker_image.assert_not_called()


def test_stack_with_container_registry_creates_non_local_build(
    mocker, remote_container_registry
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
        return_value=("image_name", "", ""),
    )

    deployment = PipelineDeploymentBase(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
        client_version="0.12.3",
        server_version="0.12.3",
    )

    build = build_utils.create_pipeline_build(deployment=deployment)
    assert build.is_local is False


def test_build_uses_correct_settings(mocker, empty_pipeline):  # noqa: F811
    """Tests that the build settings and pipeline ID get correctly forwarded."""
    build_config = BuildConfiguration(
        key="key",
        settings=DockerSettings(
            source_files=["include", "download_from_code_repository"]
        ),
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
        return_value=("image_name", "", ""),
    )

    deployment = PipelineDeploymentBase(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
        client_version="0.12.3",
        server_version="0.12.3",
    )

    pipeline_instance = empty_pipeline
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
        stack=Client().active_stack
    )


def test_building_with_identical_keys_and_settings(mocker):
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
        return_value=("image_name", "", ""),
    )

    deployment = PipelineDeploymentBase(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
        client_version="0.12.3",
        server_version="0.12.3",
    )

    build = build_utils.create_pipeline_build(deployment=deployment)
    assert len(build.images) == 1
    assert build.images["key"].image == "image_name"

    mock_build_docker_image.assert_called_once()


def test_building_with_identical_keys_and_different_settings(mocker):
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
        return_value=("image_name", "", ""),
    )

    deployment = PipelineDeploymentBase(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
        client_version="0.12.3",
        server_version="0.12.3",
    )

    with pytest.raises(RuntimeError):
        build_utils.create_pipeline_build(deployment=deployment)


def test_building_with_different_keys_and_identical_settings(mocker):
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
        return_value=("image_name", "", ""),
    )

    deployment = PipelineDeploymentBase(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={},
        client_version="0.12.3",
        server_version="0.12.3",
    )

    build = build_utils.create_pipeline_build(deployment=deployment)
    assert len(build.images) == 2
    assert build.images["key1"].image == "image_name"
    assert build.images["key2"].image == "image_name"

    mock_build_docker_image.assert_called_once()


def test_custom_build_verification(
    mocker,
    sample_deployment_response_model,
):
    """Tests the verification of a custom build."""
    mocker.patch.object(
        Stack,
        "get_docker_builds",
        return_value=[
            BuildConfiguration(key="key", settings=DockerSettings())
        ],
    )

    missing_image_build = PipelineBuildResponse(
        id=uuid4(),
        body=PipelineBuildResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            user=sample_deployment_response_model.user,
        ),
        metadata=PipelineBuildResponseMetadata(
            workspace=sample_deployment_response_model.workspace,
            images={"wrong_key": {"image": "docker_image_name"}},
            is_local=False,
            contains_code=True,
        ),
    )

    with pytest.raises(RuntimeError):
        # Image key missing
        build_utils.verify_custom_build(
            build=missing_image_build,
            deployment=sample_deployment_response_model,
        )

    correct_build = missing_image_build.model_copy(deep=True)
    correct_build.metadata = PipelineBuildResponseMetadata.model_validate(
        {
            **missing_image_build.metadata.model_dump(),
            "images": {"key": {"image": "docker_image_name"}},
        }
    )

    with does_not_raise():
        # All keys present
        build_utils.verify_custom_build(
            build=correct_build,
            deployment=sample_deployment_response_model,
        )

    build_that_requires_download = missing_image_build.model_copy(deep=True)
    build_that_requires_download.metadata = (
        PipelineBuildResponseMetadata.model_validate(
            {
                **missing_image_build.metadata.model_dump(),
                "images": {
                    "key": {
                        "image": "docker_image_name",
                        "requires_code_download": True,
                    }
                },
            }
        )
    )
    mocker.patch(
        "zenml.new.pipelines.build_utils.requires_download_from_code_repository",
        return_value=True,
    )

    with pytest.raises(RuntimeError):
        # Missing code repo for download
        build_utils.verify_custom_build(
            build=build_that_requires_download,
            deployment=sample_deployment_response_model,
        )

    code_repo = StubCodeRepository()
    with does_not_raise():
        build_utils.verify_custom_build(
            build=build_that_requires_download,
            deployment=sample_deployment_response_model,
            code_repository=code_repo,
        )


def test_build_checksum_computation(mocker):
    mocker.patch.object(
        BuildConfiguration,
        "compute_settings_checksum",
        return_value="settings_checksum",
    )

    build_config = BuildConfiguration(key="key", settings=DockerSettings())
    checksum = build_utils.compute_build_checksum(
        items=[build_config], stack=Client().active_stack
    )

    # different key
    new_build_config = BuildConfiguration(
        key="different_key", settings=DockerSettings()
    )
    new_checksum = build_utils.compute_build_checksum(
        items=[new_build_config], stack=Client().active_stack
    )
    assert checksum != new_checksum

    # different settings checksum
    mocker.patch.object(
        BuildConfiguration,
        "compute_settings_checksum",
        return_value="different_settings_checksum",
    )
    new_checksum = build_utils.compute_build_checksum(
        items=[build_config], stack=Client().active_stack
    )
    assert checksum != new_checksum


def test_local_repo_verification(
    mocker, sample_deployment_response_model: PipelineDeploymentResponse
):
    """Test the local repo verification."""

    deployment = PipelineDeploymentBase(
        run_name_template=sample_deployment_response_model.run_name_template,
        pipeline_configuration=sample_deployment_response_model.pipeline_configuration,
        step_configurations=sample_deployment_response_model.step_configurations,
        client_environment=sample_deployment_response_model.client_environment,
        client_version=sample_deployment_response_model.client_version,
        server_version=sample_deployment_response_model.server_version,
    )
    mocker.patch(
        "zenml.new.pipelines.build_utils.requires_download_from_code_repository",
        return_value=False,
    )

    dirty_local_context = StubLocalRepositoryContext(is_dirty=True)
    context_with_local_changes = StubLocalRepositoryContext(
        has_local_changes=True
    )

    assert not build_utils.verify_local_repository_context(
        deployment=deployment, local_repo_context=None
    )
    assert not build_utils.verify_local_repository_context(
        deployment=deployment,
        local_repo_context=context_with_local_changes,
    )

    mocker.patch(
        "zenml.new.pipelines.build_utils.requires_download_from_code_repository",
        return_value=True,
    )
    mocker.patch.object(Stack, "get_docker_builds", return_value=[])

    # Code download not required if no build is necessary
    assert not build_utils.verify_local_repository_context(
        deployment=deployment,
        local_repo_context=None,
    )

    build_config = BuildConfiguration(key="key", settings=DockerSettings())
    mocker.patch.object(
        Stack, "get_docker_builds", return_value=[build_config]
    )

    with pytest.raises(RuntimeError):
        # No local repo
        build_utils.verify_local_repository_context(
            deployment=deployment,
            local_repo_context=None,
        )

    with pytest.raises(RuntimeError):
        build_utils.verify_local_repository_context(
            deployment=deployment,
            local_repo_context=dirty_local_context,
        )

    with pytest.raises(RuntimeError):
        build_utils.verify_local_repository_context(
            deployment=deployment,
            local_repo_context=context_with_local_changes,
        )

    repo_response = CodeRepositoryResponse(
        id=uuid4(),
        name="name",
        body=CodeRepositoryResponseBody(
            created=datetime.now(),
            updated=datetime.now(),
            user=sample_deployment_response_model.user,
            source=Source(
                module=StubCodeRepository.__module__,
                attribute=StubCodeRepository.__name__,
                type="unknown",
            ),
        ),
        metadata=CodeRepositoryResponseMetadata(
            workspace=sample_deployment_response_model.workspace,
            config={"key": "value"},
        ),
    )

    mocker.patch(
        "zenml.client.Client.get_code_repository", return_value=repo_response
    )
    clean_local_context = StubLocalRepositoryContext(
        is_dirty=False, has_local_changes=False
    )
    code_repo = build_utils.verify_local_repository_context(
        deployment=deployment,
        local_repo_context=clean_local_context,
    )
    assert isinstance(code_repo, StubCodeRepository)


def test_finding_existing_build(mocker, sample_deployment_response_model):
    """Tests finding an existing build."""
    mock_list_builds = mocker.patch(
        "zenml.client.Client.list_builds",
        return_value=Page(
            index=1,
            max_size=1,
            total_pages=1,
            total=0,
            items=[],
        ),
    )
    mocker.patch(
        "zenml.new.pipelines.build_utils.compute_build_checksum",
        return_value="checksum",
    )
    mocker.patch.object(Stack, "get_docker_builds", return_value=[])

    build_utils.find_existing_build(
        deployment=sample_deployment_response_model,
        code_repository=StubCodeRepository(),
    )
    # No required builds -> no need to look for build to reuse
    mock_list_builds.assert_not_called()

    mocker.patch.object(
        Stack,
        "get_docker_builds",
        return_value=[
            BuildConfiguration(key="key", settings=DockerSettings())
        ],
    )

    build = build_utils.find_existing_build(
        deployment=sample_deployment_response_model,
        code_repository=StubCodeRepository(),
    )
    mock_list_builds.assert_called_once_with(
        sort_by="desc:created",
        size=1,
        stack_id=Client().active_stack.id,
        is_local=False,
        contains_code=False,
        zenml_version=zenml.__version__,
        python_version=f"startswith:{sys.version_info.major}.{sys.version_info.minor}",
        checksum="checksum",
    )

    assert not build
