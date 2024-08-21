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
"""Modal step operator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.modal import MODAL_STEP_OPERATOR_FLAVOR
from zenml.step_operators import BaseStepOperatorConfig, BaseStepOperatorFlavor

if TYPE_CHECKING:
    from zenml.integrations.modal.step_operators import ModalStepOperator


class ModalStepOperatorSettings(BaseSettings):
    """Settings for the Modal step operator.

    Attributes:
        gpu: The type of GPU to use for the step execution.
        cpu: The number of CPU cores to allocate for the step execution.
        memory: The amount of memory (in megabytes) to allocate for the step execution.
    """

    gpu: Optional[str] = None
    cpu: Optional[float] = None
    memory: Optional[int] = None


class ModalStepOperatorConfig(
    BaseStepOperatorConfig, ModalStepOperatorSettings
):
    """Configuration for the Modal step operator."""

    @property
    def is_remote(self) -> bool:
        """Checks if this stack component is running remotely.

        This designation is used to determine if the stack component can be
        used with a local ZenML database or if it requires a remote ZenML
        server.

        Returns:
            True if this config is for a remote component, False otherwise.
        """
        return True


class ModalStepOperatorFlavor(BaseStepOperatorFlavor):
    """Modal step operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return MODAL_STEP_OPERATOR_FLAVOR

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
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/step_operator/modal.png"

    @property
    def config_class(self) -> Type[ModalStepOperatorConfig]:
        """Returns `ModalStepOperatorConfig` config class.

        Returns:
            The config class.
        """
        return ModalStepOperatorConfig

    @property
    def implementation_class(self) -> Type["ModalStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.modal.step_operators import ModalStepOperator

        return ModalStepOperator
