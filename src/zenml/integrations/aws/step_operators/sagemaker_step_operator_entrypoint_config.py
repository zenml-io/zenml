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
"""Entrypoint configuration for ZenML Sagemaker step operator."""

from zenml.step_operators.step_operator_entrypoint_configuration import (
    StepOperatorEntrypointConfiguration,
)
from zenml.utils.env_utils import reconstruct_environment_variables

SAGEMAKER_ESTIMATOR_STEP_ENV_VAR_SIZE_LIMIT = 512


class SagemakerEntrypointConfiguration(StepOperatorEntrypointConfiguration):
    """Entrypoint configuration for ZenML Sagemaker step operator.

    The only purpose of this entrypoint configuration is to reconstruct the
    environment variables that exceed the maximum length of 512 characters
    allowed for Sagemaker Estimator steps from their individual components.
    """

    def run(self) -> None:
        """Runs the step."""
        # Reconstruct the environment variables that exceed the maximum length
        # of 512 characters from their individual chunks
        reconstruct_environment_variables()

        # Run the step
        super().run()
