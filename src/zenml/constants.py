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
from typing import Optional


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
CONFIG_VERSION = "1"
GIT_REPO_URL = "https://github.com/zenml-io/zenml.git"

# Environment variables
ENV_ZENML_CONFIG_PATH = "ZENML_CONFIG_PATH"
ENV_ZENML_DEBUG = "ZENML_DEBUG"
ENV_ZENML_LOGGING_VERBOSITY = "ZENML_LOGGING_VERBOSITY"
ENV_ABSL_LOGGING_VERBOSITY = "ZENML_ABSL_LOGGING_VERBOSITY"
ENV_ZENML_REPOSITORY_PATH = "ZENML_REPOSITORY_PATH"
ENV_ZENML_PREVENT_PIPELINE_EXECUTION = "ZENML_PREVENT_PIPELINE_EXECUTION"
ENV_ZENML_ENABLE_RICH_TRACEBACK = "ZENML_ENABLE_RICH_TRACEBACK"
ENV_ZENML_ACTIVE_STACK_ID = "ZENML_ACTIVE_STACK_ID"
ENV_ZENML_SUPPRESS_LOGS = "ZENML_SUPPRESS_LOGS"
ENV_ZENML_ENABLE_REPO_INIT_WARNINGS = "ZENML_ENABLE_REPO_INIT_WARNINGS"
ENV_ZENML_IGNORE_STORE_COUPLINGS = "ZENML_IGNORE_STORE_COUPLINGS"
ENV_ZENML_SECRET_VALIDATION_LEVEL = "ZENML_SECRET_VALIDATION_LEVEL"
ENV_ZENML_JWT_SECRET_KEY = "ZENML_JWT_SECRET_KEY"
ENV_ZENML_AUTH_TYPE = "ZENML_AUTH_TYPE"
ENV_ZENML_DEFAULT_USER_NAME = "ZENML_DEFAULT_USER_NAME"
ENV_ZENML_DEFAULT_USER_PASSWORD = "ZENML_DEFAULT_USER_PASSWORD"
ENV_ZENML_DEFAULT_PROJECT_NAME = "ZENML_DEFAULT_PROJECT_NAME"
ENV_ZENML_STORE_PREFIX = "ZENML_STORE_"
ENV_ZENML_SKIP_PIPELINE_REGISTRATION = "ZENML_SKIP_PIPELINE_REGISTRATION"
ENV_ZENML_SERVER_ROOT_URL_PATH = "ZENML_SERVER_ROOT_URL_PATH"
ENV_ZENML_SERVER_DEPLOYMENT_TYPE = "ZENML_SERVER_DEPLOYMENT_TYPE"
ENV_AUTO_OPEN_DASHBOARD = "AUTO_OPEN_DASHBOARD"
ENV_ZENML_DISABLE_DATABASE_MIGRATION = "DISABLE_DATABASE_MIGRATION"
ENV_ZENML_LOCAL_STORES_PATH = "ZENML_LOCAL_STORES_PATH"
ENV_ZENML_CONTAINER = "ZENML_CONTAINER"
ENV_ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING = (
    "ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING"
)
ENV_ZENML_DISABLE_PROJECT_WARNINGS = "ZENML_DISABLE_PROJECT_WARNINGS"

# Logging variables
IS_DEBUG_ENV: bool = handle_bool_env_var(ENV_ZENML_DEBUG, default=False)

ZENML_LOGGING_VERBOSITY: str = "INFO"

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

# Segment
SEGMENT_KEY_DEV = "mDBYI0m7GcCj59EZ4f9d016L1T3rh8J5"
SEGMENT_KEY_PROD = "sezE77zEoxHPFDXuyFfILx6fBnJFZ4p7"

# Container utils
SHOULD_PREVENT_PIPELINE_EXECUTION = handle_bool_env_var(
    ENV_ZENML_PREVENT_PIPELINE_EXECUTION
)

# Repository and local store directory paths:
REPOSITORY_DIRECTORY_NAME = ".zen"
LOCAL_STORES_DIRECTORY_NAME = "local_stores"

USER_MAIN_MODULE: Optional[str] = None

# Config file name
CONFIG_FILE_NAME = "config.yaml"

# Default store directory subpath:
DEFAULT_STORE_DIRECTORY_NAME = "default_zen_store"

# Secrets Manager
ZENML_SCHEMA_NAME = "zenml_schema_name"
LOCAL_SECRETS_FILENAME = "secrets.yaml"

# Rich config
ENABLE_RICH_TRACEBACK = handle_bool_env_var(
    ENV_ZENML_ENABLE_RICH_TRACEBACK, True
)

DISABLE_CLIENT_SERVER_MISMATCH_WARNING = handle_bool_env_var(
    ENV_ZENML_DISABLE_CLIENT_SERVER_MISMATCH_WARNING, default=False
)

# Services
DEFAULT_SERVICE_START_STOP_TIMEOUT = 10
DEFAULT_LOCAL_SERVICE_IP_ADDRESS = "127.0.0.1"
ZEN_SERVER_ENTRYPOINT = "zenml.zen_server.zen_server_api:app"

STEP_SOURCE_PARAMETER_NAME = "step_source"

# API Endpoint paths:
API = "/api"
HEALTH = "/health"
VERSION = "/version"
STACKS_EMPTY = "/stacks-empty"
STACKS = "/stacks"
STACK_COMPONENTS = "/components"
STATISTICS = "/statistics"
USERS = "/users"
CURRENT_USER = "/current-user"
TEAMS = "/teams"
PROJECTS = "/projects"
PERMISSIONS = "/permissions"
ROLES = "/roles"
FLAVORS = "/flavors"
ROLE_ASSIGNMENTS = "/role_assignments"
PIPELINE_RUNS = "/pipeline_runs"
LOGIN = "/login"
LOGOUT = "/logout"
PIPELINES = "/pipelines"
TRIGGERS = "/triggers"
RUNS = "/runs"
DEFAULT_STACK = "/default-stack"
PIPELINE_SPEC = "/pipeline-spec"
PIPELINE_CONFIGURATION = "/pipeline-configuration"
STEP_CONFIGURATION = "/step-configuration"
GRAPH = "/graph"
STEPS = "/steps"
ARTIFACTS = "/artifacts"
COMPONENT_TYPES = "/component-types"
COMPONENT_SIDE_EFFECTS = "/component-side-effects"
REPOSITORIES = "/repositories"
DEACTIVATE = "/deactivate"
EMAIL_ANALYTICS = "/email-opt-in"
ACTIVATE = "/activate"
INFO = "/info"
VERSION_1 = "/v1"
STATUS = "/status"

# mandatory stack component attributes
MANDATORY_COMPONENT_ATTRIBUTES = ["name", "uuid"]


# model metadata yaml file name
MODEL_METADATA_YAML_FILE_NAME = "model_metadata.yaml"

# orchestrator constants
ORCHESTRATOR_DOCKER_IMAGE_KEY = "orchestrator_docker_image"
DOCKER_IMAGE_DEPLOYMENT_CONFIG_FILE = ".zenml_deployment_config.yaml"

# Secret constants
ARBITRARY_SECRET_SCHEMA_TYPE = "arbitrary"
