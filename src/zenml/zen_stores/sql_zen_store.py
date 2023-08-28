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
from contextvars import ContextVar
from pathlib import Path, PurePath
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
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
from sqlmodel import Session, create_engine, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.analytics.enums import AnalyticsEvent
from zenml.analytics.utils import track_decorator
from zenml.config.global_config import GlobalConfiguration
from zenml.config.secrets_store_config import SecretsStoreConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    ENV_ZENML_DISABLE_DATABASE_MIGRATION,
    ENV_ZENML_SERVER_DEPLOYMENT_TYPE,
)
from zenml.enums import (
    ExecutionStatus,
    LoggingLevels,
    SecretScope,
    SorterOps,
    StackComponentType,
    StoreType,
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
    ArtifactFilterModel,
    ArtifactRequestModel,
    ArtifactResponseModel,
    BaseFilterModel,
    CodeReferenceRequestModel,
    CodeRepositoryFilterModel,
    CodeRepositoryRequestModel,
    CodeRepositoryResponseModel,
    CodeRepositoryUpdateModel,
    ComponentFilterModel,
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentUpdateModel,
    FlavorFilterModel,
    FlavorRequestModel,
    FlavorResponseModel,
    FlavorUpdateModel,
    PipelineBuildFilterModel,
    PipelineBuildRequestModel,
    PipelineBuildResponseModel,
    PipelineDeploymentFilterModel,
    PipelineDeploymentRequestModel,
    PipelineDeploymentResponseModel,
    PipelineFilterModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineRunFilterModel,
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
    PipelineUpdateModel,
    RoleFilterModel,
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
    RunMetadataRequestModel,
    RunMetadataResponseModel,
    ScheduleRequestModel,
    ScheduleResponseModel,
    ScheduleUpdateModel,
    SecretFilterModel,
    SecretRequestModel,
    ServiceConnectorFilterModel,
    ServiceConnectorRequestModel,
    ServiceConnectorResourcesModel,
    ServiceConnectorResponseModel,
    ServiceConnectorTypeModel,
    ServiceConnectorUpdateModel,
    StackFilterModel,
    StackRequestModel,
    StackResponseModel,
    StackUpdateModel,
    StepRunFilterModel,
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
    TeamFilterModel,
    TeamRequestModel,
    TeamResponseModel,
    TeamRoleAssignmentFilterModel,
    TeamRoleAssignmentRequestModel,
    TeamRoleAssignmentResponseModel,
    TeamUpdateModel,
    UserAuthModel,
    UserFilterModel,
    UserRequestModel,
    UserResponseModel,
    UserRoleAssignmentFilterModel,
    UserRoleAssignmentRequestModel,
    UserRoleAssignmentResponseModel,
    UserUpdateModel,
    WorkspaceFilterModel,
    WorkspaceRequestModel,
    WorkspaceResponseModel,
    WorkspaceUpdateModel,
)
from zenml.models.base_models import BaseResponseModel
from zenml.models.constants import TEXT_FIELD_MAX_LENGTH
from zenml.models.page_model import Page
from zenml.models.run_metadata_models import RunMetadataFilterModel
from zenml.models.schedule_model import ScheduleFilterModel
from zenml.models.secret_models import SecretUpdateModel
from zenml.models.server_models import ServerDatabaseType, ServerModel
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
    DEFAULT_ADMIN_ROLE,
    DEFAULT_GUEST_ROLE,
    DEFAULT_STACK_COMPONENT_NAME,
    DEFAULT_STACK_NAME,
    BaseZenStore,
)
from zenml.zen_stores.enums import StoreEvent
from zenml.zen_stores.migrations.alembic import (
    ZENML_ALEMBIC_START_REVISION,
    Alembic,
)
from zenml.zen_stores.schemas import (
    ArtifactSchema,
    BaseSchema,
    CodeReferenceSchema,
    CodeRepositorySchema,
    FlavorSchema,
    IdentitySchema,
    NamedSchema,
    PipelineBuildSchema,
    PipelineDeploymentSchema,
    PipelineRunSchema,
    PipelineSchema,
    RolePermissionSchema,
    RoleSchema,
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
    TeamRoleAssignmentSchema,
    TeamSchema,
    UserRoleAssignmentSchema,
    UserSchema,
    WorkspaceSchema,
)
from zenml.zen_stores.schemas.artifact_schemas import (
    ArtifactVisualizationSchema,
)
from zenml.zen_stores.schemas.logs_schemas import LogsSchema
from zenml.zen_stores.secrets_stores.sql_secrets_store import (
    SqlSecretsStoreConfiguration,
)

AnyNamedSchema = TypeVar("AnyNamedSchema", bound=NamedSchema)
AnySchema = TypeVar("AnySchema", bound=BaseSchema)
B = TypeVar("B", bound=BaseResponseModel)

params_value: ContextVar[BaseFilterModel] = ContextVar("params_value")


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
        If the error if because the MySQL database doesn't exist.
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
    def runs_inside_server(self) -> bool:
        """Whether the store is running inside a server.

        Returns:
            Whether the store is running inside a server.
        """
        if ENV_ZENML_SERVER_DEPLOYMENT_TYPE in os.environ:
            return True
        return False

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
        filter_model: BaseFilterModel,
        custom_schema_to_model_conversion: Optional[
            Callable[[AnySchema], B]
        ] = None,
        custom_fetch: Optional[
            Callable[
                [
                    Session,
                    Union[Select[AnySchema], SelectOfScalar[AnySchema]],
                    BaseFilterModel,
                ],
                List[AnySchema],
            ]
        ] = None,
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
                items.append(to_model())
                continue
            # If neither of the above work, raise an error.
            raise RuntimeError(
                f"Cannot convert schema `{schema.__class__.__name__}` to model "
                "since it does not have a `to_model` method."
            )

        return Page(
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
                # tables from scratch with alembic.
                self.alembic.upgrade()
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

        Raises:
            KeyError: If the deployment ID could not be loaded from the
                database.
        """
        model = super().get_store_info()
        sql_url = make_url(self.config.url)
        model.database_type = ServerDatabaseType(sql_url.drivername)

        # Fetch the deployment ID from the database and use it to replace
        # the one fetched from the global configuration
        with Session(self.engine) as session:
            identity = session.exec(select(IdentitySchema)).first()

            if identity is None:
                raise KeyError(
                    "The deployment ID could not be loaded from the database."
                )
            model.id = identity.id
        return model

    # ------
    # Stacks
    # ------
    @track_decorator(AnalyticsEvent.REGISTERED_STACK)
    def create_stack(self, stack: StackRequestModel) -> StackResponseModel:
        """Register a new stack.

        Args:
            stack: The stack to register.

        Returns:
            The registered stack.
        """
        with Session(self.engine) as session:
            self._fail_if_stack_with_name_exists_for_user(
                stack=stack, session=session
            )

            if stack.is_shared:
                self._fail_if_stack_with_name_already_shared(
                    stack=stack, session=session
                )

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
                is_shared=stack.is_shared,
                stack_spec_path=stack.stack_spec_path,
                name=stack.name,
                description=stack.description,
                components=defined_components,
            )

            session.add(new_stack_schema)
            session.commit()
            session.refresh(new_stack_schema)

            return new_stack_schema.to_model()

    def get_stack(self, stack_id: UUID) -> StackResponseModel:
        """Get a stack by its unique ID.

        Args:
            stack_id: The ID of the stack to get.

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
            return stack.to_model()

    def list_stacks(
        self, stack_filter_model: StackFilterModel
    ) -> Page[StackResponseModel]:
        """List all stacks matching the given filter criteria.

        Args:
            stack_filter_model: All filter parameters including pagination
                params.

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
            )

    def count_stacks(self, workspace_id: Optional[UUID]) -> int:
        """Count all stacks, optionally within a workspace scope.

        Args:
            workspace_id: The workspace to use for counting stacks

        Returns:
            The number of stacks in the workspace.
        """
        return self._count_entity(
            schema=StackSchema, workspace_id=workspace_id
        )

    @track_decorator(AnalyticsEvent.UPDATED_STACK)
    def update_stack(
        self, stack_id: UUID, stack_update: StackUpdateModel
    ) -> StackResponseModel:
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
            # Check if stack with the domain key (name, workspace, owner) already
            #  exists
            existing_stack = session.exec(
                select(StackSchema).where(StackSchema.id == stack_id)
            ).first()
            if existing_stack is None:
                raise KeyError(
                    f"Unable to update stack with id '{stack_id}': Found no"
                    f"existing stack with this id."
                )
            if existing_stack.name == DEFAULT_STACK_NAME:
                raise IllegalOperationError(
                    "The default stack cannot be modified."
                )
            # In case of a renaming update, make sure no stack already exists
            # with that name
            if stack_update.name:
                if existing_stack.name != stack_update.name:
                    self._fail_if_stack_with_name_exists_for_user(
                        stack=stack_update, session=session
                    )

            # Check if stack update makes the stack a shared stack. In that
            # case, check if a stack with the same name is already shared
            # within the workspace
            if stack_update.is_shared:
                if not existing_stack.is_shared and stack_update.is_shared:
                    self._fail_if_stack_with_name_already_shared(
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

            return existing_stack.to_model()

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
                if stack.name == DEFAULT_STACK_NAME:
                    raise IllegalOperationError(
                        "The default stack cannot be deleted."
                    )
                session.delete(stack)
            except NoResultFound as error:
                raise KeyError from error

            session.commit()

    def _fail_if_stack_with_name_exists_for_user(
        self,
        stack: StackRequestModel,
        session: Session,
    ) -> None:
        """Raise an exception if a Component with same name exists for user.

        Args:
            stack: The Stack
            session: The Session

        Returns:
            None

        Raises:
            StackExistsError: If a Stack with the given name is already
                                       owned by the user
        """
        existing_domain_stack = session.exec(
            select(StackSchema)
            .where(StackSchema.name == stack.name)
            .where(StackSchema.workspace_id == stack.workspace)
            .where(StackSchema.user_id == stack.user)
        ).first()
        if existing_domain_stack is not None:
            workspace = self._get_workspace_schema(
                workspace_name_or_id=stack.workspace, session=session
            )
            user = self._get_user_schema(
                user_name_or_id=stack.user, session=session
            )
            raise StackExistsError(
                f"Unable to register stack with name "
                f"'{stack.name}': Found an existing stack with the same "
                f"name in the active workspace, '{workspace.name}', owned by the "
                f"same user, '{user.name}'."
            )
        return None

    def _fail_if_stack_with_name_already_shared(
        self,
        stack: StackRequestModel,
        session: Session,
    ) -> None:
        """Raise an exception if a Stack with same name is already shared.

        Args:
            stack: The Stack
            session: The Session

        Raises:
            StackExistsError: If a stack with the given name is already shared
                              by a user.
        """
        # Check if component with the same name, type is already shared
        # within the workspace
        existing_shared_stack = session.exec(
            select(StackSchema)
            .where(StackSchema.name == stack.name)
            .where(StackSchema.workspace_id == stack.workspace)
            .where(StackSchema.is_shared == stack.is_shared)
        ).first()
        if existing_shared_stack is not None:
            workspace = self._get_workspace_schema(
                workspace_name_or_id=stack.workspace, session=session
            )
            error_msg = (
                f"Unable to share stack with name '{stack.name}': Found an "
                f"existing shared stack with the same name in workspace "
                f"'{workspace.name}'"
            )
            if existing_shared_stack.user_id:
                owner_of_shared = self._get_user_schema(
                    existing_shared_stack.user_id, session=session
                )
                error_msg += f" owned by '{owner_of_shared.name}'."
            else:
                error_msg += ", which is currently not owned by any user."
            raise StackExistsError(error_msg)

    # ----------------
    # Stack components
    # ----------------
    @track_decorator(AnalyticsEvent.REGISTERED_STACK_COMPONENT)
    def create_stack_component(
        self,
        component: ComponentRequestModel,
    ) -> ComponentResponseModel:
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
            self._fail_if_component_with_name_type_exists_for_user(
                name=component.name,
                component_type=component.type,
                user_id=component.user,
                workspace_id=component.workspace,
                session=session,
            )

            if component.is_shared:
                self._fail_if_component_with_name_type_already_shared(
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
                is_shared=component.is_shared,
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

            return new_component.to_model()

    def get_stack_component(
        self, component_id: UUID
    ) -> ComponentResponseModel:
        """Get a stack component by ID.

        Args:
            component_id: The ID of the stack component to get.

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

            return stack_component.to_model()

    def list_stack_components(
        self, component_filter_model: ComponentFilterModel
    ) -> Page[ComponentResponseModel]:
        """List all stack components matching the given filter criteria.

        Args:
            component_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all stack components matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(StackComponentSchema)
            paged_components: Page[
                ComponentResponseModel
            ] = self.filter_and_paginate(
                session=session,
                query=query,
                table=StackComponentSchema,
                filter_model=component_filter_model,
            )
            return paged_components

    def count_stack_components(self, workspace_id: Optional[UUID]) -> int:
        """Count all components, optionally within a workspace scope.

        Args:
            workspace_id: The workspace to use for counting components

        Returns:
            The number of components in the workspace.
        """
        return self._count_entity(
            schema=StackComponentSchema, workspace_id=workspace_id
        )

    def update_stack_component(
        self, component_id: UUID, component_update: ComponentUpdateModel
    ) -> ComponentResponseModel:
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
                existing_component.name == DEFAULT_STACK_COMPONENT_NAME
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
                if (
                    existing_component.name != component_update.name
                    and existing_component.user_id is not None
                ):
                    self._fail_if_component_with_name_type_exists_for_user(
                        name=component_update.name,
                        component_type=existing_component.type,
                        workspace_id=existing_component.workspace_id,
                        user_id=existing_component.user_id,
                        session=session,
                    )

            # Check if component update makes the component a shared component,
            # In that case check if a component with the same name, type are
            # already shared within the workspace
            if component_update.is_shared:
                if (
                    not existing_component.is_shared
                    and component_update.is_shared
                ):
                    self._fail_if_component_with_name_type_already_shared(
                        name=component_update.name or existing_component.name,
                        component_type=existing_component.type,
                        workspace_id=existing_component.workspace_id,
                        session=session,
                    )

            existing_component.update(component_update=component_update)

            service_connector: Optional[ServiceConnectorSchema] = None
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

            if service_connector:
                existing_component.connector = service_connector

            session.add(existing_component)
            session.commit()

            return existing_component.to_model()

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
                    stack_component.name == DEFAULT_STACK_COMPONENT_NAME
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

    @staticmethod
    def _fail_if_component_with_name_type_exists_for_user(
        name: str,
        component_type: StackComponentType,
        workspace_id: UUID,
        user_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a Component with same name/type exists.

        Args:
            name: The name of the component
            component_type: The type of the component
            workspace_id: The ID of the workspace
            user_id: The ID of the user
            session: The Session

        Returns:
            None

        Raises:
            StackComponentExistsError: If a component with the given name and
                                       type is already owned by the user
        """
        assert user_id
        # Check if component with the same domain key (name, type, workspace,
        # owner) already exists
        existing_domain_component = session.exec(
            select(StackComponentSchema)
            .where(StackComponentSchema.name == name)
            .where(StackComponentSchema.workspace_id == workspace_id)
            .where(StackComponentSchema.user_id == user_id)
            .where(StackComponentSchema.type == component_type)
        ).first()
        if existing_domain_component is not None:
            # Theoretically the user schema is optional, in this case there is
            #  no way that it will be None
            assert existing_domain_component.user
            raise StackComponentExistsError(
                f"Unable to register '{component_type.value}' component "
                f"with name '{name}': Found an existing "
                f"component with the same name and type in the same "
                f" workspace, '{existing_domain_component.workspace.name}', "
                f"owned by the same user, "
                f"'{existing_domain_component.user.name}'."
            )
        return None

    @staticmethod
    def _fail_if_component_with_name_type_already_shared(
        name: str,
        component_type: StackComponentType,
        workspace_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a Component with same name/type already shared.

        Args:
            name: The name of the component
            component_type: The type of the component
            workspace_id: The ID of the workspace
            session: The Session

        Raises:
            StackComponentExistsError: If a component with the given name and
                type is already shared by a user
        """
        # Check if component with the same name, type is already shared
        # within the workspace
        is_shared = True
        existing_shared_component = session.exec(
            select(StackComponentSchema)
            .where(StackComponentSchema.name == name)
            .where(StackComponentSchema.workspace_id == workspace_id)
            .where(StackComponentSchema.type == component_type)
            .where(StackComponentSchema.is_shared == is_shared)
        ).first()
        if existing_shared_component is not None:
            raise StackComponentExistsError(
                f"Unable to shared component of type '{component_type.value}' "
                f"with name '{name}': Found an existing shared "
                f"component with the same name and type in workspace "
                f"'{workspace_id}'."
            )

    # -----------------------
    # Stack component flavors
    # -----------------------

    @track_decorator(AnalyticsEvent.CREATED_FLAVOR)
    def create_flavor(self, flavor: FlavorRequestModel) -> FlavorResponseModel:
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

                return new_flavor.to_model()

    def update_flavor(
        self, flavor_id: UUID, flavor_update: FlavorUpdateModel
    ) -> FlavorResponseModel:
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
            return existing_flavor.to_model()

    def get_flavor(self, flavor_id: UUID) -> FlavorResponseModel:
        """Get a flavor by ID.

        Args:
            flavor_id: The ID of the flavor to fetch.

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
            return flavor_in_db.to_model()

    def list_flavors(
        self, flavor_filter_model: FlavorFilterModel
    ) -> Page[FlavorResponseModel]:
        """List all stack component flavors matching the given filter criteria.

        Args:
            flavor_filter_model: All filter parameters including pagination
                params

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

    # -----
    # Users
    # -----

    def create_user(self, user: UserRequestModel) -> UserResponseModel:
        """Creates a new user.

        Args:
            user: User to be created.

        Returns:
            The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """
        with Session(self.engine) as session:
            # Check if user with the given name already exists
            existing_user = session.exec(
                select(UserSchema).where(UserSchema.name == user.name)
            ).first()
            if existing_user is not None:
                raise EntityExistsError(
                    f"Unable to create user with name '{user.name}': "
                    f"Found existing user with this name."
                )

            # Create the user
            new_user = UserSchema.from_request(user)
            session.add(new_user)
            session.commit()

            return new_user.to_model()

    def get_user(
        self,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        include_private: bool = False,
    ) -> UserResponseModel:
        """Gets a specific user, when no id is specified the active user is returned.

        Raises a KeyError in case a user with that id does not exist.

        Args:
            user_name_or_id: The name or ID of the user to get.
            include_private: Whether to include private user information

        Returns:
            The requested user, if it was found.
        """
        if not user_name_or_id:
            user_name_or_id = self._default_user_name

        with Session(self.engine) as session:
            user = self._get_user_schema(user_name_or_id, session=session)

            return user.to_model(include_private=include_private)

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
            user = self._get_user_schema(user_name_or_id, session=session)
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
            )

    def list_users(
        self, user_filter_model: UserFilterModel
    ) -> Page[UserResponseModel]:
        """List all users.

        Args:
            user_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all users.
        """
        with Session(self.engine) as session:
            query = select(UserSchema)
            paged_user: Page[UserResponseModel] = self.filter_and_paginate(
                session=session,
                query=query,
                table=UserSchema,
                filter_model=user_filter_model,
            )
            return paged_user

    def update_user(
        self, user_id: UUID, user_update: UserUpdateModel
    ) -> UserResponseModel:
        """Updates an existing user.

        Args:
            user_id: The id of the user to update.
            user_update: The update to be applied to the user.

        Returns:
            The updated user.

        Raises:
            IllegalOperationError: If the request tries to update the username
                for the default user account.
        """
        with Session(self.engine) as session:
            existing_user = self._get_user_schema(user_id, session=session)
            if (
                existing_user.name == self._default_user_name
                and "name" in user_update.__fields_set__
                and user_update.name != existing_user.name
            ):
                raise IllegalOperationError(
                    "The username of the default user account cannot be "
                    "changed."
                )
            existing_user.update(user_update=user_update)
            session.add(existing_user)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_user)
            return existing_user.to_model()

    def delete_user(self, user_name_or_id: Union[str, UUID]) -> None:
        """Deletes a user.

        Args:
            user_name_or_id: The name or the ID of the user to delete.

        Raises:
            IllegalOperationError: If the user is the default user account.
        """
        with Session(self.engine) as session:
            user = self._get_user_schema(user_name_or_id, session=session)
            if user.name == self._default_user_name:
                raise IllegalOperationError(
                    "The default user account cannot be deleted."
                )

            self._trigger_event(StoreEvent.USER_DELETED, user_id=user.id)

            session.delete(user)
            session.commit()

    # -----
    # Teams
    # -----

    def create_team(self, team: TeamRequestModel) -> TeamResponseModel:
        """Creates a new team.

        Args:
            team: The team model to create.

        Returns:
            The newly created team.

        Raises:
            EntityExistsError: If a team with the given name already exists.
        """
        with Session(self.engine) as session:
            # Check if team with the given name already exists
            existing_team = session.exec(
                select(TeamSchema).where(TeamSchema.name == team.name)
            ).first()
            if existing_team is not None:
                raise EntityExistsError(
                    f"Unable to create team with name '{team.name}': "
                    f"Found existing team with this name."
                )

            defined_users = []
            if team.users:
                # Get the Schemas of all users mentioned
                filters = [
                    (UserSchema.id == user_id) for user_id in team.users
                ]

                defined_users = session.exec(
                    select(UserSchema).where(or_(*filters))
                ).all()

            # Create the team
            new_team = TeamSchema(name=team.name, users=defined_users)
            session.add(new_team)
            session.commit()

            return new_team.to_model()

    def get_team(self, team_name_or_id: Union[str, UUID]) -> TeamResponseModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.
        """
        with Session(self.engine) as session:
            team = self._get_team_schema(team_name_or_id, session=session)
            return team.to_model()

    def list_teams(
        self, team_filter_model: TeamFilterModel
    ) -> Page[TeamResponseModel]:
        """List all teams matching the given filter criteria.

        Args:
            team_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all teams matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(TeamSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=TeamSchema,
                filter_model=team_filter_model,
            )

    def update_team(
        self, team_id: UUID, team_update: TeamUpdateModel
    ) -> TeamResponseModel:
        """Update an existing team.

        Args:
            team_id: The ID of the team to be updated.
            team_update: The update to be applied to the team.

        Returns:
            The updated team.

        Raises:
            KeyError: if the team does not exist.
        """
        with Session(self.engine) as session:
            existing_team = session.exec(
                select(TeamSchema).where(TeamSchema.id == team_id)
            ).first()

            if existing_team is None:
                raise KeyError(
                    f"Unable to update team with id "
                    f"'{team_id}': Found no"
                    f"existing teams with this id."
                )

            # Update the team
            existing_team.update(team_update=team_update)
            existing_team.users = []
            if "users" in team_update.__fields_set__ and team_update.users:
                for user in team_update.users:
                    existing_team.users.append(
                        self._get_user_schema(
                            user_name_or_id=user, session=session
                        )
                    )

            session.add(existing_team)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_team)
            return existing_team.to_model()

    def delete_team(self, team_name_or_id: Union[str, UUID]) -> None:
        """Deletes a team.

        Args:
            team_name_or_id: Name or ID of the team to delete.
        """
        with Session(self.engine) as session:
            team = self._get_team_schema(team_name_or_id, session=session)
            session.delete(team)
            session.commit()

    # -----
    # Roles
    # -----

    def create_role(self, role: RoleRequestModel) -> RoleResponseModel:
        """Creates a new role.

        Args:
            role: The role model to create.

        Returns:
            The newly created role.

        Raises:
            EntityExistsError: If a role with the given name already exists.
        """
        with Session(self.engine) as session:
            # Check if role with the given name already exists
            existing_role = session.exec(
                select(RoleSchema).where(RoleSchema.name == role.name)
            ).first()
            if existing_role is not None:
                raise EntityExistsError(
                    f"Unable to create role '{role.name}': Role already exists."
                )

            # Create role
            role_schema = RoleSchema.from_request(role)
            session.add(role_schema)
            session.commit()
            # Add all permissions
            for p in role.permissions:
                session.add(
                    RolePermissionSchema(name=p, role_id=role_schema.id)
                )

            session.commit()
            return role_schema.to_model()

    def get_role(self, role_name_or_id: Union[str, UUID]) -> RoleResponseModel:
        """Gets a specific role.

        Args:
            role_name_or_id: Name or ID of the role to get.

        Returns:
            The requested role.
        """
        with Session(self.engine) as session:
            role = self._get_role_schema(role_name_or_id, session=session)
            return role.to_model()

    def list_roles(
        self, role_filter_model: RoleFilterModel
    ) -> Page[RoleResponseModel]:
        """List all roles matching the given filter criteria.

        Args:
            role_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all roles matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(RoleSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=RoleSchema,
                filter_model=role_filter_model,
            )

    def update_role(
        self, role_id: UUID, role_update: RoleUpdateModel
    ) -> RoleResponseModel:
        """Update an existing role.

        Args:
            role_id: The ID of the role to be updated.
            role_update: The update to be applied to the role.

        Returns:
            The updated role.

        Raises:
            KeyError: if the role does not exist.
            IllegalOperationError: if the role is a system role.
        """
        with Session(self.engine) as session:
            existing_role = session.exec(
                select(RoleSchema).where(RoleSchema.id == role_id)
            ).first()

            if existing_role is None:
                raise KeyError(
                    f"Unable to update role with id "
                    f"'{role_id}': Found no"
                    f"existing roles with this id."
                )

            if existing_role.name in [DEFAULT_ADMIN_ROLE, DEFAULT_GUEST_ROLE]:
                raise IllegalOperationError(
                    f"The built-in role '{existing_role.name}' cannot be "
                    f"updated."
                )

            # The relationship table for roles behaves different from the other
            #  ones. As such the required updates on the permissions have to be
            #  done manually.
            if "permissions" in role_update.__fields_set__:
                existing_permissions = {
                    p.name for p in existing_role.permissions
                }

                diff = existing_permissions.symmetric_difference(
                    role_update.permissions
                )

                for permission in diff:
                    if permission not in role_update.permissions:
                        permission_to_delete = session.exec(
                            select(RolePermissionSchema)
                            .where(RolePermissionSchema.name == permission)
                            .where(
                                RolePermissionSchema.role_id
                                == existing_role.id
                            )
                        ).one_or_none()
                        session.delete(permission_to_delete)

                    elif permission not in existing_permissions:
                        session.add(
                            RolePermissionSchema(
                                name=permission, role_id=existing_role.id
                            )
                        )

            # Update the role
            existing_role.update(role_update=role_update)
            session.add(existing_role)
            session.commit()

            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_role)
            return existing_role.to_model()

    def delete_role(self, role_name_or_id: Union[str, UUID]) -> None:
        """Deletes a role.

        Args:
            role_name_or_id: Name or ID of the role to delete.

        Raises:
            IllegalOperationError: If the role is still assigned to users or
                the role is one of the built-in roles.
        """
        with Session(self.engine) as session:
            role = self._get_role_schema(role_name_or_id, session=session)
            if role.name in [DEFAULT_ADMIN_ROLE, DEFAULT_GUEST_ROLE]:
                raise IllegalOperationError(
                    f"The built-in role '{role.name}' cannot be deleted."
                )
            user_role = session.exec(
                select(UserRoleAssignmentSchema).where(
                    UserRoleAssignmentSchema.role_id == role.id
                )
            ).all()
            team_role = session.exec(
                select(TeamRoleAssignmentSchema).where(
                    TeamRoleAssignmentSchema.role_id == role.id
                )
            ).all()

            if len(user_role) > 0 or len(team_role) > 0:
                raise IllegalOperationError(
                    f"Role `{role.name}` of type cannot be "
                    f"deleted as it is in use by multiple users and teams. "
                    f"Before deleting this role make sure to remove all "
                    f"instances where this role is used."
                )
            else:
                # Delete role
                session.delete(role)
                session.commit()

    # ----------------
    # Role assignments
    # ----------------

    def list_user_role_assignments(
        self, user_role_assignment_filter_model: UserRoleAssignmentFilterModel
    ) -> Page[UserRoleAssignmentResponseModel]:
        """List all roles assignments matching the given filter criteria.

        Args:
            user_role_assignment_filter_model: All filter parameters including
                pagination params.

        Returns:
            A list of all roles assignments matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(UserRoleAssignmentSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=UserRoleAssignmentSchema,
                filter_model=user_role_assignment_filter_model,
            )

    def create_user_role_assignment(
        self, user_role_assignment: UserRoleAssignmentRequestModel
    ) -> UserRoleAssignmentResponseModel:
        """Assigns a role to a user or team, scoped to a specific workspace.

        Args:
            user_role_assignment: The role assignment to create.

        Returns:
            The created role assignment.

        Raises:
            EntityExistsError: if the role assignment already exists.
        """
        with Session(self.engine) as session:
            role = self._get_role_schema(
                user_role_assignment.role, session=session
            )
            workspace: Optional[WorkspaceSchema] = None
            if user_role_assignment.workspace:
                workspace = self._get_workspace_schema(
                    user_role_assignment.workspace, session=session
                )
            user = self._get_user_schema(
                user_role_assignment.user, session=session
            )
            query = select(UserRoleAssignmentSchema).where(
                UserRoleAssignmentSchema.user_id == user.id,
                UserRoleAssignmentSchema.role_id == role.id,
            )
            if workspace is not None:
                query = query.where(
                    UserRoleAssignmentSchema.workspace_id == workspace.id
                )
            existing_role_assignment = session.exec(query).first()
            if existing_role_assignment is not None:
                raise EntityExistsError(
                    f"Unable to assign role '{role.name}' to user "
                    f"'{user.name}': Role already assigned in this workspace."
                )
            role_assignment = UserRoleAssignmentSchema(
                role_id=role.id,
                user_id=user.id,
                workspace_id=workspace.id if workspace else None,
                role=role,
                user=user,
                workspace=workspace,
            )
            session.add(role_assignment)
            session.commit()
            return role_assignment.to_model()

    def get_user_role_assignment(
        self, user_role_assignment_id: UUID
    ) -> UserRoleAssignmentResponseModel:
        """Gets a role assignment by ID.

        Args:
            user_role_assignment_id: ID of the role assignment to get.

        Returns:
            The role assignment.

        Raises:
            KeyError: If the role assignment does not exist.
        """
        with Session(self.engine) as session:
            user_role = session.exec(
                select(UserRoleAssignmentSchema).where(
                    UserRoleAssignmentSchema.id == user_role_assignment_id
                )
            ).one_or_none()

            if user_role:
                return user_role.to_model()
            else:
                raise KeyError(
                    f"Unable to get user role assignment with ID "
                    f"'{user_role_assignment_id}': No user role assignment "
                    f"with this ID found."
                )

    def delete_user_role_assignment(
        self, user_role_assignment_id: UUID
    ) -> None:
        """Delete a specific role assignment.

        Args:
            user_role_assignment_id: The ID of the specific role assignment.

        Raises:
            KeyError: If the role assignment does not exist.
        """
        with Session(self.engine) as session:
            user_role = session.exec(
                select(UserRoleAssignmentSchema).where(
                    UserRoleAssignmentSchema.id == user_role_assignment_id
                )
            ).one_or_none()
            if not user_role:
                raise KeyError(
                    f"No user role assignment with id "
                    f"{user_role_assignment_id} exists."
                )

            session.delete(user_role)

            session.commit()

    # ---------------------
    # Team Role assignments
    # ---------------------

    def create_team_role_assignment(
        self, team_role_assignment: TeamRoleAssignmentRequestModel
    ) -> TeamRoleAssignmentResponseModel:
        """Creates a new team role assignment.

        Args:
            team_role_assignment: The role assignment model to create.

        Returns:
            The newly created role assignment.

        Raises:
            EntityExistsError: If the role assignment already exists.
        """
        with Session(self.engine) as session:
            role = self._get_role_schema(
                team_role_assignment.role, session=session
            )
            workspace: Optional[WorkspaceSchema] = None
            if team_role_assignment.workspace:
                workspace = self._get_workspace_schema(
                    team_role_assignment.workspace, session=session
                )
            team = self._get_team_schema(
                team_role_assignment.team, session=session
            )
            query = select(UserRoleAssignmentSchema).where(
                UserRoleAssignmentSchema.user_id == team.id,
                UserRoleAssignmentSchema.role_id == role.id,
            )
            if workspace is not None:
                query = query.where(
                    UserRoleAssignmentSchema.workspace_id == workspace.id
                )
            existing_role_assignment = session.exec(query).first()
            if existing_role_assignment is not None:
                raise EntityExistsError(
                    f"Unable to assign role '{role.name}' to team "
                    f"'{team.name}': Role already assigned in this workspace."
                )
            role_assignment = TeamRoleAssignmentSchema(
                role_id=role.id,
                team_id=team.id,
                workspace_id=workspace.id if workspace else None,
                role=role,
                team=team,
                workspace=workspace,
            )
            session.add(role_assignment)
            session.commit()
            return role_assignment.to_model()

    def get_team_role_assignment(
        self, team_role_assignment_id: UUID
    ) -> TeamRoleAssignmentResponseModel:
        """Gets a specific role assignment.

        Args:
            team_role_assignment_id: ID of the role assignment to get.

        Returns:
            The requested role assignment.

        Raises:
            KeyError: If no role assignment with the given ID exists.
        """
        with Session(self.engine) as session:
            team_role = session.exec(
                select(TeamRoleAssignmentSchema).where(
                    TeamRoleAssignmentSchema.id == team_role_assignment_id
                )
            ).one_or_none()

            if team_role:
                return team_role.to_model()
            else:
                raise KeyError(
                    f"Unable to get team role assignment with ID "
                    f"'{team_role_assignment_id}': No team role assignment "
                    f"with this ID found."
                )

    def delete_team_role_assignment(
        self, team_role_assignment_id: UUID
    ) -> None:
        """Delete a specific role assignment.

        Args:
            team_role_assignment_id: The ID of the specific role assignment

        Raises:
            KeyError: If the role assignment does not exist.
        """
        with Session(self.engine) as session:
            team_role = session.exec(
                select(TeamRoleAssignmentSchema).where(
                    TeamRoleAssignmentSchema.id == team_role_assignment_id
                )
            ).one_or_none()
            if not team_role:
                raise KeyError(
                    f"No team role assignment with id "
                    f"{team_role_assignment_id} exists."
                )

            session.delete(team_role)

            session.commit()

    def list_team_role_assignments(
        self, team_role_assignment_filter_model: TeamRoleAssignmentFilterModel
    ) -> Page[TeamRoleAssignmentResponseModel]:
        """List all roles assignments matching the given filter criteria.

        Args:
            team_role_assignment_filter_model: All filter parameters including
                pagination params.

        Returns:
            A list of all roles assignments matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(TeamRoleAssignmentSchema)
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=TeamRoleAssignmentSchema,
                filter_model=team_role_assignment_filter_model,
            )

    # --------
    # Workspaces
    # --------

    @track_decorator(AnalyticsEvent.CREATED_WORKSPACE)
    def create_workspace(
        self, workspace: WorkspaceRequestModel
    ) -> WorkspaceResponseModel:
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

            return new_workspace.to_model()

    def get_workspace(
        self, workspace_name_or_id: Union[str, UUID]
    ) -> WorkspaceResponseModel:
        """Get an existing workspace by name or ID.

        Args:
            workspace_name_or_id: Name or ID of the workspace to get.

        Returns:
            The requested workspace if one was found.
        """
        with Session(self.engine) as session:
            workspace = self._get_workspace_schema(
                workspace_name_or_id, session=session
            )
        return workspace.to_model()

    def list_workspaces(
        self, workspace_filter_model: WorkspaceFilterModel
    ) -> Page[WorkspaceResponseModel]:
        """List all workspace matching the given filter criteria.

        Args:
            workspace_filter_model: All filter parameters including pagination
                params.

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
            )

    def update_workspace(
        self, workspace_id: UUID, workspace_update: WorkspaceUpdateModel
    ) -> WorkspaceResponseModel:
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
            return existing_workspace.to_model()

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

    # ---------
    # Pipelines
    # ---------
    @track_decorator(AnalyticsEvent.CREATE_PIPELINE)
    def create_pipeline(
        self,
        pipeline: PipelineRequestModel,
    ) -> PipelineResponseModel:
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

            return new_pipeline.to_model()

    def get_pipeline(self, pipeline_id: UUID) -> PipelineResponseModel:
        """Get a pipeline with a given ID.

        Args:
            pipeline_id: ID of the pipeline.

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

            return pipeline.to_model()

    def list_pipelines(
        self, pipeline_filter_model: PipelineFilterModel
    ) -> Page[PipelineResponseModel]:
        """List all pipelines matching the given filter criteria.

        Args:
            pipeline_filter_model: All filter parameters including pagination
                params.

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
            )

    def count_pipelines(self, workspace_id: Optional[UUID]) -> int:
        """Count all pipelines, optionally within a workspace scope.

        Args:
            workspace_id: The workspace to use for counting pipelines

        Returns:
            The number of pipelines in the workspace.
        """
        return self._count_entity(
            schema=PipelineSchema, workspace_id=workspace_id
        )

    def update_pipeline(
        self,
        pipeline_id: UUID,
        pipeline_update: PipelineUpdateModel,
    ) -> PipelineResponseModel:
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

            return existing_pipeline.to_model()

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

    # ---------
    # Builds
    # ---------

    def create_build(
        self,
        build: PipelineBuildRequestModel,
    ) -> PipelineBuildResponseModel:
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

            return new_build.to_model()

    def get_build(self, build_id: UUID) -> PipelineBuildResponseModel:
        """Get a build with a given ID.

        Args:
            build_id: ID of the build.

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

            return build.to_model()

    def list_builds(
        self, build_filter_model: PipelineBuildFilterModel
    ) -> Page[PipelineBuildResponseModel]:
        """List all builds matching the given filter criteria.

        Args:
            build_filter_model: All filter parameters including pagination
                params.

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

    # ----------------------
    # Pipeline Deployments
    # ----------------------

    def create_deployment(
        self,
        deployment: PipelineDeploymentRequestModel,
    ) -> PipelineDeploymentResponseModel:
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

            return new_deployment.to_model()

    def get_deployment(
        self, deployment_id: UUID
    ) -> PipelineDeploymentResponseModel:
        """Get a deployment with a given ID.

        Args:
            deployment_id: ID of the deployment.

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

            return deployment.to_model()

    def list_deployments(
        self, deployment_filter_model: PipelineDeploymentFilterModel
    ) -> Page[PipelineDeploymentResponseModel]:
        """List all deployments matching the given filter criteria.

        Args:
            deployment_filter_model: All filter parameters including pagination
                params.

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

    # ---------
    # Schedules
    # ---------

    def create_schedule(
        self, schedule: ScheduleRequestModel
    ) -> ScheduleResponseModel:
        """Creates a new schedule.

        Args:
            schedule: The schedule to create.

        Returns:
            The newly created schedule.
        """
        with Session(self.engine) as session:
            new_schedule = ScheduleSchema.from_create_model(model=schedule)
            session.add(new_schedule)
            session.commit()
            return new_schedule.to_model()

    def get_schedule(self, schedule_id: UUID) -> ScheduleResponseModel:
        """Get a schedule with a given ID.

        Args:
            schedule_id: ID of the schedule.

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
            return schedule.to_model()

    def list_schedules(
        self, schedule_filter_model: ScheduleFilterModel
    ) -> Page[ScheduleResponseModel]:
        """List all schedules in the workspace.

        Args:
            schedule_filter_model: All filter parameters including pagination
                params

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
            )

    def update_schedule(
        self,
        schedule_id: UUID,
        schedule_update: ScheduleUpdateModel,
    ) -> ScheduleResponseModel:
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
            existing_schedule = existing_schedule.from_update_model(
                schedule_update
            )
            session.add(existing_schedule)
            session.commit()
            return existing_schedule.to_model()

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

    # --------------
    # Pipeline runs
    # --------------

    def create_run(
        self, pipeline_run: PipelineRunRequestModel
    ) -> PipelineRunResponseModel:
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

            # Query stack to ensure it exists in the DB
            stack_id = None
            if pipeline_run.stack is not None:
                stack_id = session.exec(
                    select(StackSchema.id).where(
                        StackSchema.id == pipeline_run.stack
                    )
                ).first()
                if stack_id is None:
                    logger.warning(
                        f"No stack found for this run. "
                        f"Creating pipeline run '{pipeline_run.name}' without "
                        "linked stack."
                    )

            # Query pipeline to ensure it exists in the DB
            pipeline_id = None
            if pipeline_run.pipeline is not None:
                pipeline_id = session.exec(
                    select(PipelineSchema.id).where(
                        PipelineSchema.id == pipeline_run.pipeline
                    )
                ).first()
                if pipeline_id is None:
                    logger.warning(
                        f"No pipeline found. Creating pipeline run "
                        f"'{pipeline_run.name}' as unlisted run."
                    )

            # Create the pipeline run
            new_run = PipelineRunSchema.from_request(pipeline_run)
            session.add(new_run)
            session.commit()

            return self._run_schema_to_model(new_run)

    def _run_schema_to_model(
        self, run: PipelineRunSchema
    ) -> PipelineRunResponseModel:
        """Converts a pipeline run schema to a pipeline run model incl. steps.

        Args:
            run: The pipeline run schema to convert.

        Returns:
            The converted pipeline run model with steps hydrated into it.
        """
        steps = {
            step.name: self._run_step_schema_to_model(step)
            for step in run.step_runs
        }
        return run.to_model(steps=steps)

    def get_run(
        self, run_name_or_id: Union[str, UUID]
    ) -> PipelineRunResponseModel:
        """Gets a pipeline run.

        Args:
            run_name_or_id: The name or ID of the pipeline run to get.

        Returns:
            The pipeline run.
        """
        with Session(self.engine) as session:
            run = self._get_run_schema(run_name_or_id, session=session)
            return self._run_schema_to_model(run)

    def get_or_create_run(
        self, pipeline_run: PipelineRunRequestModel
    ) -> Tuple[PipelineRunResponseModel, bool]:
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

    def list_runs(
        self, runs_filter_model: PipelineRunFilterModel
    ) -> Page[PipelineRunResponseModel]:
        """List all pipeline runs matching the given filter criteria.

        Args:
            runs_filter_model: All filter parameters including pagination
                params.

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
                custom_schema_to_model_conversion=self._run_schema_to_model,
            )

    def count_runs(self, workspace_id: Optional[UUID]) -> int:
        """Count all pipeline runs, optionally within a workspace scope.

        Args:
            workspace_id: The workspace to use for counting pipeline runs

        Returns:
            The number of pipeline runs in the workspace.
        """
        return self._count_entity(
            schema=PipelineRunSchema, workspace_id=workspace_id
        )

    def update_run(
        self, run_id: UUID, run_update: PipelineRunUpdateModel
    ) -> PipelineRunResponseModel:
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
            return self._run_schema_to_model(existing_run)

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

    # ------------------
    # Pipeline run steps
    # ------------------

    def create_run_step(
        self, step_run: StepRunRequestModel
    ) -> StepRunResponseModel:
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
                    f"Unable to create step '{step_run.name}': A step with this "
                    f"name already exists in the pipeline run with ID "
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
            for input_name, artifact_id in step_run.inputs.items():
                self._set_run_step_input_artifact(
                    run_step_id=step_schema.id,
                    artifact_id=artifact_id,
                    name=input_name,
                    session=session,
                )

            # Save output artifact IDs into the database.
            for output_name, artifact_id in step_run.outputs.items():
                self._set_run_step_output_artifact(
                    step_run_id=step_schema.id,
                    artifact_id=artifact_id,
                    name=output_name,
                    session=session,
                )

            session.commit()

            return self._run_step_schema_to_model(step_schema)

    def _set_run_step_parent_step(
        self, child_id: UUID, parent_id: UUID, session: Session
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

    def _set_run_step_input_artifact(
        self, run_step_id: UUID, artifact_id: UUID, name: str, session: Session
    ) -> None:
        """Sets an artifact as an input of a step run.

        Args:
            run_step_id: The ID of the step run.
            artifact_id: The ID of the artifact.
            name: The name of the input in the step run.
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
            select(ArtifactSchema).where(ArtifactSchema.id == artifact_id)
        ).first()
        if artifact is None:
            raise KeyError(
                f"Unable to set input artifact: No artifact with ID "
                f"'{artifact_id}' found."
            )

        # Check if the input is already set.
        assignment = session.exec(
            select(StepRunInputArtifactSchema)
            .where(StepRunInputArtifactSchema.step_id == run_step_id)
            .where(StepRunInputArtifactSchema.artifact_id == artifact_id)
            .where(StepRunInputArtifactSchema.name == name)
        ).first()
        if assignment is not None:
            return

        # Save the input assignment in the database.
        assignment = StepRunInputArtifactSchema(
            step_id=run_step_id, artifact_id=artifact_id, name=name
        )
        session.add(assignment)

    def _set_run_step_output_artifact(
        self,
        step_run_id: UUID,
        artifact_id: UUID,
        name: str,
        session: Session,
    ) -> None:
        """Sets an artifact as an output of a step run.

        Args:
            step_run_id: The ID of the step run.
            artifact_id: The ID of the artifact.
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
            select(ArtifactSchema).where(ArtifactSchema.id == artifact_id)
        ).first()
        if artifact is None:
            raise KeyError(
                f"Unable to set output artifact: No artifact with ID "
                f"'{artifact_id}' found."
            )

        # Check if the output is already set.
        assignment = session.exec(
            select(StepRunOutputArtifactSchema)
            .where(StepRunOutputArtifactSchema.step_id == step_run_id)
            .where(StepRunOutputArtifactSchema.artifact_id == artifact_id)
        ).first()
        if assignment is not None:
            return

        # Save the output assignment in the database.
        assignment = StepRunOutputArtifactSchema(
            step_id=step_run_id,
            artifact_id=artifact_id,
            name=name,
        )
        session.add(assignment)

    def get_run_step(self, step_run_id: UUID) -> StepRunResponseModel:
        """Get a step run by ID.

        Args:
            step_run_id: The ID of the step run to get.

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
            return self._run_step_schema_to_model(step_run)

    def _run_step_schema_to_model(
        self, step_run: StepRunSchema
    ) -> StepRunResponseModel:
        """Converts a run step schema to a step model.

        Args:
            step_run: The run step schema to convert.

        Returns:
            The run step model.
        """
        with Session(self.engine) as session:
            # Get parent steps.
            parent_steps = session.exec(
                select(StepRunSchema)
                .where(StepRunParentsSchema.child_id == step_run.id)
                .where(StepRunParentsSchema.parent_id == StepRunSchema.id)
            ).all()
            parent_step_ids = [parent_step.id for parent_step in parent_steps]

            # Get input artifacts.
            input_artifact_list = session.exec(
                select(
                    ArtifactSchema,
                    StepRunInputArtifactSchema.name,
                )
                .where(
                    ArtifactSchema.id == StepRunInputArtifactSchema.artifact_id
                )
                .where(StepRunInputArtifactSchema.step_id == step_run.id)
            ).all()
            input_artifacts = {
                input_name: self._artifact_schema_to_model(artifact)
                for (artifact, input_name) in input_artifact_list
            }

            # Get output artifacts.
            output_artifact_list = session.exec(
                select(
                    ArtifactSchema,
                    StepRunOutputArtifactSchema.name,
                )
                .where(
                    ArtifactSchema.id
                    == StepRunOutputArtifactSchema.artifact_id
                )
                .where(StepRunOutputArtifactSchema.step_id == step_run.id)
            ).all()
            output_artifacts = {
                output_name: self._artifact_schema_to_model(artifact)
                for (artifact, output_name) in output_artifact_list
            }

            # Convert to model.
            return step_run.to_model(
                parent_step_ids=parent_step_ids,
                input_artifacts=input_artifacts,
                output_artifacts=output_artifacts,
            )

    def list_run_steps(
        self, step_run_filter_model: StepRunFilterModel
    ) -> Page[StepRunResponseModel]:
        """List all step runs matching the given filter criteria.

        Args:
            step_run_filter_model: All filter parameters including pagination
                params.

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
                custom_schema_to_model_conversion=self._run_step_schema_to_model,
            )

    def update_run_step(
        self,
        step_run_id: UUID,
        step_run_update: StepRunUpdateModel,
    ) -> StepRunResponseModel:
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
            for name, artifact_id in step_run_update.outputs.items():
                self._set_run_step_output_artifact(
                    step_run_id=step_run_id,
                    artifact_id=artifact_id,
                    name=name,
                    session=session,
                )

            # Input artifacts and parent steps cannot be updated after the
            # step has been created.

            session.commit()
            session.refresh(existing_step_run)

            return self._run_step_schema_to_model(existing_step_run)

    # ---------
    # Artifacts
    # ---------

    def create_artifact(
        self, artifact: ArtifactRequestModel
    ) -> ArtifactResponseModel:
        """Creates an artifact.

        Args:
            artifact: The artifact to create.

        Returns:
            The created artifact.
        """
        with Session(self.engine) as session:
            # Save artifact.
            artifact_schema = ArtifactSchema.from_request(artifact)
            session.add(artifact_schema)

            # Save visualizations of the artifact.
            if artifact.visualizations:
                for vis in artifact.visualizations:
                    vis_schema = ArtifactVisualizationSchema.from_model(
                        visualization=vis, artifact_id=artifact_schema.id
                    )
                    session.add(vis_schema)

            session.commit()
            return self._artifact_schema_to_model(artifact_schema)

    def _artifact_schema_to_model(
        self, artifact_schema: ArtifactSchema
    ) -> ArtifactResponseModel:
        """Converts an artifact schema to a model.

        Args:
            artifact_schema: The artifact schema to convert.

        Returns:
            The converted artifact model.
        """
        # Find the producer step run ID.
        with Session(self.engine) as session:
            producer_step_run_id = session.exec(
                select(StepRunOutputArtifactSchema.step_id)
                .where(
                    StepRunOutputArtifactSchema.artifact_id
                    == artifact_schema.id
                )
                .where(StepRunOutputArtifactSchema.step_id == StepRunSchema.id)
                .where(StepRunSchema.status != ExecutionStatus.CACHED)
            ).first()

            # Convert the artifact schema to a model.
            return artifact_schema.to_model(
                producer_step_run_id=producer_step_run_id
            )

    def get_artifact(self, artifact_id: UUID) -> ArtifactResponseModel:
        """Gets an artifact.

        Args:
            artifact_id: The ID of the artifact to get.

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
                    f"Unable to get artifact with ID {artifact_id}: "
                    f"No artifact with this ID found."
                )
            return self._artifact_schema_to_model(artifact)

    def list_artifacts(
        self, artifact_filter_model: ArtifactFilterModel
    ) -> Page[ArtifactResponseModel]:
        """List all artifacts matching the given filter criteria.

        Args:
            artifact_filter_model: All filter parameters including pagination
                params.

        Returns:
            A list of all artifacts matching the filter criteria.
        """
        with Session(self.engine) as session:
            query = select(ArtifactSchema)
            if artifact_filter_model.only_unused:
                query = query.where(
                    ArtifactSchema.id.notin_(  # type: ignore[attr-defined]
                        select(StepRunOutputArtifactSchema.artifact_id)
                    )
                )
                query = query.where(
                    ArtifactSchema.id.notin_(  # type: ignore[attr-defined]
                        select(StepRunInputArtifactSchema.artifact_id)
                    )
                )
            return self.filter_and_paginate(
                session=session,
                query=query,
                table=ArtifactSchema,
                filter_model=artifact_filter_model,
                custom_schema_to_model_conversion=self._artifact_schema_to_model,
            )

    def delete_artifact(self, artifact_id: UUID) -> None:
        """Deletes an artifact.

        Args:
            artifact_id: The ID of the artifact to delete.

        Raises:
            KeyError: if the artifact doesn't exist.
        """
        with Session(self.engine) as session:
            artifact = session.exec(
                select(ArtifactSchema).where(ArtifactSchema.id == artifact_id)
            ).first()
            if artifact is None:
                raise KeyError(
                    f"Unable to delete artifact with ID {artifact_id}: "
                    f"No artifact with this ID found."
                )
            session.delete(artifact)
            session.commit()

    # ------------
    # Run Metadata
    # ------------

    def create_run_metadata(
        self, run_metadata: RunMetadataRequestModel
    ) -> RunMetadataResponseModel:
        """Creates run metadata.

        Args:
            run_metadata: The run metadata to create.

        Returns:
            The created run metadata.
        """
        with Session(self.engine) as session:
            run_metadata_schema = RunMetadataSchema.from_request(run_metadata)
            session.add(run_metadata_schema)
            session.commit()
            return run_metadata_schema.to_model()

    def list_run_metadata(
        self,
        run_metadata_filter_model: RunMetadataFilterModel,
    ) -> Page[RunMetadataResponseModel]:
        """List run metadata.

        Args:
            run_metadata_filter_model: All filter parameters including
                pagination params.

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
            )

    # -----------------
    # Code Repositories
    # -----------------

    def create_code_repository(
        self, code_repository: CodeRepositoryRequestModel
    ) -> CodeRepositoryResponseModel:
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

            return new_repo.to_model()

    def get_code_repository(
        self, code_repository_id: UUID
    ) -> CodeRepositoryResponseModel:
        """Gets a specific code repository.

        Args:
            code_repository_id: The ID of the code repository to get.

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

            return repo.to_model()

    def list_code_repositories(
        self, filter_model: CodeRepositoryFilterModel
    ) -> Page[CodeRepositoryResponseModel]:
        """List all code repositories.

        Args:
            filter_model: All filter parameters including pagination
                params.

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
            )

    def update_code_repository(
        self, code_repository_id: UUID, update: CodeRepositoryUpdateModel
    ) -> CodeRepositoryResponseModel:
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

            return existing_repo.to_model()

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

    # ------------------
    # Service Connectors
    # ------------------

    @staticmethod
    def _fail_if_service_connector_with_name_exists_for_user(
        name: str,
        workspace_id: UUID,
        user_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a service connector with same name exists.

        Args:
            name: The name of the service connector
            workspace_id: The ID of the workspace
            user_id: The ID of the user
            session: The Session

        Returns:
            None

        Raises:
            EntityExistsError: If a service connector with the given name is
                already owned by the user
        """
        assert user_id
        # Check if service connector with the same domain key (name, workspace,
        # owner) already exists
        existing_domain_connector = session.exec(
            select(ServiceConnectorSchema)
            .where(ServiceConnectorSchema.name == name)
            .where(ServiceConnectorSchema.workspace_id == workspace_id)
            .where(ServiceConnectorSchema.user_id == user_id)
        ).first()
        if existing_domain_connector is not None:
            # Theoretically the user schema is optional, in this case there is
            #  no way that it will be None
            assert existing_domain_connector.user
            raise EntityExistsError(
                f"Unable to register service connector with name '{name}': "
                "Found an existing service connector with the same name in the "
                f"same workspace, '{existing_domain_connector.workspace.name}', "
                "owned by the same user, "
                f"{existing_domain_connector.user.name}'."
            )
        return None

    @staticmethod
    def _fail_if_service_connector_with_name_already_shared(
        name: str,
        workspace_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a service connector with same name is already shared.

        Args:
            name: The name of the service connector
            workspace_id: The ID of the workspace
            session: The Session

        Raises:
            EntityExistsError: If a service connector with the given name is
                already shared by another user
        """
        # Check if a service connector with the same name is already shared
        # within the workspace
        is_shared = True
        existing_shared_connector = session.exec(
            select(ServiceConnectorSchema)
            .where(ServiceConnectorSchema.name == name)
            .where(ServiceConnectorSchema.workspace_id == workspace_id)
            .where(ServiceConnectorSchema.is_shared == is_shared)
        ).first()
        if existing_shared_connector is not None:
            raise EntityExistsError(
                f"Unable to share service connector with name '{name}': Found "
                "an existing shared service connector with the same name in "
                f"workspace '{workspace_id}'."
            )

    def _create_connector_secret(
        self,
        connector_name: str,
        user: UUID,
        workspace: UUID,
        is_shared: bool,
        secrets: Optional[Dict[str, Optional[SecretStr]]],
    ) -> Optional[UUID]:
        """Creates a new secret to store the service connector secret credentials.

        Args:
            connector_name: The name of the service connector for which to
                create a secret.
            user: The ID of the user who owns the service connector.
            workspace: The ID of the workspace in which the service connector
                is registered.
            is_shared: Whether the service connector is shared.
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
                            scope=SecretScope.WORKSPACE
                            if is_shared
                            else SecretScope.USER,
                            values=secrets,
                        )
                    ).id
                except KeyError:
                    # The secret already exists, try again
                    continue

    def _populate_connector_type(
        self, *service_connectors: ServiceConnectorResponseModel
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
            service_connector.connector_type = (
                service_connector_registry.get_service_connector_type(
                    service_connector.type
                )
            )

    @track_decorator(AnalyticsEvent.CREATED_SERVICE_CONNECTOR)
    def create_service_connector(
        self, service_connector: ServiceConnectorRequestModel
    ) -> ServiceConnectorResponseModel:
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
            self._fail_if_service_connector_with_name_exists_for_user(
                name=service_connector.name,
                user_id=service_connector.user,
                workspace_id=service_connector.workspace,
                session=session,
            )

            if service_connector.is_shared:
                self._fail_if_service_connector_with_name_already_shared(
                    name=service_connector.name,
                    workspace_id=service_connector.workspace,
                    session=session,
                )

            # Create the secret
            secret_id = self._create_connector_secret(
                connector_name=service_connector.name,
                user=service_connector.user,
                workspace=service_connector.workspace,
                is_shared=service_connector.is_shared,
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

            connector = new_service_connector.to_model()
            self._populate_connector_type(connector)
            return connector

    def get_service_connector(
        self, service_connector_id: UUID
    ) -> ServiceConnectorResponseModel:
        """Gets a specific service connector.

        Args:
            service_connector_id: The ID of the service connector to get.

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

            connector = service_connector.to_model()
            self._populate_connector_type(connector)
            return connector

    def _list_filtered_service_connectors(
        self,
        session: Session,
        query: Union[
            Select[ServiceConnectorSchema],
            SelectOfScalar[ServiceConnectorSchema],
        ],
        filter_model: ServiceConnectorFilterModel,
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

    def list_service_connectors(
        self, filter_model: ServiceConnectorFilterModel
    ) -> Page[ServiceConnectorResponseModel]:
        """List all service connectors.

        Args:
            filter_model: All filter parameters including pagination
                params.

        Returns:
            A page of all service connectors.
        """

        def fetch_connectors(
            session: Session,
            query: Union[
                Select[ServiceConnectorSchema],
                SelectOfScalar[ServiceConnectorSchema],
            ],
            filter_model: BaseFilterModel,
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
            assert isinstance(filter_model, ServiceConnectorFilterModel)
            items = self._list_filtered_service_connectors(
                session=session, query=query, filter_model=filter_model
            )

            return items

        with Session(self.engine) as session:
            query = select(ServiceConnectorSchema)
            paged_connectors: Page[
                ServiceConnectorResponseModel
            ] = self.filter_and_paginate(
                session=session,
                query=query,
                table=ServiceConnectorSchema,
                filter_model=filter_model,
                custom_fetch=fetch_connectors,
            )

            self._populate_connector_type(*paged_connectors.items)
            return paged_connectors

    def _update_connector_secret(
        self,
        existing_connector: ServiceConnectorResponseModel,
        updated_connector: ServiceConnectorUpdateModel,
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

        is_shared = (
            existing_connector.is_shared
            if updated_connector.is_shared is None
            else updated_connector.is_shared
        )
        scope_changed = is_shared != existing_connector.is_shared

        if updated_connector.secrets is None:
            if scope_changed and existing_connector.secret_id:
                # Update the scope of the existing secret
                self.secrets_store.update_secret(
                    secret_id=existing_connector.secret_id,
                    secret_update=SecretUpdateModel(  # type: ignore[call-arg]
                        scope=SecretScope.WORKSPACE
                        if is_shared
                        else SecretScope.USER,
                    ),
                )

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
            is_shared=is_shared,
            secrets=updated_connector.secrets,
        )

    def update_service_connector(
        self, service_connector_id: UUID, update: ServiceConnectorUpdateModel
    ) -> ServiceConnectorResponseModel:
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
            if update.name:
                if (
                    existing_connector.name != update.name
                    and existing_connector.user_id is not None
                ):
                    self._fail_if_service_connector_with_name_exists_for_user(
                        name=update.name,
                        workspace_id=existing_connector.workspace_id,
                        user_id=existing_connector.user_id,
                        session=session,
                    )

            # Check if service connector update makes the service connector a
            # shared service connector
            # In that case, check if a service connector with the same name is
            # already shared within the workspace
            if update.is_shared is not None:
                if not existing_connector.is_shared and update.is_shared:
                    self._fail_if_service_connector_with_name_already_shared(
                        name=update.name or existing_connector.name,
                        workspace_id=existing_connector.workspace_id,
                        session=session,
                    )

            existing_connector_model = existing_connector.to_model()

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

            connector = existing_connector.to_model()
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

    def verify_service_connector_config(
        self,
        service_connector: ServiceConnectorRequestModel,
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
    ) -> ServiceConnectorResponseModel:
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
            is_shared=connector.is_shared,
            description=connector.description,
            labels=connector.labels,
        )

        self._populate_connector_type(connector)

        return connector

    def list_service_connector_resources(
        self,
        user_name_or_id: Union[str, UUID],
        workspace_name_or_id: Union[str, UUID],
        connector_type: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[ServiceConnectorResourcesModel]:
        """List resources that can be accessed by service connectors.

        Args:
            user_name_or_id: The name or ID of the user to scope to.
            workspace_name_or_id: The name or ID of the workspace to scope to.
            connector_type: The type of service connector to scope to.
            resource_type: The type of resource to scope to.
            resource_id: The ID of the resource to scope to.

        Returns:
            The matching list of resources that available service
            connectors have access to.
        """
        user = self.get_user(user_name_or_id)
        workspace = self.get_workspace(workspace_name_or_id)
        connector_filter_model = ServiceConnectorFilterModel(
            connector_type=connector_type,
            resource_type=resource_type,
            is_shared=True,
            workspace_id=workspace.id,
        )

        shared_connectors = self.list_service_connectors(
            filter_model=connector_filter_model
        ).items

        connector_filter_model = ServiceConnectorFilterModel(
            connector_type=connector_type,
            resource_type=resource_type,
            is_shared=False,
            user_id=user.id,
            workspace_id=workspace.id,
        )

        private_connectors = self.list_service_connectors(
            filter_model=connector_filter_model
        ).items

        resource_list: List[ServiceConnectorResourcesModel] = []

        for connector in list(shared_connectors) + list(private_connectors):
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

    # =======================
    # Internal helper methods
    # =======================

    def _count_entity(
        self, schema: Type[BaseSchema], workspace_id: Optional[UUID]
    ) -> int:
        """Return count of a given entity, optionally scoped to workspace.

        Args:
            schema: Schema of the Entity
            workspace_id: (Optional) ID of the workspace scope

        Returns:
            Count of the entity as integer.
        """
        with Session(self.engine) as session:
            query = session.query(func.count(schema.id))
            if workspace_id and hasattr(schema, "workspace_id"):
                query = query.filter(schema.workspace_id == workspace_id)

            entity_count = query.scalar()
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

    def _get_user_schema(
        self,
        user_name_or_id: Union[str, UUID],
        session: Session,
    ) -> UserSchema:
        """Gets a user schema by name or ID.

        This is a helper method that is used in various places to find the
        user associated to some other object.

        Args:
            user_name_or_id: The name or ID of the user to get.
            session: The database session to use.

        Returns:
            The user schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=user_name_or_id,
            schema_class=UserSchema,
            schema_name="user",
            session=session,
        )

    def _get_team_schema(
        self,
        team_name_or_id: Union[str, UUID],
        session: Session,
    ) -> TeamSchema:
        """Gets a team schema by name or ID.

        This is a helper method that is used in various places to find a team
        by its name or ID.

        Args:
            team_name_or_id: The name or ID of the team to get.
            session: The database session to use.

        Returns:
            The team schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=team_name_or_id,
            schema_class=TeamSchema,
            schema_name="team",
            session=session,
        )

    def _get_role_schema(
        self,
        role_name_or_id: Union[str, UUID],
        session: Session,
    ) -> RoleSchema:
        """Gets a role schema by name or ID.

        This is a helper method that is used in various places to find a role
        by its name or ID.

        Args:
            role_name_or_id: The name or ID of the role to get.
            session: The database session to use.

        Returns:
            The role schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=role_name_or_id,
            schema_class=RoleSchema,
            schema_name="role",
            session=session,
        )

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

    def _create_or_reuse_code_reference(
        self,
        session: Session,
        workspace_id: UUID,
        code_reference: Optional["CodeReferenceRequestModel"],
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
