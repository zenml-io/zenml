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
"""Skypilot orchestrator Lambda flavor."""

from typing import TYPE_CHECKING, Any, Optional, Type

from zenml.integrations.skypilot.flavors.skypilot_orchestrator_base_vm_config import (
    SkypilotBaseOrchestratorConfig,
    SkypilotBaseOrchestratorSettings,
)
from zenml.integrations.skypilot_lambda import (
    SKYPILOT_LAMBDA_ORCHESTRATOR_FLAVOR,
)
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestratorConfig, BaseOrchestratorFlavor
from zenml.utils.secret_utils import SecretField

if TYPE_CHECKING:
    from zenml.integrations.skypilot_lambda.orchestrators import (
        SkypilotLambdaOrchestrator,
    )


logger = get_logger(__name__)


class SkypilotLambdaOrchestratorSettings(SkypilotBaseOrchestratorSettings):
    """Skypilot orchestrator settings."""

    _UNSUPPORTED_FEATURES = {
        "use_spot": "Spot instances not supported for Lambda orchestrator.",
        "spot_recovery": "Spot recovery not supported for Lambda orchestrator.",
        "image_id": "Custom image IDs not supported for Lambda orchestrator.",
        # Add other unsupported features as needed
    }

    def __setattr__(self, name: str, value: Any) -> None:
        """Set attribute.

        Args:
            name: Name of the attribute.
            value: Value of the attribute.

        Raises:
            AttributeError: If the attribute is not supported.
        """
        if name in self._UNSUPPORTED_FEATURES:
            raise AttributeError(f"{name} is not supported on Lambda.")
        super().__setattr__(name, value)


class SkypilotLambdaOrchestratorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    SkypilotBaseOrchestratorConfig, SkypilotLambdaOrchestratorSettings
):
    """Skypilot orchestrator config."""

    api_key: Optional[str] = SecretField()


class SkypilotLambdaOrchestratorFlavor(BaseOrchestratorFlavor):
    """Flavor for the Skypilot Lambda orchestrator."""

    @property
    def name(self) -> str:
        """Name of the orchestrator flavor.

        Returns:
            Name of the orchestrator flavor.
        """
        return SKYPILOT_LAMBDA_ORCHESTRATOR_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/lambda.png"

    @property
    def config_class(self) -> Type[BaseOrchestratorConfig]:
        """Config class for the base orchestrator flavor.

        Returns:
            The config class.
        """
        return SkypilotLambdaOrchestratorConfig

    @property
    def implementation_class(self) -> Type["SkypilotLambdaOrchestrator"]:
        """Implementation class for this flavor.

        Returns:
            Implementation class for this flavor.
        """
        from zenml.integrations.skypilot_lambda.orchestrators import (
            SkypilotLambdaOrchestrator,
        )

        return SkypilotLambdaOrchestrator
