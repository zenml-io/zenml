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
import json
import logging
import math
import os
import random
import re
import sys
import time
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    ForwardRef,
    List,
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
from sqlalchemy import asc, case, desc, func
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import (
    ArgumentError,
    IntegrityError,
    NoResultFound,
)
from sqlalchemy.orm import Mapped, noload
from sqlalchemy.util import immutabledict
from sqlmodel import (
    Session,
    SQLModel,
    and_,
    col,
    create_engine,
    delete,
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
from zenml.config.pipeline_run_configuration import PipelineRunConfiguration
from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.config.server_config import ServerConfiguration
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
    SORT_PIPELINES_BY_LATEST_RUN_KEY,
    SQL_STORE_BACKUP_DIRECTORY_NAME,
    TEXT_FIELD_MAX_LENGTH,
    handle_bool_env_var,
    is_false_string_value,
    is_true_string_value,
)
from zenml.enums import (
    AuthScheme,
    DatabaseBackupStrategy,
    ExecutionStatus,
    LoggingLevels,
    MetadataResourceTypes,
    ModelStages,
    OnboardingStep,
    SecretScope,
    SecretsStoreType,
    SorterOps,
    StackComponentType,
    StackDeploymentProvider,
    StepRunInputArtifactType,
    StoreType,
    TaggableResourceTypes,
)
from zenml.exceptions import (
    ActionExistsError,
    AuthorizationException,
    BackupSecretsStoreNotConfiguredError,
    EntityCreationError,
    EntityExistsError,
    EventSourceExistsError,
    IllegalOperationError,
    SecretsStoreNotConfiguredError,
    StackComponentExistsError,
    StackExistsError,
    TriggerExistsError,
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
    BaseResponse,
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
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineRunResponse,
    PipelineRunUpdate,
    PipelineUpdate,
    RunMetadataFilter,
    RunMetadataRequest,
    RunMetadataResponse,
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
    UserUpdate,
    WorkspaceFilter,
    WorkspaceRequest,
    WorkspaceResponse,
    WorkspaceUpdate,
)
from zenml.models.v2.core.component import InternalComponentRequest
from zenml.service_connectors.service_connector_registry import (
    service_connector_registry,
)
from zenml.stack.flavor_registry import FlavorRegistry
from zenml.stack_deployments.utils import get_stack_deployment_class
from zenml.utils import uuid_utils
from zenml.utils.enum_utils import StrEnum
from zenml.utils.networking_utils import (
    replace_localhost_with_internal_hostname,
)
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.utils.string_utils import random_str, validate_name
from zenml.zen_stores import template_utils
from zenml.zen_stores.base_zen_store import (
    BaseZenStore,
)
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
    WorkspaceSchema,
)
from zenml.zen_stores.schemas.artifact_visualization_schemas import (
    ArtifactVisualizationSchema,
)
from zenml.zen_stores.schemas.logs_schemas import LogsSchema
from zenml.zen_stores.schemas.service_schemas import ServiceSchema
from zenml.zen_stores.schemas.trigger_schemas import TriggerSchema
from zenml.zen_stores.secrets_stores.base_secrets_store import BaseSecretsStore
from zenml.zen_stores.secrets_stores.sql_secrets_store import (
    SqlSecretsStoreConfiguration,
)

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
    username: Optional[str] = None
    password: Optional[str] = None
    ssl_ca: Optional[str] = None
    ssl_cert: Optional[str] = None
    ssl_key: Optional[str] = None
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

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def _remove_grpc_attributes(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Removes old GRPC attributes.

        Args:
            data: All model attribute values.

        Returns:
            The model attribute values
        """
        grpc_attribute_keys = [
            "grpc_metadata_host",
            "grpc_metadata_port",
            "grpc_metadata_ssl_ca",
            "grpc_metadata_ssl_key",
            "grpc_metadata_ssl_cert",
        ]
        grpc_values = [data.pop(key, None) for key in grpc_attribute_keys]
        if any(grpc_values):
            logger.warning(
                "The GRPC attributes %s are unused and will be removed soon. "
                "Please remove them from SQLZenStore configuration. This will "
                "become an error in future versions of ZenML."
            )

        return data

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
                self.username = sql_url.username
                sql_url = sql_url._replace(username=None)
            if sql_url.password:
                self.password = sql_url.password
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
                    if k == "ssl_ca":
                        if r := _get_query_result(v):
                            self.ssl_ca = r
                    elif k == "ssl_cert":
                        if r := _get_query_result(v):
                            self.ssl_cert = r
                    elif k == "ssl_key":
                        if r := _get_query_result(v):
                            self.ssl_key = r
                    elif k == "ssl_verify_server_cert":
                        if r := _get_query_result(v):
                            if is_true_string_value(r):
                                self.ssl_verify_server_cert = True
                            elif is_false_string_value(r):
                                self.ssl_verify_server_cert = False
                    else:
                        raise ValueError(
                            "Invalid MySQL URL query parameter `%s`: The "
                            "parameter must be one of: ssl_ca, ssl_cert, "
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
                if content and not os.path.isfile(content):
                    fileio.makedirs(str(secret_folder))
                    file_path = Path(secret_folder, f"{key}.pem")
                    with os.fdopen(
                        os.open(
                            file_path, flags=os.O_RDWR | os.O_CREAT, mode=0o600
                        ),
                        "w",
                    ) as f:
                        f.write(content)
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

    def expand_certificates(self) -> None:
        """Expands the certificates in the verify_ssl field."""
        # Load the certificate values back into the configuration
        for key in ["ssl_key", "ssl_ca", "ssl_cert"]:
            file_path = getattr(self, key, None)
            if file_path and os.path.isfile(file_path):
                with open(file_path, "r") as f:
                    setattr(self, key, f.read())

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
                username=self.username,
                password=self.password,
                database=database,
            )

            sqlalchemy_ssl_args: Dict[str, Any] = {}

            # Handle SSL params
            for key in ["ssl_key", "ssl_ca", "ssl_cert"]:
                ssl_setting = getattr(self, key)
                if not ssl_setting:
                    continue
                if not os.path.isfile(ssl_setting):
                    logger.warning(
                        f"Database SSL setting `{key}` is not a file. "
                    )
                sqlalchemy_ssl_args[key.lstrip("ssl_")] = ssl_setting
            if len(sqlalchemy_ssl_args) > 0:
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
        extra="forbid",
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
            # Do not send events for cloud tenants where the event comes from
            # the cloud API
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

        Returns:
            The Domain Model representation of the DB resource

        Raises:
            ValueError: if the filtered page number is out of bounds.
            RuntimeError: if the schema does not have a `to_model` method.
        """
        query = filter_model.apply_filter(query=query, table=table)
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

        # Sorting
        query = filter_model.apply_sorting(query=query, table=table)

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
            item_schemas = session.exec(
                query.limit(filter_model.size).offset(filter_model.offset)
            ).all()

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
        # Make sure the default workspace exists
        self._get_or_create_default_workspace()
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
                        f"Failed to cleanup database dump file "
                        f"{dump_file}."
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
                tzinfo=timezone.utc
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

    def _fail_if_action_with_name_exists(
        self, action_name: str, workspace_id: UUID, session: Session
    ) -> None:
        """Raise an exception if an action with same name exists.

        Args:
            action_name: The name of the action.
            workspace_id: Workspace ID of the action.
            session: DB Session.

        Raises:
            ActionExistsError: If an action with the given name already exists.
        """
        existing_domain_action = session.exec(
            select(ActionSchema)
            .where(ActionSchema.name == action_name)
            .where(ActionSchema.workspace_id == workspace_id)
        ).first()
        if existing_domain_action is not None:
            workspace = self._get_workspace_schema(
                workspace_name_or_id=workspace_id, session=session
            )
            raise ActionExistsError(
                f"Unable to register action with name "
                f"'{action_name}': Found an existing action with "
                f"the same name in the active workspace, '{workspace.name}'."
            )

    def create_action(self, action: ActionRequest) -> ActionResponse:
        """Create an action.

        Args:
            action: The action to create.

        Returns:
            The created action.
        """
        with Session(self.engine) as session:
            self._fail_if_action_with_name_exists(
                action_name=action.name,
                workspace_id=action.workspace,
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

    def _get_action(
        self,
        action_id: UUID,
        session: Session,
    ) -> ActionSchema:
        """Get an action by ID.

        Args:
            action_id: The ID of the action to get.
            session: The DB session.

        Returns:
            The action schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=action_id,
            schema_class=ActionSchema,
            schema_name="action",
            session=session,
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
            action = self._get_action(action_id=action_id, session=session)

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
            action = self._get_action(session=session, action_id=action_id)

            if action_update.service_account_id:
                # Verify that the given service account exists
                self._get_account_schema(
                    account_name_or_id=action_update.service_account_id,
                    session=session,
                    service_account=True,
                )

            # In case of a renaming update, make sure no action already exists
            # with that name
            if action_update.name:
                if action.name != action_update.name:
                    self._fail_if_action_with_name_exists(
                        action_name=action_update.name,
                        workspace_id=action.workspace.id,
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
            action = self._get_action(action_id=action_id, session=session)

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
        # Check if service with the same domain key (name, config, workspace)
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
            # Check if a service with the given name already exists
            self._fail_if_service_with_config_exists(
                service_request=service,
                session=session,
            )

            # Create the service.
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

        Raises:
            KeyError: if the service doesn't exist.
        """
        with Session(self.engine) as session:
            service = session.exec(
                select(ServiceSchema).where(ServiceSchema.id == service_id)
            ).first()
            if service is None:
                raise KeyError(
                    f"Unable to get service with ID {service_id}: No "
                    "service with this ID found."
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

        Raises:
            KeyError: if the service doesn't exist.
        """
        with Session(self.engine) as session:
            existing_service = session.exec(
                select(ServiceSchema).where(ServiceSchema.id == service_id)
            ).first()
            if not existing_service:
                raise KeyError(f"Service with ID {service_id} not found.")

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

        Raises:
            KeyError: if the service doesn't exist.
        """
        with Session(self.engine) as session:
            existing_service = session.exec(
                select(ServiceSchema).where(ServiceSchema.id == service_id)
            ).first()
            if not existing_service:
                raise KeyError(f"Service with ID {service_id} not found.")

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

        Raises:
            EntityExistsError: If an artifact with the same name already exists.
        """
        validate_name(artifact)
        with Session(self.engine) as session:
            # Check if an artifact with the given name already exists
            existing_artifact = session.exec(
                select(ArtifactSchema).where(
                    ArtifactSchema.name == artifact.name
                )
            ).first()
            if existing_artifact is not None:
                raise EntityExistsError(
                    f"Unable to create artifact with name '{artifact.name}': "
                    "An artifact with the same name already exists."
                )

            # Create the artifact.
            artifact_schema = ArtifactSchema.from_request(artifact)

            # Save tags of the artifact.
            if artifact.tags:
                self._attach_tags_to_resource(
                    tag_names=artifact.tags,
                    resource_id=artifact_schema.id,
                    resource_type=TaggableResourceTypes.ARTIFACT,
                )

            session.add(artifact_schema)
            session.commit()
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

        Raises:
            KeyError: if the artifact doesn't exist.
        """
        with Session(self.engine) as session:
            artifact = session.exec(
                select(ArtifactSchema).where(ArtifactSchema.id == artifact_id)
            ).first()
            if artifact is None:
                raise KeyError(
                    f"Unable to get artifact with ID {artifact_id}: No "
                    "artifact with this ID found."
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

        Raises:
            KeyError: if the artifact doesn't exist.
        """
        with Session(self.engine) as session:
            existing_artifact = session.exec(
                select(ArtifactSchema).where(ArtifactSchema.id == artifact_id)
            ).first()
            if not existing_artifact:
                raise KeyError(f"Artifact with ID {artifact_id} not found.")

            # Handle tag updates.
            if artifact_update.add_tags:
                self._attach_tags_to_resource(
                    tag_names=artifact_update.add_tags,
                    resource_id=existing_artifact.id,
                    resource_type=TaggableResourceTypes.ARTIFACT,
                )
            if artifact_update.remove_tags:
                self._detach_tags_from_resource(
                    tag_names=artifact_update.remove_tags,
                    resource_id=existing_artifact.id,
                    resource_type=TaggableResourceTypes.ARTIFACT,
                )

            # Update the schema itself.
            existing_artifact.update(artifact_update=artifact_update)
            session.add(existing_artifact)
            session.commit()
            session.refresh(existing_artifact)
            return existing_artifact.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_artifact(self, artifact_id: UUID) -> None:
        """Deletes an artifact.

        Args:
            artifact_id: The ID of the artifact to delete.

        Raises:
            KeyError: if the artifact doesn't exist.
        """
        with Session(self.engine) as session:
            existing_artifact = session.exec(
                select(ArtifactSchema).where(ArtifactSchema.id == artifact_id)
            ).first()
            if not existing_artifact:
                raise KeyError(f"Artifact with ID {artifact_id} not found.")
            session.delete(existing_artifact)
            session.commit()

    # -------------------- Artifact Versions --------------------

    def _get_or_create_artifact_for_name(
        self, name: str, has_custom_name: bool
    ) -> ArtifactSchema:
        """Get or create an artifact with a specific name.

        Args:
            name: The artifact name.
            has_custom_name: Whether the artifact has a custom name.

        Returns:
            Schema of the artifact.
        """
        with Session(self.engine) as session:
            artifact_query = select(ArtifactSchema).where(
                ArtifactSchema.name == name
            )
            artifact = session.exec(artifact_query).first()

            if artifact is None:
                try:
                    with session.begin_nested():
                        artifact_request = ArtifactRequest(
                            name=name, has_custom_name=has_custom_name
                        )
                        artifact = ArtifactSchema.from_request(
                            artifact_request
                        )
                        session.add(artifact)
                        session.commit()
                    session.refresh(artifact)
                except IntegrityError:
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
        if artifact_name := artifact_version.artifact_name:
            artifact_schema = self._get_or_create_artifact_for_name(
                name=artifact_name,
                has_custom_name=artifact_version.has_custom_name,
            )
            artifact_version.artifact_id = artifact_schema.id

        assert artifact_version.artifact_id

        artifact_version_id = None

        if artifact_version.version is None:
            # No explicit version in the request -> We will try to
            # auto-increment the numeric version of the artifact version
            remaining_tries = MAX_RETRIES_FOR_VERSIONED_ENTITY_CREATION
            while remaining_tries > 0:
                remaining_tries -= 1
                try:
                    with Session(self.engine) as session:
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
                        artifact_version_id = artifact_version_schema.id
                except IntegrityError:
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
            with Session(self.engine) as session:
                try:
                    artifact_version_schema = (
                        ArtifactVersionSchema.from_request(artifact_version)
                    )
                    session.add(artifact_version_schema)
                    session.commit()
                    artifact_version_id = artifact_version_schema.id
                except IntegrityError:
                    raise EntityExistsError(
                        f"Unable to create artifact version "
                        f"{artifact_schema.name} (version "
                        f"{artifact_version.version}): An artifact with the "
                        "same name and version already exists."
                    )

        assert artifact_version_id

        with Session(self.engine) as session:
            # Save visualizations of the artifact
            if artifact_version.visualizations:
                for vis in artifact_version.visualizations:
                    vis_schema = ArtifactVisualizationSchema.from_model(
                        artifact_visualization_request=vis,
                        artifact_version_id=artifact_version_id,
                    )
                    session.add(vis_schema)

            # Save tags of the artifact
            if artifact_version.tags:
                self._attach_tags_to_resource(
                    tag_names=artifact_version.tags,
                    resource_id=artifact_version_id,
                    resource_type=TaggableResourceTypes.ARTIFACT_VERSION,
                )

            # Save metadata of the artifact
            if artifact_version.metadata:
                for key, value in artifact_version.metadata.items():
                    run_metadata_schema = RunMetadataSchema(
                        workspace_id=artifact_version.workspace,
                        user_id=artifact_version.user,
                        resource_id=artifact_version_id,
                        resource_type=MetadataResourceTypes.ARTIFACT_VERSION,
                        key=key,
                        value=json.dumps(value),
                        type=get_metadata_type(value),
                    )
                    session.add(run_metadata_schema)

            session.commit()
            artifact_version_schema = session.exec(
                select(ArtifactVersionSchema).where(
                    ArtifactVersionSchema.id == artifact_version_id
                )
            ).one()

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

        Raises:
            KeyError: if the artifact version doesn't exist.
        """
        with Session(self.engine) as session:
            artifact_version = session.exec(
                select(ArtifactVersionSchema).where(
                    ArtifactVersionSchema.id == artifact_version_id
                )
            ).first()
            if artifact_version is None:
                raise KeyError(
                    f"Unable to get artifact version with ID "
                    f"{artifact_version_id}: No artifact version with this ID "
                    f"found."
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

        Raises:
            KeyError: if the artifact version doesn't exist.
        """
        with Session(self.engine) as session:
            existing_artifact_version = session.exec(
                select(ArtifactVersionSchema).where(
                    ArtifactVersionSchema.id == artifact_version_id
                )
            ).first()
            if not existing_artifact_version:
                raise KeyError(
                    f"Artifact version with ID {artifact_version_id} not found."
                )

            # Handle tag updates.
            if artifact_version_update.add_tags:
                self._attach_tags_to_resource(
                    tag_names=artifact_version_update.add_tags,
                    resource_id=existing_artifact_version.id,
                    resource_type=TaggableResourceTypes.ARTIFACT_VERSION,
                )
            if artifact_version_update.remove_tags:
                self._detach_tags_from_resource(
                    tag_names=artifact_version_update.remove_tags,
                    resource_id=existing_artifact_version.id,
                    resource_type=TaggableResourceTypes.ARTIFACT_VERSION,
                )

            # Update the schema itself.
            existing_artifact_version.update(
                artifact_version_update=artifact_version_update
            )
            session.add(existing_artifact_version)
            session.commit()
            session.refresh(existing_artifact_version)
            return existing_artifact_version.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_artifact_version(self, artifact_version_id: UUID) -> None:
        """Deletes an artifact version.

        Args:
            artifact_version_id: The ID of the artifact version to delete.

        Raises:
            KeyError: if the artifact version doesn't exist.
        """
        with Session(self.engine) as session:
            artifact_version = session.exec(
                select(ArtifactVersionSchema).where(
                    ArtifactVersionSchema.id == artifact_version_id
                )
            ).first()
            if artifact_version is None:
                raise KeyError(
                    f"Unable to delete artifact version with ID "
                    f"{artifact_version_id}: No artifact version with this ID "
                    "found."
                )
            session.delete(artifact_version)
            session.commit()

    def prune_artifact_versions(
        self,
        only_versions: bool = True,
    ) -> None:
        """Prunes unused artifact versions and their artifacts.

        Args:
            only_versions: Only delete artifact versions, keeping artifacts
        """
        with Session(self.engine) as session:
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

        Raises:
            KeyError: if the code reference doesn't exist.
        """
        with Session(self.engine) as session:
            artifact_visualization = session.exec(
                select(ArtifactVisualizationSchema).where(
                    ArtifactVisualizationSchema.id == artifact_visualization_id
                )
            ).first()
            if artifact_visualization is None:
                raise KeyError(
                    f"Unable to get artifact visualization with ID "
                    f"{artifact_visualization_id}: "
                    f"No artifact visualization with this ID found."
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

        Raises:
            KeyError: if the code reference doesn't exist.
        """
        with Session(self.engine) as session:
            code_reference = session.exec(
                select(CodeReferenceSchema).where(
                    CodeRepositorySchema.id == code_reference_id
                )
            ).first()
            if code_reference is None:
                raise KeyError(
                    f"Unable to get code reference with ID "
                    f"{code_reference_id}: "
                    f"No code reference with this ID found."
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

        Raises:
            EntityExistsError: If a code repository with the given name already
                exists.
        """
        with Session(self.engine) as session:
            existing_repo = session.exec(
                select(CodeRepositorySchema)
                .where(CodeRepositorySchema.name == code_repository.name)
                .where(
                    CodeRepositorySchema.workspace_id
                    == code_repository.workspace
                )
            ).first()
            if existing_repo is not None:
                raise EntityExistsError(
                    f"Unable to create code repository in workspace "
                    f"'{code_repository.workspace}': A code repository with "
                    "this name already exists."
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

        Raises:
            KeyError: If no code repository with the given ID exists.
        """
        with Session(self.engine) as session:
            repo = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.id == code_repository_id
                )
            ).first()
            if repo is None:
                raise KeyError(
                    f"Unable to get code repository with ID "
                    f"'{code_repository_id}': No code repository with this "
                    "ID found."
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

        Raises:
            KeyError: If no code repository with the given name exists.
        """
        with Session(self.engine) as session:
            existing_repo = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.id == code_repository_id
                )
            ).first()
            if existing_repo is None:
                raise KeyError(
                    f"Unable to update code repository with ID "
                    f"{code_repository_id}: No code repository with this ID "
                    "found."
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

        Raises:
            KeyError: If no code repository with the given ID exists.
        """
        with Session(self.engine) as session:
            existing_repo = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.id == code_repository_id
                )
            ).first()
            if existing_repo is None:
                raise KeyError(
                    f"Unable to delete code repository with ID "
                    f"{code_repository_id}: No code repository with this ID "
                    "found."
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

        Raises:
            KeyError: if the stack component references a non-existent
                connector.
        """
        validate_name(component)
        with Session(self.engine) as session:
            self._fail_if_component_with_name_type_exists(
                name=component.name,
                component_type=component.type,
                workspace_id=component.workspace,
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

            service_connector: Optional[ServiceConnectorSchema] = None
            if component.connector:
                service_connector = session.exec(
                    select(ServiceConnectorSchema).where(
                        ServiceConnectorSchema.id == component.connector
                    )
                ).first()

                if service_connector is None:
                    raise KeyError(
                        f"Service connector with ID {component.connector} not "
                        "found."
                    )

            # warn about skypilot regions, if needed
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

        Raises:
            KeyError: if the stack component doesn't exist.
        """
        with Session(self.engine) as session:
            stack_component = session.exec(
                select(StackComponentSchema).where(
                    StackComponentSchema.id == component_id
                )
            ).first()

            if stack_component is None:
                raise KeyError(
                    f"Stack component with ID {component_id} not found."
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
            KeyError: if the stack component doesn't exist.
            IllegalOperationError: if the stack component is a default stack
                component.
        """
        with Session(self.engine) as session:
            existing_component = session.exec(
                select(StackComponentSchema).where(
                    StackComponentSchema.id == component_id
                )
            ).first()

            if existing_component is None:
                raise KeyError(
                    f"Unable to update component with id "
                    f"'{component_id}': Found no"
                    f"existing component with this id."
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
                        workspace_id=existing_component.workspace_id,
                        session=session,
                    )

            existing_component.update(component_update=component_update)

            if component_update.connector:
                service_connector = session.exec(
                    select(ServiceConnectorSchema).where(
                        ServiceConnectorSchema.id == component_update.connector
                    )
                ).first()

                if service_connector is None:
                    raise KeyError(
                        "Service connector with ID "
                        f"{component_update.connector} not found."
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
            KeyError: if the stack component doesn't exist.
            IllegalOperationError: if the stack component is part of one or
                more stacks, or if it's a default stack component.
        """
        with Session(self.engine) as session:
            try:
                stack_component = session.exec(
                    select(StackComponentSchema).where(
                        StackComponentSchema.id == component_id
                    )
                ).one()

                if stack_component is None:
                    raise KeyError(f"Stack with ID {component_id} not found.")
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
                else:
                    session.delete(stack_component)
            except NoResultFound as error:
                raise KeyError from error

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
        workspace_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a component with same name/type exists.

        Args:
            name: The name of the component
            component_type: The type of the component
            workspace_id: The ID of the workspace
            session: The Session

        Raises:
            StackComponentExistsError: If a component with the given name and
                type already exists.
        """
        # Check if component with the same domain key (name, type, workspace)
        # already exists
        existing_domain_component = session.exec(
            select(StackComponentSchema)
            .where(StackComponentSchema.name == name)
            .where(StackComponentSchema.workspace_id == workspace_id)
            .where(StackComponentSchema.type == component_type)
        ).first()
        if existing_domain_component is not None:
            raise StackComponentExistsError(
                f"Unable to register '{component_type}' component "
                f"with name '{name}': Found an existing "
                f"component with the same name and type in the same "
                f" workspace '{existing_domain_component.workspace.name}'."
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

        Raises:
            KeyError: If no device with the given ID exists.
        """
        with Session(self.engine) as session:
            device = session.exec(
                select(OAuthDeviceSchema).where(
                    OAuthDeviceSchema.id == device_id
                )
            ).first()
            if device is None:
                raise KeyError(
                    f"Unable to get device with ID {device_id}: No device with "
                    "this ID found."
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

        Raises:
            KeyError: If no device with the given ID exists.
        """
        with Session(self.engine) as session:
            existing_device = session.exec(
                select(OAuthDeviceSchema).where(
                    OAuthDeviceSchema.id == device_id
                )
            ).first()
            if existing_device is None:
                raise KeyError(
                    f"Unable to update device with ID {device_id}: No "
                    "device with this ID found."
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

        Raises:
            KeyError: If no device with the given ID exists.
        """
        with Session(self.engine) as session:
            existing_device = session.exec(
                select(OAuthDeviceSchema).where(
                    OAuthDeviceSchema.id == device_id
                )
            ).first()
            if existing_device is None:
                raise KeyError(
                    f"Unable to update device with ID {device_id}: No device "
                    "with this ID found."
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

        Raises:
            KeyError: If no device with the given ID exists.
        """
        with Session(self.engine) as session:
            existing_device = session.exec(
                select(OAuthDeviceSchema).where(
                    OAuthDeviceSchema.id == device_id
                )
            ).first()
            if existing_device is None:
                raise KeyError(
                    f"Unable to delete device with ID {device_id}: No device "
                    "with this ID found."
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
                    and device.expires < datetime.now()
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
                is already owned by this user in this workspace.
            ValueError: In case the config_schema string exceeds the max length.
        """
        with Session(self.engine) as session:
            # Check if flavor with the same domain key (name, type, workspace,
            # owner) already exists
            existing_flavor = session.exec(
                select(FlavorSchema)
                .where(FlavorSchema.name == flavor.name)
                .where(FlavorSchema.type == flavor.type)
                .where(FlavorSchema.workspace_id == flavor.workspace)
                .where(FlavorSchema.user_id == flavor.user)
            ).first()

            if existing_flavor is not None:
                raise EntityExistsError(
                    f"Unable to register '{flavor.type.value}' flavor "
                    f"with name '{flavor.name}': Found an existing "
                    f"flavor with the same name and type in the same "
                    f"'{flavor.workspace}' workspace owned by the same "
                    f"'{flavor.user}' user."
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
                    workspace_id=flavor.workspace,
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

        Raises:
            KeyError: if the stack component flavor doesn't exist.
        """
        with Session(self.engine) as session:
            flavor_in_db = session.exec(
                select(FlavorSchema).where(FlavorSchema.id == flavor_id)
            ).first()
            if flavor_in_db is None:
                raise KeyError(f"Flavor with ID {flavor_id} not found.")
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
            KeyError: If no flavor with the given id exists.
        """
        with Session(self.engine) as session:
            existing_flavor = session.exec(
                select(FlavorSchema).where(FlavorSchema.id == flavor_id)
            ).first()

            if not existing_flavor:
                raise KeyError(f"Flavor with ID {flavor_id} not found.")

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
            KeyError: if the flavor doesn't exist.
            IllegalOperationError: if the flavor is used by a stack component.
        """
        with Session(self.engine) as session:
            try:
                flavor_in_db = session.exec(
                    select(FlavorSchema).where(FlavorSchema.id == flavor_id)
                ).one()

                if flavor_in_db is None:
                    raise KeyError(f"Flavor with ID {flavor_id} not found.")
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
            except NoResultFound as error:
                raise KeyError from error

    # ------------------------ Logs ------------------------

    def get_logs(self, logs_id: UUID, hydrate: bool = True) -> LogsResponse:
        """Gets logs with the given ID.

        Args:
            logs_id: The ID of the logs to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The logs.

        Raises:
            KeyError: if the logs doesn't exist.
        """
        with Session(self.engine) as session:
            logs = session.exec(
                select(LogsSchema).where(LogsSchema.id == logs_id)
            ).first()
            if logs is None:
                raise KeyError(
                    f"Unable to get logs with ID "
                    f"{logs_id}: "
                    f"No logs with this ID found."
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
        """Creates a new pipeline in a workspace.

        Args:
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            EntityExistsError: If an identical pipeline already exists.
        """
        with Session(self.engine) as session:
            new_pipeline = PipelineSchema.from_request(pipeline)

            if pipeline.tags:
                self._attach_tags_to_resource(
                    tag_names=pipeline.tags,
                    resource_id=new_pipeline.id,
                    resource_type=TaggableResourceTypes.PIPELINE,
                )

            session.add(new_pipeline)
            try:
                session.commit()
            except IntegrityError:
                raise EntityExistsError(
                    f"Unable to create pipeline in workspace "
                    f"'{pipeline.workspace}': A pipeline with the name "
                    f"{pipeline.name} already exists."
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

        Raises:
            KeyError: if the pipeline does not exist.
        """
        with Session(self.engine) as session:
            # Check if pipeline with the given ID exists
            pipeline = session.exec(
                select(PipelineSchema).where(PipelineSchema.id == pipeline_id)
            ).first()
            if pipeline is None:
                raise KeyError(
                    f"Unable to get pipeline with ID '{pipeline_id}': "
                    "No pipeline with this ID found."
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
        query: Union[Select[Any], SelectOfScalar[Any]] = select(PipelineSchema)
        _custom_conversion: Optional[Callable[[Any], PipelineResponse]] = None

        column, operand = pipeline_filter_model.sorting_params
        if column == SORT_PIPELINES_BY_LATEST_RUN_KEY:
            with Session(self.engine) as session:
                max_date_subquery = (
                    # If no run exists for the pipeline yet, we use the pipeline
                    # creation date as a fallback, otherwise newly created
                    # pipeline would always be at the top/bottom
                    select(
                        PipelineSchema.id,
                        case(
                            (
                                func.max(PipelineRunSchema.created).is_(None),
                                PipelineSchema.created,
                            ),
                            else_=func.max(PipelineRunSchema.created),
                        ).label("run_or_created"),
                    )
                    .outerjoin(
                        PipelineRunSchema,
                        PipelineSchema.id == PipelineRunSchema.pipeline_id,  # type: ignore[arg-type]
                    )
                    .group_by(col(PipelineSchema.id))
                    .subquery()
                )

                if operand == SorterOps.DESCENDING:
                    sort_clause = desc
                else:
                    sort_clause = asc

                query = (
                    # We need to include the subquery in the select here to
                    # make this query work with the distinct statement. This
                    # result will be removed in the custom conversion function
                    # applied later
                    select(PipelineSchema, max_date_subquery.c.run_or_created)
                    .where(PipelineSchema.id == max_date_subquery.c.id)
                    .order_by(sort_clause(max_date_subquery.c.run_or_created))
                    # We always add the `id` column as a tiebreaker to ensure a
                    # stable, repeatable order of items, otherwise subsequent
                    # pages might contain the same items.
                    .order_by(col(PipelineSchema.id))
                )

            def _custom_conversion(row: Any) -> PipelineResponse:
                return cast(
                    PipelineResponse,
                    row[0].to_model(
                        include_metadata=hydrate, include_resources=True
                    ),
                )

        with Session(self.engine) as session:
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=PipelineSchema,
                filter_model=pipeline_filter_model,
                hydrate=hydrate,
                custom_schema_to_model_conversion=_custom_conversion,
            )

    def count_pipelines(self, filter_model: Optional[PipelineFilter]) -> int:
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

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if pipeline with the given ID exists
            existing_pipeline = session.exec(
                select(PipelineSchema).where(PipelineSchema.id == pipeline_id)
            ).first()
            if existing_pipeline is None:
                raise KeyError(
                    f"Unable to update pipeline with ID {pipeline_id}: "
                    f"No pipeline with this ID found."
                )

            if pipeline_update.add_tags:
                self._attach_tags_to_resource(
                    tag_names=pipeline_update.add_tags,
                    resource_id=existing_pipeline.id,
                    resource_type=TaggableResourceTypes.PIPELINE,
                )
            pipeline_update.add_tags = None
            if pipeline_update.remove_tags:
                self._detach_tags_from_resource(
                    tag_names=pipeline_update.remove_tags,
                    resource_id=existing_pipeline.id,
                    resource_type=TaggableResourceTypes.PIPELINE,
                )
            pipeline_update.remove_tags = None

            existing_pipeline.update(pipeline_update)
            session.add(existing_pipeline)
            session.commit()
            session.refresh(existing_pipeline)

            return existing_pipeline.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_pipeline(self, pipeline_id: UUID) -> None:
        """Deletes a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to delete.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if pipeline with the given ID exists
            pipeline = session.exec(
                select(PipelineSchema).where(PipelineSchema.id == pipeline_id)
            ).first()
            if pipeline is None:
                raise KeyError(
                    f"Unable to delete pipeline with ID {pipeline_id}: "
                    f"No pipeline with this ID found."
                )

            session.delete(pipeline)
            session.commit()

    # --------------------------- Pipeline Builds ---------------------------

    def create_build(
        self,
        build: PipelineBuildRequest,
    ) -> PipelineBuildResponse:
        """Creates a new build in a workspace.

        Args:
            build: The build to create.

        Returns:
            The newly created build.
        """
        with Session(self.engine) as session:
            # Create the build
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

        Raises:
            KeyError: If the build does not exist.
        """
        with Session(self.engine) as session:
            # Check if build with the given ID exists
            build = session.exec(
                select(PipelineBuildSchema).where(
                    PipelineBuildSchema.id == build_id
                )
            ).first()
            if build is None:
                raise KeyError(
                    f"Unable to get build with ID '{build_id}': "
                    "No build with this ID found."
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

        Raises:
            KeyError: if the build doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if build with the given ID exists
            build = session.exec(
                select(PipelineBuildSchema).where(
                    PipelineBuildSchema.id == build_id
                )
            ).first()
            if build is None:
                raise KeyError(
                    f"Unable to delete build with ID {build_id}: "
                    f"No build with this ID found."
                )

            session.delete(build)
            session.commit()

    # -------------------------- Pipeline Deployments --------------------------

    def create_deployment(
        self,
        deployment: PipelineDeploymentRequest,
    ) -> PipelineDeploymentResponse:
        """Creates a new deployment in a workspace.

        Args:
            deployment: The deployment to create.

        Returns:
            The newly created deployment.
        """
        with Session(self.engine) as session:
            code_reference_id = self._create_or_reuse_code_reference(
                session=session,
                workspace_id=deployment.workspace,
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

        Raises:
            KeyError: If the deployment does not exist.
        """
        with Session(self.engine) as session:
            # Check if deployment with the given ID exists
            deployment = session.exec(
                select(PipelineDeploymentSchema).where(
                    PipelineDeploymentSchema.id == deployment_id
                )
            ).first()
            if deployment is None:
                raise KeyError(
                    f"Unable to get deployment with ID '{deployment_id}': "
                    "No deployment with this ID found."
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

        Raises:
            KeyError: If the deployment doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if build with the given ID exists
            deployment = session.exec(
                select(PipelineDeploymentSchema).where(
                    PipelineDeploymentSchema.id == deployment_id
                )
            ).first()
            if deployment is None:
                raise KeyError(
                    f"Unable to delete deployment with ID {deployment_id}: "
                    f"No deployment with this ID found."
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

        Raises:
            EntityExistsError: If a template with the same name already exists.
            ValueError: If the source deployment does not exist or does not
                have an associated build.
        """
        with Session(self.engine) as session:
            existing_template = session.exec(
                select(RunTemplateSchema)
                .where(RunTemplateSchema.name == template.name)
                .where(RunTemplateSchema.workspace_id == template.workspace)
            ).first()
            if existing_template is not None:
                raise EntityExistsError(
                    f"Unable to create run template in workspace "
                    f"'{existing_template.workspace.name}': A run template "
                    f"with the name '{template.name}' already exists."
                )

            deployment = session.exec(
                select(PipelineDeploymentSchema).where(
                    PipelineDeploymentSchema.id
                    == template.source_deployment_id
                )
            ).first()
            if not deployment:
                raise ValueError(
                    f"Source deployment {template.source_deployment_id} not "
                    "found."
                )

            template_utils.validate_deployment_is_templatable(deployment)

            template_schema = RunTemplateSchema.from_request(request=template)

            if template.tags:
                self._attach_tags_to_resource(
                    tag_names=template.tags,
                    resource_id=template_schema.id,
                    resource_type=TaggableResourceTypes.RUN_TEMPLATE,
                )

            session.add(template_schema)
            session.commit()
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

        Raises:
            KeyError: If the template does not exist.
        """
        with Session(self.engine) as session:
            template = session.exec(
                select(RunTemplateSchema).where(
                    RunTemplateSchema.id == template_id
                )
            ).first()
            if template is None:
                raise KeyError(
                    f"Unable to get run template with ID {template_id}: "
                    f"No run template with this ID found."
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

        Raises:
            KeyError: If the template does not exist.
        """
        with Session(self.engine) as session:
            template = session.exec(
                select(RunTemplateSchema).where(
                    RunTemplateSchema.id == template_id
                )
            ).first()
            if template is None:
                raise KeyError(
                    f"Unable to update run template with ID {template_id}: "
                    f"No run template with this ID found."
                )

            if template_update.add_tags:
                self._attach_tags_to_resource(
                    tag_names=template_update.add_tags,
                    resource_id=template.id,
                    resource_type=TaggableResourceTypes.RUN_TEMPLATE,
                )
            template_update.add_tags = None

            if template_update.remove_tags:
                self._detach_tags_from_resource(
                    tag_names=template_update.remove_tags,
                    resource_id=template.id,
                    resource_type=TaggableResourceTypes.RUN_TEMPLATE,
                )
            template_update.remove_tags = None

            template.update(template_update)
            session.add(template)
            session.commit()
            session.refresh(template)

            return template.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_run_template(self, template_id: UUID) -> None:
        """Delete a run template.

        Args:
            template_id: The ID of the template to delete.

        Raises:
            KeyError: If the template does not exist.
        """
        with Session(self.engine) as session:
            template = session.exec(
                select(RunTemplateSchema).where(
                    RunTemplateSchema.id == template_id
                )
            ).first()
            if template is None:
                raise KeyError(
                    f"Unable to delete run template with ID {template_id}: "
                    f"No run template with this ID found."
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

    def _fail_if_event_source_with_name_exists(
        self, event_source: EventSourceRequest, session: Session
    ) -> None:
        """Raise an exception if a stack with same name exists.

        Args:
            event_source: The event_source to create.
            session: The Session

        Raises:
            EventSourceExistsError: If an event source with the given name
                already exists.
        """
        existing_domain_event_source = session.exec(
            select(EventSourceSchema)
            .where(EventSourceSchema.name == event_source.name)
            .where(EventSourceSchema.workspace_id == event_source.workspace)
        ).first()
        if existing_domain_event_source is not None:
            workspace = self._get_workspace_schema(
                workspace_name_or_id=event_source.workspace, session=session
            )
            raise EventSourceExistsError(
                f"Unable to register event source with name "
                f"'{event_source.name}': Found an existing event source with "
                f"the same name in the active workspace, '{workspace.name}'."
            )

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
            self._fail_if_event_source_with_name_exists(
                event_source=event_source,
                session=session,
            )
            new_event_source = EventSourceSchema.from_request(event_source)
            session.add(new_event_source)
            session.commit()
            session.refresh(new_event_source)

            return new_event_source.to_model(
                include_metadata=True, include_resources=True
            )

    def _get_event_source(
        self,
        event_source_id: UUID,
        session: Session,
    ) -> EventSourceSchema:
        """Get an event_source by ID.

        Args:
            event_source_id: The ID of the event_source to get.
            session: The DB session.

        Returns:
            The event_source schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=event_source_id,
            schema_class=EventSourceSchema,
            schema_name="event_source",
            session=session,
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
            return self._get_event_source(
                event_source_id=event_source_id, session=session
            ).to_model(include_metadata=hydrate, include_resources=True)

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
            event_source = self._get_event_source(
                session=session, event_source_id=event_source_id
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
            KeyError: if the event_source doesn't exist.
            IllegalOperationError: If the event source can't be deleted
                because it's used by triggers.
        """
        with Session(self.engine) as session:
            event_source = self._get_event_source(
                event_source_id=event_source_id, session=session
            )
            if event_source is None:
                raise KeyError(
                    f"Unable to delete event_source with ID `{event_source_id}`: "
                    f"No event_source with this ID found."
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

    def _pipeline_run_exists(self, workspace_id: UUID, name: str) -> bool:
        """Check if a pipeline name with a certain name exists.

        Args:
            workspace_id: The workspace to check.
            name: The run name.

        Returns:
            If a pipeline run with the given name exists.
        """
        with Session(self.engine) as session:
            return (
                session.exec(
                    select(PipelineRunSchema.id)
                    .where(PipelineRunSchema.workspace_id == workspace_id)
                    .where(PipelineRunSchema.name == name)
                ).first()
                is not None
            )

    def create_run(
        self, pipeline_run: PipelineRunRequest
    ) -> PipelineRunResponse:
        """Creates a pipeline run.

        Args:
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

        Raises:
            EntityExistsError: If a run with the same name already exists.
        """
        with Session(self.engine) as session:
            # Create the pipeline run
            new_run = PipelineRunSchema.from_request(pipeline_run)

            if pipeline_run.tags:
                self._attach_tags_to_resource(
                    tag_names=pipeline_run.tags,
                    resource_id=new_run.id,
                    resource_type=TaggableResourceTypes.PIPELINE_RUN,
                )

            session.add(new_run)
            try:
                session.commit()
            except IntegrityError:
                if self._pipeline_run_exists(
                    workspace_id=pipeline_run.workspace, name=pipeline_run.name
                ):
                    raise EntityExistsError(
                        f"Unable to create pipeline run: A pipeline run with "
                        f"name '{pipeline_run.name}' already exists."
                    )
                else:
                    raise EntityExistsError(
                        "Unable to create pipeline run: A pipeline run with "
                        "the same deployment_id and orchestrator_run_id "
                        "already exists."
                    )

            return new_run.to_model(
                include_metadata=True, include_resources=True
            )

    def get_run(
        self, run_name_or_id: Union[str, UUID], hydrate: bool = True
    ) -> PipelineRunResponse:
        """Gets a pipeline run.

        Args:
            run_name_or_id: The name or ID of the pipeline run to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The pipeline run.
        """
        with Session(self.engine) as session:
            return self._get_run_schema(
                run_name_or_id, session=session
            ).to_model(include_metadata=hydrate, include_resources=True)

    def _replace_placeholder_run(
        self,
        pipeline_run: PipelineRunRequest,
        pre_replacement_hook: Optional[Callable[[], None]] = None,
    ) -> PipelineRunResponse:
        """Replace a placeholder run with the requested pipeline run.

        Args:
            pipeline_run: Pipeline run request.
            pre_replacement_hook: Optional function to run before replacing the
                pipeline run.

        Raises:
            KeyError: If no placeholder run exists.

        Returns:
            The run model.
        """
        with Session(self.engine) as session:
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
                .where(
                    PipelineRunSchema.deployment_id == pipeline_run.deployment
                )
                .where(
                    PipelineRunSchema.orchestrator_run_id.is_(None)  # type: ignore[union-attr]
                )
            ).first()

            if not run_schema:
                raise KeyError("No placeholder run found.")

            if pre_replacement_hook:
                pre_replacement_hook()
            run_schema.update_placeholder(pipeline_run)

            if pipeline_run.tags:
                self._attach_tags_to_resource(
                    tag_names=pipeline_run.tags,
                    resource_id=run_schema.id,
                    resource_type=TaggableResourceTypes.PIPELINE_RUN,
                )

            session.add(run_schema)
            session.commit()

            return run_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def _get_run_by_orchestrator_run_id(
        self, orchestrator_run_id: str, deployment_id: UUID
    ) -> PipelineRunResponse:
        """Get a pipeline run based on deployment and orchestrator run ID.

        Args:
            orchestrator_run_id: The orchestrator run ID.
            deployment_id: The deployment ID.

        Raises:
            KeyError: If no run exists for the deployment and orchestrator run
                ID.

        Returns:
            The pipeline run.
        """
        with Session(self.engine) as session:
            run_schema = session.exec(
                select(PipelineRunSchema)
                .where(PipelineRunSchema.deployment_id == deployment_id)
                .where(
                    PipelineRunSchema.orchestrator_run_id
                    == orchestrator_run_id
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
            ValueError: If the request does not contain an orchestrator run ID.
            EntityExistsError: If a run with the same name already exists.
            RuntimeError: If the run fetching failed unexpectedly.

        Returns:
            The pipeline run, and a boolean indicating whether the run was
            created or not.
        """
        if not pipeline_run.orchestrator_run_id:
            raise ValueError(
                "Unable to get or create run for request with missing "
                "orchestrator run ID."
            )

        try:
            return (
                self._replace_placeholder_run(
                    pipeline_run=pipeline_run,
                    pre_replacement_hook=pre_creation_hook,
                ),
                True,
            )
        except KeyError:
            # We were not able to find/replace a placeholder run. This could be
            # due to one of the following three reasons:
            # (1) There never was a placeholder run for the deployment. This is
            #     the case if the user ran the pipeline on a schedule.
            # (2) There was a placeholder run, but a previous pipeline run
            #     already used it. This is the case if users rerun a pipeline
            #     run e.g. from the orchestrator UI, as they will use the same
            #     deployment_id with a new orchestrator_run_id.
            # (3) A step of the same pipeline run already replaced the
            #     placeholder run.
            pass

        try:
            # We now try to create a new run. The following will happen in the
            # three cases described above:
            # (1) The behavior depends on whether we're the first step of the
            #     pipeline run that's trying to create the run. If yes, the
            #     `self.create_run(...)` will succeed. If no, a run with the
            #     same deployment_id and orchestrator_run_id already exists and
            #     the `self.create_run(...)` call will fail due to the unique
            #     constraint on those columns.
            # (2) Same as (1).
            # (3) A step of the same pipeline run replaced the placeholder
            #     run, which now contains the deployment_id and
            #     orchestrator_run_id of the run that we're trying to create.
            #     -> The `self.create_run(...) call will fail due to the unique
            #     constraint on those columns.
            if pre_creation_hook:
                pre_creation_hook()
            return self.create_run(pipeline_run), True
        except EntityExistsError as create_error:
            # Creating the run failed because
            # - a run with the same deployment_id and orchestrator_run_id
            #   exists. We now fetch and return that run.
            # - a run with the same name already exists. This could be either a
            #   different run (in which case we want to fail) or a run created
            #   by a step of the same pipeline run (in which case we want to
            #   return it).
            try:
                return (
                    self._get_run_by_orchestrator_run_id(
                        orchestrator_run_id=pipeline_run.orchestrator_run_id,
                        deployment_id=pipeline_run.deployment,
                    ),
                    False,
                )
            except KeyError:
                # We should only get here if the run creation failed because
                # of a name conflict. We raise the error that happened during
                # creation in any case to forward the error message to the
                # user.
                raise create_error

    def list_runs(
        self,
        runs_filter_model: PipelineRunFilter,
        hydrate: bool = False,
    ) -> Page[PipelineRunResponse]:
        """List all pipeline runs matching the given filter criteria.

        Args:
            runs_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all pipeline runs matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(PipelineRunSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=PipelineRunSchema,
                filter_model=runs_filter_model,
                hydrate=hydrate,
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

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if pipeline run with the given ID exists
            existing_run = session.exec(
                select(PipelineRunSchema).where(PipelineRunSchema.id == run_id)
            ).first()
            if existing_run is None:
                raise KeyError(
                    f"Unable to update pipeline run with ID {run_id}: "
                    f"No pipeline run with this ID found."
                )

            if run_update.add_tags:
                self._attach_tags_to_resource(
                    tag_names=run_update.add_tags,
                    resource_id=existing_run.id,
                    resource_type=TaggableResourceTypes.PIPELINE_RUN,
                )
            run_update.add_tags = None
            if run_update.remove_tags:
                self._detach_tags_from_resource(
                    tag_names=run_update.remove_tags,
                    resource_id=existing_run.id,
                    resource_type=TaggableResourceTypes.PIPELINE_RUN,
                )
            run_update.remove_tags = None

            existing_run.update(run_update=run_update)
            session.add(existing_run)
            session.commit()

            session.refresh(existing_run)
            return existing_run.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_run(self, run_id: UUID) -> None:
        """Deletes a pipeline run.

        Args:
            run_id: The ID of the pipeline run to delete.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if pipeline run with the given ID exists
            existing_run = session.exec(
                select(PipelineRunSchema).where(PipelineRunSchema.id == run_id)
            ).first()
            if existing_run is None:
                raise KeyError(
                    f"Unable to delete pipeline run with ID {run_id}: "
                    f"No pipeline run with this ID found."
                )

            # Delete the pipeline run
            session.delete(existing_run)
            session.commit()

    def count_runs(self, filter_model: Optional[PipelineRunFilter]) -> int:
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

    def create_run_metadata(
        self, run_metadata: RunMetadataRequest
    ) -> List[RunMetadataResponse]:
        """Creates run metadata.

        Args:
            run_metadata: The run metadata to create.

        Returns:
            The created run metadata.
        """
        return_value: List[RunMetadataResponse] = []
        with Session(self.engine) as session:
            for key, value in run_metadata.values.items():
                type_ = run_metadata.types[key]
                run_metadata_schema = RunMetadataSchema(
                    workspace_id=run_metadata.workspace,
                    user_id=run_metadata.user,
                    resource_id=run_metadata.resource_id,
                    resource_type=run_metadata.resource_type.value,
                    stack_component_id=run_metadata.stack_component_id,
                    key=key,
                    value=json.dumps(value),
                    type=type_,
                )
                session.add(run_metadata_schema)
                session.commit()
                return_value.append(
                    run_metadata_schema.to_model(
                        include_metadata=True, include_resources=True
                    )
                )
        return return_value

    def get_run_metadata(
        self, run_metadata_id: UUID, hydrate: bool = True
    ) -> RunMetadataResponse:
        """Gets run metadata with the given ID.

        Args:
            run_metadata_id: The ID of the run metadata to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The run metadata.

        Raises:
            KeyError: if the run metadata doesn't exist.
        """
        with Session(self.engine) as session:
            run_metadata = session.exec(
                select(RunMetadataSchema).where(
                    RunMetadataSchema.id == run_metadata_id
                )
            ).first()
            if run_metadata is None:
                raise KeyError(
                    f"Unable to get run metadata with ID "
                    f"{run_metadata_id}: "
                    f"No run metadata with this ID found."
                )
            return run_metadata.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_run_metadata(
        self,
        run_metadata_filter_model: RunMetadataFilter,
        hydrate: bool = False,
    ) -> Page[RunMetadataResponse]:
        """List run metadata.

        Args:
            run_metadata_filter_model: All filter parameters including
                pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The run metadata.
        """
        with Session(self.engine) as session:
            query = select(RunMetadataSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=RunMetadataSchema,
                filter_model=run_metadata_filter_model,
                hydrate=hydrate,
            )

    # ----------------------------- Schedules -----------------------------

    def create_schedule(self, schedule: ScheduleRequest) -> ScheduleResponse:
        """Creates a new schedule.

        Args:
            schedule: The schedule to create.

        Returns:
            The newly created schedule.
        """
        with Session(self.engine) as session:
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

        Raises:
            KeyError: if the schedule does not exist.
        """
        with Session(self.engine) as session:
            # Check if schedule with the given ID exists
            schedule = session.exec(
                select(ScheduleSchema).where(ScheduleSchema.id == schedule_id)
            ).first()
            if schedule is None:
                raise KeyError(
                    f"Unable to get schedule with ID '{schedule_id}': "
                    "No schedule with this ID found."
                )
            return schedule.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_schedules(
        self,
        schedule_filter_model: ScheduleFilter,
        hydrate: bool = False,
    ) -> Page[ScheduleResponse]:
        """List all schedules in the workspace.

        Args:
            schedule_filter_model: All filter parameters including pagination
                params
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of schedules.
        """
        with Session(self.engine) as session:
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

        Raises:
            KeyError: if the schedule doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if schedule with the given ID exists
            existing_schedule = session.exec(
                select(ScheduleSchema).where(ScheduleSchema.id == schedule_id)
            ).first()
            if existing_schedule is None:
                raise KeyError(
                    f"Unable to update schedule with ID {schedule_id}: "
                    f"No schedule with this ID found."
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

        Raises:
            KeyError: if the schedule doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if schedule with the given ID exists
            schedule = session.exec(
                select(ScheduleSchema).where(ScheduleSchema.id == schedule_id)
            ).first()
            if schedule is None:
                raise KeyError(
                    f"Unable to delete schedule with ID {schedule_id}: "
                    f"No schedule with this ID found."
                )

            # Delete the schedule
            session.delete(schedule)
            session.commit()

    # ------------------------- Secrets -------------------------

    def _check_sql_secret_scope(
        self,
        session: Session,
        secret_name: str,
        scope: SecretScope,
        workspace: UUID,
        user: UUID,
        exclude_secret_id: Optional[UUID] = None,
    ) -> Tuple[bool, str]:
        """Checks if a secret with the given name already exists in the given scope.

        This method enforces the following scope rules:

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            session: The SQLAlchemy session.
            secret_name: The name of the secret.
            scope: The scope of the secret.
            workspace: The ID of the workspace to which the secret belongs.
            user: The ID of the user to which the secret belongs.
            exclude_secret_id: The ID of a secret to exclude from the check
                (used e.g. during an update to exclude the existing secret).

        Returns:
            True if a secret with the given name already exists in the given
            scope, False otherwise, and an error message.
        """
        scope_filter = (
            select(SecretSchema)
            .where(SecretSchema.name == secret_name)
            .where(SecretSchema.scope == scope.value)
        )

        if scope in [SecretScope.WORKSPACE, SecretScope.USER]:
            scope_filter = scope_filter.where(
                SecretSchema.workspace_id == workspace
            )
        if scope == SecretScope.USER:
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

            msg = (
                f"Found an existing {scope.value} scoped secret with the "
                f"same '{secret_name}' name"
            )
            if scope in [SecretScope.WORKSPACE, SecretScope.USER]:
                msg += (
                    f" in the same '{existing_secret_model.workspace.name}' "
                    f"workspace"
                )
            if scope == SecretScope.USER:
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
            # whether the secret values are already stored in the backup secrets
            # store. This is to account for any inconsistencies in the backup
            # secrets store without impairing the backup functionality.
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

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret: The secret to create.

        Returns:
            The newly created secret.

        Raises:
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
        """
        with Session(self.engine) as session:
            # Check if a secret with the same name already exists in the same
            # scope.
            secret_exists, msg = self._check_sql_secret_scope(
                session=session,
                secret_name=secret.name,
                scope=secret.scope,
                workspace=secret.workspace,
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
            if secret_in_db is None:
                raise KeyError(f"Secret with ID {secret_id} not found.")
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

          - only one workspace-scoped secret with the given name can exist
            in the target workspace.
          - only one user-scoped secret with the given name can exist in the
            target workspace for the target user.

        Args:
            secret_id: The ID of the secret to be updated.
            secret_update: The update to be applied.

        Returns:
            The updated secret.

        Raises:
            KeyError: if the secret doesn't exist.
            EntityExistsError: If a secret with the same name already exists in
                the same scope.
        """
        with Session(self.engine) as session:
            existing_secret = session.exec(
                select(SecretSchema).where(SecretSchema.id == secret_id)
            ).first()

            if not existing_secret:
                raise KeyError(f"Secret with ID {secret_id} not found.")

            # A change in name or scope requires a check of the scoping rules.
            if (
                secret_update.name is not None
                and existing_secret.name != secret_update.name
                or secret_update.scope is not None
                and existing_secret.scope != secret_update.scope
            ):
                secret_exists, msg = self._check_sql_secret_scope(
                    session=session,
                    secret_name=secret_update.name or existing_secret.name,
                    scope=secret_update.scope
                    or SecretScope(existing_secret.scope),
                    workspace=existing_secret.workspace.id,
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
        # Delete the secret values in the configured secrets store
        try:
            self._delete_secret_values(secret_id=secret_id)
        except KeyError:
            # If the secret values don't exist in the secrets store, we don't
            # need to raise an error.
            pass

        with Session(self.engine) as session:
            try:
                secret_in_db = session.exec(
                    select(SecretSchema).where(SecretSchema.id == secret_id)
                ).one()
                session.delete(secret_in_db)
                session.commit()
            except NoResultFound:
                raise KeyError(f"Secret with ID {secret_id} not found.")

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
            self._fail_if_service_connector_with_name_exists(
                name=service_connector.name,
                workspace_id=service_connector.workspace,
                session=session,
            )

            # Create the secret
            secret_id = self._create_connector_secret(
                connector_name=service_connector.name,
                user=service_connector.user,
                workspace=service_connector.workspace,
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

        Raises:
            KeyError: If no service connector with the given ID exists.
        """
        with Session(self.engine) as session:
            service_connector = session.exec(
                select(ServiceConnectorSchema).where(
                    ServiceConnectorSchema.id == service_connector_id
                )
            ).first()

            if service_connector is None:
                raise KeyError(
                    f"Service connector with ID {service_connector_id} not "
                    "found."
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
            KeyError: If no service connector with the given ID exists.
            IllegalOperationError: If the service connector is referenced by
                one or more stack components and the update would change the
                connector type, resource type or resource ID.
        """
        with Session(self.engine) as session:
            existing_connector = session.exec(
                select(ServiceConnectorSchema).where(
                    ServiceConnectorSchema.id == service_connector_id
                )
            ).first()

            if existing_connector is None:
                raise KeyError(
                    f"Unable to update service connector with ID "
                    f"'{service_connector_id}': Found no existing service "
                    "connector with this ID."
                )

            # In case of a renaming update, make sure no service connector uses
            # that name already
            if update.name and existing_connector.name != update.name:
                self._fail_if_service_connector_with_name_exists(
                    name=update.name,
                    workspace_id=existing_connector.workspace_id,
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
            KeyError: If no service connector with the given ID exists.
            IllegalOperationError: If the service connector is still referenced
                by one or more stack components.
        """
        with Session(self.engine) as session:
            try:
                service_connector = session.exec(
                    select(ServiceConnectorSchema).where(
                        ServiceConnectorSchema.id == service_connector_id
                    )
                ).one()

                if service_connector is None:
                    raise KeyError(
                        f"Service connector with ID {service_connector_id} not "
                        "found."
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
            except NoResultFound as error:
                raise KeyError from error

            session.commit()

    @staticmethod
    def _fail_if_service_connector_with_name_exists(
        name: str,
        workspace_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a service connector with same name exists.

        Args:
            name: The name of the service connector
            workspace_id: The ID of the workspace
            session: The Session

        Raises:
            EntityExistsError: If a service connector with the given name
                already exists.
        """
        # Check if service connector with the same domain key (name, workspace)
        # already exists
        existing_domain_connector = session.exec(
            select(ServiceConnectorSchema)
            .where(ServiceConnectorSchema.name == name)
            .where(ServiceConnectorSchema.workspace_id == workspace_id)
        ).first()
        if existing_domain_connector is not None:
            raise EntityExistsError(
                f"Unable to register service connector with name '{name}': "
                "Found an existing service connector with the same name in the "
                f"same workspace '{existing_domain_connector.workspace.name}'."
            )

    def _create_connector_secret(
        self,
        connector_name: str,
        user: UUID,
        workspace: UUID,
        secrets: Optional[Dict[str, Optional[SecretStr]]],
    ) -> Optional[UUID]:
        """Creates a new secret to store the service connector secret credentials.

        Args:
            connector_name: The name of the service connector for which to
                create a secret.
            user: The ID of the user who owns the service connector.
            workspace: The ID of the workspace in which the service connector
                is registered.
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
                            user=user,
                            workspace=workspace,
                            scope=SecretScope.WORKSPACE,
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
            user=existing_connector.user.id,
            workspace=existing_connector.workspace.id,
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
            workspace=connector.workspace,
            description=connector.description,
            labels=connector.labels,
        )

        self._populate_connector_type(connector)

        return connector

    def list_service_connector_resources(
        self,
        workspace_name_or_id: Union[str, UUID],
        connector_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        filter_model: Optional[ServiceConnectorFilter] = None,
    ) -> List[ServiceConnectorResourcesModel]:
        """List resources that can be accessed by service connectors.

        Args:
            workspace_name_or_id: The name or ID of the workspace to scope to.
            connector_type: The type of service connector to scope to.
            resource_type: The type of resource to scope to.
            resource_id: The ID of the resource to scope to.
            filter_model: Optional filter model to use when fetching service
                connectors.

        Returns:
            The matching list of resources that available service
            connectors have access to.
        """
        workspace = self.get_workspace(workspace_name_or_id)

        if not filter_model:
            filter_model = ServiceConnectorFilter(
                connector_type=connector_type,
                resource_type=resource_type,
                workspace_id=workspace.id,
            )

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
                        resource_type=resource_type,
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
                        resource_type=resource_type,
                        resource_id=resource_id,
                        list_resources=True,
                    )
                except (ValueError, AuthorizationException) as e:
                    error = (
                        f'Failed to fetch {resource_type or "available"} '
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
                                    user=stack.user,
                                    workspace=stack.workspace,
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
                                        user=stack.user,
                                        workspace=stack.workspace,
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
                assert stack.workspace is not None

                self._fail_if_stack_with_name_exists(
                    stack_name=stack.name,
                    workspace_id=stack.workspace,
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
                    workspace_id=stack.workspace,
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

        Raises:
            KeyError: if the stack doesn't exist.
        """
        with Session(self.engine) as session:
            stack = session.exec(
                select(StackSchema).where(StackSchema.id == stack_id)
            ).first()

            if stack is None:
                raise KeyError(f"Stack with ID {stack_id} not found.")
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
            KeyError: if the stack doesn't exist.
            IllegalOperationError: if the stack is a default stack.
        """
        with Session(self.engine) as session:
            # Check if stack with the domain key (name, workspace, owner)
            # already exists
            existing_stack = session.exec(
                select(StackSchema).where(StackSchema.id == stack_id)
            ).first()
            if existing_stack is None:
                raise KeyError(
                    f"Unable to update stack with id '{stack_id}': Found no"
                    f"existing stack with this id."
                )
            if existing_stack.name == DEFAULT_STACK_AND_COMPONENT_NAME:
                raise IllegalOperationError(
                    "The default stack cannot be modified."
                )
            # In case of a renaming update, make sure no stack already exists
            # with that name
            if stack_update.name:
                if existing_stack.name != stack_update.name:
                    self._fail_if_stack_with_name_exists(
                        stack_name=stack_update.name,
                        workspace_id=existing_stack.workspace.id,
                        session=session,
                    )

            components: List["StackComponentSchema"] = []
            if stack_update.components:
                filters = [
                    (StackComponentSchema.id == component_id)
                    for list_of_component_ids in stack_update.components.values()
                    for component_id in list_of_component_ids
                ]
                components = list(
                    session.exec(
                        select(StackComponentSchema).where(or_(*filters))
                    ).all()
                )

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
            KeyError: if the stack doesn't exist.
            IllegalOperationError: if the stack is a default stack.
        """
        with Session(self.engine) as session:
            try:
                stack = session.exec(
                    select(StackSchema).where(StackSchema.id == stack_id)
                ).one()

                if stack is None:
                    raise KeyError(f"Stack with ID {stack_id} not found.")
                if stack.name == DEFAULT_STACK_AND_COMPONENT_NAME:
                    raise IllegalOperationError(
                        "The default stack cannot be deleted."
                    )
                session.delete(stack)
            except NoResultFound as error:
                raise KeyError from error

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

    def _fail_if_stack_with_name_exists(
        self,
        stack_name: str,
        workspace_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a stack with same name exists.

        Args:
            stack_name: The name of the stack
            workspace_id: The ID of the workspace
            session: The session

        Returns:
            None

        Raises:
            StackExistsError: If a stack with the given name already exists.
        """
        existing_domain_stack = session.exec(
            select(StackSchema)
            .where(StackSchema.name == stack_name)
            .where(StackSchema.workspace_id == workspace_id)
        ).first()
        if existing_domain_stack is not None:
            workspace = self._get_workspace_schema(
                workspace_name_or_id=workspace_id, session=session
            )
            raise StackExistsError(
                f"Unable to register stack with name "
                f"'{stack_name}': Found an existing stack with the same "
                f"name in the active workspace, '{workspace.name}'."
            )
        return None

    def _create_default_stack(
        self,
        workspace_id: UUID,
    ) -> StackResponse:
        """Create the default stack components and stack.

        The default stack contains a local orchestrator and a local artifact
        store.

        Args:
            workspace_id: ID of the workspace to which the stack
                belongs.

        Returns:
            The model of the created default stack.
        """
        with analytics_disabler():
            workspace = self.get_workspace(workspace_name_or_id=workspace_id)

            logger.info(
                f"Creating default stack in workspace {workspace.name}..."
            )
            orchestrator = self.create_stack_component(
                component=InternalComponentRequest(
                    # Passing `None` for the user here means the orchestrator
                    # is owned by the server, which for RBAC indicates that
                    # everyone can read it
                    user=None,
                    workspace=workspace.id,
                    name=DEFAULT_STACK_AND_COMPONENT_NAME,
                    type=StackComponentType.ORCHESTRATOR,
                    flavor="local",
                    configuration={},
                ),
            )

            artifact_store = self.create_stack_component(
                component=InternalComponentRequest(
                    # Passing `None` for the user here means the stack is owned
                    # by the server, which for RBAC indicates that everyone can
                    # read it
                    user=None,
                    workspace=workspace.id,
                    name=DEFAULT_STACK_AND_COMPONENT_NAME,
                    type=StackComponentType.ARTIFACT_STORE,
                    flavor="local",
                    configuration={},
                ),
            )

            components = {
                c.type: [c.id] for c in [orchestrator, artifact_store]
            }

            stack = StackRequest(
                user=None,
                name=DEFAULT_STACK_AND_COMPONENT_NAME,
                components=components,
                workspace=workspace.id,
            )
            return self.create_stack(stack=stack)

    def _get_or_create_default_stack(
        self, workspace: WorkspaceResponse
    ) -> StackResponse:
        """Get or create the default stack if it doesn't exist.

        Args:
            workspace: The workspace for which to create the default stack.

        Returns:
            The default stack.
        """
        try:
            return self._get_default_stack(
                workspace_id=workspace.id,
            )
        except KeyError:
            return self._create_default_stack(
                workspace_id=workspace.id,
            )

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
            KeyError: if the pipeline run doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if the pipeline run exists
            run = session.exec(
                select(PipelineRunSchema).where(
                    PipelineRunSchema.id == step_run.pipeline_run_id
                )
            ).first()
            if run is None:
                raise KeyError(
                    f"Unable to create step `{step_run.name}`: No pipeline run "
                    f"with ID '{step_run.pipeline_run_id}' found."
                )

            # Check if the step name already exists in the pipeline run
            existing_step_run = session.exec(
                select(StepRunSchema)
                .where(StepRunSchema.name == step_run.name)
                .where(
                    StepRunSchema.pipeline_run_id == step_run.pipeline_run_id
                )
            ).first()
            if existing_step_run is not None:
                raise EntityExistsError(
                    f"Unable to create step `{step_run.name}`: A step with "
                    f"this name already exists in the pipeline run with ID "
                    f"'{step_run.pipeline_run_id}'."
                )

            # Create the step
            step_schema = StepRunSchema.from_request(step_run)
            session.add(step_schema)

            # Add logs entry for the step if exists
            if step_run.logs is not None:
                log_entry = LogsSchema(
                    uri=step_run.logs.uri,
                    step_run_id=step_schema.id,
                    artifact_store_id=step_run.logs.artifact_store_id,
                )
                session.add(log_entry)

            # Save parent step IDs into the database.
            for parent_step_id in step_run.parent_step_ids:
                self._set_run_step_parent_step(
                    child_id=step_schema.id,
                    parent_id=parent_step_id,
                    session=session,
                )

            # Save input artifact IDs into the database.
            for input_name, artifact_version_id in step_run.inputs.items():
                self._set_run_step_input_artifact(
                    run_step_id=step_schema.id,
                    artifact_version_id=artifact_version_id,
                    name=input_name,
                    input_type=StepRunInputArtifactType.DEFAULT,
                    session=session,
                )

            # Save output artifact IDs into the database.
            for output_name, artifact_version_ids in step_run.outputs.items():
                for artifact_version_id in artifact_version_ids:
                    self._set_run_step_output_artifact(
                        step_run_id=step_schema.id,
                        artifact_version_id=artifact_version_id,
                        name=output_name,
                        session=session,
                    )

            if step_run.status != ExecutionStatus.RUNNING:
                self._update_pipeline_run_status(
                    pipeline_run_id=step_run.pipeline_run_id, session=session
                )

            session.commit()

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

        Raises:
            KeyError: if the step run doesn't exist.
        """
        with Session(self.engine) as session:
            step_run = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == step_run_id)
            ).first()
            if step_run is None:
                raise KeyError(
                    f"Unable to get step run with ID {step_run_id}: No step "
                    "run with this ID found."
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
            query = select(StepRunSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=StepRunSchema,
                filter_model=step_run_filter_model,
                hydrate=hydrate,
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

        Raises:
            KeyError: if the step run doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if the step exists
            existing_step_run = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == step_run_id)
            ).first()
            if existing_step_run is None:
                raise KeyError(
                    f"Unable to update step with ID {step_run_id}: "
                    f"No step with this ID found."
                )

            # Update the step
            existing_step_run.update(step_run_update)
            session.add(existing_step_run)

            # Update the artifacts.
            for name, artifact_version_id in step_run_update.outputs.items():
                self._set_run_step_output_artifact(
                    step_run_id=step_run_id,
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
                    run_step_id=step_run_id,
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

    @staticmethod
    def _set_run_step_parent_step(
        child_id: UUID, parent_id: UUID, session: Session
    ) -> None:
        """Sets the parent step run for a step run.

        Args:
            child_id: The ID of the child step run to set the parent for.
            parent_id: The ID of the parent step run to set a child for.
            session: The database session to use.

        Raises:
            KeyError: if the child step run or parent step run doesn't exist.
        """
        # Check if the child step exists.
        child_step_run = session.exec(
            select(StepRunSchema).where(StepRunSchema.id == child_id)
        ).first()
        if child_step_run is None:
            raise KeyError(
                f"Unable to set parent step for step with ID "
                f"{child_id}: No step with this ID found."
            )

        # Check if the parent step exists.
        parent_step_run = session.exec(
            select(StepRunSchema).where(StepRunSchema.id == parent_id)
        ).first()
        if parent_step_run is None:
            raise KeyError(
                f"Unable to set parent step for step with ID "
                f"{child_id}: No parent step with ID {parent_id} "
                "found."
            )

        # Check if the parent step is already set.
        assignment = session.exec(
            select(StepRunParentsSchema)
            .where(StepRunParentsSchema.child_id == child_id)
            .where(StepRunParentsSchema.parent_id == parent_id)
        ).first()
        if assignment is not None:
            return

        # Save the parent step assignment in the database.
        assignment = StepRunParentsSchema(
            child_id=child_id, parent_id=parent_id
        )
        session.add(assignment)

    @staticmethod
    def _set_run_step_input_artifact(
        run_step_id: UUID,
        artifact_version_id: UUID,
        name: str,
        input_type: StepRunInputArtifactType,
        session: Session,
    ) -> None:
        """Sets an artifact as an input of a step run.

        Args:
            run_step_id: The ID of the step run.
            artifact_version_id: The ID of the artifact.
            name: The name of the input in the step run.
            input_type: In which way the artifact was loaded in the step.
            session: The database session to use.

        Raises:
            KeyError: if the step run or artifact doesn't exist.
        """
        # Check if the step exists.
        step_run = session.exec(
            select(StepRunSchema).where(StepRunSchema.id == run_step_id)
        ).first()
        if step_run is None:
            raise KeyError(
                f"Unable to set input artifact: No step run with ID "
                f"'{run_step_id}' found."
            )

        # Check if the artifact exists.
        artifact = session.exec(
            select(ArtifactVersionSchema).where(
                ArtifactVersionSchema.id == artifact_version_id
            )
        ).first()
        if artifact is None:
            raise KeyError(
                f"Unable to set input artifact: No artifact with ID "
                f"'{artifact_version_id}' found."
            )

        # Check if the input is already set.
        assignment = session.exec(
            select(StepRunInputArtifactSchema)
            .where(StepRunInputArtifactSchema.step_id == run_step_id)
            .where(
                StepRunInputArtifactSchema.artifact_id == artifact_version_id
            )
            .where(StepRunInputArtifactSchema.name == name)
        ).first()
        if assignment is not None:
            return

        # Save the input assignment in the database.
        assignment = StepRunInputArtifactSchema(
            step_id=run_step_id,
            artifact_id=artifact_version_id,
            name=name,
            type=input_type.value,
        )
        session.add(assignment)

    @staticmethod
    def _set_run_step_output_artifact(
        step_run_id: UUID,
        artifact_version_id: UUID,
        name: str,
        session: Session,
    ) -> None:
        """Sets an artifact as an output of a step run.

        Args:
            step_run_id: The ID of the step run.
            artifact_version_id: The ID of the artifact version.
            name: The name of the output in the step run.
            session: The database session to use.

        Raises:
            KeyError: if the step run or artifact doesn't exist.
        """
        # Check if the step exists.
        step_run = session.exec(
            select(StepRunSchema).where(StepRunSchema.id == step_run_id)
        ).first()
        if step_run is None:
            raise KeyError(
                f"Unable to set output artifact: No step run with ID "
                f"'{step_run_id}' found."
            )

        # Check if the artifact exists.
        artifact = session.exec(
            select(ArtifactVersionSchema).where(
                ArtifactVersionSchema.id == artifact_version_id
            )
        ).first()
        if artifact is None:
            raise KeyError(
                f"Unable to set output artifact: No artifact with ID "
                f"'{artifact_version_id}' found."
            )

        # Check if the output is already set.
        assignment = session.exec(
            select(StepRunOutputArtifactSchema)
            .where(StepRunOutputArtifactSchema.step_id == step_run_id)
            .where(
                StepRunOutputArtifactSchema.artifact_id == artifact_version_id
            )
        ).first()
        if assignment is not None:
            return

        # Save the output assignment in the database.
        assignment = StepRunOutputArtifactSchema(
            step_id=step_run_id,
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
            select(PipelineRunSchema).where(
                PipelineRunSchema.id == pipeline_run_id
            )
        ).one()
        step_runs = session.exec(
            select(StepRunSchema).where(
                StepRunSchema.pipeline_run_id == pipeline_run_id
            )
        ).all()

        # Deployment always exists for pipeline runs of newer versions
        assert pipeline_run.deployment
        num_steps = len(pipeline_run.deployment.to_model().step_configurations)
        new_status = get_pipeline_run_status(
            step_statuses=[
                ExecutionStatus(step_run.status) for step_run in step_runs
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
                run_update.end_time = datetime.utcnow()
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
                            OnboardingStep.PRODUCTION_SETUP_COMPLETED,
                        }
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
            # Verify that the given action exists
            self._get_action(action_id=trigger.action_id, session=session)

            if trigger.event_source_id:
                # Verify that the given event_source exists
                self._get_event_source(
                    event_source_id=trigger.event_source_id, session=session
                )

            # Verify that the action exists
            self._get_action(action_id=trigger.action_id, session=session)

            # Verify that the trigger name is unique
            self._fail_if_trigger_with_name_exists(
                trigger_name=trigger.name,
                workspace_id=trigger.workspace,
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

        Raises:
            KeyError: If the trigger doesn't exist.
        """
        with Session(self.engine) as session:
            trigger = session.exec(
                select(TriggerSchema).where(TriggerSchema.id == trigger_id)
            ).first()

            if trigger is None:
                raise KeyError(f"Trigger with ID {trigger_id} not found.")
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
            KeyError: If the trigger doesn't exist.
            ValueError: If both a schedule and an event source are provided.
        """
        with Session(self.engine) as session:
            # Check if trigger with the domain key (name, workspace, owner)
            # already exists
            existing_trigger = session.exec(
                select(TriggerSchema).where(TriggerSchema.id == trigger_id)
            ).first()
            if existing_trigger is None:
                raise KeyError(
                    f"Unable to update trigger with id '{trigger_id}': No "
                    f"existing trigger with this id exists."
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
            if trigger_update.name:
                if existing_trigger.name != trigger_update.name:
                    self._fail_if_trigger_with_name_exists(
                        trigger_name=trigger_update.name,
                        workspace_id=existing_trigger.workspace.id,
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

        Raises:
            KeyError: if the trigger doesn't exist.
        """
        with Session(self.engine) as session:
            try:
                trigger = session.exec(
                    select(TriggerSchema).where(TriggerSchema.id == trigger_id)
                ).one()

                if trigger is None:
                    raise KeyError(f"Trigger with ID {trigger_id} not found.")
                session.delete(trigger)
            except NoResultFound as error:
                raise KeyError from error

            session.commit()

    def _fail_if_trigger_with_name_exists(
        self,
        trigger_name: str,
        workspace_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a trigger with same name exists.

        Args:
            trigger_name: The Trigger name
            workspace_id: The workspace ID
            session: The Session

        Returns:
            None

        Raises:
            TriggerExistsError: If a trigger with the given name already exists.
        """
        existing_domain_trigger = session.exec(
            select(TriggerSchema)
            .where(TriggerSchema.name == trigger_name)
            .where(TriggerSchema.workspace_id == workspace_id)
        ).first()
        if existing_domain_trigger is not None:
            workspace = self._get_workspace_schema(
                workspace_name_or_id=workspace_id, session=session
            )
            raise TriggerExistsError(
                f"Unable to register trigger with name "
                f"'{trigger_name}': Found an existing trigger with the same "
                f"name in the active workspace, '{workspace.name}'."
            )
        return None

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
            # TODO: Verify that the given trigger exists
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

        Raises:
            KeyError: If the trigger execution doesn't exist.
        """
        with Session(self.engine) as session:
            execution = session.exec(
                select(TriggerExecutionSchema).where(
                    TriggerExecutionSchema.id == trigger_execution_id
                )
            ).first()

            if execution is None:
                raise KeyError(
                    f"Trigger execution with ID {trigger_execution_id} not found."
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

        Raises:
            KeyError: If the trigger execution doesn't exist.
        """
        with Session(self.engine) as session:
            try:
                execution = session.exec(
                    select(TriggerExecutionSchema).where(
                        TriggerExecutionSchema.id == trigger_execution_id
                    )
                ).one()

                session.delete(execution)
                session.commit()
            except NoResultFound:
                raise KeyError(
                    f"Execution with ID {trigger_execution_id} not found."
                )

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
            if sys.version_info < (3, 9):
                # For Python versions <3.9, leave out the third parameter to
                # _evaluate
                target_schema = schema_ref._evaluate(vars(zenml_schemas), {})
            elif sys.version_info >= (3, 12, 4):
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

    def _get_active_user(self, session: Session) -> UserSchema:
        """Get the active user.

        Depending on context, this is:

        - the user that is currently authenticated, when running in the ZenML
        server
        - the default admin user, when running in the ZenML client connected
        directly to a database

        Args:
            session: The database session to use for the query.

        Returns:
            The active user schema.

        Raises:
            KeyError: If no active user is found.
        """
        if handle_bool_env_var(ENV_ZENML_SERVER):
            # Running inside server
            from zenml.zen_server.auth import get_auth_context

            # If the code is running on the server, use the auth context.
            auth_context = get_auth_context()
            if auth_context is not None:
                return self._get_account_schema(
                    session=session, account_name_or_id=auth_context.user.id
                )

            raise KeyError("No active user found.")
        else:
            # If the code is running on the client, use the default user.
            admin_username = os.getenv(
                ENV_ZENML_DEFAULT_USER_NAME, DEFAULT_USERNAME
            )
            return self._get_account_schema(
                account_name_or_id=admin_username,
                session=session,
                service_account=False,
            )

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
                # Get the active account, depending on the context
                user = self._get_active_user(session=session)
            else:
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

    # ----------------------------- Workspaces -----------------------------

    @track_decorator(AnalyticsEvent.CREATED_WORKSPACE)
    def create_workspace(
        self, workspace: WorkspaceRequest
    ) -> WorkspaceResponse:
        """Creates a new workspace.

        Args:
            workspace: The workspace to create.

        Returns:
            The newly created workspace.

        Raises:
            EntityExistsError: If a workspace with the given name already exists.
        """
        with Session(self.engine) as session:
            # Check if workspace with the given name already exists
            existing_workspace = session.exec(
                select(WorkspaceSchema).where(
                    WorkspaceSchema.name == workspace.name
                )
            ).first()
            if existing_workspace is not None:
                raise EntityExistsError(
                    f"Unable to create workspace {workspace.name}: "
                    "A workspace with this name already exists."
                )

            # Create the workspace
            new_workspace = WorkspaceSchema.from_request(workspace)
            session.add(new_workspace)
            session.commit()

            # Explicitly refresh the new_workspace schema
            session.refresh(new_workspace)

            workspace_model = new_workspace.to_model(
                include_metadata=True, include_resources=True
            )

        self._get_or_create_default_stack(workspace=workspace_model)
        return workspace_model

    def get_workspace(
        self, workspace_name_or_id: Union[str, UUID], hydrate: bool = True
    ) -> WorkspaceResponse:
        """Get an existing workspace by name or ID.

        Args:
            workspace_name_or_id: Name or ID of the workspace to get.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The requested workspace if one was found.
        """
        with Session(self.engine) as session:
            workspace = self._get_workspace_schema(
                workspace_name_or_id, session=session
            )
        return workspace.to_model(
            include_metadata=hydrate, include_resources=True
        )

    def list_workspaces(
        self,
        workspace_filter_model: WorkspaceFilter,
        hydrate: bool = False,
    ) -> Page[WorkspaceResponse]:
        """List all workspace matching the given filter criteria.

        Args:
            workspace_filter_model: All filter parameters including pagination
                params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A list of all workspace matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(WorkspaceSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=WorkspaceSchema,
                filter_model=workspace_filter_model,
                hydrate=hydrate,
            )

    def update_workspace(
        self, workspace_id: UUID, workspace_update: WorkspaceUpdate
    ) -> WorkspaceResponse:
        """Update an existing workspace.

        Args:
            workspace_id: The ID of the workspace to be updated.
            workspace_update: The update to be applied to the workspace.

        Returns:
            The updated workspace.

        Raises:
            IllegalOperationError: if the workspace is the default workspace.
            KeyError: if the workspace does not exist.
        """
        with Session(self.engine) as session:
            existing_workspace = session.exec(
                select(WorkspaceSchema).where(
                    WorkspaceSchema.id == workspace_id
                )
            ).first()
            if existing_workspace is None:
                raise KeyError(
                    f"Unable to update workspace with id "
                    f"'{workspace_id}': Found no"
                    f"existing workspaces with this id."
                )
            if (
                existing_workspace.name == self._default_workspace_name
                and "name" in workspace_update.model_fields_set
                and workspace_update.name != existing_workspace.name
            ):
                raise IllegalOperationError(
                    "The name of the default workspace cannot be changed."
                )

            # Update the workspace
            existing_workspace.update(workspace_update=workspace_update)
            session.add(existing_workspace)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_workspace)
            return existing_workspace.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_workspace(self, workspace_name_or_id: Union[str, UUID]) -> None:
        """Deletes a workspace.

        Args:
            workspace_name_or_id: Name or ID of the workspace to delete.

        Raises:
            IllegalOperationError: If the workspace is the default workspace.
        """
        with Session(self.engine) as session:
            # Check if workspace with the given name exists
            workspace = self._get_workspace_schema(
                workspace_name_or_id, session=session
            )
            if workspace.name == self._default_workspace_name:
                raise IllegalOperationError(
                    "The default workspace cannot be deleted."
                )

            session.delete(workspace)
            session.commit()

    def _get_or_create_default_workspace(self) -> WorkspaceResponse:
        """Get or create the default workspace if it doesn't exist.

        Returns:
            The default workspace.
        """
        default_workspace_name = self._default_workspace_name

        try:
            return self.get_workspace(default_workspace_name)
        except KeyError:
            logger.info(
                f"Creating default workspace '{default_workspace_name}' ..."
            )
            return self.create_workspace(
                WorkspaceRequest(name=default_workspace_name)
            )

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
                return cast(AnyIdentifiedResponse, to_model(hydrate=True))
            else:
                raise RuntimeError("Unable to convert schema to model.")

    @staticmethod
    def _get_schema_by_name_or_id(
        object_name_or_id: Union[str, UUID],
        schema_class: Type[AnyNamedSchema],
        schema_name: str,
        session: Session,
    ) -> AnyNamedSchema:
        """Query a schema by its 'name' or 'id' field.

        Args:
            object_name_or_id: The name or ID of the object to query.
            schema_class: The schema class to query. E.g., `WorkspaceSchema`.
            schema_name: The name of the schema used for error messages.
                E.g., "workspace".
            session: The database session to use.

        Returns:
            The schema object.

        Raises:
            KeyError: if the object couldn't be found.
            ValueError: if the schema_name isn't provided.
        """
        if object_name_or_id is None:
            raise ValueError(
                f"Unable to get {schema_name}: No {schema_name} ID or name "
                "provided."
            )
        if uuid_utils.is_valid_uuid(object_name_or_id):
            filter_params = schema_class.id == object_name_or_id
            error_msg = (
                f"Unable to get {schema_name} with name or ID "
                f"'{object_name_or_id}': No {schema_name} with this ID found."
            )
        else:
            filter_params = schema_class.name == object_name_or_id
            error_msg = (
                f"Unable to get {schema_name} with name or ID "
                f"'{object_name_or_id}': '{object_name_or_id}' is not a valid "
                f" UUID and no {schema_name} with this name exists."
            )

        schema = session.exec(
            select(schema_class).where(filter_params)
        ).first()

        if schema is None:
            raise KeyError(error_msg)
        return schema

    def _get_workspace_schema(
        self,
        workspace_name_or_id: Union[str, UUID],
        session: Session,
    ) -> WorkspaceSchema:
        """Gets a workspace schema by name or ID.

        This is a helper method that is used in various places to find the
        workspace associated to some other object.

        Args:
            workspace_name_or_id: The name or ID of the workspace to get.
            session: The database session to use.

        Returns:
            The workspace schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=workspace_name_or_id,
            schema_class=WorkspaceSchema,
            schema_name="workspace",
            session=session,
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

    def _get_run_schema(
        self,
        run_name_or_id: Union[str, UUID],
        session: Session,
    ) -> PipelineRunSchema:
        """Gets a run schema by name or ID.

        This is a helper method that is used in various places to find a run
        by its name or ID.

        Args:
            run_name_or_id: The name or ID of the run to get.
            session: The database session to use.

        Returns:
            The run schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=run_name_or_id,
            schema_class=PipelineRunSchema,
            schema_name="run",
            session=session,
        )

    def _get_model_schema(
        self,
        model_name_or_id: Union[str, UUID],
        session: Session,
    ) -> ModelSchema:
        """Gets a model schema by name or ID.

        This is a helper method that is used in various places to find a model
        by its name or ID.

        Args:
            model_name_or_id: The name or ID of the model to get.
            session: The database session to use.

        Returns:
            The model schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=model_name_or_id,
            schema_class=ModelSchema,
            schema_name="model",
            session=session,
        )

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
            schema_name=TagSchema.__tablename__,
            session=session,
        )

    def _get_tag_model_schema(
        self,
        tag_id: UUID,
        resource_id: UUID,
        resource_type: TaggableResourceTypes,
        session: Session,
    ) -> TagResourceSchema:
        """Gets a tag model schema by tag and resource.

        Args:
            tag_id: The ID of the tag to get.
            resource_id: The ID of the resource to get.
            resource_type: The type of the resource to get.
            session: The database session to use.

        Returns:
            The tag resource schema.

        Raises:
            KeyError: if entity not found.
        """
        with Session(self.engine) as session:
            schema = session.exec(
                select(TagResourceSchema).where(
                    TagResourceSchema.tag_id == tag_id,
                    TagResourceSchema.resource_id == resource_id,
                    TagResourceSchema.resource_type == resource_type.value,
                )
            ).first()
            if schema is None:
                raise KeyError(
                    f"Unable to get {TagResourceSchema.__tablename__} with IDs "
                    f"`tag_id`='{tag_id}' and `resource_id`='{resource_id}' and "
                    f"`resource_type`='{resource_type.value}': No "
                    f"{TagResourceSchema.__tablename__} with these IDs found."
                )
            return schema

    @staticmethod
    def _create_or_reuse_code_reference(
        session: Session,
        workspace_id: UUID,
        code_reference: Optional["CodeReferenceRequest"],
    ) -> Optional[UUID]:
        """Creates or reuses a code reference.

        Args:
            session: The database session to use.
            workspace_id: ID of the workspace in which the code reference
                should be.
            code_reference: Request of the reference to create.

        Returns:
            The code reference ID.
        """
        if not code_reference:
            return None

        existing_reference = session.exec(
            select(CodeReferenceSchema)
            .where(CodeReferenceSchema.workspace_id == workspace_id)
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
            code_reference, workspace_id=workspace_id
        )

        session.add(new_reference)
        return new_reference.id

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
            model_schema = ModelSchema.from_request(model)
            session.add(model_schema)

            if model.tags:
                self._attach_tags_to_resource(
                    tag_names=model.tags,
                    resource_id=model_schema.id,
                    resource_type=TaggableResourceTypes.MODEL,
                )
            try:
                session.commit()
            except IntegrityError:
                raise EntityExistsError(
                    f"Unable to create model {model.name}: "
                    "A model with this name already exists."
                )

            return model_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def get_model(
        self,
        model_name_or_id: Union[str, UUID],
        hydrate: bool = True,
    ) -> ModelResponse:
        """Get an existing model.

        Args:
            model_name_or_id: name or id of the model to be retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Raises:
            KeyError: specified ID or name not found.

        Returns:
            The model of interest.
        """
        with Session(self.engine) as session:
            model = self._get_model_schema(
                model_name_or_id=model_name_or_id, session=session
            )
            if model is None:
                raise KeyError(
                    f"Unable to get model with ID `{model_name_or_id}`: "
                    f"No model with this ID found."
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
            query = select(ModelSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ModelSchema,
                filter_model=model_filter_model,
                hydrate=hydrate,
            )

    def delete_model(self, model_name_or_id: Union[str, UUID]) -> None:
        """Deletes a model.

        Args:
            model_name_or_id: name or id of the model to be deleted.

        Raises:
            KeyError: specified ID or name not found.
        """
        with Session(self.engine) as session:
            model = self._get_model_schema(
                model_name_or_id=model_name_or_id, session=session
            )
            if model is None:
                raise KeyError(
                    f"Unable to delete model with ID `{model_name_or_id}`: "
                    f"No model with this ID found."
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

            if model_update.add_tags:
                self._attach_tags_to_resource(
                    tag_names=model_update.add_tags,
                    resource_id=existing_model.id,
                    resource_type=TaggableResourceTypes.MODEL,
                )
            model_update.add_tags = None
            if model_update.remove_tags:
                self._detach_tags_from_resource(
                    tag_names=model_update.remove_tags,
                    resource_id=existing_model.id,
                    resource_type=TaggableResourceTypes.MODEL,
                )
            model_update.remove_tags = None

            existing_model.update(model_update=model_update)

            session.add(existing_model)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_model)
            return existing_model.to_model(
                include_metadata=True, include_resources=True
            )

    # ----------------------------- Model Versions -----------------------------

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

    def _model_version_exists(self, model_id: UUID, version: str) -> bool:
        """Check if a model version with a certain version exists.

        Args:
            model_id: The model ID of the version.
            version: The version name.

        Returns:
            If a model version with the given version name exists.
        """
        with Session(self.engine) as session:
            return (
                session.exec(
                    select(ModelVersionSchema.id)
                    .where(ModelVersionSchema.model_id == model_id)
                    .where(ModelVersionSchema.name == version)
                ).first()
                is not None
            )

    @track_decorator(AnalyticsEvent.CREATED_MODEL_VERSION)
    def create_model_version(
        self, model_version: ModelVersionRequest
    ) -> ModelVersionResponse:
        """Creates a new model version.

        Args:
            model_version: the Model Version to be created.

        Returns:
            The newly created model version.

        Raises:
            ValueError: If `number` is not None during model version creation.
            EntityExistsError: If a model version with the given name already
                exists.
            EntityCreationError: If the model version creation failed.
        """
        if model_version.number is not None:
            raise ValueError(
                "`number` field  must be None during model version creation."
            )

        model = self.get_model(model_version.model)

        has_custom_name = model_version.name is not None
        if has_custom_name:
            validate_name(model_version)

        model_version_id = None

        remaining_tries = MAX_RETRIES_FOR_VERSIONED_ENTITY_CREATION
        while remaining_tries > 0:
            remaining_tries -= 1
            try:
                with Session(self.engine) as session:
                    model_version.number = (
                        self._get_next_numeric_version_for_model(
                            session=session,
                            model_id=model.id,
                        )
                    )
                    if not has_custom_name:
                        model_version.name = str(model_version.number)

                    model_version_schema = ModelVersionSchema.from_request(
                        model_version
                    )
                    session.add(model_version_schema)
                    session.commit()

                    model_version_id = model_version_schema.id
                break
            except IntegrityError:
                if has_custom_name and self._model_version_exists(
                    model_id=model.id, version=cast(str, model_version.name)
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
                        "(version %s) due to an integrity error. "
                        "Retrying in %f seconds.",
                        model.name,
                        model_version.number,
                        sleep_duration,
                    )
                    time.sleep(sleep_duration)

        assert model_version_id
        if model_version.tags:
            self._attach_tags_to_resource(
                tag_names=model_version.tags,
                resource_id=model_version_id,
                resource_type=TaggableResourceTypes.MODEL_VERSION,
            )

        return self.get_model_version(model_version_id)

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

        Raises:
            KeyError: specified ID or name not found.
        """
        with Session(self.engine) as session:
            model_version = self._get_schema_by_name_or_id(
                object_name_or_id=model_version_id,
                schema_class=ModelVersionSchema,
                schema_name="model_version",
                session=session,
            )
            if model_version is None:
                raise KeyError(
                    f"Unable to get model version with ID "
                    f"`{model_version_id}`: No model version with this "
                    f"ID found."
                )
            return model_version.to_model(
                include_metadata=hydrate, include_resources=True
            )

    def list_model_versions(
        self,
        model_version_filter_model: ModelVersionFilter,
        model_name_or_id: Optional[Union[str, UUID]] = None,
        hydrate: bool = False,
    ) -> Page[ModelVersionResponse]:
        """Get all model versions by filter.

        Args:
            model_name_or_id: name or id of the model containing the model
                versions.
            model_version_filter_model: All filter parameters including
                pagination params.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            A page of all model versions.
        """
        with Session(self.engine) as session:
            if model_name_or_id:
                model = self.get_model(model_name_or_id)
                model_version_filter_model.set_scope_model(model.id)

            query = select(ModelVersionSchema)

            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ModelVersionSchema,
                filter_model=model_version_filter_model,
                hydrate=hydrate,
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
                select(ModelVersionSchema)
                .where(
                    ModelVersionSchema.model_id
                    == model_version_update_model.model
                )
                .where(ModelVersionSchema.id == model_version_id)
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
                        == model_version_update_model.model
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

            if model_version_update_model.add_tags:
                self._attach_tags_to_resource(
                    tag_names=model_version_update_model.add_tags,
                    resource_id=existing_model_version.id,
                    resource_type=TaggableResourceTypes.MODEL_VERSION,
                )
            if model_version_update_model.remove_tags:
                self._detach_tags_from_resource(
                    tag_names=model_version_update_model.remove_tags,
                    resource_id=existing_model_version.id,
                    resource_type=TaggableResourceTypes.MODEL_VERSION,
                )

            existing_model_version.update(
                target_stage=stage,
                target_name=model_version_update_model.name,
                target_description=model_version_update_model.description,
            )
            session.add(existing_model_version)
            session.commit()
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

    #################
    # Tags
    #################

    def _attach_tags_to_resource(
        self,
        tag_names: List[str],
        resource_id: UUID,
        resource_type: TaggableResourceTypes,
    ) -> None:
        """Creates a tag<>resource link if not present.

        Args:
            tag_names: The list of names of the tags.
            resource_id: The id of the resource.
            resource_type: The type of the resource to create link with.
        """
        for tag_name in tag_names:
            try:
                tag = self.get_tag(tag_name)
            except KeyError:
                tag = self.create_tag(TagRequest(name=tag_name))
            try:
                self.create_tag_resource(
                    TagResourceRequest(
                        tag_id=tag.id,
                        resource_id=resource_id,
                        resource_type=resource_type,
                    )
                )
            except EntityExistsError:
                pass

    def _detach_tags_from_resource(
        self,
        tag_names: List[str],
        resource_id: UUID,
        resource_type: TaggableResourceTypes,
    ) -> None:
        """Deletes tag<>resource link if present.

        Args:
            tag_names: The list of names of the tags.
            resource_id: The id of the resource.
            resource_type: The type of the resource to create link with.
        """
        for tag_name in tag_names:
            try:
                tag = self.get_tag(tag_name)
                self.delete_tag_resource(
                    tag_id=tag.id,
                    resource_id=resource_id,
                    resource_type=resource_type,
                )
            except KeyError:
                pass

    @track_decorator(AnalyticsEvent.CREATED_TAG)
    def create_tag(self, tag: TagRequest) -> TagResponse:
        """Creates a new tag.

        Args:
            tag: the tag to be created.

        Returns:
            The newly created tag.

        Raises:
            EntityExistsError: If a tag with the given name already exists.
        """
        validate_name(tag)
        with Session(self.engine) as session:
            existing_tag = session.exec(
                select(TagSchema).where(TagSchema.name == tag.name)
            ).first()
            if existing_tag is not None:
                raise EntityExistsError(
                    f"Unable to create tag {tag.name}: "
                    "A tag with this name already exists."
                )

            tag_schema = TagSchema.from_request(tag)
            session.add(tag_schema)

            session.commit()
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

        Raises:
            KeyError: specified ID or name not found.
        """
        with Session(self.engine) as session:
            tag = self._get_tag_schema(
                tag_name_or_id=tag_name_or_id, session=session
            )
            if tag is None:
                raise KeyError(
                    f"Unable to delete tag with ID `{tag_name_or_id}`: "
                    f"No tag with this ID found."
                )
            session.delete(tag)
            session.commit()

    def get_tag(
        self, tag_name_or_id: Union[str, UUID], hydrate: bool = True
    ) -> TagResponse:
        """Get an existing tag.

        Args:
            tag_name_or_id: name or id of the tag to be retrieved.
            hydrate: Flag deciding whether to hydrate the output model(s)
                by including metadata fields in the response.

        Returns:
            The tag of interest.

        Raises:
            KeyError: specified ID or name not found.
        """
        with Session(self.engine) as session:
            tag = self._get_tag_schema(
                tag_name_or_id=tag_name_or_id, session=session
            )
            if tag is None:
                raise KeyError(
                    f"Unable to get tag with ID `{tag_name_or_id}`: "
                    f"No tag with this ID found."
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
            KeyError: If the tag is not found
        """
        with Session(self.engine) as session:
            tag = self._get_tag_schema(
                tag_name_or_id=tag_name_or_id, session=session
            )

            if not tag:
                raise KeyError(f"Tag with ID `{tag_name_or_id}` not found.")

            tag.update(update=tag_update_model)
            session.add(tag)
            session.commit()

            # Refresh the tag that was just created
            session.refresh(tag)
            return tag.to_model(include_metadata=True, include_resources=True)

    ####################
    # Tags <> resources
    ####################

    def create_tag_resource(
        self, tag_resource: TagResourceRequest
    ) -> TagResourceResponse:
        """Creates a new tag resource relationship.

        Args:
            tag_resource: the tag resource relationship to be created.

        Returns:
            The newly created tag resource relationship.

        Raises:
            EntityExistsError: If a tag resource relationship with the given
                configuration already exists.
        """
        with Session(self.engine) as session:
            existing_tag_resource = session.exec(
                select(TagResourceSchema).where(
                    TagResourceSchema.tag_id == tag_resource.tag_id,
                    TagResourceSchema.resource_id == tag_resource.resource_id,
                    TagResourceSchema.resource_type
                    == tag_resource.resource_type.value,
                )
            ).first()
            if existing_tag_resource is not None:
                raise EntityExistsError(
                    f"Unable to create a tag "
                    f"{tag_resource.resource_type.name.lower()} "
                    f"relationship with IDs "
                    f"`{tag_resource.tag_id}`|`{tag_resource.resource_id}`. "
                    "This relationship already exists."
                )

            tag_resource_schema = TagResourceSchema.from_request(tag_resource)
            session.add(tag_resource_schema)

            session.commit()
            return tag_resource_schema.to_model(
                include_metadata=True, include_resources=True
            )

    def delete_tag_resource(
        self,
        tag_id: UUID,
        resource_id: UUID,
        resource_type: TaggableResourceTypes,
    ) -> None:
        """Deletes a tag resource relationship.

        Args:
            tag_id: The ID of the tag to delete.
            resource_id: The ID of the resource to delete.
            resource_type: The type of the resource to delete.

        Raises:
            KeyError: specified ID not found.
        """
        with Session(self.engine) as session:
            tag_model = self._get_tag_model_schema(
                tag_id=tag_id,
                resource_id=resource_id,
                resource_type=resource_type,
                session=session,
            )
            if tag_model is None:
                raise KeyError(
                    f"Unable to delete tag<>resource with IDs: "
                    f"`tag_id`='{tag_id}' and `resource_id`='{resource_id}' "
                    f"and `resource_type`='{resource_type.value}': No "
                    "tag<>resource with these IDs found."
                )
            session.delete(tag_model)
            session.commit()
