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
"""ZenML server deployments."""

# DO NOT REMOVE THESE IMPORTS. They are needed so the ZenML server deployment
# providers get registered.
from zenml.zen_server.deploy import docker, local  # noqa

try:
    from zenml.zen_server.deploy import terraform  # noqa
except ImportError:
    # If ZenML is installed without the `terraform` extra, all terraform based
    # providers won't be available as the `python_terraform` library is not
    # installed
    pass

from zenml.zen_server.deploy.deployer import ServerDeployer
from zenml.zen_server.deploy.deployment import (
    ServerDeployment,
    ServerDeploymentConfig,
)

__all__ = [
    "ServerDeployer",
    "ServerDeployment",
    "ServerDeploymentConfig",
]
