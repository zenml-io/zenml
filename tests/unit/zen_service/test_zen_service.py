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
import platform
import random

import pytest
import requests

from zenml.constants import STACK_CONFIGURATIONS, STACKS
from zenml.services import ServiceState
from zenml.zen_service.zen_service import ZenService, ZenServiceConfig


@pytest.fixture
def running_zen_service() -> ZenService:
    """Spin up a zen service to do tests on."""
    port = random.randint(8003, 9000)
    zen_service = ZenService(
        ZenServiceConfig(
            port=port,
        )
    )
    zen_service.start(timeout=10)
    yield zen_service
    zen_service.stop(timeout=10)
    assert zen_service.check_status()[0] == ServiceState.INACTIVE


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenService not supported as daemon on Windows.",
)
def test_get_stack_endpoints(running_zen_service: ZenService):
    """Test that the stack methods behave as they should."""
    endpoint = running_zen_service.endpoint.status.uri.strip("/")
    stacks_response = requests.get(endpoint + STACKS)
    assert stacks_response.status_code == 200
    assert isinstance(stacks_response.json(), (list, tuple))
    assert len(stacks_response.json()) == 1

    configs_response = requests.get(endpoint + STACK_CONFIGURATIONS)
    assert configs_response.status_code == 200
    assert isinstance(configs_response.json(), dict)
    assert len(configs_response.json()) == 1


@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenService not supported as daemon on Windows.",
)
def test_service_up_down():
    """Test spinning up and shutting down Zen service."""
    port = random.randint(8003, 9000)
    zen_service = ZenService(
        ZenServiceConfig(
            port=port,
        )
    )
    endpoint = f"http://localhost:{port}/"
    try:
        zen_service.start(timeout=10)
        assert zen_service.check_status()[0] == ServiceState.ACTIVE
        assert zen_service.endpoint.status.uri == endpoint
        assert requests.head(endpoint + "health").status_code == 200
    finally:
        zen_service.stop(timeout=10)
    assert zen_service.check_status()[0] == ServiceState.INACTIVE
