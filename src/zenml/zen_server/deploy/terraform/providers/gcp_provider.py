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
"""Zen Server GCP Terraform deployer implementation."""

from typing import ClassVar, Type

from zenml.enums import ServerProviderType
from zenml.logger import get_logger
from zenml.zen_server.deploy.terraform.providers.terraform_provider import (
    TerraformServerProvider,
)
from zenml.zen_server.deploy.terraform.terraform_zen_server import (
    TerraformServerDeploymentConfig,
)

logger = get_logger(__name__)


class GCPServerDeploymentConfig(TerraformServerDeploymentConfig):
    """GCP server deployment configuration.

    Attributes:
        project_id: The project in GCP to deploy the server to.
        region: The GCP region to deploy to.
        cloudsql_name: The name of the CloudSQL instance to create
        db_name: Name of CloudSQL database to create.
        db_instance_tier: Instance class of CloudSQL database to create.
        db_disk_size: Allocated storage of CloudSQL database to create.
    """

    project_id: str
    region: str = "europe-west3"
    cloudsql_name: str = "zenmlserver"
    db_name: str = "zenmlserver"
    db_instance_tier: str = "db-n1-standard-1"
    db_disk_size: int = 10


class GCPServerProvider(TerraformServerProvider):
    """GCP ZenML server provider."""

    TYPE: ClassVar[ServerProviderType] = ServerProviderType.GCP
    CONFIG_TYPE: ClassVar[
        Type[TerraformServerDeploymentConfig]
    ] = GCPServerDeploymentConfig


GCPServerProvider.register_as_provider()
