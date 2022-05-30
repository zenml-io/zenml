#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import logging
from enum import Enum

from zenml.utils.enum_utils import StrEnum


class ExecutionStatus(StrEnum):
    """Enum that represents the current status of a step or pipeline run."""

    FAILED = "failed"
    COMPLETED = "completed"
    RUNNING = "running"
    CACHED = "cached"


class LoggingLevels(Enum):
    """Enum for logging levels."""

    NOTSET = logging.NOTSET
    ERROR = logging.ERROR
    WARN = logging.WARN
    INFO = logging.INFO
    DEBUG = logging.DEBUG
    CRITICAL = logging.CRITICAL


class StackComponentType(StrEnum):
    """All possible types a `StackComponent` can have."""

    ALERTER = "alerter"
    ORCHESTRATOR = "orchestrator"
    METADATA_STORE = "metadata_store"
    ARTIFACT_STORE = "artifact_store"
    CONTAINER_REGISTRY = "container_registry"
    STEP_OPERATOR = "step_operator"
    FEATURE_STORE = "feature_store"
    SECRETS_MANAGER = "secrets_manager"
    MODEL_DEPLOYER = "model_deployer"
    EXPERIMENT_TRACKER = "experiment_tracker"

    @property
    def plural(self) -> str:
        """Returns the plural of the enum value."""
        if self == StackComponentType.CONTAINER_REGISTRY:
            return "container_registries"

        return f"{self.value}s"


class MetadataContextTypes(Enum):
    """All possible types that contexts can have within pipeline nodes"""

    STACK = "stack"
    PIPELINE_REQUIREMENTS = "pipeline_requirements"


class StoreType(StrEnum):
    """Repository Store Backend Types"""

    LOCAL = "local"
    SQL = "sql"
    REST = "rest"


class ContainerRegistryFlavor(StrEnum):
    """Flavors of container registries."""

    DEFAULT = "default"
    GITHUB = "github"
    DOCKERHUB = "dockerhub"
    GCP = "gcp"
    AZURE = "azure"
    GITLAB = "gitlab"


class CliCategories(StrEnum):
    """All possible categories for CLI commands.
    Note: The order of the categories is important. The same
    order is used to sort the commands in the CLI help output.
    """

    STACK_COMPONENTS = "Stack Components"
    MODEL_DEPLOYMENT = "Model Deployment"
    INTEGRATIONS = "Integrations"
    MANAGEMENT_TOOLS = "Management Tools"
    IDENTITY_AND_SECURITY = "Identity and Security"
    OTHER_COMMANDS = "Other Commands"
