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
from typing import Generator, Optional, Tuple
from uuid import UUID

import pytest

from zenml.services import (
    BaseService,
    ServiceConfig,
    ServiceState,
    ServiceStatus,
)
from zenml.services.service import ZENM_ENDPOINT_PREFIX


# Create a concrete subclass of BaseService
class TestService(BaseService):
    """Test service class for testing BaseService."""

    SERVICE_TYPE = {
        "type": "model-serving",
        "flavor": "test_flavor",
        "name": "test_name",
    }

    @property
    def is_running(self):
        return True

    @property
    def is_stopped(self):
        return not self.is_running

    @property
    def is_failed(self):
        return False

    def check_status(self) -> Tuple[ServiceState, str]:
        return ServiceState.ACTIVE, "Service is running"

    def get_logs(
        self, follow: bool = False, tail: Optional[int] = None
    ) -> Generator[str, bool, None]:
        return (f"log line {i}" for i in range(5))


# Modify the base_service fixture to use the TestService subclass
@pytest.fixture
def base_service():
    return TestService(
        uuid=UUID("12345678-1234-5678-1234-567812345678"),
        admin_state=ServiceState.ACTIVE,
        config=ServiceConfig(name="test_service", param1="value1", param2=2),
        status=ServiceStatus(
            state=ServiceState.ACTIVE,
            last_error="",
            last_status=ServiceState.INACTIVE,
        ),
        endpoint=None,
    )


# Update the test_from_model to handle the case when service_source is missing
def test_from_model(service_response):
    service = BaseService.from_model(service_response)
    assert isinstance(service, TestService)
    assert service.uuid == service_response.id
    assert service.admin_state == service_response.admin_state
    assert dict(service.config) == service_response.config
    assert dict(service.status) == service_response.status
    assert service.SERVICE_TYPE["type"] == service_response.service_type.type
    assert (
        service.SERVICE_TYPE["flavor"] == service_response.service_type.flavor
    )
    assert service.endpoint == service_response.endpoint


def test_update_status(base_service, monkeypatch):
    def mock_check_status(self):
        return ServiceState.ACTIVE, "Service is running"

    monkeypatch.setattr(BaseService, "check_status", mock_check_status)
    base_service.update_status()

    assert base_service.status.state == ServiceState.ACTIVE
    assert base_service.status.last_error == "Service is running"


def test_service_config_init_without_name_or_model_name():
    """Test initialization without name or model_name."""
    with pytest.raises(ValueError) as excinfo:
        ServiceConfig()
    assert "Either 'name' or 'model_name' must be set." in str(excinfo.value)


def test_service_config_init_with_name():
    """Test initialization with name."""
    config = ServiceConfig(name="test-service")
    assert config.name == "test-service"
    assert config.service_name == f"{ZENM_ENDPOINT_PREFIX}test-service"
