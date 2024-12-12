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

import json
from contextlib import ExitStack as does_not_raise
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.enums import StackComponentType
from zenml.exceptions import StackValidationError
from zenml.stack import Stack

if TYPE_CHECKING:
    pass


def _get_vertex_orchestrator(**kwargs):
    from zenml.integrations.gcp.flavors.vertex_orchestrator_flavor import (
        VertexOrchestratorConfig,
    )
    from zenml.integrations.gcp.orchestrators import VertexOrchestrator

    return VertexOrchestrator(
        name="",
        id=uuid4(),
        config=VertexOrchestratorConfig(**kwargs),
        flavor="gcp",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def test_vertex_orchestrator_stack_validation(
    local_artifact_store,
    gcp_artifact_store,
    local_container_registry,
    remote_container_registry,
) -> None:
    """Tests that the vertex orchestrator validates that it's stack has a container registry and that all stack components used are not local."""
    from zenml.integrations.azure.artifact_stores import AzureArtifactStore
    from zenml.integrations.azure.flavors.azure_artifact_store_flavor import (
        AzureArtifactStoreConfig,
    )

    orchestrator = _get_vertex_orchestrator(
        location="europe-west4",
        pipeline_root="gs://my-bucket/pipeline",
    )
    orchestrator_no_pipeline_root = _get_vertex_orchestrator(
        location="europe-west4"
    )

    gcp_container_registry = remote_container_registry

    azure_artifact_store = AzureArtifactStore(
        name="azure_artifact_store",
        id=uuid4(),
        config=AzureArtifactStoreConfig(path="abfs://my-container/artifacts"),
        flavor="azure",
        type=StackComponentType.ARTIFACT_STORE,
        user=uuid4(),
        workspace=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )

    with pytest.raises(StackValidationError):
        # any stack component is local
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=local_artifact_store,
            container_registry=gcp_container_registry,
        ).validate()

    with pytest.raises(StackValidationError):
        # missing container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=gcp_artifact_store,
        ).validate()

    with pytest.raises(StackValidationError):
        # container registry is local
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=gcp_artifact_store,
            container_registry=local_container_registry,
        ).validate()

    with pytest.raises(StackValidationError):
        # `pipeline_root` was not set and the artifact store is not a `GCPArtifactStore`
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator_no_pipeline_root,
            artifact_store=azure_artifact_store,
            container_registry=gcp_container_registry,
        ).validate()

    with does_not_raise():
        # valid stack with container registry
        Stack(
            id=uuid4(),
            name="",
            orchestrator=orchestrator,
            artifact_store=gcp_artifact_store,
            container_registry=gcp_container_registry,
        ).validate()


@pytest.mark.parametrize(
    "resource_settings, orchestrator_resource_settings, expected_resources",
    [
        # ResourceSettings specified for the step, should take values from here
        (
            ResourceSettings(cpu_count=1, gpu_count=1, memory="1GB"),
            {"cpu_limit": "4", "gpu_limit": 4, "memory_limit": "1G"},
            {
                "accelerator": {
                    "count": "1",
                    "type": "NVIDIA_TESLA_K80",
                },
                "cpuLimit": 1.0,
                "memoryLimit": 1.0,
            },
        ),
        # No ResourceSettings, should take values from the orchestrator
        (
            ResourceSettings(cpu_count=None, gpu_count=None, memory=None),
            {"cpu_limit": "1.0", "gpu_limit": 1, "memory_limit": "1G"},
            {
                "accelerator": {
                    "count": "1",
                    "type": "NVIDIA_TESLA_K80",
                },
                "cpuLimit": 1.0,
                "memoryLimit": 1.0,
            },
        ),
        # GPU count is None, 1 gpu should be used (KFP default)
        (
            ResourceSettings(cpu_count=1, gpu_count=None, memory="1GB"),
            {"cpu_limit": None, "gpu_limit": None, "memory_limit": None},
            {
                "cpuLimit": 1.0,
                "memoryLimit": 1.0,
            },
        ),
        # GPU count is 0, should not be set in the resource spec
        (
            ResourceSettings(cpu_count=1, gpu_count=0, memory="1GB"),
            {"cpu_limit": None, "gpu_limit": None, "memory_limit": None},
            {"cpuLimit": 1.0, "memoryLimit": 1.0},
        ),
    ],
)
def test_vertex_orchestrator_configure_container_resources(
    resource_settings: ResourceSettings,
    orchestrator_resource_settings: dict,
    expected_resources: dict,
) -> None:
    """Tests that the vertex orchestrator sets the correct container resources for a step."""
    import kfp
    from kfp.compiler import Compiler

    accelerator = "NVIDIA_TESLA_K80"
    orchestrator = _get_vertex_orchestrator(
        location="europe-west4",
        pipeline_root="gs://my-bucket/pipeline",
        node_selector_constraint=(
            "cloud.google.com/gke-accelerator",
            accelerator,
        ),
        **orchestrator_resource_settings,
    )

    step_name = "unit-test"

    @kfp.dsl.pipeline(  # type: ignore[misc]
        display_name="test-vertex-pipeline",
    )
    def _build_kfp_pipeline() -> None:
        container_op = kfp.components.load_component_from_text(
            f"""
            name: {step_name}
            implementation:
                container:
                    image: hello-world
            """
        )()

        orchestrator._configure_container_resources(
            container_op,
            resource_settings,
            node_selector_constraint=orchestrator.config.node_selector_constraint,
        )

    package_path = "unit_test_pipeline.json"

    Compiler().compile(
        pipeline_func=_build_kfp_pipeline,
        package_path=package_path,
        pipeline_name="unit-test",
    )

    with open(package_path, "r") as f:
        pipeline_json = json.load(f)

    job_spec = pipeline_json["deploymentSpec"]["executors"][
        f"exec-{step_name}"
    ]["container"]
    if "accelerator" in job_spec["resources"]:
        if "count" in job_spec["resources"]["accelerator"]:
            expected_resources["accelerator"]["count"] = expected_resources[
                "accelerator"
            ]["count"]
        if "type" in job_spec["resources"]["accelerator"]:
            expected_resources["accelerator"]["type"] = expected_resources[
                "accelerator"
            ]["type"]
    assert job_spec["resources"] == expected_resources
