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

import os
from pathlib import Path
from typing import ClassVar, List, Optional, Tuple, Type, cast

from zenml.enums import ServerProviderType
from zenml.logger import get_logger
from zenml.zen_server.deploy.deployment import ServerDeploymentConfig
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
    """

    prefix: Optional[str] = "default"
    region: Optional[str] = "eu-west-1"
    zenmlserver_namespace: Optional[str] = "terraform-server"
    kubectl_config_path: Optional[str] = os.path.join(
        str(Path.home()),
        ".kube",
        "config"
    )
    rds_db_username: Optional[str] = "admin"
    rds_db_password: Optional[str] = ""
    create_rds: Optional[bool] = True
    db_name: Optional[str] = "zenmlserver"
    db_type: Optional[str] = "mysql"
    db_version: Optional[str] = "8.0.28"
    db_instance_class: Optional[str] = "db.t3.micro"
    db_allocated_storage: Optional[int] = 5
    rds_url: Optional[str] = ""
    rds_sslCa: Optional[str] = ""
    rds_sslCert: Optional[str] = ""
    rds_sslKey: Optional[str] = ""
    rds_sslVerifyServerCert: Optional[bool] = True
    ingress_path: Optional[str] = "zenmlhihi"
    create_ingress_controller: Optional[bool] = True
    ingress_controller_hostname: Optional[str] = ""


class AWSServerProvider(TerraformServerProvider):
    """AWS ZenML server provider."""

    TYPE: ClassVar[ServerProviderType] = ServerProviderType.AWS
    CONFIG_TYPE: ClassVar[
        Type[TerraformServerDeploymentConfig]
    ] = AWSServerDeploymentConfig


AWSServerProvider.register_as_provider()
