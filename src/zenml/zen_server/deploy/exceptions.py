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
"""ZenML server deployment exceptions."""

from zenml.exceptions import ZenMLBaseException


class ServerDeploymentError(ZenMLBaseException):
    """Base exception class for all ZenML server deployment related errors."""


class ServerProviderNotFoundError(ServerDeploymentError):
    """Raised when using a ZenML server provider that doesn't exist."""


class ServerDeploymentExistsError(ServerDeploymentError):
    """Raised when trying to deploy a new ZenML server with the same name."""


class ServerDeploymentNotFoundError(ServerDeploymentError):
    """Raised when trying to fetch a ZenML server deployment that doesn't exist."""


class ServerDeploymentConfigurationError(ServerDeploymentError):
    """Raised when there is a ZenML server deployment configuration error ."""
