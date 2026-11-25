#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Broker stream key derivation."""

from uuid import UUID

from zenml.zen_server.utils import server_config


def _deployment_prefix() -> str:
    """Return the deployment-scoped broker key prefix.

    Returns:
        The deployment-scoped broker key prefix.
    """
    return f"zenml:stream:server:{server_config().deployment_id}"


def stream_key_for_run(pipeline_run_id: UUID) -> str:
    """Return the broker stream key for a pipeline run.

    Args:
        pipeline_run_id: The pipeline run to derive the key for.

    Returns:
        The deployment-scoped broker stream key.
    """
    return f"{_deployment_prefix()}:run:{pipeline_run_id}"


def startup_probe_key() -> str:
    """Return the broker key used by the startup connectivity probe.

    Returns:
        The deployment-scoped startup probe key.
    """
    return f"{_deployment_prefix()}:startup-probe"
