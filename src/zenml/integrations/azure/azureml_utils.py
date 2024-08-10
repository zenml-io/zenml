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

from azure.ai.ml import MLClient
from azure.ai.ml.entities import Compute
from azure.core.exceptions import (
    ResourceNotFoundError,
)

from zenml.integrations.azure.flavors.azureml import (
    AzureMLComputeSettings,
    AzureMLComputeTypes,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


def check_settings_and_compute_configuration(
    parameter: str,
    settings: AzureMLComputeSettings,
    compute: Compute,
) -> None:
    """Utility function comparing a parameter between settings and compute.

    Args:
        parameter: the name of the parameter.
        settings: The AzureML orchestrator settings.
        compute: The compute instance or cluster from AzureML.
    """
    # Check the compute size
    compute_value = getattr(compute, parameter)
    settings_value = getattr(settings, parameter)

    if settings_value is not None and settings_value != compute_value:
        logger.warning(
            f"The '{parameter}' defined in the settings '{settings_value}' "
            "does not match the actual parameter of the instance: "
            f"'{compute_value}'. Will ignore this setting for now."
        )


def create_or_get_compute(
    client: MLClient,
    settings: AzureMLComputeSettings,
    default_compute_name: str,
) -> Optional[str]:
    """Creates or fetches the compute target if defined in the settings.

    Args:
        client: the AzureML client.
        settings: the settings for the orchestrator.
        default_compute_name: the default name for the compute target, if one
            is not provided in the settings.

    Returns:
        None, if the orchestrator is using serverless compute or
        str, the name of the compute target (instance or cluster).

    Raises:
        RuntimeError: if the fetched compute target is unsupported or the
            mode defined in the setting does not match the type of the
            compute target.
    """
    # If the mode is serverless, we can not fetch anything anyhow
    if settings.mode == AzureMLComputeTypes.SERVERLESS:
        return None

    # If a name is not provided, generate one based on the orchestrator id
    compute_name = settings.compute_name or default_compute_name

    # Try to fetch the compute target
    try:
        compute = client.compute.get(compute_name)

        logger.info(f"Using existing compute target: '{compute_name}'.")

        # Check if compute size matches with the settings
        check_settings_and_compute_configuration(
            parameter="size", settings=settings, compute=compute
        )

        compute_type = compute.type

        # Check the type and matches the settings
        if compute_type == "computeinstance":  # Compute Instance
            if settings.mode != AzureMLComputeTypes.COMPUTE_INSTANCE:
                raise RuntimeError(
                    "The mode of operation for the compute target defined"
                    f"in the settings '{settings.mode}' does not match "
                    f"the type of the compute target: `{compute_name}` "
                    "which is a 'compute-instance'. Please make sure that "
                    "the settings are adjusted properly."
                )

            if compute.state != "Running":
                raise RuntimeError(
                    f"The compute instance `{compute_name}` is not in a "
                    "running state at the moment. Please make sure that "
                    "the compute target is running, before executing the "
                    "pipeline."
                )

            # Idle time before shutdown
            check_settings_and_compute_configuration(
                parameter="idle_time_before_shutdown_minutes",
                settings=settings,
                compute=compute,
            )

        elif compute_type == "amIcompute":  # Compute Cluster
            if settings.mode != AzureMLComputeTypes.COMPUTE_CLUSTER:
                raise RuntimeError(
                    "The mode of operation for the compute target defined "
                    f"in the settings '{settings.mode}' does not match "
                    f"the type of the compute target: `{compute_name}` "
                    "which is a 'compute-cluster'. Please make sure that "
                    "the settings are adjusted properly."
                )

            if compute.provisioning_state != "Succeeded":
                raise RuntimeError(
                    f"The provisioning state '{compute.provisioning_state}'"
                    f"of the compute cluster `{compute_name}` is not "
                    "successful. Please make sure that the compute cluster "
                    "is provisioned properly, before executing the "
                    "pipeline."
                )

            for parameter in [
                "idle_time_before_scale_down",
                "max_instances",
                "min_instances",
                "tier",
                "location",
            ]:
                # Check all possible configurations
                check_settings_and_compute_configuration(
                    parameter=parameter, settings=settings, compute=compute
                )
        else:
            raise RuntimeError(f"Unsupported compute type: {compute_type}")
        return compute_name

    # If the compute target does not exist create it
    except ResourceNotFoundError:
        logger.info(
            "Can not find the compute target with name: " f"'{compute_name}':"
        )

        if settings.mode == AzureMLComputeTypes.COMPUTE_INSTANCE:
            logger.info(
                "Creating a new compute instance. This might take a "
                "few minutes."
            )

            from azure.ai.ml.entities import ComputeInstance

            compute_instance = ComputeInstance(
                name=compute_name,
                size=settings.size,
                idle_time_before_shutdown_minutes=settings.idle_time_before_shutdown_minutes,
            )
            client.begin_create_or_update(compute_instance).result()
            return compute_name

        elif settings.mode == AzureMLComputeTypes.COMPUTE_CLUSTER:
            logger.info(
                "Creating a new compute cluster. This might take a "
                "few minutes."
            )

            from azure.ai.ml.entities import AmlCompute

            compute_cluster = AmlCompute(
                name=compute_name,
                size=settings.size,
                location=settings.location,
                min_instances=settings.min_instances,
                max_instances=settings.max_instances,
                idle_time_before_scale_down=settings.idle_time_before_scaledown_down,
                tier=settings.tier,
            )
            client.begin_create_or_update(compute_cluster).result()
            return compute_name

    return None
