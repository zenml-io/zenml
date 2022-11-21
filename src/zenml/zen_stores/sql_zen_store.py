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

import logging
import os
import re
from datetime import datetime, timedelta
from pathlib import Path, PurePath
from threading import Lock, get_ident
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)
from uuid import UUID

from pydantic import root_validator
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError, NoResultFound
from sqlalchemy.sql.operators import is_, isnot
from sqlmodel import Session, SQLModel, create_engine, or_, select
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
    ArtifactModel,
    ComponentModel,
    FlavorModel,
    HydratedStackModel,
    PipelineModel,
    PipelineRunModel,
    ProjectModel,
    RoleAssignmentModel,
    RoleModel,
    StackModel,
    StepRunModel,
    TeamModel,
    UserModel,
)
from zenml.models.server_models import ServerDatabaseType, ServerModel
from zenml.utils import uuid_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track
from zenml.utils.enum_utils import StrEnum
from zenml.utils.networking_utils import (
    replace_localhost_with_internal_hostname,
)
from zenml.zen_stores.base_zen_store import (
    ADMIN_ROLE,
    DEFAULT_STACK_COMPONENT_NAME,
    DEFAULT_STACK_NAME,
    GUEST_ROLE,
    BaseZenStore,
)
from zenml.zen_stores.migrations.alembic import (
    ZENML_ALEMBIC_START_REVISION,
    Alembic,
)
from zenml.zen_stores.schemas import (
    ArtifactSchema,
    FlavorSchema,
    PipelineRunSchema,
    PipelineSchema,
    ProjectSchema,
    RoleSchema,
    StackComponentSchema,
    StackSchema,
    StepRunInputArtifactSchema,
    StepRunParentsSchema,
    StepRunSchema,
    TeamAssignmentSchema,
    TeamRoleAssignmentSchema,
    TeamSchema,
    UserRoleAssignmentSchema,
    UserSchema,
)
from zenml.zen_stores.schemas.stack_schemas import StackCompositionSchema
from zenml.zen_stores.schemas.user_management_schemas import (
    RolePermissionSchema,
)

if TYPE_CHECKING:
    from ml_metadata.proto.metadata_store_pb2 import (
        ConnectionConfig,
        MetadataStoreClientConfig,
    )

    from zenml.zen_stores.metadata_store import (
        MetadataStore,
        MLMDArtifactModel,
        MLMDPipelineRunModel,
        MLMDStepRunModel,
    )

# Enable SQL compilation caching to remove the https://sqlalche.me/e/14/cprf
# warning
SelectOfScalar.inherit_cache = True
Select.inherit_cache = True

logger = get_logger(__name__)

ZENML_SQLITE_DB_FILENAME = "zenml.db"


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
        grpc_metadata_host: The host to use for the gRPC metadata server.
        grpc_metadata_port: The port to use for the gRPC metadata server.
        grpc_metadata_ssl_ca: The certificate authority certificate to use for
            the gRPC metadata server connection.
        grpc_metadata_ssl_cert: The client certificate to use for the gRPC
            metadata server connection.
        grpc_metadata_ssl_key: The client certificate private key to use for
            the gRPC metadata server connection.
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

    grpc_metadata_host: Optional[str] = None
    grpc_metadata_port: Optional[int] = None
    grpc_metadata_ssl_ca: Optional[str] = None
    grpc_metadata_ssl_key: Optional[str] = None
    grpc_metadata_ssl_cert: Optional[str] = None

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
        """Create a copy of the store config using a different configuration path.

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

    def get_metadata_config(
        self, expand_certs: bool = False
    ) -> "ConnectionConfig":
        """Get the metadata configuration for the SQL ZenML store.

        Args:
            expand_certs: Whether to expand the certificate paths to their
                contents.

        Returns:
            The metadata configuration.

        Raises:
            NotImplementedError: If the SQL driver is not supported.
        """
        from ml_metadata.proto.metadata_store_pb2 import MySQLDatabaseConfig
        from tfx.orchestration import metadata

        sql_url = make_url(self.url)
        if sql_url.drivername == SQLDatabaseDriver.SQLITE:
            assert self.database is not None
            mlmd_config = metadata.sqlite_metadata_connection_config(
                self.database
            )
        elif sql_url.drivername == SQLDatabaseDriver.MYSQL:
            # all these are guaranteed by our root validator
            assert self.database is not None
            assert self.username is not None
            assert self.password is not None
            assert sql_url.host is not None

            mlmd_config = metadata.mysql_metadata_connection_config(
                host=sql_url.host,
                port=sql_url.port or 3306,
                database=self.database,
                username=self.username,
                password=self.password,
            )

            mlmd_ssl_options = {}
            # Handle certificate params
            for key in ["ssl_key", "ssl_ca", "ssl_cert"]:
                ssl_setting = getattr(self, key)
                if not ssl_setting:
                    continue
                if expand_certs and os.path.isfile(ssl_setting):
                    with open(ssl_setting, "r") as f:
                        ssl_setting = f.read()
                mlmd_ssl_options[key.lstrip("ssl_")] = ssl_setting

            # Handle additional params
            if mlmd_ssl_options:
                mlmd_ssl_options[
                    "verify_server_cert"
                ] = self.ssl_verify_server_cert
                mlmd_config.mysql.ssl_options.CopyFrom(
                    MySQLDatabaseConfig.SSLOptions(**mlmd_ssl_options)
                )
        else:
            raise NotImplementedError(
                f"SQL driver `{sql_url.drivername}` is not supported."
            )

        return mlmd_config

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
            # The following default value is needed for sqlite to avoid the Error:
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
        _metadata_store: The metadata store.
        _lock: A thread mutex used to ensure thread safety during the pipeline
            run synchronization.
    """

    config: SqlZenStoreConfiguration
    skip_migrations: bool = False
    TYPE: ClassVar[StoreType] = StoreType.SQL
    CONFIG_TYPE: ClassVar[Type[StoreConfiguration]] = SqlZenStoreConfiguration

    _engine: Optional[Engine] = None
    _metadata_store: Optional["MetadataStore"] = None
    _highest_synced_run_mlmd_id: int = 0
    _alembic: Optional[Alembic] = None
    _sync_lock: Optional[Lock] = None

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
    def metadata_store(self) -> "MetadataStore":
        """The metadata store.

        Returns:
            The metadata store.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._metadata_store:
            raise ValueError("Store not initialized")
        return self._metadata_store

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

    @property
    def sync_lock(self) -> Lock:
        """The mutex used to synchronize pipeline runs.

        Returns:
            The mutex used to synchronize pipeline runs.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._sync_lock:
            raise ValueError("Store not initialized")
        return self._sync_lock

    # ====================================
    # ZenML Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the SQL store."""
        from zenml.zen_stores.metadata_store import MetadataStore

        logger.debug("Initializing SqlZenStore at %s", self.config.url)

        metadata_config = self.config.get_metadata_config()
        self._metadata_store = MetadataStore(config=metadata_config)

        url, connect_args, engine_args = self.config.get_sqlmodel_config()
        self._engine = create_engine(
            url=url, connect_args=connect_args, **engine_args
        )
        self._alembic = Alembic(self.engine)
        if (
            not self.skip_migrations
            and ENV_ZENML_DISABLE_DATABASE_MIGRATION not in os.environ
        ):
            self.migrate_database()

        self._sync_lock = Lock()

    def migrate_database(self) -> None:
        """Migrate the database to the head as defined by the current python package."""
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
        """
        model = super().get_store_info()
        sql_url = make_url(self.config.url)
        model.database_type = ServerDatabaseType(sql_url.drivername)
        return model

    # ------------
    # TFX Metadata
    # ------------

    def get_metadata_config(
        self, expand_certs: bool = False
    ) -> Union["ConnectionConfig", "MetadataStoreClientConfig"]:
        """Get the TFX metadata config of this ZenStore.

        Args:
            expand_certs: Whether to expand the certificate paths in the
                connection config to their value.

        Returns:
            The TFX metadata config of this ZenStore.
        """
        from ml_metadata.proto.metadata_store_pb2 import (
            MetadataStoreClientConfig,
        )

        # If the gRPC metadata store connection configuration is present,
        # advertise it to the client instead of the direct SQL connection
        # config.
        if self.config.grpc_metadata_host:
            mlmd_config = MetadataStoreClientConfig()
            mlmd_config.host = self.config.grpc_metadata_host
            mlmd_config.port = self.config.grpc_metadata_port
            if self.config.grpc_metadata_ssl_ca:
                mlmd_config.ssl_config.custom_ca = (
                    self.config.grpc_metadata_ssl_ca
                )
            if self.config.grpc_metadata_ssl_cert:
                mlmd_config.ssl_config.server_cert = (
                    self.config.grpc_metadata_ssl_cert
                )
            if self.config.grpc_metadata_ssl_key:
                mlmd_config.ssl_config.client_key = (
                    self.config.grpc_metadata_ssl_key
                )

            return mlmd_config

        return self.config.get_metadata_config(expand_certs=expand_certs)

    # ------
    # Stacks
    # ------

    @track(AnalyticsEvent.REGISTERED_STACK)
    def create_stack(
        self,
        stack: StackModel,
    ) -> StackModel:
        """Register a new stack.

        Args:
            stack: The stack to register.

        Returns:
            The registered stack.

        Raises:
            KeyError: If one or more of the stack's components are not
                registered in the store.
        """
        with Session(self.engine) as session:
            project = self._get_project_schema(stack.project, session=session)
            user = self._get_user_schema(stack.user, session=session)

            self.fail_if_stack_with_id_already_exists(
                stack=stack, session=session
            )

            self.fail_if_stack_with_name_exists_for_user(
                stack=stack, project=project, user=user, session=session
            )

            if stack.is_shared:
                self.fail_if_stack_with_name_already_shared(
                    stack=stack, project=project, session=session
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
            defined_component_ids = [c.id for c in defined_components]

            # check if all component IDs are valid
            if len(component_ids) > 0 and len(defined_component_ids) != len(
                component_ids
            ):
                raise KeyError(
                    f"Some components referenced in the stack were not found: "
                    f"{set(component_ids) - set(defined_component_ids)}"
                )

            # Create the stack
            stack_in_db = StackSchema.from_create_model(
                defined_components=defined_components,
                stack=stack,
            )
            session.add(stack_in_db)
            session.commit()

            session.refresh(stack_in_db)

            return stack_in_db.to_model()

    def get_stack(self, stack_id: UUID) -> StackModel:
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
        hydrated: bool = False,
    ) -> Union[List[StackModel], List[HydratedStackModel]]:
        """List all stacks matching the given filter criteria.

        Args:
            project_name_or_id: Id or name of the Project containing the stack
            user_name_or_id: Optionally filter stacks by their owner
            component_id: Optionally filter for stacks that contain the
                          component
            name: Optionally filter stacks by their name
            is_shared: Optionally filter out stacks by whether they are shared
                or not
            hydrated: Flag to decide whether to return hydrated models.

        Returns:
            A list of all stacks matching the filter criteria.
        """
        with Session(self.engine) as session:
            # Get a list of all stacks
            query = select(StackSchema)
            # TODO: prettify
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

            if hydrated:
                return [stack.to_hydrated_model() for stack in stacks]
            else:
                return [stack.to_model() for stack in stacks]

    @track(AnalyticsEvent.UPDATED_STACK)
    def update_stack(self, stack: StackModel) -> StackModel:
        """Update a stack.

        Args:
            stack: The stack to use for the update.

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
                select(StackSchema).where(StackSchema.id == stack.id)
            ).first()
            if existing_stack is None:
                raise KeyError(
                    f"Unable to update stack with id "
                    f"'{stack.id}': Found no"
                    f"existing stack with this id."
                )
            if existing_stack.name == DEFAULT_STACK_NAME:
                raise IllegalOperationError(
                    "The default stack cannot be modified."
                )
            # In case of a renaming update, make sure no stack already exists
            # with that name
            if existing_stack.name != stack.name:
                project = self._get_project_schema(
                    project_name_or_id=stack.project, session=session
                )
                user = self._get_user_schema(
                    user_name_or_id=stack.user, session=session
                )
                self.fail_if_stack_with_name_exists_for_user(
                    stack=stack, project=project, user=user, session=session
                )

            # Check if stack update makes the stack a shared stack,
            # In that case check if a stack with the same name is
            # already shared within the project
            if not existing_stack.is_shared and stack.is_shared:
                project = self._get_project_schema(
                    project_name_or_id=stack.project, session=session
                )
                self.fail_if_stack_with_name_already_shared(
                    stack=stack, project=project, session=session
                )

            # Get the Schemas of all components mentioned
            filters = [
                (StackComponentSchema.id == component_id)
                for list_of_component_ids in stack.components.values()
                for component_id in list_of_component_ids
            ]

            defined_components = session.exec(
                select(StackComponentSchema).where(or_(*filters))
            ).all()

            existing_stack.from_update_model(
                stack=stack, defined_components=defined_components
            )
            session.add(existing_stack)
            session.commit()

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

    @staticmethod
    def fail_if_stack_with_id_already_exists(
        stack: StackModel, session: Session
    ) -> None:
        """Raise an exception if a Stack with the same id already exists.

        Args:
            stack: The Stack
            session: The Session

        Raises:
            StackExistsError: If a stack with the same id already
                              exists
        """
        existing_id_stack = session.exec(
            select(StackSchema).where(StackSchema.id == stack.id)
        ).first()
        if existing_id_stack is not None:
            raise StackExistsError(
                f"Unable to register stack with name "
                f"'{stack.name}' and id '{stack.id}': "
                f" Found an existing component with the same id."
            )

    @staticmethod
    def fail_if_stack_with_name_exists_for_user(
        stack: StackModel,
        project: ProjectSchema,
        session: Session,
        user: UserSchema,
    ) -> None:
        """Raise an exception if a Component with same name exists for user.

        Args:
            stack: The Stack
            project: The project scope within which to check
            user: The user that owns the Stack
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
            raise StackExistsError(
                f"Unable to register stack with name "
                f"'{stack.name}': Found an existing stack with the same "
                f"name in the active project, '{project.name}', owned by the "
                f"same user, '{user.name}'."
            )
        return None

    def fail_if_stack_with_name_already_shared(
        self, stack: StackModel, project: ProjectSchema, session: Session
    ) -> None:
        """Raise an exception if a Stack with same name is already shared.

        Args:
            stack: The Stack
            project: The project scope within which to check
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
            raise StackExistsError(
                f"Unable to share stack with name '{stack.name}': Found an "
                f"existing shared stack with the same name in project "
                f"'{project.name}'."
            )

    # ----------------
    # Stack components
    # ----------------

    @track(AnalyticsEvent.REGISTERED_STACK_COMPONENT)
    def create_stack_component(
        self,
        component: ComponentModel,
    ) -> ComponentModel:
        """Create a stack component.

        Args:
            component: The stack component to create.

        Returns:
            The created stack component.
        """
        with Session(self.engine) as session:
            project = self._get_project_schema(
                project_name_or_id=component.project, session=session
            )
            user = self._get_user_schema(
                user_name_or_id=component.user, session=session
            )

            self.fail_if_component_with_id_already_exists(
                component=component, session=session
            )

            self.fail_if_component_with_name_type_exists_for_user(
                component=component, project=project, user=user, session=session
            )

            if component.is_shared:
                self.fail_if_component_with_name_type_already_shared(
                    component=component, project=project, session=session
                )

            # Create the component
            component_in_db = StackComponentSchema.from_create_model(
                component=component
            )

            session.add(component_in_db)
            session.commit()

            session.refresh(component_in_db)

            return component_in_db.to_model()

    def get_stack_component(self, component_id: UUID) -> ComponentModel:
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
    ) -> List[ComponentModel]:
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
        self, component: ComponentModel
    ) -> ComponentModel:
        """Update an existing stack component.

        Args:
            component: The stack component model to use for the update.

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
                    StackComponentSchema.id == component.id
                )
            ).first()

            if existing_component is None:
                raise KeyError(
                    f"Unable to update component with id "
                    f"'{component.id}': Found no"
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
            if existing_component.name != component.name:
                project = self._get_project_schema(
                    project_name_or_id=component.project, session=session
                )
                user = self._get_user_schema(
                    user_name_or_id=component.user, session=session
                )
                self.fail_if_component_with_name_type_exists_for_user(
                    component=component,
                    project=project,
                    user=user,
                    session=session,
                )

            # Check if component update makes the component a shared component,
            # In that case check if a component with the same name, type are
            # already shared within the project
            if not existing_component.is_shared and component.is_shared:
                project = self._get_project_schema(
                    project_name_or_id=component.project, session=session
                )
                self.fail_if_component_with_name_type_already_shared(
                    component=component, project=project, session=session
                )

            existing_component.from_update_model(component=component)
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

    def get_stack_component_side_effects(
        self,
        component_id: UUID,
        run_id: UUID,
        pipeline_id: UUID,
        stack_id: UUID,
    ) -> Dict[Any, Any]:
        """Get the side effects of a stack component.

        Args:
            component_id: The id of the stack component to get side effects for.
            run_id: The id of the run to get side effects for.
            pipeline_id: The id of the pipeline to get side effects for.
            stack_id: The id of the stack to get side effects for.
        """
        pass  # TODO: implement this

    @staticmethod
    def fail_if_component_with_id_already_exists(
        component: ComponentModel, session: Session
    ) -> None:
        """Raise an exception if a Component with the same id already exists.

        Args:
            component: The Component
            session: The Session

        Raises:
            StackComponentExistsError: If a component with the same id already
                                       exists
        """
        existing_id_component = session.exec(
            select(StackComponentSchema).where(
                StackComponentSchema.id == component.id
            )
        ).first()
        if existing_id_component is not None:
            raise StackComponentExistsError(
                f"Unable to register '{component.type.value}' component "
                f"with name '{component.name}' and id '{component.id}': "
                f" Found an existing component with the same id."
            )

    @staticmethod
    def fail_if_component_with_name_type_exists_for_user(
        component: ComponentModel,
        project: ProjectSchema,
        session: Session,
        user: UserSchema,
    ) -> None:
        """Raise an exception if a Component with same name/type exists for user.

        Args:
            component: The Component
            project: The project scope within which to check
            user: The user that owns the Component
            session: The Session

        Returns:
            None

        Raises:
            StackComponentExistsError: If a component with the given name and
                                       type is already owned by the user
        """
        # Check if component with the same domain key (name, type, project,
        # owner) already exists
        existing_domain_component = session.exec(
            select(StackComponentSchema)
            .where(StackComponentSchema.name == component.name)
            .where(StackComponentSchema.project_id == component.project)
            .where(StackComponentSchema.user_id == component.user)
            .where(StackComponentSchema.type == component.type)
        ).first()
        if existing_domain_component is not None:
            raise StackComponentExistsError(
                f"Unable to register '{component.type.value}' component "
                f"with name '{component.name}': Found an existing "
                f"component with the same name and type in the same "
                f" project, '{project.name}', owned by the same "
                f" user, '{user.name}'."
            )
        return None

    def fail_if_component_with_name_type_already_shared(
        self,
        component: ComponentModel,
        project: ProjectSchema,
        session: Session,
    ) -> None:
        """Raise an exception if a Component with same name/type already shared.

        Args:
            component: The Component
            project: The project scope within which to check
            session: The Session

        Raises:
            StackComponentExistsError: If a component with the given name and
                                       type is already shared by a user
        """
        # Check if component with the same name, type is already shared
        # within the project
        existing_shared_component = session.exec(
            select(StackComponentSchema)
            .where(StackComponentSchema.name == component.name)
            .where(StackComponentSchema.project_id == component.project)
            .where(StackComponentSchema.is_shared == component.is_shared)
            .where(StackComponentSchema.type == component.type)
        ).first()
        if existing_shared_component is not None:
            raise StackComponentExistsError(
                f"Unable to shared component of type '{component.type.value}' "
                f"with name '{component.name}': Found an existing shared "
                f"component with the same name and type in project "
                f"'{project.name}'."
            )

    # -----------------------
    # Stack component flavors
    # -----------------------

    @track(AnalyticsEvent.CREATED_FLAVOR)
    def create_flavor(
        self,
        flavor: FlavorModel,
    ) -> FlavorModel:
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
            flavor_in_db = FlavorSchema.from_create_model(flavor=flavor)

            session.add(flavor_in_db)
            session.commit()

            return flavor_in_db.to_model()

    def get_flavor(self, flavor_id: UUID) -> FlavorModel:
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
    ) -> List[FlavorModel]:
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

    @track(AnalyticsEvent.UPDATED_FLAVOR)
    def update_flavor(self, flavor: FlavorModel) -> FlavorModel:
        """Update an existing stack component flavor.

        Args:
            flavor: The model of the flavor to update.

        Returns:
            The updated flavor.

        Raises:
            KeyError: if the flavor doesn't exist.
        """
        with Session(self.engine) as session:
            existing_flavor = session.exec(
                select(FlavorSchema).where(FlavorSchema.id == flavor.id)
            ).first()

            if existing_flavor is None:
                raise KeyError(
                    f"Unable to update flavor with id '{flavor.id}': Found no"
                    f"existing component with this id."
                )

            existing_flavor.from_update_model(flavor=flavor)
            session.add(existing_flavor)
            session.commit()

        return existing_flavor.to_model()

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

    @property
    def active_user_name(self) -> str:
        """Gets the active username.

        Returns:
            The active username.
        """
        return self._default_user_name

    @track(AnalyticsEvent.CREATED_USER)
    def create_user(self, user: UserModel) -> UserModel:
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
            new_user = UserSchema.from_create_model(user)
            session.add(new_user)
            session.commit()

            return new_user.to_model()

    def get_user(self, user_name_or_id: Union[str, UUID]) -> UserModel:
        """Gets a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The requested user, if it was found.
        """
        with Session(self.engine) as session:
            user = self._get_user_schema(user_name_or_id, session=session)
        return user.to_model()

    def list_users(self) -> List[UserModel]:
        """List all users.

        Returns:
            A list of all users.
        """
        with Session(self.engine) as session:
            users = session.exec(select(UserSchema)).all()

        return [user.to_model() for user in users]

    @track(AnalyticsEvent.UPDATED_USER)
    def update_user(self, user: UserModel) -> UserModel:
        """Updates an existing user.

        Args:
            user: The User model to use for the update.

        Returns:
            The updated user.

        Raises:
            IllegalOperationError: If the request tries to update the username
                for the default user account.
        """
        with Session(self.engine) as session:
            existing_user = self._get_user_schema(user.id, session=session)
            if (
                existing_user.name == self._default_user_name
                and user.name != existing_user.name
            ):
                raise IllegalOperationError(
                    "The username of the default user account cannot be "
                    "changed."
                )
            existing_user.from_update_model(user)
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

    def user_email_opt_in(
        self,
        user_name_or_id: Union[str, UUID],
        user_opt_in_response: bool,
        email: Optional[str] = None,
    ) -> UserModel:
        """Persist user response to the email prompt.

        Args:
            user_name_or_id: The name or the ID of the user.
            user_opt_in_response: Whether this email should be associated
                with the user id in the telemetry
            email: The users email

        Returns:
            The updated user.
        """
        with Session(self.engine) as session:
            user = self._get_user_schema(user_name_or_id, session=session)
            # TODO: In the future we might want to validate that the email
            #  is non-empty and valid at this point if user_opt_in_response
            #  is True
            user.email = email
            user.email_opted_in = user_opt_in_response
            session.add(user)
            session.commit()

            return user.to_model()

    # -----
    # Teams
    # -----

    @track(AnalyticsEvent.CREATED_TEAM)
    def create_team(self, team: TeamModel) -> TeamModel:
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

            # Create the team
            new_team = TeamSchema.from_create_model(team)
            session.add(new_team)
            session.commit()

            return new_team.to_model()

    def get_team(self, team_name_or_id: Union[str, UUID]) -> TeamModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.
        """
        with Session(self.engine) as session:
            team = self._get_team_schema(team_name_or_id, session=session)
        return team.to_model()

    def list_teams(self) -> List[TeamModel]:
        """List all teams.

        Returns:
            A list of all teams.
        """
        with Session(self.engine) as session:
            teams = session.exec(select(TeamSchema)).all()
            return [team.to_model() for team in teams]

    @track(AnalyticsEvent.UPDATED_TEAM)
    def update_team(self, team: TeamModel) -> TeamModel:
        """Update an existing team.

        Args:
            team: The team to use for the update.

        Returns:
            The updated team.

        Raises:
            KeyError: if the team does not exist.
        """
        with Session(self.engine) as session:
            existing_team = session.exec(
                select(TeamSchema).where(TeamSchema.id == team.id)
            ).first()

            if existing_team is None:
                raise KeyError(
                    f"Unable to update team with id "
                    f"'{team.id}': Found no"
                    f"existing teams with this id."
                )

            # Update the team
            existing_team.from_update_model(team)

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

    # ---------------
    # Team membership
    # ---------------

    def get_users_for_team(
        self, team_name_or_id: Union[str, UUID]
    ) -> List[UserModel]:
        """Fetches all users of a team.

        Args:
            team_name_or_id: The name or ID of the team for which to get users.

        Returns:
            A list of all users that are part of the team.
        """
        with Session(self.engine) as session:
            team = self._get_team_schema(team_name_or_id, session=session)
            return [user.to_model() for user in team.users]

    def get_teams_for_user(
        self, user_name_or_id: Union[str, UUID]
    ) -> List[TeamModel]:
        """Fetches all teams for a user.

        Args:
            user_name_or_id: The name or ID of the user for which to get all
                teams.

        Returns:
            A list of all teams that the user is part of.
        """
        with Session(self.engine) as session:
            user = self._get_user_schema(user_name_or_id, session=session)
            return [team.to_model() for team in user.teams]

    def add_user_to_team(
        self,
        user_name_or_id: Union[str, UUID],
        team_name_or_id: Union[str, UUID],
    ) -> None:
        """Adds a user to a team.

        Args:
            user_name_or_id: Name or ID of the user to add to the team.
            team_name_or_id: Name or ID of the team to which to add the user to.

        Raises:
            EntityExistsError: If the user is already a member of the team.
        """
        with Session(self.engine) as session:
            team = self._get_team_schema(team_name_or_id, session=session)
            user = self._get_user_schema(user_name_or_id, session=session)

            # Check if user is already in the team
            existing_user_in_team = session.exec(
                select(TeamAssignmentSchema)
                .where(TeamAssignmentSchema.user_id == user.id)
                .where(TeamAssignmentSchema.team_id == team.id)
            ).first()
            if existing_user_in_team is not None:
                raise EntityExistsError(
                    f"Unable to add user '{user.name}' to team "
                    f"'{team.name}': User is already in the team."
                )

            # Add user to team
            team.users = team.users + [user]
            session.add(team)
            session.commit()

    def remove_user_from_team(
        self,
        user_name_or_id: Union[str, UUID],
        team_name_or_id: Union[str, UUID],
    ) -> None:
        """Removes a user from a team.

        Args:
            user_name_or_id: Name or ID of the user to remove from the team.
            team_name_or_id: Name or ID of the team from which to remove the
                user.
        """
        with Session(self.engine) as session:
            team = self._get_team_schema(team_name_or_id, session=session)
            user = self._get_user_schema(user_name_or_id, session=session)

            # Remove user from team
            team.users = [user_ for user_ in team.users if user_.id != user.id]
            session.add(team)
            session.commit()

    # -----
    # Roles
    # -----

    @track(AnalyticsEvent.CREATED_ROLE)
    def create_role(self, role: RoleModel) -> RoleModel:
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
            role_schema = RoleSchema.from_create_model(role)
            session.add(role_schema)
            session.commit()
            # Add all permissions
            for p in role.permissions:
                session.add(
                    RolePermissionSchema(name=p, role_id=role_schema.id)
                )

            session.commit()
            return role_schema.to_model()

    def get_role(self, role_name_or_id: Union[str, UUID]) -> RoleModel:
        """Gets a specific role.

        Args:
            role_name_or_id: Name or ID of the role to get.

        Returns:
            The requested role.
        """
        with Session(self.engine) as session:
            role = self._get_role_schema(role_name_or_id, session=session)
            return role.to_model()

    def list_roles(self) -> List[RoleModel]:
        """List all roles.

        Returns:
            A list of all roles.
        """
        with Session(self.engine) as session:
            roles = session.exec(select(RoleSchema)).all()

            return [role.to_model() for role in roles]

    @track(AnalyticsEvent.UPDATED_ROLE)
    def update_role(self, role: RoleModel) -> RoleModel:
        """Update an existing role.

        Args:
            role: The role to use for the update.

        Returns:
            The updated role.

        Raises:
            KeyError: if the role does not exist.
            IllegalOperationError: if the role is a system role.
        """
        with Session(self.engine) as session:
            existing_role = session.exec(
                select(RoleSchema).where(RoleSchema.id == role.id)
            ).first()

            if existing_role is None:
                raise KeyError(
                    f"Unable to update role with id "
                    f"'{role.id}': Found no"
                    f"existing roles with this id."
                )

            if existing_role.name in [ADMIN_ROLE, GUEST_ROLE]:
                raise IllegalOperationError(
                    f"The built-in role '{role.name}' cannot be updated."
                )

            # Update the role
            existing_role.from_update_model(role)

            session.add(existing_role)
            session.commit()

            existing_permissions = {p.name for p in existing_role.permissions}

            diff = existing_permissions.symmetric_difference(role.permissions)

            for permission in diff:
                if permission not in role.permissions:
                    permission_to_delete = session.exec(
                        select(RolePermissionSchema)
                        .where(RolePermissionSchema.name == permission)
                        .where(RolePermissionSchema.role_id == existing_role.id)
                    ).one_or_none()
                    session.delete(permission_to_delete)

                elif permission not in existing_permissions:
                    session.add(
                        RolePermissionSchema(
                            name=permission, role_id=existing_role.id
                        )
                    )

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
            if role.name in [ADMIN_ROLE, GUEST_ROLE]:
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
                # TODO: Eventually we might want to allow this deletion
                #  and simply cascade
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
    ) -> List[RoleAssignmentModel]:
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
    ) -> List[RoleAssignmentModel]:
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
    ) -> List[RoleAssignmentModel]:
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
    ) -> None:
        """Assigns a role to a user, potentially scoped to a specific project.

        Args:
            project_name_or_id: Optional ID of a project in which to assign the
                role. If this is not provided, the role will be assigned
                globally.
            role_name_or_id: Name or ID of the role to assign.
            user_name_or_id: Name or ID of the user to which to assign the role.

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

    def _assign_role_to_team(
        self,
        role_name_or_id: Union[str, UUID],
        team_name_or_id: Union[str, UUID],
        project_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> None:
        """Assigns a role to a team, potentially scoped to a specific project.

        Args:
            role_name_or_id: Name or ID of the role to assign.
            team_name_or_id: Name or ID of the team to which to assign the role.
            project_name_or_id: Optional ID of a project in which to assign the
                role. If this is not provided, the role will be assigned
                globally.

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

    def assign_role(
        self,
        role_name_or_id: Union[str, UUID],
        user_or_team_name_or_id: Union[str, UUID],
        project_name_or_id: Optional[Union[str, UUID]] = None,
        is_user: bool = True,
    ) -> None:
        """Assigns a role to a user or team, scoped to a specific project.

        Args:
            project_name_or_id: Optional ID of a project in which to assign the
                role. If this is not provided, the role will be assigned
                globally.
            role_name_or_id: Name or ID of the role to assign.
            user_or_team_name_or_id: Name or ID of the user or team to which to
                assign the role.
            is_user: Whether `user_or_team_name_or_id` refers to a user or a
                team.
        """
        if is_user:
            self._assign_role_to_user(
                role_name_or_id=role_name_or_id,
                user_name_or_id=user_or_team_name_or_id,
                project_name_or_id=project_name_or_id,
            )
        else:
            self._assign_role_to_team(
                role_name_or_id=role_name_or_id,
                team_name_or_id=user_or_team_name_or_id,
                project_name_or_id=project_name_or_id,
            )

    def revoke_role(
        self,
        role_name_or_id: Union[str, UUID],
        user_or_team_name_or_id: Union[str, UUID],
        is_user: bool = True,
        project_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> None:
        """Revokes a role from a user or team for a given project.

        Args:
            project_name_or_id: Optional ID of a project in which to revoke the
                role. If this is not provided, the role will be revoked
                globally.
            role_name_or_id: Name or ID of the role to revoke.
            user_or_team_name_or_id: Name or ID of the user or team from which
                to revoke the role.
            is_user: Whether `user_or_team_name_or_id` refers to a user or a
                team.

        Raises:
            KeyError: If the role, user, team, or project does not exists.
        """
        with Session(self.engine) as session:
            project: Optional[ProjectSchema] = None
            if project_name_or_id:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )

            role = self._get_role_schema(role_name_or_id, session=session)

            role_assignment: Optional[SQLModel] = None

            if is_user:
                user = self._get_user_schema(
                    user_or_team_name_or_id, session=session
                )
                assignee_name = user.name
                user_role_query = (
                    select(UserRoleAssignmentSchema)
                    .where(UserRoleAssignmentSchema.user_id == user.id)
                    .where(UserRoleAssignmentSchema.role_id == role.id)
                )
                if project:
                    user_role_query = user_role_query.where(
                        UserRoleAssignmentSchema.project_id == project.id
                    )

                role_assignment = session.exec(user_role_query).first()
            else:
                team = self._get_team_schema(
                    user_or_team_name_or_id, session=session
                )
                assignee_name = team.name
                team_role_query = (
                    select(TeamRoleAssignmentSchema)
                    .where(TeamRoleAssignmentSchema.team_id == team.id)
                    .where(TeamRoleAssignmentSchema.role_id == role.id)
                )
                if project:
                    team_role_query = team_role_query.where(
                        TeamRoleAssignmentSchema.project_id == project.id
                    )

                role_assignment = session.exec(team_role_query).first()

            if role_assignment is None:
                assignee = "user" if is_user else "team"
                scope = f" in project '{project.name}'" if project else ""
                raise KeyError(
                    f"Unable to unassign role '{role.name}' from {assignee} "
                    f"'{assignee_name}'{scope}: The role is currently not "
                    f"assigned to the {assignee}."
                )

            session.delete(role_assignment)
            session.commit()

    # --------
    # Projects
    # --------

    @track(AnalyticsEvent.CREATED_PROJECT)
    def create_project(self, project: ProjectModel) -> ProjectModel:
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
            new_project = ProjectSchema.from_create_model(project)
            session.add(new_project)
            session.commit()

            # Explicitly refresh the new_project schema
            session.refresh(new_project)

            return new_project.to_model()

    def get_project(self, project_name_or_id: Union[str, UUID]) -> ProjectModel:
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

    def list_projects(self) -> List[ProjectModel]:
        """List all projects.

        Returns:
            A list of all projects.
        """
        with Session(self.engine) as session:
            projects = session.exec(select(ProjectSchema)).all()
            return [project.to_model() for project in projects]

    @track(AnalyticsEvent.UPDATED_PROJECT)
    def update_project(self, project: ProjectModel) -> ProjectModel:
        """Update an existing project.

        Args:
            project: The project to use for the update.

        Returns:
            The updated project.

        Raises:
            IllegalOperationError: if the project is the default project.
        """
        with Session(self.engine) as session:
            existing_project = self._get_project_schema(
                project.id, session=session
            )
            if (
                existing_project.name == self._default_project_name
                and project.name != existing_project.name
            ):
                raise IllegalOperationError(
                    "The name of the default project cannot be changed."
                )

            # Update the project
            existing_project.from_update_model(project)

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

    # ------------
    # Repositories
    # ------------

    # ---------
    # Pipelines
    # ---------

    @track(AnalyticsEvent.CREATE_PIPELINE)
    def create_pipeline(
        self,
        pipeline: PipelineModel,
    ) -> PipelineModel:
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
            new_pipeline = PipelineSchema.from_create_model(pipeline=pipeline)
            session.add(new_pipeline)
            session.commit()
            # Refresh the Model that was just created
            session.refresh(new_pipeline)

            return new_pipeline.to_model()

    def get_pipeline(self, pipeline_id: UUID) -> PipelineModel:
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
    ) -> List[PipelineModel]:
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
    def update_pipeline(self, pipeline: PipelineModel) -> PipelineModel:
        """Updates a pipeline.

        Args:
            pipeline: The pipeline to use for the update.

        Returns:
            The updated pipeline.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if pipeline with the given ID exists
            existing_pipeline = session.exec(
                select(PipelineSchema).where(PipelineSchema.id == pipeline.id)
            ).first()
            if existing_pipeline is None:
                raise KeyError(
                    f"Unable to update pipeline with ID {pipeline.id}: "
                    f"No pipeline with this ID found."
                )

            # Update the pipeline
            existing_pipeline.from_update_model(pipeline)

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

    def create_run(self, pipeline_run: PipelineRunModel) -> PipelineRunModel:
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

            # Check if pipeline run with same name MLMD ID already exists.
            if pipeline_run.mlmd_id is not None:
                existing_mlmd_id_run = session.exec(
                    select(PipelineRunSchema).where(
                        PipelineRunSchema.mlmd_id == pipeline_run.mlmd_id
                    )
                ).first()
                if existing_mlmd_id_run is not None:
                    raise EntityExistsError(
                        f"Unable to create pipeline run: A pipeline run with "
                        f"MLMD ID '{pipeline_run.mlmd_id}' already exists."
                    )

            # Query stack
            if pipeline_run.stack_id is not None:
                stack = session.exec(
                    select(StackSchema).where(
                        StackSchema.id == pipeline_run.stack_id
                    )
                ).first()
                if stack is None:
                    logger.warning(
                        f"No stack with ID '{pipeline_run.stack_id}' found. "
                        f"Creating pipeline run '{pipeline_run.name}' without "
                        "linked stack."
                    )
                    pipeline_run.stack_id = None

            # Query pipeline
            pipeline = None
            if pipeline_run.pipeline_id is not None:
                pipeline = session.exec(
                    select(PipelineSchema).where(
                        PipelineSchema.id == pipeline_run.pipeline_id
                    )
                ).first()
                if pipeline is None:
                    logger.warning(
                        f"No pipeline with ID '{pipeline_run.pipeline_id}' "
                        f"found. Creating pipeline run '{pipeline_run.name}' "
                        f"as unlisted run."
                    )
                    pipeline_run.pipeline_id = None

            new_run = PipelineRunSchema.from_create_model(
                run=pipeline_run, pipeline=pipeline
            )

            # Create the pipeline run
            session.add(new_run)
            session.commit()

            return new_run.to_model()

    def get_run(self, run_name_or_id: Union[str, UUID]) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            run_name_or_id: The name or ID of the pipeline run to get.

        Returns:
            The pipeline run.
        """
        if not self.runs_inside_server:
            self._sync_runs()
        with Session(self.engine) as session:
            run = self._get_run_schema(run_name_or_id, session=session)
            return run.to_model()

    def get_or_create_run(
        self, pipeline_run: PipelineRunModel
    ) -> PipelineRunModel:
        """Gets or creates a pipeline run.

        If a run with the same ID or name already exists, it is returned.
        Otherwise, a new run is created.

        Args:
            pipeline_run: The pipeline run to get or create.

        Returns:
            The pipeline run.
        """
        # We want to have the create statement in the try block since running it
        # first will reduce concurrency issues.
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
        project_name_or_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[UUID] = None,
        component_id: Optional[UUID] = None,
        run_name: Optional[str] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[UUID] = None,
        unlisted: bool = False,
    ) -> List[PipelineRunModel]:
        """Gets all pipeline runs.

        Args:
            project_name_or_id: If provided, only return runs for this project.
            stack_id: If provided, only return runs for this stack.
            component_id: Optionally filter for runs that used the
                          component
            run_name: Run name if provided
            user_name_or_id: If provided, only return runs for this user.
            pipeline_id: If provided, only return runs for this pipeline.
            unlisted: If True, only return unlisted runs that are not
                associated with any pipeline (filter by pipeline_id==None).

        Returns:
            A list of all pipeline runs.
        """
        if not self.runs_inside_server:
            self._sync_runs()
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
            if run_name is not None:
                query = query.where(PipelineRunSchema.name == run_name)
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

    def update_run(self, run: PipelineRunModel) -> PipelineRunModel:
        """Updates a pipeline run.

        Args:
            run: The pipeline run to use for the update.

        Returns:
            The updated pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if pipeline run with the given ID exists
            existing_run = session.exec(
                select(PipelineRunSchema).where(PipelineRunSchema.id == run.id)
            ).first()
            if existing_run is None:
                raise KeyError(
                    f"Unable to update pipeline run with ID {run.id}: "
                    f"No pipeline run with this ID found."
                )

            # Update the pipeline run
            existing_run.from_update_model(run)
            session.add(existing_run)
            session.commit()

            session.refresh(existing_run)
            return existing_run.to_model()

    def get_run_component_side_effects(
        self,
        run_id: UUID,
        component_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Gets the side effects for a component in a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.
            component_id: The ID of the component to get.
        """
        # TODO: raise KeyError if run doesn't exist
        pass  # TODO

    # ------------------
    # Pipeline run steps
    # ------------------

    def create_run_step(self, step: StepRunModel) -> StepRunModel:
        """Creates a step.

        Args:
            step: The step to create.

        Returns:
            The created step.

        Raises:
            EntityExistsError: if the step already exists.
            KeyError: if the pipeline run doesn't exist.
        """
        with Session(self.engine) as session:

            # Check if the step already exists
            if step.mlmd_id is not None:
                existing_step = session.exec(
                    select(StepRunSchema).where(
                        StepRunSchema.mlmd_id == step.mlmd_id
                    )
                ).first()
                if existing_step is not None:
                    raise EntityExistsError(
                        f"Unable to create step '{step.name}': A step with "
                        f"MLMD ID '{step.mlmd_id}' already exists."
                    )

            # Check if the pipeline run exists
            run = session.exec(
                select(PipelineRunSchema).where(
                    PipelineRunSchema.id == step.pipeline_run_id
                )
            ).first()
            if run is None:
                raise KeyError(
                    f"Unable to create step '{step.name}': No pipeline run "
                    f"with ID '{step.pipeline_run_id}' found."
                )

            # Check if the step name already exists in the pipeline run
            existing_step = session.exec(
                select(StepRunSchema)
                .where(StepRunSchema.name == step.name)
                .where(StepRunSchema.pipeline_run_id == step.pipeline_run_id)
            ).first()
            if existing_step is not None:
                raise EntityExistsError(
                    f"Unable to create step '{step.name}': A step with this "
                    f"name already exists in the pipeline run with ID "
                    f"'{step.pipeline_run_id}'."
                )

            # Create the step
            step_schema = StepRunSchema.from_create_model(step)
            session.add(step_schema)
            session.commit()

            # Save parent step IDs into the database.
            for parent_step_id in step.parent_step_ids:
                self._set_run_step_parent_step(
                    child_id=step.id, parent_id=parent_step_id
                )

            # Save input artifact IDs into the database.
            for input_name, artifact_id in step.input_artifacts.items():
                self._set_run_step_input_artifact(
                    step_id=step.id,
                    artifact_id=artifact_id,
                    name=input_name,
                )

            return step_schema.to_model(
                parent_step_ids=step.parent_step_ids,
                mlmd_parent_step_ids=step.mlmd_parent_step_ids,
                input_artifacts=step.input_artifacts,
            )

    def _set_run_step_parent_step(
        self, child_id: UUID, parent_id: UUID
    ) -> None:
        """Sets the parent step for a step.

        Args:
            child_id: The ID of the child step to set the parent for.
            parent_id: The ID of the parent step to set a child for.

        Raises:
            KeyError: if the child step or parent step doesn't exist.
        """
        with Session(self.engine) as session:

            # Check if the child step exists.
            child_step = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == child_id)
            ).first()
            if child_step is None:
                raise KeyError(
                    f"Unable to set parent step for step with ID "
                    f"{child_id}: No step with this ID found."
                )

            # Check if the parent step exists.
            parent_step = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == parent_id)
            ).first()
            if parent_step is None:
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
            session.commit()

    def _set_run_step_input_artifact(
        self, step_id: UUID, artifact_id: UUID, name: str
    ) -> None:
        """Sets an artifact as an input of a step.

        Args:
            step_id: The ID of the step.
            artifact_id: The ID of the artifact.
            name: The name of the input in the step.

        Raises:
            KeyError: if the step or artifact doesn't exist.
        """
        with Session(self.engine) as session:

            # Check if the step exists.
            step = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == step_id)
            ).first()
            if step is None:
                raise KeyError(
                    f"Unable to set input artifact: No step with ID "
                    f"'{step_id}' found."
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
                .where(StepRunInputArtifactSchema.step_id == step_id)
                .where(StepRunInputArtifactSchema.artifact_id == artifact_id)
            ).first()
            if assignment is not None:
                return

            # Save the input assignment in the database.
            assignment = StepRunInputArtifactSchema(
                step_id=step_id, artifact_id=artifact_id, name=name
            )
            session.add(assignment)
            session.commit()

    def get_run_step(self, step_id: UUID) -> StepRunModel:
        """Get a step by ID.

        Args:
            step_id: The ID of the step to get.

        Returns:
            The step.

        Raises:
            KeyError: if the step doesn't exist.
        """
        if not self.runs_inside_server:
            self._sync_runs()
        with Session(self.engine) as session:
            step = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == step_id)
            ).first()
            if step is None:
                raise KeyError(
                    f"Unable to get step with ID {step_id}: No step with this "
                    "ID found."
                )
            return self._run_step_schema_to_model(step)

    def _run_step_schema_to_model(self, step: StepRunSchema) -> StepRunModel:
        """Converts a run step schema to a step model.

        Args:
            step: The run step schema to convert.

        Returns:
            The run step model.
        """
        with Session(self.engine) as session:

            # Get parent steps.
            parent_steps = session.exec(
                select(StepRunSchema)
                .where(StepRunParentsSchema.child_id == step.id)
                .where(StepRunParentsSchema.parent_id == StepRunSchema.id)
            ).all()
            parent_step_ids = [parent_step.id for parent_step in parent_steps]
            mlmd_parent_step_ids = [
                parent_step.mlmd_id
                for parent_step in parent_steps
                if parent_step.mlmd_id is not None
            ]

            # Get input artifacts.
            input_artifact_list = session.exec(
                select(
                    StepRunInputArtifactSchema.artifact_id,
                    StepRunInputArtifactSchema.name,
                ).where(StepRunInputArtifactSchema.step_id == step.id)
            ).all()
            input_artifacts = {
                input_artifact[1]: input_artifact[0]
                for input_artifact in input_artifact_list
            }

            # Convert to model.
            return step.to_model(
                parent_step_ids=parent_step_ids,
                mlmd_parent_step_ids=mlmd_parent_step_ids,
                input_artifacts=input_artifacts,
            )

    def list_run_steps(
        self, run_id: Optional[UUID] = None
    ) -> List[StepRunModel]:
        """Get all run steps.

        Args:
            run_id: If provided, only return steps for this pipeline run.

        Returns:
            A list of all run steps.
        """
        if not self.runs_inside_server:
            self._sync_runs()
        query = select(StepRunSchema)
        if run_id is not None:
            query = query.where(StepRunSchema.pipeline_run_id == run_id)
        with Session(self.engine) as session:
            steps = session.exec(query).all()
            return [self._run_step_schema_to_model(step) for step in steps]

    def update_run_step(self, step: StepRunModel) -> StepRunModel:
        """Updates a step.

        Args:
            step: The step to update.

        Returns:
            The updated step.

        Raises:
            KeyError: if the step doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if the step exists
            existing_step = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == step.id)
            ).first()
            if existing_step is None:
                raise KeyError(
                    f"Unable to update step with ID {step.id}: "
                    f"No step with this ID found."
                )

            # Update the step
            existing_step.from_update_model(step)
            session.add(existing_step)
            session.commit()

            session.refresh(existing_step)
            return existing_step.to_model(
                parent_step_ids=step.parent_step_ids,
                mlmd_parent_step_ids=step.mlmd_parent_step_ids,
                input_artifacts=step.input_artifacts,
            )

    def get_run_step_inputs(self, step_id: UUID) -> Dict[str, ArtifactModel]:
        """Get the inputs for a specific step.

        Args:
            step_id: The id of the step to get inputs for.

        Returns:
            A dict mapping artifact names to the input artifacts for the step.

        Raises:
            KeyError: if the step doesn't exist.
        """
        with Session(self.engine) as session:
            step = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == step_id)
            ).first()
            if step is None:
                raise KeyError(
                    f"Unable to get input artifacts for step with ID "
                    f"{step_id}: No step with this ID found."
                )
            query_result = session.exec(
                select(ArtifactSchema, StepRunInputArtifactSchema)
                .where(
                    ArtifactSchema.id == StepRunInputArtifactSchema.artifact_id
                )
                .where(StepRunInputArtifactSchema.step_id == step_id)
            ).all()
            return {
                step_input_artifact.name: artifact.to_model()
                for artifact, step_input_artifact in query_result
            }

    # ---------
    # Artifacts
    # ---------

    def create_artifact(self, artifact: ArtifactModel) -> ArtifactModel:
        """Creates an artifact.

        Args:
            artifact: The artifact to create.

        Returns:
            The created artifact.

        Raises:
            KeyError: if the parent step doesn't exist.
            EntityExistsError: if the artifact already exists.
        """
        with Session(self.engine) as session:
            # Check if the step exists
            step = session.exec(
                select(StepRunSchema).where(
                    StepRunSchema.id == artifact.parent_step_id
                )
            ).first()
            if step is None:
                raise KeyError(
                    f"Unable to create artifact: Could not find parent step "
                    f"with ID '{artifact.parent_step_id}'."
                )

            # Check if the artifact already exists
            if artifact.mlmd_id is not None:
                existing_artifact = session.exec(
                    select(ArtifactSchema)
                    .where(ArtifactSchema.mlmd_id == artifact.mlmd_id)
                    .where(
                        ArtifactSchema.mlmd_parent_step_id
                        == artifact.mlmd_parent_step_id
                    )
                ).first()
                if existing_artifact is not None:
                    raise EntityExistsError(
                        f"Unable to create artifact: An artifact with MLMD ID "
                        f"'{artifact.mlmd_id}' already exists as output of "
                        f"step '{artifact.mlmd_parent_step_id}'."
                    )

            # Create the artifact
            artifact_schema = ArtifactSchema.from_create_model(artifact)
            session.add(artifact_schema)
            session.commit()
            return artifact_schema.to_model()

    def list_artifacts(
        self,
        artifact_uri: Optional[str] = None,
        parent_step_id: Optional[UUID] = None,
    ) -> List[ArtifactModel]:
        """Lists all artifacts.

        Args:
            artifact_uri: If specified, only artifacts with the given URI will
                be returned.
            parent_step_id: If specified, only artifacts for the given step run
                will be returned.

        Returns:
            A list of all artifacts.
        """
        if not self.runs_inside_server:
            self._sync_runs()
        with Session(self.engine) as session:
            query = select(ArtifactSchema)
            if artifact_uri is not None:
                query = query.where(ArtifactSchema.uri == artifact_uri)
            if parent_step_id is not None:
                query = query.where(
                    ArtifactSchema.parent_step_id == parent_step_id
                )
            artifacts = session.exec(query).all()
            return [artifact.to_model() for artifact in artifacts]

    # =======================
    # Internal helper methods
    # =======================

    def _get_schema_by_name_or_id(
        self,
        object_name_or_id: Union[str, UUID],
        schema_class: Type[SQLModel],
        schema_name: str,
        session: Session,
    ) -> SQLModel:
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
            filter = schema_class.id == object_name_or_id  # type: ignore[attr-defined]
            error_msg = (
                f"Unable to get {schema_name} with name or ID "
                f"'{object_name_or_id}': No {schema_name} with this ID found."
            )
        else:
            filter = schema_class.name == object_name_or_id  # type: ignore[attr-defined]
            error_msg = (
                f"Unable to get {schema_name} with name or ID "
                f"'{object_name_or_id}': '{object_name_or_id}' is not a valid "
                f" UUID and no {schema_name} with this name exists."
            )

        schema = session.exec(select(schema_class).where(filter)).first()

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
        return cast(
            ProjectSchema,
            self._get_schema_by_name_or_id(
                object_name_or_id=project_name_or_id,
                schema_class=ProjectSchema,
                schema_name="project",
                session=session,
            ),
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
        return cast(
            UserSchema,
            self._get_schema_by_name_or_id(
                object_name_or_id=user_name_or_id,
                schema_class=UserSchema,
                schema_name="user",
                session=session,
            ),
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
        return cast(
            TeamSchema,
            self._get_schema_by_name_or_id(
                object_name_or_id=team_name_or_id,
                schema_class=TeamSchema,
                schema_name="team",
                session=session,
            ),
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
        return cast(
            RoleSchema,
            self._get_schema_by_name_or_id(
                object_name_or_id=role_name_or_id,
                schema_class=RoleSchema,
                schema_name="role",
                session=session,
            ),
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
        return cast(
            PipelineRunSchema,
            self._get_schema_by_name_or_id(
                object_name_or_id=run_name_or_id,
                schema_class=PipelineRunSchema,
                schema_name="run",
                session=session,
            ),
        )

    # MLMD Stuff

    def _resolve_mlmd_step_id(self, mlmd_id: int) -> UUID:
        """Resolves a step ID from MLMD to a ZenML step ID.

        Args:
            mlmd_id: The MLMD ID of the step.

        Returns:
            The ZenML step ID.

        Raises:
            KeyError: if the step couldn't be found.
        """
        with Session(self.engine) as session:
            step = session.exec(
                select(StepRunSchema).where(StepRunSchema.mlmd_id == mlmd_id)
            ).first()
            if step is None:
                raise KeyError(
                    f"Unable to resolve MLMD step ID {mlmd_id}: "
                    f"No step with this ID found."
                )
            return step.id

    def _resolve_mlmd_artifact_id(
        self, mlmd_id: int, mlmd_parent_step_id: int
    ) -> UUID:
        """Resolves an artifact ID from MLMD to a ZenML artifact ID.

        Since a single MLMD artifact can map to multiple ZenML artifacts, we
        also need to know the parent step to resolve this correctly.

        Args:
            mlmd_id: The MLMD ID of the artifact.
            mlmd_parent_step_id: The MLMD ID of the parent step.

        Returns:
            The ZenML artifact ID.

        Raises:
            KeyError: if the artifact couldn't be found.
        """
        with Session(self.engine) as session:
            artifact = session.exec(
                select(ArtifactSchema)
                .where(ArtifactSchema.mlmd_id == mlmd_id)
                .where(
                    ArtifactSchema.mlmd_parent_step_id == mlmd_parent_step_id
                )
            ).first()
            if artifact is None:
                raise KeyError(
                    f"Unable to resolve MLMD artifact ID {mlmd_id}: "
                    f"No artifact with this ID found."
                )
            return artifact.id

    def _sync_runs(self) -> None:
        """Sync runs from MLMD into the database.

        This queries all runs from MLMD, checks for each whether it already
        exists in the database, and if not, creates it.
        """
        from zenml.zen_stores.migrations.alembic import AlembicVersion
        from zenml.zen_stores.rest_zen_store import DEFAULT_HTTP_TIMEOUT

        # This is to synchronize the locally running threads so that only
        # one thread attempts to sync the runs at any given time.
        # The timeout is set to be shorter than the default REST client
        # timeout, so that we don't block the client for too long.
        logger.debug(f"[{get_ident()}] Trying to acquire sync lock...")
        if not self.sync_lock.acquire(timeout=DEFAULT_HTTP_TIMEOUT - 10):
            logger.warning(
                f"[{get_ident()}] Timed out waiting to acquire pipeline "
                f"run sync lock. Skipping the sync this time around."
            )
            return

        logger.debug(f"[{get_ident()}] Pipeline run sync lock acquired.")
        try:
            with Session(self.engine) as session:
                logger.debug("Syncing pipeline runs...")
                if self.config.driver != SQLDatabaseDriver.SQLITE:
                    # This is to synchronize all server processes trying to
                    # sync the pipeline runs at the same time. We use the
                    # alembic version table as a shared resource that we can
                    # lock to prevent multiple processes from syncing runs
                    # at the same time.
                    session.query(AlembicVersion).with_for_update().all()
                self._sync_runs_with_lock(session)
                logger.debug("Pipeline runs sync complete")
        except Exception:
            logger.exception("Failed to sync pipeline runs.")
        finally:
            self.sync_lock.release()

    def _sync_runs_with_lock(self, session: Session) -> None:
        """Sync runs from MLMD into the database while the DB is locked.

        This queries all runs from MLMD, checks for each whether it already
        exists in the database, and if not, creates it.

        Args:
            session: The database session to use.
        """
        # Find all runs that already have an MLMD ID. These are already
        # synced and connected to MLMD, so we don't need to query them from
        # MLMD again.
        synced_mlmd_ids = session.exec(
            select(PipelineRunSchema.mlmd_id).where(
                isnot(PipelineRunSchema.mlmd_id, None)
            )
        ).all()
        logger.debug(f"Found {len(synced_mlmd_ids)} pipeline runs with MLMD ID")

        # Find all runs that have no MLMD ID. These might need to be
        # connected.
        runs_without_mlmd_id = session.exec(
            select(PipelineRunSchema).where(
                is_(PipelineRunSchema.mlmd_id, None)
            )
        ).all()
        logger.debug(
            f"Found {len(runs_without_mlmd_id)} pipeline runs without MLMD ID"
        )
        runs_without_mlmd_id_dict = {
            run_.name: run_ for run_ in runs_without_mlmd_id
        }

        # Sync all MLMD runs that don't exist in ZenML. For performance reasons,
        # we determine this by explicitly ignoring runs that are already synced.
        unsynced_mlmd_runs = self.metadata_store.get_all_runs(
            ignored_ids=[id_ for id_ in synced_mlmd_ids if id_ is not None]
        )
        logger.debug(
            f"Adding {len(unsynced_mlmd_runs)} new pipeline runs from MLMD"
        )
        for mlmd_run in unsynced_mlmd_runs:

            # If a run is written in both ZenML and MLMD but doesn't have an
            # MLMD ID set in the DB, we need to set it to connect the two.
            if mlmd_run.name in runs_without_mlmd_id_dict:
                run_model = runs_without_mlmd_id_dict[mlmd_run.name].to_model()
                run_model.mlmd_id = mlmd_run.mlmd_id
                try:
                    self.update_run(run_model)
                except Exception as err:
                    logger.warning(
                        f"Syncing run '{mlmd_run.name}' failed: {str(err)}"
                    )
                    continue

            # Create runs that are in MLMD but not in the DB.
            else:
                try:
                    self._sync_run(mlmd_run)
                except EntityExistsError as exists_err:
                    logger.debug(
                        f"Run '{mlmd_run.name}' already exists: "
                        f"{str(exists_err)}. Skipping sync."
                    )
                    continue
                except Exception as err:
                    logger.warning(
                        f"Syncing run '{mlmd_run.name}' failed: {str(err)}"
                    )
                    continue

        # Sync steps and status of all unfinished runs.
        # We also filter out anything older than 1 week to prevent old broken
        # unfinished runs from being synced over and over again.
        unfinished_runs = session.exec(
            select(PipelineRunSchema)
            .where(PipelineRunSchema.status == ExecutionStatus.RUNNING)
            .where(
                PipelineRunSchema.updated >= datetime.now() - timedelta(weeks=1)
            )
        ).all()
        logger.debug(
            f"Updating {len(unfinished_runs)} unfinished pipeline runs from "
            "MLMD"
        )
        for run_ in unfinished_runs:
            try:
                logger.debug(f"Syncing run steps for pipeline run '{run_.id}'")
                self._sync_run_steps(run_.id)
                logger.debug(
                    f"Updating run status for pipeline run '{run_.id}'"
                )
                self._sync_run_status(run_.to_model())
            except Exception as err:
                logger.warning(f"Syncing run '{run_.name}' failed: {str(err)}")

        logger.debug("Pipeline runs sync complete.")

    def _sync_run(self, mlmd_run: "MLMDPipelineRunModel") -> PipelineRunModel:
        """Sync a single run from MLMD into the database.

        Args:
            mlmd_run: The MLMD run model to sync.

        Returns:
            The synced run model.
        """
        new_run = PipelineRunModel(
            name=mlmd_run.name,
            mlmd_id=mlmd_run.mlmd_id,
            project=mlmd_run.project or self._default_project.id,  # For legacy
            user=mlmd_run.user or self._default_user.id,  # For legacy
            stack_id=mlmd_run.stack_id,
            pipeline_id=mlmd_run.pipeline_id,
            pipeline_configuration=mlmd_run.pipeline_configuration,
            num_steps=mlmd_run.num_steps,
            status=ExecutionStatus.RUNNING,  # Update later.
        )
        return self.create_run(new_run)

    def _sync_run_steps(self, run_id: UUID) -> None:
        """Sync run steps from MLMD into the database.

        Since we do not allow to create steps in the database directly, this is
        a one-way sync from MLMD to the database.

        Args:
            run_id: The ID of the pipeline run to sync steps for.

        Raises:
            KeyError: if the run couldn't be found.
        """
        with Session(self.engine) as session:
            run = session.exec(
                select(PipelineRunSchema).where(PipelineRunSchema.id == run_id)
            ).first()

            # If the run doesn't exist, raise an error.
            if run is None:
                raise KeyError(
                    f"Unable to sync run steps for run with ID {run_id}: "
                    f"No run with this ID found."
                )

            # If the run didn't come from MLMD, we can't sync artifacts.
            if run.mlmd_id is None:
                return

            # Get all steps that already exist in the database.
            zenml_steps = session.exec(
                select(StepRunSchema).where(
                    StepRunSchema.pipeline_run_id == run_id
                )
            ).all()
            zenml_step_dict = {step.name: step for step in zenml_steps}

        # Get all steps from MLMD.
        mlmd_steps = self.metadata_store.get_pipeline_run_steps(run.mlmd_id)

        # For each step in MLMD, sync it into ZenML if it doesn't exist yet.
        for step_name, mlmd_step in mlmd_steps.items():
            if step_name not in zenml_step_dict:
                try:
                    step_model = self._sync_run_step(
                        run_id, step_name, mlmd_step
                    )
                except EntityExistsError as exists_err:
                    logger.debug(
                        f"Run step '{step_name}' of run {run.name} already "
                        f"exists: {str(exists_err)}. Skipping sync."
                    )
                    continue
            else:
                step_schema = zenml_step_dict[step_name]
                step_model = self._run_step_schema_to_model(step_schema)

            # Sync artifacts and status of all unfinished steps.
            self._sync_run_step_artifacts(step_model)
            self._sync_run_step_status(step_model)

    def _sync_run_step(
        self, run_id: UUID, step_name: str, mlmd_step: "MLMDStepRunModel"
    ) -> StepRunModel:
        """Sync a single run step from MLMD into the database.

        Args:
            run_id: The ID of the pipeline run to sync the step for.
            step_name: The name of the step to sync.
            mlmd_step: The MLMD step model to sync.

        Returns:
            The synced run step model.
        """
        # Build dict of input artifacts.
        mlmd_inputs = self.metadata_store.get_step_input_artifacts(
            step_id=mlmd_step.mlmd_id,
            step_parent_step_ids=mlmd_step.mlmd_parent_step_ids,
        )
        input_artifacts = {}
        for input_name, mlmd_artifact in mlmd_inputs.items():
            artifact_id = self._resolve_mlmd_artifact_id(
                mlmd_id=mlmd_artifact.mlmd_id,
                mlmd_parent_step_id=mlmd_artifact.mlmd_parent_step_id,
            )
            input_artifacts[input_name] = artifact_id

        # Create step.
        new_step = StepRunModel(
            name=step_name,
            mlmd_id=mlmd_step.mlmd_id,
            mlmd_parent_step_ids=mlmd_step.mlmd_parent_step_ids,
            entrypoint_name=mlmd_step.entrypoint_name,
            parameters=mlmd_step.parameters,
            step_configuration=mlmd_step.step_configuration,
            docstring=mlmd_step.docstring,
            num_outputs=mlmd_step.num_outputs,
            pipeline_run_id=run_id,
            parent_step_ids=[
                self._resolve_mlmd_step_id(parent_step_id)
                for parent_step_id in mlmd_step.mlmd_parent_step_ids
            ],
            input_artifacts=input_artifacts,
            status=ExecutionStatus.RUNNING,  # Update later.
        )
        return self.create_run_step(new_step)

    def _sync_run_step_artifacts(self, step_model: StepRunModel) -> None:
        """Sync run step artifacts from MLMD into the database.

        Since we do not allow to create artifacts in the database directly, this
        is a one-way sync from MLMD to the database.

        Args:
            step_model: The model of the step run to sync artifacts for.
        """
        # If the step didn't come from MLMD, we can't sync artifacts.
        if step_model.mlmd_id is None:
            return

        # Get the names of all outputs that are already in ZenML.
        with Session(self.engine) as session:
            zenml_output_names = session.exec(
                select(ArtifactSchema.name).where(
                    ArtifactSchema.parent_step_id == step_model.id
                )
            ).all()

        # Get all MLMD output artifacts.
        mlmd_outputs = self.metadata_store.get_step_output_artifacts(
            step_id=step_model.mlmd_id
        )

        # For each output in MLMD, sync it into ZenML if it doesn't exist yet.
        for output_name, mlmd_artifact in mlmd_outputs.items():
            if output_name not in zenml_output_names:
                try:
                    self._sync_run_step_artifact(output_name, mlmd_artifact)
                except EntityExistsError as exists_err:
                    logger.debug(
                        f"Artifact {output_name} already exists: "
                        f"{str(exists_err)}. Skipping sync."
                    )
                    continue

    def _sync_run_step_artifact(
        self, output_name: str, mlmd_artifact: "MLMDArtifactModel"
    ) -> ArtifactModel:
        """Sync a single run step artifact from MLMD into the database.

        Args:
            output_name: The name of the output artifact.
            mlmd_artifact: The MLMD artifact model to sync.

        Returns:
            The synced artifact model.
        """
        new_artifact = ArtifactModel(
            name=output_name,
            mlmd_id=mlmd_artifact.mlmd_id,
            type=mlmd_artifact.type,
            uri=mlmd_artifact.uri,
            materializer=mlmd_artifact.materializer,
            data_type=mlmd_artifact.data_type,
            mlmd_parent_step_id=mlmd_artifact.mlmd_parent_step_id,
            mlmd_producer_step_id=mlmd_artifact.mlmd_producer_step_id,
            is_cached=mlmd_artifact.is_cached,
            parent_step_id=self._resolve_mlmd_step_id(
                mlmd_artifact.mlmd_parent_step_id
            ),
            producer_step_id=self._resolve_mlmd_step_id(
                mlmd_artifact.mlmd_producer_step_id
            ),
        )
        return self.create_artifact(new_artifact)

    def _sync_run_step_status(self, step_model: StepRunModel) -> StepRunModel:
        """Updates the status of a step run model.

        In contrast to other update methods, this does not use the status of the
        model to overwrite the DB. Instead, the status is queried from MLMD.

        Args:
            step_model: The step run model to update.

        Returns:
            The step run model with updated status.
        """
        # Update status only if the step is running and has an MLMD ID.
        if (
            step_model.status != ExecutionStatus.RUNNING
            or step_model.mlmd_id is None
        ):
            return step_model

        # Check if all output artifacts have been synced.
        all_synced = True
        if step_model.num_outputs and step_model.num_outputs > 0:
            with Session(self.engine) as session:
                outputs = session.exec(
                    select(ArtifactSchema).where(
                        ArtifactSchema.parent_step_id == step_model.id
                    )
                ).all()
            if len(outputs) < step_model.num_outputs:
                all_synced = False

        # Get the status from MLMD and update the model if necessary.
        status = self.metadata_store.get_step_status(step_model.mlmd_id)
        is_failed = status == ExecutionStatus.FAILED
        is_done = status in (ExecutionStatus.COMPLETED, ExecutionStatus.CACHED)
        if is_failed or (is_done and all_synced):
            step_model.status = status
            self.update_run_step(step_model)

        return step_model

    def _sync_run_status(self, run_model: PipelineRunModel) -> PipelineRunModel:
        """Updates the status of a pipeline run model.

        In contrast to other update methods, this does not use the status of the
        model to overwrite the DB. Instead, the status is computed based on the
        status of each step, and if that is different from the status in the DB,
        the DB and model are both updated.

        Args:
            run_model: The pipeline run model to update.

        Returns:
            The pipeline run model with updated status.
        """
        # Update status only if the run is running.
        if run_model.status != ExecutionStatus.RUNNING:
            return run_model

        # Get all steps of the run.
        with Session(self.engine) as session:
            steps = session.exec(
                select(StepRunSchema).where(
                    StepRunSchema.pipeline_run_id == run_model.id
                )
            ).all()

        # Check if all steps have been synced.
        all_synced = True
        if run_model.num_steps and run_model.num_steps > 0:
            if len(steps) < run_model.num_steps:
                all_synced = False

        # Compute the status of the run based on the status of the steps and
        # update the model if necessary.
        status = ExecutionStatus.run_status([step.status for step in steps])
        is_failed = status == ExecutionStatus.FAILED
        is_done = status in (ExecutionStatus.COMPLETED, ExecutionStatus.CACHED)
        if is_failed or (is_done and all_synced):
            run_model.status = status
            self.update_run(run_model)

        return run_model
