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

from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger

logger = get_logger(__name__)


class DeployerError(Exception):
    """Base class for deployer errors."""


class DeploymentAlreadyExistsError(EntityExistsError, DeployerError):
    """Error raised when a deployment already exists."""


class DeploymentNotFoundError(KeyError, DeployerError):
    """Error raised when a deployment is not found."""


class DeploymentProvisionError(DeployerError):
    """Error raised when a deployment provisioning fails."""


class DeploymentTimeoutError(DeployerError):
    """Error raised when a deployment provisioning or deprovisioning times out."""


class DeploymentDeprovisionError(DeployerError):
    """Error raised when a deployment deprovisioning fails."""


class DeploymentLogsNotFoundError(KeyError, DeployerError):
    """Error raised when pipeline logs are not found."""


class DeploymentDeployerMismatchError(DeployerError):
    """Error raised when a deployment is not managed by this deployer."""


class DeploymentSnapshotMismatchError(DeployerError):
    """Error raised when a deployment snapshot does not match the current deployer."""


class DeploymentHTTPError(DeployerError):
    """Error raised when an HTTP request to a deployment fails."""


class DeploymentInvalidParametersError(DeployerError):
    """Error raised when the parameters for a deployment are invalid."""
