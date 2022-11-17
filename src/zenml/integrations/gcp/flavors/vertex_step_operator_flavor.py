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
"""Vertex step operator flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.config.base_settings import BaseSettings
from zenml.integrations.gcp import GCP_VERTEX_STEP_OPERATOR_FLAVOR
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.step_operators.base_step_operator import (
    BaseStepOperatorConfig,
    BaseStepOperatorFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.gcp.step_operators import VertexStepOperator


class VertexStepOperatorSettings(BaseSettings):
    """Settings for the Vertex step operator.

    Attributes:
        accelerator_type: Defines which accelerator (GPU, TPU) is used for the
            job. Check out out this table to see which accelerator
            type and count are compatible with your chosen machine type:
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#gpu-compatibility-table.
        accelerator_count: Defines number of accelerators to be used for the
            job. Check out out this table to see which accelerator
            type and count are compatible with your chosen machine type:
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#gpu-compatibility-table.
        machine_type: Machine type specified here
            https://cloud.google.com/vertex-ai/docs/training/configure-compute#machine-types.

    """

    accelerator_type: Optional[str] = None
    accelerator_count: int = 0
    machine_type: str = "n1-standard-4"


class VertexStepOperatorConfig(  # type: ignore[misc] # https://github.com/pydantic/pydantic/issues/4173
    BaseStepOperatorConfig,
    GoogleCredentialsConfigMixin,
    VertexStepOperatorSettings,
):
    """Configuration for the Vertex step operator.

    Attributes:
        region: Region name, e.g., `europe-west1`.
        project: GCP project name. If left None, inferred from the
            environment.
        encryption_spec_key_name: Encryption spec key name.
    """

    region: str
    project: Optional[str] = None

    # customer managed encryption key resource name
    # will be applied to all Vertex AI resources if set
    encryption_spec_key_name: Optional[str] = None

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


class VertexStepOperatorFlavor(BaseStepOperatorFlavor):
    """Vertex Step Operator flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            Name of the flavor.
        """
        return GCP_VERTEX_STEP_OPERATOR_FLAVOR

    @property
    def config_class(self) -> Type[VertexStepOperatorConfig]:
        """Returns `VertexStepOperatorConfig` config class.

        Returns:
                The config class.
        """
        return VertexStepOperatorConfig

    @property
    def implementation_class(self) -> Type["VertexStepOperator"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.gcp.step_operators import VertexStepOperator

        return VertexStepOperator
