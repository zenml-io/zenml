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

import os
import re
from pathlib import Path, PurePath
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
from sqlalchemy.sql.operators import is_
from sqlmodel import Session, SQLModel, create_engine, or_, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.config.global_config import GlobalConfiguration
from zenml.config.store_config import StoreConfiguration
from zenml.constants import ENV_ZENML_SERVER_DEPLOYMENT_TYPE
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.exceptions import (
    EntityExistsError,
    IllegalOperationError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.logger import get_logger
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
from zenml.zen_stores.base_zen_store import BaseZenStore
from zenml.zen_stores.schemas import (
    ArtifactSchema,
    FlavorSchema,
    PipelineRunSchema,
    PipelineSchema,
    ProjectSchema,
    RoleSchema,
    StackComponentSchema,
    StackSchema,
    StepInputArtifactSchema,
    StepRunOrderSchema,
    StepRunSchema,
    TeamAssignmentSchema,
    TeamRoleAssignmentSchema,
    TeamSchema,
    UserRoleAssignmentSchema,
    UserSchema,
)
from zenml.zen_stores.schemas.stack_schemas import StackCompositionSchema

if TYPE_CHECKING:
    from ml_metadata.proto.metadata_store_pb2 import ConnectionConfig

    from zenml.zen_stores.metadata_store import MetadataStore

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
        sqlalchemy_connect_args = {}
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

            # Handle certificate params
            for key in ["ssl_key", "ssl_ca", "ssl_cert"]:
                ssl_setting = getattr(self, key)
                if ssl_setting and os.path.isfile(ssl_setting):
                    if key == "ssl_cert":
                        sqlalchemy_connect_args["ssl_capath"] = ssl_setting
                    else:
                        sqlalchemy_connect_args[key] = ssl_setting
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
        TYPE: The type of the store.
        CONFIG_TYPE: The type of the store configuration.
        _engine: The SQLAlchemy engine.
        _metadata_store: The metadata store.
    """

    config: SqlZenStoreConfiguration
    TYPE: ClassVar[StoreType] = StoreType.SQL
    CONFIG_TYPE: ClassVar[Type[StoreConfiguration]] = SqlZenStoreConfiguration

    _engine: Optional[Engine] = None
    _metadata_store: Optional["MetadataStore"] = None

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
        SQLModel.metadata.create_all(self._engine)

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
    ) -> "ConnectionConfig":
        """Get the TFX metadata config of this ZenStore.

        Args:
            expand_certs: Whether to expand the certificate paths in the
                connection config to their value.

        Returns:
            The TFX metadata config of this ZenStore.
        """
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
        """
        with Session(self.engine) as session:
            try:
                stack = session.exec(
                    select(StackSchema).where(StackSchema.id == stack_id)
                ).one()
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
            owner_of_shared = self._get_user_schema(
                existing_shared_stack.user_id, session=session
            )

            raise StackExistsError(
                f"Unable to share stack with name '{stack.name}': Found an "
                f"existing stack with the same name in project "
                f"'{project.name}' shared by '{owner_of_shared.name}'."
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
                more stacks.
        """
        with Session(self.engine) as session:
            try:
                stack_component = session.exec(
                    select(StackComponentSchema).where(
                        StackComponentSchema.id == component_id
                    )
                ).one()
                if len(stack_component.stacks) > 0:
                    raise IllegalOperationError(
                        f"Stack Component `{stack_component.name}` of type "
                        f"`{stack_component.type} can not be "
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
            owner_of_shared = self._get_user_schema(
                existing_shared_component.user_id, session=session
            )

            raise StackComponentExistsError(
                f"Unable to shared component of type '{component.type.value}' "
                f"with name '{component.name}': Found an "
                f"existing component with the same name and type in project "
                f"'{project.name}' shared by "
                f"'{owner_of_shared.name}'."
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
                        f"`{flavor_in_db.type} can not be "
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
        """
        with Session(self.engine) as session:
            existing_user = self._get_user_schema(user.id, session=session)
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
            KeyError: If no user with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                user = self._get_user_schema(user_name_or_id, session=session)
                session.delete(user)
                session.commit()
            except NoResultFound as error:
                raise KeyError from error

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

        Raises:
            KeyError: If no user with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                user = self._get_user_schema(user_name_or_id, session=session)
            except NoResultFound as error:
                raise KeyError from error
            else:
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

        Raises:
            KeyError: If no team with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                team = self._get_team_schema(team_name_or_id, session=session)
                session.delete(team)
                session.commit()

            except NoResultFound as error:
                raise KeyError from error

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

            # Update the role
            existing_role.from_update_model(role)

            session.add(existing_role)
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
            IllegalOperationError: If the role is still assigned to users.
            KeyError: If the role does not exist.
        """
        with Session(self.engine) as session:
            try:
                role = self._get_role_schema(role_name_or_id, session=session)

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
                        f"Role `{role.name}` of type can not be "
                        f"deleted as it is in use by multiple users and teams. "
                        f"Before deleting this role make sure to remove all "
                        f"instances where this role is used."
                    )
                else:
                    # Delete role
                    session.delete(role)
                    session.commit()
            except NoResultFound as error:
                raise KeyError from error

    # ----------------
    # Role assignments
    # ----------------

    def _list_user_role_assignments(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List[RoleAssignmentModel]:
        """List all user role assignments.

        Args:
            project_name_or_id: If provided, only return role assignments for
                this project.
            user_name_or_id: If provided, only list assignments for this user.

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
            if user_name_or_id is not None:
                user = self._get_user_schema(user_name_or_id, session=session)
                query = query.where(UserRoleAssignmentSchema.user_id == user.id)
            assignments = session.exec(query).all()
            return [assignment.to_model() for assignment in assignments]

    def _list_team_role_assignments(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        team_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List[RoleAssignmentModel]:
        """List all team role assignments.

        Args:
            project_name_or_id: If provided, only return role assignments for
                this project.
            team_name_or_id: If provided, only list assignments for this team.

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
            if team_name_or_id is not None:
                team = self._get_team_schema(team_name_or_id, session=session)
                query = query.where(TeamRoleAssignmentSchema.team_id == team.id)
            assignments = session.exec(query).all()
            return [assignment.to_model() for assignment in assignments]

    def list_role_assignments(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        team_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List[RoleAssignmentModel]:
        """List all role assignments.

        Args:
            project_name_or_id: If provided, only return role assignments for
                this project.
            team_name_or_id: If provided, only list assignments for this team.
            user_name_or_id: If provided, only list assignments for this user.

        Returns:
            A list of all role assignments.
        """
        user_role_assignments = self._list_user_role_assignments(
            project_name_or_id=project_name_or_id,
            user_name_or_id=user_name_or_id,
        )
        team_role_assignments = self._list_team_role_assignments(
            project_name_or_id=project_name_or_id,
            team_name_or_id=team_name_or_id,
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
            KeyError: if the project does not exist.
        """
        with Session(self.engine) as session:
            existing_project = session.exec(
                select(ProjectSchema).where(ProjectSchema.id == project.id)
            ).first()

            if existing_project is None:
                raise KeyError(
                    f"Unable to update project with id "
                    f"'{project.id}': Found no"
                    f"existing projects with this id."
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
            KeyError: If the project does not exist.
        """
        with Session(self.engine) as session:
            try:
                # Check if project with the given name exists
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )

                session.delete(project)
                session.commit()
            except NoResultFound as error:
                raise KeyError from error

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
    # Pipeline steps
    # --------------

    def list_steps(self, pipeline_id: UUID) -> List[StepRunModel]:
        """List all steps.

        Args:
            pipeline_id: The ID of the pipeline to list steps for.
        """
        pass  # TODO

    # --------------
    # Pipeline runs
    # --------------

    def get_run(self, run_id: UUID) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        if not self.runs_inside_server:
            self._sync_runs()  # Sync with MLMD
        with Session(self.engine) as session:
            # Check if pipeline run with the given ID exists
            run = session.exec(
                select(PipelineRunSchema).where(PipelineRunSchema.id == run_id)
            ).first()
            if run is None:
                raise KeyError(
                    f"Unable to get pipeline run with ID {run_id}: "
                    f"No pipeline run with this ID found."
                )

            return run.to_model()

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
            self._sync_runs()  # Sync with MLMD
        with Session(self.engine) as session:
            query = select(PipelineRunSchema)
            if project_name_or_id is not None:
                project = self._get_project_schema(
                    project_name_or_id, session=session
                )
                query = query.where(StackSchema.project_id == project.id)
                query = query.where(
                    PipelineRunSchema.stack_id == StackSchema.id
                )
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

    def get_run_status(self, run_id: UUID) -> ExecutionStatus:
        """Gets the execution status of a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get the status for.

        Returns:
            The status of the pipeline run.
        """
        steps = self.list_run_steps(run_id)

        # If any step is failed or running, return that status respectively
        for step in steps:
            step_status = self.get_run_step_status(step.id)
            if step_status == ExecutionStatus.FAILED:
                return ExecutionStatus.FAILED
            if step_status == ExecutionStatus.RUNNING:
                return ExecutionStatus.RUNNING

        # If not all steps have started yet, return running
        if len(steps) < self.get_run(run_id).num_steps:
            return ExecutionStatus.RUNNING

        # Otherwise, return succeeded
        return ExecutionStatus.COMPLETED

    # ------------------
    # Pipeline run steps
    # ------------------

    def get_run_step(self, step_id: UUID) -> StepRunModel:
        """Get a step by ID.

        Args:
            step_id: The ID of the step to get.

        Returns:
            The step.

        Raises:
            KeyError: if the step doesn't exist.
        """
        with Session(self.engine) as session:
            step = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == step_id)
            ).first()
            if step is None:
                raise KeyError(
                    f"Unable to get step with ID {step_id}: No step with this "
                    "ID found."
                )
            parent_steps = session.exec(
                select(StepRunSchema)
                .where(StepRunOrderSchema.child_id == step.id)
                .where(StepRunOrderSchema.parent_id == StepRunSchema.id)
            ).all()
            parent_step_ids = [parent_step.id for parent_step in parent_steps]
            mlmd_parent_step_ids = [
                parent_step.mlmd_id for parent_step in parent_steps
            ]
            step_model = step.to_model(parent_step_ids, mlmd_parent_step_ids)
            return step_model

    def get_run_step_outputs(self, step_id: UUID) -> Dict[str, ArtifactModel]:
        """Get the outputs for a specific step.

        Args:
            step_id: The id of the step to get outputs for.

        Returns:
            A dict mapping artifact names to the output artifacts for the step.

        Raises:
            KeyError: if the step doesn't exist.
        """
        with Session(self.engine) as session:
            step = session.exec(
                select(StepRunSchema).where(StepRunSchema.id == step_id)
            ).first()
            if step is None:
                raise KeyError(
                    f"Unable to get output artifacts for step with ID "
                    f"{step_id}: No step with this ID found."
                )
            artifacts = session.exec(
                select(ArtifactSchema).where(
                    ArtifactSchema.parent_step_id == step_id
                )
            ).all()
            return {
                artifact.name: artifact.to_model() for artifact in artifacts
            }

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
                select(ArtifactSchema, StepInputArtifactSchema)
                .where(ArtifactSchema.id == StepInputArtifactSchema.artifact_id)
                .where(StepInputArtifactSchema.step_id == step_id)
            ).all()
            return {
                step_input_artifact.name: artifact.to_model()
                for artifact, step_input_artifact in query_result
            }

    def get_run_step_status(self, step_id: UUID) -> ExecutionStatus:
        """Gets the execution status of a single step.

        Args:
            step_id: The ID of the step to get the status for.

        Returns:
            ExecutionStatus: The status of the step.
        """
        step = self.get_run_step(step_id)
        return self.metadata_store.get_step_status(step.mlmd_id)

    def list_run_steps(self, run_id: UUID) -> List[StepRunModel]:
        """Gets all steps in a pipeline run.

        Args:
            run_id: The ID of the pipeline run for which to list runs.

        Returns:
            A mapping from step names to step models for all steps in the run.
        """
        if not self.runs_inside_server:
            self._sync_run_steps(run_id)
        with Session(self.engine) as session:
            steps = session.exec(
                select(StepRunSchema).where(
                    StepRunSchema.pipeline_run_id == run_id
                )
            ).all()
            return [self.get_run_step(step.id) for step in steps]

    def list_artifacts(
        self, artifact_uri: Optional[str] = None
    ) -> List[ArtifactModel]:
        """Lists all artifacts.

        Args:
            artifact_uri: If specified, only artifacts with the given URI will
                be returned.

        Returns:
            A list of all artifacts.
        """
        if not self.runs_inside_server:
            self._sync_runs()
        with Session(self.engine) as session:
            query = select(ArtifactSchema)
            if artifact_uri is not None:
                query = query.where(ArtifactSchema.uri == artifact_uri)
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
        # Get all runs from ZenML.
        with Session(self.engine) as session:
            zenml_runs_list = session.exec(select(PipelineRunSchema)).all()
        zenml_runs = {run.name: run.to_model() for run in zenml_runs_list}

        # Get all runs from MLMD.
        mlmd_runs = self.metadata_store.get_all_runs()

        # Sync all MLMD runs that don't exist in ZenML.
        for run_name, mlmd_run in mlmd_runs.items():

            # If the run is in MLMD but not in ZenML, we create it
            if run_name not in zenml_runs:
                new_run = PipelineRunModel(
                    name=run_name,
                    mlmd_id=mlmd_run.mlmd_id,
                    project=mlmd_run.project,
                    user=mlmd_run.user,
                    stack_id=mlmd_run.stack_id,
                    pipeline_id=mlmd_run.pipeline_id,
                    pipeline_configuration=mlmd_run.pipeline_configuration,
                    num_steps=mlmd_run.num_steps,
                )
                new_run = self._create_run(new_run)
                zenml_runs[run_name] = new_run

        for run_ in zenml_runs.values():
            self._sync_run_steps(run_.id)

    def _sync_run_steps(self, run_id: UUID) -> None:
        """Sync run steps from MLMD into the database.

        Since we do not allow to create steps in the database directly, this is
        a one-way sync from MLMD to the database.

        Args:
            run_id: The ID of the pipeline run to sync steps for.

        Raises:
            KeyError: if the run couldn't be found.
        """
        # Get all steps from ZenML.
        with Session(self.engine) as session:
            run = session.exec(
                select(PipelineRunSchema).where(PipelineRunSchema.id == run_id)
            ).first()
            if run is None:
                raise KeyError(
                    f"Unable to sync run steps for run with ID {run_id}: "
                    f"No run with this ID found."
                )
            zenml_steps_list = session.exec(
                select(StepRunSchema).where(
                    StepRunSchema.pipeline_run_id == run_id
                )
            ).all()
        zenml_steps = {
            step.name: self.get_run_step(step.id) for step in zenml_steps_list
        }

        # Get all steps from MLMD.
        mlmd_steps = self.metadata_store.get_pipeline_run_steps(run.mlmd_id)

        # For each step in MLMD, sync it into ZenML if it doesn't exist yet.
        for step_name, mlmd_step in mlmd_steps.items():
            if step_name not in zenml_steps:
                docstring = mlmd_step.step_configuration["config"]["docstring"]
                new_step = StepRunModel(
                    name=step_name,
                    mlmd_id=mlmd_step.mlmd_id,
                    mlmd_parent_step_ids=mlmd_step.mlmd_parent_step_ids,
                    entrypoint_name=mlmd_step.entrypoint_name,
                    parameters=mlmd_step.parameters,
                    step_configuration=mlmd_step.step_configuration,
                    docstring=docstring,
                    pipeline_run_id=run_id,
                    parent_step_ids=[
                        self._resolve_mlmd_step_id(parent_step_id)
                        for parent_step_id in mlmd_step.mlmd_parent_step_ids
                    ],
                )
                new_step = self._create_run_step(new_step)
                zenml_steps[step_name] = new_step

        # Save parent step IDs into the database.
        for step in zenml_steps.values():
            for parent_step_id in step.parent_step_ids:
                self._set_parent_step(
                    child_id=step.id, parent_id=parent_step_id
                )

        # Sync Artifacts.
        for step in zenml_steps.values():
            self._sync_run_step_artifacts(step.id)

    def _sync_run_step_artifacts(self, run_step_id: UUID) -> None:
        """Sync run step artifacts from MLMD into the database.

        Since we do not allow to create artifacts in the database directly, this
        is a one-way sync from MLMD to the database.

        Args:
            run_step_id: The ID of the step run to sync artifacts for.
        """
        # Get all ZenML artifacts.
        zenml_inputs = self.get_run_step_inputs(run_step_id)
        zenml_outputs = self.get_run_step_outputs(run_step_id)

        # Get all MLMD artifacts.
        step_model = self.get_run_step(run_step_id)
        mlmd_inputs, mlmd_outputs = self.metadata_store.get_step_artifacts(
            step_id=step_model.mlmd_id,
            step_parent_step_ids=step_model.mlmd_parent_step_ids,
            step_name=step_model.entrypoint_name,
        )

        # For each output in MLMD, sync it into ZenML if it doesn't exist yet.
        for output_name, mlmd_artifact in mlmd_outputs.items():
            if output_name not in zenml_outputs:
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
                self._create_run_step_artifact(new_artifact)

        # For each input in MLMD, sync it into ZenML if it doesn't exist yet.
        for input_name, mlmd_artifact in mlmd_inputs.items():
            if input_name not in zenml_inputs:
                artifact_id = self._resolve_mlmd_artifact_id(
                    mlmd_id=mlmd_artifact.mlmd_id,
                    mlmd_parent_step_id=mlmd_artifact.mlmd_parent_step_id,
                )
                self._set_run_step_input_artifact(
                    step_id=run_step_id,
                    artifact_id=artifact_id,
                    name=input_name,
                )

    def _create_run(self, pipeline_run: PipelineRunModel) -> PipelineRunModel:
        """Creates a pipeline run.

        Args:
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

        Raises:
            EntityExistsError: If an identical pipeline run already exists.
            KeyError: If the pipeline does not exist.
        """
        # TODO: fix for when creating without associating to a project
        with Session(self.engine) as session:
            # Check if pipeline run already exists
            existing_domain_run = session.exec(
                select(PipelineRunSchema).where(
                    PipelineRunSchema.name == pipeline_run.name
                )
            ).first()
            if existing_domain_run is not None:
                raise EntityExistsError(
                    f"Unable to create pipeline run {pipeline_run.name}: "
                    f"A pipeline run with this name already exists."
                )
            existing_id_run = session.exec(
                select(PipelineRunSchema).where(
                    PipelineRunSchema.id == pipeline_run.id
                )
            ).first()
            if existing_id_run is not None:
                raise EntityExistsError(
                    f"Unable to create pipeline run {pipeline_run.id}: "
                    f"A pipeline run with this id already exists."
                )

            # Query pipeline
            if pipeline_run.pipeline_id is not None:
                pipeline = session.exec(
                    select(PipelineSchema).where(
                        PipelineSchema.id == pipeline_run.pipeline_id
                    )
                ).first()
                if pipeline is None:
                    raise KeyError(
                        f"Unable to create pipeline run: {pipeline_run.name}: "
                        f"No pipeline with ID {pipeline_run.pipeline_id} found."
                    )
                new_run = PipelineRunSchema.from_create_model(
                    run=pipeline_run, pipeline=pipeline
                )
            else:
                new_run = PipelineRunSchema.from_create_model(run=pipeline_run)

            # Create the pipeline run
            session.add(new_run)
            session.commit()

            return new_run.to_model()

    def _update_run(self, run: PipelineRunModel) -> PipelineRunModel:
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

    def _create_run_step(self, step: StepRunModel) -> StepRunModel:
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
            existing_step = session.exec(
                select(StepRunSchema).where(
                    StepRunSchema.mlmd_id == step.mlmd_id
                )
            ).first()
            if existing_step is not None:
                raise EntityExistsError(
                    f"Unable to create step '{step.name}': A step with MLMD ID "
                    f"'{step.mlmd_id}' already exists."
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

            assert step.parent_step_ids is not None
            return step_schema.to_model(
                parent_step_ids=step.parent_step_ids,
                mlmd_parent_step_ids=step.mlmd_parent_step_ids,
            )

    def _set_parent_step(self, child_id: UUID, parent_id: UUID) -> None:
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
                select(StepRunOrderSchema)
                .where(StepRunOrderSchema.child_id == child_id)
                .where(StepRunOrderSchema.parent_id == parent_id)
            ).first()
            if assignment is not None:
                return

            # Save the parent step assignment in the database.
            assignment = StepRunOrderSchema(
                child_id=child_id, parent_id=parent_id
            )
            session.add(assignment)
            session.commit()

    def _create_run_step_artifact(
        self, artifact: ArtifactModel
    ) -> ArtifactModel:
        """Creates an artifact of a step.

        Args:
            artifact: The artifact to create.

        Returns:
            The created artifact.

        Raises:
            KeyError: if the step doesn't exist.
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

            # Create the artifact
            artifact_schema = ArtifactSchema.from_create_model(artifact)
            session.add(artifact_schema)
            session.commit()
            return artifact_schema.to_model()

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

            # Save the input artifact assignment in the database.
            step_input = StepInputArtifactSchema(
                step_id=step_id,
                artifact_id=artifact_id,
                name=name,
            )
            session.add(step_input)
            session.commit()
