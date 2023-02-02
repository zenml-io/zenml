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

from typing import cast
import pytest

from tests.integration.examples.utils import run_example
from zenml.client import Client
from zenml.integrations.seldon.model_deployers.seldon_model_deployer import (
    SeldonModelDeployer,
)
from zenml.integrations.seldon.services.seldon_deployment import (
    SeldonDeploymentService,
)
from zenml.post_execution.pipeline import get_pipeline


def test_example(request: pytest.FixtureRequest) -> None:
    """Runs the seldon_deployment example.

    Args:
        tmp_path_factory: Factory to generate temporary test paths.
    """
    with run_example(
        request=request,
        name="seldon_deployment",
        pipeline_name="continuous_deployment_pipeline",
        run_count=1,
    ) as (example, _):

        pipeline = get_pipeline("continuous_deployment_pipeline")
        assert pipeline

        # activate the stack set up and used by the example
        client = Client()
        model_deployer = client.active_stack.model_deployer
        assert isinstance(model_deployer, SeldonModelDeployer)

        services = model_deployer.find_model_server(
            pipeline_name="continuous_deployment_pipeline",
            pipeline_step_name="seldon_model_deployer_step",
        )

        assert services
        service = cast(SeldonDeploymentService, services[0])
        assert service.is_running
