#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Utility methods for Service Connectors."""

from typing import Dict, List, Union
from uuid import UUID

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.models.v2.core.service_connector import ServiceConnectorRequest
from zenml.models.v2.misc.full_stack import (
    ResourcesInfo,
    ServiceConnectorInfo,
    ServiceConnectorResourcesInfo,
)
from zenml.utils.pagination_utils import depaginate


def _prepare_resource_info(
    connector_details: Union[UUID, ServiceConnectorInfo],
    resource_ids: List[str],
    stack_component_type: StackComponentType,
    flavor: str,
    required_configuration: Dict[str, str],
    flavor_display_name: str,
    use_resource_value_as_fixed_config: bool = False,
) -> ResourcesInfo:
    existing_components = []
    if isinstance(connector_details, UUID):
        existing_components = depaginate(
            Client().list_stack_components,
            type=stack_component_type.value,
            connector_id=connector_details,
            flavor=flavor,
        )
    return ResourcesInfo(
        flavor=flavor,
        required_configuration=required_configuration,
        flavor_display_name=flavor_display_name,
        use_resource_value_as_fixed_config=use_resource_value_as_fixed_config,
        accessible_by_service_connector=resource_ids,
        connected_through_service_connector=existing_components,
    )


def _raise_specific_cloud_exception_if_needed(
    cloud_provider: str,
    artifact_stores: List[ResourcesInfo],
    orchestrators: List[ResourcesInfo],
    container_registries: List[ResourcesInfo],
) -> None:
    AWS_DOCS = (
        "https://docs.zenml.io/how-to/auth-management/aws-service-connector"
    )
    GCP_DOCS = (
        "https://docs.zenml.io/how-to/auth-management/gcp-service-connector"
    )

    if not artifact_stores:
        error_msg = (
            "We were unable to find any {obj_name} available "
            "to configured service connector. Please, verify "
            "that needed permission are granted for the "
            "service connector.\nDocumentation for the "
            "{obj_name} configuration can be found at "
            "{docs}"
        )
        if cloud_provider == "aws":
            raise ValueError(
                error_msg.format(
                    obj_name="S3 Bucket", docs=f"{AWS_DOCS}#s3-bucket"
                )
            )
        elif cloud_provider == "gcp":
            raise ValueError(
                error_msg.format(
                    obj_name="GCS Bucket", docs=f"{GCP_DOCS}#gcs-bucket"
                )
            )
        elif cloud_provider == "azure":
            pass
    if not orchestrators:
        error_msg = (
            "We were unable to find any orchestrator engines "
            "available to the service connector. Please, verify "
            "that needed permission are granted for the "
            "service connector.\nDocumentation for the Generic "
            "{cloud_name} resource configuration can be found at "
            "{gen_docs}\n Documentation for the {k8s_name} resource "
            "configuration can be found at {k8s_docs}"
        )
        if cloud_provider == "aws":
            raise ValueError(
                error_msg.format(
                    cloud_name="AWS",
                    gen_docs=f"{AWS_DOCS}#generic-aws-resource",
                    k8s_name="Kubernetes",
                    k8s_docs=f"{AWS_DOCS}#eks-kubernetes-cluster",
                )
            )

        elif cloud_provider == "gcp":
            raise ValueError(
                error_msg.format(
                    cloud_name="GCP",
                    gen_docs=f"{GCP_DOCS}#generic-gcp-resource",
                    k8s_name="GKE Kubernetes",
                    k8s_docs=f"{GCP_DOCS}#gke-kubernetes-cluster",
                )
            )
        elif cloud_provider == "azure":
            pass
    if not container_registries:
        error_msg = (
            "We were unable to find any container registries "
            "available to the service connector. Please, verify "
            "that needed permission are granted for the "
            "service connector.\nDocumentation for the {registry_name} "
            "container registry resource configuration can "
            "be found at {docs_link}"
        )
        if cloud_provider == "aws":
            raise ValueError(
                error_msg.format(
                    registry_name="ECR",
                    docs_link=f"{AWS_DOCS}#ecr-container-registry",
                )
            )
        elif cloud_provider == "gcp":
            raise ValueError(
                error_msg.format(
                    registry_name="GCR",
                    docs_link=f"{GCP_DOCS}#gcr-container-registry",
                )
            )
        elif cloud_provider == "azure":
            pass


def get_resources_options_from_resource_model_for_full_stack(
    connector_details: Union[UUID, ServiceConnectorInfo],
) -> ServiceConnectorResourcesInfo:
    """Get the resource options from the resource model for the full stack.

    Args:
        connector_details: The service connector details (UUID or Info).

    Returns:
        All available service connector resource options.
    """
    client = Client()
    zen_store = client.zen_store

    can_generate_long_tokens = False
    if isinstance(connector_details, UUID):
        resource_model = zen_store.verify_service_connector(
            connector_details,
            list_resources=True,
        )
        can_generate_long_tokens = not zen_store.get_service_connector(
            connector_details
        ).configuration.get("generate_temporary_tokens", True)
    else:
        resource_model = zen_store.verify_service_connector_config(
            service_connector=ServiceConnectorRequest(
                user=client.active_user.id,
                workspace=client.active_workspace.id,
                name="fake",
                connector_type=connector_details.type,
                auth_method=connector_details.auth_method,
                configuration=connector_details.configuration,
                secrets={},
                labels={},
            ),
            list_resources=True,
        )
        can_generate_long_tokens = True

    resources = resource_model.resources

    if isinstance(
        resource_model.connector_type,
        str,
    ):
        connector_type = resource_model.connector_type
    else:
        connector_type = resource_model.connector_type.connector_type

    artifact_stores: List[ResourcesInfo] = []
    orchestrators: List[ResourcesInfo] = []
    container_registries: List[ResourcesInfo] = []

    if connector_type == "aws":
        for each in resources:
            if each.resource_ids:
                if each.resource_type == "s3-bucket":
                    artifact_stores.append(
                        _prepare_resource_info(
                            connector_details=connector_details,
                            resource_ids=each.resource_ids,
                            stack_component_type=StackComponentType.ARTIFACT_STORE,
                            flavor="s3",
                            required_configuration={"path": "Path"},
                            use_resource_value_as_fixed_config=True,
                            flavor_display_name="S3 Bucket",
                        )
                    )
                if each.resource_type == "aws-generic":
                    orchestrators.append(
                        _prepare_resource_info(
                            connector_details=connector_details,
                            resource_ids=each.resource_ids,
                            stack_component_type=StackComponentType.ORCHESTRATOR,
                            flavor="sagemaker",
                            required_configuration={
                                "execution_role": "execution role ARN"
                            },
                            flavor_display_name="AWS Sagemaker",
                        )
                    )
                    if can_generate_long_tokens:
                        orchestrators.append(
                            _prepare_resource_info(
                                connector_details=connector_details,
                                resource_ids=each.resource_ids,
                                stack_component_type=StackComponentType.ORCHESTRATOR,
                                flavor="vm_aws",
                                required_configuration={"region": "region"},
                                use_resource_value_as_fixed_config=True,
                                flavor_display_name="Skypilot (EC2)",
                            )
                        )

                if each.resource_type == "kubernetes-cluster":
                    orchestrators.append(
                        _prepare_resource_info(
                            connector_details=connector_details,
                            resource_ids=each.resource_ids,
                            stack_component_type=StackComponentType.ORCHESTRATOR,
                            flavor="kubernetes",
                            required_configuration={},
                            flavor_display_name="Kubernetes",
                        )
                    )
                if each.resource_type == "docker-registry":
                    container_registries.append(
                        _prepare_resource_info(
                            connector_details=connector_details,
                            resource_ids=each.resource_ids,
                            stack_component_type=StackComponentType.CONTAINER_REGISTRY,
                            flavor="aws",
                            required_configuration={"uri": "URI"},
                            use_resource_value_as_fixed_config=True,
                            flavor_display_name="ECR",
                        )
                    )

    elif connector_type == "gcp":
        for each in resources:
            if each.resource_ids:
                if each.resource_type == "gcs-bucket":
                    artifact_stores.append(
                        _prepare_resource_info(
                            connector_details=connector_details,
                            resource_ids=each.resource_ids,
                            stack_component_type=StackComponentType.ARTIFACT_STORE,
                            flavor="gcp",
                            required_configuration={},
                            flavor_display_name="GCS Bucket",
                        )
                    )
                if each.resource_type == "gcp-generic":
                    orchestrators.append(
                        _prepare_resource_info(
                            connector_details=connector_details,
                            resource_ids=each.resource_ids,
                            stack_component_type=StackComponentType.ORCHESTRATOR,
                            flavor="vertex",
                            required_configuration={"location": "region name"},
                            flavor_display_name="Vertex AI",
                        )
                    )
                    if can_generate_long_tokens:
                        orchestrators.append(
                            _prepare_resource_info(
                                connector_details=connector_details,
                                resource_ids=each.resource_ids,
                                stack_component_type=StackComponentType.ORCHESTRATOR,
                                flavor="vm_gcp",
                                required_configuration={
                                    "region": "region name"
                                },
                                flavor_display_name="Skypilot (Compute)",
                            )
                        )

                if each.resource_type == "kubernetes-cluster":
                    orchestrators.append(
                        _prepare_resource_info(
                            connector_details=connector_details,
                            resource_ids=each.resource_ids,
                            stack_component_type=StackComponentType.ORCHESTRATOR,
                            flavor="kubernetes",
                            required_configuration={},
                            flavor_display_name="Kubernetes",
                        )
                    )
                if each.resource_type == "docker-registry":
                    container_registries.append(
                        _prepare_resource_info(
                            connector_details=connector_details,
                            resource_ids=each.resource_ids,
                            stack_component_type=StackComponentType.CONTAINER_REGISTRY,
                            flavor="gcp",
                            required_configuration={"uri": "URI"},
                            use_resource_value_as_fixed_config=True,
                            flavor_display_name="GCR",
                        )
                    )

    elif connector_type == "azure":
        pass

    _raise_specific_cloud_exception_if_needed(
        cloud_provider=connector_type,
        artifact_stores=artifact_stores,
        orchestrators=orchestrators,
        container_registries=container_registries,
    )

    return ServiceConnectorResourcesInfo(
        connector_type=connector_type,
        components_resources_info={
            StackComponentType.ARTIFACT_STORE: artifact_stores,
            StackComponentType.ORCHESTRATOR: orchestrators,
            StackComponentType.CONTAINER_REGISTRY: container_registries,
        },
    )
