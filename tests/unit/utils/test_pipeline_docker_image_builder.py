#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from pathlib import Path

import pytest

from zenml.client import Client
from zenml.config import DockerSettings
from zenml.integrations.sklearn import SKLEARN, SklearnIntegration
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)


def test_check_user_is_set():
    """Tests the setting of the user if configured."""
    docker_settings = DockerSettings(user=None)
    generated_dockerfile = (
        PipelineDockerImageBuilder._generate_zenml_pipeline_dockerfile(
            "image:tag",
            docker_settings,
            download_files=False,
        )
    )
    assert "USER" not in generated_dockerfile

    docker_settings = DockerSettings(user="test_user")
    generated_dockerfile = (
        PipelineDockerImageBuilder._generate_zenml_pipeline_dockerfile(
            "image:tag",
            docker_settings,
            download_files=False,
        )
    )
    assert "USER test_user" in generated_dockerfile


def test_requirements_file_generation(mocker, local_stack, tmp_path: Path):
    """Tests that the requirements get included in the correct order and only when configured."""
    mocker.patch("subprocess.check_output", return_value=b"local_requirements")
    mocker.patch.object(
        local_stack, "requirements", return_value={"stack_requirements"}
    )

    # just local requirements
    settings = DockerSettings(
        install_stack_requirements=False,
        requirements=None,
        required_integrations=[],
        replicate_local_python_environment="pip_freeze",
    )
    files = PipelineDockerImageBuilder.gather_requirements_files(
        settings, stack=local_stack
    )
    assert len(files) == 1
    assert files[0][1] == "local_requirements"

    # just stack requirements
    settings = DockerSettings(
        install_stack_requirements=True,
        requirements=None,
        required_integrations=[],
        replicate_local_python_environment=None,
    )
    files = PipelineDockerImageBuilder.gather_requirements_files(
        settings, stack=local_stack
    )
    assert len(files) == 1
    assert files[0][1] == "stack_requirements"

    # just user requirements
    settings = DockerSettings(
        install_stack_requirements=False,
        requirements=["user_requirements"],
        required_integrations=[],
        replicate_local_python_environment=None,
    )
    files = PipelineDockerImageBuilder.gather_requirements_files(
        settings, stack=local_stack
    )
    assert len(files) == 1
    assert files[0][1] == "user_requirements"

    # all values set
    requirements_file = tmp_path / "requirements.txt"
    requirements_file.write_text("user_requirements")
    settings = DockerSettings(
        install_stack_requirements=True,
        requirements=str(requirements_file),
        required_integrations=[SKLEARN],
        replicate_local_python_environment="pip_freeze",
    )
    files = PipelineDockerImageBuilder.gather_requirements_files(
        settings, stack=local_stack
    )
    assert len(files) == 4
    # first up the local python requirements
    assert files[0][1] == "local_requirements"
    # then the stack requirements
    assert files[1][1] == "stack_requirements"
    # then the integration requirements
    expected_integration_requirements = "\n".join(
        sorted(SklearnIntegration.REQUIREMENTS)
    )
    assert files[2][1] == expected_integration_requirements
    # last the user requirements
    assert files[3][1] == "user_requirements"


def test_build_skipping():
    """Tests that the parent image is returned directly if `skip_build` is set
    to `True`."""
    settings = DockerSettings(skip_build=True, parent_image="my_parent_image")
    image_digest, _, _ = PipelineDockerImageBuilder().build_docker_image(
        docker_settings=settings,
        tag="tag",
        stack=Client().active_stack,
        include_files=True,
        download_files=False,
    )
    assert image_digest


def test_python_package_installer_args():
    """Tests that the python package installer args get passed correctly."""
    docker_settings = DockerSettings(
        python_package_installer_args={
            "default-timeout": 99,
            "other-arg": "value",
            "option": None,
        }
    )

    requirements_files = [("requirements.txt", "numpy", [])]
    generated_dockerfile = (
        PipelineDockerImageBuilder._generate_zenml_pipeline_dockerfile(
            "image:tag",
            docker_settings,
            download_files=False,
            requirements_files=requirements_files,
        )
    )

    assert (
        "RUN pip install --no-cache-dir --default-timeout=99 --other-arg=value --option"
        in generated_dockerfile
    )


def test_dockerfile_needs_to_exist():
    """Tests that an error gets raised if the Dockerfile specified in the
    DockerSettings does not exist."""
    docker_settings = DockerSettings(
        dockerfile="/a/file/that/does/not/exist.random"
    )

    with pytest.raises(ValueError):
        PipelineDockerImageBuilder().build_docker_image(
            docker_settings=docker_settings,
            tag="tag",
            stack=Client().active_stack,
            include_files=True,
            download_files=False,
        )
