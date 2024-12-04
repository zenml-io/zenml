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

import json
import logging
import os
from typing import Any, List, Optional, Type, TypeVar

from zenml.enums import AuthScheme

T = TypeVar("T")


def handle_json_env_var(
    var: str,
    expected_type: Type[T],
    default: Optional[List[str]] = None,
) -> Any:
    """Converts a json env var into a Python object.

    Args:
        var:  The environment variable to convert.
        default: The default value to return if the env var is not set.
        expected_type: The type of the expected Python object.

    Returns:
        The converted list value.

    Raises:
        TypeError: In case the value of the environment variable is not of a
                   valid type.

    """
    # this needs to be here to avoid mutable defaults
    if default is None:
        default = []

    value = os.getenv(var)
    if value:
        try:
            loaded_value = json.loads(value)
            # check if loaded value is of correct type
            if expected_type is None or isinstance(
                loaded_value, expected_type
            ):
                return loaded_value
            else:
                raise TypeError  # if not correct type, raise TypeError
        except (TypeError, json.JSONDecodeError):
            # Use raw logging to avoid cyclic dependency
            logging.warning(
                f"Environment Variable {var} could not be loaded, into type "
                f"{expected_type}, defaulting to: {default}."
            )
            return default
    else:
        return default


def is_true_string_value(value: Any) -> bool:
    """Checks if the given value is a string representation of 'True'.

    Args:
        value: the value to check.

    Returns:
        Whether the input value represents a string version of 'True'.
    """
    return value in ["1", "y", "yes", "True", "true"]


def is_false_string_value(value: Any) -> bool:
    """Checks if the given value is a string representation of 'False'.

    Args:
        value: the value to check.

    Returns:
        Whether the input value represents a string version of 'False'.
    """
    return value in ["0", "n", "no", "False", "false"]


def handle_bool_env_var(var: str, default: bool = False) -> bool:
    """Converts normal env var to boolean.

    Args:
        var: The environment variable to convert.
        default: The default value to return if the env var is not set.

    Returns:
        The converted value.
    """
    value = os.getenv(var)
    if is_true_string_value(value):
        return True
    elif is_false_string_value(value):
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
ENV_ZENML_LOGGING_COLORS_DISABLED = "ZENML_LOGGING_COLORS_DISABLED"
ENV_ZENML_ANALYTICS_OPT_IN = "ZENML_ANALYTICS_OPT_IN"
ENV_ZENML_USER_ID = "ZENML_USER_ID"
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
ENV_ZENML_BACKUP_SECRETS_STORE_PREFIX = "ZENML_BACKUP_SECRETS_STORE_"
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
ENV_ZENML_SERVER = "ZENML_SERVER"
ENV_ZENML_ENFORCE_TYPE_ANNOTATIONS = "ZENML_ENFORCE_TYPE_ANNOTATIONS"
ENV_ZENML_ENABLE_IMPLICIT_AUTH_METHODS = "ZENML_ENABLE_IMPLICIT_AUTH_METHODS"
ENV_ZENML_DISABLE_STEP_LOGS_STORAGE = "ZENML_DISABLE_STEP_LOGS_STORAGE"
ENV_ZENML_IGNORE_FAILURE_HOOK = "ZENML_IGNORE_FAILURE_HOOK"
ENV_ZENML_CUSTOM_SOURCE_ROOT = "ZENML_CUSTOM_SOURCE_ROOT"
ENV_ZENML_WHEEL_PACKAGE_NAME = "ZENML_WHEEL_PACKAGE_NAME"
ENV_ZENML_PIPELINE_RUN_API_TOKEN_EXPIRATION = (
    "ZENML_PIPELINE_API_TOKEN_EXPIRATION"
)

# ZenML Server environment variables
ENV_ZENML_SERVER_PREFIX = "ZENML_SERVER_"
ENV_ZENML_SERVER_DEPLOYMENT_TYPE = f"{ENV_ZENML_SERVER_PREFIX}DEPLOYMENT_TYPE"
ENV_ZENML_SERVER_AUTH_SCHEME = f"{ENV_ZENML_SERVER_PREFIX}AUTH_SCHEME"
ENV_ZENML_SERVER_REPORTABLE_RESOURCES = (
    f"{ENV_ZENML_SERVER_PREFIX}REPORTABLE_RESOURCES"
)
ENV_ZENML_SERVER_AUTO_ACTIVATE = f"{ENV_ZENML_SERVER_PREFIX}AUTO_ACTIVATE"
ENV_ZENML_RUN_SINGLE_STEPS_WITHOUT_STACK = (
    "ZENML_RUN_SINGLE_STEPS_WITHOUT_STACK"
)
ENV_ZENML_PREVENT_CLIENT_SIDE_CACHING = "ZENML_PREVENT_CLIENT_SIDE_CACHING"
ENV_ZENML_DISABLE_CREDENTIALS_DISK_CACHING = "DISABLE_CREDENTIALS_DISK_CACHING"

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

# SQL Store backup directory subpath:
SQL_STORE_BACKUP_DIRECTORY_NAME = "database_backup"

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

CODE_HASH_PARAMETER_NAME = "step_source"

# Server settings
DEFAULT_ZENML_SERVER_NAME = "default"
DEFAULT_ZENML_SERVER_THREAD_POOL_SIZE = 40
DEFAULT_ZENML_JWT_TOKEN_LEEWAY = 10
DEFAULT_ZENML_JWT_TOKEN_ALGORITHM = "HS256"
DEFAULT_ZENML_AUTH_SCHEME = AuthScheme.OAUTH2_PASSWORD_BEARER
EXTERNAL_AUTHENTICATOR_TIMEOUT = 10  # seconds
DEFAULT_ZENML_SERVER_MAX_DEVICE_AUTH_ATTEMPTS = 3
DEFAULT_ZENML_SERVER_DEVICE_AUTH_TIMEOUT = 60 * 5  # 5 minutes
DEFAULT_ZENML_SERVER_DEVICE_AUTH_POLLING = 5  # seconds
DEFAULT_HTTP_TIMEOUT = 30
SERVICE_CONNECTOR_VERIFY_REQUEST_TIMEOUT = 120  # seconds
ZENML_API_KEY_PREFIX = "ZENKEY_"
DEFAULT_ZENML_SERVER_PIPELINE_RUN_AUTH_WINDOW = 60 * 48  # 48 hours
DEFAULT_ZENML_SERVER_LOGIN_RATE_LIMIT_MINUTE = 5
DEFAULT_ZENML_SERVER_LOGIN_RATE_LIMIT_DAY = 1000
DEFAULT_ZENML_SERVER_GENERIC_API_TOKEN_LIFETIME = 60 * 60  # 1 hour
DEFAULT_ZENML_SERVER_GENERIC_API_TOKEN_MAX_LIFETIME = (
    60 * 60 * 24 * 7
)  # 7 days

DEFAULT_ZENML_SERVER_SECURE_HEADERS_HSTS = (
    "max-age=63072000; includeSubdomains"
)
DEFAULT_ZENML_SERVER_SECURE_HEADERS_XFO = "SAMEORIGIN"
DEFAULT_ZENML_SERVER_SECURE_HEADERS_XXP = "0"
DEFAULT_ZENML_SERVER_SECURE_HEADERS_CONTENT = "nosniff"
_csp_script_src_urls = ["https://widgets-v3.featureos.app"]
_csp_connect_src_urls = [
    "https://sdkdocs.zenml.io",
    "https://analytics.zenml.io",
]
_csp_img_src_urls = [
    "https://public-flavor-logos.s3.eu-central-1.amazonaws.com",
    "https://avatar.vercel.sh",
]
_csp_frame_src_urls = [
    "https://zenml.hellonext.co",
    "https://sdkdocs.zenml.io",
    "https://widgets-v3.hellonext.co",
    "https://widgets-v3.featureos.app",
    "https://zenml.portal.trainn.co",
]
DEFAULT_ZENML_SERVER_SECURE_HEADERS_CSP = (
    "default-src 'none'; "
    f"script-src 'self' 'unsafe-inline' 'unsafe-eval' {' '.join(_csp_script_src_urls)}; "
    f"connect-src 'self' {' '.join(_csp_connect_src_urls)}; "
    f"img-src 'self' data: {' '.join(_csp_img_src_urls)}; "
    "style-src 'self' 'unsafe-inline'; "
    "base-uri 'self'; "
    "form-action 'self'; "
    "font-src 'self';"
    f"frame-src {' '.join(_csp_frame_src_urls)}"
)
DEFAULT_ZENML_SERVER_SECURE_HEADERS_REFERRER = "no-referrer-when-downgrade"
DEFAULT_ZENML_SERVER_SECURE_HEADERS_CACHE = (
    "no-store, no-cache, must-revalidate"
)
DEFAULT_ZENML_SERVER_SECURE_HEADERS_PERMISSIONS = (
    "accelerometer=(), autoplay=(), camera=(), encrypted-media=(), "
    "geolocation=(), gyroscope=(), magnetometer=(), microphone=(), midi=(), "
    "payment=(), sync-xhr=(), usb=()"
)
DEFAULT_ZENML_SERVER_SECURE_HEADERS_REPORT_TO = "default"
DEFAULT_ZENML_SERVER_REPORT_USER_ACTIVITY_TO_DB_SECONDS = 30
DEFAULT_ZENML_SERVER_MAX_REQUEST_BODY_SIZE_IN_BYTES = 256 * 1024 * 1024

# Configurations to decide which resources report their usage and check for
# entitlement in the case of a cloud deployment. Expected Format is this:
# ENV_ZENML_REPORTABLE_RESOURCES='["Foo", "bar"]'
REPORTABLE_RESOURCES: List[str] = handle_json_env_var(
    ENV_ZENML_SERVER_REPORTABLE_RESOURCES,
    expected_type=list,
    default=["pipeline", "pipeline_run", "model"],
)
REQUIRES_CUSTOM_RESOURCE_REPORTING = ["pipeline", "pipeline_run"]

# API Endpoint paths:
ACTIVATE = "/activate"
ACTIONS = "/actions"
API = "/api"
API_KEYS = "/api_keys"
API_KEY_ROTATE = "/rotate"
API_TOKEN = "/api_token"
ARTIFACTS = "/artifacts"
ARTIFACT_VERSIONS = "/artifact_versions"
ARTIFACT_VISUALIZATIONS = "/artifact_visualizations"
AUTH = "/auth"
BATCH = "/batch"
CODE_REFERENCES = "/code_references"
CODE_REPOSITORIES = "/code_repositories"
COMPONENT_TYPES = "/component-types"
CONFIG = "/config"
CURRENT_USER = "/current-user"
DEACTIVATE = "/deactivate"
DEVICES = "/devices"
DEVICE_AUTHORIZATION = "/device_authorization"
DEVICE_VERIFY = "/verify"
EMAIL_ANALYTICS = "/email-opt-in"
EVENT_FLAVORS = "/event-flavors"
EVENT_SOURCES = "/event-sources"
FLAVORS = "/flavors"
GET_OR_CREATE = "/get-or-create"
HEALTH = "/health"
INFO = "/info"
LOAD_INFO = "/load-info"
LOGIN = "/login"
LOGOUT = "/logout"
LOGS = "/logs"
PIPELINE_BUILDS = "/pipeline_builds"
PIPELINE_CONFIGURATION = "/pipeline-configuration"
PIPELINE_DEPLOYMENTS = "/pipeline_deployments"
PIPELINES = "/pipelines"
PIPELINE_SPEC = "/pipeline-spec"
PLUGIN_FLAVORS = "/plugin-flavors"
REFRESH = "/refresh"
RUNS = "/runs"
RUN_TEMPLATES = "/run_templates"
RUN_METADATA = "/run-metadata"
SCHEDULES = "/schedules"
SECRETS = "/secrets"
SECRETS_OPERATIONS = "/secrets_operations"
SECRETS_BACKUP = "/backup"
SECRETS_RESTORE = "/restore"
SERVER_SETTINGS = "/settings"
SERVICE_ACCOUNTS = "/service_accounts"
SERVICE_CONNECTOR_CLIENT = "/client"
SERVICE_CONNECTOR_RESOURCES = "/resources"
SERVICE_CONNECTOR_TYPES = "/service_connector_types"
SERVICE_CONNECTOR_VERIFY = "/verify"
SERVICE_CONNECTOR_FULL_STACK = "/full_stack_resources"
MODELS = "/models"
MODEL_VERSIONS = "/model_versions"
MODEL_VERSION_ARTIFACTS = "/model_version_artifacts"
MODEL_VERSION_PIPELINE_RUNS = "/model_version_pipeline_runs"
SERVICES = "/services"
SERVICE_CONNECTORS = "/service_connectors"
STACK = "/stack"
STACK_DEPLOYMENT = "/stack-deployment"
STACKS = "/stacks"
STACK_COMPONENTS = "/components"
STATISTICS = "/statistics"
STATUS = "/status"
STEP_CONFIGURATION = "/step-configuration"
STEPS = "/steps"
TAGS = "/tags"
TRIGGERS = "/triggers"
TRIGGER_EXECUTIONS = "/trigger_executions"
ONBOARDING_STATE = "/onboarding_state"
USERS = "/users"
URL = "/url"
VERSION_1 = "/v1"
VISUALIZE = "/visualize"
WEBHOOKS = "/webhooks"
WORKSPACES = "/workspaces"

# model metadata yaml file name
MODEL_METADATA_YAML_FILE_NAME = "model_metadata.yaml"

# orchestrator constants
ORCHESTRATOR_DOCKER_IMAGE_KEY = "orchestrator"

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
SORT_PIPELINES_BY_LATEST_RUN_KEY = "latest_run"

# Metadata constants
METADATA_ORCHESTRATOR_URL = "orchestrator_url"
METADATA_ORCHESTRATOR_LOGS_URL = "orchestrator_logs_url"
METADATA_ORCHESTRATOR_RUN_ID = "orchestrator_run_id"
METADATA_EXPERIMENT_TRACKER_URL = "experiment_tracker_url"
METADATA_DEPLOYED_MODEL_URL = "deployed_model_url"

# Model registries constants
MLFLOW_MODEL_FORMAT = "MLflow"

# Service connector constants
DOCKER_REGISTRY_RESOURCE_TYPE = "docker-registry"
KUBERNETES_CLUSTER_RESOURCE_TYPE = "kubernetes-cluster"

# Stack Recipe constants
STACK_RECIPES_GITHUB_REPO = "https://github.com/zenml-io/mlops-stacks.git"

# Parameters for internal ZenML Models
TEXT_FIELD_MAX_LENGTH = 65535
STR_FIELD_MAX_LENGTH = 255
MEDIUMTEXT_MAX_LENGTH = 2**24 - 1

# Model Control Plane constants
LATEST_MODEL_VERSION_PLACEHOLDER = "__latest__"


# Service connector constants
SERVICE_CONNECTOR_SKEW_TOLERANCE_SECONDS = 60 * 5  # 5 minutes

# Versioned entities
MAX_RETRIES_FOR_VERSIONED_ENTITY_CREATION = (
    10  # empirical value to pass heavy parallelized tests
)


FINISHED_ONBOARDING_SURVEY_KEY = "finished_onboarding_survey"

# Name validation
BANNED_NAME_CHARACTERS = "\t\n\r\v\f"


STACK_DEPLOYMENT_API_TOKEN_EXPIRATION = 60 * 6  # 6 hours

ZENML_PIPELINE_RUN_API_TOKEN_EXPIRATION = handle_int_env_var(
    ENV_ZENML_PIPELINE_RUN_API_TOKEN_EXPIRATION, default=0
)
