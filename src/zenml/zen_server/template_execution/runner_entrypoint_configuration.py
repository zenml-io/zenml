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
"""Runner entrypoint configuration."""

from zenml.client import Client
from zenml.entrypoints.base_entrypoint_configuration import (
    BaseEntrypointConfiguration,
)
from zenml.pipelines.run_utils import deploy_pipeline, get_placeholder_run


class RunnerEntrypointConfiguration(BaseEntrypointConfiguration):
    """Runner entrypoint configuration."""

    def run(self) -> None:
        """Run the entrypoint configuration.

        This method runs the pipeline defined by the deployment given as input
        to the entrypoint configuration.
        """
        deployment = self.load_deployment()

        stack = Client().active_stack
        assert deployment.stack and stack.id == deployment.stack.id

        placeholder_run = get_placeholder_run(deployment_id=deployment.id)
        deploy_pipeline(
            deployment=deployment,
            stack=stack,
            placeholder_run=placeholder_run,
        )
