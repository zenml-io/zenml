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
"""Initialization of the ZenML services module.

A service is a process or set of processes that outlive a pipeline run.
"""

from zenml.services.container.container_service import (
    ContainerService,
    ContainerServiceConfig,
    ContainerServiceStatus,
)
from zenml.services.container.container_service_endpoint import (
    ContainerServiceEndpoint,
    ContainerServiceEndpointConfig,
    ContainerServiceEndpointStatus,
)
from zenml.services.local.local_service import (
    LocalDaemonService,
    LocalDaemonServiceConfig,
    LocalDaemonServiceStatus,
)
from zenml.services.local.local_service_endpoint import (
    LocalDaemonServiceEndpoint,
    LocalDaemonServiceEndpointConfig,
    LocalDaemonServiceEndpointStatus,
)
from zenml.services.service import BaseService, ServiceConfig
from zenml.services.service_endpoint import (
    BaseServiceEndpoint,
    ServiceEndpointConfig,
    ServiceEndpointProtocol,
    ServiceEndpointStatus,
)
from zenml.services.service_monitor import (
    BaseServiceEndpointHealthMonitor,
    HTTPEndpointHealthMonitor,
    HTTPEndpointHealthMonitorConfig,
    ServiceEndpointHealthMonitorConfig,
    TCPEndpointHealthMonitor,
    TCPEndpointHealthMonitorConfig,
)
from zenml.services.service_registry import ServiceRegistry
from zenml.services.service_status import ServiceState, ServiceStatus
from zenml.services.service_type import ServiceType
from zenml.services.terraform.terraform_service import (
    TerraformService,
    TerraformServiceConfig,
    TerraformServiceStatus,
)
from zenml.services.utils import load_last_service_from_step

__all__ = [
    "ServiceState",
    "ServiceConfig",
    "ServiceStatus",
    "ServiceEndpointProtocol",
    "ServiceEndpointConfig",
    "ServiceEndpointStatus",
    "BaseServiceEndpoint",
    "ServiceType",
    "BaseService",
    "ServiceEndpointHealthMonitorConfig",
    "BaseServiceEndpointHealthMonitor",
    "HTTPEndpointHealthMonitorConfig",
    "HTTPEndpointHealthMonitor",
    "TCPEndpointHealthMonitorConfig",
    "TCPEndpointHealthMonitor",
    "ContainerService",
    "ContainerServiceConfig",
    "ContainerServiceStatus",
    "ContainerServiceEndpoint",
    "ContainerServiceEndpointConfig",
    "ContainerServiceEndpointStatus",
    "LocalDaemonService",
    "LocalDaemonServiceConfig",
    "LocalDaemonServiceStatus",
    "LocalDaemonServiceEndpointConfig",
    "LocalDaemonServiceEndpointStatus",
    "LocalDaemonServiceEndpoint",
    "ServiceRegistry",
    "TerraformService",
    "TerraformServiceConfig",
    "TerraformServiceStatus",
]
