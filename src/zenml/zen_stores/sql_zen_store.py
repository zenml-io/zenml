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
"""SQL Zen Store implementation."""

import base64
import inspect
import json
import logging
import math
import os
import random
import re
import sys
import threading
import time
from collections import defaultdict
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    ClassVar,
    Dict,
    ForwardRef,
    List,
    Literal,
    NoReturn,
    Optional,
    Sequence,
    Set,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
    get_origin,
    overload,
)
from uuid import UUID

from packaging import version
from pydantic import (
    ConfigDict,
    Field,
    SecretStr,
    SerializeAsAny,
    field_validator,
    model_validator,
)
from sqlalchemy import QueuePool, func
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import (
    ArgumentError,
    IntegrityError,
)
from sqlalchemy.orm import Mapped, joinedload, noload
from sqlalchemy.sql.base import ExecutableOption
from sqlalchemy.util import immutabledict
from sqlmodel import Session as SqlModelSession

# Important to note: The select function of SQLModel works slightly differently
# from the select function of sqlalchemy. If you input only one entity on the
# select function of SQLModel, it automatically maps it to a SelectOfScalar.
# As a result, it will not return a tuple as a result, but the first entity in
# the tuple. While this is convenient in most cases, in unique cases like using
# the "add_columns" functionality, one might encounter unexpected results.
from sqlmodel import (
    SQLModel,
    and_,
    col,
    create_engine,
    delete,
    desc,
    or_,
    select,
)
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.analytics import track
from zenml.analytics.context import AnalyticsContext
from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import (
    analytics_disabler,
    track_decorator,
    track_handler,
)
from zenml.config.global_config import GlobalConfiguration
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.config.server_config import ServerConfiguration
from zenml.config.source import Source
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    DEFAULT_PASSWORD,
    DEFAULT_STACK_AND_COMPONENT_NAME,
    DEFAULT_USERNAME,
    ENV_ZENML_DEFAULT_USER_NAME,
    ENV_ZENML_DEFAULT_USER_PASSWORD,
    ENV_ZENML_DISABLE_DATABASE_MIGRATION,
    ENV_ZENML_SERVER,
    FINISHED_ONBOARDING_SURVEY_KEY,
    MAX_RETRIES_FOR_VERSIONED_ENTITY_CREATION,
    SQL_STORE_BACKUP_DIRECTORY_NAME,
    TEXT_FIELD_MAX_LENGTH,
    handle_bool_env_var,
    is_false_string_value,
    is_true_string_value,
)
from zenml.enums import (
    ArtifactSaveType,
    AuthScheme,
    DatabaseBackupStrategy,
    ExecutionStatus,
    LoggingLevels,
    MetadataResourceTypes,
    ModelStages,
    OnboardingStep,
    SecretsStoreType,
    StackComponentType,
    StackDeploymentProvider,
    StepRunInputArtifactType,
    StoreType,
    TaggableResourceTypes,
)
from zenml.exceptions import (
    AuthorizationException,
    BackupSecretsStoreNotConfiguredError,
    EntityCreationError,
    EntityExistsError,
    IllegalOperationError,
    SecretsStoreNotConfiguredError,
)
from zenml.io import fileio
from zenml.logger import get_console_handler, get_logger, get_logging_level
from zenml.metadata.metadata_types import get_metadata_type
from zenml.models import (
    ActionFilter,
    ActionRequest,
    ActionResponse,
    ActionUpdate,
    APIKeyFilter,
    APIKeyInternalResponse,
    APIKeyInternalUpdate,
    APIKeyRequest,
    APIKeyResponse,
    APIKeyRotateRequest,
    APIKeyUpdate,
    ArtifactFilter,
    ArtifactRequest,
    ArtifactResponse,
    ArtifactUpdate,
    ArtifactVersionFilter,
    ArtifactVersionRequest,
    ArtifactVersionResponse,
    ArtifactVersionUpdate,
    ArtifactVisualizationResponse,
    BaseFilter,
    BaseIdentifiedResponse,
    BaseRequest,
    BaseResponse,
    BaseUpdate,
    CodeReferenceRequest,
    CodeReferenceResponse,
    CodeRepositoryFilter,
    CodeRepositoryRequest,
    CodeRepositoryResponse,
    CodeRepositoryUpdate,
    ComponentFilter,
    ComponentRequest,
    ComponentResponse,
    ComponentUpdate,
    DefaultComponentRequest,
    DefaultStackRequest,
    DeployedStack,
    EventSourceFilter,
    EventSourceRequest,
    EventSourceResponse,
    EventSourceUpdate,
    FlavorFilter,
    FlavorRequest,
    FlavorResponse,
    FlavorUpdate,
    LogsResponse,
    ModelFilter,
    ModelRequest,
    ModelResponse,
    ModelUpdate,
    ModelVersionArtifactFilter,
    ModelVersionArtifactRequest,
    ModelVersionArtifactResponse,
    ModelVersionFilter,
    ModelVersionPipelineRunFilter,
    ModelVersionPipelineRunRequest,
    ModelVersionPipelineRunResponse,
    ModelVersionRequest,
    ModelVersionResponse,
    ModelVersionUpdate,
    OAuthDeviceFilter,
    OAuthDeviceInternalRequest,
    OAuthDeviceInternalResponse,
    OAuthDeviceInternalUpdate,
    OAuthDeviceResponse,
    OAuthDeviceUpdate,
    Page,
    PipelineBuildFilter,
    PipelineBuildRequest,
    PipelineBuildResponse,
    PipelineDeploymentFilter,
    PipelineDeploymentRequest,
    PipelineDeploymentResponse,
    PipelineFilter,
    PipelineRequest,
    PipelineResponse,
    PipelineRunDAG,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    PipelineUpdate,
    ProjectFilter,
    ProjectRequest,
    ProjectResponse,
    ProjectScopedFilter,
    ProjectScopedRequest,
    ProjectUpdate,
    RunMetadataRequest,
    RunMetadataResource,
    RunTemplateFilter,
    RunTemplateRequest,
    RunTemplateResponse,
    RunTemplateUpdate,
    ScheduleFilter,
    ScheduleRequest,
    ScheduleResponse,
    ScheduleUpdate,
    SecretFilter,
    SecretRequest,
    SecretResponse,
    SecretUpdate,
    ServerActivationRequest,
    ServerDatabaseType,
    ServerDeploymentType,
    ServerModel,
    ServerSettingsResponse,
    ServerSettingsUpdate,
    ServiceAccountFilter,
    ServiceAccountRequest,
    ServiceAccountResponse,
    ServiceAccountUpdate,
    ServiceConnectorFilter,
    ServiceConnectorRequest,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponse,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdate,
    ServiceFilter,
    ServiceRequest,
    ServiceResponse,
    ServiceUpdate,
    StackDeploymentConfig,
    StackDeploymentInfo,
    StackFilter,
    StackRequest,
    StackResponse,
    StackUpdate,
    StepRunFilter,
    StepRunRequest,
    StepRunResponse,
    StepRunUpdate,
    TagFilter,
    TagRequest,
    TagResourceRequest,
    TagResourceResponse,
    TagResponse,
    TagUpdate,
    TriggerExecutionFilter,
    TriggerExecutionRequest,
    TriggerExecutionResponse,
    TriggerFilter,
    TriggerRequest,
    TriggerResponse,
    TriggerUpdate,
    UserAuthModel,
    UserFilter,
    UserRequest,
    UserResponse,
    UserScopedRequest,
    UserUpdate,
)
from zenml.service_connectors.service_connector_registry import (
    service_connector_registry,
)
from zenml.stack.flavor_registry import FlavorRegistry
from zenml.stack_deployments.utils import get_stack_deployment_class
from zenml.utils import tag_utils, uuid_utils
from zenml.utils.enum_utils import StrEnum
from zenml.utils.networking_utils import (
    replace_localhost_with_internal_hostname,
)
from zenml.utils.secret_utils import PlainSerializedSecretStr
from zenml.utils.string_utils import (
    format_name_template,
    random_str,
    validate_name,
)
from zenml.utils.time_utils import utc_now
from zenml.zen_stores import template_utils
from zenml.zen_stores.base_zen_store import (
    BaseZenStore,
)
from zenml.zen_stores.dag_generator import DAGGeneratorHelper
from zenml.zen_stores.migrations.alembic import (
    Alembic,
)
from zenml.zen_stores.migrations.utils import MigrationUtils
from zenml.zen_stores.schemas import (
    ActionSchema,
    APIKeySchema,
    ArtifactSchema,
    ArtifactVersionSchema,
    BaseSchema,
    CodeReferenceSchema,
    CodeRepositorySchema,
    EventSourceSchema,
    FlavorSchema,
    ModelSchema,
    ModelVersionArtifactSchema,
    ModelVersionPipelineRunSchema,
    ModelVersionSchema,
    NamedSchema,
    OAuthDeviceSchema,
    PipelineBuildSchema,
    PipelineDeploymentSchema,
    PipelineRunSchema,
    PipelineSchema,
    ProjectSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    RunTemplateSchema,
    ScheduleSchema,
    SecretSchema,
    ServerSettingsSchema,
    ServiceConnectorSchema,
    StackComponentSchema,
    StackSchema,
    StepRunInputArtifactSchema,
    StepRunOutputArtifactSchema,
    StepRunParentsSchema,
    StepRunSchema,
    TagResourceSchema,
    TagSchema,
    TriggerExecutionSchema,
    UserSchema,
)
from zenml.zen_stores.schemas.artifact_visualization_schemas import (
    ArtifactVisualizationSchema,
)
from zenml.zen_stores.schemas.logs_schemas import LogsSchema
from zenml.zen_stores.schemas.service_schemas import ServiceSchema
from zenml.zen_stores.schemas.trigger_schemas import TriggerSchema
from zenml.zen_stores.schemas.utils import (
    get_resource_type_name,
    jl_arg,
)
from zenml.zen_stores.secrets_stores.base_secrets_store import BaseSecretsStore
from zenml.zen_stores.secrets_stores.sql_secrets_store import (
    SqlSecretsStoreConfiguration,
)

if TYPE_CHECKING:
    from zenml.metadata.metadata_types import MetadataType, MetadataTypeEnum

AnyNamedSchema = TypeVar("AnyNamedSchema", bound=NamedSchema)
AnySchema = TypeVar("AnySchema", bound=BaseSchema)

AnyResponse = TypeVar("AnyResponse", bound=BaseResponse)  # type: ignore[type-arg]  # noqa: F821
AnyIdentifiedResponse = TypeVar(
    "AnyIdentifiedResponse",
    bound=BaseIdentifiedResponse,  # type: ignore[type-arg]  # noqa: F821
)

# Enable SQL compilation caching to remove the https://sqlalche.me/e/14/cprf
# warning
SelectOfScalar.inherit_cache = True
Select.inherit_cache = True

logger = get_logger(__name__)

ZENML_SQLITE_DB_FILENAME = "zenml.db"


def exponential_backoff_with_jitter(
    attempt: int, base_duration: float = 0.05
) -> float:
    """Exponential backoff with jitter.

    Implemented the `Full jitter` algorithm described in
    https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

    Args:
        attempt: The backoff attempt.
        base_duration: The backoff base duration.

    Returns:
        The backoff duration.
    """
    exponential_backoff = base_duration * 1.5**attempt
    return random.uniform(0, exponential_backoff)


class Session(SqlModelSession):
    """Session subclass that automatically tracks duration and calling context."""

    def __enter__(self) -> "Session":
        """Enter the context manager.

        Returns:
            The SqlModel session.
        """
        if logger.isEnabledFor(logging.DEBUG):
            # Get the request ID from the current thread object
            self.request_id = threading.current_thread().name

            # Get SQLAlchemy connection pool info
            assert isinstance(self.bind, Engine)
            assert isinstance(self.bind.pool, QueuePool)
            checked_out_connections = self.bind.pool.checkedout()
            available_connections = self.bind.pool.checkedin()
            overflow = self.bind.pool.overflow()

            # Look up the stack to find the SQLZenStore method
            for frame in inspect.stack():
                if "self" in frame.frame.f_locals:
                    instance = frame.frame.f_locals["self"]
                    if isinstance(instance, SqlZenStore):
                        self.caller_method = (
                            f"{instance.__class__.__name__}.{frame.function}"
                        )
                        break
            else:
                self.caller_method = "unknown"

            logger.debug(
                f"[{self.request_id}] SQL STATS - "
                f"'{self.caller_method}' started [ conn(active): "
                f"{checked_out_connections} conn(idle): "
                f"{available_connections} conn(overflow): {overflow} ]"
            )

            self.start_time = time.time()

        return super().__enter__()

    def __exit__(
        self,
        exc_type: Optional[Any],
        exc_val: Optional[Any],
        exc_tb: Optional[Any],
    ) -> None:
        """Exit the context manager.

        Args:
            exc_type: The exception type.
            exc_val: The exception value.
            exc_tb: The exception traceback.
        """
        if logger.isEnabledFor(logging.DEBUG):
            duration = (time.time() - self.start_time) * 1000

            # Get SQLAlchemy connection pool info
            assert isinstance(self.bind, Engine)
            assert isinstance(self.bind.pool, QueuePool)
            checked_out_connections = self.bind.pool.checkedout()
            available_connections = self.bind.pool.checkedin()
            overflow = self.bind.pool.overflow()
            logger.debug(
                f"[{self.request_id}] SQL STATS - "
                f"'{self.caller_method}' completed in "
                f"{duration:.2f}ms [ conn(active): "
                f"{checked_out_connections} conn(idle): "
                f"{available_connections} conn(overflow): {overflow} ]"
            )
        super().__exit__(exc_type, exc_val, exc_tb)


class SQLDatabaseDriver(StrEnum):
    """SQL database drivers supported by the SQL ZenML store."""

    MYSQL = "mysql"
    SQLITE = "sqlite"


class SqlZenStoreConfiguration(StoreConfiguration):
    """SQL ZenML store configuration.

    Attributes:
        type: The type of the store.
        secrets_store: The configuration of the secrets store to use.
            This defaults to a SQL secrets store that extends the SQL ZenML
            store.
        backup_secrets_store: The configuration of a backup secrets store to
            use in addition to the primary one as an intermediate step during
            the migration to a new secrets store.
        driver: The SQL database driver.
        database: database name. If not already present on the server, it will
            be created automatically on first access.
        username: The database username.
        password: The database password.
        ssl: Whether to use SSL.
        ssl_ca: certificate authority certificate. Required for SSL
            enabled authentication if the CA certificate is not part of the
            certificates shipped by the operating system.
        ssl_cert: client certificate. Required for SSL enabled
            authentication if client certificates are used.
        ssl_key: client certificate private key. Required for SSL
            enabled if client certificates are used.
        ssl_verify_server_cert: set to verify the identity of the server
            against the provided server certificate.
        pool_size: The maximum number of connections to keep in the SQLAlchemy
            pool.
        max_overflow: The maximum number of connections to allow in the
            SQLAlchemy pool in addition to the pool_size.
        pool_pre_ping: Enable emitting a test statement on the SQL connection
            at the start of each connection pool checkout, to test that the
            database connection is still viable.
    """

    type: StoreType = StoreType.SQL

    secrets_store: Optional[SerializeAsAny[SecretsStoreConfiguration]] = None
    backup_secrets_store: Optional[
        SerializeAsAny[SecretsStoreConfiguration]
    ] = None

    driver: Optional[SQLDatabaseDriver] = None
    database: Optional[str] = None
    username: Optional[PlainSerializedSecretStr] = None
    password: Optional[PlainSerializedSecretStr] = None
    ssl: bool = False
    ssl_ca: Optional[PlainSerializedSecretStr] = None
    ssl_cert: Optional[PlainSerializedSecretStr] = None
    ssl_key: Optional[PlainSerializedSecretStr] = None
    ssl_verify_server_cert: bool = False
    pool_size: int = 20
    max_overflow: int = 20
    pool_pre_ping: bool = True

    backup_strategy: DatabaseBackupStrategy = DatabaseBackupStrategy.IN_MEMORY
    # database backup directory
    backup_directory: str = Field(
        default_factory=lambda: os.path.join(
            GlobalConfiguration().config_directory,
            SQL_STORE_BACKUP_DIRECTORY_NAME,
        )
    )
    backup_database: Optional[str] = None

    @field_validator("secrets_store")
    @classmethod
    def validate_secrets_store(
        cls, secrets_store: Optional[SecretsStoreConfiguration]
    ) -> SecretsStoreConfiguration:
        """Ensures that the secrets store is initialized with a default SQL secrets store.

        Args:
            secrets_store: The secrets store config to be validated.

        Returns:
            The validated secrets store config.
        """
        if secrets_store is None:
            secrets_store = SqlSecretsStoreConfiguration()

        return secrets_store

    @model_validator(mode="after")
    def _validate_backup_strategy(self) -> "SqlZenStoreConfiguration":
        """Validate the backup strategy.

        Returns:
            The model attribute values.

        Raises:
            ValueError: If the backup database name is not set when the backup
                database is requested.
        """
        if (
            self.backup_strategy == DatabaseBackupStrategy.DATABASE
            and not self.backup_database
        ):
            raise ValueError(
                "The `backup_database` attribute must also be set if the "
                "backup strategy is set to use a backup database."
            )

        return self

    @model_validator(mode="after")
    def _validate_url(self) -> "SqlZenStoreConfiguration":
        """Validate the SQL URL.

        The validator also moves the MySQL username, password and database
        parameters from the URL into the other configuration arguments, if they
        are present in the URL.

        Returns:
            The validated values.

        Raises:
            ValueError: If the URL is invalid or the SQL driver is not
                supported.
        """
        if self.url is None:
            return self

        # When running inside a container, if the URL uses localhost, the
        # target service will not be available. We try to replace localhost
        # with one of the special Docker or K3D internal hostnames.
        url = replace_localhost_with_internal_hostname(self.url)

        try:
            sql_url = make_url(url)
        except ArgumentError as e:
            raise ValueError(
                "Invalid SQL URL `%s`: %s. The URL must be in the format "
                "`driver://[[username:password@]hostname:port]/database["
                "?<extra-args>]`.",
                url,
                str(e),
            )

        if sql_url.drivername not in SQLDatabaseDriver.values():
            raise ValueError(
                "Invalid SQL driver value `%s`: The driver must be one of: %s.",
                url,
                ", ".join(SQLDatabaseDriver.values()),
            )
        self.driver = SQLDatabaseDriver(sql_url.drivername)
        if sql_url.drivername == SQLDatabaseDriver.SQLITE:
            if (
                sql_url.username
                or sql_url.password
                or sql_url.query
                or sql_url.database is None
            ):
                raise ValueError(
                    "Invalid SQLite URL `%s`: The URL must be in the "
                    "format `sqlite:///path/to/database.db`.",
                    url,
                )
            if self.username or self.password:
                raise ValueError(
                    "Invalid SQLite configuration: The username and password "
                    "must not be set",
                    url,
                )
            self.database = sql_url.database
        elif sql_url.drivername == SQLDatabaseDriver.MYSQL:
            if sql_url.username:
                self.username = PlainSerializedSecretStr(sql_url.username)
                sql_url = sql_url._replace(username=None)
            if sql_url.password:
                self.password = PlainSerializedSecretStr(sql_url.password)
                sql_url = sql_url._replace(password=None)
            if sql_url.database:
                self.database = sql_url.database
                sql_url = sql_url._replace(database=None)
            if sql_url.query:

                def _get_query_result(
                    result: Union[str, Tuple[str, ...]],
                ) -> Optional[str]:
                    """Returns the only or the first result of a query.

                    Args:
                        result: The result of the query.

                    Returns:
                        The only or the first result, None otherwise.
                    """
                    if isinstance(result, str):
                        return result
                    elif isinstance(result, tuple) and len(result) > 0:
                        return result[0]
                    else:
                        return None

                for k, v in sql_url.query.items():
                    if k == "ssl":
                        if r := _get_query_result(v):
                            self.ssl = is_true_string_value(r)
                    elif k == "ssl_ca":
                        if r := _get_query_result(v):
                            self.ssl_ca = PlainSerializedSecretStr(r)
                            self.ssl = True
                    elif k == "ssl_cert":
                        if r := _get_query_result(v):
                            self.ssl_cert = PlainSerializedSecretStr(r)
                            self.ssl = True
                    elif k == "ssl_key":
                        if r := _get_query_result(v):
                            self.ssl_key = PlainSerializedSecretStr(r)
                            self.ssl = True
                    elif k == "ssl_verify_server_cert":
                        if r := _get_query_result(v):
                            if is_true_string_value(r):
                                self.ssl_verify_server_cert = True
                            elif is_false_string_value(r):
                                self.ssl_verify_server_cert = False
                    else:
                        raise ValueError(
                            "Invalid MySQL URL query parameter `%s`: The "
                            "parameter must be one of: ssl, ssl_ca, ssl_cert, "
                            "ssl_key, or ssl_verify_server_cert.",
                            k,
                        )
                sql_url = sql_url._replace(query=immutabledict())

            database = self.database
            if not self.username or not self.password or not database:
                raise ValueError(
                    "Invalid MySQL configuration: The username, password and "
                    "database must be set in the URL or as configuration "
                    "attributes",
                )

            regexp = r"^[^\\/?%*:|\"<>.-]{1,64}$"
            match = re.match(regexp, database)
            if not match:
                raise ValueError(
                    f"The database name does not conform to the required "
                    f"format "
                    f"rules ({regexp}): {database}"
                )

            # Save the certificates in a secure location on disk
            secret_folder = Path(
                GlobalConfiguration().local_stores_path,
                "certificates",
            )
            for key in ["ssl_key", "ssl_ca", "ssl_cert"]:
                content = getattr(self, key)
                if content and not os.path.isfile(content.get_secret_value()):
                    fileio.makedirs(str(secret_folder))
                    file_path = Path(secret_folder, f"{key}.pem")
                    with os.fdopen(
                        os.open(
                            file_path, flags=os.O_RDWR | os.O_CREAT, mode=0o600
                        ),
                        "w",
                    ) as f:
                        f.write(content.get_secret_value())
                    setattr(self, key, str(file_path))

        self.url = str(sql_url)
        return self

    @staticmethod
    def get_local_url(path: str) -> str:
        """Get a local SQL url for a given local path.

        Args:
            path: The path to the local sqlite file.

        Returns:
            The local SQL url for the given path.
        """
        return f"sqlite:///{path}/{ZENML_SQLITE_DB_FILENAME}"

    @classmethod
    def supports_url_scheme(cls, url: str) -> bool:
        """Check if a URL scheme is supported by this store.

        Args:
            url: The URL to check.

        Returns:
            True if the URL scheme is supported, False otherwise.
        """
        return make_url(url).drivername in SQLDatabaseDriver.values()

    def get_sqlalchemy_config(
        self,
        database: Optional[str] = None,
    ) -> Tuple[URL, Dict[str, Any], Dict[str, Any]]:
        """Get the SQLAlchemy engine configuration for the SQL ZenML store.

        Args:
            database: Custom database name to use. If not set, the database name
                from the configuration will be used.

        Returns:
            The URL and connection arguments for the SQLAlchemy engine.

        Raises:
            NotImplementedError: If the SQL driver is not supported.
        """
        sql_url = make_url(self.url)
        sqlalchemy_connect_args: Dict[str, Any] = {}
        engine_args = {}
        if sql_url.drivername == SQLDatabaseDriver.SQLITE:
            assert self.database is not None
            # The following default value is needed for sqlite to avoid the
            # Error:
            #   sqlite3.ProgrammingError: SQLite objects created in a thread can
            #   only be used in that same thread.
            sqlalchemy_connect_args = {"check_same_thread": False}
        elif sql_url.drivername == SQLDatabaseDriver.MYSQL:
            # all these are guaranteed by our root validator
            assert self.database is not None
            assert self.username is not None
            assert self.password is not None
            assert sql_url.host is not None

            if not database:
                database = self.database

            engine_args = {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_pre_ping": self.pool_pre_ping,
            }

            sql_url = sql_url._replace(
                drivername="mysql+pymysql",
                username=self.username.get_secret_value(),
                password=self.password.get_secret_value(),
                database=database,
            )

            sqlalchemy_ssl_args: Dict[str, Any] = {}

            # Handle SSL params
            if self.ssl:
                sqlalchemy_ssl_args["ssl"] = True
                for key in ["ssl_key", "ssl_ca", "ssl_cert"]:
                    ssl_setting = getattr(self, key)
                    if not ssl_setting:
                        continue
                    if not os.path.isfile(ssl_setting.get_secret_value()):
                        logger.warning(
                            f"Database SSL setting `{key}` is not a file. "
                        )
                    sqlalchemy_ssl_args[key.removeprefix("ssl_")] = (
                        ssl_setting.get_secret_value()
                    )
                sqlalchemy_ssl_args["check_hostname"] = (
                    self.ssl_verify_server_cert
                )
                sqlalchemy_connect_args["ssl"] = sqlalchemy_ssl_args
        else:
            raise NotImplementedError(
                f"SQL driver `{sql_url.drivername}` is not supported."
            )

        return sql_url, sqlalchemy_connect_args, engine_args

    model_config = ConfigDict(
        # Don't validate attributes when assigning them. This is necessary
        # because the certificate attributes can be expanded to the contents
        # of the certificate files.
        validate_assignment=False,
        # Forbid extra attributes set in the class.
        extra="ignore",
    )


class SqlZenStore(BaseZenStore):
    """Store Implementation that uses SQL database backend.

    Attributes:
        config: The configuration of the SQL ZenML store.
        skip_migrations: Whether to skip migrations when initializing the store.
        TYPE: The type of the store.
        CONFIG_TYPE: The type of the store configuration.
        _engine: The SQLAlchemy engine.
    """

    config: SqlZenStoreConfiguration
    skip_migrations: bool = False
    TYPE: ClassVar[StoreType] = StoreType.SQL
    CONFIG_TYPE: ClassVar[Type[StoreConfiguration]] = SqlZenStoreConfiguration

    _engine: Optional[Engine] = None
    _migration_utils: Optional[MigrationUtils] = None
    _alembic: Optional[Alembic] = None
    _secrets_store: Optional[BaseSecretsStore] = None
    _backup_secrets_store: Optional[BaseSecretsStore] = None
    _should_send_user_enriched_events: bool = False
    _cached_onboarding_state: Optional[Set[str]] = None
    _default_user: Optional[UserResponse] = None

    @property
    def secrets_store(self) -> "BaseSecretsStore":
        """The secrets store associated with this store.

        Returns:
            The secrets store associated with this store.

        Raises:
            SecretsStoreNotConfiguredError: If no secrets store is configured.
        """
        if self._secrets_store is None:
            raise SecretsStoreNotConfiguredError(
                "No secrets store is configured. Please configure a secrets "
                "store to create and manage ZenML secrets."
            )

        return self._secrets_store

    @property
    def backup_secrets_store(self) -> Optional["BaseSecretsStore"]:
        """The backup secrets store associated with this store.

        Returns:
            The backup secrets store associated with this store.
        """
        return self._backup_secrets_store

    @property
    def engine(self) -> Engine:
        """The SQLAlchemy engine.

        Returns:
            The SQLAlchemy engine.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._engine:
            raise ValueError("Store not initialized")
        return self._engine

    @property
    def migration_utils(self) -> MigrationUtils:
        """The migration utils.

        Returns:
            The migration utils.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._migration_utils:
            raise ValueError("Store not initialized")
        return self._migration_utils

    @property
    def alembic(self) -> Alembic:
        """The Alembic wrapper.

        Returns:
            The Alembic wrapper.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._alembic:
            raise ValueError("Store not initialized")
        return self._alembic

    def _send_user_enriched_events_if_necessary(self) -> None:
        """Send user enriched event for all existing users."""
        if not self._should_send_user_enriched_events:
            return

        logger.debug("Sending user enriched events for legacy users.")
        self._should_send_user_enriched_events = False

        server_config = ServerConfiguration.get_server_config()

        if server_config.deployment_type == ServerDeploymentType.CLOUD:
            # Do not send events for Pro workspaces where the event comes from
            # the Pro API
            return

        query = select(UserSchema).where(
            UserSchema.is_service_account.is_(False)  # type: ignore[attr-defined]
        )

        with Session(self.engine) as session:
            users = session.exec(query).unique().all()

            for user_orm in users:
                user_model = user_orm.to_model(
                    include_metadata=True, include_private=True
                )

                if not user_model.email:
                    continue

                if (
                    FINISHED_ONBOARDING_SURVEY_KEY
                    not in user_model.user_metadata
                ):
                    continue

                analytics_metadata = {
                    **user_model.user_metadata,
                    "email": user_model.email,
                    "newsletter": user_model.email_opted_in,
                    "name": user_model.name,
                    "full_name": user_model.full_name,
                }
                with AnalyticsContext() as context:
                    context.user_id = user_model.id

                    context.track(
                        event=AnalyticsEvent.USER_ENRICHED,
                        properties=analytics_metadata,
                    )

    @classmethod
    def filter_and_paginate(
        cls,
        session: Session,
        query: Union[Select[Any], SelectOfScalar[Any]],
        table: Type[AnySchema],
        filter_model: BaseFilter,
        custom_schema_to_model_conversion: Optional[
            Callable[..., AnyResponse]
        ] = None,
        custom_fetch: Optional[
            Callable[
                [
                    Session,
                    Union[Select[Any], SelectOfScalar[Any]],
                    BaseFilter,
                ],
                Sequence[Any],
            ]
        ] = None,
        hydrate: bool = False,
        apply_query_options_from_schema: bool = False,
    ) -> Page[AnyResponse]:
        """Given a query, return a Page instance with a list of filtered Models.

        Args:
            session: The SQLModel Session
            query: The query to execute
            table: The table to select from
            filter_model: The filter to use, including pagination and sorting
            custom_schema_to_model_conversion: Callable to convert the schema
                into a model. This is used if the Model contains additional
                data that is not explicitly stored as a field or relationship
                on the model.
            custom_fetch: Custom callable to use to fetch items from the
                database for a given query. This is used if the items fetched
                from the database need to be processed differently (e.g. to
                perform additional filtering). The callable should take a
                `Session`, a `Select` query and a `BaseFilterModel` filter as
                arguments and return a `List` of items.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            apply_query_options_from_schema: Flag deciding whether to apply
                query options defined on the schema.

        Returns:
            The Domain Model representation of the DB resource

        Raises:
            ValueError: if the filtered page number is out of bounds.
            RuntimeError: if the schema does not have a `to_model` method.
        """
        query = filter_model.apply_filter(query=query, table=table)
        query = filter_model.apply_sorting(query=query, table=table)
        query = query.distinct()

        # Get the total amount of items in the database for a given query
        custom_fetch_result: Optional[Sequence[Any]] = None
        if custom_fetch:
            custom_fetch_result = custom_fetch(session, query, filter_model)
            total = len(custom_fetch_result)
        else:
            result = session.scalar(
                select(func.count()).select_from(
                    query.options(noload("*")).subquery()
                )
            )

            if result:
                total = result
            else:
                total = 0

        # Get the total amount of pages in the database for a given query
        if total == 0:
            total_pages = 1
        else:
            total_pages = math.ceil(total / filter_model.size)

        if filter_model.page > total_pages:
            raise ValueError(
                f"Invalid page {filter_model.page}. The requested page size is "
                f"{filter_model.size} and there are a total of {total} items "
                f"for this query. The maximum page value therefore is "
                f"{total_pages}."
            )

        query_options = table.get_query_options(
            include_metadata=hydrate, include_resources=True
        )
        if apply_query_options_from_schema and query_options:
            query = query.options(*query_options)

        # Get a page of the actual data
        item_schemas: Sequence[AnySchema]
        if custom_fetch:
            assert custom_fetch_result is not None
            item_schemas = custom_fetch_result
            # select the items in the current page
            item_schemas = item_schemas[
                filter_model.offset : filter_model.offset + filter_model.size
            ]
        else:
            query_result = session.exec(
                query.limit(filter_model.size).offset(filter_model.offset)
            )
            item_schemas = query_result.all()

        # Convert this page of items from schemas to models.
        items: List[AnyResponse] = []
        for schema in item_schemas:
            # If a custom conversion function is provided, use it.
            if custom_schema_to_model_conversion:
                items.append(custom_schema_to_model_conversion(schema))
                continue
            # Otherwise, try to use the `to_model` method of the schema.
            to_model = getattr(schema, "to_model", None)
            if callable(to_model):
                items.append(
                    to_model(include_metadata=hydrate, include_resources=True)
                )
                continue
            # If neither of the above work, raise an error.
            raise RuntimeError(
                f"Cannot convert schema `{schema.__class__.__name__}` to model "
                "since it does not have a `to_model` method."
            )

        return Page[Any](
            total=total,
            total_pages=total_pages,
            items=items,
            index=filter_model.page,
            max_size=filter_model.size,
        )

    # ====================================
    # ZenML Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the SQL store."""
        logger.debug("Initializing SqlZenStore at %s", self.config.url)

        url, connect_args, engine_args = self.config.get_sqlalchemy_config()
        self._engine = create_engine(
            url=url, connect_args=connect_args, **engine_args
        )
        self._migration_utils = MigrationUtils(
            url=url,
            connect_args=connect_args,
            engine_args=engine_args,
        )

        # SQLite: As long as the parent directory exists, SQLAlchemy will
        # automatically create the database.
        if (
            self.config.driver == SQLDatabaseDriver.SQLITE
            and self.config.database
            and not fileio.exists(self.config.database)
        ):
            fileio.makedirs(os.path.dirname(self.config.database))

        # MySQL: We might need to create the database manually.
        # To do so, we create a new engine that connects to the `mysql` database
        # and then create the desired database.
        # See https://stackoverflow.com/a/8977109
        if (
            self.config.driver == SQLDatabaseDriver.MYSQL
            and self.config.database
        ):
            if not self.migration_utils.database_exists():
                self.migration_utils.create_database()

        self._alembic = Alembic(self.engine)

        if (
            not self.skip_migrations
            and ENV_ZENML_DISABLE_DATABASE_MIGRATION not in os.environ
        ):
            self.migrate_database()

        secrets_store_config = self.config.secrets_store

        # Initialize the secrets store
        if (
            secrets_store_config
            and secrets_store_config.type != SecretsStoreType.NONE
        ):
            secrets_store_class = BaseSecretsStore.get_store_class(
                secrets_store_config
            )
            self._secrets_store = secrets_store_class(
                zen_store=self,
                config=secrets_store_config,
            )
            # Update the config with the actual secrets store config
            # to reflect the default values in the saved configuration
            self.config.secrets_store = self._secrets_store.config

        backup_secrets_store_config = self.config.backup_secrets_store

        # Initialize the backup secrets store, if configured
        if (
            backup_secrets_store_config
            and backup_secrets_store_config.type != SecretsStoreType.NONE
        ):
            secrets_store_class = BaseSecretsStore.get_store_class(
                backup_secrets_store_config
            )
            self._backup_secrets_store = secrets_store_class(
                zen_store=self,
                config=backup_secrets_store_config,
            )
            # Update the config with the actual secrets store config
            # to reflect the default values in the saved configuration
            self.config.backup_secrets_store = (
                self._backup_secrets_store.config
            )

    def _initialize_database(self) -> None:
        """Initialize the database if not already initialized."""
        if self._default_project_enabled:
            # Make sure the default project exists
            self._get_or_create_default_project()
        # Make sure the default stack exists
        self._get_or_create_default_stack()
        # Make sure the server is activated and the default user exists, if
        # applicable
        self._auto_activate_server()

        # Send user enriched events that we missed due to a bug in 0.57.0
        self._send_user_enriched_events_if_necessary()

    def _get_db_backup_file_path(self) -> str:
        """Get the path to the database backup file.

        Returns:
            The path to the configured database backup file.
        """
        if self.config.driver == SQLDatabaseDriver.SQLITE:
            return os.path.join(
                self.config.backup_directory,
                # Add the -backup suffix to the database filename
                ZENML_SQLITE_DB_FILENAME[:-3] + "-backup.db",
            )

        # For a MySQL database, we need to dump the database to a JSON
        # file
        return os.path.join(
            self.config.backup_directory,
            f"{self.engine.url.database}-backup.json",
        )

    def backup_database(
        self,
        strategy: Optional[DatabaseBackupStrategy] = None,
        location: Optional[str] = None,
        overwrite: bool = False,
    ) -> Tuple[str, Any]:
        """Backup the database.

        Args:
            strategy: Custom backup strategy to use. If not set, the backup
                strategy from the store configuration will be used.
            location: Custom target location to backup the database to. If not
                set, the configured backup location will be used. Depending on
                the backup strategy, this can be a file path or a database name.
            overwrite: Whether to overwrite an existing backup if it exists.
                If set to False, the existing backup will be reused.

        Returns:
            The location where the database was backed up to and an accompanying
            user-friendly message that describes the backup location, or None
            if no backup was created (i.e. because the backup already exists).

        Raises:
            ValueError: If the backup database name is not set when the backup
                database is requested or if the backup strategy is invalid.
        """
        strategy = strategy or self.config.backup_strategy

        if (
            strategy == DatabaseBackupStrategy.DUMP_FILE
            or self.config.driver == SQLDatabaseDriver.SQLITE
        ):
            dump_file = location or self._get_db_backup_file_path()

            if not overwrite and os.path.isfile(dump_file):
                logger.warning(
                    f"A previous backup file already exists at '{dump_file}'. "
                    "Reusing the existing backup."
                )
            else:
                self.migration_utils.backup_database_to_file(
                    dump_file=dump_file
                )
            return f"the '{dump_file}' backup file", dump_file
        elif strategy == DatabaseBackupStrategy.DATABASE:
            backup_db_name = location or self.config.backup_database
            if not backup_db_name:
                raise ValueError(
                    "The backup database name must be set in the store "
                    "configuration to use the backup database strategy."
                )

            if not overwrite and self.migration_utils.database_exists(
                backup_db_name
            ):
                logger.warning(
                    "A previous backup database already exists at "
                    f"'{backup_db_name}'. Reusing the existing backup."
                )
            else:
                self.migration_utils.backup_database_to_db(
                    backup_db_name=backup_db_name
                )
            return f"the '{backup_db_name}' backup database", backup_db_name
        elif strategy == DatabaseBackupStrategy.IN_MEMORY:
            return (
                "memory",
                self.migration_utils.backup_database_to_memory(),
            )

        else:
            raise ValueError(f"Invalid backup strategy: {strategy}.")

    def restore_database(
        self,
        strategy: Optional[DatabaseBackupStrategy] = None,
        location: Optional[Any] = None,
        cleanup: bool = False,
    ) -> None:
        """Restore the database.

        Args:
            strategy: Custom backup strategy to use. If not set, the backup
                strategy from the store configuration will be used.
            location: Custom target location to restore the database from. If
                not set, the configured backup location will be used. Depending
                on the backup strategy, this can be a file path, a database
                name or an in-memory database representation.
            cleanup: Whether to cleanup the backup after restoring the database.

        Raises:
            ValueError: If the backup database name is not set when the backup
                database is requested or if the backup strategy is invalid.
        """
        strategy = strategy or self.config.backup_strategy

        if (
            strategy == DatabaseBackupStrategy.DUMP_FILE
            or self.config.driver == SQLDatabaseDriver.SQLITE
        ):
            dump_file = location or self._get_db_backup_file_path()
            self.migration_utils.restore_database_from_file(
                dump_file=dump_file
            )
        elif strategy == DatabaseBackupStrategy.DATABASE:
            backup_db_name = location or self.config.backup_database
            if not backup_db_name:
                raise ValueError(
                    "The backup database name must be set in the store "
                    "configuration to use the backup database strategy."
                )

            self.migration_utils.restore_database_from_db(
                backup_db_name=backup_db_name
            )
        elif strategy == DatabaseBackupStrategy.IN_MEMORY:
            if location is None or not isinstance(location, list):
                raise ValueError(
                    "The in-memory database representation must be provided "
                    "to restore the database from an in-memory backup."
                )
            self.migration_utils.restore_database_from_memory(db_dump=location)

        else:
            raise ValueError(f"Invalid backup strategy: {strategy}.")

        if cleanup:
            self.cleanup_database_backup()

    def cleanup_database_backup(
        self,
        strategy: Optional[DatabaseBackupStrategy] = None,
        location: Optional[Any] = None,
    ) -> None:
        """Delete the database backup.

        Args:
            strategy: Custom backup strategy to use. If not set, the backup
                strategy from the store configuration will be used.
            location: Custom target location to delete the database backup
                from. If not set, the configured backup location will be used.
                Depending on the backup strategy, this can be a file path or a
                database name.

        Raises:
            ValueError: If the backup database name is not set when the backup
                database is requested.
        """
        strategy = strategy or self.config.backup_strategy

        if (
            strategy == DatabaseBackupStrategy.DUMP_FILE
            or self.config.driver == SQLDatabaseDriver.SQLITE
        ):
            dump_file = location or self._get_db_backup_file_path()
            if dump_file is not None and os.path.isfile(dump_file):
                try:
                    os.remove(dump_file)
                except OSError:
                    logger.warning(
                        f"Failed to cleanup database dump file {dump_file}."
                    )
                else:
                    logger.info(
                        f"Successfully cleaned up database dump file "
                        f"{dump_file}."
                    )
        elif strategy == DatabaseBackupStrategy.DATABASE:
            backup_db_name = location or self.config.backup_database

            if not backup_db_name:
                raise ValueError(
                    "The backup database name must be set in the store "
                    "configuration to use the backup database strategy."
                )
            if self.migration_utils.database_exists(backup_db_name):
                # Drop the backup database
                self.migration_utils.drop_database(
                    database=backup_db_name,
                )
                logger.info(
                    f"Successfully cleaned up backup database "
                    f"{backup_db_name}."
                )

    def migrate_database(self) -> None:
        """Migrate the database to the head as defined by the python package.

        Raises:
            RuntimeError: If the database exists and is not empty but has never
                been migrated with alembic before.
        """
        alembic_logger = logging.getLogger("alembic")

        # remove all existing handlers
        while len(alembic_logger.handlers):
            alembic_logger.removeHandler(alembic_logger.handlers[0])

        logging_level = get_logging_level()

        # suppress alembic info logging if the zenml logging level is not debug
        if logging_level == LoggingLevels.DEBUG:
            alembic_logger.setLevel(logging.DEBUG)
        else:
            alembic_logger.setLevel(logging.WARNING)

        alembic_logger.addHandler(get_console_handler())

        # We need to account for 3 distinct cases here:
        # 1. the database is completely empty (not initialized)
        # 2. the database is not empty and has been migrated with alembic before
        # 3. the database is not empty, but has never been migrated with alembic
        #   before (i.e. was created with SQLModel back when alembic wasn't
        #   used). We don't support this direct upgrade case anymore.
        current_revisions = self.alembic.current_revisions()
        head_revisions = self.alembic.head_revisions()
        if len(current_revisions) >= 1:
            # Case 2: the database has been migrated with alembic before. Just
            # upgrade to the latest revision.
            if len(current_revisions) > 1:
                logger.warning(
                    "The ZenML database has more than one migration head "
                    "revision. This is not expected and might indicate a "
                    "database migration problem. Please raise an issue on "
                    "GitHub if you encounter this."
                )

            logger.debug("Current revisions: %s", current_revisions)
            logger.debug("Head revisions: %s", head_revisions)

            # If the current revision and head revision don't match, a database
            # migration that changes the database structure or contents may
            # actually be performed, in which case we enable the backup
            # functionality. We only enable the backup functionality if the
            # database will actually be changed, to avoid the overhead for
            # unnecessary backups.
            backup_enabled = (
                self.config.backup_strategy != DatabaseBackupStrategy.DISABLED
                and set(current_revisions) != set(head_revisions)
            )
            backup_location: Optional[Any] = None
            backup_location_msg: Optional[str] = None

            if backup_enabled:
                try:
                    logger.info("Backing up the database before migration.")
                    (
                        backup_location_msg,
                        backup_location,
                    ) = self.backup_database(overwrite=True)
                except Exception as e:
                    # The database backup feature was not entirely functional
                    # in ZenML 0.56.3 and earlier, due to inconsistencies in the
                    # database schema. If the database is at version 0.56.3
                    # or earlier and if the backup fails, we only log the
                    # exception and leave the upgrade process to proceed.
                    allow_backup_failures = False
                    try:
                        if version.parse(
                            current_revisions[0]
                        ) <= version.parse("0.56.3"):
                            allow_backup_failures = True
                    except version.InvalidVersion:
                        # This can happen if the database is not currently
                        # stamped with an official ZenML version (e.g. in
                        # development environments).
                        pass

                    if allow_backup_failures:
                        logger.exception(
                            "Failed to backup the database. The database "
                            "upgrade will proceed without a backup."
                        )
                    else:
                        raise RuntimeError(
                            f"Failed to backup the database: {str(e)}. "
                            "Please check the logs for more details. "
                            "If you would like to disable the database backup "
                            "functionality, set the `backup_strategy` attribute "
                            "of the store configuration to `disabled`."
                        ) from e
                else:
                    if backup_location is not None:
                        logger.info(
                            "Database successfully backed up to "
                            f"{backup_location_msg}. If something goes wrong "
                            "with the upgrade, ZenML will attempt to restore "
                            "the database from this backup automatically."
                        )

            try:
                self.alembic.upgrade()
            except Exception as e:
                if backup_enabled and backup_location:
                    logger.exception(
                        "Failed to migrate the database. Attempting to restore "
                        f"the database from {backup_location_msg}."
                    )
                    try:
                        self.restore_database(location=backup_location)
                    except Exception:
                        logger.exception(
                            "Failed to restore the database from "
                            f"{backup_location_msg}. Please "
                            "check the logs for more details. You might need "
                            "to restore the database manually."
                        )
                    else:
                        raise RuntimeError(
                            "The database migration failed, but the database "
                            "was successfully restored from the backup. "
                            "You can safely retry the upgrade or revert to "
                            "the previous version of ZenML. Please check the "
                            "logs for more details."
                        ) from e
                raise RuntimeError(
                    f"The database migration failed: {str(e)}"
                ) from e

            else:
                # We always remove the backup after a successful upgrade,
                # not just to avoid cluttering the disk, but also to avoid
                # reusing an outdated database from the backup in case of
                # future upgrade failures.
                try:
                    self.cleanup_database_backup()
                except Exception:
                    logger.exception("Failed to cleanup the database backup.")

        elif self.alembic.db_is_empty():
            # Case 1: the database is empty. We can just create the
            # tables from scratch with from SQLModel. After tables are
            # created we put an alembic revision to latest and initialize
            # the settings table with needed info.
            logger.info("Creating database tables")
            with self.engine.begin() as conn:
                SQLModel.metadata.create_all(conn)
            with Session(self.engine) as session:
                server_config = ServerConfiguration.get_server_config()

                # Initialize the settings
                id_ = (
                    server_config.external_server_id
                    or GlobalConfiguration().user_id
                )
                session.add(
                    ServerSettingsSchema(
                        id=id_,
                        server_name=server_config.server_name,
                        # We always initialize the server as inactive and decide
                        # whether to activate it later in `_initialize_database`
                        active=False,
                        enable_analytics=GlobalConfiguration().analytics_opt_in,
                        display_announcements=server_config.display_announcements,
                        display_updates=server_config.display_updates,
                        logo_url=None,
                        onboarding_state=None,
                    )
                )
                session.commit()
            self.alembic.stamp("head")
        else:
            # Case 3: the database is not empty, but has never been
            # migrated with alembic before. We don't support this direct
            # upgrade case anymore. The user needs to run a two-step
            # upgrade.
            raise RuntimeError(
                "The ZenML database has never been migrated with alembic "
                "before. This can happen if you are performing a direct "
                "upgrade from a really old version of ZenML. This direct "
                "upgrade path is not supported anymore. Please upgrade "
                "your ZenML installation first to 0.54.0 or an earlier "
                "version and then to the latest version."
            )

        # If an alembic migration took place, all non-custom flavors are purged
        #  and the FlavorRegistry recreates all in-built and integration
        #  flavors in the db.
        revisions_afterwards = self.alembic.current_revisions()

        if current_revisions != revisions_afterwards:
            try:
                if current_revisions and version.parse(
                    current_revisions[0]
                ) < version.parse("0.57.1"):
                    # We want to send the missing user enriched events for users
                    # which were created pre 0.57.1 and only on one upgrade
                    self._should_send_user_enriched_events = True
            except version.InvalidVersion:
                # This can happen if the database is not currently
                # stamped with an official ZenML version (e.g. in
                # development environments).
                pass

            self._sync_flavors()

    def _sync_flavors(self) -> None:
        """Purge all in-built and integration flavors from the DB and sync."""
        FlavorRegistry().register_flavors(store=self)

    def get_store_info(self) -> ServerModel:
        """Get information about the store.

        Returns:
            Information about the store.
        """
        model = super().get_store_info()
        sql_url = make_url(self.config.url)
        model.database_type = ServerDatabaseType(sql_url.drivername)
        settings = self.get_server_settings(hydrate=True)
        # Fetch the deployment ID from the database and use it to replace
        # the one fetched from the global configuration
        model.id = settings.server_id
        model.name = settings.server_name
        model.active = settings.active
        model.last_user_activity = settings.last_user_activity
        model.analytics_enabled = settings.enable_analytics
        return model

    def get_deployment_id(self) -> UUID:
        """Get the ID of the deployment.

        Returns:
            The ID of the deployment.

        Raises:
            KeyError: If the deployment ID could not be loaded from the
                database.
        """
        # Fetch the deployment ID from the database
        with Session(self.engine) as session:
            identity = session.exec(select(ServerSettingsSchema)).first()

            if identity is None:
                raise KeyError(
                    "The deployment ID could not be loaded from the database."
                )
            return identity.id

    # -------------------- Server Settings --------------------

    def _get_server_settings(self, session: Session) -> ServerSettingsSchema:
        """Get the server settings or fail.

        Args:
            session: SQLAlchemy session to use.

        Returns:
            The settings table.

        Raises:
            RuntimeError: If the settings table is not found.
        """
        settings = session.exec(select(ServerSettingsSchema)).first()

        if settings is None:
            raise RuntimeError("The server settings have not been initialized")

        return settings

    def get_server_settings(
        self, hydrate: bool = True
    ) -> ServerSettingsResponse:
        """Get the server settings.

        Args:
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The server settings.
        """
        with Session(self.engine) as session:
            settings = self._get_server_settings(session=session)
            return settings.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def update_server_settings(
        self, settings_update: ServerSettingsUpdate
    ) -> ServerSettingsResponse:
        """Update the server settings.

        Args:
            settings_update: The server settings update.

        Returns:
            The updated server settings.
        """
        with Session(self.engine) as session:
            settings = self._get_server_settings(session=session)

            analytics_metadata = settings_update.model_dump(
                include={
                    "enable_analytics",
                    "display_announcements",
                    "display_updates",
                },
                exclude_none=True,
            )
            # Filter to only include the values that changed in this update
            analytics_metadata = {
                key: value
                for key, value in analytics_metadata.items()
                if getattr(settings, key) != value
            }

            track(
                event=AnalyticsEvent.SERVER_SETTINGS_UPDATED,
                metadata=analytics_metadata,
            )

            settings.update(settings_update)
            session.add(settings)
            session.commit()
            session.refresh(settings)

            return settings.to_model(
                include_metadata=True, include_resources=True
            )

    def _update_last_user_activity_timestamp(
        self, last_user_activity: datetime
    ) -> None:
        """Update the last user activity timestamp.

        Args:
            last_user_activity: The timestamp of latest user activity
                traced by server instance.
        """
        with Session(self.engine) as session:
            settings = self._get_server_settings(session=session)

            if last_user_activity < settings.last_user_activity.replace(
                tzinfo=None
            ):
                return

            settings.last_user_activity = last_user_activity
            # `updated` kept intentionally unchanged here
            session.add(settings)
            session.commit()
            session.refresh(settings)

    def get_onboarding_state(self) -> List[str]:
        """Get the server onboarding state.

        Returns:
            The server onboarding state.
        """
        with Session(self.engine) as session:
            settings = self._get_server_settings(session=session)
            if settings.onboarding_state:
                self._cached_onboarding_state = set(
                    json.loads(settings.onboarding_state)
                )
                return list(self._cached_onboarding_state)
            else:
                return []

    def _update_onboarding_state(
        self, completed_steps: Set[str], session: Session
    ) -> None:
        """Update the server onboarding state.

        Args:
            completed_steps: Newly completed onboarding steps.
            session: DB session.
        """
        if self._cached_onboarding_state and completed_steps.issubset(
            self._cached_onboarding_state
        ):
            # All the onboarding steps are already completed, no need to query
            # the DB
            return

        settings = self._get_server_settings(session=session)
        settings.update_onboarding_state(completed_steps=completed_steps)
        session.add(settings)
        session.commit()
        session.refresh(settings)

        assert settings.onboarding_state
        self._cached_onboarding_state = set(
            json.loads(settings.onboarding_state)
        )

    def update_onboarding_state(self, completed_steps: Set[str]) -> None:
        """Update the server onboarding state.

        Args:
            completed_steps: Newly completed onboarding steps.
        """
        with Session(self.engine) as session:
            self._update_onboarding_state(
                completed_steps=completed_steps, session=session
            )

    def activate_server(
        self, request: ServerActivationRequest
    ) -> Optional[UserResponse]:
        """Activate the server and optionally create the default admin user.

        Args:
            request: The server activation request.

        Returns:
            The default admin user that was created, if any.

        Raises:
            IllegalOperationError: If the server is already active.
        """
        with Session(self.engine) as session:
            settings = self._get_server_settings(session=session)

            if settings.active:
                # The server can only be activated once
                raise IllegalOperationError("The server is already active.")

            settings.update(request)
            settings.active = True
            session.add(settings)
            session.commit()

        # Update the server settings to reflect the activation
        self.update_server_settings(request)

        if request.admin_username and request.admin_password is not None:
            # Create the default admin user
            return self.create_user(
                UserRequest(
                    name=request.admin_username,
                    active=True,
                    password=request.admin_password,
                    is_admin=True,
                )
            )

        return None

    def _auto_activate_server(self) -> None:
        """Automatically activate the server if needed."""
        settings = self.get_server_settings()

        if settings.active:
            # Activation only happens once
            return

        if not self._activate_server_at_initialization():
            # The server is not configured to be activated automatically
            return

        # Activate the server
        request = ServerActivationRequest()
        if self._create_default_user_on_db_init():
            # Create the default admin user too, if needed

            request.admin_username = os.getenv(
                ENV_ZENML_DEFAULT_USER_NAME, DEFAULT_USERNAME
            )
            request.admin_password = os.getenv(
                ENV_ZENML_DEFAULT_USER_PASSWORD, DEFAULT_PASSWORD
            )

        self.activate_server(request)

    # -------------------- Actions  --------------------

    def create_action(self, action: ActionRequest) -> ActionResponse:
        """Create an action.

        Args:
            action: The action to create.

        Returns:
            The created action.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=action, session=session)

            self._verify_name_uniqueness(
                resource=action,
                schema=ActionSchema,
                session=session,
            )

            # Verify that the given service account exists
            self._get_account_schema(
                account_name_or_id=action.service_account_id,
                session=session,
                service_account=True,
            )

            new_action = ActionSchema.from_request(action)
            session.add(new_action)
            session.commit()
            session.refresh(new_action)

            return new_action.to_model(
                include_metadata=True, include_resources=True
            )

    def get_action(
        self,
        action_id: UUID,
        hydrate: bool = True,
    ) -> ActionResponse:
        """Get an action by ID.

        Args:
            action_id: The ID of the action to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The action.
        """
        with Session(self.engine) as session:
            action = self._get_schema_by_id(
                resource_id=action_id,
                schema_class=ActionSchema,
                session=session,
            )

            return action.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_actions(
        self,
        action_filter_model: ActionFilter,
        hydrate: bool = False,
    ) -> Page[ActionResponse]:
        """List all actions matching the given filter criteria.

        Args:
            action_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of actions matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=action_filter_model,
                session=session,
            )
            query = select(ActionSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ActionSchema,
                filter_model=action_filter_model,
                hydrate=hydrate,
            )

    def update_action(
        self,
        action_id: UUID,
        action_update: ActionUpdate,
    ) -> ActionResponse:
        """Update an existing action.

        Args:
            action_id: The ID of the action to update.
            action_update: The update to be applied to the action.

        Returns:
            The updated action.
        """
        with Session(self.engine) as session:
            action = self._get_schema_by_id(
                resource_id=action_id,
                schema_class=ActionSchema,
                session=session,
            )

            if action_update.service_account_id:
                # Verify that the given service account exists
                self._get_account_schema(
                    account_name_or_id=action_update.service_account_id,
                    session=session,
                    service_account=True,
                )

            # In case of a renaming update, make sure no action already exists
            # with that name
            self._verify_name_uniqueness(
                resource=action_update,
                schema=action,
                session=session,
            )

            action.update(action_update=action_update)
            session.add(action)
            session.commit()

            session.refresh(action)

            return action.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_action(self, action_id: UUID) -> None:
        """Delete an action.

        Args:
            action_id: The ID of the action to delete.

        Raises:
            IllegalOperationError: If the action can't be deleted
                because it's used by triggers.
        """
        with Session(self.engine) as session:
            action = self._get_schema_by_id(
                resource_id=action_id,
                schema_class=ActionSchema,
                session=session,
            )

            # Prevent deletion of action if it is used by a trigger
            if action.triggers:
                raise IllegalOperationError(
                    f"Unable to delete action with ID `{action_id}` "
                    f"as it is used by {len(action.triggers)} triggers."
                )

            session.delete(action)
            session.commit()

    # ------------------------- API Keys -------------------------

    def _get_api_key(
        self,
        service_account_id: UUID,
        api_key_name_or_id: Union[str, UUID],
        session: Session,
    ) -> APIKeySchema:
        """Helper method to fetch an API key by name or ID.

        Args:
            service_account_id: The ID of the service account for which to
                fetch the API key.
            api_key_name_or_id: The name or ID of the API key to get.
            session: The database session to use for the query.

        Returns:
            The requested API key.

        Raises:
            KeyError: if the name or ID does not identify an API key that is
                configured for the given service account.
        """
        # Fetch the service account, to make sure it exists
        service_account = self._get_account_schema(
            service_account_id, session=session, service_account=True
        )

        if uuid_utils.is_valid_uuid(api_key_name_or_id):
            filter_params = APIKeySchema.id == api_key_name_or_id
        else:
            filter_params = APIKeySchema.name == api_key_name_or_id

        api_key = session.exec(
            select(APIKeySchema)
            .where(filter_params)
            .where(APIKeySchema.service_account_id == service_account.id)
        ).first()

        if api_key is None:
            raise KeyError(
                f"An API key with ID or name '{api_key_name_or_id}' is not "
                f"configured for service account with ID "
                f"'{service_account_id}'."
            )
        return api_key

    def create_api_key(
        self, service_account_id: UUID, api_key: APIKeyRequest
    ) -> APIKeyResponse:
        """Create a new API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to
                create the API key.
            api_key: The API key to create.

        Returns:
            The created API key.

        Raises:
            EntityExistsError: If an API key with the same name is already
                configured for the same service account.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=api_key, session=session)

            # Fetch the service account
            service_account = self._get_account_schema(
                service_account_id, session=session, service_account=True
            )

            # Check if a key with the same name already exists for the same
            # service account
            try:
                self._get_api_key(
                    service_account_id=service_account.id,
                    api_key_name_or_id=api_key.name,
                    session=session,
                )
                raise EntityExistsError(
                    f"Unable to register API key with name '{api_key.name}': "
                    "Found an existing API key with the same name configured "
                    f"for the same '{service_account.name}' service account."
                )
            except KeyError:
                pass

            new_api_key, key_value = APIKeySchema.from_request(
                service_account_id=service_account.id,
                request=api_key,
            )
            session.add(new_api_key)
            session.commit()

            api_key_model = new_api_key.to_model(
                include_metadata=True, include_resources=True
            )
            api_key_model.set_key(key_value)
            return api_key_model

    def get_api_key(
        self,
        service_account_id: UUID,
        api_key_name_or_id: Union[str, UUID],
        hydrate: bool = True,
    ) -> APIKeyResponse:
        """Get an API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to fetch
                the API key.
            api_key_name_or_id: The name or ID of the API key to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The API key with the given ID.
        """
        with Session(self.engine) as session:
            api_key = self._get_api_key(
                service_account_id=service_account_id,
                api_key_name_or_id=api_key_name_or_id,
                session=session,
            )
            return api_key.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def get_internal_api_key(
        self, api_key_id: UUID, hydrate: bool = True
    ) -> APIKeyInternalResponse:
        """Get internal details for an API key by its unique ID.

        Args:
            api_key_id: The ID of the API key to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The internal details for the API key with the given ID.

        Raises:
            KeyError: if the API key doesn't exist.
        """
        with Session(self.engine) as session:
            api_key = session.exec(
                select(APIKeySchema).where(APIKeySchema.id == api_key_id)
            ).first()
            if api_key is None:
                raise KeyError(f"API key with ID {api_key_id} not found.")
            return api_key.to_internal_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_api_keys(
        self,
        service_account_id: UUID,
        filter_model: APIKeyFilter,
        hydrate: bool = False,
    ) -> Page[APIKeyResponse]:
        """List all API keys for a service account matching the given filter criteria.

        Args:
            service_account_id: The ID of the service account for which to list
                the API keys.
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all API keys matching the filter criteria.
        """
        with Session(self.engine) as session:
            # Fetch the service account
            service_account = self._get_account_schema(
                service_account_id, session=session, service_account=True
            )

            filter_model.set_service_account(service_account.id)
            query = select(APIKeySchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=APIKeySchema,
                filter_model=filter_model,
                hydrate=hydrate,
            )

    def update_api_key(
        self,
        service_account_id: UUID,
        api_key_name_or_id: Union[str, UUID],
        api_key_update: APIKeyUpdate,
    ) -> APIKeyResponse:
        """Update an API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to update
                the API key.
            api_key_name_or_id: The name or ID of the API key to update.
            api_key_update: The update request on the API key.

        Returns:
            The updated API key.

        Raises:
            EntityExistsError: if the API key update would result in a name
                conflict with an existing API key for the same service account.
        """
        with Session(self.engine) as session:
            api_key = self._get_api_key(
                service_account_id=service_account_id,
                api_key_name_or_id=api_key_name_or_id,
                session=session,
            )

            if api_key_update.name and api_key.name != api_key_update.name:
                # Check if a key with the new name already exists for the same
                # service account
                try:
                    self._get_api_key(
                        service_account_id=service_account_id,
                        api_key_name_or_id=api_key_update.name,
                        session=session,
                    )

                    raise EntityExistsError(
                        f"Unable to update API key with name "
                        f"'{api_key_update.name}': Found an existing API key "
                        "with the same name configured for the same "
                        f"'{api_key.service_account.name}' service account."
                    )
                except KeyError:
                    pass

            api_key.update(update=api_key_update)
            session.add(api_key)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(api_key)
            return api_key.to_model(
                include_metadata=True, include_resources=True
            )

    def update_internal_api_key(
        self, api_key_id: UUID, api_key_update: APIKeyInternalUpdate
    ) -> APIKeyResponse:
        """Update an API key with internal details.

        Args:
            api_key_id: The ID of the API key.
            api_key_update: The update request on the API key.

        Returns:
            The updated API key.

        Raises:
            KeyError: if the API key doesn't exist.
        """
        with Session(self.engine) as session:
            api_key = session.exec(
                select(APIKeySchema).where(APIKeySchema.id == api_key_id)
            ).first()

            if not api_key:
                raise KeyError(f"API key with ID {api_key_id} not found.")

            api_key.internal_update(update=api_key_update)
            session.add(api_key)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(api_key)
            return api_key.to_model(
                include_metadata=True, include_resources=True
            )

    def rotate_api_key(
        self,
        service_account_id: UUID,
        api_key_name_or_id: Union[str, UUID],
        rotate_request: APIKeyRotateRequest,
    ) -> APIKeyResponse:
        """Rotate an API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to
                rotate the API key.
            api_key_name_or_id: The name or ID of the API key to rotate.
            rotate_request: The rotate request on the API key.

        Returns:
            The updated API key.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=rotate_request, session=session
            )

            api_key = self._get_api_key(
                service_account_id=service_account_id,
                api_key_name_or_id=api_key_name_or_id,
                session=session,
            )

            _, new_key = api_key.rotate(rotate_request)
            session.add(api_key)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(api_key)
            api_key_model = api_key.to_model()
            api_key_model.set_key(new_key)

            return api_key_model

    def delete_api_key(
        self,
        service_account_id: UUID,
        api_key_name_or_id: Union[str, UUID],
    ) -> None:
        """Delete an API key for a service account.

        Args:
            service_account_id: The ID of the service account for which to
                delete the API key.
            api_key_name_or_id: The name or ID of the API key to delete.
        """
        with Session(self.engine) as session:
            api_key = self._get_api_key(
                service_account_id=service_account_id,
                api_key_name_or_id=api_key_name_or_id,
                session=session,
            )

            session.delete(api_key)
            session.commit()

    # -------------------- Services --------------------

    @staticmethod
    def _fail_if_service_with_config_exists(
        service_request: ServiceRequest, session: Session
    ) -> None:
        """Raise an exception if a service with same name/config exists.

        Args:
            service_request: The service to check for.
            session: The database session to use for the query.

        Raises:
            EntityExistsError: If a service with the given name and
                type already exists.
        """
        # Check if service with the same domain key (name, config, project)
        # already exists
        existing_domain_service = session.exec(
            select(ServiceSchema).where(
                ServiceSchema.config
                == base64.b64encode(
                    json.dumps(
                        service_request.config,
                        sort_keys=False,
                    ).encode("utf-8")
                )
            )
        ).first()

        if existing_domain_service:
            raise EntityExistsError(
                f"Unable to create service '{service_request.name}' with the "
                "given configuration: A service with the same configuration "
                "already exists."
            )

    def create_service(self, service: ServiceRequest) -> ServiceResponse:
        """Create a new service.

        Args:
            service: The service to create.

        Returns:
            The newly created service.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=service, session=session)
            # Check if a service with the given name already exists
            self._fail_if_service_with_config_exists(
                service_request=service,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=service,
                reference_schema=PipelineRunSchema,
                reference_id=service.pipeline_run_id,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=service,
                reference_schema=ModelVersionSchema,
                reference_id=service.model_version_id,
                session=session,
            )

            service_schema = ServiceSchema.from_request(service)
            logger.debug("Creating service: %s", service_schema)
            session.add(service_schema)
            session.commit()

            return service_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def get_service(
        self, service_id: UUID, hydrate: bool = True
    ) -> ServiceResponse:
        """Get a service.

        Args:
            service_id: The ID of the service to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The service.
        """
        with Session(self.engine) as session:
            service = self._get_schema_by_id(
                resource_id=service_id,
                schema_class=ServiceSchema,
                session=session,
            )
            return service.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_services(
        self, filter_model: ServiceFilter, hydrate: bool = False
    ) -> Page[ServiceResponse]:
        """List all services matching the given filter criteria.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all services matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=filter_model,
                session=session,
            )
            query = select(ServiceSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ServiceSchema,
                filter_model=filter_model,
                hydrate=hydrate,
            )

    def update_service(
        self, service_id: UUID, update: ServiceUpdate
    ) -> ServiceResponse:
        """Update a service.

        Args:
            service_id: The ID of the service to update.
            update: The update to be applied to the service.

        Returns:
            The updated service.
        """
        with Session(self.engine) as session:
            existing_service = self._get_schema_by_id(
                resource_id=service_id,
                schema_class=ServiceSchema,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=existing_service,
                reference_schema=ModelVersionSchema,
                reference_id=update.model_version_id,
                session=session,
            )

            # Update the schema itself.
            existing_service.update(update=update)
            logger.debug("Updated service: %s", existing_service)
            session.add(existing_service)
            session.commit()
            session.refresh(existing_service)
            return existing_service.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_service(self, service_id: UUID) -> None:
        """Delete a service.

        Args:
            service_id: The ID of the service to delete.
        """
        with Session(self.engine) as session:
            existing_service = self._get_schema_by_id(
                resource_id=service_id,
                schema_class=ServiceSchema,
                session=session,
            )

            # Delete the service
            session.delete(existing_service)
            session.commit()

    # -------------------- Artifacts --------------------

    def create_artifact(self, artifact: ArtifactRequest) -> ArtifactResponse:
        """Creates a new artifact.

        Args:
            artifact: The artifact to create.

        Returns:
            The newly created artifact.
        """
        validate_name(artifact)
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=artifact, session=session)

            # Check if an artifact with the given name already exists
            self._verify_name_uniqueness(
                resource=artifact,
                schema=ArtifactSchema,
                session=session,
            )

            # Create the artifact.
            artifact_schema = ArtifactSchema.from_request(artifact)

            session.add(artifact_schema)
            session.commit()

            # Save tags of the artifact.
            self._attach_tags_to_resources(
                tags=artifact.tags,
                resources=artifact_schema,
                session=session,
            )
            session.refresh(artifact_schema)

            return artifact_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def get_artifact(
        self, artifact_id: UUID, hydrate: bool = True
    ) -> ArtifactResponse:
        """Gets an artifact.

        Args:
            artifact_id: The ID of the artifact to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact.
        """
        with Session(self.engine) as session:
            artifact = self._get_schema_by_id(
                resource_id=artifact_id,
                schema_class=ArtifactSchema,
                session=session,
            )
            return artifact.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_artifacts(
        self, filter_model: ArtifactFilter, hydrate: bool = False
    ) -> Page[ArtifactResponse]:
        """List all artifacts matching the given filter criteria.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all artifacts matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=filter_model,
                session=session,
            )
            query = select(ArtifactSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ArtifactSchema,
                filter_model=filter_model,
                hydrate=hydrate,
            )

    def update_artifact(
        self, artifact_id: UUID, artifact_update: ArtifactUpdate
    ) -> ArtifactResponse:
        """Updates an artifact.

        Args:
            artifact_id: The ID of the artifact to update.
            artifact_update: The update to be applied to the artifact.

        Returns:
            The updated artifact.
        """
        with Session(self.engine) as session:
            existing_artifact = self._get_schema_by_id(
                resource_id=artifact_id,
                schema_class=ArtifactSchema,
                session=session,
            )

            self._verify_name_uniqueness(
                resource=artifact_update,
                schema=existing_artifact,
                session=session,
            )

            # Update the schema itself.
            existing_artifact.update(artifact_update=artifact_update)
            session.add(existing_artifact)
            session.commit()
            session.refresh(existing_artifact)

            # Handle tag updates.
            self._attach_tags_to_resources(
                tags=artifact_update.add_tags,
                resources=existing_artifact,
                session=session,
            )
            self._detach_tags_from_resources(
                tags=artifact_update.remove_tags,
                resources=existing_artifact,
                session=session,
            )
            session.refresh(existing_artifact)
            return existing_artifact.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_artifact(self, artifact_id: UUID) -> None:
        """Deletes an artifact.

        Args:
            artifact_id: The ID of the artifact to delete.
        """
        with Session(self.engine) as session:
            existing_artifact = self._get_schema_by_id(
                resource_id=artifact_id,
                schema_class=ArtifactSchema,
                session=session,
            )
            session.delete(existing_artifact)
            session.commit()

    # -------------------- Artifact Versions --------------------

    def _get_or_create_artifact_for_name(
        self,
        name: str,
        project_id: UUID,
        has_custom_name: bool,
        session: Session,
    ) -> ArtifactSchema:
        """Get or create an artifact with a specific name.

        Args:
            name: The artifact name.
            project_id: The project ID.
            has_custom_name: Whether the artifact has a custom name.
            session: DB session.

        Returns:
            Schema of the artifact.
        """
        artifact_query = (
            select(ArtifactSchema)
            .where(ArtifactSchema.name == name)
            .where(ArtifactSchema.project_id == project_id)
        )
        artifact = session.exec(artifact_query).first()

        if artifact is None:
            try:
                with session.begin_nested():
                    artifact_request = ArtifactRequest(
                        name=name,
                        project=project_id,
                        has_custom_name=has_custom_name,
                    )
                    self._set_request_user_id(
                        request_model=artifact_request, session=session
                    )
                    artifact = ArtifactSchema.from_request(artifact_request)
                    session.add(artifact)
                    session.commit()
                session.refresh(artifact)
            except IntegrityError:
                # We have to rollback the failed session first in order to
                # continue using it
                session.rollback()
                # We failed to create the artifact due to the unique constraint
                # for artifact names -> The artifact was already created, we can
                # just fetch it from the DB now
                artifact = session.exec(artifact_query).one()

        if artifact.has_custom_name is False and has_custom_name:
            # If a new version with custom name was created for an artifact
            # that previously had no custom name, we update it.
            artifact.has_custom_name = True
            session.commit()
            session.refresh(artifact)

        return artifact

    def _get_next_numeric_version_for_artifact(
        self, session: Session, artifact_id: UUID
    ) -> int:
        """Get the next numeric version for an artifact.

        Args:
            session: DB session.
            artifact_id: ID of the artifact for which to get the next numeric
                version.

        Returns:
            The next numeric version.
        """
        current_max_version = session.exec(
            select(func.max(ArtifactVersionSchema.version_number)).where(
                ArtifactVersionSchema.artifact_id == artifact_id
            )
        ).first()

        if current_max_version is None:
            return 1
        else:
            return int(current_max_version) + 1

    def create_artifact_version(
        self, artifact_version: ArtifactVersionRequest
    ) -> ArtifactVersionResponse:
        """Create an artifact version.

        Args:
            artifact_version: The artifact version to create.

        Raises:
            EntityExistsError: If an artifact version with the same name
                already exists.
            EntityCreationError: If the artifact version creation failed.

        Returns:
            The created artifact version.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=artifact_version, session=session
            )

            self._get_reference_schema_by_id(
                resource=artifact_version,
                reference_schema=StackComponentSchema,
                reference_id=artifact_version.artifact_store_id,
                session=session,
                reference_type="artifact store",
            )

            if artifact_name := artifact_version.artifact_name:
                artifact_schema = self._get_or_create_artifact_for_name(
                    name=artifact_name,
                    project_id=artifact_version.project,
                    has_custom_name=artifact_version.has_custom_name,
                    session=session,
                )
                artifact_version.artifact_id = artifact_schema.id

            assert artifact_version.artifact_id

            artifact_version_schema: Optional[ArtifactVersionSchema] = None

            if artifact_version.version is None:
                # No explicit version in the request -> We will try to
                # auto-increment the numeric version of the artifact version
                remaining_tries = MAX_RETRIES_FOR_VERSIONED_ENTITY_CREATION
                while remaining_tries > 0:
                    remaining_tries -= 1
                    try:
                        artifact_version.version = str(
                            self._get_next_numeric_version_for_artifact(
                                session=session,
                                artifact_id=artifact_version.artifact_id,
                            )
                        )

                        artifact_version_schema = (
                            ArtifactVersionSchema.from_request(
                                artifact_version
                            )
                        )
                        session.add(artifact_version_schema)
                        session.commit()
                    except IntegrityError:
                        # We have to rollback the failed session first in order
                        # to continue using it
                        session.rollback()
                        if remaining_tries == 0:
                            raise EntityCreationError(
                                f"Failed to create version for artifact "
                                f"{artifact_schema.name}. This is most likely "
                                "caused by multiple parallel requests that try "
                                "to create versions for this artifact in the "
                                "database."
                            )
                        else:
                            attempt = (
                                MAX_RETRIES_FOR_VERSIONED_ENTITY_CREATION
                                - remaining_tries
                            )
                            sleep_duration = exponential_backoff_with_jitter(
                                attempt=attempt
                            )

                            logger.debug(
                                "Failed to create artifact version %s "
                                "(version %s) due to an integrity error. "
                                "Retrying in %f seconds.",
                                artifact_schema.name,
                                artifact_version.version,
                                sleep_duration,
                            )
                            time.sleep(sleep_duration)
                    else:
                        break
            else:
                # An explicit version was specified for the artifact version.
                # We don't do any incrementing and fail immediately if the
                # version already exists.
                try:
                    artifact_version_schema = (
                        ArtifactVersionSchema.from_request(artifact_version)
                    )
                    session.add(artifact_version_schema)
                    session.commit()
                except IntegrityError:
                    # We have to rollback the failed session first in order
                    # to continue using it
                    session.rollback()
                    raise EntityExistsError(
                        f"Unable to create artifact version "
                        f"{artifact_schema.name} (version "
                        f"{artifact_version.version}): An artifact with the "
                        "same name and version already exists."
                    )

            assert artifact_version_schema is not None

            # Save visualizations of the artifact
            if artifact_version.visualizations:
                for vis in artifact_version.visualizations:
                    vis_schema = ArtifactVisualizationSchema.from_model(
                        artifact_visualization_request=vis,
                        artifact_version_id=artifact_version_schema.id,
                    )
                    session.add(vis_schema)

            # Save tags of the artifact
            self._attach_tags_to_resources(
                tags=artifact_version.tags,
                resources=artifact_version_schema,
                session=session,
            )

            # Save metadata of the artifact
            if artifact_version.metadata:
                values: Dict[str, "MetadataType"] = {}
                types: Dict[str, "MetadataTypeEnum"] = {}
                for key, value in artifact_version.metadata.items():
                    # Skip metadata that is too large to be stored in the DB.
                    if len(json.dumps(value)) > TEXT_FIELD_MAX_LENGTH:
                        logger.warning(
                            f"Metadata value for key '{key}' is too large to be "
                            "stored in the database. Skipping."
                        )
                        continue
                    # Skip metadata that is not of a supported type.
                    try:
                        metadata_type = get_metadata_type(value)
                    except ValueError as e:
                        logger.warning(
                            f"Metadata value for key '{key}' is not of a "
                            f"supported type. Skipping. Full error: {e}"
                        )
                        continue
                    values[key] = value
                    types[key] = metadata_type
                self.create_run_metadata(
                    RunMetadataRequest(
                        project=artifact_version.project,
                        resources=[
                            RunMetadataResource(
                                id=artifact_version_schema.id,
                                type=MetadataResourceTypes.ARTIFACT_VERSION,
                            )
                        ],
                        values=values,
                        types=types,
                    )
                )

            session.commit()
            session.refresh(artifact_version_schema)

            return artifact_version_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def batch_create_artifact_versions(
        self, artifact_versions: List[ArtifactVersionRequest]
    ) -> List[ArtifactVersionResponse]:
        """Creates a batch of artifact versions.

        Args:
            artifact_versions: The artifact versions to create.

        Returns:
            The created artifact versions.
        """
        return [
            self.create_artifact_version(artifact_version)
            for artifact_version in artifact_versions
        ]

    def get_artifact_version(
        self, artifact_version_id: UUID, hydrate: bool = True
    ) -> ArtifactVersionResponse:
        """Gets an artifact version.

        Args:
            artifact_version_id: The ID of the artifact version to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact version.
        """
        with Session(self.engine) as session:
            artifact_version = self._get_schema_by_id(
                resource_id=artifact_version_id,
                schema_class=ArtifactVersionSchema,
                session=session,
            )
            return artifact_version.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_artifact_versions(
        self,
        artifact_version_filter_model: ArtifactVersionFilter,
        hydrate: bool = False,
    ) -> Page[ArtifactVersionResponse]:
        """List all artifact versions matching the given filter criteria.

        Args:
            artifact_version_filter_model: All filter parameters including
                pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all artifact versions matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=artifact_version_filter_model,
                session=session,
            )
            query = select(ArtifactVersionSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ArtifactVersionSchema,
                filter_model=artifact_version_filter_model,
                hydrate=hydrate,
            )

    def update_artifact_version(
        self,
        artifact_version_id: UUID,
        artifact_version_update: ArtifactVersionUpdate,
    ) -> ArtifactVersionResponse:
        """Updates an artifact version.

        Args:
            artifact_version_id: The ID of the artifact version to update.
            artifact_version_update: The update to be applied to the artifact
                version.

        Returns:
            The updated artifact version.
        """
        with Session(self.engine) as session:
            existing_artifact_version = self._get_schema_by_id(
                resource_id=artifact_version_id,
                schema_class=ArtifactVersionSchema,
                session=session,
            )

            # Update the schema itself.
            existing_artifact_version.update(
                artifact_version_update=artifact_version_update
            )
            session.add(existing_artifact_version)
            session.commit()
            session.refresh(existing_artifact_version)

            # Handle tag updates.
            self._attach_tags_to_resources(
                tags=artifact_version_update.add_tags,
                resources=existing_artifact_version,
                session=session,
            )
            self._detach_tags_from_resources(
                tags=artifact_version_update.remove_tags,
                resources=existing_artifact_version,
                session=session,
            )

            session.refresh(existing_artifact_version)
            return existing_artifact_version.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_artifact_version(self, artifact_version_id: UUID) -> None:
        """Deletes an artifact version.

        Args:
            artifact_version_id: The ID of the artifact version to delete.
        """
        with Session(self.engine) as session:
            artifact_version = self._get_schema_by_id(
                resource_id=artifact_version_id,
                schema_class=ArtifactVersionSchema,
                session=session,
            )
            session.delete(artifact_version)
            session.commit()

    def prune_artifact_versions(
        self,
        project_name_or_id: Union[str, UUID],
        only_versions: bool = True,
    ) -> None:
        """Prunes unused artifact versions and their artifacts.

        Args:
            project_name_or_id: The project name or ID to prune artifact
                versions for.
            only_versions: Only delete artifact versions, keeping artifacts
        """
        with Session(self.engine) as session:
            project_id = self._get_schema_by_name_or_id(
                object_name_or_id=project_name_or_id,
                schema_class=ProjectSchema,
                session=session,
            ).id

            unused_artifact_versions = [
                a[0]
                for a in session.execute(
                    select(ArtifactVersionSchema.id).where(
                        and_(
                            col(ArtifactVersionSchema.id).notin_(
                                select(StepRunOutputArtifactSchema.artifact_id)
                            ),
                            col(ArtifactVersionSchema.id).notin_(
                                select(StepRunInputArtifactSchema.artifact_id)
                            ),
                            col(ArtifactVersionSchema.project_id)
                            == project_id,
                        )
                    )
                ).fetchall()
            ]
            session.execute(
                delete(ArtifactVersionSchema).where(
                    col(ArtifactVersionSchema.id).in_(
                        unused_artifact_versions
                    ),
                )
            )
            if not only_versions:
                unused_artifacts = [
                    a[0]
                    for a in session.execute(
                        select(ArtifactSchema.id).where(
                            col(ArtifactSchema.id).notin_(
                                select(ArtifactVersionSchema.artifact_id)
                            )
                        )
                    ).fetchall()
                ]
                session.execute(
                    delete(ArtifactSchema).where(
                        col(ArtifactSchema.id).in_(unused_artifacts)
                    )
                )
            session.commit()

    # ------------------------ Artifact Visualizations ------------------------

    def get_artifact_visualization(
        self, artifact_visualization_id: UUID, hydrate: bool = True
    ) -> ArtifactVisualizationResponse:
        """Gets an artifact visualization.

        Args:
            artifact_visualization_id: The ID of the artifact visualization to
                get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The artifact visualization.
        """
        with Session(self.engine) as session:
            artifact_visualization = self._get_schema_by_id(
                resource_id=artifact_visualization_id,
                schema_class=ArtifactVisualizationSchema,
                session=session,
            )
            return artifact_visualization.to_model(
                include_metadata=hydrate, include_resources=True
            )

    # ------------------------ Code References ------------------------

    def get_code_reference(
        self, code_reference_id: UUID, hydrate: bool = True
    ) -> CodeReferenceResponse:
        """Gets a code reference.

        Args:
            code_reference_id: The ID of the code reference to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The code reference.
        """
        with Session(self.engine) as session:
            code_reference = self._get_schema_by_id(
                resource_id=code_reference_id,
                schema_class=CodeReferenceSchema,
                session=session,
            )
            return code_reference.to_model(
                include_metadata=hydrate, include_resources=True
            )

    # --------------------------- Code Repositories ---------------------------

    @track_decorator(AnalyticsEvent.REGISTERED_CODE_REPOSITORY)
    def create_code_repository(
        self, code_repository: CodeRepositoryRequest
    ) -> CodeRepositoryResponse:
        """Creates a new code repository.

        Args:
            code_repository: Code repository to be created.

        Returns:
            The newly created code repository.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=code_repository, session=session
            )

            self._verify_name_uniqueness(
                resource=code_repository,
                schema=CodeRepositorySchema,
                session=session,
            )

            new_repo = CodeRepositorySchema.from_request(code_repository)
            session.add(new_repo)
            session.commit()
            session.refresh(new_repo)

            return new_repo.to_model(
                include_metadata=True, include_resources=True
            )

    def get_code_repository(
        self, code_repository_id: UUID, hydrate: bool = True
    ) -> CodeRepositoryResponse:
        """Gets a specific code repository.

        Args:
            code_repository_id: The ID of the code repository to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested code repository, if it was found.
        """
        with Session(self.engine) as session:
            repo = self._get_schema_by_id(
                resource_id=code_repository_id,
                schema_class=CodeRepositorySchema,
                session=session,
            )

            return repo.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_code_repositories(
        self,
        filter_model: CodeRepositoryFilter,
        hydrate: bool = False,
    ) -> Page[CodeRepositoryResponse]:
        """List all code repositories.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all code repositories.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=filter_model,
                session=session,
            )
            query = select(CodeRepositorySchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=CodeRepositorySchema,
                filter_model=filter_model,
                hydrate=hydrate,
            )

    def update_code_repository(
        self, code_repository_id: UUID, update: CodeRepositoryUpdate
    ) -> CodeRepositoryResponse:
        """Updates an existing code repository.

        Args:
            code_repository_id: The ID of the code repository to update.
            update: The update to be applied to the code repository.

        Returns:
            The updated code repository.
        """
        with Session(self.engine) as session:
            existing_repo = self._get_schema_by_id(
                resource_id=code_repository_id,
                schema_class=CodeRepositorySchema,
                session=session,
            )

            self._verify_name_uniqueness(
                resource=update,
                schema=existing_repo,
                session=session,
            )

            existing_repo.update(update)

            session.add(existing_repo)
            session.commit()

            return existing_repo.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_code_repository(self, code_repository_id: UUID) -> None:
        """Deletes a code repository.

        Args:
            code_repository_id: The ID of the code repository to delete.
        """
        with Session(self.engine) as session:
            existing_repo = self._get_schema_by_id(
                resource_id=code_repository_id,
                schema_class=CodeRepositorySchema,
                session=session,
            )

            session.delete(existing_repo)
            session.commit()

    # ----------------------------- Components -----------------------------

    @track_decorator(AnalyticsEvent.REGISTERED_STACK_COMPONENT)
    def create_stack_component(
        self,
        component: ComponentRequest,
    ) -> ComponentResponse:
        """Create a stack component.

        Args:
            component: The stack component to create.

        Returns:
            The created stack component.
        """
        validate_name(component)
        with Session(self.engine) as session:
            if isinstance(component, DefaultComponentRequest):
                # Set the user to None for default components
                component.user = None
            else:
                self._set_request_user_id(
                    request_model=component, session=session
                )

            self._fail_if_component_with_name_type_exists(
                name=component.name,
                component_type=component.type,
                session=session,
            )

            is_default_stack_component = (
                component.name == DEFAULT_STACK_AND_COMPONENT_NAME
                and component.type
                in {
                    StackComponentType.ORCHESTRATOR,
                    StackComponentType.ARTIFACT_STORE,
                }
            )
            # We have to skip the validation of the default components
            # as it creates a loop of initialization.
            if not is_default_stack_component:
                from zenml.stack.utils import validate_stack_component_config

                validate_stack_component_config(
                    configuration_dict=component.configuration,
                    flavor=component.flavor,
                    component_type=component.type,
                    zen_store=self,
                    validate_custom_flavors=False,
                )

            service_connector = self._get_reference_schema_by_id(
                resource=component,
                reference_schema=ServiceConnectorSchema,
                reference_id=component.connector,
                session=session,
            )

            # warn about skypilot regions, if needed
            # TODO: this sooo does not belong here!
            if component.flavor in {"vm_gcp", "vm_azure"}:
                stack_deployment_class = get_stack_deployment_class(
                    StackDeploymentProvider.GCP
                    if component.flavor == "vm_gcp"
                    else StackDeploymentProvider.AZURE
                )
                skypilot_regions = (
                    stack_deployment_class.skypilot_default_regions().values()
                )
                if (
                    component.configuration.get("region", None)
                    and component.configuration["region"]
                    not in skypilot_regions
                ):
                    logger.warning(
                        f"Region `{component.configuration['region']}` is "
                        "not enabled in Skypilot by default. Supported regions "
                        f"by default are: {skypilot_regions}. Check the "
                        "Skypilot documentation to learn how to enable "
                        "regions rather than default ones. (If you have "
                        "already extended your configuration - "
                        "simply ignore this warning)"
                    )

            # Create the component
            new_component = StackComponentSchema.from_request(
                request=component, service_connector=service_connector
            )

            session.add(new_component)
            session.commit()

            session.refresh(new_component)

            return new_component.to_model(
                include_metadata=True, include_resources=True
            )

    def get_stack_component(
        self, component_id: UUID, hydrate: bool = True
    ) -> ComponentResponse:
        """Get a stack component by ID.

        Args:
            component_id: The ID of the stack component to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The stack component.
        """
        with Session(self.engine) as session:
            stack_component = self._get_schema_by_id(
                resource_id=component_id,
                schema_class=StackComponentSchema,
                session=session,
            )

            return stack_component.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_stack_components(
        self,
        component_filter_model: ComponentFilter,
        hydrate: bool = False,
    ) -> Page[ComponentResponse]:
        """List all stack components matching the given filter criteria.

        Args:
            component_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all stack components matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(StackComponentSchema)
            paged_components: Page[ComponentResponse] = (
                self.filter_and_paginate(
                    session=session,
                    query=query,
                    table=StackComponentSchema,
                    filter_model=component_filter_model,
                    hydrate=hydrate,
                )
            )
            return paged_components

    def update_stack_component(
        self, component_id: UUID, component_update: ComponentUpdate
    ) -> ComponentResponse:
        """Update an existing stack component.

        Args:
            component_id: The ID of the stack component to update.
            component_update: The update to be applied to the stack component.

        Returns:
            The updated stack component.

        Raises:
            IllegalOperationError: if the stack component is a default stack
                component.
        """
        with Session(self.engine) as session:
            existing_component = self._get_schema_by_id(
                resource_id=component_id,
                schema_class=StackComponentSchema,
                session=session,
            )

            if component_update.configuration is not None:
                from zenml.stack.utils import validate_stack_component_config

                validate_stack_component_config(
                    configuration_dict=component_update.configuration,
                    flavor=existing_component.flavor,
                    component_type=StackComponentType(existing_component.type),
                    zen_store=self,
                    validate_custom_flavors=False,
                )

            if (
                existing_component.name == DEFAULT_STACK_AND_COMPONENT_NAME
                and existing_component.type
                in [
                    StackComponentType.ORCHESTRATOR,
                    StackComponentType.ARTIFACT_STORE,
                ]
            ):
                raise IllegalOperationError(
                    f"The default {existing_component.type} cannot be modified."
                )

            # In case of a renaming update, make sure no component of the same
            # type already exists with that name
            if component_update.name:
                if existing_component.name != component_update.name:
                    self._fail_if_component_with_name_type_exists(
                        name=component_update.name,
                        component_type=StackComponentType(
                            existing_component.type
                        ),
                        session=session,
                    )

            existing_component.update(component_update=component_update)

            if component_update.connector:
                service_connector = self._get_reference_schema_by_id(
                    resource=existing_component,
                    reference_schema=ServiceConnectorSchema,
                    reference_id=component_update.connector,
                    session=session,
                )

                existing_component.connector = service_connector
                existing_component.connector_resource_id = (
                    component_update.connector_resource_id
                )
            else:
                existing_component.connector = None
                existing_component.connector_resource_id = None

            session.add(existing_component)
            session.commit()

            return existing_component.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_stack_component(self, component_id: UUID) -> None:
        """Delete a stack component.

        Args:
            component_id: The id of the stack component to delete.

        Raises:
            IllegalOperationError: if the stack component is part of one or
                more stacks, or if it's a default stack component.
        """
        with Session(self.engine) as session:
            stack_component = self._get_schema_by_id(
                resource_id=component_id,
                schema_class=StackComponentSchema,
                session=session,
            )

            if (
                stack_component.name == DEFAULT_STACK_AND_COMPONENT_NAME
                and stack_component.type
                in [
                    StackComponentType.ORCHESTRATOR,
                    StackComponentType.ARTIFACT_STORE,
                ]
            ):
                raise IllegalOperationError(
                    f"The default {stack_component.type} cannot be deleted."
                )

            if len(stack_component.stacks) > 0:
                raise IllegalOperationError(
                    f"Stack Component `{stack_component.name}` of type "
                    f"`{stack_component.type} cannot be "
                    f"deleted as it is part of "
                    f"{len(stack_component.stacks)} stacks. "
                    f"Before deleting this stack "
                    f"component, make sure to remove it "
                    f"from all stacks."
                )

            session.delete(stack_component)
            session.commit()

    def count_stack_components(
        self, filter_model: Optional[ComponentFilter] = None
    ) -> int:
        """Count all components.

        Args:
            filter_model: The filter model to use for counting components.

        Returns:
            The number of components.
        """
        return self._count_entity(
            schema=StackComponentSchema, filter_model=filter_model
        )

    @staticmethod
    def _fail_if_component_with_name_type_exists(
        name: str,
        component_type: StackComponentType,
        session: Session,
    ) -> None:
        """Raise an exception if a component with same name/type exists.

        Args:
            name: The name of the component
            component_type: The type of the component
            session: The Session

        Raises:
            EntityExistsError: If a component with the given name and
                type already exists.
        """
        # Check if component with the same domain key (name, type) already
        # exists
        existing_domain_component = session.exec(
            select(StackComponentSchema)
            .where(StackComponentSchema.name == name)
            .where(StackComponentSchema.type == component_type)
        ).first()
        if existing_domain_component is not None:
            raise EntityExistsError(
                f"Unable to register '{component_type}' component "
                f"with name '{name}': Found an existing "
                f"component with the same name and type."
            )

    # -------------------------- Devices -------------------------

    def create_authorized_device(
        self, device: OAuthDeviceInternalRequest
    ) -> OAuthDeviceInternalResponse:
        """Creates a new OAuth 2.0 authorized device.

        Args:
            device: The device to be created.

        Returns:
            The newly created device.

        Raises:
            EntityExistsError: If a device for the same client ID already
                exists.
        """
        with Session(self.engine) as session:
            existing_device = session.exec(
                select(OAuthDeviceSchema).where(
                    # We search for a device with the same client ID
                    # because the client ID is the one that is used to
                    # identify the device
                    OAuthDeviceSchema.client_id == device.client_id
                )
            ).first()
            if existing_device is not None:
                raise EntityExistsError(
                    f"Unable to create device with client ID "
                    f"'{device.client_id}': A device with this client ID "
                    "already exists."
                )

            (
                new_device,
                user_code,
                device_code,
            ) = OAuthDeviceSchema.from_request(device)
            session.add(new_device)
            session.commit()
            session.refresh(new_device)

            device_model = new_device.to_internal_model(
                include_metadata=True, include_resources=True
            )
            # Replace the hashed user code with the original user code
            device_model.user_code = user_code
            # Replace the hashed device code with the original device code
            device_model.device_code = device_code

            return device_model

    def get_authorized_device(
        self, device_id: UUID, hydrate: bool = True
    ) -> OAuthDeviceResponse:
        """Gets a specific OAuth 2.0 authorized device.

        Args:
            device_id: The ID of the device to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested device, if it was found.
        """
        with Session(self.engine) as session:
            device = self._get_schema_by_id(
                resource_id=device_id,
                schema_class=OAuthDeviceSchema,
                session=session,
                resource_type="authorized device",
            )

            return device.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def get_internal_authorized_device(
        self,
        device_id: Optional[UUID] = None,
        client_id: Optional[UUID] = None,
        hydrate: bool = True,
    ) -> OAuthDeviceInternalResponse:
        """Gets a specific OAuth 2.0 authorized device for internal use.

        Args:
            client_id: The client ID of the device to get.
            device_id: The ID of the device to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested device, if it was found.

        Raises:
            KeyError: If no device with the given client ID exists.
            ValueError: If neither device ID nor client ID are provided.
        """
        with Session(self.engine) as session:
            if device_id is not None:
                device = session.exec(
                    select(OAuthDeviceSchema).where(
                        OAuthDeviceSchema.id == device_id
                    )
                ).first()
            elif client_id is not None:
                device = session.exec(
                    select(OAuthDeviceSchema).where(
                        OAuthDeviceSchema.client_id == client_id
                    )
                ).first()
            else:
                raise ValueError(
                    "Either device ID or client ID must be provided."
                )
            if device is None:
                raise KeyError(
                    f"Unable to get device with client ID {client_id}: No "
                    "device with this client ID found."
                )

            return device.to_internal_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_authorized_devices(
        self,
        filter_model: OAuthDeviceFilter,
        hydrate: bool = False,
    ) -> Page[OAuthDeviceResponse]:
        """List all OAuth 2.0 authorized devices for a user.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all matching OAuth 2.0 authorized devices.
        """
        with Session(self.engine) as session:
            query = select(OAuthDeviceSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=OAuthDeviceSchema,
                filter_model=filter_model,
                hydrate=hydrate,
            )

    def update_authorized_device(
        self, device_id: UUID, update: OAuthDeviceUpdate
    ) -> OAuthDeviceResponse:
        """Updates an existing OAuth 2.0 authorized device for internal use.

        Args:
            device_id: The ID of the device to update.
            update: The update to be applied to the device.

        Returns:
            The updated OAuth 2.0 authorized device.
        """
        with Session(self.engine) as session:
            existing_device = self._get_schema_by_id(
                resource_id=device_id,
                schema_class=OAuthDeviceSchema,
                session=session,
                resource_type="authorized device",
            )

            existing_device.update(update)

            session.add(existing_device)
            session.commit()

            return existing_device.to_model(
                include_metadata=True, include_resources=True
            )

    def update_internal_authorized_device(
        self, device_id: UUID, update: OAuthDeviceInternalUpdate
    ) -> OAuthDeviceInternalResponse:
        """Updates an existing OAuth 2.0 authorized device.

        Args:
            device_id: The ID of the device to update.
            update: The update to be applied to the device.

        Returns:
            The updated OAuth 2.0 authorized device.
        """
        with Session(self.engine) as session:
            existing_device = self._get_schema_by_id(
                resource_id=device_id,
                schema_class=OAuthDeviceSchema,
                session=session,
                resource_type="authorized device",
            )

            (
                _,
                user_code,
                device_code,
            ) = existing_device.internal_update(update)

            session.add(existing_device)
            session.commit()

            device_model = existing_device.to_internal_model(
                include_metadata=True, include_resources=True
            )
            if user_code:
                # Replace the hashed user code with the original user code
                device_model.user_code = user_code

            if device_code:
                # Replace the hashed device code with the original device code
                device_model.device_code = device_code

            return device_model

    def delete_authorized_device(self, device_id: UUID) -> None:
        """Deletes an OAuth 2.0 authorized device.

        Args:
            device_id: The ID of the device to delete.
        """
        with Session(self.engine) as session:
            existing_device = self._get_schema_by_id(
                resource_id=device_id,
                schema_class=OAuthDeviceSchema,
                session=session,
                resource_type="authorized device",
            )

            session.delete(existing_device)
            session.commit()

    def delete_expired_authorized_devices(self) -> None:
        """Deletes all expired OAuth 2.0 authorized devices."""
        with Session(self.engine) as session:
            expired_devices = session.exec(
                select(OAuthDeviceSchema).where(OAuthDeviceSchema.user is None)
            ).all()
            for device in expired_devices:
                # Delete devices that have expired
                if (
                    device.expires is not None
                    and device.expires < utc_now()
                    and device.user_id is None
                ):
                    session.delete(device)
            session.commit()

    # ----------------------------- Flavors -----------------------------

    @track_decorator(AnalyticsEvent.CREATED_FLAVOR)
    def create_flavor(self, flavor: FlavorRequest) -> FlavorResponse:
        """Creates a new stack component flavor.

        Args:
            flavor: The stack component flavor to create.

        Returns:
            The newly created flavor.

        Raises:
            EntityExistsError: If a flavor with the same name and type
                is already owned by this user.
            ValueError: In case the config_schema string exceeds the max length.
        """
        with Session(self.engine) as session:
            if flavor.is_custom is False:
                # Set the user to None for built-in flavors
                flavor.user = None
            else:
                self._set_request_user_id(
                    request_model=flavor, session=session
                )
            # Check if flavor with the same domain key (name, type) already
            # exists
            existing_flavor = session.exec(
                select(FlavorSchema)
                .where(FlavorSchema.name == flavor.name)
                .where(FlavorSchema.type == flavor.type)
            ).first()

            if existing_flavor is not None:
                raise EntityExistsError(
                    f"Unable to register '{flavor.type.value}' flavor "
                    f"with name '{flavor.name}' and type '{flavor.type}': "
                    "Found an existing flavor with the same name and type."
                )

            config_schema = json.dumps(flavor.config_schema)

            if len(config_schema) > TEXT_FIELD_MAX_LENGTH:
                raise ValueError(
                    "Json representation of configuration schema"
                    "exceeds max length."
                )

            else:
                new_flavor = FlavorSchema(
                    name=flavor.name,
                    type=flavor.type,
                    source=flavor.source,
                    config_schema=config_schema,
                    integration=flavor.integration,
                    connector_type=flavor.connector_type,
                    connector_resource_type=flavor.connector_resource_type,
                    connector_resource_id_attr=flavor.connector_resource_id_attr,
                    user_id=flavor.user,
                    logo_url=flavor.logo_url,
                    docs_url=flavor.docs_url,
                    sdk_docs_url=flavor.sdk_docs_url,
                    is_custom=flavor.is_custom,
                )
                session.add(new_flavor)
                session.commit()

                return new_flavor.to_model(
                    include_metadata=True, include_resources=True
                )

    def get_flavor(
        self, flavor_id: UUID, hydrate: bool = True
    ) -> FlavorResponse:
        """Get a flavor by ID.

        Args:
            flavor_id: The ID of the flavor to fetch.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The stack component flavor.
        """
        with Session(self.engine) as session:
            flavor_in_db = self._get_schema_by_id(
                resource_id=flavor_id,
                schema_class=FlavorSchema,
                session=session,
            )
            return flavor_in_db.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_flavors(
        self,
        flavor_filter_model: FlavorFilter,
        hydrate: bool = False,
    ) -> Page[FlavorResponse]:
        """List all stack component flavors matching the given filter criteria.

        Args:
            flavor_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            List of all the stack component flavors matching the given criteria.
        """
        with Session(self.engine) as session:
            query = select(FlavorSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=FlavorSchema,
                filter_model=flavor_filter_model,
                hydrate=hydrate,
            )

    def update_flavor(
        self, flavor_id: UUID, flavor_update: FlavorUpdate
    ) -> FlavorResponse:
        """Updates an existing user.

        Args:
            flavor_id: The id of the flavor to update.
            flavor_update: The update to be applied to the flavor.

        Returns:
            The updated flavor.

        Raises:
            EntityExistsError: If a flavor with the same name and type already
                exists.
        """
        with Session(self.engine) as session:
            existing_flavor = self._get_schema_by_id(
                resource_id=flavor_id,
                schema_class=FlavorSchema,
                session=session,
            )

            # Check if flavor with the new domain key (name, type) already
            # exists
            if (
                flavor_update.name
                and flavor_update.name != existing_flavor.name
                or flavor_update.type
                and flavor_update.type != existing_flavor.type
            ):
                other_flavor = session.exec(
                    select(FlavorSchema)
                    .where(
                        FlavorSchema.name
                        == (flavor_update.name or existing_flavor.name)
                    )
                    .where(
                        FlavorSchema.type
                        == (flavor_update.type or existing_flavor.type)
                    )
                ).first()

                if other_flavor is not None:
                    raise EntityExistsError(
                        f"Unable to update '{existing_flavor.type}' flavor "
                        f"with name '{existing_flavor.name}': Found an existing "
                        f"flavor with the same name and type."
                    )

            existing_flavor.update(flavor_update=flavor_update)
            session.add(existing_flavor)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_flavor)
            return existing_flavor.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_flavor(self, flavor_id: UUID) -> None:
        """Delete a flavor.

        Args:
            flavor_id: The id of the flavor to delete.

        Raises:
            IllegalOperationError: if the flavor is used by a stack component.
        """
        with Session(self.engine) as session:
            flavor_in_db = self._get_schema_by_id(
                resource_id=flavor_id,
                schema_class=FlavorSchema,
                session=session,
            )
            components_of_flavor = session.exec(
                select(StackComponentSchema).where(
                    StackComponentSchema.flavor == flavor_in_db.name
                )
            ).all()
            if len(components_of_flavor) > 0:
                raise IllegalOperationError(
                    f"Stack Component `{flavor_in_db.name}` of type "
                    f"`{flavor_in_db.type} cannot be "
                    f"deleted as it is used by "
                    f"{len(components_of_flavor)} "
                    f"components. Before deleting this "
                    f"flavor, make sure to delete all "
                    f"associated components."
                )
            else:
                session.delete(flavor_in_db)
                session.commit()

    # ------------------------ Logs ------------------------

    def get_logs(self, logs_id: UUID, hydrate: bool = True) -> LogsResponse:
        """Gets logs with the given ID.

        Args:
            logs_id: The ID of the logs to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The logs.
        """
        with Session(self.engine) as session:
            logs = self._get_schema_by_id(
                resource_id=logs_id,
                schema_class=LogsSchema,
                session=session,
            )
            return logs.to_model(
                include_metadata=hydrate, include_resources=True
            )

    # ----------------------------- Pipelines -----------------------------

    @track_decorator(AnalyticsEvent.CREATE_PIPELINE)
    def create_pipeline(
        self,
        pipeline: PipelineRequest,
    ) -> PipelineResponse:
        """Creates a new pipeline.

        Args:
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            EntityExistsError: If an identical pipeline already exists.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=pipeline, session=session)

            new_pipeline = PipelineSchema.from_request(pipeline)

            session.add(new_pipeline)
            try:
                session.commit()
            except IntegrityError:
                # We have to rollback the failed session first in order
                # to continue using it
                session.rollback()
                raise EntityExistsError(
                    f"Unable to create pipeline in project "
                    f"'{pipeline.project}': A pipeline with the name "
                    f"{pipeline.name} already exists."
                )
            session.refresh(new_pipeline)

            self._attach_tags_to_resources(
                tags=pipeline.tags,
                resources=new_pipeline,
                session=session,
            )

            session.refresh(new_pipeline)

            return new_pipeline.to_model(
                include_metadata=True, include_resources=True
            )

    def get_pipeline(
        self, pipeline_id: UUID, hydrate: bool = True
    ) -> PipelineResponse:
        """Get a pipeline with a given ID.

        Args:
            pipeline_id: ID of the pipeline.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The pipeline.
        """
        with Session(self.engine) as session:
            # Check if pipeline with the given ID exists
            pipeline = self._get_schema_by_id(
                resource_id=pipeline_id,
                schema_class=PipelineSchema,
                session=session,
            )
            return pipeline.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_pipelines(
        self,
        pipeline_filter_model: PipelineFilter,
        hydrate: bool = False,
    ) -> Page[PipelineResponse]:
        """List all pipelines matching the given filter criteria.

        Args:
            pipeline_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all pipelines matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=pipeline_filter_model,
                session=session,
            )
            query = select(PipelineSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=PipelineSchema,
                filter_model=pipeline_filter_model,
                hydrate=hydrate,
            )

    def count_pipelines(self, filter_model: PipelineFilter) -> int:
        """Count all pipelines.

        Args:
            filter_model: The filter model to use for counting pipelines.

        Returns:
            The number of pipelines.
        """
        return self._count_entity(
            schema=PipelineSchema, filter_model=filter_model
        )

    def update_pipeline(
        self,
        pipeline_id: UUID,
        pipeline_update: PipelineUpdate,
    ) -> PipelineResponse:
        """Updates a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to be updated.
            pipeline_update: The update to be applied.

        Returns:
            The updated pipeline.
        """
        with Session(self.engine) as session:
            # Check if pipeline with the given ID exists
            existing_pipeline = self._get_schema_by_id(
                resource_id=pipeline_id,
                schema_class=PipelineSchema,
                session=session,
            )

            existing_pipeline.update(pipeline_update)
            session.add(existing_pipeline)
            session.commit()
            session.refresh(existing_pipeline)

            self._attach_tags_to_resources(
                tags=pipeline_update.add_tags,
                resources=existing_pipeline,
                session=session,
            )
            self._detach_tags_from_resources(
                tags=pipeline_update.remove_tags,
                resources=existing_pipeline,
                session=session,
            )
            session.refresh(existing_pipeline)

            return existing_pipeline.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_pipeline(self, pipeline_id: UUID) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.
        """
        with Session(self.engine) as session:
            # Check if pipeline with the given ID exists
            pipeline = self._get_schema_by_id(
                resource_id=pipeline_id,
                schema_class=PipelineSchema,
                session=session,
            )

            session.delete(pipeline)
            session.commit()

    # --------------------------- Pipeline Builds ---------------------------

    def create_build(
        self,
        build: PipelineBuildRequest,
    ) -> PipelineBuildResponse:
        """Creates a new build.

        Args:
            build: The build to create.

        Returns:
            The newly created build.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=build, session=session)
            self._get_reference_schema_by_id(
                resource=build,
                reference_schema=StackSchema,
                reference_id=build.stack,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=build,
                reference_schema=PipelineSchema,
                reference_id=build.pipeline,
                session=session,
            )

            new_build = PipelineBuildSchema.from_request(build)
            session.add(new_build)
            session.commit()
            session.refresh(new_build)

            return new_build.to_model(
                include_metadata=True, include_resources=True
            )

    def get_build(
        self, build_id: UUID, hydrate: bool = True
    ) -> PipelineBuildResponse:
        """Get a build with a given ID.

        Args:
            build_id: ID of the build.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The build.
        """
        with Session(self.engine) as session:
            # Check if build with the given ID exists
            build = self._get_schema_by_id(
                resource_id=build_id,
                schema_class=PipelineBuildSchema,
                session=session,
            )
            return build.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_builds(
        self,
        build_filter_model: PipelineBuildFilter,
        hydrate: bool = False,
    ) -> Page[PipelineBuildResponse]:
        """List all builds matching the given filter criteria.

        Args:
            build_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all builds matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=build_filter_model,
                session=session,
            )
            query = select(PipelineBuildSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=PipelineBuildSchema,
                filter_model=build_filter_model,
                hydrate=hydrate,
            )

    def delete_build(self, build_id: UUID) -> None:
        """Deletes a build.

        Args:
            build_id: The ID of the build to delete.
        """
        with Session(self.engine) as session:
            # Check if build with the given ID exists
            build = self._get_schema_by_id(
                resource_id=build_id,
                schema_class=PipelineBuildSchema,
                session=session,
            )

            session.delete(build)
            session.commit()

    # -------------------------- Pipeline Deployments --------------------------

    @staticmethod
    def _create_or_reuse_code_reference(
        session: Session,
        project_id: UUID,
        code_reference: Optional["CodeReferenceRequest"],
    ) -> Optional[UUID]:
        """Creates or reuses a code reference.

        Args:
            session: The database session to use.
            project_id: ID of the project in which the code reference
                should be.
            code_reference: Request of the reference to create.

        Returns:
            The code reference ID.
        """
        if not code_reference:
            return None

        existing_reference = session.exec(
            select(CodeReferenceSchema)
            .where(CodeReferenceSchema.project_id == project_id)
            .where(
                CodeReferenceSchema.code_repository_id
                == code_reference.code_repository
            )
            .where(CodeReferenceSchema.commit == code_reference.commit)
            .where(
                CodeReferenceSchema.subdirectory == code_reference.subdirectory
            )
        ).first()
        if existing_reference is not None:
            return existing_reference.id

        new_reference = CodeReferenceSchema.from_request(
            code_reference, project_id=project_id
        )

        session.add(new_reference)
        return new_reference.id

    def create_deployment(
        self,
        deployment: PipelineDeploymentRequest,
    ) -> PipelineDeploymentResponse:
        """Creates a new deployment.

        Args:
            deployment: The deployment to create.

        Returns:
            The newly created deployment.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=deployment, session=session
            )
            self._get_reference_schema_by_id(
                resource=deployment,
                reference_schema=StackSchema,
                reference_id=deployment.stack,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=deployment,
                reference_schema=PipelineSchema,
                reference_id=deployment.pipeline,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=deployment,
                reference_schema=PipelineBuildSchema,
                reference_id=deployment.build,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=deployment,
                reference_schema=ScheduleSchema,
                reference_id=deployment.schedule,
                session=session,
            )

            if deployment.code_reference:
                self._get_reference_schema_by_id(
                    resource=deployment,
                    reference_schema=CodeRepositorySchema,
                    reference_id=deployment.code_reference.code_repository,
                    session=session,
                )

            self._get_reference_schema_by_id(
                resource=deployment,
                reference_schema=RunTemplateSchema,
                reference_id=deployment.template,
                session=session,
            )

            code_reference_id = self._create_or_reuse_code_reference(
                session=session,
                project_id=deployment.project,
                code_reference=deployment.code_reference,
            )

            new_deployment = PipelineDeploymentSchema.from_request(
                deployment, code_reference_id=code_reference_id
            )
            session.add(new_deployment)
            session.commit()
            session.refresh(new_deployment)

            return new_deployment.to_model(
                include_metadata=True, include_resources=True
            )

    def get_deployment(
        self, deployment_id: UUID, hydrate: bool = True
    ) -> PipelineDeploymentResponse:
        """Get a deployment with a given ID.

        Args:
            deployment_id: ID of the deployment.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The deployment.
        """
        with Session(self.engine) as session:
            # Check if deployment with the given ID exists
            deployment = self._get_schema_by_id(
                resource_id=deployment_id,
                schema_class=PipelineDeploymentSchema,
                session=session,
            )

            return deployment.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_deployments(
        self,
        deployment_filter_model: PipelineDeploymentFilter,
        hydrate: bool = False,
    ) -> Page[PipelineDeploymentResponse]:
        """List all deployments matching the given filter criteria.

        Args:
            deployment_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all deployments matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=deployment_filter_model,
                session=session,
            )
            query = select(PipelineDeploymentSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=PipelineDeploymentSchema,
                filter_model=deployment_filter_model,
                hydrate=hydrate,
            )

    def delete_deployment(self, deployment_id: UUID) -> None:
        """Deletes a deployment.

        Args:
            deployment_id: The ID of the deployment to delete.
        """
        with Session(self.engine) as session:
            # Check if build with the given ID exists
            deployment = self._get_schema_by_id(
                resource_id=deployment_id,
                schema_class=PipelineDeploymentSchema,
                session=session,
            )

            session.delete(deployment)
            session.commit()

    # -------------------- Run templates --------------------

    @track_decorator(AnalyticsEvent.CREATED_RUN_TEMPLATE)
    def create_run_template(
        self,
        template: RunTemplateRequest,
    ) -> RunTemplateResponse:
        """Create a new run template.

        Args:
            template: The template to create.

        Returns:
            The newly created template.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=template, session=session)

            self._verify_name_uniqueness(
                resource=template,
                schema=RunTemplateSchema,
                session=session,
            )

            deployment = self._get_reference_schema_by_id(
                resource=template,
                reference_schema=PipelineDeploymentSchema,
                reference_id=template.source_deployment_id,
                session=session,
            )

            template_utils.validate_deployment_is_templatable(deployment)

            template_schema = RunTemplateSchema.from_request(request=template)

            session.add(template_schema)
            session.commit()
            session.refresh(template_schema)

            self._attach_tags_to_resources(
                tags=template.tags,
                resources=template_schema,
                session=session,
            )

            session.refresh(template_schema)

            return template_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def get_run_template(
        self, template_id: UUID, hydrate: bool = True
    ) -> RunTemplateResponse:
        """Get a run template with a given ID.

        Args:
            template_id: ID of the template.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The template.
        """
        with Session(self.engine) as session:
            template = self._get_schema_by_id(
                resource_id=template_id,
                schema_class=RunTemplateSchema,
                session=session,
            )
            return template.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_run_templates(
        self,
        template_filter_model: RunTemplateFilter,
        hydrate: bool = False,
    ) -> Page[RunTemplateResponse]:
        """List all run templates matching the given filter criteria.

        Args:
            template_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all templates matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=template_filter_model,
                session=session,
            )
            query = select(RunTemplateSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=RunTemplateSchema,
                filter_model=template_filter_model,
                hydrate=hydrate,
            )

    def update_run_template(
        self,
        template_id: UUID,
        template_update: RunTemplateUpdate,
    ) -> RunTemplateResponse:
        """Updates a run template.

        Args:
            template_id: The ID of the template to update.
            template_update: The update to apply.

        Returns:
            The updated template.
        """
        with Session(self.engine) as session:
            template = self._get_schema_by_id(
                resource_id=template_id,
                schema_class=RunTemplateSchema,
                session=session,
            )

            template.update(template_update)
            session.add(template)
            session.commit()
            session.refresh(template)

            self._attach_tags_to_resources(
                tags=template_update.add_tags,
                resources=template,
                session=session,
            )
            self._detach_tags_from_resources(
                tags=template_update.remove_tags,
                resources=template,
                session=session,
            )

            session.refresh(template)

            return template.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_run_template(self, template_id: UUID) -> None:
        """Delete a run template.

        Args:
            template_id: The ID of the template to delete.
        """
        with Session(self.engine) as session:
            template = self._get_schema_by_id(
                resource_id=template_id,
                schema_class=RunTemplateSchema,
                session=session,
            )

            session.delete(template)
            # We set the reference of all deployments to this template to null
            # manually as we can't have a foreign key there to avoid a cycle
            deployments = session.exec(
                select(PipelineDeploymentSchema).where(
                    PipelineDeploymentSchema.template_id == template_id
                )
            ).all()
            for deployment in deployments:
                deployment.template_id = None
                session.add(deployment)

            session.commit()

    def run_template(
        self,
        template_id: UUID,
        run_configuration: Optional[PipelineRunConfiguration] = None,
    ) -> NoReturn:
        """Run a template.

        Args:
            template_id: The ID of the template to run.
            run_configuration: Configuration for the run.

        Raises:
            NotImplementedError: Always.
        """
        raise NotImplementedError(
            "Running a template is not possible with a local store."
        )

    # -------------------- Event Sources  --------------------

    def create_event_source(
        self, event_source: EventSourceRequest
    ) -> EventSourceResponse:
        """Create an event_source.

        Args:
            event_source: The event_source to create.

        Returns:
            The created event_source.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=event_source, session=session
            )

            self._verify_name_uniqueness(
                resource=event_source,
                schema=EventSourceSchema,
                session=session,
            )

            new_event_source = EventSourceSchema.from_request(event_source)
            session.add(new_event_source)
            session.commit()
            session.refresh(new_event_source)

            return new_event_source.to_model(
                include_metadata=True, include_resources=True
            )

    def get_event_source(
        self,
        event_source_id: UUID,
        hydrate: bool = True,
    ) -> EventSourceResponse:
        """Get an event_source by ID.

        Args:
            event_source_id: The ID of the event_source to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The event_source.
        """
        with Session(self.engine) as session:
            event_source = self._get_schema_by_id(
                resource_id=event_source_id,
                schema_class=EventSourceSchema,
                session=session,
            )
            return event_source.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_event_sources(
        self,
        event_source_filter_model: EventSourceFilter,
        hydrate: bool = False,
    ) -> Page[EventSourceResponse]:
        """List all event_sources matching the given filter criteria.

        Args:
            event_source_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all event_sources matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=event_source_filter_model,
                session=session,
            )
            query = select(EventSourceSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=EventSourceSchema,
                filter_model=event_source_filter_model,
                hydrate=hydrate,
            )

    def update_event_source(
        self,
        event_source_id: UUID,
        event_source_update: EventSourceUpdate,
    ) -> EventSourceResponse:
        """Update an existing event_source.

        Args:
            event_source_id: The ID of the event_source to update.
            event_source_update: The update to be applied to the event_source.

        Returns:
            The updated event_source.
        """
        with Session(self.engine) as session:
            event_source = self._get_schema_by_id(
                resource_id=event_source_id,
                schema_class=EventSourceSchema,
                session=session,
            )

            self._verify_name_uniqueness(
                resource=event_source_update,
                schema=event_source,
                session=session,
            )

            event_source.update(update=event_source_update)
            session.add(event_source)
            session.commit()

            # Refresh the event_source that was just created
            session.refresh(event_source)
            return event_source.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_event_source(self, event_source_id: UUID) -> None:
        """Delete an event_source.

        Args:
            event_source_id: The ID of the event_source to delete.

        Raises:
            IllegalOperationError: If the event source can't be deleted
                because it's used by triggers.
        """
        with Session(self.engine) as session:
            event_source = self._get_schema_by_id(
                resource_id=event_source_id,
                schema_class=EventSourceSchema,
                session=session,
            )

            # Prevent deletion of event source if it is used by a trigger
            if event_source.triggers:
                raise IllegalOperationError(
                    f"Unable to delete event_source with ID `{event_source_id}`"
                    f" as it is used by {len(event_source.triggers)} triggers."
                )

            session.delete(event_source)
            session.commit()

    # ----------------------------- Pipeline runs -----------------------------

    def get_pipeline_run_dag(self, pipeline_run_id: UUID) -> PipelineRunDAG:
        """Get the DAG of a pipeline run.

        Args:
            pipeline_run_id: The ID of the pipeline run.

        Returns:
            The DAG of the pipeline run.
        """
        helper = DAGGeneratorHelper()
        with Session(self.engine) as session:
            run = self._get_schema_by_id(
                resource_id=pipeline_run_id,
                schema_class=PipelineRunSchema,
                session=session,
                query_options=[
                    joinedload(jl_arg(PipelineRunSchema.deployment)),
                    # joinedload(jl_arg(PipelineRunSchema.step_runs)).sele(
                    #     jl_arg(StepRunSchema.input_artifacts)
                    # ),
                    # joinedload(jl_arg(PipelineRunSchema.step_runs)).joinedload(
                    #     jl_arg(StepRunSchema.output_artifacts)
                    # ),
                ],
            )
            assert run.deployment is not None
            deployment = run.deployment
            step_runs = {step.name: step for step in run.step_runs}

            pipeline_configuration = PipelineConfiguration.model_validate_json(
                deployment.pipeline_configuration
            )
            pipeline_configuration.finalize_substitutions(
                start_time=run.start_time, inplace=True
            )

            steps = {
                step_name: Step.from_dict(
                    config_dict, pipeline_configuration=pipeline_configuration
                )
                for step_name, config_dict in json.loads(
                    deployment.step_configurations
                ).items()
            }
            regular_output_artifact_nodes: Dict[
                str, Dict[str, PipelineRunDAG.Node]
            ] = defaultdict(dict)

            def _get_regular_output_artifact_node(
                step_name: str, output_name: str
            ) -> PipelineRunDAG.Node:
                substituted_output_name = format_name_template(
                    output_name,
                    substitutions=steps[step_name].config.substitutions,
                )
                return regular_output_artifact_nodes[step_name][
                    substituted_output_name
                ]

            for step_name, step in steps.items():
                upstream_steps = set(step.spec.upstream_steps)

                step_id = None
                metadata: Dict[str, Any] = {}

                step_run = step_runs.get(step_name)
                if step_run:
                    step_id = step_run.id
                    metadata["status"] = step_run.status

                    if step_run.end_time and step_run.start_time:
                        metadata["duration"] = (
                            step_run.end_time - step_run.start_time
                        ).total_seconds()

                step_node = helper.add_step_node(
                    node_id=helper.get_step_node_id(name=step_name),
                    id=step_id,
                    name=step_name,
                    **metadata,
                )

                if step_run:
                    for input in step_run.input_artifacts:
                        input_type = StepRunInputArtifactType(input.type)

                        if input_type == StepRunInputArtifactType.STEP_OUTPUT:
                            # This is a regular input artifact, so it is
                            # guaranteed that an upstream step already ran and
                            # produced the artifact.
                            input_config = step.spec.inputs[input.name]
                            artifact_node = _get_regular_output_artifact_node(
                                input_config.step_name,
                                input_config.output_name,
                            )

                            # If the upstream step and the current step are
                            # already connected via a regular artifact, we
                            # don't add a direct edge between the two.
                            try:
                                upstream_steps.remove(input_config.step_name)
                            except KeyError:
                                pass
                        else:
                            # This is not a regular input artifact, but a
                            # dynamic (loaded inside the step), external or
                            # lazy-loaded artifact. It might be that this was
                            # produced by another step in this pipeline, but
                            # we want to display them as separate nodes in the
                            # DAG. We can therefore always create a new node
                            # here.
                            artifact_node = helper.add_artifact_node(
                                node_id=helper.get_artifact_node_id(
                                    name=input.name,
                                    step_name=step_name,
                                    io_type=input.type,
                                    is_input=True,
                                ),
                                id=input.artifact_id,
                                name=input.name,
                                type=input.artifact_version.type,
                                data_type=Source.model_validate_json(
                                    input.artifact_version.data_type
                                ).import_path,
                                save_type=input.artifact_version.save_type,
                            )

                        helper.add_edge(
                            source=artifact_node.node_id,
                            target=step_node.node_id,
                            input_name=input.name,
                            type=input_type.value,
                        )

                    for output in step_run.output_artifacts:
                        # There is a very rare case where a node in the DAG
                        # already exists for an output artifact. This can happen
                        # when there are two steps that have no direct
                        # dependency and can therefore run at the same time, and
                        # one of them is producing an artifact that is then lazy
                        # or dynamically loaded by the other step. We do not
                        # want to merge these and instead display them
                        # separately in the DAG, but if that should ever change
                        # this would be the place to merge them.
                        artifact_node = helper.add_artifact_node(
                            node_id=helper.get_artifact_node_id(
                                name=output.name,
                                step_name=step_name,
                                io_type=output.artifact_version.save_type,
                                is_input=False,
                            ),
                            id=output.artifact_id,
                            name=output.name,
                            type=output.artifact_version.type,
                            data_type=Source.model_validate_json(
                                output.artifact_version.data_type
                            ).import_path,
                            save_type=output.artifact_version.save_type,
                        )

                        helper.add_edge(
                            source=step_node.node_id,
                            target=artifact_node.node_id,
                            output_name=output.name,
                            type=output.artifact_version.save_type,
                        )
                        if (
                            output.artifact_version.save_type
                            == ArtifactSaveType.STEP_OUTPUT
                        ):
                            regular_output_artifact_nodes[step_name][
                                output.name
                            ] = artifact_node

                    for output_name in step.config.outputs.keys():
                        # If the step failed or is still running, we do not have
                        # its regular outputs. So we populate the DAG with the
                        # outputs from the config instead.
                        substituted_output_name = format_name_template(
                            output_name,
                            substitutions=step.config.substitutions,
                        )
                        if (
                            substituted_output_name
                            in regular_output_artifact_nodes[step_name]
                        ):
                            # If the real output already exists we can skip
                            # adding a new node for it.
                            continue

                        artifact_node = helper.add_artifact_node(
                            node_id=helper.get_artifact_node_id(
                                name=substituted_output_name,
                                step_name=step_name,
                                io_type=ArtifactSaveType.STEP_OUTPUT.value,
                                is_input=False,
                            ),
                            name=substituted_output_name,
                        )
                        helper.add_edge(
                            source=step_node.node_id,
                            target=artifact_node.node_id,
                            output_name=output_name,
                            type=ArtifactSaveType.STEP_OUTPUT.value,
                        )
                        regular_output_artifact_nodes[step_name][
                            substituted_output_name
                        ] = artifact_node
                else:
                    for input_name, input_config in step.spec.inputs.items():
                        # This node should always exist, as the step
                        # configurations are sorted and therefore all
                        # upstream steps should have been processed already.
                        artifact_node = _get_regular_output_artifact_node(
                            input_config.step_name,
                            input_config.output_name,
                        )

                        helper.add_edge(
                            source=artifact_node.node_id,
                            target=step_node.node_id,
                            input_name=input_name,
                            type=StepRunInputArtifactType.STEP_OUTPUT.value,
                        )
                        # If the upstream step and the current step are
                        # already connected via a regular artifact, we
                        # don't add a direct edge between the two.
                        try:
                            upstream_steps.remove(input_config.step_name)
                        except KeyError:
                            pass

                    for input_name in step.config.client_lazy_loaders.keys():
                        artifact_node = helper.add_artifact_node(
                            node_id=helper.get_artifact_node_id(
                                name=input_name,
                                step_name=step_name,
                                io_type=StepRunInputArtifactType.LAZY_LOADED.value,
                                is_input=True,
                            ),
                            name=input_name,
                        )
                        helper.add_edge(
                            source=artifact_node.node_id,
                            target=step_node.node_id,
                            input_name=input_name,
                            type=StepRunInputArtifactType.LAZY_LOADED.value,
                        )

                    for (
                        input_name
                    ) in step.config.model_artifacts_or_metadata.keys():
                        artifact_node = helper.add_artifact_node(
                            node_id=helper.get_artifact_node_id(
                                name=input_name,
                                step_name=step_name,
                                io_type=StepRunInputArtifactType.LAZY_LOADED.value,
                                is_input=True,
                            ),
                            name=input_name,
                        )
                        helper.add_edge(
                            source=artifact_node.node_id,
                            target=step_node.node_id,
                            input_name=input_name,
                            type=StepRunInputArtifactType.LAZY_LOADED.value,
                        )

                    for (
                        input_name
                    ) in step.config.external_input_artifacts.keys():
                        artifact_node = helper.add_artifact_node(
                            node_id=helper.get_artifact_node_id(
                                name=input_name,
                                step_name=step_name,
                                io_type=StepRunInputArtifactType.EXTERNAL.value,
                                is_input=True,
                            ),
                            name=input_name,
                        )
                        helper.add_edge(
                            source=artifact_node.node_id,
                            target=step_node.node_id,
                            input_name=input_name,
                            type=StepRunInputArtifactType.EXTERNAL.value,
                        )

                    for output_name in step.config.outputs.keys():
                        substituted_output_name = format_name_template(
                            output_name,
                            substitutions=step.config.substitutions,
                        )
                        artifact_node = helper.add_artifact_node(
                            node_id=helper.get_artifact_node_id(
                                name=substituted_output_name,
                                step_name=step_name,
                                io_type=ArtifactSaveType.STEP_OUTPUT.value,
                                is_input=False,
                            ),
                            name=substituted_output_name,
                        )
                        helper.add_edge(
                            source=step_node.node_id,
                            target=artifact_node.node_id,
                            output_name=output_name,
                            type=ArtifactSaveType.STEP_OUTPUT.value,
                        )
                        regular_output_artifact_nodes[step_name][
                            substituted_output_name
                        ] = artifact_node

                for upstream_step_name in upstream_steps:
                    upstream_node = helper.get_step_node_by_name(
                        upstream_step_name
                    )
                    helper.add_edge(
                        source=upstream_node.node_id,
                        target=step_node.node_id,
                    )

        return helper.finalize_dag(
            pipeline_run_id=pipeline_run_id, status=ExecutionStatus(run.status)
        )

    def _create_run(
        self, pipeline_run: PipelineRunRequest, session: Session
    ) -> PipelineRunResponse:
        """Creates a pipeline run.

        Args:
            pipeline_run: The pipeline run to create.
            session: SQLAlchemy session.

        Returns:
            The created pipeline run.

        Raises:
            EntityExistsError: If a run with the same name already exists.
        """
        self._set_request_user_id(request_model=pipeline_run, session=session)
        self._get_reference_schema_by_id(
            resource=pipeline_run,
            reference_schema=PipelineDeploymentSchema,
            reference_id=pipeline_run.deployment,
            session=session,
        )

        self._get_reference_schema_by_id(
            resource=pipeline_run,
            reference_schema=PipelineSchema,
            reference_id=pipeline_run.pipeline,
            session=session,
        )

        new_run = PipelineRunSchema.from_request(pipeline_run)

        session.add(new_run)

        # Add logs entry for the run if exists
        if pipeline_run.logs is not None:
            self._get_reference_schema_by_id(
                resource=pipeline_run,
                reference_schema=StackComponentSchema,
                reference_id=pipeline_run.logs.artifact_store_id,
                session=session,
                reference_type="logs artifact store",
            )

            log_entry = LogsSchema(
                uri=pipeline_run.logs.uri,
                pipeline_run_id=new_run.id,
                artifact_store_id=pipeline_run.logs.artifact_store_id,
            )
            session.add(log_entry)

        try:
            session.commit()
        except IntegrityError:
            # We have to rollback the failed session first in order to
            # continue using it
            session.rollback()
            # This can fail if the name is taken by a different run
            self._verify_name_uniqueness(
                resource=pipeline_run,
                schema=PipelineRunSchema,
                session=session,
            )

            # ... or if the deployment_id and orchestrator_run_id are used
            # by an existing run
            raise EntityExistsError(
                "Unable to create pipeline run: A pipeline run with "
                "the same deployment_id and orchestrator_run_id "
                "already exists."
            )

        if model_version_id := self._get_or_create_model_version_for_run(
            new_run
        ):
            new_run.model_version_id = model_version_id
            session.add(new_run)
            session.commit()

            self.create_model_version_pipeline_run_link(
                ModelVersionPipelineRunRequest(
                    model_version=model_version_id, pipeline_run=new_run.id
                )
            )
            session.refresh(new_run)

        self._attach_tags_to_resources(
            tags=pipeline_run.tags,
            resources=new_run,
            session=session,
        )

        session.refresh(new_run)

        return new_run.to_model(include_metadata=True, include_resources=True)

    def get_run(
        self,
        run_id: UUID,
        hydrate: bool = True,
        include_full_metadata: bool = False,
        include_python_packages: bool = False,
    ) -> PipelineRunResponse:
        """Gets a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            include_full_metadata: Flag deciding whether to include the
                full metadata in the response.
            include_python_packages: Flag deciding whether to include the
                python packages in the response.

        Returns:
            The pipeline run.
        """
        with Session(self.engine) as session:
            run = self._get_schema_by_id(
                resource_id=run_id,
                schema_class=PipelineRunSchema,
                session=session,
                query_options=PipelineRunSchema.get_query_options(
                    include_metadata=hydrate, include_resources=True
                ),
            )
            return run.to_model(
                include_metadata=hydrate,
                include_resources=True,
                include_python_packages=include_python_packages,
                include_full_metadata=include_full_metadata,
            )

    def get_run_status(
        self,
        run_id: UUID,
    ) -> Tuple[ExecutionStatus, Optional[datetime]]:
        """Gets the status of a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The pipeline run status and end time.
        """
        with Session(self.engine) as session:
            run = self._get_schema_by_id(
                resource_id=run_id,
                schema_class=PipelineRunSchema,
                session=session,
            )
            return ExecutionStatus(run.status), run.end_time

    def _replace_placeholder_run(
        self,
        pipeline_run: PipelineRunRequest,
        session: Session,
        pre_replacement_hook: Optional[Callable[[], None]] = None,
    ) -> PipelineRunResponse:
        """Replace a placeholder run with the requested pipeline run.

        Args:
            pipeline_run: Pipeline run request.
            session: SQLAlchemy session.
            pre_replacement_hook: Optional function to run before replacing the
                pipeline run.

        Raises:
            KeyError: If no placeholder run exists.

        Returns:
            The run model.
        """
        run_schema = session.exec(
            select(PipelineRunSchema)
            # The following line locks the row in the DB, so anyone else
            # calling `SELECT ... FOR UPDATE` will wait until the first
            # transaction to do so finishes. After the first transaction
            # finishes, the subsequent queries will not be able to find a
            # placeholder run anymore, as we already updated the
            # orchestrator_run_id.
            # Note: This only locks a single row if the where clause of
            # the query is indexed (we have a unique index due to the
            # unique constraint on those columns). Otherwise, this will lock
            # multiple rows or even the complete table which we want to
            # avoid.
            .with_for_update()
            .where(PipelineRunSchema.deployment_id == pipeline_run.deployment)
            .where(
                PipelineRunSchema.orchestrator_run_id.is_(None)  # type: ignore[union-attr]
            )
            .where(PipelineRunSchema.project_id == pipeline_run.project)
        ).first()

        if not run_schema:
            raise KeyError("No placeholder run found.")

        if pre_replacement_hook:
            pre_replacement_hook()
        run_schema.update_placeholder(pipeline_run)

        session.add(run_schema)
        session.commit()

        self._attach_tags_to_resources(
            tags=pipeline_run.tags,
            resources=run_schema,
            session=session,
        )

        session.refresh(run_schema)

        return run_schema.to_model(
            include_metadata=True, include_resources=True
        )

    def _get_run_by_orchestrator_run_id(
        self, orchestrator_run_id: str, deployment_id: UUID, session: Session
    ) -> PipelineRunResponse:
        """Get a pipeline run based on deployment and orchestrator run ID.

        Args:
            orchestrator_run_id: The orchestrator run ID.
            deployment_id: The deployment ID.
            session: SQLAlchemy session.

        Raises:
            KeyError: If no run exists for the deployment and orchestrator run
                ID.

        Returns:
            The pipeline run.
        """
        run_schema = session.exec(
            select(PipelineRunSchema)
            .where(PipelineRunSchema.deployment_id == deployment_id)
            .where(
                PipelineRunSchema.orchestrator_run_id == orchestrator_run_id
            )
        ).first()

        if not run_schema:
            raise KeyError(
                f"Unable to get run for orchestrator run ID "
                f"{orchestrator_run_id} and deployment ID {deployment_id}."
            )

        return run_schema.to_model(
            include_metadata=True, include_resources=True
        )

    def get_or_create_run(
        self,
        pipeline_run: PipelineRunRequest,
        pre_creation_hook: Optional[Callable[[], None]] = None,
    ) -> Tuple[PipelineRunResponse, bool]:
        """Gets or creates a pipeline run.

        If a run with the same ID or name already exists, it is returned.
        Otherwise, a new run is created.

        Args:
            pipeline_run: The pipeline run to get or create.
            pre_creation_hook: Optional function to run before creating the
                pipeline run.

        # noqa: DAR401
        Raises:
            EntityExistsError: If a run with the same name already exists.
            RuntimeError: If the run fetching failed unexpectedly.

        Returns:
            The pipeline run, and a boolean indicating whether the run was
            created or not.
        """
        with Session(self.engine) as session:
            if pipeline_run.orchestrator_run_id:
                try:
                    # We first try the most likely case that the run was already
                    # created by a previous step in the same pipeline run.
                    return (
                        self._get_run_by_orchestrator_run_id(
                            orchestrator_run_id=pipeline_run.orchestrator_run_id,
                            deployment_id=pipeline_run.deployment,
                            session=session,
                        ),
                        False,
                    )
                except KeyError:
                    pass

            try:
                return (
                    self._replace_placeholder_run(
                        pipeline_run=pipeline_run,
                        pre_replacement_hook=pre_creation_hook,
                        session=session,
                    ),
                    True,
                )
            except KeyError:
                # We were not able to find/replace a placeholder run. This could
                # be due to one of the following three reasons:
                # (1) There never was a placeholder run for the deployment. This
                #     is the case if the user ran the pipeline on a schedule.
                # (2) There was a placeholder run, but a previous pipeline run
                #     already used it. This is the case if users rerun a
                #     pipeline run e.g. from the orchestrator UI, as they will
                #     use the same deployment_id with a new orchestrator_run_id.
                # (3) A step of the same pipeline run already replaced the
                #     placeholder run.
                pass

            try:
                # We now try to create a new run. The following will happen in
                # the three cases described above:
                # (1) The behavior depends on whether we're the first step of
                #     the pipeline run that's trying to create the run. If yes,
                #     the `self._create_run(...)` call will succeed. If no, a
                #     run with the same deployment_id and orchestrator_run_id
                #     already exists and the `self._create_run(...)` call will
                #     fail due to the unique constraint on those columns.
                # (2) Same as (1).
                # (3) A step of the same pipeline run replaced the placeholder
                #     run, which now contains the deployment_id and
                #     orchestrator_run_id of the run that we're trying to
                #     create.
                #     -> The `self._create_run(...)` call will fail due to the
                #     unique constraint on those columns.
                if pre_creation_hook:
                    pre_creation_hook()
                return self._create_run(pipeline_run, session=session), True
            except EntityExistsError as create_error:
                if not pipeline_run.orchestrator_run_id:
                    raise
                # Creating the run failed because
                # - a run with the same deployment_id and orchestrator_run_id
                #   exists. We now fetch and return that run.
                # - a run with the same name already exists. This could be
                #   either a different run (in which case we want to fail) or a
                #   run created by a step of the same pipeline run (in which
                #   case we want to return it).
                try:
                    return (
                        self._get_run_by_orchestrator_run_id(
                            orchestrator_run_id=pipeline_run.orchestrator_run_id,
                            deployment_id=pipeline_run.deployment,
                            session=session,
                        ),
                        False,
                    )
                except KeyError:
                    # We should only get here if the run creation failed because
                    # of a name conflict. We raise the error that happened
                    # during creation in any case to forward the error message
                    # to the user.
                    raise create_error

    def list_runs(
        self,
        runs_filter_model: PipelineRunFilter,
        hydrate: bool = False,
        include_full_metadata: bool = False,
    ) -> Page[PipelineRunResponse]:
        """List all pipeline runs matching the given filter criteria.

        Args:
            runs_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.
            include_full_metadata: If True, include metadata of all steps in
                the response.

        Returns:
            A list of all pipeline runs matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=runs_filter_model,
                session=session,
            )
            query = select(PipelineRunSchema)

            return self.filter_and_paginate(
                session=session,
                query=query,
                table=PipelineRunSchema,
                filter_model=runs_filter_model,
                hydrate=hydrate,
                custom_schema_to_model_conversion=lambda schema: schema.to_model(
                    include_metadata=hydrate,
                    include_resources=True,
                    include_full_metadata=include_full_metadata,
                ),
                apply_query_options_from_schema=True,
            )

    def update_run(
        self, run_id: UUID, run_update: PipelineRunUpdate
    ) -> PipelineRunResponse:
        """Updates a pipeline run.

        Args:
            run_id: The ID of the pipeline run to update.
            run_update: The update to be applied to the pipeline run.

        Returns:
            The updated pipeline run.
        """
        with Session(self.engine) as session:
            # Check if pipeline run with the given ID exists
            existing_run = self._get_schema_by_id(
                resource_id=run_id,
                schema_class=PipelineRunSchema,
                session=session,
            )

            existing_run.update(run_update=run_update)
            session.add(existing_run)
            session.commit()
            session.refresh(existing_run)

            self._attach_tags_to_resources(
                tags=run_update.add_tags,
                resources=existing_run,
                session=session,
            )
            self._detach_tags_from_resources(
                tags=run_update.remove_tags,
                resources=existing_run,
                session=session,
            )
            session.refresh(existing_run)
            return existing_run.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_run(self, run_id: UUID) -> None:
        """Deletes a pipeline run.

        Args:
            run_id: The ID of the pipeline run to delete.
        """
        with Session(self.engine) as session:
            # Check if pipeline run with the given ID exists
            existing_run = self._get_schema_by_id(
                resource_id=run_id,
                schema_class=PipelineRunSchema,
                session=session,
            )

            # Delete the pipeline run
            session.delete(existing_run)
            session.commit()

    def count_runs(self, filter_model: PipelineRunFilter) -> int:
        """Count all pipeline runs.

        Args:
            filter_model: The filter model to filter the runs.

        Returns:
            The number of pipeline runs.
        """
        return self._count_entity(
            schema=PipelineRunSchema, filter_model=filter_model
        )

    # ----------------------------- Run Metadata -----------------------------

    def create_run_metadata(self, run_metadata: RunMetadataRequest) -> None:
        """Creates run metadata.

        Args:
            run_metadata: The run metadata to create.

        Returns:
            The created run metadata.

        Raises:
            RuntimeError: If the resource type is not supported.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=run_metadata, session=session
            )

            self._get_reference_schema_by_id(
                resource=run_metadata,
                reference_schema=StackComponentSchema,
                reference_id=run_metadata.stack_component_id,
                session=session,
            )

            for resource in run_metadata.resources:
                reference_schema: Type[BaseSchema]
                if resource.type == MetadataResourceTypes.PIPELINE_RUN:
                    reference_schema = PipelineRunSchema
                elif resource.type == MetadataResourceTypes.STEP_RUN:
                    reference_schema = StepRunSchema
                elif resource.type == MetadataResourceTypes.ARTIFACT_VERSION:
                    reference_schema = ArtifactVersionSchema
                elif resource.type == MetadataResourceTypes.MODEL_VERSION:
                    reference_schema = ModelVersionSchema
                elif resource.type == MetadataResourceTypes.SCHEDULE:
                    reference_schema = ScheduleSchema
                else:
                    raise RuntimeError(
                        f"Unknown resource type: {resource.type}"
                    )

                self._get_reference_schema_by_id(
                    resource=run_metadata,
                    reference_schema=reference_schema,
                    reference_id=resource.id,
                    session=session,
                )

            if run_metadata.resources:
                for key, value in run_metadata.values.items():
                    type_ = run_metadata.types[key]

                    run_metadata_schema = RunMetadataSchema(
                        project_id=run_metadata.project,
                        user_id=run_metadata.user,
                        stack_component_id=run_metadata.stack_component_id,
                        key=key,
                        value=json.dumps(value),
                        type=type_,
                        publisher_step_id=run_metadata.publisher_step_id,
                    )

                    session.add(run_metadata_schema)
                    session.commit()

                    for resource in run_metadata.resources:
                        rm_resource_link = RunMetadataResourceSchema(
                            resource_id=resource.id,
                            resource_type=resource.type.value,
                            run_metadata_id=run_metadata_schema.id,
                        )
                        session.add(rm_resource_link)
                        session.commit()
        return None

    # ----------------------------- Schedules -----------------------------

    def create_schedule(self, schedule: ScheduleRequest) -> ScheduleResponse:
        """Creates a new schedule.

        Args:
            schedule: The schedule to create.

        Returns:
            The newly created schedule.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=schedule, session=session)

            self._verify_name_uniqueness(
                resource=schedule,
                schema=ScheduleSchema,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=schedule,
                reference_schema=StackComponentSchema,
                reference_id=schedule.orchestrator_id,
                session=session,
                reference_type="orchestrator",
            )

            self._get_reference_schema_by_id(
                resource=schedule,
                reference_schema=PipelineSchema,
                reference_id=schedule.pipeline_id,
                session=session,
            )

            new_schedule = ScheduleSchema.from_request(schedule)
            session.add(new_schedule)
            session.commit()
            return new_schedule.to_model(
                include_metadata=True, include_resources=True
            )

    def get_schedule(
        self, schedule_id: UUID, hydrate: bool = True
    ) -> ScheduleResponse:
        """Get a schedule with a given ID.

        Args:
            schedule_id: ID of the schedule.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The schedule.
        """
        with Session(self.engine) as session:
            # Check if schedule with the given ID exists
            schedule = self._get_schema_by_id(
                resource_id=schedule_id,
                schema_class=ScheduleSchema,
                session=session,
            )
            return schedule.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_schedules(
        self,
        schedule_filter_model: ScheduleFilter,
        hydrate: bool = False,
    ) -> Page[ScheduleResponse]:
        """List all schedules.

        Args:
            schedule_filter_model: All filter parameters including pagination
                params
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of schedules.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=schedule_filter_model,
                session=session,
            )
            query = select(ScheduleSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ScheduleSchema,
                filter_model=schedule_filter_model,
                hydrate=hydrate,
            )

    def update_schedule(
        self,
        schedule_id: UUID,
        schedule_update: ScheduleUpdate,
    ) -> ScheduleResponse:
        """Updates a schedule.

        Args:
            schedule_id: The ID of the schedule to be updated.
            schedule_update: The update to be applied.

        Returns:
            The updated schedule.
        """
        with Session(self.engine) as session:
            # Check if schedule with the given ID exists
            existing_schedule = self._get_schema_by_id(
                resource_id=schedule_id,
                schema_class=ScheduleSchema,
                session=session,
            )

            self._verify_name_uniqueness(
                resource=schedule_update,
                schema=existing_schedule,
                session=session,
            )

            # Update the schedule
            existing_schedule = existing_schedule.update(schedule_update)
            session.add(existing_schedule)
            session.commit()
            return existing_schedule.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_schedule(self, schedule_id: UUID) -> None:
        """Deletes a schedule.

        Args:
            schedule_id: The ID of the schedule to delete.
        """
        with Session(self.engine) as session:
            # Check if schedule with the given ID exists
            schedule = self._get_schema_by_id(
                resource_id=schedule_id,
                schema_class=ScheduleSchema,
                session=session,
            )

            # Delete the schedule
            session.delete(schedule)
            session.commit()

    # ------------------------- Secrets -------------------------

    def _check_sql_secret_scope(
        self,
        session: Session,
        secret_name: str,
        private: bool,
        user: UUID,
        exclude_secret_id: Optional[UUID] = None,
    ) -> Tuple[bool, str]:
        """Checks if a secret with the given name already exists with the given private status.

        This method enforces the following private status rules:

        - a user cannot own two private secrets with the same name
        - two public secrets cannot have the same name

        Args:
            session: The SQLAlchemy session.
            secret_name: The name of the secret.
            private: The private status of the secret.
            user: The ID of the user to which the secret belongs.
            exclude_secret_id: The ID of a secret to exclude from the check
                (used e.g. during an update to exclude the existing secret).

        Returns:
            True if a secret with the given name already exists with the given
            private status, False otherwise, and an error message.
        """
        scope_filter = (
            select(SecretSchema)
            .where(SecretSchema.name == secret_name)
            .where(SecretSchema.private == private)
        )

        if private:
            scope_filter = scope_filter.where(SecretSchema.user_id == user)
        if exclude_secret_id is not None:
            scope_filter = scope_filter.where(
                SecretSchema.id != exclude_secret_id
            )

        existing_secret = session.exec(scope_filter).first()

        if existing_secret is not None:
            existing_secret_model = existing_secret.to_model(
                include_metadata=True
            )

            private_status = "private" if private else "public"
            msg = (
                f"Found an existing {private_status} secret with the "
                f"same '{secret_name}' name"
            )
            if private:
                assert existing_secret_model.user
                msg += (
                    f" for the same '{existing_secret_model.user.name}' user"
                )

            return True, msg

        return False, ""

    def _set_secret_values(
        self, secret_id: UUID, values: Dict[str, str], backup: bool = True
    ) -> None:
        """Sets the values of a secret in the configured secrets store.

        Args:
            secret_id: The ID of the secret to set the values of.
            values: The values to set.
            backup: Whether to back up the values in the backup secrets store,
                if configured.

        # noqa: DAR401
        """

        def do_backup() -> bool:
            """Backs up the values of a secret in the configured backup secrets store.

            Returns:
                True if the backup succeeded, False otherwise.
            """
            if not backup or not self.backup_secrets_store:
                return False
            logger.info(
                f"Storing secret {secret_id} in the backup secrets store. "
            )
            try:
                self._backup_secret_values(secret_id=secret_id, values=values)
            except Exception:
                logger.exception(
                    f"Failed to store secret values for secret with ID "
                    f"{secret_id} in the backup secrets store. "
                )
                return False
            return True

        try:
            self.secrets_store.store_secret_values(
                secret_id=secret_id, secret_values=values
            )
        except Exception:
            logger.exception(
                f"Failed to store secret values for secret with ID "
                f"{secret_id} in the primary secrets store. "
            )
            if not do_backup():
                raise
        else:
            do_backup()

    def _backup_secret_values(
        self, secret_id: UUID, values: Dict[str, str]
    ) -> None:
        """Backs up the values of a secret in the configured backup secrets store.

        Args:
            secret_id: The ID of the secret the values of which to backup.
            values: The values to back up.
        """
        if self.backup_secrets_store:
            # We attempt either an update or a create operation depending on
            # whether the secret values are already stored in the backup
            # secrets store. This is to account for any inconsistencies in the
            # backup secrets store without impairing the backup functionality.
            try:
                self.backup_secrets_store.get_secret_values(
                    secret_id=secret_id,
                )
            except KeyError:
                self.backup_secrets_store.store_secret_values(
                    secret_id=secret_id, secret_values=values
                )
            else:
                self.backup_secrets_store.update_secret_values(
                    secret_id=secret_id, secret_values=values
                )

    def _get_secret_values(
        self, secret_id: UUID, use_backup: bool = True
    ) -> Dict[str, str]:
        """Gets the values of a secret from the configured secrets store.

        Args:
            secret_id: The ID of the secret to get the values of.
            use_backup: Whether to use the backup secrets store if the primary
                secrets store fails to retrieve the values and if a backup
                secrets store is configured.

        Returns:
            The values of the secret.

        # noqa: DAR401
        """
        try:
            return self.secrets_store.get_secret_values(
                secret_id=secret_id,
            )
        except Exception as e:
            if use_backup and self.backup_secrets_store:
                logger.exception(
                    f"Failed to get secret values for secret with ID "
                    f"{secret_id} from the primary secrets store. "
                    f"Trying to get them from the backup secrets store. "
                )
                try:
                    backup_values = self._get_backup_secret_values(
                        secret_id=secret_id
                    )
                    if isinstance(e, KeyError):
                        # Attempt to automatically restore the values in the
                        # primary secrets store if the backup secrets store
                        # succeeds in retrieving them and if the values are
                        # missing in the primary secrets store.
                        try:
                            self.secrets_store.store_secret_values(
                                secret_id=secret_id,
                                secret_values=backup_values,
                            )
                        except Exception:
                            logger.exception(
                                f"Failed to restore secret values for secret "
                                f"with ID {secret_id} in the primary secrets "
                                "store. "
                            )
                    return backup_values
                except Exception:
                    logger.exception(
                        f"Failed to get secret values for secret with ID "
                        f"{secret_id} from the backup secrets store. "
                    )
            raise

    def _get_backup_secret_values(self, secret_id: UUID) -> Dict[str, str]:
        """Gets the backup values of a secret from the configured backup secrets store.

        Args:
            secret_id: The ID of the secret to get the values of.

        Returns:
            The backup values of the secret.

        Raises:
            KeyError: If no backup secrets store is configured.
        """
        if self.backup_secrets_store:
            return self.backup_secrets_store.get_secret_values(
                secret_id=secret_id,
            )
        raise KeyError(
            f"Unable to get backup secret values for secret with ID "
            f"{secret_id}: No backup secrets store is configured."
        )

    def _update_secret_values(
        self,
        secret_id: UUID,
        values: Dict[str, Optional[str]],
        overwrite: bool = False,
        backup: bool = True,
    ) -> Dict[str, str]:
        """Updates the values of a secret in the configured secrets store.

        This method will update the existing values with the new values
        and drop `None` values.

        Args:
            secret_id: The ID of the secret to set the values of.
            values: The updated values to set.
            overwrite: Whether to overwrite the existing values with the new
                values. If set to False, the new values will be merged with the
                existing values.
            backup: Whether to back up the updated values in the backup secrets
                store, if configured.

        Returns:
            The updated values.

        # noqa: DAR401
        """
        try:
            existing_values = self._get_secret_values(
                secret_id=secret_id, use_backup=backup
            )
        except KeyError:
            logger.error(
                f"Unable to update secret values for secret with ID "
                f"{secret_id}: No secret with this ID found in the secrets "
                f"store back-end. Creating a new secret instead."
            )
            # If no secret values are yet stored in the secrets store,
            # we simply treat this as a create operation. This is to account
            # for cases in which secrets are manually deleted in the secrets
            # store backend or when the secrets store backend is reconfigured to
            # a different account, provider, region etc. without migrating
            # the actual existing secrets themselves.
            new_values: Dict[str, str] = {
                k: v for k, v in values.items() if v is not None
            }
            self._set_secret_values(
                secret_id=secret_id, values=new_values, backup=backup
            )
            return new_values

        if overwrite:
            existing_values = {
                k: v for k, v in values.items() if v is not None
            }
        else:
            for k, v in values.items():
                if v is not None:
                    existing_values[k] = v
                # Drop values removed in the update
                if v is None and k in existing_values:
                    del existing_values[k]

        def do_backup() -> bool:
            """Backs up the values of a secret in the configured backup secrets store.

            Returns:
                True if the backup succeeded, False otherwise.
            """
            if not backup or not self.backup_secrets_store:
                return False
            logger.info(
                f"Storing secret {secret_id} in the backup secrets store. "
            )
            try:
                self._backup_secret_values(
                    secret_id=secret_id, values=existing_values
                )
            except Exception:
                logger.exception(
                    f"Failed to store secret values for secret with ID "
                    f"{secret_id} in the backup secrets store. "
                )
                return False
            return True

        try:
            self.secrets_store.update_secret_values(
                secret_id=secret_id, secret_values=existing_values
            )
        except Exception:
            logger.exception(
                f"Failed to update secret values for secret with ID "
                f"{secret_id} in the primary secrets store. "
            )
            if not do_backup():
                raise
        else:
            do_backup()

        return existing_values

    def _delete_secret_values(
        self,
        secret_id: UUID,
        delete_backup: bool = True,
    ) -> None:
        """Deletes the values of a secret in the configured secrets store.

        Args:
            secret_id: The ID of the secret for which to delete the values.
            delete_backup: Whether to delete the backup values of the secret
                from the backup secrets store, if configured.

        # noqa: DAR401
        """

        def do_delete_backup() -> bool:
            """Deletes the backup values of a secret in the configured backup secrets store.

            Returns:
                True if the backup deletion succeeded, False otherwise.
            """
            if not delete_backup or not self.backup_secrets_store:
                return False

            logger.info(
                f"Deleting secret {secret_id} from the backup secrets store."
            )
            try:
                self._delete_backup_secret_values(secret_id=secret_id)
            except KeyError:
                # If the secret doesn't exist in the backup secrets store, we
                # consider this a success.
                return True
            except Exception:
                logger.exception(
                    f"Failed to delete secret values for secret with ID "
                    f"{secret_id} from the backup secrets store. "
                )
                return False

            return True

        try:
            self.secrets_store.delete_secret_values(secret_id=secret_id)
        except KeyError:
            # If the secret doesn't exist in the primary secrets store, we
            # consider this a success.
            do_delete_backup()
        except Exception:
            logger.exception(
                f"Failed to delete secret values for secret with ID "
                f"{secret_id} from the primary secrets store. "
            )
            if not do_delete_backup():
                raise
        else:
            do_delete_backup()

    def _delete_backup_secret_values(
        self,
        secret_id: UUID,
    ) -> None:
        """Deletes the backup values of a secret in the configured backup secrets store.

        Args:
            secret_id: The ID of the secret for which to delete the backup values.
        """
        if self.backup_secrets_store:
            self.backup_secrets_store.delete_secret_values(secret_id=secret_id)

    @track_decorator(AnalyticsEvent.CREATED_SECRET)
    def create_secret(self, secret: SecretRequest) -> SecretResponse:
        """Creates a new secret.

        The new secret is also validated against the scoping rules enforced in
        the secrets store:

        - a user cannot own two private secrets with the same name
        - two public secrets cannot have the same name

        Args:
            secret: The secret to create.

        Returns:
            The newly created secret.

        Raises:
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=secret, session=session)
            assert secret.user is not None
            # Check if a secret with the same name already exists in the same
            # scope.
            secret_exists, msg = self._check_sql_secret_scope(
                session=session,
                secret_name=secret.name,
                private=secret.private,
                user=secret.user,
            )
            if secret_exists:
                raise EntityExistsError(msg)

            new_secret = SecretSchema.from_request(
                secret,
            )
            session.add(new_secret)
            session.commit()

            secret_model = new_secret.to_model(
                include_metadata=True, include_resources=True
            )

        try:
            # Set the secret values in the configured secrets store
            self._set_secret_values(
                secret_id=new_secret.id, values=secret.secret_values
            )
        except:
            # If setting the secret values fails, delete the secret from the
            # database.
            with Session(self.engine) as session:
                session.delete(new_secret)
                session.commit()
            raise

        secret_model.set_secrets(secret.secret_values)
        return secret_model

    def get_secret(
        self, secret_id: UUID, hydrate: bool = True
    ) -> SecretResponse:
        """Get a secret by ID.

        Args:
            secret_id: The ID of the secret to fetch.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The secret.

        Raises:
            KeyError: if the secret doesn't exist.
        """
        with Session(self.engine) as session:
            secret_in_db = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).first()
            if (
                secret_in_db is None
                # Private secrets are only accessible to their owner
                or secret_in_db.private
                and secret_in_db.user.id != self._get_active_user(session).id
            ):
                raise KeyError(
                    f"Secret with ID {secret_id} not found or is private and "
                    "not owned by the current user."
                )

            secret_model = secret_in_db.to_model(
                include_metadata=hydrate, include_resources=True
            )

        secret_model.set_secrets(self._get_secret_values(secret_id=secret_id))

        return secret_model

    def list_secrets(
        self, secret_filter_model: SecretFilter, hydrate: bool = False
    ) -> Page[SecretResponse]:
        """List all secrets matching the given filter criteria.

        Note that returned secrets do not include any secret values. To fetch
        the secret values, use `get_secret`.

        Args:
            secret_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all secrets matching the filter criteria, with pagination
            information and sorted according to the filter criteria. The
            returned secrets do not include any secret values, only metadata. To
            fetch the secret values, use `get_secret` individually with each
            secret.
        """
        with Session(self.engine) as session:
            # Filter all secrets according to their private status and the active
            # user
            secret_filter_model.set_scope_user(
                self._get_active_user(session).id
            )
            query = select(SecretSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=SecretSchema,
                filter_model=secret_filter_model,
                hydrate=hydrate,
            )

    def update_secret(
        self, secret_id: UUID, secret_update: SecretUpdate
    ) -> SecretResponse:
        """Updates a secret.

        Secret values that are specified as `None` in the update that are
        present in the existing secret are removed from the existing secret.
        Values that are present in both secrets are overwritten. All other
        values in both the existing secret and the update are kept (merged).

        If the update includes a change of name or scope, the scoping rules
        enforced in the secrets store are used to validate the update:

        - a user cannot own two private secrets with the same name
        - two public secrets cannot have the same name

        Args:
            secret_id: The ID of the secret to be updated.
            secret_update: The update to be applied.

        Returns:
            The updated secret.

        Raises:
            KeyError: if the secret doesn't exist.
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
            IllegalOperationError: if the secret is private and the current user
                is not the owner of the secret.
        """
        with Session(self.engine) as session:
            existing_secret = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).first()

            active_user = self._get_active_user(session)

            if not existing_secret or (
                # Private secrets are only accessible to their owner
                existing_secret.private
                and existing_secret.user.id != active_user.id
            ):
                raise KeyError(
                    f"Secret with ID {secret_id} not found or is private and "
                    "not owned by the current user."
                )

            if (
                secret_update.private is not None
                and existing_secret.user.id != active_user.id
            ):
                raise IllegalOperationError(
                    "Only the user who created the secret is allowed to update "
                    "its private status."
                )

            # A change in name or scope requires a check of the scoping rules.
            if (
                secret_update.name is not None
                and existing_secret.name != secret_update.name
                or secret_update.private is not None
                and existing_secret.private != secret_update.private
            ):
                secret_exists, msg = self._check_sql_secret_scope(
                    session=session,
                    secret_name=secret_update.name or existing_secret.name,
                    private=secret_update.private
                    if secret_update.private is not None
                    else existing_secret.private,
                    user=existing_secret.user.id,
                    exclude_secret_id=secret_id,
                )

                if secret_exists:
                    raise EntityExistsError(msg)

            existing_secret.update(
                secret_update=secret_update,
            )
            session.add(existing_secret)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_secret)
            secret_model = existing_secret.to_model(
                include_metadata=True, include_resources=True
            )

        if secret_update.values is not None:
            # Update the secret values in the configured secrets store
            updated_values = self._update_secret_values(
                secret_id=secret_id,
                values=secret_update.get_secret_values_update(),
            )
            secret_model.set_secrets(updated_values)
        else:
            secret_model.set_secrets(self._get_secret_values(secret_id))

        return secret_model

    def delete_secret(self, secret_id: UUID) -> None:
        """Delete a secret.

        Args:
            secret_id: The id of the secret to delete.

        Raises:
            KeyError: if the secret doesn't exist.
        """
        with Session(self.engine) as session:
            existing_secret = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).first()

            if not existing_secret or (
                # Private secrets are only accessible to their owner
                existing_secret.private
                and existing_secret.user.id
                != self._get_active_user(session).id
            ):
                raise KeyError(
                    f"Secret with ID {secret_id} not found or is private and "
                    "not owned by the current user."
                )

            # Delete the secret values in the configured secrets store
            try:
                self._delete_secret_values(secret_id=secret_id)
            except KeyError:
                # If the secret values don't exist in the secrets store, we don't
                # need to raise an error.
                pass

            secret_in_db = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).one()
            session.delete(secret_in_db)
            session.commit()

    def backup_secrets(
        self, ignore_errors: bool = True, delete_secrets: bool = False
    ) -> None:
        """Backs up all secrets to the configured backup secrets store.

        Args:
            ignore_errors: Whether to ignore individual errors during the backup
                process and attempt to backup all secrets.
            delete_secrets: Whether to delete the secrets that have been
                successfully backed up from the primary secrets store. Setting
                this flag effectively moves all secrets from the primary secrets
                store to the backup secrets store.

        # noqa: DAR401
        Raises:
            BackupSecretsStoreNotConfiguredError: if no backup secrets store is
                configured.
        """
        if not self.backup_secrets_store:
            raise BackupSecretsStoreNotConfiguredError(
                "Unable to backup secrets: No backup secrets store is "
                "configured."
            )

        with Session(self.engine) as session:
            secrets_in_db = session.exec(select(SecretSchema)).all()

        for secret in secrets_in_db:
            try:
                values = self._get_secret_values(
                    secret_id=secret.id, use_backup=False
                )
            except Exception:
                logger.exception(
                    f"Failed to get secret values for secret with ID "
                    f"{secret.id}."
                )
                if ignore_errors:
                    continue
                raise

            try:
                self._backup_secret_values(secret_id=secret.id, values=values)
            except Exception:
                logger.exception(
                    f"Failed to backup secret with ID {secret.id}. "
                )
                if ignore_errors:
                    continue
                raise

            if delete_secrets:
                try:
                    self._delete_secret_values(
                        secret_id=secret.id, delete_backup=False
                    )
                except Exception:
                    logger.exception(
                        f"Failed to delete secret with ID {secret.id} from the "
                        f"primary secrets store after backing it up to the "
                        f"backup secrets store."
                    )
                    if ignore_errors:
                        continue
                    raise

    def restore_secrets(
        self, ignore_errors: bool = False, delete_secrets: bool = False
    ) -> None:
        """Restore all secrets from the configured backup secrets store.

        Args:
            ignore_errors: Whether to ignore individual errors during the
                restore process and attempt to restore all secrets.
            delete_secrets: Whether to delete the secrets that have been
                successfully restored from the backup secrets store. Setting
                this flag effectively moves all secrets from the backup secrets
                store to the primary secrets store.

        # noqa: DAR401
        Raises:
            BackupSecretsStoreNotConfiguredError: if no backup secrets store is
                configured.
        """
        if not self.backup_secrets_store:
            raise BackupSecretsStoreNotConfiguredError(
                "Unable to restore secrets: No backup secrets store is "
                "configured."
            )

        with Session(self.engine) as session:
            secrets_in_db = session.exec(select(SecretSchema)).all()

        for secret in secrets_in_db:
            try:
                values = self._get_backup_secret_values(secret_id=secret.id)
            except Exception:
                logger.exception(
                    f"Failed to get backup secret values for secret with ID "
                    f"{secret.id}."
                )
                if ignore_errors:
                    continue
                raise

            try:
                self._update_secret_values(
                    secret_id=secret.id,
                    values=cast(Dict[str, Optional[str]], values),
                    overwrite=True,
                    backup=False,
                )
            except Exception:
                logger.exception(
                    f"Failed to restore secret with ID {secret.id}. "
                )
                if ignore_errors:
                    continue
                raise

            if delete_secrets:
                try:
                    self._delete_backup_secret_values(secret_id=secret.id)
                except Exception:
                    logger.exception(
                        f"Failed to delete backup secret with ID {secret.id} "
                        f"from the backup secrets store after restoring it to "
                        f"the primary secrets store."
                    )
                    if ignore_errors:
                        continue
                    raise

    # ------------------------- Service Accounts -------------------------

    @track_decorator(AnalyticsEvent.CREATED_SERVICE_ACCOUNT)
    def create_service_account(
        self, service_account: ServiceAccountRequest
    ) -> ServiceAccountResponse:
        """Creates a new service account.

        Args:
            service_account: Service account to be created.

        Returns:
            The newly created service account.

        Raises:
            EntityExistsError: If a user or service account with the given name
                already exists.
        """
        with Session(self.engine) as session:
            # Check if a service account with the given name already
            # exists
            err_msg = (
                f"Unable to create service account with name "
                f"'{service_account.name}': Found existing service "
                "account with this name."
            )
            try:
                self._get_account_schema(
                    service_account.name, session=session, service_account=True
                )
                raise EntityExistsError(err_msg)
            except KeyError:
                pass

            # Create the service account
            new_account = UserSchema.from_service_account_request(
                service_account
            )
            session.add(new_account)
            # on commit an IntegrityError may arise we let it bubble up
            session.commit()

            return new_account.to_service_account_model(
                include_metadata=True, include_resources=True
            )

    def get_service_account(
        self,
        service_account_name_or_id: Union[str, UUID],
        hydrate: bool = True,
    ) -> ServiceAccountResponse:
        """Gets a specific service account.

        Raises a KeyError in case a service account with that id does not exist.

        Args:
            service_account_name_or_id: The name or ID of the service account to
                get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested service account, if it was found.
        """
        with Session(self.engine) as session:
            account = self._get_account_schema(
                service_account_name_or_id,
                session=session,
                service_account=True,
            )

            return account.to_service_account_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_service_accounts(
        self,
        filter_model: ServiceAccountFilter,
        hydrate: bool = False,
    ) -> Page[ServiceAccountResponse]:
        """List all service accounts.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of filtered service accounts.
        """
        with Session(self.engine) as session:
            query = select(UserSchema)
            paged_service_accounts: Page[ServiceAccountResponse] = (
                self.filter_and_paginate(
                    session=session,
                    query=query,
                    table=UserSchema,
                    filter_model=filter_model,
                    custom_schema_to_model_conversion=lambda user: user.to_service_account_model(
                        include_metadata=hydrate, include_resources=True
                    ),
                    hydrate=hydrate,
                )
            )
            return paged_service_accounts

    def update_service_account(
        self,
        service_account_name_or_id: Union[str, UUID],
        service_account_update: ServiceAccountUpdate,
    ) -> ServiceAccountResponse:
        """Updates an existing service account.

        Args:
            service_account_name_or_id: The name or the ID of the service
                account to update.
            service_account_update: The update to be applied to the service
                account.

        Returns:
            The updated service account.

        Raises:
            EntityExistsError: If a user or service account with the given name
                already exists.
        """
        with Session(self.engine) as session:
            existing_service_account = self._get_account_schema(
                service_account_name_or_id,
                session=session,
                service_account=True,
            )

            if (
                service_account_update.name is not None
                and service_account_update.name
                != existing_service_account.name
            ):
                try:
                    self._get_account_schema(
                        service_account_update.name,
                        session=session,
                        service_account=True,
                    )
                    raise EntityExistsError(
                        f"Unable to update service account with name "
                        f"'{service_account_update.name}': Found an existing "
                        "service account with this name."
                    )
                except KeyError:
                    pass

            existing_service_account.update_service_account(
                service_account_update=service_account_update
            )
            session.add(existing_service_account)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_service_account)
            return existing_service_account.to_service_account_model(
                include_metadata=True, include_resources=True
            )

    def delete_service_account(
        self,
        service_account_name_or_id: Union[str, UUID],
    ) -> None:
        """Delete a service account.

        Args:
            service_account_name_or_id: The name or the ID of the service
                account to delete.

        Raises:
            IllegalOperationError: if the service account has already been used
                to create other resources.
        """
        with Session(self.engine) as session:
            service_account = self._get_account_schema(
                service_account_name_or_id,
                session=session,
                service_account=True,
            )
            # Check if the service account has any resources associated with it
            # and raise an error if it does.
            if self._account_owns_resources(service_account, session=session):
                raise IllegalOperationError(
                    "The service account has already been used to create "
                    "other resources that it now owns and therefore cannot be "
                    "deleted. Please delete all resources owned by the service "
                    "account or consider deactivating it instead."
                )

            session.delete(service_account)
            session.commit()

    # --------------------------- Service Connectors ---------------------------

    @track_decorator(AnalyticsEvent.CREATED_SERVICE_CONNECTOR)
    def create_service_connector(
        self, service_connector: ServiceConnectorRequest
    ) -> ServiceConnectorResponse:
        """Creates a new service connector.

        Args:
            service_connector: Service connector to be created.

        Returns:
            The newly created service connector.

        Raises:
            Exception: If anything goes wrong during the creation of the
                service connector.
        """
        # If the connector type is locally available, we validate the request
        # against the connector type schema before storing it in the database
        if service_connector_registry.is_registered(service_connector.type):
            connector_type = (
                service_connector_registry.get_service_connector_type(
                    service_connector.type
                )
            )
            service_connector.validate_and_configure_resources(
                connector_type=connector_type,
                resource_types=service_connector.resource_types,
                resource_id=service_connector.resource_id,
                configuration=service_connector.configuration,
                secrets=service_connector.secrets,
            )

        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=service_connector, session=session
            )
            assert service_connector.user is not None

            self._verify_name_uniqueness(
                resource=service_connector,
                schema=ServiceConnectorSchema,
                session=session,
            )

            # Create the secret
            secret_id = self._create_connector_secret(
                connector_name=service_connector.name,
                secrets=service_connector.secrets,
            )
            try:
                # Create the service connector
                new_service_connector = ServiceConnectorSchema.from_request(
                    service_connector,
                    secret_id=secret_id,
                )

                session.add(new_service_connector)
                session.commit()

                session.refresh(new_service_connector)
            except Exception:
                # Delete the secret if it was created
                if secret_id:
                    try:
                        self.delete_secret(secret_id)
                    except Exception:
                        # Ignore any errors that occur while deleting the
                        # secret
                        pass

                raise

            connector = new_service_connector.to_model(
                include_metadata=True, include_resources=True
            )
            self._populate_connector_type(connector)

            return connector

    def get_service_connector(
        self, service_connector_id: UUID, hydrate: bool = True
    ) -> ServiceConnectorResponse:
        """Gets a specific service connector.

        Args:
            service_connector_id: The ID of the service connector to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested service connector, if it was found.
        """
        with Session(self.engine) as session:
            service_connector = self._get_schema_by_id(
                resource_id=service_connector_id,
                schema_class=ServiceConnectorSchema,
                session=session,
            )

            connector = service_connector.to_model(
                include_metadata=hydrate, include_resources=True
            )
            self._populate_connector_type(connector)
            return connector

    def list_service_connectors(
        self,
        filter_model: ServiceConnectorFilter,
        hydrate: bool = False,
    ) -> Page[ServiceConnectorResponse]:
        """List all service connectors.

        Args:
            filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all service connectors.
        """

        def fetch_connectors(
            session: Session,
            query: Union[
                Select[ServiceConnectorSchema],
                SelectOfScalar[ServiceConnectorSchema],
            ],
            filter_model: BaseFilter,
        ) -> Sequence[ServiceConnectorSchema]:
            """Custom fetch function for connector filtering and pagination.

            Applies resource type and label filters to the query.

            Args:
                session: The database session.
                query: The query to filter.
                filter_model: The filter model.

            Returns:
                The filtered and paginated results.
            """
            assert isinstance(filter_model, ServiceConnectorFilter)
            items = self._list_filtered_service_connectors(
                session=session, query=query, filter_model=filter_model
            )

            return items

        with Session(self.engine) as session:
            query = select(ServiceConnectorSchema)
            paged_connectors: Page[ServiceConnectorResponse] = (
                self.filter_and_paginate(
                    session=session,
                    query=query,
                    table=ServiceConnectorSchema,
                    filter_model=filter_model,
                    custom_fetch=fetch_connectors,
                    hydrate=hydrate,
                )
            )

            self._populate_connector_type(*paged_connectors.items)
            return paged_connectors

    def update_service_connector(
        self, service_connector_id: UUID, update: ServiceConnectorUpdate
    ) -> ServiceConnectorResponse:
        """Updates an existing service connector.

        The update model contains the fields to be updated. If a field value is
        set to None in the model, the field is not updated, but there are
        special rules concerning some fields:

        * the `configuration` and `secrets` fields together represent a full
        valid configuration update, not just a partial update. If either is
        set (i.e. not None) in the update, their values are merged together and
        will replace the existing configuration and secrets values.
        * the `resource_id` field value is also a full replacement value: if set
        to `None`, the resource ID is removed from the service connector.
        * the `expiration_seconds` field value is also a full replacement value:
        if set to `None`, the expiration is removed from the service connector.
        * the `secret_id` field value in the update is ignored, given that
        secrets are managed internally by the ZenML store.
        * the `labels` field is also a full labels update: if set (i.e. not
        `None`), all existing labels are removed and replaced by the new labels
        in the update.

        Args:
            service_connector_id: The ID of the service connector to update.
            update: The update to be applied to the service connector.

        Returns:
            The updated service connector.

        Raises:
            IllegalOperationError: If the service connector is referenced by
                one or more stack components and the update would change the
                connector type, resource type or resource ID.
        """
        with Session(self.engine) as session:
            existing_connector = self._get_schema_by_id(
                resource_id=service_connector_id,
                schema_class=ServiceConnectorSchema,
                session=session,
            )

            # In case of a renaming update, make sure no service connector uses
            # that name already
            self._verify_name_uniqueness(
                resource=update,
                schema=existing_connector,
                session=session,
            )

            existing_connector_model = existing_connector.to_model(
                include_metadata=True
            )

            if len(existing_connector.components):
                # If the service connector is already used in one or more
                # stack components, the update is no longer allowed to change
                # the service connector's authentication method, connector type,
                # resource type, or resource ID
                if (
                    update.connector_type
                    and update.type != existing_connector_model.connector_type
                ):
                    raise IllegalOperationError(
                        "The service type of a service connector that is "
                        "already actively used in one or more stack components "
                        "cannot be changed."
                    )

                if (
                    update.auth_method
                    and update.auth_method
                    != existing_connector_model.auth_method
                ):
                    raise IllegalOperationError(
                        "The authentication method of a service connector that "
                        "is already actively used in one or more stack "
                        "components cannot be changed."
                    )

                if (
                    update.resource_types
                    and update.resource_types
                    != existing_connector_model.resource_types
                ):
                    raise IllegalOperationError(
                        "The resource type of a service connector that is "
                        "already actively used in one or more stack components "
                        "cannot be changed."
                    )

                # The resource ID field cannot be used as a partial update: if
                # set to None, the existing resource ID is also removed
                if update.resource_id != existing_connector_model.resource_id:
                    raise IllegalOperationError(
                        "The resource ID of a service connector that is "
                        "already actively used in one or more stack components "
                        "cannot be changed."
                    )

            # If the connector type is locally available, we validate the update
            # against the connector type schema before storing it in the
            # database
            if service_connector_registry.is_registered(
                existing_connector.connector_type
            ):
                connector_type = (
                    service_connector_registry.get_service_connector_type(
                        existing_connector.connector_type
                    )
                )
                # We need the auth method to be set to be able to validate the
                # configuration
                update.auth_method = (
                    update.auth_method or existing_connector_model.auth_method
                )
                # Validate the configuration update. If the configuration or
                # secrets fields are set, together they are merged into a
                # full configuration that is validated against the connector
                # type schema and replaces the existing configuration and
                # secrets values
                update.validate_and_configure_resources(
                    connector_type=connector_type,
                    resource_types=update.resource_types,
                    resource_id=update.resource_id,
                    configuration=update.configuration,
                    secrets=update.secrets,
                )

            # Update secret
            secret_id = self._update_connector_secret(
                existing_connector=existing_connector_model,
                updated_connector=update,
            )

            existing_connector.update(
                connector_update=update, secret_id=secret_id
            )
            session.add(existing_connector)
            session.commit()

            connector = existing_connector.to_model(
                include_metadata=True, include_resources=True
            )
            self._populate_connector_type(connector)
            return connector

    def delete_service_connector(self, service_connector_id: UUID) -> None:
        """Deletes a service connector.

        Args:
            service_connector_id: The ID of the service connector to delete.

        Raises:
            IllegalOperationError: If the service connector is still referenced
                by one or more stack components.
        """
        with Session(self.engine) as session:
            service_connector = self._get_schema_by_id(
                resource_id=service_connector_id,
                schema_class=ServiceConnectorSchema,
                session=session,
            )

            if len(service_connector.components) > 0:
                raise IllegalOperationError(
                    f"Service connector with ID {service_connector_id} "
                    f"cannot be deleted as it is still referenced by "
                    f"{len(service_connector.components)} "
                    "stack components. Before deleting this service "
                    "connector, make sure to remove it from all stack "
                    "components."
                )
            else:
                session.delete(service_connector)

            if service_connector.secret_id:
                try:
                    self.delete_secret(service_connector.secret_id)
                except KeyError:
                    # If the secret doesn't exist anymore, we can ignore
                    # this error
                    pass

            session.commit()

    def _create_connector_secret(
        self,
        connector_name: str,
        secrets: Optional[Dict[str, Optional[SecretStr]]],
    ) -> Optional[UUID]:
        """Creates a new secret to store the service connector secret credentials.

        Args:
            connector_name: The name of the service connector for which to
                create a secret.
            secrets: The secret credentials to store.

        Returns:
            The ID of the newly created secret or None, if the service connector
            does not contain any secret credentials.
        """
        if not secrets:
            return None

        # Generate a unique name for the secret
        # Replace all non-alphanumeric characters with a dash because
        # the secret name must be a valid DNS subdomain name in some
        # secrets stores
        connector_name = re.sub(r"[^a-zA-Z0-9-]", "-", connector_name)
        # Generate unique names using a random suffix until we find a name
        # that is not already in use
        while True:
            secret_name = f"connector-{connector_name}-{random_str(4)}".lower()
            existing_secrets = self.list_secrets(
                SecretFilter(
                    name=secret_name,
                )
            )
            if not existing_secrets.size:
                try:
                    return self.create_secret(
                        SecretRequest(
                            name=secret_name,
                            private=False,
                            values=secrets,
                        )
                    ).id
                except KeyError:
                    # The secret already exists, try again
                    continue

    @staticmethod
    def _populate_connector_type(
        *service_connectors: ServiceConnectorResponse,
    ) -> None:
        """Populates the connector type of the given service connectors.

        If the connector type is not locally available, the connector type
        field is left as is.

        Args:
            service_connectors: The service connectors to populate.
        """
        for service_connector in service_connectors:
            if not service_connector_registry.is_registered(
                service_connector.type
            ):
                continue
            service_connector.set_connector_type(
                service_connector_registry.get_service_connector_type(
                    service_connector.type
                )
            )

    @staticmethod
    def _list_filtered_service_connectors(
        session: Session,
        query: Union[
            Select[ServiceConnectorSchema],
            SelectOfScalar[ServiceConnectorSchema],
        ],
        filter_model: ServiceConnectorFilter,
    ) -> Sequence[ServiceConnectorSchema]:
        """Refine a service connector query.

        Applies resource type and label filters to the query.

        Args:
            session: The database session.
            query: The query to filter.
            filter_model: The filter model.

        Returns:
            The filtered list of service connectors.
        """
        items: Sequence[ServiceConnectorSchema] = session.exec(query).all()

        # filter out items that don't match the resource type
        if filter_model.resource_type:
            items = [
                item
                for item in items
                if filter_model.resource_type in item.resource_types_list
            ]

        # filter out items that don't match the labels
        if filter_model.labels:
            items = [
                item for item in items if item.has_labels(filter_model.labels)
            ]

        return items

    def _update_connector_secret(
        self,
        existing_connector: ServiceConnectorResponse,
        updated_connector: ServiceConnectorUpdate,
    ) -> Optional[UUID]:
        """Updates the secret for a service connector.

        If the secrets field in the service connector update is set (i.e. not
        None), the existing secret, if any, is replaced. If the secrets field is
        set to an empty dict, the existing secret is deleted.

        Args:
            existing_connector: Existing service connector for which to update a
                secret.
            updated_connector: Updated service connector.

        Returns:
            The ID of the updated secret or None, if the new service connector
            does not contain any secret credentials.
        """
        if updated_connector.secrets is None:
            # If the connector update does not contain a secrets update, keep
            # the existing secret (if any)
            return existing_connector.secret_id

        # Delete the existing secret (if any), to be replaced by the new secret
        if existing_connector.secret_id:
            try:
                self.delete_secret(existing_connector.secret_id)
            except KeyError:
                # Ignore if the secret no longer exists
                pass

        # If the new service connector does not contain any secret credentials,
        # return None
        if not updated_connector.secrets:
            return None

        assert existing_connector.user is not None
        # A secret does not exist yet, create a new one
        return self._create_connector_secret(
            connector_name=updated_connector.name or existing_connector.name,
            secrets=updated_connector.secrets,
        )

    def verify_service_connector_config(
        self,
        service_connector: ServiceConnectorRequest,
        list_resources: bool = True,
    ) -> ServiceConnectorResourcesModel:
        """Verifies if a service connector configuration has access to resources.

        Args:
            service_connector: The service connector configuration to verify.
            list_resources: If True, the list of all resources accessible
                through the service connector is returned.

        Returns:
            The list of resources that the service connector configuration has
            access to.
        """
        connector_instance = service_connector_registry.instantiate_connector(
            model=service_connector
        )
        return connector_instance.verify(list_resources=list_resources)

    def verify_service_connector(
        self,
        service_connector_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        list_resources: bool = True,
    ) -> ServiceConnectorResourcesModel:
        """Verifies if a service connector instance has access to one or more resources.

        Args:
            service_connector_id: The ID of the service connector to verify.
            resource_type: The type of resource to verify access to.
            resource_id: The ID of the resource to verify access to.
            list_resources: If True, the list of all resources accessible
                through the service connector and matching the supplied resource
                type and ID are returned.

        Returns:
            The list of resources that the service connector has access to,
            scoped to the supplied resource type and ID, if provided.
        """
        connector = self.get_service_connector(service_connector_id)

        connector_instance = service_connector_registry.instantiate_connector(
            model=connector
        )

        return connector_instance.verify(
            resource_type=resource_type,
            resource_id=resource_id,
            list_resources=list_resources,
        )

    def get_service_connector_client(
        self,
        service_connector_id: UUID,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> ServiceConnectorResponse:
        """Get a service connector client for a service connector and given resource.

        Args:
            service_connector_id: The ID of the base service connector to use.
            resource_type: The type of resource to get a client for.
            resource_id: The ID of the resource to get a client for.

        Returns:
            A service connector client that can be used to access the given
            resource.
        """
        connector = self.get_service_connector(service_connector_id)

        connector_instance = service_connector_registry.instantiate_connector(
            model=connector
        )

        # Fetch the connector client
        connector_client = connector_instance.get_connector_client(
            resource_type=resource_type,
            resource_id=resource_id,
        )

        # Return the model for the connector client
        connector = connector_client.to_response_model(
            user=connector.user,
            description=connector.description,
            labels=connector.labels,
        )

        self._populate_connector_type(connector)

        return connector

    def list_service_connector_resources(
        self,
        filter_model: ServiceConnectorFilter,
    ) -> List[ServiceConnectorResourcesModel]:
        """List resources that can be accessed by service connectors.

        Args:
            filter_model: Optional filter model to use when fetching service
                connectors.

        Returns:
            The matching list of resources that available service
            connectors have access to.
        """
        # We process the resource_id filter separately, if set, because
        # this is not a simple string comparison, but specific to every
        # connector type.
        resource_id = filter_model.resource_id
        filter_model.resource_id = None

        service_connectors = self.list_service_connectors(
            filter_model=filter_model
        ).items

        resource_list: List[ServiceConnectorResourcesModel] = []

        for connector in service_connectors:
            if not service_connector_registry.is_registered(connector.type):
                # For connectors that we can instantiate, i.e. those that have a
                # connector type available locally, we return complete
                # information about the resources that they have access to.
                #
                # For those that are not locally available, we only return
                # rudimentary information extracted from the connector model
                # without actively trying to discover the resources that they
                # have access to.

                if resource_id and connector.resource_id != resource_id:
                    # If an explicit resource ID is required, the connector
                    # has to be configured with it.
                    continue

                resources = (
                    ServiceConnectorResourcesModel.from_connector_model(
                        connector,
                        resource_type=filter_model.resource_type,
                    )
                )
                for r in resources.resources:
                    if not r.resource_ids:
                        r.error = (
                            f"The service '{connector.type}' connector type is "
                            "not available."
                        )

            else:
                try:
                    connector_instance = (
                        service_connector_registry.instantiate_connector(
                            model=connector
                        )
                    )

                    resources = connector_instance.verify(
                        resource_type=filter_model.resource_type,
                        resource_id=resource_id,
                        list_resources=True,
                    )
                except (ValueError, AuthorizationException) as e:
                    error = (
                        f"Failed to fetch {filter_model.resource_type or 'available'} "
                        f"resources from service connector {connector.name}/"
                        f"{connector.id}: {e}"
                    )
                    # Log an exception if debug logging is enabled
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.exception(error)
                    else:
                        logger.error(error)
                    continue

            resource_list.append(resources)

        return resource_list

    def list_service_connector_types(
        self,
        connector_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        auth_method: Optional[str] = None,
    ) -> List[ServiceConnectorTypeModel]:
        """Get a list of service connector types.

        Args:
            connector_type: Filter by connector type.
            resource_type: Filter by resource type.
            auth_method: Filter by authentication method.

        Returns:
            List of service connector types.
        """
        return service_connector_registry.list_service_connector_types(
            connector_type=connector_type,
            resource_type=resource_type,
            auth_method=auth_method,
        )

    def get_service_connector_type(
        self,
        connector_type: str,
    ) -> ServiceConnectorTypeModel:
        """Returns the requested service connector type.

        Args:
            connector_type: the service connector type identifier.

        Returns:
            The requested service connector type.
        """
        return service_connector_registry.get_service_connector_type(
            connector_type
        )

    # ----------------------------- Stacks -----------------------------

    @track_decorator(AnalyticsEvent.REGISTERED_STACK)
    def create_stack(self, stack: StackRequest) -> StackResponse:
        """Register a full stack.

        Args:
            stack: The full stack configuration.

        Returns:
            The registered stack.

        Raises:
            ValueError: If the full stack creation fails, due to the corrupted
                input.
            Exception: If the full stack creation fails, due to unforeseen
                errors.
        """
        with Session(self.engine) as session:
            if isinstance(stack, DefaultStackRequest):
                # Set the user to None for default stacks
                stack.user = None
            else:
                self._set_request_user_id(request_model=stack, session=session)

            # For clean-up purposes, each created entity is tracked here
            service_connectors_created_ids: List[UUID] = []
            components_created_ids: List[UUID] = []

            try:
                # Validate the name of the new stack
                validate_name(stack)

                if stack.labels is None:
                    stack.labels = {}

                # Service Connectors
                service_connectors: List[ServiceConnectorResponse] = []

                orchestrator_components = stack.components[
                    StackComponentType.ORCHESTRATOR
                ]
                for orchestrator_component in orchestrator_components:
                    if isinstance(orchestrator_component, UUID):
                        orchestrator = self.get_stack_component(
                            orchestrator_component,
                            hydrate=False,
                        )
                        need_to_generate_permanent_tokens = (
                            orchestrator.flavor_name.startswith("vm_")
                        )
                    else:
                        need_to_generate_permanent_tokens = (
                            orchestrator_component.flavor.startswith("vm_")
                        )

                for connector_id_or_info in stack.service_connectors:
                    # Fetch an existing service connector
                    if isinstance(connector_id_or_info, UUID):
                        existing_service_connector = (
                            self.get_service_connector(connector_id_or_info)
                        )
                        if need_to_generate_permanent_tokens:
                            if (
                                existing_service_connector.configuration.get(
                                    "generate_temporary_tokens", None
                                )
                                is not False
                            ):
                                connector_config = (
                                    existing_service_connector.configuration
                                )
                                connector_config[
                                    "generate_temporary_tokens"
                                ] = False
                                self.update_service_connector(
                                    existing_service_connector.id,
                                    ServiceConnectorUpdate(
                                        configuration=connector_config
                                    ),
                                )
                        service_connectors.append(
                            self.get_service_connector(connector_id_or_info)
                        )
                    # Create a new service connector
                    else:
                        connector_name = stack.name
                        connector_config = connector_id_or_info.configuration
                        connector_config[
                            "generate_temporary_tokens"
                        ] = not need_to_generate_permanent_tokens

                        while True:
                            try:
                                service_connector_request = ServiceConnectorRequest(
                                    name=connector_name,
                                    connector_type=connector_id_or_info.type,
                                    auth_method=connector_id_or_info.auth_method,
                                    configuration=connector_config,
                                    labels={
                                        k: str(v)
                                        for k, v in stack.labels.items()
                                    },
                                )
                                service_connector_response = self.create_service_connector(
                                    service_connector=service_connector_request
                                )
                                service_connectors.append(
                                    service_connector_response
                                )
                                service_connectors_created_ids.append(
                                    service_connector_response.id
                                )
                                break
                            except EntityExistsError:
                                connector_name = (
                                    f"{stack.name}-{random_str(4)}".lower()
                                )
                                continue

                # Stack Components
                components_mapping: Dict[StackComponentType, List[UUID]] = {}
                for (
                    component_type,
                    components,
                ) in stack.components.items():
                    for component_info in components:
                        # Fetch an existing component
                        if isinstance(component_info, UUID):
                            component = self.get_stack_component(
                                component_id=component_info
                            )
                        # Create a new component
                        else:
                            flavor_list = self.list_flavors(
                                flavor_filter_model=FlavorFilter(
                                    name=component_info.flavor,
                                    type=component_type,
                                )
                            )
                            if not len(flavor_list):
                                raise ValueError(
                                    f"Flavor '{component_info.flavor}' not found "
                                    f"for component type '{component_type}'."
                                )

                            flavor_model = flavor_list[0]

                            component_name = stack.name
                            while True:
                                try:
                                    component_request = ComponentRequest(
                                        name=component_name,
                                        type=component_type,
                                        flavor=component_info.flavor,
                                        configuration=component_info.configuration,
                                        labels=stack.labels,
                                    )
                                    component = self.create_stack_component(
                                        component=component_request
                                    )
                                    components_created_ids.append(component.id)
                                    break
                                except EntityExistsError:
                                    component_name = (
                                        f"{stack.name}-{random_str(4)}".lower()
                                    )
                                    continue

                            if (
                                component_info.service_connector_index
                                is not None
                            ):
                                service_connector = service_connectors[
                                    component_info.service_connector_index
                                ]

                                requirements = (
                                    flavor_model.connector_requirements
                                )

                                if not requirements:
                                    raise ValueError(
                                        f"The '{flavor_model.name}' implementation "
                                        "does not support using a service "
                                        "connector to connect to resources."
                                    )

                                if component_info.service_connector_resource_id:
                                    resource_id = component_info.service_connector_resource_id
                                else:
                                    resource_id = None
                                    resource_type = requirements.resource_type
                                    if (
                                        requirements.resource_id_attr
                                        is not None
                                    ):
                                        resource_id = (
                                            component_info.configuration.get(
                                                requirements.resource_id_attr
                                            )
                                        )

                                satisfied, msg = requirements.is_satisfied_by(
                                    connector=service_connector,
                                    component=component,
                                )

                                if not satisfied:
                                    raise ValueError(
                                        "Please pick a connector that is "
                                        "compatible with the component flavor and "
                                        "try again.."
                                    )

                                if not resource_id:
                                    if service_connector.resource_id:
                                        resource_id = (
                                            service_connector.resource_id
                                        )
                                    elif service_connector.supports_instances:
                                        raise ValueError(
                                            f"Multiple {resource_type} resources "
                                            "are available for the selected "
                                            "connector. Please use a `resource_id` "
                                            "to configure a "
                                            f"{resource_type} resource."
                                        )

                                component_update = ComponentUpdate(
                                    connector=service_connector.id,
                                    connector_resource_id=resource_id,
                                )
                                self.update_stack_component(
                                    component_id=component.id,
                                    component_update=component_update,
                                )

                        components_mapping[component_type] = [
                            component.id,
                        ]

                # Stack
                self._verify_name_uniqueness(
                    resource=stack,
                    schema=StackSchema,
                    session=session,
                )

                component_ids = (
                    [
                        component_id
                        for list_of_component_ids in components_mapping.values()
                        for component_id in list_of_component_ids
                    ]
                    if stack.components is not None
                    else []
                )
                filters = [
                    (StackComponentSchema.id == component_id)
                    for component_id in component_ids
                ]

                defined_components = session.exec(
                    select(StackComponentSchema).where(or_(*filters))
                ).all()

                new_stack_schema = StackSchema(
                    user_id=stack.user,
                    stack_spec_path=stack.stack_spec_path,
                    name=stack.name,
                    description=stack.description,
                    components=defined_components,
                    labels=base64.b64encode(
                        json.dumps(stack.labels).encode("utf-8")
                    ),
                )

                session.add(new_stack_schema)
                session.commit()
                session.refresh(new_stack_schema)

                for defined_component in defined_components:
                    if (
                        defined_component.type
                        == StackComponentType.ORCHESTRATOR
                    ):
                        if defined_component.flavor not in {
                            "local",
                            "local_docker",
                        }:
                            self._update_onboarding_state(
                                completed_steps={
                                    OnboardingStep.STACK_WITH_REMOTE_ORCHESTRATOR_CREATED
                                },
                                session=session,
                            )
                    if (
                        defined_component.type
                        == StackComponentType.ARTIFACT_STORE
                    ):
                        if defined_component.flavor != "local":
                            self._update_onboarding_state(
                                completed_steps={
                                    OnboardingStep.STACK_WITH_REMOTE_ARTIFACT_STORE_CREATED
                                },
                                session=session,
                            )

                return new_stack_schema.to_model(
                    include_metadata=True, include_resources=True
                )

            except Exception:
                for component_id in components_created_ids:
                    self.delete_stack_component(component_id=component_id)
                for service_connector_id in service_connectors_created_ids:
                    self.delete_service_connector(
                        service_connector_id=service_connector_id
                    )
                logger.error(
                    "Stack creation has failed. Cleaned up the entities "
                    "that are created in the process."
                )
                raise

    def get_stack(self, stack_id: UUID, hydrate: bool = True) -> StackResponse:
        """Get a stack by its unique ID.

        Args:
            stack_id: The ID of the stack to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The stack with the given ID.
        """
        with Session(self.engine) as session:
            stack = self._get_schema_by_id(
                resource_id=stack_id,
                schema_class=StackSchema,
                session=session,
            )
            return stack.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_stacks(
        self,
        stack_filter_model: StackFilter,
        hydrate: bool = False,
    ) -> Page[StackResponse]:
        """List all stacks matching the given filter criteria.

        Args:
            stack_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all stacks matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(StackSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=StackSchema,
                filter_model=stack_filter_model,
                hydrate=hydrate,
            )

    @track_decorator(AnalyticsEvent.UPDATED_STACK)
    def update_stack(
        self, stack_id: UUID, stack_update: StackUpdate
    ) -> StackResponse:
        """Update a stack.

        Args:
            stack_id: The ID of the stack update.
            stack_update: The update request on the stack.

        Returns:
            The updated stack.

        Raises:
            IllegalOperationError: if the stack is a default stack.
        """
        with Session(self.engine) as session:
            existing_stack = self._get_schema_by_id(
                resource_id=stack_id,
                schema_class=StackSchema,
                session=session,
            )
            if existing_stack.name == DEFAULT_STACK_AND_COMPONENT_NAME:
                raise IllegalOperationError(
                    "The default stack cannot be modified."
                )
            # In case of a renaming update, make sure no stack already exists
            # with that name
            self._verify_name_uniqueness(
                resource=stack_update,
                schema=existing_stack,
                session=session,
            )

            components: List["StackComponentSchema"] = []
            if stack_update.components:
                for (
                    component_type,
                    list_of_component_ids,
                ) in stack_update.components.items():
                    for component_id in list_of_component_ids:
                        component = self._get_reference_schema_by_id(
                            resource=existing_stack,
                            reference_schema=StackComponentSchema,
                            reference_id=component_id,
                            session=session,
                            reference_type=f"{str(component_type)} stack component",
                        )
                        components.append(component)

            existing_stack.update(
                stack_update=stack_update,
                components=components,
            )

            session.add(existing_stack)
            session.commit()
            session.refresh(existing_stack)

            return existing_stack.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_stack(self, stack_id: UUID) -> None:
        """Delete a stack.

        Args:
            stack_id: The ID of the stack to delete.

        Raises:
            IllegalOperationError: if the stack is a default stack.
        """
        with Session(self.engine) as session:
            stack = self._get_schema_by_id(
                resource_id=stack_id,
                schema_class=StackSchema,
                session=session,
            )
            if stack.name == DEFAULT_STACK_AND_COMPONENT_NAME:
                raise IllegalOperationError(
                    "The default stack cannot be deleted."
                )
            session.delete(stack)
            session.commit()

    def count_stacks(self, filter_model: Optional[StackFilter]) -> int:
        """Count all stacks.

        Args:
            filter_model: The filter model to filter the stacks.

        Returns:
            The number of stacks.
        """
        return self._count_entity(
            schema=StackSchema, filter_model=filter_model
        )

    def _create_default_stack(
        self,
    ) -> StackResponse:
        """Create the default stack components and stack.

        The default stack contains a local orchestrator and a local artifact
        store.

        Returns:
            The model of the created default stack.
        """
        with analytics_disabler():
            logger.info("Creating default stack...")
            orchestrator = self.create_stack_component(
                # Use `DefaultComponentRequest` instead of
                # `ComponentRequest` here to force the `create_stack_component`
                # call to use `None` for the user, meaning the orchestrator
                # is owned by the server, which for RBAC indicates that
                # everyone can read it
                component=DefaultComponentRequest(
                    name=DEFAULT_STACK_AND_COMPONENT_NAME,
                    type=StackComponentType.ORCHESTRATOR,
                    flavor="local",
                    configuration={},
                ),
            )

            artifact_store = self.create_stack_component(
                # Use `DefaultComponentRequest` instead of
                # `ComponentRequest` here to force the `create_stack_component`
                # call to use `None` for the user, meaning the artifact store
                # is owned by the server, which for RBAC indicates that everyone
                # can read it
                component=DefaultComponentRequest(
                    name=DEFAULT_STACK_AND_COMPONENT_NAME,
                    type=StackComponentType.ARTIFACT_STORE,
                    flavor="local",
                    configuration={},
                ),
            )

            components = {
                c.type: [c.id] for c in [orchestrator, artifact_store]
            }

            # Use `DefaultStackRequest` instead of `StackRequest` here to force
            # the `create_stack` call to use `None` for the user, meaning the
            # stack is owned by the server, which for RBAC indicates that
            # everyone can read it
            stack = DefaultStackRequest(
                name=DEFAULT_STACK_AND_COMPONENT_NAME,
                components=components,
            )
            return self.create_stack(stack=stack)

    def _get_or_create_default_stack(
        self,
    ) -> StackResponse:
        """Get or create the default stack if it doesn't exist.

        Returns:
            The default stack.
        """
        try:
            return self._get_default_stack()
        except KeyError:
            return self._create_default_stack()

    # ---------------- Stack deployments-----------------

    def get_stack_deployment_info(
        self,
        provider: StackDeploymentProvider,
    ) -> StackDeploymentInfo:
        """Get information about a stack deployment provider.

        Args:
            provider: The stack deployment provider.

        Raises:
            NotImplementedError: Stack deployments are not supported by the
                local ZenML deployment.
        """
        raise NotImplementedError(
            "Stack deployments are not supported by local ZenML deployments."
        )

    def get_stack_deployment_config(
        self,
        provider: StackDeploymentProvider,
        stack_name: str,
        location: Optional[str] = None,
    ) -> StackDeploymentConfig:
        """Return the cloud provider console URL and configuration needed to deploy the ZenML stack.

        Args:
            provider: The stack deployment provider.
            stack_name: The name of the stack.
            location: The location where the stack should be deployed.

        Raises:
            NotImplementedError: Stack deployments are not supported by the
                local ZenML deployment.
        """
        raise NotImplementedError(
            "Stack deployments are not supported by local ZenML deployments."
        )

    def get_stack_deployment_stack(
        self,
        provider: StackDeploymentProvider,
        stack_name: str,
        location: Optional[str] = None,
        date_start: Optional[datetime] = None,
    ) -> Optional[DeployedStack]:
        """Return a matching ZenML stack that was deployed and registered.

        Args:
            provider: The stack deployment provider.
            stack_name: The name of the stack.
            location: The location where the stack should be deployed.
            date_start: The date when the deployment started.

        Raises:
            NotImplementedError: Stack deployments are not supported by the
                local ZenML deployment.
        """
        raise NotImplementedError(
            "Stack deployments are not supported by local ZenML deployments."
        )

    # ----------------------------- Step runs -----------------------------

    def create_run_step(self, step_run: StepRunRequest) -> StepRunResponse:
        """Creates a step run.

        Args:
            step_run: The step run to create.

        Returns:
            The created step run.

        Raises:
            EntityExistsError: if the step run already exists.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=step_run, session=session)

            # Check if the pipeline run exists
            run = self._get_reference_schema_by_id(
                resource=step_run,
                reference_schema=PipelineRunSchema,
                reference_id=step_run.pipeline_run_id,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=step_run,
                reference_schema=StepRunSchema,
                reference_id=step_run.original_step_run_id,
                session=session,
                reference_type="original step run",
            )

            step_schema = StepRunSchema.from_request(
                step_run, deployment_id=run.deployment_id
            )
            session.add(step_schema)
            try:
                session.commit()
            except IntegrityError:
                # We have to rollback the failed session first in order
                # to continue using it
                session.rollback()
                raise EntityExistsError(
                    f"Unable to create step `{step_run.name}`: A step with "
                    f"this name already exists in the pipeline run with ID "
                    f"'{step_run.pipeline_run_id}'."
                )

            # Add logs entry for the step if exists
            if step_run.logs is not None:
                self._get_reference_schema_by_id(
                    resource=step_run,
                    reference_schema=StackComponentSchema,
                    reference_id=step_run.logs.artifact_store_id,
                    session=session,
                    reference_type="logs artifact store",
                )

                log_entry = LogsSchema(
                    uri=step_run.logs.uri,
                    step_run_id=step_schema.id,
                    artifact_store_id=step_run.logs.artifact_store_id,
                )
                session.add(log_entry)

            # If cached, attach metadata of the original step
            if (
                step_run.status == ExecutionStatus.CACHED
                and step_run.original_step_run_id is not None
            ):
                original_metadata_links = session.exec(
                    select(RunMetadataResourceSchema)
                    .where(
                        RunMetadataResourceSchema.run_metadata_id
                        == RunMetadataSchema.id
                    )
                    .where(
                        RunMetadataResourceSchema.resource_id
                        == step_run.original_step_run_id
                    )
                    .where(
                        RunMetadataResourceSchema.resource_type
                        == MetadataResourceTypes.STEP_RUN
                    )
                    .where(
                        RunMetadataSchema.publisher_step_id
                        == step_run.original_step_run_id
                    )
                ).all()

                # Create new links in a batch
                new_links = [
                    RunMetadataResourceSchema(
                        resource_id=step_schema.id,
                        resource_type=link.resource_type,
                        run_metadata_id=link.run_metadata_id,
                    )
                    for link in original_metadata_links
                ]
                # Add all new links in a single operation
                session.add_all(new_links)
                # Commit the changes
                session.commit()
                session.refresh(step_schema)

            # Save parent step IDs into the database.
            for parent_step_id in step_run.parent_step_ids:
                self._set_run_step_parent_step(
                    child_step_run=step_schema,
                    parent_id=parent_step_id,
                    session=session,
                )

            session.commit()
            session.refresh(step_schema)

            step_model = step_schema.to_model(include_metadata=True)

            # Save input artifact IDs into the database.
            for input_name, artifact_version_ids in step_run.inputs.items():
                for artifact_version_id in artifact_version_ids:
                    if step_run.original_step_run_id:
                        # This is a cached step run, for which the input
                        # artifacts might include manually loaded artifacts
                        # which can not be inferred from the step config. In
                        # this case, we check the input type of the artifact
                        # for the original step run.
                        input_type = self._get_step_run_input_type_from_cached_step_run(
                            input_name=input_name,
                            artifact_version_id=artifact_version_id,
                            cached_step_run_id=step_run.original_step_run_id,
                            session=session,
                        )
                    else:
                        # This is a non-cached step run, which means all input
                        # artifacts we receive at creation time are inputs that
                        # are defined in the step config.
                        input_type = self._get_step_run_input_type_from_config(
                            input_name=input_name,
                            step_config=step_model.config,
                            step_spec=step_model.spec,
                        )
                    self._set_run_step_input_artifact(
                        step_run=step_schema,
                        artifact_version_id=artifact_version_id,
                        name=input_name,
                        input_type=input_type,
                        session=session,
                    )

            # Save output artifact IDs into the database.
            for name, artifact_version_ids in step_run.outputs.items():
                for artifact_version_id in artifact_version_ids:
                    self._set_run_step_output_artifact(
                        step_run=step_schema,
                        artifact_version_id=artifact_version_id,
                        name=name,
                        session=session,
                    )

            if step_run.status != ExecutionStatus.RUNNING:
                self._update_pipeline_run_status(
                    pipeline_run_id=step_run.pipeline_run_id, session=session
                )

            session.commit()
            session.refresh(step_schema)

            if model_version_id := self._get_or_create_model_version_for_run(
                step_schema
            ):
                step_schema.model_version_id = model_version_id
                session.add(step_schema)
                session.commit()

                self.create_model_version_pipeline_run_link(
                    ModelVersionPipelineRunRequest(
                        model_version=model_version_id,
                        pipeline_run=step_schema.pipeline_run_id,
                    )
                )
                session.refresh(step_schema)

            return step_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def get_run_step(
        self, step_run_id: UUID, hydrate: bool = True
    ) -> StepRunResponse:
        """Get a step run by ID.

        Args:
            step_run_id: The ID of the step run to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The step run.
        """
        with Session(self.engine) as session:
            step_run = self._get_schema_by_id(
                resource_id=step_run_id,
                schema_class=StepRunSchema,
                session=session,
                query_options=StepRunSchema.get_query_options(
                    include_metadata=hydrate, include_resources=True
                ),
            )
            return step_run.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_run_steps(
        self,
        step_run_filter_model: StepRunFilter,
        hydrate: bool = False,
    ) -> Page[StepRunResponse]:
        """List all step runs matching the given filter criteria.

        Args:
            step_run_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all step runs matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=step_run_filter_model,
                session=session,
            )
            query = select(StepRunSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=StepRunSchema,
                filter_model=step_run_filter_model,
                hydrate=hydrate,
                apply_query_options_from_schema=True,
            )

    def update_run_step(
        self,
        step_run_id: UUID,
        step_run_update: StepRunUpdate,
    ) -> StepRunResponse:
        """Updates a step run.

        Args:
            step_run_id: The ID of the step to update.
            step_run_update: The update to be applied to the step.

        Returns:
            The updated step run.
        """
        with Session(self.engine) as session:
            # Check if the step exists
            existing_step_run = self._get_schema_by_id(
                resource_id=step_run_id,
                schema_class=StepRunSchema,
                session=session,
            )

            # Update the step
            existing_step_run.update(step_run_update)
            session.add(existing_step_run)

            # Update the artifacts.
            for name, artifact_version_ids in step_run_update.outputs.items():
                for artifact_version_id in artifact_version_ids:
                    self._set_run_step_output_artifact(
                        step_run=existing_step_run,
                        artifact_version_id=artifact_version_id,
                        name=name,
                        session=session,
                    )

            # Update loaded artifacts.
            for (
                artifact_name,
                artifact_version_id,
            ) in step_run_update.loaded_artifact_versions.items():
                self._set_run_step_input_artifact(
                    step_run=existing_step_run,
                    artifact_version_id=artifact_version_id,
                    name=artifact_name,
                    input_type=StepRunInputArtifactType.MANUAL,
                    session=session,
                )

            self._update_pipeline_run_status(
                pipeline_run_id=existing_step_run.pipeline_run_id,
                session=session,
            )

            session.commit()
            session.refresh(existing_step_run)

            return existing_step_run.to_model(
                include_metadata=True, include_resources=True
            )

    def _get_step_run_input_type_from_cached_step_run(
        self,
        input_name: str,
        artifact_version_id: UUID,
        cached_step_run_id: UUID,
        session: Session,
    ) -> StepRunInputArtifactType:
        """Get the input type of an artifact from a cached step run.

        Args:
            input_name: The name of the input artifact.
            artifact_version_id: The ID of the artifact version.
            cached_step_run_id: The ID of the cached step run.
            session: The database session to use.

        Raises:
            RuntimeError: If no input artifact is found for the given input
                name and artifact version ID.

        Returns:
            The input type of the artifact.
        """
        query = (
            select(StepRunInputArtifactSchema.type)
            .where(StepRunInputArtifactSchema.name == input_name)
            .where(
                StepRunInputArtifactSchema.artifact_id == artifact_version_id
            )
            .where(StepRunInputArtifactSchema.step_id == cached_step_run_id)
        )
        result = session.exec(query).first()
        if result is None:
            raise RuntimeError(
                f"No input artifact found for input name `{input_name}`, "
                f"artifact version `{artifact_version_id}` and step run "
                f"`{cached_step_run_id}`."
            )
        return StepRunInputArtifactType(result)

    def _get_step_run_input_type_from_config(
        self,
        input_name: str,
        step_config: StepConfiguration,
        step_spec: StepSpec,
    ) -> StepRunInputArtifactType:
        """Get the input type of an artifact.

        Args:
            input_name: The name of the input artifact.
            step_config: The step config.
            step_spec: The step spec.

        Returns:
            The input type of the artifact.
        """
        if input_name in step_spec.inputs:
            return StepRunInputArtifactType.STEP_OUTPUT
        if input_name in step_config.external_input_artifacts:
            return StepRunInputArtifactType.EXTERNAL
        elif (
            input_name in step_config.model_artifacts_or_metadata
            or input_name in step_config.client_lazy_loaders
        ):
            return StepRunInputArtifactType.LAZY_LOADED
        else:
            return StepRunInputArtifactType.MANUAL

    def _set_run_step_parent_step(
        self, child_step_run: StepRunSchema, parent_id: UUID, session: Session
    ) -> None:
        """Sets the parent step run for a step run.

        Args:
            child_step_run: The child step run to set the parent for.
            parent_id: The ID of the parent step run to set a child for.
            session: The database session to use.
        """
        parent_step_run = self._get_reference_schema_by_id(
            resource=child_step_run,
            reference_schema=StepRunSchema,
            reference_id=parent_id,
            session=session,
            reference_type="parent step",
        )

        # Check if the parent step is already set.
        assignment = session.exec(
            select(StepRunParentsSchema)
            .where(StepRunParentsSchema.child_id == child_step_run.id)
            .where(StepRunParentsSchema.parent_id == parent_step_run.id)
        ).first()
        if assignment is not None:
            return

        # Save the parent step assignment in the database.
        assignment = StepRunParentsSchema(
            child_id=child_step_run.id, parent_id=parent_step_run.id
        )
        session.add(assignment)

    def _set_run_step_input_artifact(
        self,
        step_run: StepRunSchema,
        artifact_version_id: UUID,
        name: str,
        input_type: StepRunInputArtifactType,
        session: Session,
    ) -> None:
        """Sets an artifact as an input of a step run.

        Args:
            step_run: The step run.
            artifact_version_id: The ID of the artifact.
            name: The name of the input in the step run.
            input_type: In which way the artifact was loaded in the step.
            session: The database session to use.
        """
        # Check if the artifact exists.
        self._get_reference_schema_by_id(
            resource=step_run,
            reference_schema=ArtifactVersionSchema,
            reference_id=artifact_version_id,
            session=session,
            reference_type="input artifact",
        )

        # Check if the input is already set.
        assignment = session.exec(
            select(StepRunInputArtifactSchema)
            .where(StepRunInputArtifactSchema.step_id == step_run.id)
            .where(
                StepRunInputArtifactSchema.artifact_id == artifact_version_id
            )
            .where(StepRunInputArtifactSchema.name == name)
        ).first()
        if assignment is not None:
            return

        # Save the input assignment in the database.
        assignment = StepRunInputArtifactSchema(
            step_id=step_run.id,
            artifact_id=artifact_version_id,
            name=name,
            type=input_type.value,
        )
        session.add(assignment)

    def _set_run_step_output_artifact(
        self,
        step_run: StepRunSchema,
        artifact_version_id: UUID,
        name: str,
        session: Session,
    ) -> None:
        """Sets an artifact as an output of a step run.

        Args:
            step_run: The step run.
            artifact_version_id: The ID of the artifact version.
            name: The name of the output in the step run.
            session: The database session to use.
        """
        # Check if the artifact exists.
        self._get_reference_schema_by_id(
            resource=step_run,
            reference_schema=ArtifactVersionSchema,
            reference_id=artifact_version_id,
            session=session,
            reference_type="output artifact",
        )

        # Check if the output is already set.
        assignment = session.exec(
            select(StepRunOutputArtifactSchema)
            .where(StepRunOutputArtifactSchema.step_id == step_run.id)
            .where(
                StepRunOutputArtifactSchema.artifact_id == artifact_version_id
            )
        ).first()
        if assignment is not None:
            return

        # Save the output assignment in the database.
        assignment = StepRunOutputArtifactSchema(
            step_id=step_run.id,
            artifact_id=artifact_version_id,
            name=name,
        )
        session.add(assignment)

    def _update_pipeline_run_status(
        self,
        pipeline_run_id: UUID,
        session: Session,
    ) -> None:
        """Updates the status of a pipeline run.

        Args:
            pipeline_run_id: The ID of the pipeline run to update.
            session: The database session to use.
        """
        from zenml.orchestrators.publish_utils import get_pipeline_run_status

        pipeline_run = session.exec(
            select(PipelineRunSchema)
            .options(
                joinedload(
                    jl_arg(PipelineRunSchema.deployment), innerjoin=True
                )
            )
            .where(PipelineRunSchema.id == pipeline_run_id)
        ).one()
        step_run_statuses = session.exec(
            select(StepRunSchema.status).where(
                StepRunSchema.pipeline_run_id == pipeline_run_id
            )
        ).all()

        # Deployment always exists for pipeline runs of newer versions
        assert pipeline_run.deployment
        num_steps = len(
            json.loads(pipeline_run.deployment.step_configurations)
        )
        new_status = get_pipeline_run_status(
            step_statuses=[
                ExecutionStatus(status) for status in step_run_statuses
            ],
            num_steps=num_steps,
        )

        if pipeline_run.is_placeholder_run() and not new_status.is_finished:
            # If the pipeline run is a placeholder run, no step has been started
            # for the run yet. This means the orchestrator hasn't started
            # running yet, and this method is most likely being called as
            # part of the creation of some cached steps. In this case, we don't
            # update the status unless the run is finished.
            return

        if new_status != pipeline_run.status:
            run_update = PipelineRunUpdate(status=new_status)
            if new_status in {
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
            }:
                run_update.end_time = utc_now()
                if pipeline_run.start_time and isinstance(
                    pipeline_run.start_time, datetime
                ):
                    duration_time = (
                        run_update.end_time - pipeline_run.start_time
                    )
                    duration_seconds = duration_time.total_seconds()
                    start_time_str = pipeline_run.start_time.strftime(
                        "%Y-%m-%dT%H:%M:%S.%fZ"
                    )
                else:
                    start_time_str = None
                    duration_seconds = None

                stack = pipeline_run.deployment.stack
                assert stack
                stack_metadata = {
                    str(component.type): component.flavor
                    for component in stack.components
                }
                with track_handler(
                    AnalyticsEvent.RUN_PIPELINE_ENDED
                ) as analytics_handler:
                    analytics_handler.metadata = {
                        "project_id": pipeline_run.project_id,
                        "pipeline_run_id": pipeline_run_id,
                        "template_id": pipeline_run.deployment.template_id,
                        "status": new_status,
                        "num_steps": num_steps,
                        "start_time": start_time_str,
                        "end_time": run_update.end_time.strftime(
                            "%Y-%m-%dT%H:%M:%S.%fZ"
                        ),
                        "duration_seconds": duration_seconds,
                        **stack_metadata,
                    }

                completed_onboarding_steps: Set[str] = {
                    OnboardingStep.PIPELINE_RUN,
                    OnboardingStep.STARTER_SETUP_COMPLETED,
                }
                if stack_metadata["orchestrator"] not in {
                    "local",
                    "local_docker",
                }:
                    completed_onboarding_steps.update(
                        {
                            OnboardingStep.PIPELINE_RUN_WITH_REMOTE_ORCHESTRATOR,
                        }
                    )
                if stack_metadata["artifact_store"] != "local":
                    completed_onboarding_steps.update(
                        {
                            OnboardingStep.PIPELINE_RUN_WITH_REMOTE_ARTIFACT_STORE,
                            OnboardingStep.PRODUCTION_SETUP_COMPLETED,
                        }
                    )
                if OnboardingStep.THIRD_PIPELINE_RUN not in (
                    self._cached_onboarding_state or {}
                ):
                    onboarding_state = self.get_onboarding_state()
                    if OnboardingStep.PIPELINE_RUN in onboarding_state:
                        completed_onboarding_steps.add(
                            OnboardingStep.SECOND_PIPELINE_RUN
                        )
                    if OnboardingStep.SECOND_PIPELINE_RUN in onboarding_state:
                        completed_onboarding_steps.add(
                            OnboardingStep.THIRD_PIPELINE_RUN
                        )

                self._update_onboarding_state(
                    completed_steps=completed_onboarding_steps, session=session
                )
            pipeline_run.update(run_update)
            session.add(pipeline_run)

    # --------------------------- Triggers ---------------------------

    @track_decorator(AnalyticsEvent.CREATED_TRIGGER)
    def create_trigger(self, trigger: TriggerRequest) -> TriggerResponse:
        """Creates a new trigger.

        Args:
            trigger: Trigger to be created.

        Returns:
            The newly created trigger.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=trigger, session=session)

            # Verify that the trigger name is unique
            self._verify_name_uniqueness(
                resource=trigger,
                schema=TriggerSchema,
                session=session,
            )

            # Verify that the given action exists
            self._get_reference_schema_by_id(
                resource=trigger,
                reference_schema=ActionSchema,
                reference_id=trigger.action_id,
                session=session,
            )

            self._get_reference_schema_by_id(
                resource=trigger,
                reference_schema=EventSourceSchema,
                reference_id=trigger.event_source_id,
                session=session,
            )

            new_trigger = TriggerSchema.from_request(trigger)
            session.add(new_trigger)
            session.commit()
            session.refresh(new_trigger)

            return new_trigger.to_model(
                include_metadata=True, include_resources=True
            )

    def get_trigger(
        self, trigger_id: UUID, hydrate: bool = True
    ) -> TriggerResponse:
        """Get a trigger by its unique ID.

        Args:
            trigger_id: The ID of the trigger to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The trigger with the given ID.
        """
        with Session(self.engine) as session:
            trigger = self._get_schema_by_id(
                resource_id=trigger_id,
                schema_class=TriggerSchema,
                session=session,
            )
            return trigger.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_triggers(
        self,
        trigger_filter_model: TriggerFilter,
        hydrate: bool = False,
    ) -> Page[TriggerResponse]:
        """List all trigger matching the given filter criteria.

        Args:
            trigger_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all triggers matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=trigger_filter_model,
                session=session,
            )
            query = select(TriggerSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=TriggerSchema,
                filter_model=trigger_filter_model,
                hydrate=hydrate,
            )

    @track_decorator(AnalyticsEvent.UPDATED_TRIGGER)
    def update_trigger(
        self, trigger_id: UUID, trigger_update: TriggerUpdate
    ) -> TriggerResponse:
        """Update a trigger.

        Args:
            trigger_id: The ID of the trigger update.
            trigger_update: The update request on the trigger.

        Returns:
            The updated trigger.

        Raises:
            ValueError: If both a schedule and an event source are provided.
        """
        with Session(self.engine) as session:
            # Check if trigger with the domain key (name, project, owner)
            # already exists
            existing_trigger = self._get_schema_by_id(
                resource_id=trigger_id,
                schema_class=TriggerSchema,
                session=session,
            )

            # Verify that either a schedule or an event source is provided, not
            # both
            if existing_trigger.event_source and trigger_update.schedule:
                raise ValueError(
                    "Unable to update trigger: A trigger cannot have both a "
                    "schedule and an event source."
                )

            # In case of a renaming update, make sure no trigger already exists
            # with that name
            self._verify_name_uniqueness(
                resource=trigger_update,
                schema=existing_trigger,
                session=session,
            )

            existing_trigger.update(
                trigger_update=trigger_update,
            )

            session.add(existing_trigger)
            session.commit()
            session.refresh(existing_trigger)

            return existing_trigger.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_trigger(self, trigger_id: UUID) -> None:
        """Delete a trigger.

        Args:
            trigger_id: The ID of the trigger to delete.
        """
        with Session(self.engine) as session:
            trigger = self._get_schema_by_id(
                resource_id=trigger_id,
                schema_class=TriggerSchema,
                session=session,
            )
            session.delete(trigger)
            session.commit()

    # -------------------- Trigger Executions --------------------

    def create_trigger_execution(
        self, trigger_execution: TriggerExecutionRequest
    ) -> TriggerExecutionResponse:
        """Create a trigger execution.

        Args:
            trigger_execution: The trigger execution to create.

        Returns:
            The created trigger execution.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=trigger_execution, session=session
            )
            self._get_reference_schema_by_id(
                resource=trigger_execution,
                reference_schema=TriggerSchema,
                reference_id=trigger_execution.trigger,
                session=session,
            )
            new_execution = TriggerExecutionSchema.from_request(
                trigger_execution
            )
            session.add(new_execution)
            session.commit()
            session.refresh(new_execution)

            return new_execution.to_model(
                include_metadata=True, include_resources=True
            )

    def get_trigger_execution(
        self,
        trigger_execution_id: UUID,
        hydrate: bool = True,
    ) -> TriggerExecutionResponse:
        """Get an trigger execution by ID.

        Args:
            trigger_execution_id: The ID of the trigger execution to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The trigger execution.
        """
        with Session(self.engine) as session:
            execution = self._get_schema_by_id(
                resource_id=trigger_execution_id,
                schema_class=TriggerExecutionSchema,
                session=session,
            )
            return execution.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_trigger_executions(
        self,
        trigger_execution_filter_model: TriggerExecutionFilter,
        hydrate: bool = False,
    ) -> Page[TriggerExecutionResponse]:
        """List all trigger executions matching the given filter criteria.

        Args:
            trigger_execution_filter_model: All filter parameters including
                pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all trigger executions matching the filter criteria.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=trigger_execution_filter_model,
                session=session,
            )
            query = select(TriggerExecutionSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=TriggerExecutionSchema,
                filter_model=trigger_execution_filter_model,
                hydrate=hydrate,
            )

    def delete_trigger_execution(self, trigger_execution_id: UUID) -> None:
        """Delete a trigger execution.

        Args:
            trigger_execution_id: The ID of the trigger execution to delete.
        """
        with Session(self.engine) as session:
            execution = self._get_schema_by_id(
                resource_id=trigger_execution_id,
                schema_class=TriggerExecutionSchema,
                session=session,
            )

            session.delete(execution)
            session.commit()

    # ----------------------------- Users -----------------------------

    @classmethod
    @lru_cache(maxsize=1)
    def _get_resource_references(
        cls,
    ) -> List[Tuple[Type[SQLModel], str]]:
        """Get a list of all other table columns that reference the user table.

        Given that this list doesn't change at runtime, we cache it.

        Returns:
            A list of all other table columns that reference the user table
            as a list of tuples of the form
            (<sqlmodel-schema-class>, <attribute-name>).
        """
        from zenml.zen_stores import schemas as zenml_schemas

        # Get a list of attributes that represent relationships to other
        # resources
        resource_attrs = [
            attr
            for attr in UserSchema.__sqlmodel_relationships__.keys()
            if not attr.startswith("_")
            and attr
            not in
            # These are not resources owned by the user or  are resources that
            # are deleted automatically when the user is deleted.
            ["api_keys", "auth_devices"]
        ]

        # This next part is crucial in preserving scalability: we don't fetch
        # the values of the relationship attributes, because this would
        # potentially load a huge amount of data into memory through
        # lazy-loading. Instead, we use a DB query to count resources
        # associated with the user for each individual resource attribute.

        # To create this query, we need a list of all tables and their foreign
        # keys that point to the user table.
        foreign_keys: List[Tuple[Type[SQLModel], str]] = []
        for resource_attr in resource_attrs:
            # Extract the target schema from the annotation
            annotation = UserSchema.__annotations__[resource_attr]
            if get_origin(annotation) == Mapped:
                annotation = annotation.__args__[0]

            # The annotation must be of the form
            # `typing.List[ForwardRef('<schema-class>')]`
            # We need to recover the schema class from the ForwardRef
            assert annotation._name == "List"
            assert annotation.__args__
            schema_ref = annotation.__args__[0]
            assert isinstance(schema_ref, ForwardRef)
            # We pass the zenml_schemas module as the globals dict to
            # _evaluate, because this is where the schema classes are
            # defined
            if sys.version_info >= (3, 12, 4):
                target_schema = schema_ref._evaluate(
                    vars(zenml_schemas), {}, recursive_guard=frozenset()
                )
            else:
                target_schema = schema_ref._evaluate(
                    vars(zenml_schemas), {}, frozenset()
                )
            assert target_schema is not None
            assert issubclass(target_schema, SQLModel)

            # Next, we need to identify the foreign key attribute in the
            # target table
            table = UserSchema.metadata.tables[target_schema.__tablename__]
            foreign_key_attr = None
            for fk in table.foreign_keys:
                if fk.column.table.name != UserSchema.__tablename__:
                    continue
                if fk.column.name != "id":
                    continue
                assert fk.parent is not None
                foreign_key_attr = fk.parent.name
                break

            assert foreign_key_attr is not None

            foreign_keys.append((target_schema, foreign_key_attr))

        return foreign_keys

    def _account_owns_resources(
        self, account: UserSchema, session: Session
    ) -> bool:
        """Check if the account owns any resources.

        Args:
            account: The account to check.
            session: The database session to use for the query.

        Returns:
            Whether the account owns any resources.
        """
        # Get a list of all other table columns that reference the user table
        resource_attrs = self._get_resource_references()
        for schema, resource_attr in resource_attrs:
            # Check if the user owns any resources of this type
            count = (
                session.query(func.count())
                .select_from(schema)
                .where(getattr(schema, resource_attr) == account.id)
                .scalar()
            )

            if count > 0:
                logger.debug(
                    f"User {account.name} owns {count} resources of type "
                    f"{schema.__tablename__}"
                )
                return True

        return False

    def _get_default_user(self, session: Session) -> UserResponse:
        """Get the default user.

        Args:
            session: The database session to use for the query.

        Returns:
            The default user schema.
        """
        if self._default_user is None:
            default_username = os.getenv(
                ENV_ZENML_DEFAULT_USER_NAME, DEFAULT_USERNAME
            )

            self._default_user = self._get_account_schema(
                account_name_or_id=default_username,
                session=session,
                service_account=False,
            ).to_model(include_metadata=True, include_resources=True)

        return self._default_user

    def _get_active_user(
        self,
        session: Session,
    ) -> UserResponse:
        """Get the active user.

        Depending on context, this is:

        - the user that is currently authenticated, when running in the ZenML
        server
        - the default admin user, when running in the ZenML client connected
        directly to a database

        Args:
            session: The DB session to use to use for queries.

        Returns:
            The active user.

        Raises:
            RuntimeError: If no active user is found.
        """
        if handle_bool_env_var(ENV_ZENML_SERVER):
            # Running inside server
            from zenml.zen_server.auth import get_auth_context

            # If the code is running on the server, use the auth context.
            auth_context = get_auth_context()
            if auth_context is None:
                raise RuntimeError("No active user found.")

            user = auth_context.user
        else:
            user = self._get_default_user(session)

        return user

    def create_user(self, user: UserRequest) -> UserResponse:
        """Creates a new user.

        Args:
            user: User to be created.

        Returns:
            The newly created user.

        Raises:
            EntityExistsError: If a user or service account with the given name
                already exists.
        """
        with Session(self.engine) as session:
            # Check if a user account with the given name already exists
            err_msg = (
                f"Unable to create user with name '{user.name}': "
                f"Found an existing user account with this name."
            )
            try:
                self._get_account_schema(
                    user.name,
                    session=session,
                    # Filter out service accounts
                    service_account=False,
                )
                raise EntityExistsError(err_msg)
            except KeyError:
                pass

            # Create the user
            new_user = UserSchema.from_user_request(user)
            session.add(new_user)
            # on commit an IntegrityError may arise we let it bubble up
            session.commit()

            server_info = self.get_store_info()
            with AnalyticsContext() as context:
                context.user_id = new_user.id

                context.group(
                    group_id=server_info.id,
                    traits={
                        "server_id": server_info.id,
                        "version": server_info.version,
                        "deployment_type": str(server_info.deployment_type),
                        "database_type": str(server_info.database_type),
                    },
                )

            return new_user.to_model(
                include_metadata=True, include_resources=True
            )

    def get_user(
        self,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        include_private: bool = False,
        hydrate: bool = True,
    ) -> UserResponse:
        """Gets a specific user, when no id is specified the active user is returned.

        # noqa: DAR401
        # noqa: DAR402

        Raises a KeyError in case a user with that name or id does not exist.

        For backwards-compatibility reasons, this method can also be called
        to fetch service accounts by their ID.

        Args:
            user_name_or_id: The name or ID of the user to get.
            include_private: Whether to include private user information
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If the user does not exist.
        """
        with Session(self.engine) as session:
            if user_name_or_id is None:
                user_name_or_id = self._get_active_user(session=session).id

            # If a UUID is passed, we also allow fetching service accounts
            # with that ID.
            service_account: Optional[bool] = False
            if uuid_utils.is_valid_uuid(user_name_or_id):
                service_account = None
            user = self._get_account_schema(
                user_name_or_id,
                session=session,
                service_account=service_account,
            )

            return user.to_model(
                include_private=include_private,
                include_metadata=hydrate,
                include_resources=True,
            )

    def get_auth_user(
        self, user_name_or_id: Union[str, UUID]
    ) -> UserAuthModel:
        """Gets the auth model to a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The requested user, if it was found.
        """
        with Session(self.engine) as session:
            user = self._get_account_schema(
                user_name_or_id, session=session, service_account=False
            )
            return UserAuthModel(
                id=user.id,
                name=user.name,
                full_name=user.full_name,
                email_opted_in=user.email_opted_in,
                active=user.active,
                created=user.created,
                updated=user.updated,
                password=user.password,
                activation_token=user.activation_token,
                is_service_account=False,
            )

    def list_users(
        self,
        user_filter_model: UserFilter,
        hydrate: bool = False,
    ) -> Page[UserResponse]:
        """List all users.

        Args:
            user_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all users.
        """
        with Session(self.engine) as session:
            query = select(UserSchema)
            paged_user: Page[UserResponse] = self.filter_and_paginate(
                session=session,
                query=query,
                table=UserSchema,
                filter_model=user_filter_model,
                hydrate=hydrate,
            )
            return paged_user

    def update_user(
        self, user_id: UUID, user_update: UserUpdate
    ) -> UserResponse:
        """Updates an existing user.

        Args:
            user_id: The id of the user to update.
            user_update: The update to be applied to the user.

        Returns:
            The updated user.

        Raises:
            IllegalOperationError: If the request tries to update the username
                for the default user account.
            EntityExistsError: If the request tries to update the username to
                a name that is already taken by another user or service account.
        """
        with Session(self.engine) as session:
            existing_user = self._get_account_schema(
                user_id, session=session, service_account=False
            )

            if (
                existing_user.is_admin is True
                and user_update.is_admin is False
            ):
                # There must be at least one admin account configured
                admin_accounts_count = session.scalar(
                    select(func.count(UserSchema.id)).where(  # type: ignore[arg-type]
                        UserSchema.is_admin == True  # noqa: E712
                    )
                )
                if admin_accounts_count == 1:
                    raise IllegalOperationError(
                        "There has to be at least one admin account configured "
                        "on your system at all times. This is the only admin "
                        "account and therefore it cannot be demoted to a "
                        "regular user account."
                    )

            if (
                user_update.name is not None
                and user_update.name != existing_user.name
            ):
                try:
                    self._get_account_schema(
                        user_update.name,
                        session=session,
                        service_account=False,
                    )
                    raise EntityExistsError(
                        f"Unable to update user account with name "
                        f"'{user_update.name}': Found an existing user "
                        "account with this name."
                    )
                except KeyError:
                    pass

            user_model = existing_user.to_model(include_metadata=True)
            survey_finished_before = (
                FINISHED_ONBOARDING_SURVEY_KEY in user_model.user_metadata
            )

            existing_user.update_user(user_update=user_update)
            session.add(existing_user)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_user)
            updated_user = existing_user.to_model(
                include_metadata=True, include_resources=True
            )

            survey_finished_after = (
                FINISHED_ONBOARDING_SURVEY_KEY in updated_user.user_metadata
            )

            if not survey_finished_before and survey_finished_after:
                analytics_metadata = {
                    **updated_user.user_metadata,
                    # We need to get the email from the DB model as it is not
                    # included in the model that's returned from this method
                    "email": existing_user.email,
                    "newsletter": existing_user.email_opted_in,
                    "name": updated_user.name,
                    "full_name": updated_user.full_name,
                }
                with AnalyticsContext() as context:
                    # This method can be called from the `/users/activate`
                    # endpoint in which the auth context is not set
                    # -> We need to manually set the user ID in that case,
                    # otherwise the event will not be sent
                    if context.user_id is None:
                        context.user_id = updated_user.id

                    context.track(
                        event=AnalyticsEvent.USER_ENRICHED,
                        properties=analytics_metadata,
                    )

            return updated_user

    def delete_user(self, user_name_or_id: Union[str, UUID]) -> None:
        """Deletes a user.

        Args:
            user_name_or_id: The name or the ID of the user to delete.

        Raises:
            IllegalOperationError: If the user is the default user account or
                if the user already owns resources.
        """
        with Session(self.engine) as session:
            user = self._get_account_schema(
                user_name_or_id, session=session, service_account=False
            )
            if user.is_admin:
                # Don't allow the last admin to be deleted
                admin_accounts_count = session.scalar(
                    select(func.count(UserSchema.id)).where(  # type: ignore[arg-type]
                        UserSchema.is_admin == True  # noqa: E712
                    )
                )
                if admin_accounts_count == 1:
                    raise IllegalOperationError(
                        "There has to be at least one admin account configured "
                        "on your system. This is the only admin account and "
                        "therefore it cannot be deleted."
                    )
            if self._account_owns_resources(user, session=session):
                raise IllegalOperationError(
                    "The user account has already been used to create "
                    "other resources that it now owns and therefore cannot be "
                    "deleted. Please delete all resources owned by the user "
                    "account or consider deactivating it instead."
                )

            session.delete(user)
            session.commit()

    def _create_default_user_on_db_init(self) -> bool:
        """Check if the default user should be created on database initialization.

        We create a default admin user account with an empty password when the
        database is initialized in the following cases:

        * local ZenML client deployments: the client is not connected to a ZenML
        server, but uses the database directly.
        * server deployments that set the `auto_activate` server
        setting explicitly to `True`. This includes:
            * local ZenML server deployments: the server is deployed locally
            with `zenml login --local`
            * local ZenML docker deployments: the server is deployed locally
            with `zenml login --local --docker`

        For all other cases, or if the external authentication scheme is used,
        no default admin user is created. The user must activate the server and
        create a default admin user account the first time they visit the
        dashboard.

        Returns:
            Whether the default user should be created on database
            initialization.
        """
        if handle_bool_env_var(ENV_ZENML_SERVER):
            # Running inside server
            from zenml.zen_server.utils import server_config

            config = server_config()

            if config.auth_scheme == AuthScheme.EXTERNAL:
                # Running inside server with external auth
                return False

            if config.auto_activate:
                return True

        else:
            # Running inside client
            return True

        return False

    def _activate_server_at_initialization(self) -> bool:
        """Check if the server should be activated on database initialization.

        We activate the server when the database is initialized in the following
        cases:

        * all the cases in which the default user account is also automatically
        created on initialization (see `_create_default_user_on_db_init`)
        * when the authentication scheme is set to external

        Returns:
            Whether the server should be activated on database initialization.
        """
        if self._create_default_user_on_db_init():
            return True

        if handle_bool_env_var(ENV_ZENML_SERVER):
            # Running inside server
            from zenml.zen_server.utils import server_config

            config = server_config()

            if config.auth_scheme == AuthScheme.EXTERNAL:
                return True

        return False

    # ----------------------------- Projects -----------------------------

    @track_decorator(AnalyticsEvent.CREATED_PROJECT)
    def create_project(self, project: ProjectRequest) -> ProjectResponse:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.
        """
        with Session(self.engine) as session:
            # Check if project with the given name already exists
            self._verify_name_uniqueness(
                resource=project,
                schema=ProjectSchema,
                session=session,
            )

            # Create the project
            new_project = ProjectSchema.from_request(project)
            session.add(new_project)
            session.commit()

            # Explicitly refresh the new_project schema
            session.refresh(new_project)

            project_model = new_project.to_model(
                include_metadata=True, include_resources=True
            )

            self._update_onboarding_state(
                completed_steps={OnboardingStep.PROJECT_CREATED},
                session=session,
            )

        return project_model

    def get_project(
        self, project_name_or_id: Union[str, UUID], hydrate: bool = True
    ) -> ProjectResponse:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested project if one was found.
        """
        with Session(self.engine) as session:
            project = self._get_schema_by_name_or_id(
                object_name_or_id=project_name_or_id,
                schema_class=ProjectSchema,
                session=session,
            )
        return project.to_model(
            include_metadata=hydrate, include_resources=True
        )

    def list_projects(
        self,
        project_filter_model: ProjectFilter,
        hydrate: bool = False,
    ) -> Page[ProjectResponse]:
        """List all projects matching the given filter criteria.

        Args:
            project_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all projects matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(ProjectSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ProjectSchema,
                filter_model=project_filter_model,
                hydrate=hydrate,
            )

    def update_project(
        self, project_id: UUID, project_update: ProjectUpdate
    ) -> ProjectResponse:
        """Update an existing project.

        Args:
            project_id: The ID of the project to be updated.
            project_update: The update to be applied to the project.

        Returns:
            The updated project.

        Raises:
            IllegalOperationError: If the request tries to update the name of
                the default project.
        """
        with Session(self.engine) as session:
            existing_project = self._get_schema_by_id(
                resource_id=project_id,
                schema_class=ProjectSchema,
                session=session,
            )
            if (
                self._default_project_enabled
                and existing_project.name == self._default_project_name
                and "name" in project_update.model_fields_set
                and project_update.name != existing_project.name
            ):
                raise IllegalOperationError(
                    "The name of the default project cannot be changed."
                )

            self._verify_name_uniqueness(
                resource=project_update,
                schema=existing_project,
                session=session,
            )

            # Update the project
            existing_project.update(project_update=project_update)
            session.add(existing_project)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_project)
            return existing_project.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_project(self, project_name_or_id: Union[str, UUID]) -> None:
        """Deletes a project.

        Args:
            project_name_or_id: Name or ID of the project to delete.

        Raises:
            IllegalOperationError: If the project is the default project.
        """
        with Session(self.engine) as session:
            # Check if project with the given name exists
            project = self._get_schema_by_name_or_id(
                object_name_or_id=project_name_or_id,
                schema_class=ProjectSchema,
                session=session,
            )
            if (
                self._default_project_enabled
                and project.name == self._default_project_name
            ):
                raise IllegalOperationError(
                    "The default project cannot be deleted."
                )

            session.delete(project)
            session.commit()

    def count_projects(
        self, filter_model: Optional[ProjectFilter] = None
    ) -> int:
        """Count all projects.

        Args:
            filter_model: The filter model to use for counting projects.

        Returns:
            The number of projects.
        """
        return self._count_entity(
            schema=ProjectSchema, filter_model=filter_model
        )

    def set_filter_project_id(
        self,
        filter_model: ProjectScopedFilter,
        project_name_or_id: Optional[Union[UUID, str]] = None,
    ) -> None:
        """Set the project ID on a filter model.

        Args:
            filter_model: The filter model to set the project ID on.
            project_name_or_id: The project to set the scope for. If not
                provided, the project scope is determined from the request
                project filter or the default project, in that order.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=filter_model,
                session=session,
                project_name_or_id=project_name_or_id,
            )

    def _get_or_create_default_project(self) -> ProjectResponse:
        """Get or create the default project if it doesn't exist.

        Returns:
            The default project.
        """
        default_project_name = self._default_project_name

        try:
            return self.get_project(default_project_name)
        except KeyError:
            logger.info(
                f"Creating default project '{default_project_name}' ..."
            )
            return self.create_project(
                ProjectRequest(name=default_project_name)
            )

    @property
    def _default_project_enabled(self) -> bool:
        """Check if the default project is enabled.

        When running in a Pro ZenML server, the default project is not enabled.

        Returns:
            True if the default project is enabled, False otherwise.
        """
        default_project_enabled = True
        if ENV_ZENML_SERVER in os.environ:
            from zenml.config.server_config import ServerConfiguration

            if (
                ServerConfiguration.get_server_config().deployment_type
                == ServerDeploymentType.CLOUD
            ):
                default_project_enabled = False

        return default_project_enabled

    # =======================
    # Internal helper methods
    # =======================

    def _count_entity(
        self,
        schema: Type[BaseSchema],
        filter_model: Optional[BaseFilter] = None,
    ) -> int:
        """Return count of a given entity.

        Args:
            schema: Schema of the Entity
            filter_model: The filter model to filter the entity table.

        Returns:
            Count of the entity as integer.
        """
        with Session(self.engine) as session:
            query = select(func.count(schema.id))  # type: ignore[arg-type]

            if filter_model:
                if isinstance(filter_model, ProjectScopedFilter):
                    self._set_filter_project_id(
                        filter_model=filter_model,
                        session=session,
                        project_name_or_id=filter_model.project,
                    )
                query = filter_model.apply_filter(query=query, table=schema)

            entity_count = session.scalar(query)

        return int(entity_count) if entity_count else 0

    def entity_exists(
        self, entity_id: UUID, schema_class: Type[AnySchema]
    ) -> bool:
        """Check whether an entity exists in the database.

        Args:
            entity_id: The ID of the entity to check.
            schema_class: The schema class.

        Returns:
            If the entity exists.
        """
        with Session(self.engine) as session:
            schema = session.exec(
                select(schema_class.id).where(schema_class.id == entity_id)
            ).first()

            return False if schema is None else True

    def get_entity_by_id(
        self, entity_id: UUID, schema_class: Type[AnySchema]
    ) -> Optional[AnyIdentifiedResponse]:
        """Get an entity by ID.

        Args:
            entity_id: The ID of the entity to get.
            schema_class: The schema class.

        Raises:
            RuntimeError: If the schema to model conversion failed.

        Returns:
            The entity if it exists, None otherwise
        """
        with Session(self.engine) as session:
            schema = session.exec(
                select(schema_class).where(schema_class.id == entity_id)
            ).first()

            if not schema:
                return None

            to_model = getattr(schema, "to_model", None)
            if callable(to_model):
                return cast(
                    AnyIdentifiedResponse,
                    to_model(include_metadata=True, include_resources=True),
                )
            else:
                raise RuntimeError("Unable to convert schema to model.")

    @staticmethod
    def _get_schema_by_id(
        resource_id: UUID,
        schema_class: Type[AnySchema],
        session: Session,
        resource_type: Optional[str] = None,
        project_id: Optional[UUID] = None,
        query_options: Optional[Sequence[ExecutableOption]] = None,
    ) -> AnySchema:
        """Query a schema by its 'id' field.

        Args:
            resource_id: The ID of the resource to query.
            schema_class: The schema class to query. E.g., `StackSchema`.
            session: The database session to use.
            resource_type: Optional name of the resource type to use in error
                messages. If not provided, the type name will be inferred
                from the schema class.
            project_id: Optional ID of a project to filter by.
            query_options: Optional list of query options to apply to the query.

        Returns:
            The schema object.

        Raises:
            KeyError: if the object couldn't be found.
            RuntimeError: if the schema is not project-scoped but the
                project ID is provided.
        """
        resource_type = resource_type or get_resource_type_name(schema_class)
        error_msg = (
            f"Unable to get {resource_type} with ID "
            f"'{resource_id}': No {resource_type} with this ID found"
        )
        query = select(schema_class).where(schema_class.id == resource_id)
        if project_id:
            error_msg += f" in project `{str(project_id)}`"
            if not hasattr(schema_class, "project_id"):
                raise RuntimeError(
                    f"Schema {schema_class.__name__} is not project-scoped."
                )

            query = query.where(schema_class.project_id == project_id)  # type: ignore[attr-defined]

        if query_options:
            query = query.options(*query_options)

        schema = session.exec(query).first()

        if schema is None:
            raise KeyError(error_msg)
        return schema

    @staticmethod
    def _get_schema_by_name_or_id(
        object_name_or_id: Union[str, UUID],
        schema_class: Type[AnyNamedSchema],
        session: Session,
        project_name_or_id: Optional[Union[UUID, str]] = None,
    ) -> AnyNamedSchema:
        """Query a schema by its 'name' or 'id' field.

        Args:
            object_name_or_id: The name or ID of the object to query.
            schema_class: The schema class to query. E.g., `ProjectSchema`.
            session: The database session to use.
            project_name_or_id: The name or ID of the project to filter by.
                Required if the resource is project-scoped and the
                object_name_or_id is not a UUID.

        Returns:
            The schema object.

        Raises:
            KeyError: if the object couldn't be found.
        """
        schema_name = get_resource_type_name(schema_class)
        if uuid_utils.is_valid_uuid(object_name_or_id):
            filter_params = schema_class.id == object_name_or_id
            error_msg = (
                f"Unable to get {schema_name} with name or ID "
                f"'{object_name_or_id}': No {schema_name} with this ID found"
            )
        else:
            filter_params = schema_class.name == object_name_or_id
            error_msg = (
                f"Unable to get {schema_name} with name or ID "
                f"'{object_name_or_id}': '{object_name_or_id}' is not a valid "
                f" UUID and no {schema_name} with this name exists"
            )

        query = select(schema_class).where(filter_params)
        if project_name_or_id and hasattr(schema_class, "project_id"):
            if uuid_utils.is_valid_uuid(project_name_or_id):
                query = query.where(
                    schema_class.project_id == project_name_or_id  # type: ignore[attr-defined]
                )
            else:
                # Join the project table to get the project name
                query = query.join(ProjectSchema).where(
                    ProjectSchema.name == project_name_or_id
                )
            error_msg += f" in project `{project_name_or_id}`."
        else:
            error_msg += "."

        schema = session.exec(query).first()

        if schema is None:
            raise KeyError(error_msg)
        return schema

    @overload
    def _get_reference_schema_by_id(
        self,
        session: Session,
        resource: Union[BaseRequest, BaseSchema],
        reference_schema: Type[AnySchema],
        reference_id: UUID,
        reference_type: Optional[str] = None,
    ) -> AnySchema: ...

    @overload
    def _get_reference_schema_by_id(
        self,
        session: Session,
        resource: Union[BaseRequest, BaseSchema],
        reference_schema: Type[AnySchema],
        reference_id: None,
        reference_type: Optional[str] = None,
    ) -> None: ...

    def _get_reference_schema_by_id(
        self,
        session: Session,
        resource: Union[BaseRequest, BaseSchema],
        reference_schema: Type[AnySchema],
        reference_id: Optional[UUID] = None,
        reference_type: Optional[str] = None,
    ) -> Optional[AnySchema]:
        """Fetch a referenced resource and verify scope relationship rules.

        This helper function is used for two things:
        1. Fetch a referenced resource from the database.
        2. Enforce the scope relationship rules established between any main
        resource and its references:
            a) a project-scoped resource (e.g. pipeline run) may reference
            another project-scoped resource (e.g. pipeline) if it is within
            the same project.
            b) a project-scoped resource (e.g. pipeline run) may reference a
            global-scoped resource (e.g. stack).
            c) a global-scoped resource (e.g. stack) may never reference a
            project-scoped resource (e.g. pipeline).
            d) a global-scoped resource (e.g. stack) may reference another
            global-scoped resource (e.g. component).

        Args:
            session: The session to use to perform the verification.
            resource: The main entity. This can be a request model, passed
                during resource creation or a response model, passed during
                resource updates.
            reference_schema: The schema of the referenced entity.
            reference_id: The ID of the referenced entity. If not provided, the
                function will return immediately with a None value.
            reference_type: The type name of the referenced resource to use in
                error messages. If not provided, the type name will be inferred
                from the schema class.

        Returns:
            The referenced resource.

        Raises:
            RuntimeError: If the schema has no project_id attribute.
            KeyError: If the referenced resource is not found.
        """
        if reference_id is None:
            return None

        # Create a resource type name out of the model name
        resource_type = type(resource).__name__
        # Remove the "Response" and "Request" suffix
        resource_type = resource_type.removesuffix("Response").removesuffix(
            "Request"
        )
        # Split into words
        resource_type = re.sub(r"(?<!^)(?=[A-Z])", " ", resource_type).lower()

        reference_type = reference_type or get_resource_type_name(
            reference_schema
        )

        operation: str = "created"
        if isinstance(resource, BaseSchema):
            operation = "updated"

        resource_project_id: Optional[UUID] = None
        resource_project_name: Optional[str] = None
        if isinstance(resource, ProjectScopedRequest):
            resource_project_id = resource.project
            resource_project_name = str(resource.project)
        elif isinstance(resource, BaseSchema):
            resource_project_id = getattr(resource, "project_id", None)
            resource_project = getattr(resource, "project", None)
            if resource_project:
                assert isinstance(resource_project, ProjectSchema)
                resource_project_name = resource_project.name

        error_msg = (
            f"The {reference_type} with ID {str(reference_id)} referenced by "
            f"the {resource_type} being {operation} was not found"
        )

        reference_is_project_scoped = hasattr(reference_schema, "project_id")

        # There's one particular case that should never happen: if a global
        # resource (e.g. a stack) references a project-scoped resource
        # (e.g. a pipeline), this is a design error.
        if resource_project_id is None and reference_is_project_scoped:
            raise RuntimeError(
                f"A global resource {resource_type} cannot reference a "
                f"project-scoped resource {reference_type}. This is a "
                "design error."
            )

        # Filter the reference by project if the resource itself is
        # project-scoped and the reference is project-scoped.
        reference_project_filter = (
            resource_project_id if reference_is_project_scoped else None
        )
        try:
            return self._get_schema_by_id(
                resource_id=reference_id,
                schema_class=reference_schema,
                session=session,
                project_id=reference_project_filter,
                resource_type=reference_type,
            )
        except KeyError:
            if reference_project_filter:
                error_msg += f" in the '{resource_project_name}' project"

            raise KeyError(error_msg)

    def _set_request_user_id(
        self,
        request_model: BaseRequest,
        session: Session,
    ) -> None:
        """Set the user ID on a request model to the active user.

        Args:
            request_model: The request model to set the user ID on.
            session: The DB session to use for queries.
        """
        if not isinstance(request_model, UserScopedRequest):
            # If the request model is not a UserScopedRequest, we don't need to
            # set the user ID.
            return

        request_model.user = self._get_active_user(session).id

    def _set_filter_project_id(
        self,
        filter_model: ProjectScopedFilter,
        session: Session,
        project_name_or_id: Optional[Union[UUID, str]] = None,
    ) -> None:
        """Set the project ID on a filter model.

        Args:
            filter_model: The filter model to set the project ID on.
            session: The DB session to use for queries.
            project_name_or_id: The project to set the scope for. If not
                provided, the project scope is determined from the request
                project filter or the default project, in that order.

        Raises:
            ValueError: If the project scope is missing from the filter.
        """
        if project_name_or_id:
            project = self._get_schema_by_name_or_id(
                object_name_or_id=project_name_or_id,
                schema_class=ProjectSchema,
                session=session,
            )
            project_id = project.id
        elif filter_model.project:
            project = self._get_schema_by_name_or_id(
                object_name_or_id=filter_model.project,
                schema_class=ProjectSchema,
                session=session,
            )
            project_id = project.id
        elif self._default_project_enabled:
            # Use the default project as a last resort.
            try:
                project = self._get_schema_by_name_or_id(
                    object_name_or_id=self._default_project_name,
                    schema_class=ProjectSchema,
                    session=session,
                )
                project_id = project.id
            except KeyError:
                raise ValueError("Project scope missing from the filter")
        else:
            raise ValueError("Project scope missing from the filter")

        filter_model.project = project_id

    def _verify_name_uniqueness(
        self,
        resource: Union[BaseRequest, BaseUpdate],
        schema: Union[Type[AnyNamedSchema], AnyNamedSchema],
        session: Session,
    ) -> None:
        """Check the name uniqueness constraint for a given entity.

        This method can be used to verify the name uniqueness constraint for
        a given entity during creation and during subsequent updates:

        * during creation, by providing a request and a schema class.
        * during updates, by providing an update and the schema object
        of the existing entity being updated

        The scope in which the name uniqueness is verified depends on the
        entity type: for global resources (e.g. stack, service-connector), the
        name must be globally unique, while for project-scoped resources (e.g.
        pipeline, artifact, etc.), the name must be unique within the
        project.

        Args:
            resource: The resource to verify the name uniqueness for. This can
                be a request model used during a resource creation or an update
                model used during a resource update.
            schema: The schema for the resource. For a created resource, this
                will be the schema class, while for an updated resource, this
                will be the existing schema object being updated.
            session: The session to use to verify the name of.

        Raises:
            RuntimeError: If the arguments are invalid.
            EntityExistsError: If the name is not unique.
        """
        # If the model type doesn't have a `name` attribute, we can't verify
        # the name uniqueness.
        if not hasattr(resource, "name"):
            raise RuntimeError(
                f"Model {type(resource)} does not represent a named entity."
            )
        name = getattr(resource, "name")

        if isinstance(schema, BaseSchema):
            schema_class = type(schema)
        else:
            schema_class = schema

        if not hasattr(schema_class, "name"):
            raise RuntimeError(f"Schema {schema_class.__name__} has no name.")

        operation: Literal["create", "update"] = "create"
        project_id: Optional[UUID] = None
        if isinstance(resource, BaseRequest):
            # Create operation
            if isinstance(resource, ProjectScopedRequest):
                project_id = resource.project
            else:
                project_id = None
        else:
            # Update operation
            if name is None:
                # If the name is not set - i.e. the name is not actually updated
                # during an update - we don't need to verify the name
                # uniqueness.
                return
            if not isinstance(schema, BaseSchema):
                raise RuntimeError(
                    "An existing schema instance must be provided for update "
                    "operations."
                )
            existing_name = getattr(schema, "name", None)
            if existing_name == name:
                # If the name is not being changed during an update, we don't
                # need to verify the name uniqueness.
                return
            project_id = getattr(schema, "project_id", None)
            operation = "update"

        query = select(schema_class).where(schema_class.name == name)

        # We "detect" if the entity is project-scoped by looking at the
        # project_id attribute.
        if project_id:
            if not hasattr(schema_class, "project_id") or not hasattr(
                schema_class, "project"
            ):
                raise RuntimeError(
                    f"Model {type(resource)} is project-scoped, but "
                    f"schema {schema_class.__name__} has no "
                    "project_id and project attributes."
                )
            query = query.where(schema_class.project_id == project_id)  # type: ignore[attr-defined]

        existing_entry = session.exec(query).first()
        if existing_entry is not None:
            resource_name = get_resource_type_name(schema_class)
            if project_id:
                scope = f" in the '{existing_entry.project.name}' project"  # type: ignore[attr-defined]
            else:
                scope = ""
            raise EntityExistsError(
                f"Unable to {operation} the requested {resource_name} with name "
                f"'{name}': Found another existing {resource_name} with the same "
                f"name{scope}."
            )

    def _get_account_schema(
        self,
        account_name_or_id: Union[str, UUID],
        session: Session,
        service_account: Optional[bool] = None,
    ) -> UserSchema:
        """Gets a user account or a service account schema by name or ID.

        This helper method is used to fetch both user accounts and service
        accounts by name or ID. It is required because in the DB, user accounts
        and service accounts are stored using the same UserSchema to make
        it easier to implement resource ownership.

        Args:
            account_name_or_id: The name or ID of the account to get.
            session: The database session to use.
            service_account: Whether to get a service account or a user
                account. If None, both are considered with a priority for
                user accounts if both exist (e.g. with the same name).

        Returns:
            The account schema.

        Raises:
            KeyError: If no account with the given name or ID exists.
        """
        account_type = ""
        query = select(UserSchema)
        if uuid_utils.is_valid_uuid(account_name_or_id):
            query = query.where(UserSchema.id == account_name_or_id)
        else:
            query = query.where(UserSchema.name == account_name_or_id)
        if service_account is not None:
            if service_account is True:
                account_type = "service "
            elif service_account is False:
                account_type = "user "
            query = query.where(
                UserSchema.is_service_account == service_account  # noqa: E712
            )
        error_msg = (
            f"No {account_type}account with the '{account_name_or_id}' name "
            "or ID was found"
        )

        results = session.exec(query).all()

        if len(results) == 0:
            raise KeyError(error_msg)

        if len(results) == 1:
            return results[0]

        # We could have two results if a service account and a user account
        # have the same name. In that case, we return the user account.
        for result in results:
            if not result.is_service_account:
                return result

        raise KeyError(error_msg)

    # ----------------------------- Models -----------------------------

    @track_decorator(AnalyticsEvent.CREATED_MODEL)
    def create_model(self, model: ModelRequest) -> ModelResponse:
        """Creates a new model.

        Args:
            model: the Model to be created.

        Returns:
            The newly created model.

        Raises:
            EntityExistsError: If a model with the given name already exists.
        """
        validate_name(model)
        with Session(self.engine) as session:
            self._set_request_user_id(request_model=model, session=session)

            self._verify_name_uniqueness(
                resource=model,
                schema=ModelSchema,
                session=session,
            )

            model_schema = ModelSchema.from_request(model)
            session.add(model_schema)

            try:
                session.commit()
            except IntegrityError:
                # We have to rollback the failed session first in order
                # to continue using it
                session.rollback()
                raise EntityExistsError(
                    f"Unable to create model {model.name}: "
                    "A model with this name already exists."
                )

            self._attach_tags_to_resources(
                tags=model.tags,
                resources=model_schema,
                session=session,
            )

            session.refresh(model_schema)

            return model_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def get_model(
        self,
        model_id: UUID,
        hydrate: bool = True,
    ) -> ModelResponse:
        """Get an existing model.

        Args:
            model_id: id of the model to be retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The model of interest.
        """
        with Session(self.engine) as session:
            model = self._get_schema_by_id(
                resource_id=model_id,
                schema_class=ModelSchema,
                session=session,
            )
            return model.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def get_model_by_name_or_id(
        self,
        model_name_or_id: Union[str, UUID],
        project: UUID,
        hydrate: bool = True,
    ) -> ModelResponse:
        """Get a model by name or ID.

        Args:
            model_name_or_id: The name or ID of the model to get.
            project: The project ID of the model to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The model.
        """
        with Session(self.engine) as session:
            model = self._get_schema_by_name_or_id(
                object_name_or_id=model_name_or_id,
                schema_class=ModelSchema,
                session=session,
                project_name_or_id=project,
            )

            return model.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_models(
        self,
        model_filter_model: ModelFilter,
        hydrate: bool = False,
    ) -> Page[ModelResponse]:
        """Get all models by filter.

        Args:
            model_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all models.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=model_filter_model,
                session=session,
            )
            query = select(ModelSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ModelSchema,
                filter_model=model_filter_model,
                hydrate=hydrate,
            )

    def delete_model(self, model_id: UUID) -> None:
        """Deletes a model.

        Args:
            model_id: id of the model to be deleted.
        """
        with Session(self.engine) as session:
            model = self._get_schema_by_id(
                resource_id=model_id,
                schema_class=ModelSchema,
                session=session,
            )

            session.delete(model)
            session.commit()

    def update_model(
        self,
        model_id: UUID,
        model_update: ModelUpdate,
    ) -> ModelResponse:
        """Updates an existing model.

        Args:
            model_id: UUID of the model to be updated.
            model_update: the Model to be updated.

        Raises:
            KeyError: specified ID not found.

        Returns:
            The updated model.
        """
        with Session(self.engine) as session:
            existing_model = session.exec(
                select(ModelSchema).where(ModelSchema.id == model_id)
            ).first()

            if not existing_model:
                raise KeyError(f"Model with ID {model_id} not found.")

            self._verify_name_uniqueness(
                resource=model_update,
                schema=existing_model,
                session=session,
            )

            existing_model.update(model_update=model_update)

            session.add(existing_model)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_model)

            self._attach_tags_to_resources(
                tags=model_update.add_tags,
                resources=existing_model,
                session=session,
            )
            self._detach_tags_from_resources(
                tags=model_update.remove_tags,
                resources=existing_model,
                session=session,
            )

            session.refresh(existing_model)

            return existing_model.to_model(
                include_metadata=True, include_resources=True
            )

    # ----------------------------- Model Versions -----------------------------

    def _get_or_create_model(
        self, model_request: ModelRequest
    ) -> Tuple[bool, ModelResponse]:
        """Get or create a model.

        Args:
            model_request: The model request.

        Returns:
            A boolean whether the model was created or not, and the model.
        """
        try:
            return True, self.create_model(model_request)
        except EntityExistsError:
            return False, self.get_model_by_name_or_id(
                model_name_or_id=model_request.name,
                project=model_request.project,
            )

    def _get_next_numeric_version_for_model(
        self, session: Session, model_id: UUID
    ) -> int:
        """Get the next numeric version for a model.

        Args:
            session: DB session.
            model_id: ID of the model for which to get the next numeric
                version.

        Returns:
            The next numeric version.
        """
        current_max_version = session.exec(
            select(func.max(ModelVersionSchema.number)).where(
                ModelVersionSchema.model_id == model_id
            )
        ).first()

        if current_max_version is None:
            return 1
        else:
            return int(current_max_version) + 1

    def _model_version_exists(
        self,
        session: Session,
        model_id: UUID,
        version: Optional[str] = None,
        producer_run_id: Optional[UUID] = None,
    ) -> bool:
        """Check if a model version with a certain version exists.

        Args:
            session: SQLAlchemy session.
            model_id: The model ID of the version.
            version: The version name.
            producer_run_id: The producer run ID. If given, checks if a numeric
                version for the producer run exists.

        Returns:
            If a model version for the given arguments exists.
        """
        query = select(ModelVersionSchema.id).where(
            ModelVersionSchema.model_id == model_id
        )

        if version:
            query = query.where(ModelVersionSchema.name == version)

        if producer_run_id:
            query = query.where(
                ModelVersionSchema.producer_run_id_if_numeric
                == producer_run_id,
            )

        with Session(self.engine) as session:
            return session.exec(query).first() is not None

    def _get_model_version(
        self,
        model_id: UUID,
        version_name: Optional[str] = None,
        producer_run_id: Optional[UUID] = None,
    ) -> ModelVersionResponse:
        """Get a model version.

        Args:
            model_id: The ID of the model.
            version_name: The name of the model version.
            producer_run_id: The ID of the producer pipeline run. If this is
                set, only numeric versions created as part of the pipeline run
                will be returned.

        Raises:
            ValueError: If no version name or producer run ID was provided.
            KeyError: If no model version was found.

        Returns:
            The model version.
        """
        query = select(ModelVersionSchema).where(
            ModelVersionSchema.model_id == model_id
        )

        if version_name:
            if version_name.isnumeric():
                query = query.where(
                    ModelVersionSchema.number == int(version_name)
                )
                error_text = (
                    f"No version with number {version_name} found "
                    f"for model {model_id}."
                )
            elif version_name in ModelStages.values():
                if version_name == ModelStages.LATEST:
                    query = query.order_by(
                        desc(col(ModelVersionSchema.number))
                    ).limit(1)
                else:
                    query = query.where(
                        ModelVersionSchema.stage == version_name
                    )
                error_text = (
                    f"No {version_name} stage version found for "
                    f"model {model_id}."
                )
            else:
                query = query.where(ModelVersionSchema.name == version_name)
                error_text = (
                    f"No {version_name} version found for model {model_id}."
                )

        elif producer_run_id:
            query = query.where(
                ModelVersionSchema.producer_run_id_if_numeric
                == producer_run_id,
            )
            error_text = (
                f"No numeric model version found for model {model_id} "
                f"and producer run {producer_run_id}."
            )
        else:
            raise ValueError(
                "Version name or producer run id need to be specified."
            )

        with Session(self.engine) as session:
            schema = session.exec(query).one_or_none()

            if not schema:
                raise KeyError(error_text)

            return schema.to_model(
                include_metadata=True, include_resources=True
            )

    def _get_or_create_model_version(
        self,
        model_version_request: ModelVersionRequest,
        producer_run_id: Optional[UUID] = None,
    ) -> Tuple[bool, ModelVersionResponse]:
        """Get or create a model version.

        Args:
            model_version_request: The model version request.
            producer_run_id: ID of the producer pipeline run.

        Raises:
            EntityCreationError: If the model version creation failed.

        Returns:
            A boolean whether the model version was created or not, and the
            model version.
        """
        try:
            model_version = self._create_model_version(
                model_version=model_version_request,
                producer_run_id=producer_run_id,
            )
            track(
                event=AnalyticsEvent.CREATED_MODEL_VERSION,
                metadata={"project_id": model_version.project_id},
            )
            return True, model_version
        except EntityCreationError:
            # Need to explicitly re-raise this here as otherwise the catching
            # of the RuntimeError would include this
            raise
        except RuntimeError:
            return False, self._get_model_version(
                model_id=model_version_request.model,
                producer_run_id=producer_run_id,
            )
        except EntityExistsError:
            return False, self._get_model_version(
                model_id=model_version_request.model,
                version_name=model_version_request.name,
            )

    def _get_or_create_model_version_for_run(
        self, pipeline_or_step_run: Union[PipelineRunSchema, StepRunSchema]
    ) -> Optional[UUID]:
        """Get or create a model version for a pipeline or step run.

        Args:
            pipeline_or_step_run: The pipeline or step run for which to create
                the model version.

        Returns:
            The model version.
        """
        if isinstance(pipeline_or_step_run, PipelineRunSchema):
            producer_run_id = pipeline_or_step_run.id
            pipeline_run = pipeline_or_step_run.to_model(include_metadata=True)
            configured_model = pipeline_run.config.model
            substitutions = pipeline_run.config.substitutions
        else:
            producer_run_id = pipeline_or_step_run.pipeline_run_id
            step_run = pipeline_or_step_run.to_model(include_metadata=True)
            configured_model = step_run.config.model
            substitutions = step_run.config.substitutions

        if not configured_model:
            return None

        model_request = ModelRequest(
            name=format_name_template(
                configured_model.name, substitutions=substitutions
            ),
            license=configured_model.license,
            description=configured_model.description,
            audience=configured_model.audience,
            use_cases=configured_model.use_cases,
            limitations=configured_model.limitations,
            trade_offs=configured_model.trade_offs,
            ethics=configured_model.ethics,
            save_models_to_registry=configured_model.save_models_to_registry,
            user=pipeline_or_step_run.user_id,
            project=pipeline_or_step_run.project_id,
        )

        _, model_response = self._get_or_create_model(
            model_request=model_request
        )

        version_name = None
        if configured_model.version is not None:
            version_name = format_name_template(
                str(configured_model.version), substitutions=substitutions
            )

            # If the model version was specified to be a numeric version or
            # stage we don't try to create it (which will fail because it is not
            # allowed) but try to fetch it immediately
            if (
                version_name.isnumeric()
                or version_name in ModelStages.values()
            ):
                return self._get_model_version(
                    model_id=model_response.id, version_name=version_name
                ).id

        model_version_request = ModelVersionRequest(
            model=model_response.id,
            name=version_name,
            description=configured_model.description,
            tags=configured_model.tags,
            user=pipeline_or_step_run.user_id,
            project=pipeline_or_step_run.project_id,
        )

        _, model_version_response = self._get_or_create_model_version(
            model_version_request=model_version_request,
            producer_run_id=producer_run_id,
        )
        return model_version_response.id

    def _create_model_version(
        self,
        model_version: ModelVersionRequest,
        producer_run_id: Optional[UUID] = None,
    ) -> ModelVersionResponse:
        """Creates a new model version.

        Args:
            model_version: the Model Version to be created.
            producer_run_id: ID of the pipeline run that produced this model
                version.

        Returns:
            The newly created model version.

        Raises:
            ValueError: If the requested version name is invalid.
            EntityExistsError: If a model version with the given name already
                exists.
            EntityCreationError: If the model version creation failed.
            RuntimeError: If an auto-incremented model version already exists
                for the producer run.
        """
        has_custom_name = False
        if model_version.name:
            has_custom_name = True
            validate_name(model_version)

            if model_version.name.isnumeric():
                raise ValueError(
                    "Can't create model version with custom numeric model "
                    "version name."
                )

            if str(model_version.name).lower() in ModelStages.values():
                raise ValueError(
                    "Can't create model version with a name that is used as a "
                    f"model version stage ({ModelStages.values()})."
                )

        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=model_version, session=session
            )
            model = self._get_reference_schema_by_id(
                resource=model_version,
                reference_schema=ModelSchema,
                reference_id=model_version.model,
                session=session,
            )
            assert model is not None

            model_version_schema: Optional[ModelVersionSchema] = None

            remaining_tries = MAX_RETRIES_FOR_VERSIONED_ENTITY_CREATION
            while remaining_tries > 0:
                remaining_tries -= 1
                try:
                    model_version_number = (
                        self._get_next_numeric_version_for_model(
                            session=session,
                            model_id=model.id,
                        )
                    )
                    if not has_custom_name:
                        model_version.name = str(model_version_number)

                    model_version_schema = ModelVersionSchema.from_request(
                        model_version,
                        model_version_number=model_version_number,
                        producer_run_id=producer_run_id,
                    )
                    session.add(model_version_schema)
                    session.commit()
                    break
                except IntegrityError:
                    # We have to rollback the failed session first in order to
                    # continue using it
                    session.rollback()
                    if has_custom_name and self._model_version_exists(
                        model_id=model.id,
                        version=cast(str, model_version.name),
                        session=session,
                    ):
                        # We failed not because of a version number conflict,
                        # but because the user requested a version name that
                        # is already taken -> We don't retry anymore but fail
                        # immediately.
                        raise EntityExistsError(
                            f"Unable to create model version "
                            f"{model.name} (version "
                            f"{model_version.name}): A model with the "
                            "same name and version already exists."
                        )
                    elif producer_run_id and self._model_version_exists(
                        model_id=model.id,
                        producer_run_id=producer_run_id,
                        session=session,
                    ):
                        raise RuntimeError(
                            "Auto-incremented model version already exists for "
                            f"producer run {producer_run_id}."
                        )
                    elif remaining_tries == 0:
                        raise EntityCreationError(
                            f"Failed to create version for model "
                            f"{model.name}. This is most likely "
                            "caused by multiple parallel requests that try "
                            "to create versions for this model in the "
                            "database."
                        )
                    else:
                        attempt = (
                            MAX_RETRIES_FOR_VERSIONED_ENTITY_CREATION
                            - remaining_tries
                        )
                        sleep_duration = exponential_backoff_with_jitter(
                            attempt=attempt
                        )
                        logger.debug(
                            "Failed to create model version %s "
                            "due to an integrity error. "
                            "Retrying in %f seconds.",
                            model.name,
                            sleep_duration,
                        )
                        time.sleep(sleep_duration)

            assert model_version_schema is not None
            self._attach_tags_to_resources(
                tags=model_version.tags,
                resources=model_version_schema,
                session=session,
            )
            session.refresh(model_version_schema)
            return self.get_model_version(model_version_schema.id)

    @track_decorator(AnalyticsEvent.CREATED_MODEL_VERSION)
    def create_model_version(
        self, model_version: ModelVersionRequest
    ) -> ModelVersionResponse:
        """Creates a new model version.

        Args:
            model_version: the Model Version to be created.

        Returns:
            The newly created model version.
        """
        return self._create_model_version(model_version=model_version)

    def get_model_version(
        self, model_version_id: UUID, hydrate: bool = True
    ) -> ModelVersionResponse:
        """Get an existing model version.

        Args:
            model_version_id: name, id, stage or number of the model version to
                be retrieved. If skipped - latest is retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The model version of interest.
        """
        with Session(self.engine) as session:
            model_version = self._get_schema_by_id(
                resource_id=model_version_id,
                schema_class=ModelVersionSchema,
                session=session,
                query_options=ModelVersionSchema.get_query_options(
                    include_metadata=hydrate, include_resources=True
                ),
            )

            return model_version.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_model_versions(
        self,
        model_version_filter_model: ModelVersionFilter,
        hydrate: bool = False,
    ) -> Page[ModelVersionResponse]:
        """Get all model versions by filter.

        Args:
            model_version_filter_model: All filter parameters including
                pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all model versions.
        """
        with Session(self.engine) as session:
            self._set_filter_project_id(
                filter_model=model_version_filter_model,
                session=session,
            )
            query = select(ModelVersionSchema)

            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ModelVersionSchema,
                filter_model=model_version_filter_model,
                hydrate=hydrate,
                apply_query_options_from_schema=True,
            )

    def delete_model_version(
        self,
        model_version_id: UUID,
    ) -> None:
        """Deletes a model version.

        Args:
            model_version_id: name or id of the model version to be deleted.

        Raises:
            KeyError: specified ID or name not found.
        """
        with Session(self.engine) as session:
            query = select(ModelVersionSchema).where(
                ModelVersionSchema.id == model_version_id
            )
            model_version = session.exec(query).first()
            if model_version is None:
                raise KeyError(
                    "Unable to delete model version with id "
                    f"`{model_version_id}`: "
                    "No model version with this id found."
                )
            session.delete(model_version)
            session.commit()

    def update_model_version(
        self,
        model_version_id: UUID,
        model_version_update_model: ModelVersionUpdate,
    ) -> ModelVersionResponse:
        """Get all model versions by filter.

        Args:
            model_version_id: The ID of model version to be updated.
            model_version_update_model: The model version to be updated.

        Returns:
            An updated model version.

        Raises:
            KeyError: If the model version not found
            RuntimeError: If there is a model version with target stage,
                but `force` flag is off
        """
        with Session(self.engine) as session:
            existing_model_version = session.exec(
                select(ModelVersionSchema).where(
                    ModelVersionSchema.id == model_version_id
                )
            ).first()

            if not existing_model_version:
                raise KeyError(f"Model version {model_version_id} not found.")

            stage = None
            if (stage_ := model_version_update_model.stage) is not None:
                stage = getattr(stage_, "value", stage_)

                existing_model_version_in_target_stage = session.exec(
                    select(ModelVersionSchema)
                    .where(
                        ModelVersionSchema.model_id
                        == existing_model_version.model_id
                    )
                    .where(ModelVersionSchema.stage == stage)
                ).first()

                if (
                    existing_model_version_in_target_stage is not None
                    and existing_model_version_in_target_stage.id
                    != existing_model_version.id
                ):
                    if not model_version_update_model.force:
                        raise RuntimeError(
                            f"Model version {existing_model_version_in_target_stage.name} is "
                            f"in {stage}, but `force` flag is False."
                        )
                    else:
                        existing_model_version_in_target_stage.update(
                            target_stage=ModelStages.ARCHIVED.value
                        )
                        session.add(existing_model_version_in_target_stage)

                        logger.info(
                            f"Model version {existing_model_version_in_target_stage.name} has been set to {ModelStages.ARCHIVED.value}."
                        )

            existing_model_version.update(
                target_stage=stage,
                target_name=model_version_update_model.name,
                target_description=model_version_update_model.description,
            )
            session.add(existing_model_version)
            session.commit()
            session.refresh(existing_model_version)

            self._attach_tags_to_resources(
                tags=model_version_update_model.add_tags,
                resources=existing_model_version,
                session=session,
            )
            self._detach_tags_from_resources(
                tags=model_version_update_model.remove_tags,
                resources=existing_model_version,
                session=session,
            )
            session.refresh(existing_model_version)
            return existing_model_version.to_model(
                include_metadata=True, include_resources=True
            )

    # ------------------------ Model Versions Artifacts ------------------------

    def create_model_version_artifact_link(
        self, model_version_artifact_link: ModelVersionArtifactRequest
    ) -> ModelVersionArtifactResponse:
        """Creates a new model version link.

        Args:
            model_version_artifact_link: the Model Version to Artifact Link
                to be created.

        Returns:
            The newly created model version to artifact link.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=model_version_artifact_link, session=session
            )

            # If the link already exists, return it
            existing_model_version_artifact_link = session.exec(
                select(ModelVersionArtifactSchema)
                .where(
                    ModelVersionArtifactSchema.model_version_id
                    == model_version_artifact_link.model_version
                )
                .where(
                    ModelVersionArtifactSchema.artifact_version_id
                    == model_version_artifact_link.artifact_version,
                )
            ).first()
            if existing_model_version_artifact_link is not None:
                return existing_model_version_artifact_link.to_model()

            model_version_artifact_link_schema = (
                ModelVersionArtifactSchema.from_request(
                    model_version_artifact_request=model_version_artifact_link,
                )
            )
            session.add(model_version_artifact_link_schema)
            session.commit()
            return model_version_artifact_link_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def list_model_version_artifact_links(
        self,
        model_version_artifact_link_filter_model: ModelVersionArtifactFilter,
        hydrate: bool = False,
    ) -> Page[ModelVersionArtifactResponse]:
        """Get all model version to artifact links by filter.

        Args:
            model_version_artifact_link_filter_model: All filter parameters
                including pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all model version to artifact links.
        """
        with Session(self.engine) as session:
            query = select(ModelVersionArtifactSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ModelVersionArtifactSchema,
                filter_model=model_version_artifact_link_filter_model,
                hydrate=hydrate,
            )

    def delete_model_version_artifact_link(
        self,
        model_version_id: UUID,
        model_version_artifact_link_name_or_id: Union[str, UUID],
    ) -> None:
        """Deletes a model version to artifact link.

        Args:
            model_version_id: ID of the model version containing the link.
            model_version_artifact_link_name_or_id: name or ID of the model
                version to artifact link to be deleted.

        Raises:
            KeyError: specified ID or name not found.
        """
        with Session(self.engine) as session:
            model_version = self.get_model_version(model_version_id)
            query = select(ModelVersionArtifactSchema).where(
                ModelVersionArtifactSchema.model_version_id == model_version.id
            )
            try:
                UUID(str(model_version_artifact_link_name_or_id))
                query = query.where(
                    ModelVersionArtifactSchema.id
                    == model_version_artifact_link_name_or_id
                )
            except ValueError:
                query = (
                    query.where(
                        ModelVersionArtifactSchema.artifact_version_id
                        == ArtifactVersionSchema.id
                    )
                    .where(
                        ArtifactVersionSchema.artifact_id == ArtifactSchema.id
                    )
                    .where(
                        ArtifactSchema.name
                        == model_version_artifact_link_name_or_id
                    )
                )

            model_version_artifact_link = session.exec(query).first()
            if model_version_artifact_link is None:
                raise KeyError(
                    f"Unable to delete model version link with name or ID "
                    f"`{model_version_artifact_link_name_or_id}`: "
                    f"No model version link with this name found."
                )

            session.delete(model_version_artifact_link)
            session.commit()

    def delete_all_model_version_artifact_links(
        self,
        model_version_id: UUID,
        only_links: bool = True,
    ) -> None:
        """Deletes all model version to artifact links.

        Args:
            model_version_id: ID of the model version containing the link.
            only_links: Whether to only delete the link to the artifact.
        """
        with Session(self.engine) as session:
            if not only_links:
                artifact_version_ids = session.execute(
                    select(
                        ModelVersionArtifactSchema.artifact_version_id
                    ).where(
                        ModelVersionArtifactSchema.model_version_id
                        == model_version_id
                    )
                ).fetchall()
                session.execute(
                    delete(ArtifactVersionSchema).where(
                        col(ArtifactVersionSchema.id).in_(
                            [a[0] for a in artifact_version_ids]
                        )
                    ),
                )
            session.execute(
                delete(ModelVersionArtifactSchema).where(
                    ModelVersionArtifactSchema.model_version_id  # type: ignore[arg-type]
                    == model_version_id
                )
            )

            session.commit()

    # ---------------------- Model Versions Pipeline Runs ----------------------

    def create_model_version_pipeline_run_link(
        self,
        model_version_pipeline_run_link: ModelVersionPipelineRunRequest,
    ) -> ModelVersionPipelineRunResponse:
        """Creates a new model version to pipeline run link.

        Args:
            model_version_pipeline_run_link: the Model Version to Pipeline Run
                Link to be created.

        Returns:
            - If Model Version to Pipeline Run Link already exists - returns
                the existing link.
            - Otherwise, returns the newly created model version to pipeline
                run link.
        """
        with Session(self.engine) as session:
            self._set_request_user_id(
                request_model=model_version_pipeline_run_link, session=session
            )

            # If the link already exists, return it
            existing_model_version_pipeline_run_link = session.exec(
                select(ModelVersionPipelineRunSchema)
                .where(
                    ModelVersionPipelineRunSchema.model_version_id
                    == model_version_pipeline_run_link.model_version
                )
                .where(
                    ModelVersionPipelineRunSchema.pipeline_run_id
                    == model_version_pipeline_run_link.pipeline_run,
                )
            ).first()
            if existing_model_version_pipeline_run_link is not None:
                return existing_model_version_pipeline_run_link.to_model()

            # Otherwise, create a new link
            model_version_pipeline_run_link_schema = (
                ModelVersionPipelineRunSchema.from_request(
                    model_version_pipeline_run_link
                )
            )
            session.add(model_version_pipeline_run_link_schema)
            session.commit()
            return model_version_pipeline_run_link_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def list_model_version_pipeline_run_links(
        self,
        model_version_pipeline_run_link_filter_model: ModelVersionPipelineRunFilter,
        hydrate: bool = False,
    ) -> Page[ModelVersionPipelineRunResponse]:
        """Get all model version to pipeline run links by filter.

        Args:
            model_version_pipeline_run_link_filter_model: All filter parameters
                including pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all model version to pipeline run links.
        """
        query = select(ModelVersionPipelineRunSchema)
        with Session(self.engine) as session:
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ModelVersionPipelineRunSchema,
                filter_model=model_version_pipeline_run_link_filter_model,
                hydrate=hydrate,
            )

    def delete_model_version_pipeline_run_link(
        self,
        model_version_id: UUID,
        model_version_pipeline_run_link_name_or_id: Union[str, UUID],
    ) -> None:
        """Deletes a model version to pipeline run link.

        Args:
            model_version_id: name or ID of the model version containing the
                link.
            model_version_pipeline_run_link_name_or_id: name or ID of the model
                version to pipeline run link to be deleted.

        Raises:
            KeyError: specified ID not found.
        """
        with Session(self.engine) as session:
            model_version = self.get_model_version(
                model_version_id=model_version_id
            )
            query = select(ModelVersionPipelineRunSchema).where(
                ModelVersionPipelineRunSchema.model_version_id
                == model_version.id
            )
            try:
                UUID(str(model_version_pipeline_run_link_name_or_id))
                query = query.where(
                    ModelVersionPipelineRunSchema.id
                    == model_version_pipeline_run_link_name_or_id
                )
            except ValueError:
                query = query.where(
                    ModelVersionPipelineRunSchema.pipeline_run_id
                    == PipelineRunSchema.id
                ).where(
                    PipelineRunSchema.name
                    == model_version_pipeline_run_link_name_or_id
                )

            model_version_pipeline_run_link = session.exec(query).first()
            if model_version_pipeline_run_link is None:
                raise KeyError(
                    f"Unable to delete model version link with name "
                    f"`{model_version_pipeline_run_link_name_or_id}`: "
                    f"No model version link with this name found."
                )

            session.delete(model_version_pipeline_run_link)
            session.commit()

    # ---------------------------------- Tags ----------------------------------

    @staticmethod
    def _get_taggable_resource_type(
        resource: BaseSchema,
    ) -> TaggableResourceTypes:
        """Get the taggable resource type for a given resource.

        Args:
            resource: The resource to get the taggable resource type for.

        Returns:
            The taggable resource type for the given resource.

        Raises:
            ValueError: If the resource type is not taggable.
        """
        resource_types: Dict[Type[BaseSchema], TaggableResourceTypes] = {
            ArtifactSchema: TaggableResourceTypes.ARTIFACT,
            ArtifactVersionSchema: TaggableResourceTypes.ARTIFACT_VERSION,
            ModelSchema: TaggableResourceTypes.MODEL,
            ModelVersionSchema: TaggableResourceTypes.MODEL_VERSION,
            PipelineSchema: TaggableResourceTypes.PIPELINE,
            PipelineRunSchema: TaggableResourceTypes.PIPELINE_RUN,
            RunTemplateSchema: TaggableResourceTypes.RUN_TEMPLATE,
        }
        if type(resource) not in resource_types:
            raise ValueError(
                f"Resource type {type(resource)} is not taggable."
            )

        return resource_types[type(resource)]

    @staticmethod
    def _get_schema_from_resource_type(
        resource_type: TaggableResourceTypes,
    ) -> Any:
        """Get the schema for a resource type.

        Args:
            resource_type: The type of the resource.

        Returns:
            The schema for the resource type.
        """
        from zenml.zen_stores.schemas import (
            ArtifactSchema,
            ArtifactVersionSchema,
            ModelSchema,
            ModelVersionSchema,
            PipelineRunSchema,
            PipelineSchema,
            RunTemplateSchema,
        )

        resource_type_to_schema_mapping: Dict[
            TaggableResourceTypes, Type[BaseSchema]
        ] = {
            TaggableResourceTypes.ARTIFACT: ArtifactSchema,
            TaggableResourceTypes.ARTIFACT_VERSION: ArtifactVersionSchema,
            TaggableResourceTypes.MODEL: ModelSchema,
            TaggableResourceTypes.MODEL_VERSION: ModelVersionSchema,
            TaggableResourceTypes.PIPELINE: PipelineSchema,
            TaggableResourceTypes.PIPELINE_RUN: PipelineRunSchema,
            TaggableResourceTypes.RUN_TEMPLATE: RunTemplateSchema,
        }

        return resource_type_to_schema_mapping[resource_type]

    def _get_tag_schema(
        self,
        tag_name_or_id: Union[str, UUID],
        session: Session,
    ) -> TagSchema:
        """Gets a tag schema by name or ID.

        This is a helper method that is used in various places to find a tag
        by its name or ID.

        Args:
            tag_name_or_id: The name or ID of the tag to get.
            session: The database session to use.

        Returns:
            The tag schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=tag_name_or_id,
            schema_class=TagSchema,
            session=session,
        )

    def _attach_tags_to_resources(
        self,
        tags: Optional[Sequence[Union[str, tag_utils.Tag]]],
        resources: Union[BaseSchema, List[BaseSchema]],
        session: Session,
    ) -> None:
        """Attaches multiple tags to multiple resources.

        Args:
            tags: The list of tags to attach.
            resources: The list of resources to attach the tags to.
            session: The database session to use.

        Raises:
            ValueError: If a tag exists but doesn't match the same exclusive
                setting.
        """
        if tags is None:
            return

        tag_schemas = []
        for tag in tags:
            # Check if the tag is a string that can be converted to a UUID
            if isinstance(tag, str):
                try:
                    tag_uuid = UUID(tag)
                except ValueError:
                    # Not a valid UUID string, proceed normally
                    pass
                else:
                    tag_schema = self._get_schema_by_id(
                        resource_id=tag_uuid,
                        schema_class=TagSchema,
                        session=session,
                    )
                    tag_schemas.append(tag_schema)
                    continue

            try:
                if isinstance(tag, tag_utils.Tag):
                    tag_request = tag.to_request()
                else:
                    tag_request = TagRequest(name=tag)

                tag_schemas.append(
                    self._create_tag_schema(
                        tag=tag_request,
                        session=session,
                    )
                )
            except EntityExistsError:
                if isinstance(tag, tag_utils.Tag):
                    tag_schema = self._get_tag_schema(tag.name, session)
                    if bool(tag.exclusive) != tag_schema.exclusive:
                        raise ValueError(
                            f"Tag `{tag_schema.name}` has been defined as "
                            f"{'an exclusive' if tag_schema.exclusive else 'a non-exclusive'} "
                            "tag. Please update it before attaching it to resources."
                        )
                else:
                    tag_schema = self._get_tag_schema(tag, session)

                tag_schemas.append(tag_schema)

        resources = (
            [resources] if isinstance(resources, BaseSchema) else resources
        )

        tag_resources: List[
            Tuple[TagSchema, TaggableResourceTypes, BaseSchema]
        ] = []

        for resource in resources:
            resource_type = self._get_taggable_resource_type(resource=resource)
            for tag_schema in tag_schemas:
                tag_resources.append((tag_schema, resource_type, resource))

        self._create_tag_resource_schemas(
            tag_resources=tag_resources, session=session
        )

    def _detach_tags_from_resources(
        self,
        tags: Optional[Sequence[Union[str, UUID, tag_utils.Tag]]],
        resources: Union[BaseSchema, List[BaseSchema]],
        session: Session,
    ) -> None:
        """Detaches multiple tags from multiple resources.

        Args:
            tags: The list of tags to detach.
            resources: The list of resources to detach the tags from.
            session: The database session to use.
        """
        if tags is None:
            return

        tag_schemas = []
        for tag in tags:
            try:
                if isinstance(tag, tag_utils.Tag):
                    tag_schemas.append(self._get_tag_schema(tag.name, session))
                else:
                    tag_schemas.append(
                        self._get_tag_schema(
                            tag_name_or_id=tag, session=session
                        )
                    )
            except KeyError:
                continue

        resources = (
            [resources] if isinstance(resources, BaseSchema) else resources
        )

        tag_resources = []

        for tag_schema in tag_schemas:
            for resource in resources:
                resource_type = self._get_taggable_resource_type(
                    resource=resource
                )
                tag_resources.append(
                    TagResourceRequest(
                        tag_id=tag_schema.id,
                        resource_id=resource.id,
                        resource_type=resource_type,
                    )
                )

        self._delete_tag_resource_schemas(
            tag_resources=tag_resources, session=session
        )

    def _create_tag_schema(
        self, tag: TagRequest, session: Session
    ) -> TagSchema:
        """Creates a new tag schema.

        Args:
            session: The database session to use.
            tag: the tag to be created.

        Returns:
            The newly created tag schema.

        Raises:
            EntityExistsError: If a tag with the same name
                already exists.
        """
        validate_name(tag)
        self._set_request_user_id(request_model=tag, session=session)

        tag_schema = TagSchema.from_request(tag)
        session.add(tag_schema)

        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            raise EntityExistsError(
                f"Tag with name `{tag.name}` already exists."
            )
        return tag_schema

    @track_decorator(AnalyticsEvent.CREATED_TAG)
    def create_tag(self, tag: TagRequest) -> TagResponse:
        """Creates a new tag.

        Args:
            tag: the tag to be created.

        Returns:
            The newly created tag.
        """
        with Session(self.engine) as session:
            tag_schema = self._create_tag_schema(tag=tag, session=session)
            return tag_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_tag(
        self,
        tag_name_or_id: Union[str, UUID],
    ) -> None:
        """Deletes a tag.

        Args:
            tag_name_or_id: name or id of the tag to delete.
        """
        with Session(self.engine) as session:
            tag = self._get_tag_schema(
                tag_name_or_id=tag_name_or_id,
                session=session,
            )
            session.delete(tag)
            session.commit()

    def get_tag(
        self,
        tag_name_or_id: Union[str, UUID],
        hydrate: bool = True,
    ) -> TagResponse:
        """Get an existing tag.

        Args:
            tag_name_or_id: name or id of the tag to be retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The tag of interest.
        """
        with Session(self.engine) as session:
            tag = self._get_tag_schema(
                tag_name_or_id=tag_name_or_id,
                session=session,
            )
            return tag.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_tags(
        self,
        tag_filter_model: TagFilter,
        hydrate: bool = False,
    ) -> Page[TagResponse]:
        """Get all tags by filter.

        Args:
            tag_filter_model: All filter parameters including pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all tags.
        """
        with Session(self.engine) as session:
            query = select(TagSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=TagSchema,
                filter_model=tag_filter_model,
                hydrate=hydrate,
            )

    def update_tag(
        self,
        tag_name_or_id: Union[str, UUID],
        tag_update_model: TagUpdate,
    ) -> TagResponse:
        """Update tag.

        Args:
            tag_name_or_id: name or id of the tag to be updated.
            tag_update_model: Tag to use for the update.

        Returns:
            An updated tag.

        Raises:
            ValueError: If the tag can not be converted to an exclusive tag due
                to it being associated to multiple entities.
        """
        with Session(self.engine) as session:
            tag = self._get_tag_schema(
                tag_name_or_id=tag_name_or_id,
                session=session,
            )
            self._verify_name_uniqueness(
                resource=tag_update_model,
                schema=tag,
                session=session,
            )

            if tag_update_model.exclusive is True:
                error_messages = []

                # Define allowed resource types for exclusive tags
                allowed_resource_types = [
                    TaggableResourceTypes.PIPELINE_RUN.value,
                    TaggableResourceTypes.ARTIFACT_VERSION.value,
                    TaggableResourceTypes.RUN_TEMPLATE.value,
                ]

                # Check if tag is associated with any non-allowed resource types
                non_allowed_resources_query = (
                    select(TagResourceSchema.resource_type)
                    .where(
                        TagResourceSchema.tag_id == tag.id,
                        TagResourceSchema.resource_type.not_in(  # type: ignore[attr-defined]
                            allowed_resource_types
                        ),
                    )
                    .distinct()
                )

                non_allowed_resources = session.exec(
                    non_allowed_resources_query
                ).all()
                if non_allowed_resources:
                    error_message = (
                        f"The tag `{tag.name}` cannot be made "
                        "exclusive because it is associated with "
                        "non-allowed resource types: "
                        f"{', '.join(non_allowed_resources)}. "
                        "Exclusive tags can only be applied "
                        "to pipeline runs, artifact versions, "
                        "and run templates."
                    )
                    error_messages.append(error_message)

                for resource_type, resource_id, scope_id in [
                    (
                        TaggableResourceTypes.PIPELINE_RUN,
                        PipelineRunSchema.id,
                        PipelineRunSchema.pipeline_id,
                    ),
                    (
                        TaggableResourceTypes.ARTIFACT_VERSION,
                        ArtifactVersionSchema.id,
                        ArtifactVersionSchema.artifact_id,
                    ),
                    (
                        TaggableResourceTypes.RUN_TEMPLATE,
                        RunTemplateSchema.id,
                        None,  # Special case - will be handled differently
                    ),
                ]:
                    # Special handling for run templates as they don't have direct pipeline_id
                    if resource_type == TaggableResourceTypes.RUN_TEMPLATE:
                        query = (
                            select(
                                PipelineDeploymentSchema.pipeline_id,
                                func.count().label("count"),
                            )
                            .select_from(RunTemplateSchema)
                            .join(
                                TagResourceSchema,
                                and_(
                                    TagResourceSchema.resource_id
                                    == RunTemplateSchema.id,
                                    TagResourceSchema.resource_type
                                    == "run_template",
                                ),
                            )
                            .join(
                                PipelineDeploymentSchema,
                                RunTemplateSchema.source_deployment_id  # type: ignore[arg-type]
                                == PipelineDeploymentSchema.id,
                            )
                            .where(TagResourceSchema.tag_id == tag.id)
                            .group_by(PipelineDeploymentSchema.pipeline_id)  # type: ignore[arg-type]
                        )

                        results = session.exec(query).all()
                        conflicts = [k for k, v in results if v > 1]
                        if conflicts:
                            error_message = (
                                f"The tag `{tag.name}` is associated with multiple entries of "
                                f"`{resource_type.value}`s that share the same pipeline_id"
                            )
                            error_message += f": {conflicts}"
                            error_messages.append(error_message)
                    else:
                        check, error = self._exclusive_check_for_existing_tags(
                            tag=tag,
                            session=session,
                            resource_type=resource_type,
                            resource_id_column=resource_id,
                            scope_id_column=scope_id,
                        )
                        if check is False:
                            error_messages.append(error)

                if error_messages:
                    raise ValueError(
                        "\n".join(error_messages)
                        + "\nYou can only convert a tag into an exclusive tag "
                        "if the conflicts mentioned above are resolved."
                    )

            tag.update(update=tag_update_model)
            session.add(tag)
            session.commit()

            # Refresh the tag that was just created
            session.refresh(tag)
            return tag.to_model(include_metadata=True, include_resources=True)

    @staticmethod
    def _exclusive_check_for_existing_tags(
        tag: TagSchema,
        session: Session,
        resource_type: TaggableResourceTypes,
        resource_id_column: Any,
        scope_id_column: Any,
    ) -> Tuple[bool, str]:
        query = (
            select(scope_id_column, func.count().label("count"))
            .join(
                TagResourceSchema,
                and_(
                    TagResourceSchema.resource_id == resource_id_column,
                    TagResourceSchema.resource_type == resource_type,
                ),
            )
            .where(TagResourceSchema.tag_id == tag.id)
            .group_by(scope_id_column)
        )
        results = session.exec(query).all()
        conflicts = [k for k, v in results if v > 1]
        if conflicts:
            error_message = (
                f"The tag `{tag.name}` is associated with multiple entries of "
                f"`{resource_type.value}`s"
            )

            if resource_id_column != scope_id_column:
                error_message += (
                    f" that share the same `{scope_id_column.name}`s"
                )
            error_message += f": {conflicts}"
            return False, error_message

        return True, ""

    def _get_tag_resource_schema(
        self,
        tag_resource: TagResourceRequest,
        session: Session,
    ) -> TagResourceSchema:
        """Gets a tag model schema.

        Args:
            tag_resource: The tag resource to get.
            session: The database session to use.

        Returns:
            The tag resource schema.

        Raises:
            KeyError: if a relationship between the tag and the resource does
                not exist.
        """
        schema = session.exec(
            select(TagResourceSchema).where(
                TagResourceSchema.tag_id == tag_resource.tag_id,
                TagResourceSchema.resource_id == tag_resource.resource_id,
                TagResourceSchema.resource_type
                == tag_resource.resource_type.value,
            )
        ).first()
        if schema is None:
            raise KeyError(
                f"Tag `{tag_resource.tag_id}` is not currently assigned to "
                f"{tag_resource.resource_type.value} with ID "
                f"`{tag_resource.resource_id}`."
            )
        return schema

    def _create_tag_resource_schemas(
        self,
        tag_resources: List[
            Tuple[TagSchema, TaggableResourceTypes, BaseSchema]
        ],
        session: Session,
    ) -> List[TagResourceSchema]:
        """Creates a set of tag resource relationships.

        Args:
            tag_resources: the tag resource relationships to be created.
            session: The database session to use.

        Returns:
            The newly created tag resource relationships.

        Raises:
            ValueError: If an exclusive tag is being attached
                to multiple resources of the same type within the same scope.
            EntityExistsError: If a tag resource already exists.
        """
        max_retries = 10

        for _ in range(max_retries):
            tag_resource_schemas = []
            tag_resources_to_create: Set[
                Tuple[UUID, UUID, TaggableResourceTypes]
            ] = set()

            for tag_schema, resource_type, resource in tag_resources:
                if (
                    tag_schema.id,
                    resource.id,
                    resource_type,
                ) in tag_resources_to_create:
                    continue
                try:
                    existing_schema = self._get_tag_resource_schema(
                        tag_resource=TagResourceRequest(
                            tag_id=tag_schema.id,
                            resource_id=resource.id,
                            resource_type=resource_type,
                        ),
                        session=session,
                    )
                except KeyError:
                    pass
                else:
                    logger.debug(
                        f"Tag `{tag_schema.name}` is already assigned to "
                        f"{resource_type.value} with ID: `{resource.id}`."
                    )
                    tag_resource_schemas.append(existing_schema)
                    continue

                tag_resource_schema = TagResourceSchema.from_request(
                    TagResourceRequest(
                        tag_id=tag_schema.id,
                        resource_id=resource.id,
                        resource_type=resource_type,
                    )
                )
                session.add(tag_resource_schema)
                tag_resource_schemas.append(tag_resource_schema)

                # If the tag is an exclusive tag, apply the check and attach/detach accordingly
                if tag_schema.exclusive:
                    scope_ids: Dict[
                        TaggableResourceTypes, List[Union[UUID, int]]
                    ] = defaultdict(list)
                    detach_resources: List[TagResourceRequest] = []

                    if isinstance(resource, PipelineRunSchema):
                        if resource.pipeline_id:
                            scope_ids[
                                TaggableResourceTypes.PIPELINE_RUN
                            ].append(resource.pipeline_id)

                            other_runs_with_same_tag = self.list_runs(
                                PipelineRunFilter(
                                    id=f"notequals:{resource.id}",
                                    pipeline_id=resource.pipeline_id,
                                    tags=[tag_schema.name],
                                )
                            )
                            if other_runs_with_same_tag.items:
                                detach_resources.append(
                                    TagResourceRequest(
                                        tag_id=tag_schema.id,
                                        resource_id=other_runs_with_same_tag.items[
                                            0
                                        ].id,
                                        resource_type=TaggableResourceTypes.PIPELINE_RUN,
                                    )
                                )
                    elif isinstance(resource, ArtifactVersionSchema):
                        if resource.artifact_id:
                            scope_ids[
                                TaggableResourceTypes.ARTIFACT_VERSION
                            ].append(resource.artifact_id)

                            other_versions_with_same_tag = (
                                self.list_artifact_versions(
                                    ArtifactVersionFilter(
                                        id=f"notequals:{resource.id}",
                                        artifact_id=resource.artifact_id,
                                        tags=[tag_schema.name],
                                    )
                                )
                            )
                            if other_versions_with_same_tag.items:
                                detach_resources.append(
                                    TagResourceRequest(
                                        tag_id=tag_schema.id,
                                        resource_id=other_versions_with_same_tag.items[
                                            0
                                        ].id,
                                        resource_type=TaggableResourceTypes.ARTIFACT_VERSION,
                                    )
                                )
                    elif isinstance(resource, RunTemplateSchema):
                        scope_id = None
                        if resource.source_deployment:
                            if resource.source_deployment.pipeline_id:
                                scope_id = (
                                    resource.source_deployment.pipeline_id
                                )
                                scope_ids[
                                    TaggableResourceTypes.RUN_TEMPLATE
                                ].append(scope_id)

                                older_templates = self.list_run_templates(
                                    RunTemplateFilter(
                                        id=f"notequals:{resource.id}",
                                        pipeline_id=scope_id,
                                        tags=[tag_schema.name],
                                    )
                                )
                                if older_templates.items:
                                    detach_resources.append(
                                        TagResourceRequest(
                                            tag_id=tag_schema.id,
                                            resource_id=older_templates.items[
                                                0
                                            ].id,
                                            resource_type=TaggableResourceTypes.RUN_TEMPLATE,
                                        )
                                    )
                    else:
                        raise ValueError(
                            "Can not attach exclusive tag to resource of type "
                            f"{resource_type.value} with ID: `{resource.id}`. "
                            "Exclusive tag functionality only works for "
                            "templates, for pipeline runs (within the scope of "
                            "pipelines) and for artifact versions (within the "
                            "scope of artifacts)."
                        )

                    # Check for duplicate IDs in any of the scope_ids list
                    for resource_type, id_list in scope_ids.items():
                        if len(id_list) != len(set(id_list)):
                            raise ValueError(
                                f"You are trying to attach an exclusive tag to "
                                f"multiple {resource_type.value}s within the "
                                "same scope. This is not allowed."
                            )

                    if detach_resources:
                        self._delete_tag_resource_schemas(
                            tag_resources=detach_resources,
                            session=session,
                            # Don't commit the session here, because we want
                            # to have one big mega-transaction.
                            commit=False,
                        )

                tag_resources_to_create.add(
                    (tag_schema.id, resource.id, resource_type)
                )
            try:
                session.commit()
            except IntegrityError:
                session.rollback()
                continue
            else:
                break
        else:
            raise EntityExistsError(
                f"Failed to create tag resources after {max_retries} retries. "
                "Some of the tag resources already exist. Please try again later."
            )
        return tag_resource_schemas

    def create_tag_resource(
        self, tag_resource: TagResourceRequest
    ) -> TagResourceResponse:
        """Creates a new tag resource relationship.

        Args:
            tag_resource: the tag resource relationship to be created.

        Returns:
            The newly created tag resource relationship.
        """
        return self.batch_create_tag_resource(tag_resources=[tag_resource])[0]

    def batch_create_tag_resource(
        self, tag_resources: List[TagResourceRequest]
    ) -> List[TagResourceResponse]:
        """Create a batch of tag resource relationships.

        Args:
            tag_resources: The tag resource relationships to be created.

        Returns:
            The newly created tag resource relationships.
        """
        with Session(self.engine) as session:
            resources: List[
                Tuple[TagSchema, TaggableResourceTypes, BaseSchema]
            ] = []
            for tag_resource in tag_resources:
                resource_schema = self._get_schema_from_resource_type(
                    tag_resource.resource_type
                )
                resource = self._get_schema_by_id(
                    resource_id=tag_resource.resource_id,
                    schema_class=resource_schema,
                    session=session,
                )
                tag_schema = self._get_tag_schema(
                    tag_name_or_id=tag_resource.tag_id,
                    session=session,
                )
                resources.append(
                    (
                        tag_schema,
                        tag_resource.resource_type,
                        resource,
                    )
                )
            return [
                r.to_model()
                for r in self._create_tag_resource_schemas(
                    tag_resources=resources, session=session
                )
            ]

    def _delete_tag_resource_schemas(
        self,
        tag_resources: List[TagResourceRequest],
        session: Session,
        commit: bool = True,
    ) -> None:
        """Deletes a set of tag resource relationships.

        Args:
            tag_resources: The set of tag resource relationships to delete.
            session: The database session to use.
            commit: Whether to commit the session after deleting the tag
                resource relationships.
        """
        for tag_resource in tag_resources:
            try:
                tag_resource_schema = self._get_tag_resource_schema(
                    tag_resource=tag_resource,
                    session=session,
                )
            except KeyError:
                logger.warning(
                    f"Tag `{tag_resource.tag_id}` is not currently assigned to "
                    f"{tag_resource.resource_type.value} with ID "
                    f"`{tag_resource.resource_id}`."
                )
                continue
            else:
                session.delete(tag_resource_schema)

        if commit:
            session.commit()

    def delete_tag_resource(
        self,
        tag_resource: TagResourceRequest,
    ) -> None:
        """Deletes a tag resource relationship.

        Args:
            tag_resource: The tag resource relationship to delete.
        """
        self.batch_delete_tag_resource(tag_resources=[tag_resource])

    def batch_delete_tag_resource(
        self, tag_resources: List[TagResourceRequest]
    ) -> None:
        """Delete a batch of tag resource relationships.

        Args:
            tag_resources: The tag resource relationships to be deleted.
        """
        with Session(self.engine) as session:
            self._delete_tag_resource_schemas(
                tag_resources=tag_resources,
                session=session,
            )
