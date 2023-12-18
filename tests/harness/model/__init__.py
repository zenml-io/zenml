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
"""ZenML test framework models."""

from tests.harness.model.base import BaseTestConfigModel
from tests.harness.model.config import Configuration
from tests.harness.model.deployment import (
    DeploymentConfig,
    DeploymentSetup,
    DeploymentStoreConfig,
    ServerType,
)
from tests.harness.model.environment import EnvironmentConfig
from tests.harness.model.requirements import TestRequirements
from tests.harness.model.secret import Secret
from tests.harness.model.test import TestConfig

__all__ = [
    "BaseTestConfigModel",
    "Configuration",
    "DeploymentConfig",
    "DeploymentSetup",
    "ServerType",
    "DeploymentStoreConfig",
    "EnvironmentConfig",
    "TestRequirements",
    "Secret",
    "TestConfig",
]
