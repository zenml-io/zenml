#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Base class for all ZenML deployers."""

from typing import (
    TYPE_CHECKING,
)

from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

DEFAULT_PIPELINE_ENDPOINT_LCM_TIMEOUT = 300


class DeployerError(Exception):
    """Base class for deployer errors."""


class PipelineEndpointAlreadyExistsError(EntityExistsError, DeployerError):
    """Error raised when a pipeline endpoint already exists."""


class PipelineEndpointNotFoundError(KeyError, DeployerError):
    """Error raised when a pipeline endpoint is not found."""


class PipelineEndpointDeploymentError(DeployerError):
    """Error raised when a pipeline endpoint deployment fails."""


class PipelineEndpointDeploymentTimeoutError(DeployerError):
    """Error raised when a pipeline endpoint deployment times out."""


class PipelineEndpointDeprovisionError(DeployerError):
    """Error raised when a pipeline endpoint deletion fails."""


class PipelineEndpointDeletionTimeoutError(DeployerError):
    """Error raised when a pipeline endpoint deletion times out."""


class PipelineLogsNotFoundError(KeyError, DeployerError):
    """Error raised when pipeline logs are not found."""


class PipelineEndpointDeployerMismatchError(DeployerError):
    """Error raised when a pipeline endpoint is not managed by this deployer."""


class PipelineEndpointSnapshotMismatchError(DeployerError):
    """Error raised when a pipeline endpoint snapshot does not match the current deployer."""


class PipelineEndpointHTTPError(DeployerError):
    """Error raised when an HTTP request to a pipeline endpoint fails."""


class PipelineEndpointSchemaNotFoundError(KeyError, DeployerError):
    """Error raised when a pipeline endpoint schema is not found."""


class PipelineEndpointInvalidParametersError(DeployerError):
    """Error raised when the parameters for a pipeline endpoint are invalid."""
