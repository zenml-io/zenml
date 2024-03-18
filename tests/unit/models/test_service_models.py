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

import pytest

from zenml.constants import STR_FIELD_MAX_LENGTH
from zenml.models import (
    ServiceRequest,
    ServiceResponse,
    ServiceResponseBody,
    ServiceResponseMetadata,
)
from zenml.services.service_status import ServiceState
from zenml.services.service_type import ServiceType

# Test data
service_id = "12345678-1234-5678-1234-567812345678"
service_name = "test_service"
service_type = ServiceType(
    type="model-serving", flavor="test_flavor", name="test_name"
)
service_source = "tests.unit.services.test_service.TestService"
admin_state = ServiceState.ACTIVE
config = {
    "type": "zenml.services.service.ServiceConfig",
    "name": "test_service",
    "description": "",
    "pipeline_name": "",
    "pipeline_step_name": "",
    "model_name": "",
    "model_version": "",
    "service_name": "zenml-test_service",
}
labels = {"label1": "value1", "label2": "value2"}
status = {
    "type": "zenml.services.service_status.ServiceStatus",
    "state": ServiceState.ACTIVE,
    "last_state": ServiceState.INACTIVE,
    "last_error": "",
}
endpoint = None
prediction_url = "http://example.com/predict"
health_check_url = "http://example.com/health"
created_time = datetime(2023, 3, 14, 10, 30)
updated_time = datetime(2023, 3, 14, 11, 45)


@pytest.fixture
def service_response(
    sample_workspace_model,
):
    body = ServiceResponseBody(
        service_type=service_type,
        labels=labels,
        created=created_time,
        updated=updated_time,
        state=admin_state,
    )
    metadata = ServiceResponseMetadata(
        service_source=service_source,
        admin_state=admin_state,
        config=config,
        status=status,
        endpoint=endpoint,
        prediction_url=prediction_url,
        health_check_url=health_check_url,
        workspace=sample_workspace_model,
    )
    return ServiceResponse(
        id=service_id,
        name=service_name,
        body=body,
        metadata=metadata,
    )


def test_service_response_properties(service_response):
    assert service_response.service_type == service_type
    assert service_response.labels == labels
    assert service_response.service_source == service_source
    assert service_response.config == config
    assert service_response.status == status
    assert service_response.endpoint == endpoint
    assert service_response.created == created_time
    assert service_response.updated == updated_time
    assert service_response.admin_state == admin_state
    assert service_response.prediction_url == prediction_url
    assert service_response.health_check_url == health_check_url
    assert service_response.state == admin_state


def test_service_request_name_too_long():
    # Test that the service name cannot be longer than the maximum allowed length
    long_name = "a" * (STR_FIELD_MAX_LENGTH + 1)
    with pytest.raises(ValueError):
        ServiceRequest(
            name=long_name,
            service_type=ServiceType(
                type="model-serving", flavor="test_flavor", name="test_name"
            ),
            service_source="path.to.ServiceClass",
            admin_state=ServiceState.ACTIVE,
            config={"param1": "value1"},
        )


def test_service_request_invalid_service_type():
    # Test that an invalid service type raises an error
    invalid_service_type = "invalid_type"
    with pytest.raises(ValueError):
        ServiceRequest(
            name="test_service",
            service_type=invalid_service_type,
            service_source="path.to.ServiceClass",
            admin_state=ServiceState.ACTIVE,
            config={"param1": "value1"},
        )
