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


class StepRunInputArtifactType(StrEnum):
    """All possible types of a step run input artifact."""

    DEFAULT = "default"  # input argument that is the output of a previous step
    MANUAL = "manual"  # manually loaded via `zenml.load_artifact()`


class StepRunOutputArtifactType(StrEnum):
    """All possible types of a step run output artifact."""

    DEFAULT = "default"  # output of the current step
    MANUAL = "manual"  # manually saved via `zenml.save_artifact()`


class VisualizationType(StrEnum):
    """All currently available visualization types."""

    CSV = "csv"
    HTML = "html"
    IMAGE = "image"
    MARKDOWN = "markdown"


class ZenMLServiceType(StrEnum):
    """All possible types a service can have."""

    ZEN_SERVER = "zen_server"
    MODEL_SERVING = "model-serving"


class ExecutionStatus(StrEnum):
    """Enum that represents the current status of a step or pipeline run."""

    INITIALIZING = "initializing"
    FAILED = "failed"
    COMPLETED = "completed"
    RUNNING = "running"
    CACHED = "cached"

    @property
    def is_finished(self) -> bool:
        """Whether the execution status refers to a finished execution.

        Returns:
            Whether the execution status refers to a finished execution.
        """
        return self in {
            ExecutionStatus.FAILED,
            ExecutionStatus.COMPLETED,
            ExecutionStatus.CACHED,
        }


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
    """Secrets Store Backend Types."""

    NONE = "none"  # indicates that no secrets store is used
    SQL = "sql"
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
    MODEL_CONTROL_PLANE = "Model Control Plane"
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


class AuthScheme(StrEnum):
    """The authentication scheme."""

    NO_AUTH = "NO_AUTH"
    HTTP_BASIC = "HTTP_BASIC"
    OAUTH2_PASSWORD_BEARER = "OAUTH2_PASSWORD_BEARER"
    EXTERNAL = "EXTERNAL"


class OAuthGrantTypes(StrEnum):
    """The OAuth grant types."""

    OAUTH_PASSWORD = "password"
    OAUTH_DEVICE_CODE = "urn:ietf:params:oauth:grant-type:device_code"
    ZENML_EXTERNAL = "zenml-external"
    ZENML_API_KEY = "zenml-api-key"


class OAuthDeviceStatus(StrEnum):
    """The OAuth device status."""

    PENDING = "pending"
    VERIFIED = "verified"
    ACTIVE = "active"
    LOCKED = "locked"


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
    DASHBOARD_V2 = "dashboard-v2"
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


class ModelStages(StrEnum):
    """All possible stages of a Model Version."""

    NONE = "none"
    STAGING = "staging"
    PRODUCTION = "production"
    ARCHIVED = "archived"
    LATEST = "latest"


class ColorVariants(StrEnum):
    """All possible color variants for frontend."""

    GREY = "grey"
    PURPLE = "purple"
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    LIME = "lime"
    TEAL = "teal"
    TURQUOISE = "turquoise"
    MAGENTA = "magenta"
    BLUE = "blue"


class TaggableResourceTypes(StrEnum):
    """All possible resource types for tagging."""

    ARTIFACT = "artifact"
    ARTIFACT_VERSION = "artifact_version"
    MODEL = "model"
    MODEL_VERSION = "model_version"


class ResponseUpdateStrategy(StrEnum):
    """All available strategies to handle updated properties in the response."""

    ALLOW = "allow"
    IGNORE = "ignore"
    DENY = "deny"


class MetadataResourceTypes(StrEnum):
    """All possible resource types for adding metadata."""

    PIPELINE_RUN = "pipeline_run"
    STEP_RUN = "step_run"
    ARTIFACT_VERSION = "artifact_version"
    MODEL_VERSION = "model_version"


class DatabaseBackupStrategy(StrEnum):
    """All available database backup strategies."""

    # Backup disabled
    DISABLED = "disabled"
    # In-memory backup
    IN_MEMORY = "in-memory"
    # Dump the database to a file
    DUMP_FILE = "dump-file"
    # Create a backup of the database in the remote database service
    DATABASE = "database"


class PluginType(StrEnum):
    """All possible types of Plugins."""

    EVENT_SOURCE = "event_source"
    ACTION = "action"


class PluginSubType(StrEnum):
    """All possible types of Plugins."""

    # Event Source Subtypes
    WEBHOOK = "webhook"
    # Action Subtypes
    PIPELINE_RUN = "pipeline_run"


class OnboardingStep(StrEnum):
    """All onboarding steps."""

    DEVICE_VERIFIED = "device_verified"
    PIPELINE_RUN = "pipeline_run"
    STARTER_SETUP_COMPLETED = "starter_setup_completed"
    STACK_WITH_REMOTE_ORCHESTRATOR_CREATED = (
        "stack_with_remote_orchestrator_created"
    )
    PIPELINE_RUN_WITH_REMOTE_ORCHESTRATOR = (
        "pipeline_run_with_remote_orchestrator"
    )
    PRODUCTION_SETUP_COMPLETED = "production_setup_completed"


class StackDeploymentProvider(StrEnum):
    """All possible stack deployment providers."""

    AWS = "aws"
    GCP = "gcp"
    AZURE = "azure"
