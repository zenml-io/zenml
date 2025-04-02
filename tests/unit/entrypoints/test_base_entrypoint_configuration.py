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

from contextlib import ExitStack as does_not_raise
from uuid import uuid4

import pytest

from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.models import PipelineDeploymentRequest


class StubEntrypointConfiguration(BaseEntrypointConfiguration):
    def run(self) -> None:
        pass


def test_calling_entrypoint_configuration_with_invalid_deployment_id():
    """Tests that a valid deployment ID is required as argument."""
    with pytest.raises(ValueError):
        BaseEntrypointConfiguration.get_entrypoint_arguments()

    with pytest.raises(ValueError):
        BaseEntrypointConfiguration.get_entrypoint_arguments(
            deployment_id="not_a_uuid"
        )

    with does_not_raise():
        BaseEntrypointConfiguration.get_entrypoint_arguments(
            deployment_id=uuid4()
        )


def test_loading_the_deployment(clean_client):
    """Tests loading the deployment by ID."""
    request = PipelineDeploymentRequest(
        user=clean_client.active_user.id,
        project=clean_client.active_project.id,
        run_name_template="",
        pipeline_configuration={"name": "pipeline"},
        stack=clean_client.active_stack.id,
        client_version="0.12.3",
        server_version="0.12.3",
    )

    deployment = clean_client.zen_store.create_deployment(request)

    entrypoint_config = StubEntrypointConfiguration(
        arguments=["--deployment_id", str(deployment.id)]
    )

    assert entrypoint_config.load_deployment() == deployment
