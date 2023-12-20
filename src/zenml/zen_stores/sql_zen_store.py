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
import re
import sys
from datetime import datetime
from functools import lru_cache
from pathlib import Path, PurePath
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    ForwardRef,
    List,
    Optional,
    Tuple,
    Type,
    TypeVar,
    Union,
    cast,
)
from uuid import UUID

import pymysql
from pydantic import SecretStr, root_validator, validator
from sqlalchemy import asc, desc, func, text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import (
    ArgumentError,
    IntegrityError,
    NoResultFound,
    OperationalError,
)
from sqlalchemy.orm import noload
from sqlmodel import Session, SQLModel, create_engine, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import analytics_disabler, track_decorator
from zenml.config.global_config import GlobalConfiguration
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
    TEXT_FIELD_MAX_LENGTH,
)
from zenml.enums import (
    AuthScheme,
    ExecutionStatus,
    LoggingLevels,
    ModelStages,
    SecretScope,
    SorterOps,
    StackComponentType,
    StepRunInputArtifactType,
    StepRunOutputArtifactType,
    StoreType,
    TaggableResourceTypes,
)
from zenml.exceptions import (
    AuthorizationException,
    EntityExistsError,
    IllegalOperationError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.logger import get_console_handler, get_logger, get_logging_level
from zenml.models import (
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
    BaseResponse,
    BaseResponseModel,
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
    ScheduleFilter,
    ScheduleRequest,
    ScheduleResponse,
    ScheduleUpdate,
    SecretFilterModel,
    SecretRequestModel,
    ServerDatabaseType,
    ServerModel,
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
    StackFilter,
    StackRequest,
    StackResponse,
    StackUpdate,
    StepRunFilter,
    StepRunRequest,
    StepRunResponse,
    StepRunUpdate,
    TagFilterModel,
    TagRequestModel,
    TagResourceRequestModel,
    TagResourceResponseModel,
    TagResponseModel,
    TagUpdateModel,
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
from zenml.models.v2.core.stack import InternalStackRequest
from zenml.service_connectors.service_connector_registry import (
    service_connector_registry,
)
from zenml.stack.flavor_registry import FlavorRegistry
from zenml.utils import uuid_utils
from zenml.utils.enum_utils import StrEnum
from zenml.utils.networking_utils import (
    replace_localhost_with_internal_hostname,
)
from zenml.utils.string_utils import random_str
from zenml.zen_stores.base_zen_store import (
    BaseZenStore,
)
from zenml.zen_stores.enums import StoreEvent
from zenml.zen_stores.migrations.alembic import (
    ZENML_ALEMBIC_START_REVISION,
    Alembic,
)
from zenml.zen_stores.schemas import (
    APIKeySchema,
    ArtifactSchema,
    ArtifactVersionSchema,
    BaseSchema,
    CodeReferenceSchema,
    CodeRepositorySchema,
    FlavorSchema,
    IdentitySchema,
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
    ScheduleSchema,
    ServiceConnectorSchema,
    StackComponentSchema,
    StackCompositionSchema,
    StackSchema,
    StepRunInputArtifactSchema,
    StepRunOutputArtifactSchema,
    StepRunParentsSchema,
    StepRunSchema,
    TagResourceSchema,
    TagSchema,
    UserSchema,
    WorkspaceSchema,
)
from zenml.zen_stores.schemas.artifact_visualization_schemas import (
    ArtifactVisualizationSchema,
)
from zenml.zen_stores.schemas.logs_schemas import LogsSchema
from zenml.zen_stores.secrets_stores.sql_secrets_store import (
    SqlSecretsStoreConfiguration,
)

AnyNamedSchema = TypeVar("AnyNamedSchema", bound=NamedSchema)
AnySchema = TypeVar("AnySchema", bound=BaseSchema)
B = TypeVar(
    "B",
    bound=Union[BaseResponse, BaseResponseModel],  # type: ignore[type-arg]
)

# Enable SQL compilation caching to remove the https://sqlalche.me/e/14/cprf
# warning
SelectOfScalar.inherit_cache = True
Select.inherit_cache = True


logger = get_logger(__name__)

ZENML_SQLITE_DB_FILENAME = "zenml.db"


def _is_mysql_missing_database_error(error: OperationalError) -> bool:
    """Checks if the given error is due to a missing database.

    Args:
        error: The error to check.

    Returns:
        If the error because the MySQL database doesn't exist.
    """
    from pymysql.constants.ER import BAD_DB_ERROR

    if not isinstance(error.orig, pymysql.err.OperationalError):
        return False

    error_code = cast(int, error.orig.args[0])
    return error_code == BAD_DB_ERROR


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

    secrets_store: Optional[SecretsStoreConfiguration] = None

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

    @validator("secrets_store")
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

    @root_validator(pre=True)
    def _remove_grpc_attributes(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Removes old GRPC attributes.

        Args:
            values: All model attribute values.

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
        grpc_values = [values.pop(key, None) for key in grpc_attribute_keys]
        if any(grpc_values):
            logger.warning(
                "The GRPC attributes %s are unused and will be removed soon. "
                "Please remove them from SQLZenStore configuration. This will "
                "become an error in future versions of ZenML."
            )

        return values

    @root_validator
    def _validate_url(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate the SQL URL.

        The validator also moves the MySQL username, password and database
        parameters from the URL into the other configuration arguments, if they
        are present in the URL.

        Args:
            values: The values to validate.

        Returns:
            The validated values.

        Raises:
            ValueError: If the URL is invalid or the SQL driver is not
                supported.
        """
        url = values.get("url")
        if url is None:
            return values

        # When running inside a container, if the URL uses localhost, the
        # target service will not be available. We try to replace localhost
        # with one of the special Docker or K3D internal hostnames.
        url = replace_localhost_with_internal_hostname(url)

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
        values["driver"] = SQLDatabaseDriver(sql_url.drivername)
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
            if values.get("username") or values.get("password"):
                raise ValueError(
                    "Invalid SQLite configuration: The username and password "
                    "must not be set",
                    url,
                )
            values["database"] = sql_url.database
        elif sql_url.drivername == SQLDatabaseDriver.MYSQL:
            if sql_url.username:
                values["username"] = sql_url.username
                sql_url = sql_url._replace(username=None)
            if sql_url.password:
                values["password"] = sql_url.password
                sql_url = sql_url._replace(password=None)
            if sql_url.database:
                values["database"] = sql_url.database
                sql_url = sql_url._replace(database=None)
            if sql_url.query:
                for k, v in sql_url.query.items():
                    if k == "ssl_ca":
                        values["ssl_ca"] = v
                    elif k == "ssl_cert":
                        values["ssl_cert"] = v
                    elif k == "ssl_key":
                        values["ssl_key"] = v
                    elif k == "ssl_verify_server_cert":
                        values["ssl_verify_server_cert"] = v
                    else:
                        raise ValueError(
                            "Invalid MySQL URL query parameter `%s`: The "
                            "parameter must be one of: ssl_ca, ssl_cert, "
                            "ssl_key, or ssl_verify_server_cert.",
                            k,
                        )
                sql_url = sql_url._replace(query={})

            database = values.get("database")
            if (
                not values.get("username")
                or not values.get("password")
                or not database
            ):
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
                content = values.get(key)
                if content and not os.path.isfile(content):
                    fileio.makedirs(str(secret_folder))
                    file_path = Path(secret_folder, f"{key}.pem")
                    with open(file_path, "w") as f:
                        f.write(content)
                    file_path.chmod(0o600)
                    values[key] = str(file_path)

        values["url"] = str(sql_url)
        return values

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

    @classmethod
    def copy_configuration(
        cls,
        config: "StoreConfiguration",
        config_path: str,
        load_config_path: Optional[PurePath] = None,
    ) -> "StoreConfiguration":
        """Copy the store config using a different configuration path.

        This method is used to create a copy of the store configuration that can
        be loaded using a different configuration path or in the context of a
        new environment, such as a container image.

        The configuration files accompanying the store configuration are also
        copied to the new configuration path (e.g. certificates etc.).

        Args:
            config: The store configuration to copy.
            config_path: new path where the configuration copy will be loaded
                from.
            load_config_path: absolute path that will be used to load the copied
                configuration. This can be set to a value different from
                `config_path` if the configuration copy will be loaded from
                a different environment, e.g. when the configuration is copied
                to a container image and loaded using a different absolute path.
                This will be reflected in the paths and URLs encoded in the
                copied configuration.

        Returns:
            A new store configuration object that reflects the new configuration
            path.
        """
        assert isinstance(config, SqlZenStoreConfiguration)
        config = config.copy()

        if config.driver == SQLDatabaseDriver.MYSQL:
            # Load the certificate values back into the configuration
            config.expand_certificates()

        elif config.driver == SQLDatabaseDriver.SQLITE:
            if load_config_path:
                config.url = cls.get_local_url(str(load_config_path))
            else:
                config.url = cls.get_local_url(config_path)

        return config

    def get_sqlmodel_config(
        self,
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Get the SQLModel engine configuration for the SQL ZenML store.

        Returns:
            The URL and connection arguments for the SQLModel engine.

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

            engine_args = {
                "pool_size": self.pool_size,
                "max_overflow": self.max_overflow,
                "pool_pre_ping": self.pool_pre_ping,
            }

            sql_url = sql_url._replace(
                drivername="mysql+pymysql",
                username=self.username,
                password=self.password,
                database=self.database,
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
                sqlalchemy_ssl_args[
                    "check_hostname"
                ] = self.ssl_verify_server_cert
                sqlalchemy_connect_args["ssl"] = sqlalchemy_ssl_args
        else:
            raise NotImplementedError(
                f"SQL driver `{sql_url.drivername}` is not supported."
            )

        return str(sql_url), sqlalchemy_connect_args, engine_args

    class Config:
        """Pydantic configuration class."""

        # Don't validate attributes when assigning them. This is necessary
        # because the certificate attributes can be expanded to the contents
        # of the certificate files.
        validate_assignment = False
        # Forbid extra attributes set in the class.
        extra = "forbid"


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
    _alembic: Optional[Alembic] = None

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

    @classmethod
    def filter_and_paginate(
        cls,
        session: Session,
        query: Union[Select[AnySchema], SelectOfScalar[AnySchema]],
        table: Type[AnySchema],
        filter_model: BaseFilter,
        custom_schema_to_model_conversion: Optional[
            Callable[[AnySchema], B]
        ] = None,
        custom_fetch: Optional[
            Callable[
                [
                    Session,
                    Union[Select[AnySchema], SelectOfScalar[AnySchema]],
                    BaseFilter,
                ],
                List[AnySchema],
            ]
        ] = None,
        hydrate: bool = False,
    ) -> Page[B]:
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

        # Get the total amount of items in the database for a given query
        if custom_fetch:
            total = len(custom_fetch(session, query, filter_model))
        else:
            total = session.scalar(
                select([func.count("*")]).select_from(
                    query.options(noload("*")).subquery()
                )
            )

        # Sorting
        column, operand = filter_model.sorting_params
        if operand == SorterOps.DESCENDING:
            query = query.order_by(desc(getattr(table, column)))
        else:
            query = query.order_by(asc(getattr(table, column)))

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
        item_schemas: List[AnySchema]
        if custom_fetch:
            item_schemas = custom_fetch(session, query, filter_model)
            # select the items in the current page
            item_schemas = item_schemas[
                filter_model.offset : filter_model.offset + filter_model.size
            ]
        else:
            item_schemas = (
                session.exec(
                    query.limit(filter_model.size).offset(filter_model.offset)
                )
                .unique()
                .all()
            )

        # Convert this page of items from schemas to models.
        items: List[B] = []
        for schema in item_schemas:
            # If a custom conversion function is provided, use it.
            if custom_schema_to_model_conversion:
                items.append(custom_schema_to_model_conversion(schema))
                continue
            # Otherwise, try to use the `to_model` method of the schema.
            to_model = getattr(schema, "to_model", None)
            if callable(to_model):
                items.append(to_model(hydrate=hydrate))
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
        """Initialize the SQL store.

        Raises:
            OperationalError: If connecting to the database failed.
        """
        logger.debug("Initializing SqlZenStore at %s", self.config.url)

        url, connect_args, engine_args = self.config.get_sqlmodel_config()
        self._engine = create_engine(
            url=url, connect_args=connect_args, **engine_args
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
            try:
                self._engine.connect()
            except OperationalError as e:
                logger.debug(
                    "Failed to connect to mysql database `%s`.",
                    self._engine.url.database,
                )

                if _is_mysql_missing_database_error(e):
                    self._create_mysql_database(
                        url=self._engine.url,
                        connect_args=connect_args,
                        engine_args=engine_args,
                    )
                else:
                    raise

        self._alembic = Alembic(self.engine)
        if (
            not self.skip_migrations
            and ENV_ZENML_DISABLE_DATABASE_MIGRATION not in os.environ
        ):
            self.migrate_database()

    def _initialize_database(self) -> None:
        """Initialize the database on first use."""
        self._get_or_create_default_workspace()

        config = ServerConfiguration.get_server_config()
        # If the auth scheme is external, don't create the default user
        if config.auth_scheme != AuthScheme.EXTERNAL:
            self._get_or_create_default_user()

    def _create_mysql_database(
        self,
        url: URL,
        connect_args: Dict[str, Any],
        engine_args: Dict[str, Any],
    ) -> None:
        """Creates a mysql database.

        Args:
            url: The URL of the database to create.
            connect_args: Connect arguments for the SQLAlchemy engine.
            engine_args: Additional initialization arguments for the SQLAlchemy
                engine
        """
        logger.info("Trying to create database %s.", url.database)
        master_url = url._replace(database=None)
        master_engine = create_engine(
            url=master_url, connect_args=connect_args, **engine_args
        )
        query = f"CREATE DATABASE IF NOT EXISTS {self.config.database}"
        try:
            connection = master_engine.connect()
            connection.execute(text(query))
        finally:
            connection.close()

    def migrate_database(self) -> None:
        """Migrate the database to the head as defined by the python package."""
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
        # 2. the database is not empty, but has never been migrated with alembic
        #   before (i.e. was created with SQLModel back when alembic wasn't
        #   used)
        # 3. the database is not empty and has been migrated with alembic before
        revisions = self.alembic.current_revisions()
        if len(revisions) >= 1:
            if len(revisions) > 1:
                logger.warning(
                    "The ZenML database has more than one migration head "
                    "revision. This is not expected and might indicate a "
                    "database migration problem. Please raise an issue on "
                    "GitHub if you encounter this."
                )
            # Case 3: the database has been migrated with alembic before. Just
            # upgrade to the latest revision.
            self.alembic.upgrade()
        else:
            if self.alembic.db_is_empty():
                # Case 1: the database is empty. We can just create the
                # tables from scratch with from SQLModel. After tables are
                # created we put an alembic revision to latest and populate
                # identity table with needed info.
                logger.info("Creating database tables")
                with self.engine.begin() as conn:
                    conn.run_callable(
                        SQLModel.metadata.create_all  # type: ignore[arg-type]
                    )
                with Session(self.engine) as session:
                    session.add(
                        IdentitySchema(
                            id=str(GlobalConfiguration().user_id).replace(
                                "-", ""
                            )
                        )
                    )
                    session.commit()
                self.alembic.stamp("head")
            else:
                # Case 2: the database is not empty, but has never been
                # migrated with alembic before. We need to create the alembic
                # version table, initialize it with the first revision where we
                # introduced alembic and then upgrade to the latest revision.
                self.alembic.stamp(ZENML_ALEMBIC_START_REVISION)
                self.alembic.upgrade()

        # If an alembic migration took place, all non-custom flavors are purged
        #  and the FlavorRegistry recreates all in-built and integration
        #  flavors in the db.
        revisions_afterwards = self.alembic.current_revisions()

        if revisions != revisions_afterwards:
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
        # Fetch the deployment ID from the database and use it to replace
        # the one fetched from the global configuration
        model.id = self.get_deployment_id()

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
            identity = session.exec(select(IdentitySchema)).first()

            if identity is None:
                raise KeyError(
                    "The deployment ID could not be loaded from the database."
                )
            return identity.id

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

            api_key_model = new_api_key.to_model(hydrate=True)
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
            return api_key.to_model(hydrate=hydrate)

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
            return api_key.to_internal_model(hydrate=hydrate)

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
            return api_key.to_model(hydrate=True)

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
            return api_key.to_model(hydrate=True)

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
            session.add(artifact_schema)
            session.commit()
            return artifact_schema.to_model(hydrate=True)

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
            return artifact.to_model(hydrate=hydrate)

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
            return existing_artifact.to_model(hydrate=True)

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

    def create_artifact_version(
        self, artifact_version: ArtifactVersionRequest
    ) -> ArtifactVersionResponse:
        """Creates an artifact version.

        Args:
            artifact_version: The artifact version to create.

        Returns:
            The created artifact version.

        Raises:
            EntityExistsError: if an artifact with the same name and version
                already exists.
        """
        with Session(self.engine) as session:
            # Check if an artifact with the given name and version exists
            existing_artifact = session.exec(
                select(ArtifactVersionSchema)
                .where(
                    ArtifactVersionSchema.artifact_id
                    == artifact_version.artifact_id
                )
                .where(
                    ArtifactVersionSchema.version == artifact_version.version
                )
            ).first()
            if existing_artifact is not None:
                raise EntityExistsError(
                    f"Unable to create artifact with name "
                    f"'{existing_artifact.artifact.name}' and version "
                    f"'{artifact_version.version}': An artifact with the same "
                    "name and version already exists."
                )

            # Create the artifact version.
            artifact_version_schema = ArtifactVersionSchema.from_request(
                artifact_version
            )
            session.add(artifact_version_schema)

            # Save visualizations of the artifact.
            if artifact_version.visualizations:
                for vis in artifact_version.visualizations:
                    vis_schema = ArtifactVisualizationSchema.from_model(
                        artifact_visualization_request=vis,
                        artifact_version_id=artifact_version_schema.id,
                    )
                    session.add(vis_schema)

            # Save tags of the artifact.
            if artifact_version.tags:
                self._attach_tags_to_resource(
                    tag_names=artifact_version.tags,
                    resource_id=artifact_version_schema.id,
                    resource_type=TaggableResourceTypes.ARTIFACT_VERSION,
                )

            session.commit()
            return artifact_version_schema.to_model(hydrate=True)

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
                    f"{artifact_version_id}: No artifact versionwith this ID "
                    f"found."
                )
            return artifact_version.to_model(hydrate=hydrate)

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
            if artifact_version_filter_model.only_unused:
                query = query.where(
                    ArtifactVersionSchema.id.notin_(  # type: ignore[attr-defined]
                        select(StepRunOutputArtifactSchema.artifact_id)
                    )
                )
                query = query.where(
                    ArtifactVersionSchema.id.notin_(  # type: ignore[attr-defined]
                        select(StepRunInputArtifactSchema.artifact_id)
                    )
                )
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
            return existing_artifact_version.to_model(hydrate=True)

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
            return artifact_visualization.to_model(hydrate=hydrate)

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
            return code_reference.to_model(hydrate=hydrate)

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

            return new_repo.to_model(hydrate=True)

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

            return repo.to_model(hydrate=hydrate)

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

            return existing_repo.to_model(hydrate=True)

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
        with Session(self.engine) as session:
            self._fail_if_component_with_name_type_exists(
                name=component.name,
                component_type=component.type,
                workspace_id=component.workspace,
                session=session,
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

            # Create the component
            new_component = StackComponentSchema(
                name=component.name,
                workspace_id=component.workspace,
                user_id=component.user,
                component_spec_path=component.component_spec_path,
                type=component.type,
                flavor=component.flavor,
                configuration=base64.b64encode(
                    json.dumps(component.configuration).encode("utf-8")
                ),
                labels=base64.b64encode(
                    json.dumps(component.labels).encode("utf-8")
                ),
                connector=service_connector,
                connector_resource_id=component.connector_resource_id,
            )

            session.add(new_component)
            session.commit()

            session.refresh(new_component)

            return new_component.to_model(hydrate=True)

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

            return stack_component.to_model(hydrate=hydrate)

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
            paged_components: Page[
                ComponentResponse
            ] = self.filter_and_paginate(
                session=session,
                query=query,
                table=StackComponentSchema,
                filter_model=component_filter_model,
                hydrate=hydrate,
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
                        component_type=existing_component.type,
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

            return existing_component.to_model(hydrate=True)

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

            device_model = new_device.to_internal_model(hydrate=True)
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

            return device.to_model(hydrate=hydrate)

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

            return device.to_internal_model(hydrate=hydrate)

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

            return existing_device.to_model(hydrate=True)

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

            device_model = existing_device.to_internal_model(hydrate=True)
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

                return new_flavor.to_model(hydrate=True)

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
            return flavor_in_db.to_model(hydrate=hydrate)

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
            return existing_flavor.to_model(hydrate=True)

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
            return logs.to_model(hydrate=hydrate)

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
            # Check if pipeline with the given name already exists
            existing_pipeline = session.exec(
                select(PipelineSchema)
                .where(PipelineSchema.name == pipeline.name)
                .where(PipelineSchema.version == pipeline.version)
                .where(PipelineSchema.workspace_id == pipeline.workspace)
            ).first()
            if existing_pipeline is not None:
                raise EntityExistsError(
                    f"Unable to create pipeline in workspace "
                    f"'{pipeline.workspace}': A pipeline with this name and "
                    f"version already exists."
                )

            # Create the pipeline
            new_pipeline = PipelineSchema.from_request(pipeline)
            session.add(new_pipeline)
            session.commit()
            session.refresh(new_pipeline)

            return new_pipeline.to_model(hydrate=True)

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

            return pipeline.to_model(hydrate=hydrate)

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
            query = select(PipelineSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=PipelineSchema,
                filter_model=pipeline_filter_model,
                hydrate=hydrate,
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

            # Update the pipeline
            existing_pipeline.update(pipeline_update)

            session.add(existing_pipeline)
            session.commit()

            return existing_pipeline.to_model(hydrate=True)

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

            return new_build.to_model(hydrate=True)

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

            return build.to_model(hydrate=hydrate)

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

            return new_deployment.to_model(hydrate=True)

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

            return deployment.to_model(hydrate=hydrate)

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

    # ----------------------------- Pipeline runs -----------------------------

    def create_run(
        self, pipeline_run: PipelineRunRequest
    ) -> PipelineRunResponse:
        """Creates a pipeline run.

        Args:
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

        Raises:
            EntityExistsError: If an identical pipeline run already exists.
        """
        with Session(self.engine) as session:
            # Check if pipeline run with same name already exists.
            existing_domain_run = session.exec(
                select(PipelineRunSchema).where(
                    PipelineRunSchema.name == pipeline_run.name
                )
            ).first()
            if existing_domain_run is not None:
                raise EntityExistsError(
                    f"Unable to create pipeline run: A pipeline run with name "
                    f"'{pipeline_run.name}' already exists."
                )

            # Check if pipeline run with same ID already exists.
            existing_id_run = session.exec(
                select(PipelineRunSchema).where(
                    PipelineRunSchema.id == pipeline_run.id
                )
            ).first()
            if existing_id_run is not None:
                raise EntityExistsError(
                    f"Unable to create pipeline run: A pipeline run with ID "
                    f"'{pipeline_run.id}' already exists."
                )

            # Create the pipeline run
            new_run = PipelineRunSchema.from_request(pipeline_run)
            session.add(new_run)
            session.commit()

            return new_run.to_model(hydrate=True)

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
            ).to_model(hydrate=hydrate)

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

            # Update the pipeline run
            existing_run.update(run_update=run_update)
            session.add(existing_run)
            session.commit()

            session.refresh(existing_run)
            return existing_run.to_model(hydrate=True)

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

    def get_or_create_run(
        self, pipeline_run: PipelineRunRequest
    ) -> Tuple[PipelineRunResponse, bool]:
        """Gets or creates a pipeline run.

        If a run with the same ID or name already exists, it is returned.
        Otherwise, a new run is created.

        Args:
            pipeline_run: The pipeline run to get or create.

        Returns:
            The pipeline run, and a boolean indicating whether the run was
            created or not.
        """
        # We want to have the 'create' statement in the try block since running
        # it first will reduce concurrency issues.
        try:
            return self.create_run(pipeline_run), True
        except (EntityExistsError, IntegrityError):
            # Catch both `EntityExistsError`` and `IntegrityError`` exceptions
            # since either one can be raised by the database when trying
            # to create a new pipeline run with duplicate ID or name.
            try:
                return self.get_run(pipeline_run.id), False
            except KeyError:
                return self.get_run(pipeline_run.name), False

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
                return_value.append(run_metadata_schema.to_model(hydrate=True))
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
            return run_metadata.to_model(hydrate=hydrate)

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
            return new_schedule.to_model(hydrate=True)

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
            return schedule.to_model(hydrate=hydrate)

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
            return existing_schedule.to_model(hydrate=True)

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
            try:
                self._get_account_schema(
                    service_account.name, session=session, service_account=True
                )
                raise EntityExistsError(
                    f"Unable to create service account with name "
                    f"'{service_account.name}': Found existing service "
                    "account with this name."
                )
            except KeyError:
                pass

            # Create the service account
            new_account = UserSchema.from_service_account_request(
                service_account
            )
            session.add(new_account)
            session.commit()

            return new_account.to_service_account_model(hydrate=True)

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

            return account.to_service_account_model(hydrate=hydrate)

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
            paged_service_accounts: Page[
                ServiceAccountResponse
            ] = self.filter_and_paginate(
                session=session,
                query=query,
                table=UserSchema,
                filter_model=filter_model,
                custom_schema_to_model_conversion=lambda user: user.to_service_account_model(
                    hydrate=hydrate
                ),
                hydrate=hydrate,
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
                hydrate=True
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
                if secret_id and self.secrets_store:
                    try:
                        self.secrets_store.delete_secret(secret_id)
                    except Exception:
                        # Ignore any errors that occur while deleting the
                        # secret
                        pass

                raise

            connector = new_service_connector.to_model(hydrate=True)
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

            connector = service_connector.to_model(hydrate=hydrate)
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
        ) -> List[ServiceConnectorSchema]:
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
            paged_connectors: Page[
                ServiceConnectorResponse
            ] = self.filter_and_paginate(
                session=session,
                query=query,
                table=ServiceConnectorSchema,
                filter_model=filter_model,
                custom_fetch=fetch_connectors,
                hydrate=hydrate,
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
                hydrate=True
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

            connector = existing_connector.to_model(hydrate=True)
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

                if service_connector.secret_id and self.secrets_store:
                    try:
                        self.secrets_store.delete_secret(
                            service_connector.secret_id
                        )
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

        Raises:
            NotImplementedError: If a secrets store is not configured or
                supported.
        """
        if not secrets:
            return None

        if not self.secrets_store:
            raise NotImplementedError(
                "A secrets store is not configured or supported."
            )

        # Generate a unique name for the secret
        # Replace all non-alphanumeric characters with a dash because
        # the secret name must be a valid DNS subdomain name in some
        # secrets stores
        connector_name = re.sub(r"[^a-zA-Z0-9-]", "-", connector_name)
        # Generate unique names using a random suffix until we find a name
        # that is not already in use
        while True:
            secret_name = f"connector-{connector_name}-{random_str(4)}".lower()
            existing_secrets = self.secrets_store.list_secrets(
                SecretFilterModel(
                    name=secret_name,
                )
            )
            if not existing_secrets.size:
                try:
                    return self.secrets_store.create_secret(
                        SecretRequestModel(
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
    ) -> List[ServiceConnectorSchema]:
        """Refine a service connector query.

        Applies resource type and label filters to the query.

        Args:
            session: The database session.
            query: The query to filter.
            filter_model: The filter model.

        Returns:
            The filtered list of service connectors.
        """
        items: List[ServiceConnectorSchema] = (
            session.exec(query).unique().all()
        )

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

        Raises:
            NotImplementedError: If a secrets store is not configured or
                supported.
        """
        if not self.secrets_store:
            raise NotImplementedError(
                "A secrets store is not configured or supported."
            )

        if updated_connector.secrets is None:
            # If the connector update does not contain a secrets update, keep
            # the existing secret (if any)
            return existing_connector.secret_id

        # Delete the existing secret (if any), to be replaced by the new secret
        if existing_connector.secret_id:
            try:
                self.secrets_store.delete_secret(existing_connector.secret_id)
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
        """Register a new stack.

        Args:
            stack: The stack to register.

        Returns:
            The registered stack.
        """
        with Session(self.engine) as session:
            self._fail_if_stack_with_name_exists(stack=stack, session=session)

            # Get the Schemas of all components mentioned
            component_ids = (
                [
                    component_id
                    for list_of_component_ids in stack.components.values()
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
            )

            session.add(new_stack_schema)
            session.commit()
            session.refresh(new_stack_schema)

            return new_stack_schema.to_model(hydrate=True)

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
            return stack.to_model(hydrate=hydrate)

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
            if stack_filter_model.component_id:
                query = query.where(
                    StackCompositionSchema.stack_id == StackSchema.id
                ).where(
                    StackCompositionSchema.component_id
                    == stack_filter_model.component_id
                )
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
                        stack=stack_update, session=session
                    )

            components = []
            if stack_update.components:
                filters = [
                    (StackComponentSchema.id == component_id)
                    for list_of_component_ids in stack_update.components.values()
                    for component_id in list_of_component_ids
                ]
                components = session.exec(
                    select(StackComponentSchema).where(or_(*filters))
                ).all()

            existing_stack.update(
                stack_update=stack_update,
                components=components,
            )

            session.add(existing_stack)
            session.commit()
            session.refresh(existing_stack)

            return existing_stack.to_model(hydrate=True)

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
        stack: StackRequest,
        session: Session,
    ) -> None:
        """Raise an exception if a stack with same name exists.

        Args:
            stack: The Stack
            session: The Session

        Returns:
            None

        Raises:
            StackExistsError: If a stack with the given name already exists.
        """
        existing_domain_stack = session.exec(
            select(StackSchema)
            .where(StackSchema.name == stack.name)
            .where(StackSchema.workspace_id == stack.workspace)
        ).first()
        if existing_domain_stack is not None:
            workspace = self._get_workspace_schema(
                workspace_name_or_id=stack.workspace, session=session
            )
            raise StackExistsError(
                f"Unable to register stack with name "
                f"'{stack.name}': Found an existing stack with the same "
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

            stack = InternalStackRequest(
                # Passing `None` for the user here means the stack is owned by
                # the server, which for RBAC indicates that everyone can read it
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
                    f"Unable to create step '{step_run.name}': No pipeline run "
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
                    f"Unable to create step '{step_run.name}': A step with "
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
            for output_name, artifact_version_id in step_run.outputs.items():
                self._set_run_step_output_artifact(
                    step_run_id=step_schema.id,
                    artifact_version_id=artifact_version_id,
                    name=output_name,
                    output_type=StepRunOutputArtifactType.DEFAULT,
                    session=session,
                )

            if step_run.status != ExecutionStatus.RUNNING:
                self._update_pipeline_run_status(
                    pipeline_run_id=step_run.pipeline_run_id, session=session
                )

            session.commit()

            return step_schema.to_model(hydrate=True)

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
            return step_run.to_model(hydrate=hydrate)

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

            # Update the output artifacts.
            for name, artifact_version_id in step_run_update.outputs.items():
                self._set_run_step_output_artifact(
                    step_run_id=step_run_id,
                    artifact_version_id=artifact_version_id,
                    name=name,
                    output_type=StepRunOutputArtifactType.DEFAULT,
                    session=session,
                )

            # Update saved artifacts
            for (
                artifact_name,
                artifact_version_id,
            ) in step_run_update.saved_artifact_versions.items():
                self._set_run_step_output_artifact(
                    step_run_id=step_run_id,
                    artifact_version_id=artifact_version_id,
                    name=artifact_name,
                    output_type=StepRunOutputArtifactType.MANUAL,
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

            return existing_step_run.to_model(hydrate=True)

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
            type=input_type,
        )
        session.add(assignment)

    @staticmethod
    def _set_run_step_output_artifact(
        step_run_id: UUID,
        artifact_version_id: UUID,
        name: str,
        output_type: StepRunOutputArtifactType,
        session: Session,
    ) -> None:
        """Sets an artifact as an output of a step run.

        Args:
            step_run_id: The ID of the step run.
            artifact_version_id: The ID of the artifact version.
            name: The name of the output in the step run.
            output_type: In which way the artifact was saved by the step.
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
            type=output_type,
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
            step_statuses=[step_run.status for step_run in step_runs],
            num_steps=num_steps,
        )

        if new_status != pipeline_run.status:
            pipeline_run.status = new_status
            if new_status in {
                ExecutionStatus.COMPLETED,
                ExecutionStatus.FAILED,
            }:
                pipeline_run.end_time = datetime.utcnow()

            session.add(pipeline_run)

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
            # are deleted automatically when the user is deleted. Secrets in
            # particular are left out because they are automatically deleted
            # even when stored in an external secret store.
            ["api_keys", "auth_devices", "secrets"]
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
            count = session.scalar(
                select([func.count("*")])
                .select_from(schema)
                .where(getattr(schema, resource_attr) == account.id)
            )
            if count > 0:
                logger.debug(
                    f"User {account.name} owns {count} resources of type "
                    f"{schema.__tablename__}"
                )
                return True

        return False

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
            try:
                self._get_account_schema(
                    user.name,
                    session=session,
                    # Filter out service accounts
                    service_account=False,
                )
                raise EntityExistsError(
                    f"Unable to create user with name '{user.name}': "
                    f"Found an existing user account with this name."
                )
            except KeyError:
                pass

            # Create the user
            new_user = UserSchema.from_user_request(user)
            session.add(new_user)
            session.commit()
            return new_user.to_model(hydrate=True)

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
        if not user_name_or_id:
            user_name_or_id = self._default_user_name

        with Session(self.engine) as session:
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
                include_private=include_private, hydrate=hydrate
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
                user_update.name is not None
                and user_update.name != existing_user.name
            ):
                if existing_user.name == self._default_user_name:
                    raise IllegalOperationError(
                        "The username of the default user account cannot be "
                        "changed."
                    )

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

            existing_user.update_user(user_update=user_update)
            session.add(existing_user)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_user)
            return existing_user.to_model(hydrate=True)

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
            if user.name == self._default_user_name:
                raise IllegalOperationError(
                    "The default user account cannot be deleted."
                )
            if self._account_owns_resources(user, session=session):
                raise IllegalOperationError(
                    "The user account has already been used to create "
                    "other resources that it now owns and therefore cannot be "
                    "deleted. Please delete all resources owned by the user "
                    "account or consider deactivating it instead."
                )

            self._trigger_event(StoreEvent.USER_DELETED, user_id=user.id)

            session.delete(user)
            session.commit()

    @property
    def _default_user_name(self) -> str:
        """Get the default user name.

        Returns:
            The default user name.
        """
        return os.getenv(ENV_ZENML_DEFAULT_USER_NAME, DEFAULT_USERNAME)

    def _get_or_create_default_user(self) -> UserResponse:
        """Get or create the default user if it doesn't exist.

        Returns:
            The default user.
        """
        default_user_name = self._default_user_name
        try:
            return self.get_user(default_user_name)
        except KeyError:
            password = os.getenv(
                ENV_ZENML_DEFAULT_USER_PASSWORD, DEFAULT_PASSWORD
            )

            logger.info(f"Creating default user '{default_user_name}' ...")
            return self.create_user(
                UserRequest(
                    name=default_user_name,
                    active=True,
                    password=password,
                )
            )

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

            workspace_model = new_workspace.to_model(hydrate=True)

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
        return workspace.to_model(hydrate=hydrate)

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
                and "name" in workspace_update.__fields_set__
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
            return existing_workspace.to_model(hydrate=True)

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

            self._trigger_event(
                StoreEvent.WORKSPACE_DELETED, workspace_id=workspace.id
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
            query = select([func.count(schema.id)])

            if filter_model:
                query = filter_model.apply_filter(query=query, table=schema)

            entity_count = session.scalar(query)

        return int(entity_count)

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
            EntityExistsError: If a workspace with the given name already exists.
        """
        with Session(self.engine) as session:
            existing_model = session.exec(
                select(ModelSchema).where(ModelSchema.name == model.name)
            ).first()
            if existing_model is not None:
                raise EntityExistsError(
                    f"Unable to create model {model.name}: "
                    "A model with this name already exists."
                )

            model_schema = ModelSchema.from_request(model)
            session.add(model_schema)

            if model.tags:
                self._attach_tags_to_resource(
                    tag_names=model.tags,
                    resource_id=model_schema.id,
                    resource_type=TaggableResourceTypes.MODEL,
                )
            session.commit()
            return model_schema.to_model(hydrate=True)

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
            return model.to_model(hydrate=hydrate)

    def list_models(
        self, model_filter_model: ModelFilter, hydrate: bool = False
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
            return existing_model.to_model(hydrate=True)

    # ----------------------------- Model Versions -----------------------------

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
            EntityExistsError: If a workspace with the given name already exists.
        """
        if model_version.number is not None:
            raise ValueError(
                "`number` field  must be None during model version creation."
            )
        with Session(self.engine) as session:
            model = self.get_model(model_version.model)
            existing_model_version = session.exec(
                select(ModelVersionSchema)
                .where(ModelVersionSchema.model_id == model.id)
                .where(ModelVersionSchema.name == model_version.name)
            ).first()
            if existing_model_version is not None:
                raise EntityExistsError(
                    f"Unable to create model version {model_version.name}: "
                    f"A model version with this name already exists in {model.name} model."
                )

            all_versions = session.exec(
                select(ModelVersionSchema)
                .where(ModelVersionSchema.model_id == model.id)
                .order_by(ModelVersionSchema.number.desc())  # type: ignore[attr-defined]
            ).first()

            model_version.number = (
                all_versions.number + 1 if all_versions else 1
            )

            if model_version.name is None:
                model_version.name = str(model_version.number)

            model_version_schema = ModelVersionSchema.from_request(
                model_version
            )
            session.add(model_version_schema)

            if model_version.tags:
                self._attach_tags_to_resource(
                    tag_names=model_version.tags,
                    resource_id=model_version_schema.id,
                    resource_type=TaggableResourceTypes.MODEL_VERSION,
                )

            session.commit()
            return model_version_schema.to_model(hydrate=True)

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
            return model_version.to_model(hydrate=hydrate)

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
            )
            session.add(existing_model_version)
            session.commit()
            session.refresh(existing_model_version)

            return existing_model_version.to_model(hydrate=True)

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
            return model_version_artifact_link_schema.to_model(hydrate=True)

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

            # Handle artifact name
            if model_version_artifact_link_filter_model.artifact_name:
                query = query.where(
                    ModelVersionArtifactSchema.artifact_version_id
                    == ArtifactSchema.id
                ).where(
                    ArtifactSchema.name
                    == model_version_artifact_link_filter_model.artifact_name
                )

            # Handle model artifact types
            if model_version_artifact_link_filter_model.only_data_artifacts:
                query = query.where(
                    ModelVersionArtifactSchema.is_model_artifact == False  # noqa: E712
                ).where(
                    ModelVersionArtifactSchema.is_deployment_artifact == False  # noqa: E712
                )
            elif model_version_artifact_link_filter_model.only_deployment_artifacts:
                query = query.where(
                    ModelVersionArtifactSchema.is_deployment_artifact
                )
            elif model_version_artifact_link_filter_model.only_model_artifacts:
                query = query.where(
                    ModelVersionArtifactSchema.is_model_artifact
                )

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
                hydrate=True
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
        # Handle pipeline run name
        if model_version_pipeline_run_link_filter_model.pipeline_run_name:
            query = query.where(
                ModelVersionPipelineRunSchema.pipeline_run_id
                == PipelineRunSchema.id
            ).where(
                PipelineRunSchema.name
                == model_version_pipeline_run_link_filter_model.pipeline_run_name
            )
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
                tag = self.create_tag(TagRequestModel(name=tag_name))
            try:
                self.create_tag_resource(
                    TagResourceRequestModel(
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
    def create_tag(self, tag: TagRequestModel) -> TagResponseModel:
        """Creates a new tag.

        Args:
            tag: the tag to be created.

        Returns:
            The newly created tag.

        Raises:
            EntityExistsError: If a tag with the given name already exists.
        """
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
            return TagSchema.to_model(tag_schema)

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
        self,
        tag_name_or_id: Union[str, UUID],
    ) -> TagResponseModel:
        """Get an existing tag.

        Args:
            tag_name_or_id: name or id of the tag to be retrieved.

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
            return TagSchema.to_model(tag)

    def list_tags(
        self,
        tag_filter_model: TagFilterModel,
    ) -> Page[TagResponseModel]:
        """Get all tags by filter.

        Args:
            tag_filter_model: All filter parameters including pagination params.

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
            )

    def update_tag(
        self,
        tag_name_or_id: Union[str, UUID],
        tag_update_model: TagUpdateModel,
    ) -> TagResponseModel:
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
            return tag.to_model()

    ####################
    # Tags <> resources
    ####################

    def create_tag_resource(
        self, tag_resource: TagResourceRequestModel
    ) -> TagResourceResponseModel:
        """Creates a new tag resource relationship.

        Args:
            tag_resource: the tag resource relationship to be created.

        Returns:
            The newly created tag resource relationship.

        Raises:
            EntityExistsError: If a tag resource relationship with the given configuration.
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
                    f"Unable to create a tag {tag_resource.resource_type.name.lower()} "
                    f"relationship with IDs `{tag_resource.tag_id}`|`{tag_resource.resource_id}`. "
                    "This relationship already exists."
                )

            tag_resource_schema = TagResourceSchema.from_request(tag_resource)
            session.add(tag_resource_schema)

            session.commit()
            return TagResourceSchema.to_model(tag_resource_schema)

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
                    f"`tag_id`='{tag_id}' and `resource_id`='{resource_id}' and "
                    f"`resource_type`='{resource_type.value}': No "
                    "tag<>resource with these IDs found."
                )
            session.delete(tag_model)
            session.commit()
