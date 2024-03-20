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

import pytest

from tests.integration.examples.utils import run_example
from zenml.client import Client


def test_huggingface_deployment(request: pytest.FixtureRequest) -> None:
    """Runs the huggingface deployment and inference example."""

    with run_example(
        request=request,
        name="huggingface",
        example_args=["--task", "deployment"],
        pipelines={"huggingface_deployment_pipeline": (1, 2)},
    ):
        from zenml.integrations.huggingface.model_deployers.huggingface_model_deployer import (
            HuggingFaceModelDeployer,
        )

        client = Client()
        pipeline = client.get_pipeline("huggingface_deployment_pipeline")
        assert pipeline

        # get the active model deployer used by the example
        model_deployer = client.active_stack.model_deployer
        assert isinstance(model_deployer, HuggingFaceModelDeployer)
