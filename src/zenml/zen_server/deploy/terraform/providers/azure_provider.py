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
"""Zen Server Azure Terraform deployer implementation."""

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


class AzureServerDeploymentConfig(TerraformServerDeploymentConfig):
    """Azure server deployment configuration.

    Attributes:
        resource_group: The Azure resource_group to deploy to.
        db_instance_name: The name of the Flexible MySQL instance to create
        db_name: Name of RDS database to create.
        db_version: Version of MySQL database to create.
        db_sku_name: The sku_name for the database resource.
        db_disk_size: Allocated storage of MySQL database to create.
    """

    resource_group: str = "zenml"
    db_instance_name: str = "zenmlserver"
    db_name: str = "zenmlserver"
    db_version: str = "5.7"
    db_sku_name: str = "B_Standard_B1s"
    db_disk_size: int = 20


class AzureServerProvider(TerraformServerProvider):
    """Azure ZenML server provider."""

    TYPE: ClassVar[ServerProviderType] = ServerProviderType.AZURE
    CONFIG_TYPE: ClassVar[
        Type[TerraformServerDeploymentConfig]
    ] = AzureServerDeploymentConfig


AzureServerProvider.register_as_provider()
