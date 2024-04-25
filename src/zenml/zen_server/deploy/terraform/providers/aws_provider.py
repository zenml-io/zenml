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
"""Zen Server AWS Terraform deployer implementation."""

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


class AWSServerDeploymentConfig(TerraformServerDeploymentConfig):
    """AWS server deployment configuration.

    Attributes:
        region: The AWS region to deploy to.
        rds_name: The name of the RDS instance to create
        db_name: Name of RDS database to create.
        db_type: Type of RDS database to create.
        db_version: Version of RDS database to create.
        db_instance_class: Instance class of RDS database to create.
        db_allocated_storage: Allocated storage of RDS database to create.
    """

    region: str = "eu-west-1"
    rds_name: str = "zenmlserver"
    db_name: str = "zenmlserver"
    db_type: str = "mysql"
    db_version: str = "5.7.38"
    db_instance_class: str = "db.t3.micro"
    db_allocated_storage: int = 5


class AWSServerProvider(TerraformServerProvider):
    """AWS ZenML server provider."""

    TYPE: ClassVar[ServerProviderType] = ServerProviderType.AWS
    CONFIG_TYPE: ClassVar[Type[TerraformServerDeploymentConfig]] = (
        AWSServerDeploymentConfig
    )


AWSServerProvider.register_as_provider()
