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
"""ZenML constants."""

import os

from zenml.enums import AuthScheme


def handle_bool_env_var(var: str, default: bool = False) -> bool:
    """Converts normal env var to boolean.

    Args:
        var: The environment variable to convert.
        default: The default value to return if the env var is not set.

    Returns:
        The converted value.
    """
    value = os.getenv(var)
    if value in ["1", "y", "yes", "True", "true"]:
        return True
    elif value in ["0", "n", "no", "False", "false"]:
        return False
    return default


def handle_int_env_var(var: str, default: int = 0) -> int:
    """Converts normal env var to int.

    Args:
        var: The environment variable to convert.
        default: The default value to return if the env var is not set.

    Returns:
        The converted value.
    """
    value = os.getenv(var, "")
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


# Global constants
APP_NAME = "zenml"

# Environment variables
ENV_ZENML_ANALYTICS_OPT_IN = "ZENML_ANALYTICS_OPT_IN"
ENV_ZENML_CONFIG_PATH = "ZENML_CONFIG_PATH"
ENV_ZENML_DEBUG = "ZENML_DEBUG"
ENV_ZENML_LOGGING_VERBOSITY = "ZENML_LOGGING_VERBOSITY"
ENV_ZENML_REPOSITORY_PATH = "ZENML_REPOSITORY_PATH"
ENV_ZENML_PREVENT_PIPELINE_EXECUTION = "ZENML_PREVENT_PIPELINE_EXECUTION"
ENV_ZENML_ENABLE_RICH_TRACEBACK = "ZENML_ENABLE_RICH_TRACEBACK"
ENV_ZENML_ACTIVE_STACK_ID = "ZENML_ACTIVE_STACK_ID"
ENV_ZENML_ACTIVE_WORKSPACE_ID = "ZENML_ACTIVE_WORKSPACE_ID"
ENV_ZENML_SUPPRESS_LOGS = "ZENML_SUPPRESS_LOGS"
ENV_ZENML_ENABLE_REPO_INIT_WARNINGS = "ZENML_ENABLE_REPO_INIT_WARNINGS"
ENV_ZENML_SECRET_VALIDATION_LEVEL = "ZENML_SECRET_VALIDATION_LEVEL"
ENV_ZENML_DEFAULT_USER_NAME = "ZENML_DEFAULT_USER_NAME"
ENV_ZENML_DEFAULT_USER_PASSWORD = "ZENML_DEFAULT_USER_PASSWORD"
ENV_ZENML_DEFAULT_WORKSPACE_NAME = "ZENML_DEFAULT_WORKSPACE_NAME"
ENV_ZENML_STORE_PREFIX = "ZENML_STORE_"
ENV_ZENML_SECRETS_STORE_PREFIX = "ZENML_SECRETS_STORE_"
ENV_ZENML_SKIP_PIPELINE_REGISTRATION = "ZENML_SKIP_PIPELINE_REGISTRATION"
ENV_AUTO_OPEN_DASHBOARD = "AUTO_OPEN_DASHBOARD"
ENV_ZENML_DISABLE_DATABASE_MIGRATION = "DISABLE_DATABASE_MIGRATION"
ENV_ZENML_LOCAL_STORES_PATH = "ZENML_LOCAL_STORES_PATH"
ENV_ZENML_CONTAINER = "ZENML_CONTAINER"
ENV_ZENML_PAGINATION_DEFAULT_LIMIT = "ZENML_PAGINATION_DEFAULT_LIMIT"
ENV_ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING = (
    "ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING"
)
ENV_ZENML_DISABLE_WORKSPACE_WARNINGS = "ZENML_DISABLE_WORKSPACE_WARNINGS"
ENV_ZENML_SKIP_IMAGE_BUILDER_DEFAULT = "ZENML_SKIP_IMAGE_BUILDER_DEFAULT"
ENV_ZENML_REQUIRES_CODE_DOWNLOAD = "ZENML_REQUIRES_CODE_DOWNLOAD"
ENV_ZENML_SERVER = "ZENML_SERVER"
ENV_ZENML_HUB_URL = "ZENML_HUB_URL"
ENV_ZENML_ENFORCE_TYPE_ANNOTATIONS = "ZENML_ENFORCE_TYPE_ANNOTATIONS"
ENV_ZENML_ENABLE_IMPLICIT_AUTH_METHODS = "ZENML_ENABLE_IMPLICIT_AUTH_METHODS"
ENV_ZENML_DISABLE_STEP_LOGS_STORAGE = "ZENML_DISABLE_STEP_LOGS_STORAGE"
ENV_ZENML_PIPELINE_API_TOKEN_EXPIRES_MINUTES = (
    "ZENML_PIPELINE_API_TOKEN_EXPIRES_MINUTES"
)

# ZenML Server environment variables
ENV_ZENML_SERVER_PREFIX = "ZENML_SERVER_"
ENV_ZENML_SERVER_DEPLOYMENT_TYPE = f"{ENV_ZENML_SERVER_PREFIX}DEPLOYMENT_TYPE"
ENV_ZENML_SERVER_AUTH_SCHEME = f"{ENV_ZENML_SERVER_PREFIX}AUTH_SCHEME"

# Logging variables
IS_DEBUG_ENV: bool = handle_bool_env_var(ENV_ZENML_DEBUG, default=False)

if IS_DEBUG_ENV:
    ZENML_LOGGING_VERBOSITY = os.getenv(
        ENV_ZENML_LOGGING_VERBOSITY, default="DEBUG"
    ).upper()
else:
    ZENML_LOGGING_VERBOSITY = os.getenv(
        ENV_ZENML_LOGGING_VERBOSITY, default="INFO"
    ).upper()

INSIDE_ZENML_CONTAINER = handle_bool_env_var(ENV_ZENML_CONTAINER, False)

# Analytics constants
VALID_OPERATING_SYSTEMS = ["Windows", "Darwin", "Linux"]

# Path utilities constants
REMOTE_FS_PREFIX = ["gs://", "hdfs://", "s3://", "az://", "abfs://"]

# ZenML Analytics Server - URL
ANALYTICS_SERVER_URL = "https://analytics.zenml.io/"

# Container utils
SHOULD_PREVENT_PIPELINE_EXECUTION = handle_bool_env_var(
    ENV_ZENML_PREVENT_PIPELINE_EXECUTION
)

# Repository and local store directory paths:
REPOSITORY_DIRECTORY_NAME = ".zen"
LOCAL_STORES_DIRECTORY_NAME = "local_stores"

# Config file name
CONFIG_FILE_NAME = "config.yaml"

# Default store directory subpath:
DEFAULT_STORE_DIRECTORY_NAME = "default_zen_store"

DEFAULT_USERNAME = "default"
DEFAULT_PASSWORD = ""
DEFAULT_WORKSPACE_NAME = "default"
DEFAULT_STACK_AND_COMPONENT_NAME = "default"

# Rich config
ENABLE_RICH_TRACEBACK = handle_bool_env_var(
    ENV_ZENML_ENABLE_RICH_TRACEBACK, True
)

DISABLE_CLIENT_SERVER_MISMATCH_WARNING = handle_bool_env_var(
    ENV_ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING, default=False
)

ENFORCE_TYPE_ANNOTATIONS = handle_bool_env_var(
    ENV_ZENML_ENFORCE_TYPE_ANNOTATIONS, default=False
)

# Services
DEFAULT_SERVICE_START_STOP_TIMEOUT = 60
DEFAULT_LOCAL_SERVICE_IP_ADDRESS = "127.0.0.1"
ZEN_SERVER_ENTRYPOINT = "zenml.zen_server.zen_server_api:app"

STEP_SOURCE_PARAMETER_NAME = "step_source"

# Server settings
DEFAULT_ZENML_JWT_TOKEN_LEEWAY = 10
DEFAULT_ZENML_JWT_TOKEN_ALGORITHM = "HS256"
DEFAULT_ZENML_AUTH_SCHEME = AuthScheme.OAUTH2_PASSWORD_BEARER
EXTERNAL_AUTHENTICATOR_TIMEOUT = 10  # seconds
DEFAULT_ZENML_SERVER_MAX_DEVICE_AUTH_ATTEMPTS = 3
DEFAULT_ZENML_SERVER_DEVICE_AUTH_TIMEOUT = 60 * 5  # 5 minutes
DEFAULT_ZENML_SERVER_DEVICE_AUTH_POLLING = 5  # seconds
DEFAULT_HTTP_TIMEOUT = 30
ZENML_API_KEY_PREFIX = "ZENKEY_"

# API Endpoint paths:
API = "/api"
HEALTH = "/health"
STACKS = "/stacks"
STACK_COMPONENTS = "/components"
STATISTICS = "/statistics"
USERS = "/users"
CURRENT_USER = "/current-user"
WORKSPACES = "/workspaces"
FLAVORS = "/flavors"
LOGIN = "/login"
LOGOUT = "/logout"
PIPELINES = "/pipelines"
PIPELINE_BUILDS = "/pipeline_builds"
PIPELINE_DEPLOYMENTS = "/pipeline_deployments"
RUNS = "/runs"
RUN_METADATA = "/run-metadata"
SCHEDULES = "/schedules"
PIPELINE_SPEC = "/pipeline-spec"
PIPELINE_CONFIGURATION = "/pipeline-configuration"
STEP_CONFIGURATION = "/step-configuration"
GRAPH = "/graph"
STEPS = "/steps"
LOGS = "/logs"
ARTIFACTS = "/artifacts"
ARTIFACT_VERSIONS = "/artifact_versions"
ARTIFACT_VISUALIZATIONS = "/artifact_visualizations"
COMPONENT_TYPES = "/component-types"
DEACTIVATE = "/deactivate"
EMAIL_ANALYTICS = "/email-opt-in"
ACTIVATE = "/activate"
INFO = "/info"
VERSION_1 = "/v1"
STATUS = "/status"
GET_OR_CREATE = "/get-or-create"
SECRETS = "/secrets"
VISUALIZE = "/visualize"
CODE_REPOSITORIES = "/code_repositories"
CODE_REFERENCES = "/code_references"
SERVICE_CONNECTORS = "/service_connectors"
SERVICE_CONNECTOR_TYPES = "/service_connector_types"
SERVICE_CONNECTOR_VERIFY = "/verify"
SERVICE_CONNECTOR_RESOURCES = "/resources"
SERVICE_CONNECTOR_CLIENT = "/client"
MODELS = "/models"
MODEL_VERSIONS = "/model_versions"
MODEL_VERSION_ARTIFACTS = "/model_version_artifacts"
MODEL_VERSION_PIPELINE_RUNS = "/model_version_pipeline_runs"
DEVICES = "/devices"
DEVICE_AUTHORIZATION = "/device_authorization"
DEVICE_VERIFY = "/verify"
API_TOKEN = "/api_token"
TAGS = "/tags"
SERVICE_ACCOUNTS = "/service_accounts"
API_KEYS = "/api_keys"
API_KEY_ROTATE = "/rotate"

# model metadata yaml file name
MODEL_METADATA_YAML_FILE_NAME = "model_metadata.yaml"

# orchestrator constants
ORCHESTRATOR_DOCKER_IMAGE_KEY = "orchestrator"
PIPELINE_API_TOKEN_EXPIRES_MINUTES = handle_int_env_var(
    ENV_ZENML_PIPELINE_API_TOKEN_EXPIRES_MINUTES,
    default=60 * 24,  # 24 hours
)

# Secret constants
SECRET_VALUES = "values"

# Pagination and filtering defaults
PAGINATION_STARTING_PAGE: int = 1
PAGE_SIZE_DEFAULT: int = handle_int_env_var(
    ENV_ZENML_PAGINATION_DEFAULT_LIMIT, default=20
)
PAGE_SIZE_MAXIMUM: int = handle_int_env_var(
    ENV_ZENML_PAGINATION_DEFAULT_LIMIT, default=10000
)
FILTERING_DATETIME_FORMAT: str = "%Y-%m-%d %H:%M:%S"

# Metadata constants
METADATA_ORCHESTRATOR_URL = "orchestrator_url"
METADATA_EXPERIMENT_TRACKER_URL = "experiment_tracker_url"
METADATA_DEPLOYED_MODEL_URL = "deployed_model_url"

# Model registries constants
MLFLOW_MODEL_FORMAT = "MLflow"

# Service connector constants
DOCKER_REGISTRY_RESOURCE_TYPE = "docker-registry"
KUBERNETES_CLUSTER_RESOURCE_TYPE = "kubernetes-cluster"

# Stack Recipe constants
STACK_RECIPES_GITHUB_REPO = "https://github.com/zenml-io/mlops-stacks.git"
ALPHA_MESSAGE = (
    "The mlstacks tool/package is in alpha and actively being developed. "
    "Please avoid running mission-critical workloads on resources deployed "
    "through these commands. If you encounter any problems, create an issue "
    f"on the repository {STACK_RECIPES_GITHUB_REPO} and we'll help you out!"
)
NOT_INSTALLED_MESSAGE = (
    "The prerequisites for using `mlstacks` (the `mlstacks` and "
    "`python-terraform` packages seem to be unavailable on your machine "
    "and/or in your environment. To install the missing dependencies: \n\n"
    "`pip install mlstacks`"
)
TERRAFORM_NOT_INSTALLED_MESSAGE = (
    "Terraform appears not to be installed on your machine and/or in your "
    "environment. Please install Terraform and try again."
)
STACK_RECIPE_MODULAR_RECIPES = ["aws", "gcp", "k3d"]
MLSTACKS_SUPPORTED_STACK_COMPONENTS = [
    "artifact_store",
    "container_registry",
    "experiment_tracker",
    "orchestrator",
    "model_deployer",
    "mlops_platform",
    "step_operator",
]

# Parameters for internal ZenML Models
TEXT_FIELD_MAX_LENGTH = 65535
STR_FIELD_MAX_LENGTH = 255
MEDIUMTEXT_MAX_LENGTH = 2**24 - 1

# Model Control Plane constants
LATEST_MODEL_VERSION_PLACEHOLDER = "__latest__"


# Service connector constants
SERVICE_CONNECTOR_SKEW_TOLERANCE_SECONDS = 60 * 5  # 5 minutes
