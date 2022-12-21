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
import os
import re
from pathlib import Path, PurePath
from typing import (
    Any,
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
from pydantic import root_validator
from sqlalchemy import text
from sqlalchemy.engine import URL, Engine, make_url
from sqlalchemy.exc import ArgumentError, NoResultFound, OperationalError
from sqlalchemy.sql.operators import is_
from sqlmodel import Session, create_engine, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    ENV_ZENML_DISABLE_DATABASE_MIGRATION,
    ENV_ZENML_SERVER_DEPLOYMENT_TYPE,
)
from zenml.enums import (
    ExecutionStatus,
    LoggingLevels,
    StackComponentType,
    StoreType,
)
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.logger import get_console_handler, get_logger, get_logging_level
from zenml.models import (
    ArtifactRequestModel,
    ArtifactResponseModel,
    ComponentRequestModel,
    ComponentResponseModel,
    ComponentUpdateModel,
    FlavorRequestModel,
    FlavorResponseModel,
    PipelineRequestModel,
    PipelineResponseModel,
    PipelineRunRequestModel,
    PipelineRunResponseModel,
    PipelineRunUpdateModel,
    PipelineUpdateModel,
    ProjectRequestModel,
    ProjectResponseModel,
    ProjectUpdateModel,
    RoleAssignmentRequestModel,
    RoleAssignmentResponseModel,
    RoleRequestModel,
    RoleResponseModel,
    RoleUpdateModel,
    StackRequestModel,
    StackResponseModel,
    StackUpdateModel,
    StepRunRequestModel,
    StepRunResponseModel,
    StepRunUpdateModel,
    TeamRequestModel,
    TeamResponseModel,
    TeamUpdateModel,
    UserAuthModel,
    UserRequestModel,
    UserResponseModel,
    UserUpdateModel,
)
from zenml.models.server_models import ServerDatabaseType, ServerModel
from zenml.utils import uuid_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track
from zenml.utils.enum_utils import StrEnum
from zenml.utils.networking_utils import (
    replace_localhost_with_internal_hostname,
)
from zenml.zen_stores.base_zen_store import (
    DEFAULT_ADMIN_ROLE,
    DEFAULT_GUEST_ROLE,
    DEFAULT_STACK_COMPONENT_NAME,
    DEFAULT_STACK_NAME,
    BaseZenStore,
)
from zenml.zen_stores.migrations.alembic import (
    ZENML_ALEMBIC_START_REVISION,
    Alembic,
)
from zenml.zen_stores.schemas import (
    ArtifactSchema,
    FlavorSchema,
    IdentitySchema,
    NamedSchema,
    PipelineRunSchema,
    PipelineSchema,
    ProjectSchema,
    RolePermissionSchema,
    RoleSchema,
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
)

AnyNamedSchema = TypeVar("AnyNamedSchema", bound=NamedSchema)

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
    """

    type: StoreType = StoreType.SQL

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
        # flake8: noqa: C901
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

    def get_sqlmodel_config(self) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
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

        # Fetch the deployment ID from the database and use it to replace the one
        # fetched from the global configuration
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

    @track(AnalyticsEvent.REGISTERED_STACK)
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
            component_ids = [
                component_id
                for list_of_component_ids in stack.components.values()
                for component_id in list_of_component_ids
            ]
            filters = [
                (StackComponentSchema.id == component_id)
                for component_id in component_ids
            ]

            defined_components = session.exec(
                select(StackComponentSchema).where(or_(*filters))
            ).all()

            new_stack_schema = StackSchema(
                project_id=stack.project,
                user_id=stack.user,
                is_shared=stack.is_shared,
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
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        component_id: Optional[UUID] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[StackResponseModel]:
        """List all stacks matching the given filter criteria.

        Args:
            project_name_or_id: ID or name of the Project containing the stack
            user_name_or_id: Optionally filter stacks by their owner
            component_id: Optionally filter for stacks that contain the
                          component
            name: Optionally filter stacks by their name
            is_shared: Optionally filter out stacks by whether they are shared
                or not

        Returns:
            A list of all stacks matching the filter criteria.
        """
        with Session(self.engine) as session:
            # Get a list of all stacks
            query = select(StackSchema)
            if project_name_or_id:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
                query = query.where(StackSchema.project_id == project.id)
            if user_name_or_id:
                user = self._get_user_schema(user_name_or_id, session=session)
                query = query.where(StackSchema.user_id == user.id)
            if component_id:
                query = query.where(
                    StackCompositionSchema.stack_id == StackSchema.id
                ).where(StackCompositionSchema.component_id == component_id)
            if name:
                query = query.where(StackSchema.name == name)
            if is_shared is not None:
                query = query.where(StackSchema.is_shared == is_shared)

            stacks = session.exec(query.order_by(StackSchema.name)).all()

            return [stack.to_model() for stack in stacks]

    @track(AnalyticsEvent.UPDATED_STACK)
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
            # Check if stack with the domain key (name, project, owner) already
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
            # within the project
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

    @track(AnalyticsEvent.DELETED_STACK)
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
            .where(StackSchema.project_id == stack.project)
            .where(StackSchema.user_id == stack.user)
        ).first()
        if existing_domain_stack is not None:
            project = self._get_project_schema(
                project_name_or_id=stack.project, session=session
            )
            user = self._get_user_schema(
                user_name_or_id=stack.user, session=session
            )
            raise StackExistsError(
                f"Unable to register stack with name "
                f"'{stack.name}': Found an existing stack with the same "
                f"name in the active project, '{project.name}', owned by the "
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
        # within the project
        existing_shared_stack = session.exec(
            select(StackSchema)
            .where(StackSchema.name == stack.name)
            .where(StackSchema.project_id == stack.project)
            .where(StackSchema.is_shared == stack.is_shared)
        ).first()
        if existing_shared_stack is not None:
            project = self._get_project_schema(
                project_name_or_id=stack.project, session=session
            )
            error_msg = (
                f"Unable to share stack with name '{stack.name}': Found an "
                f"existing shared stack with the same name in project "
                f"'{project.name}'"
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

    @track(AnalyticsEvent.REGISTERED_STACK_COMPONENT)
    def create_stack_component(
        self,
        component: ComponentRequestModel,
    ) -> ComponentResponseModel:
        """Create a stack component.

        Args:
            component: The stack component to create.

        Returns:
            The created stack component.
        """
        with Session(self.engine) as session:
            self._fail_if_component_with_name_type_exists_for_user(
                name=component.name,
                component_type=component.type,
                user_id=component.user,
                project_id=component.project,
                session=session,
            )

            if component.is_shared:
                self._fail_if_component_with_name_type_already_shared(
                    name=component.name,
                    component_type=component.type,
                    project_id=component.project,
                    session=session,
                )

            # Create the component
            new_component = StackComponentSchema(
                name=component.name,
                project_id=component.project,
                user_id=component.user,
                is_shared=component.is_shared,
                type=component.type,
                flavor=component.flavor,
                configuration=base64.b64encode(
                    json.dumps(component.configuration).encode("utf-8")
                ),
            )

            session.add(new_component)
            session.commit()

            session.refresh(new_component)

            return new_component.to_model()

    def get_stack_component(self, component_id: UUID) -> ComponentResponseModel:
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
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        type: Optional[str] = None,
        flavor_name: Optional[str] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[ComponentResponseModel]:
        """List all stack components matching the given filter criteria.

        Args:
            project_name_or_id: The ID or name of the Project to which the stack
                components belong
            user_name_or_id: Optionally filter stack components by the owner
            type: Optionally filter by type of stack component
            flavor_name: Optionally filter by flavor
            name: Optionally filter stack component by name
            is_shared: Optionally filter out stack component by whether they are
                shared or not

        Returns:
            A list of all stack components matching the filter criteria.
        """
        with Session(self.engine) as session:
            # Get a list of all stacks
            query = select(StackComponentSchema)
            if project_name_or_id:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
                query = query.where(
                    StackComponentSchema.project_id == project.id
                )
            if user_name_or_id:
                user = self._get_user_schema(user_name_or_id, session=session)
                query = query.where(StackComponentSchema.user_id == user.id)
            if type:
                query = query.where(StackComponentSchema.type == type)
            if flavor_name:
                query = query.where(StackComponentSchema.flavor == flavor_name)
            if name:
                query = query.where(StackComponentSchema.name == name)
            if is_shared is not None:
                query = query.where(StackComponentSchema.is_shared == is_shared)

            list_of_stack_components_in_db = session.exec(query).all()

            return [comp.to_model() for comp in list_of_stack_components_in_db]

    @track(AnalyticsEvent.UPDATED_STACK_COMPONENT)
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
                        project_id=existing_component.project_id,
                        user_id=existing_component.user_id,
                        session=session,
                    )

            # Check if component update makes the component a shared component,
            # In that case check if a component with the same name, type are
            # already shared within the project
            if component_update.is_shared:
                if (
                    not existing_component.is_shared
                    and component_update.is_shared
                ):
                    self._fail_if_component_with_name_type_already_shared(
                        name=component_update.name or existing_component.name,
                        component_type=existing_component.type,
                        project_id=existing_component.project_id,
                        session=session,
                    )

            existing_component.update(component_update=component_update)
            session.add(existing_component)
            session.commit()

            return existing_component.to_model()

    @track(AnalyticsEvent.DELETED_STACK_COMPONENT)
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
        project_id: UUID,
        user_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a Component with same name/type exists.

        Args:
            name: The name of the component
            component_type: The type of the component
            project_id: The ID of the project
            user_id: The ID of the user
            session: The Session

        Returns:
            None

        Raises:
            StackComponentExistsError: If a component with the given name and
                                       type is already owned by the user
        """
        assert user_id
        # Check if component with the same domain key (name, type, project,
        # owner) already exists
        existing_domain_component = session.exec(
            select(StackComponentSchema)
            .where(StackComponentSchema.name == name)
            .where(StackComponentSchema.project_id == project_id)
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
                f" project, '{existing_domain_component.project.name}', "
                f"owned by the same user, "
                f"'{existing_domain_component.user.name}'."
            )
        return None

    @staticmethod
    def _fail_if_component_with_name_type_already_shared(
        name: str,
        component_type: StackComponentType,
        project_id: UUID,
        session: Session,
    ) -> None:
        """Raise an exception if a Component with same name/type already shared.

        Args:
            name: The name of the component
            component_type: The type of the component
            project_id: The ID of the project
            session: The Session

        Raises:
            StackComponentExistsError: If a component with the given name and
                type is already shared by a user
        """
        # Check if component with the same name, type is already shared
        # within the project
        existing_shared_component = session.exec(
            select(StackComponentSchema)
            .where(StackComponentSchema.name == name)
            .where(StackComponentSchema.project_id == project_id)
            .where(StackComponentSchema.type == component_type)
            .where(StackComponentSchema.is_shared == True)
        ).first()
        if existing_shared_component is not None:
            raise StackComponentExistsError(
                f"Unable to shared component of type '{component_type.value}' "
                f"with name '{name}': Found an existing shared "
                f"component with the same name and type in project "
                f"'{project_id}'."
            )

    # -----------------------
    # Stack component flavors
    # -----------------------

    @track(AnalyticsEvent.CREATED_FLAVOR)
    def create_flavor(self, flavor: FlavorRequestModel) -> FlavorResponseModel:
        """Creates a new stack component flavor.

        Args:
            flavor: The stack component flavor to create.

        Returns:
            The newly created flavor.

        Raises:
            EntityExistsError: If a flavor with the same name and type
                is already owned by this user in this project.
        """
        with Session(self.engine) as session:
            # Check if component with the same domain key (name, type, project,
            # owner) already exists
            existing_flavor = session.exec(
                select(FlavorSchema)
                .where(FlavorSchema.name == flavor.name)
                .where(FlavorSchema.type == flavor.type)
                .where(FlavorSchema.project_id == flavor.project)
                .where(FlavorSchema.user_id == flavor.user)
            ).first()

            if existing_flavor is not None:
                raise EntityExistsError(
                    f"Unable to register '{flavor.type.value}' flavor "
                    f"with name '{flavor.name}': Found an existing "
                    f"flavor with the same name and type in the same "
                    f"'{flavor.project}' project owned by the same "
                    f"'{flavor.user}' user."
                )

            new_flavor = FlavorSchema(
                name=flavor.name,
                type=flavor.type,
                source=flavor.source,
                config_schema=flavor.config_schema,
                integration=flavor.integration,
                project_id=flavor.project,
                user_id=flavor.user,
            )
            session.add(new_flavor)
            session.commit()

            return new_flavor.to_model()

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
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        component_type: Optional[StackComponentType] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[FlavorResponseModel]:
        """List all stack component flavors matching the given filter criteria.

        Args:
            project_name_or_id: Optionally filter by the Project to which the
                component flavors belong
            component_type: Optionally filter by type of stack component
            user_name_or_id: Optionally filter by the owner
            component_type: Optionally filter by type of stack component
            name: Optionally filter flavors by name
            is_shared: Optionally filter out flavors by whether they are
                shared or not

        Returns:
            List of all the stack component flavors matching the given criteria
        """
        with Session(self.engine) as session:
            query = select(FlavorSchema)
            if project_name_or_id:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
                query = query.where(FlavorSchema.project_id == project.id)
            if component_type:
                query = query.where(FlavorSchema.type == component_type)
            if name:
                query = query.where(FlavorSchema.name == name)
            if user_name_or_id:
                user = self._get_user_schema(user_name_or_id, session=session)
                query = query.where(FlavorSchema.user_id == user.id)

            list_of_flavors_in_db = session.exec(query).all()

            return [flavor.to_model() for flavor in list_of_flavors_in_db]

    @track(AnalyticsEvent.DELETED_FLAVOR)
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
                components_of_flavor = session.exec(
                    select(StackComponentSchema).where(
                        StackComponentSchema.flavor == flavor_in_db.name
                    )
                ).all()
                if len(components_of_flavor) > 0:
                    raise IllegalOperationError(
                        f"Stack Component `{flavor_in_db.name}` of type "
                        f"`{flavor_in_db.type} cannot be "
                        f"deleted as it is used by"
                        f"{len(components_of_flavor)} "
                        f"components. Before deleting this "
                        f"flavor, make sure to delete all "
                        f"associated components."
                    )
                else:
                    session.delete(flavor_in_db)
            except NoResultFound as error:
                raise KeyError from error

            session.commit()

    # -----
    # Users
    # -----

    @track(AnalyticsEvent.CREATED_USER)
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

    def get_auth_user(self, user_name_or_id: Union[str, UUID]) -> UserAuthModel:
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

    def list_users(self, name: Optional[str] = None) -> List[UserResponseModel]:
        """List all users.

        Args:
            name: Optionally filter by name

        Returns:
            A list of all users.
        """
        with Session(self.engine) as session:
            query = select(UserSchema)
            if name:
                query = query.where(UserSchema.name == name)
            users = session.exec(query.order_by(UserSchema.name)).all()

            return [user.to_model() for user in users]

    @track(AnalyticsEvent.UPDATED_USER)
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

    @track(AnalyticsEvent.DELETED_USER)
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
            session.delete(user)
            session.commit()

    # -----
    # Teams
    # -----

    @track(AnalyticsEvent.CREATED_TEAM)
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
                filters = [(UserSchema.id == user_id) for user_id in team.users]

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

    def list_teams(self, name: Optional[str] = None) -> List[TeamResponseModel]:
        """List all teams.

        Args:
            name: Optionally filter by name

        Returns:
            A list of all teams.
        """
        with Session(self.engine) as session:
            query = select(TeamSchema)
            if name:
                query = query.where(TeamSchema.name == name)
            teams = session.exec(query.order_by(TeamSchema.name)).all()

            return [team.to_model() for team in teams]

    @track(AnalyticsEvent.UPDATED_TEAM)
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

    @track(AnalyticsEvent.DELETED_TEAM)
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

    @track(AnalyticsEvent.CREATED_ROLE)
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

    def list_roles(self, name: Optional[str] = None) -> List[RoleResponseModel]:
        """List all roles.

        Args:
            name: Optionally filter by name

        Returns:
            A list of all roles.
        """
        with Session(self.engine) as session:
            query = select(RoleSchema)
            if name:
                query = query.where(RoleSchema.name == name)
            roles = session.exec(query.order_by(RoleSchema.name)).all()

            return [role.to_model() for role in roles]

    @track(AnalyticsEvent.UPDATED_ROLE)
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
                                RolePermissionSchema.role_id == existing_role.id
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

    @track(AnalyticsEvent.DELETED_ROLE)
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

    def _list_user_role_assignments(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        role_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List[RoleAssignmentResponseModel]:
        """List all user role assignments.

        Args:
            project_name_or_id: If provided, only return role assignments for
                this project.
            user_name_or_id: If provided, only list assignments for this user.
            role_name_or_id: If provided, only list assignments of the given
                role

        Returns:
            A list of user role assignments.
        """
        with Session(self.engine) as session:
            query = select(UserRoleAssignmentSchema)
            if project_name_or_id is not None:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
                query = query.where(
                    UserRoleAssignmentSchema.project_id == project.id
                )
            if role_name_or_id is not None:
                role = self._get_role_schema(role_name_or_id, session=session)
                query = query.where(UserRoleAssignmentSchema.role_id == role.id)
            if user_name_or_id is not None:
                user = self._get_user_schema(user_name_or_id, session=session)
                query = query.where(UserRoleAssignmentSchema.user_id == user.id)
            assignments = session.exec(query).all()
            return [assignment.to_model() for assignment in assignments]

    def _list_team_role_assignments(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        team_name_or_id: Optional[Union[str, UUID]] = None,
        role_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List[RoleAssignmentResponseModel]:
        """List all team role assignments.

        Args:
            project_name_or_id: If provided, only return role assignments for
                this project.
            team_name_or_id: If provided, only list assignments for this team.
            role_name_or_id: If provided, only list assignments of the given
                role

        Returns:
            A list of team role assignments.
        """
        with Session(self.engine) as session:
            query = select(TeamRoleAssignmentSchema)
            if project_name_or_id is not None:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
                query = query.where(
                    TeamRoleAssignmentSchema.project_id == project.id
                )
            if role_name_or_id is not None:
                role = self._get_role_schema(role_name_or_id, session=session)
                query = query.where(TeamRoleAssignmentSchema.role_id == role.id)
            if team_name_or_id is not None:
                team = self._get_team_schema(team_name_or_id, session=session)
                query = query.where(TeamRoleAssignmentSchema.team_id == team.id)
            assignments = session.exec(query).all()
            return [assignment.to_model() for assignment in assignments]

    def list_role_assignments(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        role_name_or_id: Optional[Union[str, UUID]] = None,
        team_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List[RoleAssignmentResponseModel]:
        """List all role assignments.

        Args:
            project_name_or_id: If provided, only return role assignments for
                this project.
            role_name_or_id: If provided, only list assignments of the given
                role
            team_name_or_id: If provided, only list assignments for this team.
            user_name_or_id: If provided, only list assignments for this user.

        Returns:
            A list of all role assignments.
        """
        user_role_assignments = self._list_user_role_assignments(
            project_name_or_id=project_name_or_id,
            user_name_or_id=user_name_or_id,
            role_name_or_id=role_name_or_id,
        )
        team_role_assignments = self._list_team_role_assignments(
            project_name_or_id=project_name_or_id,
            team_name_or_id=team_name_or_id,
            role_name_or_id=role_name_or_id,
        )
        return user_role_assignments + team_role_assignments

    def _assign_role_to_user(
        self,
        role_name_or_id: Union[str, UUID],
        user_name_or_id: Union[str, UUID],
        project_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> RoleAssignmentResponseModel:
        """Assigns a role to a user, potentially scoped to a specific project.

        Args:
            project_name_or_id: Optional ID of a project in which to assign the
                role. If this is not provided, the role will be assigned
                globally.
            role_name_or_id: Name or ID of the role to assign.
            user_name_or_id: Name or ID of the user to which to assign the role.

        Returns:
            A model of the role assignment.

        Raises:
            EntityExistsError: If the role assignment already exists.
        """
        with Session(self.engine) as session:
            role = self._get_role_schema(role_name_or_id, session=session)
            project: Optional[ProjectSchema] = None
            if project_name_or_id:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
            user = self._get_user_schema(user_name_or_id, session=session)
            query = select(UserRoleAssignmentSchema).where(
                UserRoleAssignmentSchema.user_id == user.id,
                UserRoleAssignmentSchema.role_id == role.id,
            )
            if project is not None:
                query = query.where(
                    UserRoleAssignmentSchema.project_id == project.id
                )
            existing_role_assignment = session.exec(query).first()
            if existing_role_assignment is not None:
                raise EntityExistsError(
                    f"Unable to assign role '{role.name}' to user "
                    f"'{user.name}': Role already assigned in this project."
                )
            role_assignment = UserRoleAssignmentSchema(
                role_id=role.id,
                user_id=user.id,
                project_id=project.id if project else None,
                role=role,
                user=user,
                project=project,
            )
            session.add(role_assignment)
            session.commit()
            return role_assignment.to_model()

    def _assign_role_to_team(
        self,
        role_name_or_id: Union[str, UUID],
        team_name_or_id: Union[str, UUID],
        project_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> RoleAssignmentResponseModel:
        """Assigns a role to a team, potentially scoped to a specific project.

        Args:
            role_name_or_id: Name or ID of the role to assign.
            team_name_or_id: Name or ID of the team to which to assign the role.
            project_name_or_id: Optional ID of a project in which to assign the
                role. If this is not provided, the role will be assigned
                globally.

        Returns:
            A model of the role assignment.

        Raises:
            EntityExistsError: If the role assignment already exists.
        """
        with Session(self.engine) as session:
            role = self._get_role_schema(role_name_or_id, session=session)
            project: Optional[ProjectSchema] = None
            if project_name_or_id:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
            team = self._get_team_schema(team_name_or_id, session=session)
            query = select(TeamRoleAssignmentSchema).where(
                TeamRoleAssignmentSchema.team_id == team.id,
                TeamRoleAssignmentSchema.role_id == role.id,
            )
            if project is not None:
                query = query.where(
                    TeamRoleAssignmentSchema.project_id == project.id
                )
            existing_role_assignment = session.exec(query).first()
            if existing_role_assignment is not None:
                raise EntityExistsError(
                    f"Unable to assign role '{role.name}' to team "
                    f"'{team.name}': Role already assigned in this project."
                )
            role_assignment = TeamRoleAssignmentSchema(
                role_id=role.id,
                team_id=team.id,
                project_id=project.id if project else None,
                role=role,
                team=team,
                project=project,
            )
            session.add(role_assignment)
            session.commit()

            return role_assignment.to_model()

    def create_role_assignment(
        self, role_assignment: RoleAssignmentRequestModel
    ) -> RoleAssignmentResponseModel:
        """Assigns a role to a user or team, scoped to a specific project.

        Args:
            role_assignment: The role assignment to create.

        Returns:
            The created role assignment.

        Raises:
            ValueError: If neither a user nor a team is specified.
        """
        if role_assignment.user:
            return self._assign_role_to_user(
                role_name_or_id=role_assignment.role,
                user_name_or_id=role_assignment.user,
                project_name_or_id=role_assignment.project,
            )
        if role_assignment.team:
            return self._assign_role_to_team(
                role_name_or_id=role_assignment.role,
                team_name_or_id=role_assignment.team,
                project_name_or_id=role_assignment.project,
            )
        raise ValueError(
            "Role assignment must be assigned to either a user or a team."
        )

    def get_role_assignment(
        self, role_assignment_id: UUID
    ) -> RoleAssignmentResponseModel:
        """Gets a role assignment by ID.

        Args:
            role_assignment_id: ID of the role assignment to get.

        Returns:
            The role assignment.

        Raises:
            KeyError: If the role assignment does not exist.
        """
        with Session(self.engine) as session:
            user_role = session.exec(
                select(UserRoleAssignmentSchema).where(
                    UserRoleAssignmentSchema.id == role_assignment_id
                )
            ).one_or_none()

            if user_role:
                return user_role.to_model()

            team_role = session.exec(
                select(TeamRoleAssignmentSchema).where(
                    TeamRoleAssignmentSchema.id == role_assignment_id
                )
            ).one_or_none()

            if team_role:
                return team_role.to_model()

            raise KeyError(
                f"RoleAssignment with ID {role_assignment_id} not found."
            )

    def delete_role_assignment(self, role_assignment_id: UUID) -> None:
        """Delete a specific role assignment.

        Args:
            role_assignment_id: The ID of the specific role assignment.

        Raises:
            KeyError: If the role assignment does not exist.
        """
        with Session(self.engine) as session:
            user_role = session.exec(
                select(UserRoleAssignmentSchema).where(
                    UserRoleAssignmentSchema.id == role_assignment_id
                )
            ).one_or_none()
            if user_role:
                session.delete(user_role)

            team_role = session.exec(
                select(TeamRoleAssignmentSchema).where(
                    TeamRoleAssignmentSchema.id == role_assignment_id
                )
            ).one_or_none()

            if team_role:
                session.delete(team_role)

            if user_role is None and team_role is None:
                raise KeyError(
                    f"RoleAssignment with ID {role_assignment_id} not found."
                )
            else:
                session.commit()

    # --------
    # Projects
    # --------

    @track(AnalyticsEvent.CREATED_PROJECT)
    def create_project(
        self, project: ProjectRequestModel
    ) -> ProjectResponseModel:
        """Creates a new project.

        Args:
            project: The project to create.

        Returns:
            The newly created project.

        Raises:
            EntityExistsError: If a project with the given name already exists.
        """
        with Session(self.engine) as session:
            # Check if project with the given name already exists
            existing_project = session.exec(
                select(ProjectSchema).where(ProjectSchema.name == project.name)
            ).first()
            if existing_project is not None:
                raise EntityExistsError(
                    f"Unable to create project {project.name}: "
                    "A project with this name already exists."
                )

            # Create the project
            new_project = ProjectSchema.from_request(project)
            session.add(new_project)
            session.commit()

            # Explicitly refresh the new_project schema
            session.refresh(new_project)

            return new_project.to_model()

    def get_project(
        self, project_name_or_id: Union[str, UUID]
    ) -> ProjectResponseModel:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.

        Returns:
            The requested project if one was found.
        """
        with Session(self.engine) as session:
            project = self._get_project_schema(
                project_name_or_id, session=session
            )
        return project.to_model()

    def list_projects(
        self, name: Optional[str] = None
    ) -> List[ProjectResponseModel]:
        """List all projects.

        Args:
            name: Optionally filter by name

        Returns:
            A list of all projects.
        """
        with Session(self.engine) as session:
            query = select(ProjectSchema)
            if name:
                query = query.where(ProjectSchema.name == name)
            projects = session.exec(query.order_by(ProjectSchema.name)).all()

            return [project.to_model() for project in projects]

    @track(AnalyticsEvent.UPDATED_PROJECT)
    def update_project(
        self, project_id: UUID, project_update: ProjectUpdateModel
    ) -> ProjectResponseModel:
        """Update an existing project.

        Args:
            project_id: The ID of the project to be updated.
            project_update: The update to be applied to the project.

        Returns:
            The updated project.

        Raises:
            IllegalOperationError: if the project is the default project.
            KeyError: if the project does not exist.
        """
        with Session(self.engine) as session:
            existing_project = session.exec(
                select(ProjectSchema).where(ProjectSchema.id == project_id)
            ).first()
            if existing_project is None:
                raise KeyError(
                    f"Unable to update project with id "
                    f"'{project_id}': Found no"
                    f"existing projects with this id."
                )
            if (
                existing_project.name == self._default_project_name
                and "name" in project_update.__fields_set__
                and project_update.name != existing_project.name
            ):
                raise IllegalOperationError(
                    "The name of the default project cannot be changed."
                )

            # Update the project
            existing_project.update(project_update=project_update)
            session.add(existing_project)
            session.commit()

            # Refresh the Model that was just created
            session.refresh(existing_project)
            return existing_project.to_model()

    @track(AnalyticsEvent.DELETED_PROJECT)
    def delete_project(self, project_name_or_id: Union[str, UUID]) -> None:
        """Deletes a project.

        Args:
            project_name_or_id: Name or ID of the project to delete.

        Raises:
            IllegalOperationError: If the project is the default project.
        """
        with Session(self.engine) as session:
            # Check if project with the given name exists
            project = self._get_project_schema(
                project_name_or_id, session=session
            )
            if project.name == self._default_project_name:
                raise IllegalOperationError(
                    "The default project cannot be deleted."
                )

            session.delete(project)
            session.commit()

    # ---------
    # Pipelines
    # ---------

    @track(AnalyticsEvent.CREATE_PIPELINE)
    def create_pipeline(
        self,
        pipeline: PipelineRequestModel,
    ) -> PipelineResponseModel:
        """Creates a new pipeline in a project.

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
                .where(PipelineSchema.project_id == pipeline.project)
            ).first()
            if existing_pipeline is not None:
                raise EntityExistsError(
                    f"Unable to create pipeline in project "
                    f"'{pipeline.project}': A pipeline with this name "
                    f"already exists."
                )

            # Create the pipeline
            new_pipeline = PipelineSchema(
                name=pipeline.name,
                project_id=pipeline.project,
                user_id=pipeline.user,
                docstring=pipeline.docstring,
                spec=pipeline.spec.json(sort_keys=True),
            )
            session.add(new_pipeline)
            session.commit()
            # Refresh the Model that was just created
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
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
    ) -> List[PipelineResponseModel]:
        """List all pipelines in the project.

        Args:
            project_name_or_id: If provided, only list pipelines in this
                project.
            user_name_or_id: If provided, only list pipelines from this user.
            name: If provided, only list pipelines with this name.

        Returns:
            A list of pipelines.
        """
        with Session(self.engine) as session:
            # Check if project with the given name exists
            query = select(PipelineSchema)
            if project_name_or_id is not None:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
                query = query.where(PipelineSchema.project_id == project.id)

            if user_name_or_id is not None:
                user = self._get_user_schema(user_name_or_id, session=session)
                query = query.where(PipelineSchema.user_id == user.id)

            if name:
                query = query.where(PipelineSchema.name == name)

            # Get all pipelines in the project
            pipelines = session.exec(query).all()
            return [pipeline.to_model() for pipeline in pipelines]

    @track(AnalyticsEvent.UPDATE_PIPELINE)
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

    @track(AnalyticsEvent.DELETE_PIPELINE)
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

            configuration = json.dumps(pipeline_run.pipeline_configuration)

            new_run = PipelineRunSchema(
                id=pipeline_run.id,
                name=pipeline_run.name,
                orchestrator_run_id=pipeline_run.orchestrator_run_id,
                stack_id=stack_id,
                project_id=pipeline_run.project,
                user_id=pipeline_run.user,
                pipeline_id=pipeline_id,
                status=pipeline_run.status,
                pipeline_configuration=configuration,
                num_steps=pipeline_run.num_steps,
                git_sha=pipeline_run.git_sha,
                zenml_version=pipeline_run.zenml_version,
            )

            # Create the pipeline run
            session.add(new_run)
            session.commit()

            return new_run.to_model()

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
            return run.to_model()

    def get_or_create_run(
        self, pipeline_run: PipelineRunRequestModel
    ) -> PipelineRunResponseModel:
        """Gets or creates a pipeline run.

        If a run with the same ID or name already exists, it is returned.
        Otherwise, a new run is created.

        Args:
            pipeline_run: The pipeline run to get or create.

        Returns:
            The pipeline run.
        """
        # We want to have the 'create' statement in the try block since running
        # it first will reduce concurrency issues.
        try:
            return self.create_run(pipeline_run)
        except EntityExistsError:
            # Currently, an `EntityExistsError` is raised if either the run ID
            # or the run name already exists. Therefore, we need to have another
            # try block since getting the run by ID might still fail.
            try:
                return self.get_run(pipeline_run.id)
            except KeyError:
                return self.get_run(pipeline_run.name)

    def list_runs(
        self,
        name: Optional[str] = None,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[UUID] = None,
        component_id: Optional[UUID] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[UUID] = None,
        unlisted: bool = False,
    ) -> List[PipelineRunResponseModel]:
        """Gets all pipeline runs.

        Args:
            name: Run name if provided
            project_name_or_id: If provided, only return runs for this project.
            stack_id: If provided, only return runs for this stack.
            component_id: Optionally filter for runs that used the
                          component
            user_name_or_id: If provided, only return runs for this user.
            pipeline_id: If provided, only return runs for this pipeline.
            unlisted: If True, only return unlisted runs that are not
                associated with any pipeline (filter by pipeline_id==None).

        Returns:
            A list of all pipeline runs.
        """
        with Session(self.engine) as session:
            query = select(PipelineRunSchema)
            if project_name_or_id is not None:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
                query = query.where(PipelineRunSchema.project_id == project.id)
            if stack_id is not None:
                query = query.where(PipelineRunSchema.stack_id == stack_id)
            if component_id:
                query = query.where(
                    StackCompositionSchema.stack_id
                    == PipelineRunSchema.stack_id
                ).where(StackCompositionSchema.component_id == component_id)
            if name is not None:
                query = query.where(PipelineRunSchema.name == name)
            if pipeline_id is not None:
                query = query.where(
                    PipelineRunSchema.pipeline_id == pipeline_id
                )
            elif unlisted:
                query = query.where(is_(PipelineRunSchema.pipeline_id, None))
            if user_name_or_id is not None:
                user = self._get_user_schema(user_name_or_id, session=session)
                query = query.where(PipelineRunSchema.user_id == user.id)
            query = query.order_by(PipelineRunSchema.created)
            runs = session.exec(query).all()
            return [run.to_model() for run in runs]

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
            return existing_run.to_model()

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

            # Save parent step IDs into the database.
            for parent_step_id in step_run.parent_step_ids:
                self._set_run_step_parent_step(
                    child_id=step_schema.id,
                    parent_id=parent_step_id,
                    session=session,
                )

            # Save input artifact IDs into the database.
            for input_name, artifact_id in step_run.input_artifacts.items():
                self._set_run_step_input_artifact(
                    run_step_id=step_schema.id,
                    artifact_id=artifact_id,
                    name=input_name,
                    session=session,
                )

            # Save output artifact IDs into the database.
            for output_name, artifact_id in step_run.output_artifacts.items():
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
                    ArtifactSchema.id == StepRunOutputArtifactSchema.artifact_id
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
        self,
        run_id: Optional[UUID] = None,
        project_id: Optional[UUID] = None,
        cache_key: Optional[str] = None,
        status: Optional[ExecutionStatus] = None,
    ) -> List[StepRunResponseModel]:
        """Get all step runs.

        Args:
            run_id: If provided, only return steps for this pipeline run.
            project_id: If provided, only return step runs in this project.
            cache_key: If provided, only return steps with this cache key.
            status: If provided, only return steps with this status.

        Returns:
            A list of step runs.
        """
        query = select(StepRunSchema)
        if run_id is not None:
            query = query.where(StepRunSchema.pipeline_run_id == run_id)
        elif project_id is not None:
            query = query.where(
                StepRunSchema.pipeline_run_id == PipelineRunSchema.id
            ).where(PipelineRunSchema.project_id == project_id)
        if cache_key is not None:
            query = query.where(StepRunSchema.cache_key == cache_key)
        if status is not None:
            query = query.where(StepRunSchema.status == status)
        with Session(self.engine) as session:
            steps = session.exec(query).all()
            return [self._run_step_schema_to_model(step) for step in steps]

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
            for name, artifact_id in step_run_update.output_artifacts.items():
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
            artifact_schema = ArtifactSchema.from_request(artifact)
            session.add(artifact_schema)
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
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        artifact_uri: Optional[str] = None,
        artifact_store_id: Optional[UUID] = None,
        only_unused: bool = False,
    ) -> List[ArtifactResponseModel]:
        """Lists all artifacts.

        Args:
            project_name_or_id: If specified, only artifacts from the given
                project will be returned.
            artifact_uri: If specified, only artifacts with the given URI will
                be returned.
            artifact_store_id: If specified, only artifacts from the given
                artifact store will be returned.
            only_unused: If True, only return artifacts that are not used in
                any runs.

        Returns:
            A list of all artifacts.
        """
        with Session(self.engine) as session:
            query = select(ArtifactSchema)
            if project_name_or_id is not None:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
                query = query.where(ArtifactSchema.project_id == project.id)
            if artifact_uri is not None:
                query = query.where(ArtifactSchema.uri == artifact_uri)
            if artifact_store_id is not None:
                query = query.where(
                    ArtifactSchema.artifact_store_id == artifact_store_id
                )
            if only_unused:
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
            artifacts = session.exec(query).all()
            return [
                self._artifact_schema_to_model(artifact)
                for artifact in artifacts
            ]

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

    # =======================
    # Internal helper methods
    # =======================
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
            schema_class: The schema class to query. E.g., `ProjectSchema`.
            schema_name: The name of the schema used for error messages.
                E.g., "project".
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

        schema = session.exec(select(schema_class).where(filter_params)).first()

        if schema is None:
            raise KeyError(error_msg)
        return schema

    def _get_project_schema(
        self,
        project_name_or_id: Union[str, UUID],
        session: Session,
    ) -> ProjectSchema:
        """Gets a project schema by name or ID.

        This is a helper method that is used in various places to find the
        project associated to some other object.

        Args:
            project_name_or_id: The name or ID of the project to get.
            session: The database session to use.

        Returns:
            The project schema.
        """
        return self._get_schema_by_name_or_id(
            object_name_or_id=project_name_or_id,
            schema_class=ProjectSchema,
            schema_name="project",
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
