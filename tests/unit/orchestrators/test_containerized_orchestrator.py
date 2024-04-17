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
from datetime import datetime
from typing import Optional
from uuid import uuid4

import pytest

from zenml.config import DockerSettings
from zenml.config.step_configurations import Step
from zenml.constants import ORCHESTRATOR_DOCKER_IMAGE_KEY
from zenml.enums import StackComponentType
from zenml.models import BuildItem, PipelineDeploymentBase
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.base_orchestrator import BaseOrchestratorConfig


class StubContainerizedOrchestrator(ContainerizedOrchestrator):
    def get_orchestrator_run_id(self) -> str:
        return ""

    def prepare_or_run_pipeline(self, deployment, stack):
        pass


def _get_orchestrator() -> StubContainerizedOrchestrator:
    return StubContainerizedOrchestrator(
        name="",
        id=uuid4(),
        config=BaseOrchestratorConfig(),
        flavor="stub",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _get_step(
    name: str, docker_settings: Optional[DockerSettings] = None
) -> Step:
    settings = {"docker": docker_settings} if docker_settings else {}
    return Step.model_validate(
        {
            "spec": {
                "source": "module.step_class",
                "upstream_steps": [],
                "inputs": {},
            },
            "config": {"name": "step_1", "settings": settings},
        }
    )


def test_builds_with_no_docker_settings():
    """Tests that only a generic pipeline build is returned when no step
    specifies custom Docker settings."""
    orchestrator = _get_orchestrator()

    deployment = PipelineDeploymentBase(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={
            "step_1": _get_step(name="step_1"),
            "step_2": _get_step(name="step_2"),
        },
        client_version="0.12.3",
        server_version="0.12.3",
    )

    builds = orchestrator.get_docker_builds(deployment=deployment)
    assert len(builds) == 1
    build = builds[0]
    assert build.key == "orchestrator"
    assert build.step_name is None
    assert build.entrypoint is None
    assert build.extra_files == {}
    assert build.settings == DockerSettings()


def test_builds_with_custom_docker_settings_for_some_steps():
    """Tests that steps with custom Docker settings get their own build and
    the remaining steps use a shared pipeline image."""
    orchestrator = _get_orchestrator()
    custom_step_1_settings = DockerSettings(
        requirements=["step_1_requirements"]
    )
    deployment = PipelineDeploymentBase(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={
            "step_1": _get_step(
                name="step_1", docker_settings=custom_step_1_settings
            ),
            "step_2": _get_step(name="step_2"),
        },
        client_version="0.12.3",
        server_version="0.12.3",
    )

    builds = orchestrator.get_docker_builds(deployment=deployment)
    assert len(builds) == 2
    step_1_build = builds[0]
    assert step_1_build.key == "orchestrator"
    assert step_1_build.step_name == "step_1"
    assert step_1_build.settings == custom_step_1_settings

    pipeline_build = builds[1]
    assert pipeline_build.key == "orchestrator"
    assert pipeline_build.step_name is None
    assert pipeline_build.settings == DockerSettings()


def test_builds_with_custom_docker_settings_for_all_steps():
    """Tests that no generic pipeline image is built if all steps specify their
    custom Docker settings."""
    orchestrator = _get_orchestrator()
    custom_step_1_settings = DockerSettings(
        requirements=["step_1_requirements"]
    )
    custom_step_2_settings = DockerSettings(
        requirements=["step_2_requirements"]
    )
    deployment = PipelineDeploymentBase(
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        step_configurations={
            "step_1": _get_step(
                name="step_1", docker_settings=custom_step_1_settings
            ),
            "step_2": _get_step(
                name="step_2", docker_settings=custom_step_2_settings
            ),
        },
        client_version="0.12.3",
        server_version="0.12.3",
    )

    builds = orchestrator.get_docker_builds(deployment=deployment)
    assert len(builds) == 2
    step_1_build = builds[0]
    assert step_1_build.key == "orchestrator"
    assert step_1_build.step_name == "step_1"
    assert step_1_build.settings == custom_step_1_settings

    step_2_build = builds[1]
    assert step_2_build.key == "orchestrator"
    assert step_2_build.step_name == "step_2"
    assert step_2_build.settings == custom_step_2_settings


def test_getting_image_from_deployment(
    sample_deployment_response_model, sample_build_response_model
):
    """Tests getting the image from a deployment."""
    assert not sample_deployment_response_model.build
    with pytest.raises(RuntimeError):
        # Missing build in deployment
        ContainerizedOrchestrator.get_image(
            deployment=sample_deployment_response_model
        )

    sample_deployment_response_model.metadata.build = (
        sample_build_response_model
    )
    assert not sample_build_response_model.images

    with pytest.raises(KeyError):
        # Missing the image in build
        ContainerizedOrchestrator.get_image(
            deployment=sample_deployment_response_model
        )

    sample_build_response_model.metadata.images = {
        ORCHESTRATOR_DOCKER_IMAGE_KEY: BuildItem(image="image_name")
    }
    assert (
        ContainerizedOrchestrator.get_image(
            deployment=sample_deployment_response_model
        )
        == "image_name"
    )
