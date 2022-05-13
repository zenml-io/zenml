#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
The GCP secrets manager integration submodule provides a way to access the gcp secrets manager
from within you ZenML Pipeline runs.
"""
from typing import List

from zenml.enums import StackComponentType
from zenml.integrations.constants import GCP_SECRETS_MANAGER
from zenml.integrations.integration import Integration
from zenml.zen_stores.models import FlavorWrapper

GCP_SECRETS_MANAGER_FLAVOR = "gcp_secrets_manager"


class GcpSecretManagerIntegration(Integration):
    """Definition of the Secrets Manager for the Google Cloud Platform
    integration with ZenML."""

    NAME = GCP_SECRETS_MANAGER
    REQUIREMENTS = ["google-cloud-secret-manager"]

    @classmethod
    def flavors(cls) -> List[FlavorWrapper]:
        """Declare the stack component flavors for the GCP integration."""
        return [
            FlavorWrapper(
                name=GCP_SECRETS_MANAGER_FLAVOR,
                source="zenml.integrations.gcp_secrets_manager.secrets_manager."
                "GCPSecretsManager",
                type=StackComponentType.SECRETS_MANAGER,
                integration=cls.NAME,
            )
        ]


GcpSecretManagerIntegration.check_installation()
