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

from zenml.config import DockerSettings
from zenml.integrations.sklearn import SKLEARN, SklearnIntegration
from zenml.stack import Stack
from zenml.utils.pipeline_docker_image_builder import (
    DOCKER_IMAGE_ZENML_CONFIG_DIR,
    PipelineDockerImageBuilder,
    _include_active_profile,
)


def test_including_active_profile_in_build_context(tmp_path: Path):
    """Tests that the context manager includes the active profile in the build
    context."""
    root = tmp_path / "build_context"
    config_path = root / DOCKER_IMAGE_ZENML_CONFIG_DIR

    assert not config_path.exists()

    with _include_active_profile(build_context_root=str(root)):
        assert config_path.exists()

    assert not config_path.exists()


def test_check_user_is_set():
    """Tests the setting of the user if configured."""
    config = DockerSettings(user=None)
    generated_dockerfile = (
        PipelineDockerImageBuilder._generate_zenml_pipeline_dockerfile(
            "image:tag", config
        )
    )
    assert all(["USER" not in line for line in generated_dockerfile])

    config = DockerSettings(user="test_user")
    generated_dockerfile = (
        PipelineDockerImageBuilder._generate_zenml_pipeline_dockerfile(
            "image:tag", config
        )
    )
    assert "USER test_user" in generated_dockerfile


def test_requirements_file_generation(mocker, tmp_path: Path):
    """Tests that the requirements get included in the correct order and only
    when configured."""
    mocker.patch("subprocess.check_output", return_value=b"local_requirements")

    stack = Stack.default_local_stack()
    mocker.patch.object(
        stack, "requirements", return_value={"stack_requirements"}
    )

    # just local requirements
    settings = DockerSettings(
        install_stack_requirements=False,
        requirements=None,
        required_integrations=[],
        replicate_local_python_environment="pip_freeze",
    )
    files = PipelineDockerImageBuilder._gather_requirements_files(
        settings, stack=stack
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
    files = PipelineDockerImageBuilder._gather_requirements_files(
        settings, stack=stack
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
    files = PipelineDockerImageBuilder._gather_requirements_files(
        settings, stack=stack
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
    files = PipelineDockerImageBuilder._gather_requirements_files(
        settings, stack=stack
    )
    assert len(files) == 3
    # first up the local python requirements
    assert files[0][1] == "local_requirements"
    # then the user requirements
    assert files[1][1] == "user_requirements"
    # last the integration requirements
    expected_integration_requirements = "\n".join(
        sorted(SklearnIntegration.REQUIREMENTS + ["stack_requirements"])
    )
    assert files[2][1] == expected_integration_requirements
