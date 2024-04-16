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
"""Endpoint definitions for server analytics."""

from fastapi import APIRouter, Security

from zenml.constants import ACTION, API, VERSION_1, GENERATE_HISTOGRAM
from zenml.enums import DurationType
from zenml.models import (
    ArtifactFilter,
    ArtifactVersionFilter,
    CodeRepositoryFilter,
    ComponentFilter,
    EventSourceFilter,
    FlavorFilter,
    ModelFilter,
    ModelVersionFilter,
    PipelineBuildFilter,
    PipelineDeploymentFilter,
    PipelineFilter,
    PipelineRunFilter,
    ReportRequest,
    ReportResponse,
    RunMetadataFilter,
    SecretFilter,
    ServiceAccountFilter,
    ServiceConnectorFilter,
    ServiceFilter,
    StackFilter,
    TagFilter,
    TriggerExecutionFilter,
    TriggerFilter,
    UserFilter,
    WorkspaceFilter,
)
from zenml.zen_server.auth import AuthContext, authorize, get_auth_context
from zenml.zen_server.exceptions import error_response
from zenml.zen_server.rbac.models import ResourceType
from zenml.zen_server.rbac.utils import (
    get_allowed_resource_ids,
)
from zenml.zen_server.utils import handle_exceptions, zen_store

ResourceTypeFilterMapping = {
    ResourceType.ARTIFACT: ArtifactFilter,
    ResourceType.ARTIFACT_VERSION: ArtifactVersionFilter,
    ResourceType.CODE_REPOSITORY: CodeRepositoryFilter,
    ResourceType.EVENT_SOURCE: EventSourceFilter,
    ResourceType.FLAVOR: FlavorFilter,
    ResourceType.MODEL: ModelFilter,
    ResourceType.MODEL_VERSION: ModelVersionFilter,
    ResourceType.PIPELINE: PipelineFilter,
    ResourceType.PIPELINE_RUN: PipelineRunFilter,
    ResourceType.PIPELINE_DEPLOYMENT: PipelineDeploymentFilter,
    ResourceType.PIPELINE_BUILD: PipelineBuildFilter,
    ResourceType.USER: UserFilter,
    ResourceType.SERVICE: ServiceFilter,
    ResourceType.RUN_METADATA: RunMetadataFilter,
    ResourceType.SECRET: SecretFilter,
    ResourceType.SERVICE_ACCOUNT: ServiceAccountFilter,
    ResourceType.SERVICE_CONNECTOR: ServiceConnectorFilter,
    ResourceType.STACK: StackFilter,
    ResourceType.STACK_COMPONENT: ComponentFilter,
    ResourceType.TAG: TagFilter,
    ResourceType.TRIGGER: TriggerFilter,
    ResourceType.TRIGGER_EXECUTION: TriggerExecutionFilter,
    ResourceType.WORKSPACE: WorkspaceFilter,
}

router = APIRouter(
    prefix=API + VERSION_1 + ACTION,
    tags=["action"],
    responses={401: error_response, 403: error_response},
)


@router.get(
    GENERATE_HISTOGRAM,
    response_model=ReportResponse,
    responses={401: error_response, 404: error_response, 422: error_response},
)
@handle_exceptions
def generate_histogram(
    duration_length: int,
    duration_type: DurationType,
    resource_type: ResourceType,
    _: AuthContext = Security(authorize),
) -> ReportResponse:
    """Generate a histogram for the creation a specific type of entities.

    This histogram tells you how many total entries of a specific type are
    created in a certain time period and also breaks it down by the type.

    For instance:

    A user runs a pipeline on 23.09.2024 and two pipelines 24.10.2024. If he
    requests a pipeline run report on 25.11.2024, the outputs will be as follows
    based on the input values:

    duration_type: "days" duration_length: "90"
        {"total": 2, "results": {"23.09.2024": 1, "24.10.2024": 1}}

    duration_type: "months" duration_length: "1"
        {"total": 1, "results": {"10.2024": 1}}

    duration_type: "years" duration_length: "3"
        {"total": 2, "results": {"2024": 2}}

    Args:
        duration_type: type of the duration to base the report in. You need
            to set it to the associated `ResourceType`. Supported formats
            include: minute, hour, day, month and year.
        duration_length: the amount of times to repeat the duration while
            generating the report.
        resource_type: the type of the entity to create the report for.
        _:

    Returns:
        The resulting report.
    """
    # Check the auth context
    auth_context = get_auth_context()
    assert auth_context

    # Get the correct filter and apply RBAC
    allowed_ids = get_allowed_resource_ids(resource_type=resource_type)
    filter_model = ResourceTypeFilterMapping[resource_type]()
    filter_model.configure_rbac(
        authenticated_user_id=auth_context.user.id, id=allowed_ids
    )

    # Create the request model
    report_request = ReportRequest(
        duration_type=duration_type,
        duration_length=duration_length,
    )

    # Generate report
    return zen_store().generate_histogram(
        filter_model=filter_model,
        report_request=report_request,
        resource_type=resource_type,
    )
