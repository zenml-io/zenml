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
"""AzureML definitions."""

from typing import Optional

from pydantic import model_validator

from zenml.config.base_settings import BaseSettings
from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)


class AzureMLComputeTypes(StrEnum):
    """Enum for different types of compute on AzureML."""

    SERVERLESS = "serverless"
    COMPUTE_INSTANCE = "compute-instance"
    COMPUTE_CLUSTER = "compute-cluster"


class AzureMLComputeSettings(BaseSettings):
    """Settings for the AzureML compute.

    These settings adjust the compute resources that will be used by the
    pipeline execution.

    There are three possible use cases for this implementation:

        1. Serverless compute (default behavior):
            - The `mode` is set to `serverless` (default behavior).
            - All the other parameters become irrelevant and will throw a
            warning if set.

        2. Compute instance:
            - The `mode` is set to `compute-instance`.
            - In this case, users have to provide a `compute_name`.
                - If a compute instance exists with this name, this instance
                will be used and all the other parameters become irrelevant
                and will throw a warning if set.
                - If a compute instance does not already exist, ZenML will
                create it. You can use the parameters `size` and
                `idle_type_before_shutdown_minutes` for this operation.

        3. Compute cluster:
            - The `mode` is set to `compute-cluster`.
            - In this case, users have to provide a `compute_name`.
                - If a compute cluster exists with this name, this instance
                will be used and all the other parameters become irrelevant
                and will throw a warning if set.
                - If a compute cluster does not already exist, ZenML will
                create it. You can set the additional parameters for this
                operation.
    """

    # Mode for compute
    mode: AzureMLComputeTypes = AzureMLComputeTypes.SERVERLESS

    # Common Configuration for Compute Instances and Clusters
    compute_name: Optional[str] = None
    # TODO: migrate to instance type
    size: Optional[str] = None

    # Additional configuration for a Compute Instance
    idle_time_before_shutdown_minutes: Optional[int] = None

    # Additional configuration for a Compute Cluster
    idle_time_before_scaledown_down: Optional[int] = None
    location: Optional[str] = None
    min_instances: Optional[int] = None
    max_instances: Optional[int] = None
    tier: Optional[str] = None

    @model_validator(mode="after")
    def azureml_settings_validator(self) -> "AzureMLComputeSettings":
        """Checks whether the right configuration is set based on mode.

        Returns:
            the instance itself.

        Raises:
            AssertionError: if a name is not provided when working with
                instances and clusters.
        """
        viable_configuration_fields = {
            AzureMLComputeTypes.SERVERLESS: {"mode"},
            AzureMLComputeTypes.COMPUTE_INSTANCE: {
                "mode",
                "compute_name",
                "size",
                "idle_time_before_shutdown_minutes",
            },
            AzureMLComputeTypes.COMPUTE_CLUSTER: {
                "mode",
                "compute_name",
                "size",
                "idle_time_before_scaledown_down",
                "location",
                "min_instances",
                "max_instances",
                "tier",
            },
        }
        viable_fields = viable_configuration_fields[self.mode]

        for field in self.model_fields_set:
            if (
                field not in viable_fields
                and field in AzureMLComputeSettings.model_fields
            ):
                logger.warning(
                    f"In the {self.__class__.__name__} settings, the mode of "
                    f"operation is set to {self.mode}. In this mode, you can "
                    f"not configure the parameter '{field}'. This "
                    "configuration will be ignored."
                )

        if (
            self.mode == AzureMLComputeTypes.COMPUTE_INSTANCE
            or self.mode == AzureMLComputeTypes.COMPUTE_CLUSTER
        ):
            assert self.compute_name is not None, (
                "When you are working with compute instances and clusters, "
                "please define a name for the compute target."
            )

        return self
