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
"""ZenML enums."""
import logging
from enum import Enum

from zenml.utils.enum_utils import StrEnum


class ArtifactType(StrEnum):
    """All possible types an artifact can have."""

    DATA_ANALYSIS = "DataAnalysisArtifact"
    DATA = "DataArtifact"
    MODEL = "ModelArtifact"
    SCHEMA = "SchemaArtifact"  # deprecated
    SERVICE = "ServiceArtifact"
    STATISTICS = "StatisticsArtifact"  # deprecated in favor of `DATA_ANALYSIS`
    BASE = "BaseArtifact"


class VisualizationType(StrEnum):
    """All currently available visualization types."""

    CSV = "csv"
    HTML = "html"
    IMAGE = "image"
    MARKDOWN = "markdown"


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
    ANNOTATOR = "annotator"
    ARTIFACT_STORE = "artifact_store"
    CONTAINER_REGISTRY = "container_registry"
    DATA_VALIDATOR = "data_validator"
    EXPERIMENT_TRACKER = "experiment_tracker"
    FEATURE_STORE = "feature_store"
    IMAGE_BUILDER = "image_builder"
    MODEL_DEPLOYER = "model_deployer"
    ORCHESTRATOR = "orchestrator"
    SECRETS_MANAGER = "secrets_manager"
    STEP_OPERATOR = "step_operator"
    MODEL_REGISTRY = "model_registry"

    @property
    def plural(self) -> str:
        """Returns the plural of the enum value.

        Returns:
            The plural of the enum value.
        """
        if self == StackComponentType.CONTAINER_REGISTRY:
            return "container_registries"
        elif self == StackComponentType.MODEL_REGISTRY:
            return "model_registries"

        return f"{self.value}s"


class SecretScope(StrEnum):
    """Enum for the scope of a secret."""

    WORKSPACE = "workspace"
    USER = "user"


class StoreType(StrEnum):
    """Zen Store Backend Types."""

    SQL = "sql"
    REST = "rest"


class SecretsStoreType(StrEnum):
    """Secrets Store Backend Types.

    NOTE: this is a superset of the StoreType values because the set of secrets
    store backends includes all the backends supported for zen stores.
    """

    NONE = "none"  # indicates that the secrets store is disabled
    SQL = StoreType.SQL.value
    REST = StoreType.REST.value
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
    HASHICORP = "hashicorp"
    CUSTOM = "custom"  # indicates that the secrets store uses a custom backend


class ContainerRegistryFlavor(StrEnum):
    """Flavors of container registries."""

    DEFAULT = "default"
    GITHUB = "github"
    DOCKERHUB = "dockerhub"
    GCP = "gcp"
    AZURE = "azure"


class CliCategories(StrEnum):
    """All possible categories for CLI commands.

    Note: The order of the categories is important. The same
    order is used to sort the commands in the CLI help output.
    """

    STACK_COMPONENTS = "Stack Components"
    MODEL_DEPLOYMENT = "Model Deployment"
    HUB = "ZenML Hub"
    INTEGRATIONS = "Integrations"
    MANAGEMENT_TOOLS = "Management Tools"
    IDENTITY_AND_SECURITY = "Identity and Security"
    OTHER_COMMANDS = "Other Commands"


class AnnotationTasks(StrEnum):
    """Supported annotation tasks."""

    IMAGE_CLASSIFICATION = "image_classification"
    OBJECT_DETECTION_BOUNDING_BOXES = "object_detection_bounding_boxes"
    OCR = "optical_character_recognition"
    TEXT_CLASSIFICATION = "text_classification"


class SecretValidationLevel(StrEnum):
    """Secret validation levels."""

    SECRET_AND_KEY_EXISTS = "SECRET_AND_KEY_EXISTS"
    SECRET_EXISTS = "SECRET_EXISTS"
    NONE = "NONE"


class ServerProviderType(StrEnum):
    """ZenML server providers."""

    LOCAL = "local"
    DOCKER = "docker"
    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"


class AnalyticsEventSource(StrEnum):
    """Enum to identify analytics events source."""

    ZENML_GO = "zenml go"
    ZENML_INIT = "zenml init"
    ZENML_SERVER = "zenml server"


class PermissionType(StrEnum):
    """All permission types."""

    # ANY CHANGES TO THIS ENUM WILL NEED TO BE DONE TOGETHER WITH A DB MIGRATION
    WRITE = "write"  # allows the user to create, update, delete everything
    READ = "read"  # allows the user to read everything
    ME = (
        "me"  # allows the user to self administrate (change name, password...)
    )


class GenericFilterOps(StrEnum):
    """Ops for all filters for string values on list methods."""

    EQUALS = "equals"
    CONTAINS = "contains"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"
    GTE = "gte"
    GT = "gt"
    LTE = "lte"
    LT = "lt"


class SorterOps(StrEnum):
    """Ops for all filters for string values on list methods."""

    ASCENDING = "asc"
    DESCENDING = "desc"


class LogicalOperators(StrEnum):
    """Logical Ops to use to combine filters on list methods."""

    OR = "or"
    AND = "and"


class OperatingSystemType(StrEnum):
    """Enum for OS types."""

    LINUX = "Linux"
    WINDOWS = "Windows"
    MACOS = "Darwin"


class SourceContextTypes(StrEnum):
    """Enum for event source types."""

    CLI = "cli"
    PYTHON = "python"
    DASHBOARD = "dashboard"
    API = "api"
    UNKNOWN = "unknown"


class EnvironmentType(StrEnum):
    """Enum for environment types."""

    BITBUCKET_CI = "bitbucket_ci"
    CIRCLE_CI = "circle_ci"
    COLAB = "colab"
    CONTAINER = "container"
    DOCKER = "docker"
    GENERIC_CI = "generic_ci"
    GITHUB_ACTION = "github_action"
    GITLAB_CI = "gitlab_ci"
    KUBERNETES = "kubernetes"
    NATIVE = "native"
    NOTEBOOK = "notebook"
    PAPERSPACE = "paperspace"
    WSL = "wsl"
