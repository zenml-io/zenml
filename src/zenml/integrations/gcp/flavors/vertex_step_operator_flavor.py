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

from pydantic import validator as property_validator

from zenml.integrations.gcp import GCP_VERTEX_STEP_OPERATOR_FLAVOR
from zenml.integrations.gcp.google_credentials_mixin import (
    GoogleCredentialsConfigMixin,
)
from zenml.step_operators.base_step_operator import (
    BaseStepOperatorConfig,
    BaseStepOperatorFlavor,
)
from zenml.utils import deprecation_utils

if TYPE_CHECKING:
    from zenml.integrations.gcp.step_operators import VertexStepOperator


class VertexStepOperatorConfig(
    BaseStepOperatorConfig,
    GoogleCredentialsConfigMixin,
):
    """Configuration for the Vertex step operator.

    Attributes:
        region: Region name, e.g., `europe-west1`.
        project: GCP project name. If left None, inferred from the
            environment.
        accelerator_type: Accelerator type from list: https://cloud.google.com/vertex-ai/docs/reference/rest/v1/MachineSpec#AcceleratorType
        accelerator_count: Defines number of accelerators to be
            used for the job.
        machine_type: Machine type specified here: https://cloud.google.com/vertex-ai/docs/training/configure-compute#machine-types
        base_image: Base image for building the custom job container.
        encryption_spec_key_name: Encryption spec key name.
    """

    region: str
    project: Optional[str] = None
    accelerator_type: Optional[str] = None
    accelerator_count: int = 0
    machine_type: str = "n1-standard-4"
    base_image: Optional[str] = None

    # customer managed encryption key resource name
    # will be applied to all Vertex AI resources if set
    encryption_spec_key_name: Optional[str] = None

    _deprecation_validator = deprecation_utils.deprecate_pydantic_attributes(
        ("base_image", "docker_parent_image")
    )

    @property_validator("accelerator_type")
    def validate_accelerator_enum(cls, accelerator_type: Optional[str]) -> None:
        """Validates that the accelerator type is valid.

        Args:
            accelerator_type: Accelerator type

        Raises:
            ValueError: If the accelerator type is not valid.
        """
        # TODO: refactor this into the actual implementation
        from google.cloud import aiplatform

        accepted_vals = list(
            aiplatform.gapic.AcceleratorType.__members__.keys()
        )
        if accelerator_type and accelerator_type.upper() not in accepted_vals:
            raise ValueError(
                f"Accelerator must be one of the following: {accepted_vals}"
            )


class VertexStepOperatorFlavor(BaseStepOperatorFlavor):
    """Vertex Step Operator flavor."""

    @property
    def name(self) -> str:
        return GCP_VERTEX_STEP_OPERATOR_FLAVOR

    @property
    def config_class(self) -> Type[VertexStepOperatorConfig]:
        return VertexStepOperatorConfig

    @property
    def implementation_class(self) -> Type["VertexStepOperator"]:
        from zenml.integrations.gcp.step_operators import VertexStepOperator

        return VertexStepOperator
