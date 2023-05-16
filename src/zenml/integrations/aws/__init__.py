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
"""Integrates multiple AWS Tools as Stack Components.

The AWS integration provides a way for our users to manage their secrets
through AWS, a way to use the aws container registry. Additionally, the
Sagemaker integration submodule provides a way to run ZenML steps in
Sagemaker.
"""
from typing import List, Type

from zenml.integrations.constants import AWS
from zenml.integrations.integration import Integration
from zenml.stack import Flavor

AWS_SECRET_MANAGER_FLAVOR = "aws"
AWS_CONTAINER_REGISTRY_FLAVOR = "aws"
AWS_SAGEMAKER_STEP_OPERATOR_FLAVOR = "sagemaker"
AWS_SAGEMAKER_ORCHESTRATOR_FLAVOR = "sagemaker"


class AWSIntegration(Integration):
    """Definition of AWS integration for ZenML."""

    NAME = AWS
    REQUIREMENTS = [
        "sagemaker==2.117.0",
    ]

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        """Declare the stack component flavors for the AWS integration.

        Returns:
            List of stack component flavors for this integration.
        """
        from zenml.integrations.aws.flavors import (
            AWSContainerRegistryFlavor,
            AWSSecretsManagerFlavor,
            SagemakerOrchestratorFlavor,
            SagemakerStepOperatorFlavor,
        )

        return [
            AWSSecretsManagerFlavor,
            AWSContainerRegistryFlavor,
            SagemakerStepOperatorFlavor,
            SagemakerOrchestratorFlavor,
        ]


AWSIntegration.check_installation()
