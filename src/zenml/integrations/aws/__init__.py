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
"""
The AWS integration provides a way for our users to manage their secrets
through AWS.
"""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import AWS
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

AWS_SECRET_MANAGER_FLAVOR = "aws"
AWS_CONTAINER_REGISTRY_FLAVOR = "aws"


class AWSIntegration(Integration):
    """Definition of AWS integration for ZenML."""

    NAME = AWS
    REQUIREMENTS = ["boto3==1.21.21"]

    @classmethod
    def activate(cls) -> None:
        """Activates the integration."""
        from zenml.integrations.aws import secret_schemas  # noqa

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the AWS integration."""
        return [
            FlavorWrapper(
                name=AWS_SECRET_MANAGER_FLAVOR,
                source="zenml.integrations.aws.secrets_managers"
                ".AWSSecretsManager",
                type=StackComponentType.SECRETS_MANAGER,
                integration=cls.NAME,
            ),
            FlavorWrapper(
                name=AWS_CONTAINER_REGISTRY_FLAVOR,
                source="zenml.integrations.aws.container_registries.AWSContainerRegistry",
                type=StackComponentType.CONTAINER_REGISTRY,
                integration=cls.NAME,
            ),
        ]


AWSIntegration.check_installation()
