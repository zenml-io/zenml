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
from pathlib import Path, PurePath
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union, cast
from uuid import UUID

from sqlalchemy import or_
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError, NoResultFound
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.config.store_config import StoreConfiguration
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.exceptions import (
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata_stores.sqlite_metadata_store import SQLiteMetadataStore
from zenml.models import (
    ComponentModel,
    FlavorModel,
    PipelineRunModel,
    ProjectModel,
    RoleAssignmentModel,
    RoleModel,
    StackModel,
    TeamModel,
    UserModel,
)
from zenml.models.code_models import CodeRepositoryModel
from zenml.models.pipeline_models import (
    ArtifactModel,
    PipelineModel,
    StepRunModel,
)
from zenml.utils import io_utils, uuid_utils
from zenml.utils.analytics_utils import AnalyticsEvent, track
from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME, BaseZenStore
from zenml.zen_stores.schemas import (
    CodeRepositorySchema,
    FlavorSchema,
    PipelineRunSchema,
    PipelineSchema,
    ProjectSchema,
    RoleSchema,
    StackComponentSchema,
    StackSchema,
    TeamAssignmentSchema,
    TeamRoleAssignmentSchema,
    TeamSchema,
    UserRoleAssignmentSchema,
    UserSchema,
)

# Enable SQL compilation caching to remove the https://sqlalche.me/e/14/cprf
# warning
SelectOfScalar.inherit_cache = True
Select.inherit_cache = True

logger = get_logger(__name__)

ZENML_SQLITE_DB_FILENAME = "zenml.db"


class SqlZenStoreConfiguration(StoreConfiguration):
    """SQL ZenML store configuration.

    Attributes:
        _sql_kwargs: Additional keyword arguments to pass to the SQLAlchemy
            engine.
    """

    type: StoreType = StoreType.SQL
    _sql_kwargs: Dict[str, Any] = {}

    def __init__(self, **kwargs: Any) -> None:
        """Initializes the SQL ZenML store configuration.

        The constructor collects all extra fields into a private _sql_kwargs
        attribute.

        Args:
            **kwargs: Keyword arguments to pass to the Pydantic constructor.
        """
        # Create a list of fields that are in the Pydantic schema
        field_names = {
            field.alias
            for field in self.__fields__.values()
            if field.alias != "_sql_kwargs"
        }

        sql_kwargs: Dict[str, Any] = {}
        for field_name in list(kwargs):
            if field_name not in field_names:
                # Remove fields that are not in the Pydantic schema and add them
                # to the sql_kwargs dict
                sql_kwargs[field_name] = kwargs.get(field_name)
        super().__init__(**kwargs)
        self._sql_kwargs = sql_kwargs


class SqlZenStore(BaseZenStore):
    """Store Implementation that uses SQL database backend."""

    config: SqlZenStoreConfiguration
    TYPE: ClassVar[StoreType] = StoreType.SQL
    CONFIG_TYPE: ClassVar[Type[StoreConfiguration]] = SqlZenStoreConfiguration

    _engine: Optional[Engine] = None
    _metadata_store: Optional[SQLiteMetadataStore] = None

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
    def metadata_store(self) -> SQLiteMetadataStore:
        """The metadata store.

        Returns:
            The metadata store.

        Raises:
            ValueError: If the store is not initialized.
        """
        if not self._metadata_store:
            raise ValueError("Store not initialized")
        return self._metadata_store

    # ====================================
    # ZenML Store interface implementation
    # ====================================

    # --------------------------------
    # Initialization and configuration
    # --------------------------------

    def _initialize(self) -> None:
        """Initialize the SQL store."""
        logger.debug("Initializing SqlZenStore at %s", self.config.url)

        local_path = self.get_path_from_url(self.config.url)
        if local_path:
            io_utils.create_dir_recursive_if_not_exists(str(local_path.parent))

        metadata_store_path = os.path.join(
            os.path.dirname(str(local_path)), "metadata.db"
        )
        self._metadata_store = SQLiteMetadataStore(uri=metadata_store_path)

        self._engine = create_engine(self.config.url, **self.config._sql_kwargs)
        SQLModel.metadata.create_all(self._engine)

    @staticmethod
    def get_path_from_url(url: str) -> Optional[Path]:
        """Get the local path from a URL, if it points to a local sqlite file.

        This method first checks that the URL is a valid SQLite URL, which is
        backed by a file in the local filesystem. All other types of supported
        SQLAlchemy connection URLs are considered non-local and won't return
        a valid local path.

        Args:
            url: The URL to get the path from.

        Returns:
            The path extracted from the URL, or None, if the URL does not
            point to a local sqlite file.
        """
        url = SqlZenStore.validate_url(url)
        if not url.startswith("sqlite:///"):
            return None
        url = url.replace("sqlite:///", "")
        return Path(url)

    @staticmethod
    def get_local_url(path: str) -> str:
        """Get a local SQL url for a given local path.

        Args:
            path: The path to the local sqlite file.

        Returns:
            The local SQL url for the given path.
        """
        return f"sqlite:///{path}/{ZENML_SQLITE_DB_FILENAME}"

    @staticmethod
    def validate_url(url: str) -> str:
        """Check if the given url is valid.

        Args:
            url: The url to check.

        Returns:
            The validated url.

        Raises:
            ValueError: If the url is not valid.
        """
        try:
            make_url(url)
        except ArgumentError as e:
            raise ValueError(
                "Invalid SQLAlchemy URL `%s`: %s. Check the SQLAlchemy "
                "documentation at https://docs.sqlalchemy.org/en/14/core/engines.html#database-urls "
                "for the correct format.",
                url,
                str(e),
            )
        return url

    @classmethod
    def copy_local_store(
        cls,
        config: StoreConfiguration,
        path: str,
        load_config_path: Optional[PurePath] = None,
    ) -> StoreConfiguration:
        """Copy a local store to a new location.

        Use this method to create a copy of a store database to a new location
        and return a new store configuration pointing to the database copy. This
        only applies to stores that use the local filesystem to store their
        data. Calling this method for remote stores simply returns the input
        store configuration unaltered.

        Args:
            config: The configuration of the store to copy.
            path: The new local path where the store DB will be copied.
            load_config_path: path that will be used to load the copied store
                database. This can be set to a value different from `path`
                if the local database copy will be loaded from a different
                environment, e.g. when the database is copied to a container
                image and loaded using a different absolute path. This will be
                reflected in the paths and URLs encoded in the copied store
                configuration.

        Returns:
            The store configuration of the copied store.
        """
        config_copy = config.copy()

        local_path = cls.get_path_from_url(config.url)
        if not local_path:
            # this is not a configuration backed by a local filesystem
            return config_copy
        io_utils.create_dir_recursive_if_not_exists(path)
        fileio.copy(
            str(local_path), str(Path(path) / local_path.name), overwrite=True
        )
        if load_config_path:
            config_copy.url = cls.get_local_url(str(load_config_path))
        else:
            config_copy.url = cls.get_local_url(path)

        return config_copy

    # ------------
    # TFX Metadata
    # ------------

    def get_metadata_config(self) -> str:
        """Get the TFX metadata config of this ZenStore.

        Returns:
            The TFX metadata config of this ZenStore.
        """
        from google.protobuf.json_format import MessageToJson

        config = self.metadata_store.get_tfx_metadata_config()
        return MessageToJson(config)

    # ------
    # Stacks
    # ------

    @track(AnalyticsEvent.REGISTERED_STACK)
    def register_stack(
        self,
        user_name_or_id: Union[str, UUID],
        project_name_or_id: Union[str, UUID],
        stack: StackModel,
    ) -> StackModel:
        """Register a new stack.

        Args:
            user_name_or_id: The stack owner.
            project_name_or_id: The project that the stack belongs to.
            stack: The stack to register.

        Returns:
            The registered stack.

        Raises:
            StackExistsError: If a stack with the same name is already owned
                by this user in this project.
        """
        with Session(self.engine) as session:
            project = self._get_project_schema(project_name_or_id)
            user = self._get_user_schema(user_name_or_id)
            # Check if stack with the domain key (name, project, owner) already
            #  exists
            existing_stack = session.exec(
                select(StackSchema)
                .where(StackSchema.name == stack.name)
                .where(StackSchema.project_id == project.id)
                .where(StackSchema.owner == user.id)
            ).first()
            # TODO: verify if is_shared status needs to be checked here
            if existing_stack is not None:
                raise StackExistsError(
                    f"Unable to register stack with name "
                    f"'{stack.name}': Found an existing stack with the same "
                    f"name in the same '{project.name}' project owned by the "
                    f"same '{user.name}' user."
                )

            # Get the Schemas of all components mentioned
            filters = [
                (StackComponentSchema.id == c.id)
                for c in stack.components.values()
            ]

            defined_components = session.exec(
                select(StackComponentSchema).where(or_(*filters))
            ).all()

            # Create the stack
            stack_in_db = StackSchema.from_create_model(
                project_id=project.id,
                user_id=user.id,
                defined_components=defined_components,
                stack=stack,
            )
            session.add(stack_in_db)
            session.commit()

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
        project_name_or_id: Union[str, UUID],
        user_name_or_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[StackModel]:
        """List all stacks matching the given filter criteria.

        Args:
            project_name_or_id: Id or name of the Project containing the stack
            user_name_or_id: Optionally filter stacks by their owner
            name: Optionally filter stacks by their name
            is_shared: Optionally filter out stacks by whether they are shared
                or not


        Returns:
            A list of all stacks matching the filter criteria.

        Raises:
            KeyError: if the project doesn't exist.
        """
        with Session(self.engine) as session:
            project = self._get_project_schema(project_name_or_id)

            # Get a list of all stacks
            query = select(StackSchema).where(
                StackSchema.project_id == project.id
            )
            # TODO: prettify
            if user_name_or_id:
                user = self._get_user_schema(user_name_or_id)
                query = query.where(StackSchema.owner == user.id)
            if name:
                query = query.where(StackSchema.name == name)
            if is_shared is not None:
                query = query.where(StackSchema.is_shared == is_shared)
            stacks = session.exec(query).all()

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

            # Get the Schemas of all components mentioned
            filters = [
                (StackComponentSchema.id == c.id)
                for c in stack.components.values()
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

    # ----------------
    # Stack components
    # ----------------

    @track(AnalyticsEvent.REGISTERED_STACK_COMPONENT)
    def register_stack_component(
        self,
        user_name_or_id: Union[UUID, str],
        project_name_or_id: Union[str, UUID],
        component: ComponentModel,
    ) -> ComponentModel:
        """Create a stack component.

        Args:
            user_name_or_id: The stack component owner.
            project_name_or_id: The project the stack component is created in.
            component: The stack component to create.

        Returns:
            The created stack component.

        Raises:
            StackComponentExistsError: If a stack component with the same name
                and type is already owned by this user in this project.
        """
        with Session(self.engine) as session:
            project = self._get_project_schema(project_name_or_id)
            user = self._get_user_schema(user_name_or_id)

            # Check if component with the same domain key (name, type, project,
            # owner) already exists
            existing_component = session.exec(
                select(StackComponentSchema)
                .where(StackComponentSchema.name == component.name)
                .where(StackComponentSchema.project_id == project.id)
                .where(StackComponentSchema.owner == user.id)
                .where(StackComponentSchema.type == component.type)
            ).first()

            if existing_component is not None:
                raise StackComponentExistsError(
                    f"Unable to register '{component.type.value}' component "
                    f"with name '{component.name}': Found an existing "
                    f"component with the same name and type in the same "
                    f"'{project.name}' project owned by the same "
                    f"'{user.name}' user."
                )

            # Create the component
            component_in_db = StackComponentSchema.from_create_model(
                user_id=user.id, project_id=project.id, component=component
            )

            session.add(component_in_db)
            session.commit()

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
        project_name_or_id: Union[str, UUID],
        type: Optional[str] = None,
        flavor_name: Optional[str] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[ComponentModel]:
        """List all stack components matching the given filter criteria.

        Args:
            project_name_or_id: The ID or name of the Project to which the stack
                components belong
            type: Optionally filter by type of stack component
            flavor_name: Optionally filter by flavor
            user_name_or_id: Optionally filter stack components by the owner
            name: Optionally filter stack component by name
            is_shared: Optionally filter out stack component by whether they are
                shared or not

        Returns:
            A list of all stack components matching the filter criteria.

        Raises:
            KeyError: if the project doesn't exist.
        """
        with Session(self.engine) as session:
            project = self._get_project_schema(project_name_or_id)

            # Get a list of all stacks
            query = select(StackComponentSchema).where(
                StackComponentSchema.project_id == project.id
            )
            # TODO: [server] prettify this
            if type:
                query = query.where(StackComponentSchema.type == type)
            if flavor_name:
                query = query.where(
                    StackComponentSchema.flavor_name == flavor_name
                )
            if user_name_or_id:
                user = self._get_user_schema(user_name_or_id)
                query = query.where(StackComponentSchema.owner == user.id)
            if name:
                query = query.where(StackComponentSchema.name == name)
            if is_shared is not None:
                query = query.where(StackComponentSchema.is_shared == is_shared)

            list_of_stack_components_in_db = session.exec(query).all()

        return [comp.to_model() for comp in list_of_stack_components_in_db]

    @track(AnalyticsEvent.UPDATED_STACK_COMPONENT)
    def update_stack_component(
        self, component_id: UUID, component: ComponentModel
    ) -> ComponentModel:
        """Update an existing stack component.

        Args:
            component: The stack component to use for the update.

        Returns:
            The updated stack component.

        Raises:
            KeyError: if the stack component doesn't exist.
        """
        with Session(self.engine) as session:
            existing_component = session.exec(
                select(StackComponentSchema).where(
                    StackComponentSchema.id == component_id
                )
            ).first()

            # TODO: verify if is_shared status needs to be checked here
            if existing_component is None:
                raise KeyError(
                    f"Unable to update component with id "
                    f"'{component.id}': Found no"
                    f"existing component with this id."
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
        """
        with Session(self.engine) as session:
            try:
                stack_component = session.exec(
                    select(StackComponentSchema).where(
                        StackComponentSchema.id == component_id
                    )
                ).one()
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
        # TODO: implement this
        raise NotImplementedError

    # -----------------------
    # Stack component flavors
    # -----------------------

    @track(AnalyticsEvent.CREATED_FLAVOR)
    def create_flavor(
        self,
        user_name_or_id: Union[str, UUID],
        project_name_or_id: Union[str, UUID],
        flavor: FlavorModel,
    ) -> FlavorModel:
        """Creates a new stack component flavor.

        Args:
            user_name_or_id: The stack component flavor owner.
            project_name_or_id: The project in which the stack component flavor
                is created.
            flavor: The stack component flavor to create.

        Returns:
            The newly created flavor.

        Raises:
            EntityExistsError: If a flavor with the same name and type
                is already owned by this user in this project.
        """
        with Session(self.engine) as session:
            # TODO [Baris]: handle the domain key (name+type+owner+project) correctly
            existing_flavor = session.exec(
                select(FlavorSchema).where(
                    FlavorSchema.name == flavor.name,
                    FlavorSchema.type == flavor.type,
                )
            ).first()
            if existing_flavor:
                raise EntityExistsError(
                    f"A {flavor.type} with '{flavor.name}' flavor already "
                    f"exists."
                )
            # TODO: add logic to convert from model in schema
            sql_flavor = FlavorSchema(
                name=flavor.name,
                source=flavor.source,
                type=flavor.type,
            )
            flavor_model = FlavorModel(**sql_flavor.dict())
            session.add(sql_flavor)
            session.commit()

        # with Session(self.engine) as session:
        #     flavor_in_db = FlavorSchema.from_create_model(
        #         user_id=user_id, project_id=project_id, flavor=flavor
        #     )
        #     session.add(flavor_in_db)
        #     session.commit()
        #
        # return flavor_in_db.to_model()
        return flavor_model

    def get_flavor(self, flavor_id: UUID) -> FlavorModel:
        """Get a stack component flavor by ID.

        Args:
            component_id: The ID of the stack component flavor to get.

        Returns:
            The stack component flavor.

        Raises:
            KeyError: if the stack component flavor doesn't exist.
        """
        # TODO[Baris]: implement this

        # with Session(self.engine) as session:
        #     flavor_in_db = session.exec(
        #         select(FlavorSchema).where(FlavorSchema.id == flavor_id)
        #     ).first()
        #
        # return flavor_in_db.to_model()

    def list_flavors(
        self,
        project_name_or_id: Union[str, UUID],
        component_type: Optional[StackComponentType] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[FlavorModel]:
        """List all stack component flavors matching the given filter criteria.

        Args:
            project_name_or_id: The ID or name of the Project to which the
                component flavors belong
            component_type: Optionally filter by type of stack component
            flavor_name: Optionally filter by flavor name
            user_name_or_id: Optionally filter by the owner
            name: Optionally filter flavors by name
            is_shared: Optionally filter out flavors by whether they are
                shared or not

        Returns:
            List of all the stack component flavors matching the given criteria.

        Raises:
            KeyError: if the project doesn't exist.
        """
        with Session(self.engine) as session:
            self._get_project_schema(project_name_or_id)

            # TODO [Baris]: implement filtering by component type, name, project etc.

            # Get a list of all flavors
            query = select(
                FlavorSchema
            )  # .where(FlavorSchema.project_id == project.id)
            if component_type:
                query = query.where(FlavorSchema.type == component_type)
            if name:
                query = query.where(FlavorSchema.name == name)

            # TODO: implement this
            # if user_name_or_id:
            #     user = self._get_user_schema(user_name_or_id)
            #     query = query.where(FlavorSchema.owner == user.id)
            # if name:
            #     query = query.where(FlavorSchema.name == name)
            # if is_shared is not None:
            #     query = query.where(FlavorSchema.is_shared == is_shared)

            list_of_flavors_in_db = session.exec(query).all()

        # TODO: add logic to convert to model in schema
        # return [flavor.to_model() for flavor in list_of_flavors_in_db]

        # BARIS CODE
        # with Session(self.engine) as session:
        #
        #     query = select(FlavorSchema).where(
        #         FlavorSchema.project_id == project_id
        #     )
        #
        #     if type:
        #         query = query.where(FlavorSchema.type == type)
        #     if name:
        #         query = query.where(FlavorSchema.name == name)
        #     if user_id:
        #         query = query.where(FlavorSchema.user_id == user_id)
        #
        #     list_of_flavors_in_db = session.exec(query).all()
        #
        # return [flavor.to_model() for flavor in list_of_flavors_in_db]
        return [
            FlavorModel(**flavor.dict()) for flavor in list_of_flavors_in_db
        ]

    def update_flavor(self, flavor: FlavorModel) -> None:
        """"""
        # with Session(self.engine) as session:
        #     existing_flavor = session.exec(
        #         select(FlavorSchema).where(FlavorSchema.id == flavor.id)
        #     ).first()
        #     existing_flavor.from_update_model(flavor=flavor)
        #     session.add(existing_flavor)
        #     session.commit()
        #
        # return existing_flavor.to_model()

    def delete_flavor(self, flavor_id: UUID) -> None:
        """"""
        # with Session(self.engine) as session:
        #     try:
        #         flavor_in_db = session.exec(
        #             select(FlavorSchema).where(FlavorSchema.id == flavor_id)
        #         ).one()
        #         session.delete(flavor_in_db)
        #     except NoResultFound as error:
        #         raise KeyError from error
        #
        #     session.commit()

    # -----
    # Users
    # -----

    @property
    def active_user_name(self) -> str:
        """Gets the active username.

        Returns:
            The active username.
        """
        return DEFAULT_USERNAME

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

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

            return new_user.to_model()

    def get_user(self, user_name_or_id: Union[str, UUID]) -> UserModel:
        """Gets a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name or ID exists.
        """
        user = self._get_user_schema(user_name_or_id)
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
    def update_user(
        self, user_name_or_id: Union[str, UUID], user: UserModel
    ) -> UserModel:
        """Updates an existing user.

        Args:
            user_name_or_id: The name or ID of the user to update.
            user: The User model to use for the update.

        Returns:
            The updated user.

        Raises:
            KeyError: If no user with the given name exists.
        """
        with Session(self.engine) as session:
            existing_user = self._get_user_schema(user_name_or_id)
            existing_user.from_update_model(user)
            session.add(existing_user)
            session.commit()
            return existing_user.to_model()

    @track(AnalyticsEvent.DELETED_USER)
    def delete_user(self, user_name_or_id: Union[str, UUID]) -> None:
        """Deletes a user.

        Args:
            user_id: The ID of the user to delete.

        Raises:
            KeyError: If no user with the given name exists.
        """
        with Session(self.engine) as session:
            user = self._get_user_schema(user_name_or_id)
            session.delete(user)
            session.commit()

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

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

            return new_team.to_model()

    def get_team(self, team_name_or_id: Union[str, UUID]) -> TeamModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name or ID exists.
        """
        team = self._get_team_schema(team_name_or_id)
        return team.to_model()

    def list_teams(self) -> List[TeamModel]:
        """List all teams.

        Returns:
            A list of all teams.
        """
        with Session(self.engine) as session:
            teams = session.exec(select(TeamSchema)).all()
            return [team.to_model() for team in teams]

    @track(AnalyticsEvent.DELETED_TEAM)
    def delete_team(self, team_name_or_id: Union[str, UUID]) -> None:
        """Deletes a team.

        Args:
            team_name_or_id: Name or ID of the team to delete.

        Raises:
            KeyError: If no team with the given ID exists.
        """
        with Session(self.engine) as session:
            team = self._get_team_schema(team_name_or_id)
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

        Raises:
            KeyError: If no team with the given ID exists.
        """
        team = self._get_team_schema(team_name_or_id)
        return [user.to_model() for user in team.users]

    def get_teams_for_user(
        self, user_name_or_id: Union[str, UUID]
    ) -> List[TeamModel]:
        """Fetches all teams for a user.

        Args:
            user_name_or_id: The name or ID of the user for which to get all teams.

        Returns:
            A list of all teams that the user is part of.

        Raises:
            KeyError: If no user with the given ID exists.
        """
        user = self._get_user_schema(user_name_or_id)
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
            KeyError: If the team or user does not exist.
            EntityExistsError: If the user is already a member of the team.
        """
        with Session(self.engine) as session:
            team = self._get_team_schema(team_name_or_id)
            user = self._get_user_schema(user_name_or_id)

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
            team_name_or_id: Name or ID of the team from which to remove the user.

        Raises:
            KeyError: If the team or user does not exist.
        """
        with Session(self.engine) as session:
            team = self._get_team_schema(team_name_or_id)
            user = self._get_user_schema(user_name_or_id)

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

        Raises:
            KeyError: If no role with the given name exists.
        """
        role = self._get_role_schema(role_name_or_id)
        return role.to_model()

    def list_roles(self) -> List[RoleModel]:
        """List all roles.

        Returns:
            A list of all roles.
        """
        with Session(self.engine) as session:
            roles = session.exec(select(RoleSchema)).all()

        return [role.to_model() for role in roles]

    @track(AnalyticsEvent.DELETED_ROLE)
    def delete_role(self, role_name_or_id: Union[str, UUID]) -> None:
        """Deletes a role.

        Args:
            role_name_or_id: Name or ID of the role to delete.

        Raises:
            KeyError: If no role with the given ID exists.
        """
        with Session(self.engine) as session:
            role = self._get_role_schema(role_name_or_id)

            # Delete role
            session.delete(role)
            session.commit()

    # ----------------
    # Role assignments
    # ----------------

    def list_role_assignments(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        team_name_or_id: Optional[Union[str, UUID]] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List[RoleAssignmentModel]:
        """List all role assignments.

        Args:
            project_name_or_id: Name or Id of the Project for the role
                                assignment
            team_name_or_id: If provided, only list assignments for the given team
            user_name_or_id: If provided, only list assignments for the given user

        Returns:
            A list of all role assignments.
        """
        with Session(self.engine) as session:
            # Get user role assignments
            query = select(UserRoleAssignmentSchema)

            if project_name_or_id is not None:
                project = self._get_project_schema(project_name_or_id)
                query = query.where(
                    UserRoleAssignmentSchema.project_id == project.id
                )
            if user_name_or_id is not None:
                user = self._get_user_schema(user_name_or_id)
                query = query.where(UserRoleAssignmentSchema.user_id == user.id)
            user_role_assignments = session.exec(query).all()

            # Get team role assignments
            query = select(TeamRoleAssignmentSchema)
            if project_name_or_id is not None:
                project = self._get_project_schema(project_name_or_id)
                query = query.where(
                    TeamRoleAssignmentSchema.project_id == project.id
                )
            if team_name_or_id is not None:
                team = self._get_team_schema(team_name_or_id)
                query = query.where(TeamRoleAssignmentSchema.team_id == team.id)
            team_role_assignments = session.exec(query).all()

        return [
            role_assignment.to_model()
            for role_assignment in user_role_assignments + team_role_assignments
        ]

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

        Raises:
            EntityExistsError: If the role assignment already exists.
        """
        # TODO: Check if the role assignment already exists + raise error
        with Session(self.engine) as session:
            role = self._get_role_schema(role_name_or_id)
            project: Optional[ProjectSchema] = None
            if project_name_or_id:
                project = self._get_project_schema(project_name_or_id)

            role_assignment: SQLModel

            # Assign role to user
            if is_user:
                user = self._get_user_schema(user_or_team_name_or_id)

                # Check if role assignment already exists
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

            # Assign role to team
            else:
                team = self._get_team_schema(user_or_team_name_or_id)

                # Check if role assignment already exists
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
                project = self._get_project_schema(project_name_or_id)

            role = self._get_role_schema(role_name_or_id)

            role_assignment: Optional[SQLModel] = None

            if is_user:
                user = self._get_user_schema(user_or_team_name_or_id)
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
                team = self._get_team_schema(user_or_team_name_or_id)
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

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

            return new_project.to_model()

    def get_project(self, project_name_or_id: Union[str, UUID]) -> ProjectModel:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.

        Returns:
            The requested project if one was found.

        Raises:
            KeyError: If there is no such project.
        """
        project = self._get_project_schema(project_name_or_id)
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
    def update_project(
        self, project_name_or_id: Union[str, UUID], project: ProjectModel
    ) -> ProjectModel:
        """Update an existing project.

        Args:
            project_name_or_id: Name or ID of the project to update.
            project: The project to use for the update.

        Returns:
            The updated project.

        Raises:
            KeyError: if the project does not exist.
        """
        with Session(self.engine) as session:
            # Check if project with the given name already exists
            existing_project = self._get_project_schema(project_name_or_id)

            # Update the project
            existing_project.from_update_model(project)
            # other fields are not updatable
            session.add(existing_project)
            session.commit()

            return existing_project.to_model()

    @track(AnalyticsEvent.DELETED_PROJECT)
    def delete_project(self, project_name_or_id: Union[str, UUID]) -> None:
        """Deletes a project.

        Args:
            project_name_or_id: Name or ID of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """
        with Session(self.engine) as session:
            # Check if project with the given name exists
            project = self._get_project_schema(project_name_or_id)

            session.delete(project)  # TODO: cascade delete
            session.commit()

    # ------------
    # Repositories
    # ------------

    # TODO: create repos?

    @track(AnalyticsEvent.CONNECT_REPOSITORY)
    def connect_project_repository(
        self,
        project_name_or_id: Union[str, UUID],
        repository: CodeRepositoryModel,
    ) -> CodeRepositoryModel:
        """Connects a repository to a project.

        Args:
            project_name_or_id: Name or ID of the project to connect the
                repository to.
            repository: The repository to connect.

        Returns:
            The connected repository.

        Raises:
            KeyError: if the project or repository doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if project with the given name already exists
            project = self._get_project_schema(project_name_or_id)

            # Check if repository with the given name already exists
            existing_repository = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.id == repository.id
                )
            ).first()
            if existing_repository is None:
                raise KeyError(
                    f"Unable to connect repository with ID {repository.id} to "
                    f"project '{project.name}': No repository with this ID found."
                )

            # Connect the repository to the project
            existing_repository.project_id = project.id
            session.add(existing_repository)
            session.commit()

            return existing_repository.to_model()

    def get_repository(self, repository_id: UUID) -> CodeRepositoryModel:
        """Get a repository by ID.

        Args:
            repository_id: The ID of the repository to get.

        Returns:
            The repository.

        Raises:
            KeyError: if the repository doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if repository with the given ID exists
            existing_repository = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.id == repository_id
                )
            ).first()
            if existing_repository is None:
                raise KeyError(
                    f"Unable to get repository with ID {repository_id}: "
                    "No repository with this ID found."
                )

            return existing_repository.to_model()

    def list_repositories(
        self, project_name_or_id: Union[str, UUID]
    ) -> List[CodeRepositoryModel]:
        """Get all repositories in the project.

        Args:
            project_name_or_id: The name or ID of the project.

        Returns:
            A list of all repositories in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if project with the given name already exists
            project = self._get_project_schema(project_name_or_id)

            # Get all repositories in the project
            repositories = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.project_id == project.id
                )
            ).all()

        return [repository.to_model() for repository in repositories]

    @track(AnalyticsEvent.UPDATE_REPOSITORY)
    def update_repository(
        self, repository_id: UUID, repository: CodeRepositoryModel
    ) -> CodeRepositoryModel:
        """Update a repository.

        Args:
            repository_id: The ID of the repository to update.
            repository: The repository to use for the update.

        Returns:
            The updated repository.

        Raises:
            KeyError: if the repository doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if repository with the given ID exists
            existing_repository = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.id == repository_id
                )
            ).first()
            if existing_repository is None:
                raise KeyError(
                    f"Unable to update repository with ID {repository_id}: "
                    "No repository with this ID found."
                )

            # Update the repository
            existing_repository.from_update_model(repository)
            session.add(existing_repository)
            session.commit()

            return existing_repository.to_model()

    @track(AnalyticsEvent.DELETE_REPOSITORY)
    def delete_repository(self, repository_id: UUID) -> None:
        """Delete a repository.

        Args:
            repository_id: The ID of the repository to delete.

        Raises:
            KeyError: if the repository doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if repository with the given ID exists
            existing_repository = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.id == repository_id
                )
            ).first()
            if existing_repository is None:
                raise KeyError(
                    f"Unable to delete repository with ID {repository_id}: "
                    "No repository with this ID found."
                )

            session.delete(existing_repository)  # TODO: handle dependencies
            session.commit()

    # ---------
    # Pipelines
    # ---------

    @track(AnalyticsEvent.CREATE_PIPELINE)
    def create_pipeline(
        self, project_name_or_id: Union[str, UUID], pipeline: PipelineModel
    ) -> PipelineModel:
        """Creates a new pipeline in a project.

        Args:
            project_name_or_id: ID or name of the project to create the pipeline
                in.
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            KeyError: if the project does not exist.
            EntityExistsError: If an identical pipeline already exists.
        """
        with Session(self.engine) as session:
            # Check if project with the given name exists
            project = self._get_project_schema(project_name_or_id)

            # Check if pipeline with the given name already exists
            existing_pipeline = session.exec(
                select(PipelineSchema)
                .where(PipelineSchema.name == pipeline.name)
                .where(PipelineSchema.project_id == project.id)
            ).first()
            if existing_pipeline is not None:
                raise EntityExistsError(
                    f"Unable to create pipeline in project '{project.name}': "
                    f"A pipeline with this name already exists."
                )

            # Create the pipeline
            new_pipeline = PipelineSchema.from_create_model(pipeline)
            session.add(new_pipeline)
            session.commit()

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

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

    def get_pipeline_in_project(
        self,
        pipeline_name: str,
        project_name_or_id: Union[str, UUID],
    ) -> PipelineModel:
        """Get a pipeline with a given name in a project.

        Args:
            pipeline_name: Name of the pipeline.
            project_name_or_id: ID or name of the project.

        Returns:
            The pipeline.

        Raises:
            KeyError: if the pipeline does not exist.
        """
        with Session(self.engine) as session:
            project = self._get_project_schema(project_name_or_id)
            # Check if pipeline with the given name exists in the project
            pipeline = session.exec(
                select(PipelineSchema).where(
                    PipelineSchema.name == pipeline_name,
                    PipelineSchema.project_id == project.id,
                )
            ).first()
            if pipeline is None:
                raise KeyError(
                    f"Unable to get pipeline '{pipeline_name}' in project "
                    f"'{project.name}': No pipeline with this name found."
                )
            return pipeline.to_model()

    def list_pipelines(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
    ) -> List[PipelineModel]:
        """List all pipelines in the project.

        Args:
            project_name_or_id: If provided, only list pipelines in this
                project.

        Returns:
            A list of pipelines.

        Raises:
            KeyError: if the project does not exist.
        """
        with Session(self.engine) as session:
            # Check if project with the given name exists
            query = select(PipelineSchema)
            if project_name_or_id is not None:
                project = self._get_project_schema(project_name_or_id)
                query = query.where(PipelineSchema.project_id == project.id)

            # Get all pipelines in the project
            pipelines = session.exec(query).all()
            return [pipeline.to_model() for pipeline in pipelines]

    @track(AnalyticsEvent.UPDATE_PIPELINE)
    def update_pipeline(
        self, pipeline_id: UUID, pipeline: PipelineModel
    ) -> PipelineModel:
        """Updates a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to update.
            pipeline: The pipeline to use for the update.

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

        Returns:
            A list of all steps.
        """
        pass  # TODO

    # --------------
    # Pipeline runs
    # --------------

    def _sync_runs(self) -> None:
        """Sync runs from the database with those registered in MLMD."""
        with Session(self.engine) as session:
            runs = session.exec(select(PipelineRunSchema)).all()
        zenml_runs = {run.name: run.to_model() for run in runs}
        mlmd_runs = self.metadata_store.get_all_runs()
        for run_name, mlmd_id in mlmd_runs.items():

            # If the run is in MLMD but not in ZenML, we create it
            if run_name not in zenml_runs:
                new_run = PipelineRunModel(name=run_name, mlmd_id=mlmd_id)
                self.create_run(new_run)
                continue

            # If an existing run had no MLMD ID, we update it
            existing_run = zenml_runs[run_name]
            if not existing_run.mlmd_id and existing_run.id is not None:
                existing_run.mlmd_id = mlmd_id
                self.update_run(run_id=existing_run.id, run=existing_run)

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
            # Check if pipeline run already exists
            existing_run = session.exec(
                select(PipelineRunSchema).where(
                    PipelineRunSchema.name == pipeline_run.name
                )
            ).first()
            if existing_run is not None:
                raise EntityExistsError(
                    f"Unable to create pipeline run {pipeline_run.name}: "
                    f"A pipeline run with this name already exists."
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
                    model=pipeline_run, pipeline=pipeline
                )
            else:
                new_run = PipelineRunSchema.from_create_model(pipeline_run)

            # Create the pipeline run
            session.add(new_run)
            session.commit()

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

            return new_run.to_model()

    def get_run(self, run_id: UUID) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
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

    def get_run_in_project(
        self,
        run_name: str,
        project_name_or_id: Union[str, UUID],
    ) -> PipelineRunModel:
        """Get a pipeline run with a given name in a project.

        Args:
            run_name: Name of the pipeline run.
            project_name_or_id: Name or ID of the project.

        Returns:
            The pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        self._sync_runs()  # Sync with MLMD
        with Session(self.engine) as session:
            project = self._get_project_schema(project_name_or_id)
            # Check if pipeline run with the given name exists in the project
            run = session.exec(
                select(PipelineRunSchema)
                .where(PipelineRunSchema.name == run_name)
                .where(PipelineRunSchema.stack_id == StackSchema.id)
                .where(StackSchema.project_id == project.id)
            ).first()
            if run is None:
                raise KeyError(
                    f"Unable to get pipeline run '{run_name}' in project "
                    f"'{project.name}': No pipeline run with this name "
                    "found."
                )

            return run.to_model()

    def get_run_dag(self, run_id: UUID) -> str:
        """Gets the DAG for a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The DAG for the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        pass  # TODO

    def get_run_component_side_effects(
        self,
        run_id: UUID,
        component_id: Optional[str] = None,
        component_type: Optional[StackComponentType] = None,
    ) -> Dict[str, Any]:
        """Gets the side effects for a component in a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.
            component_id: The ID of the component to get.

        Returns:
            The side effects for the component in the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        pass  # TODO

    def list_runs(
        self,
        project_name_or_id: Optional[Union[str, UUID]] = None,
        stack_id: Optional[UUID] = None,
        user_name_or_id: Optional[Union[str, UUID]] = None,
        pipeline_id: Optional[UUID] = None,
        unlisted: bool = False,
    ) -> List[PipelineRunModel]:
        """Gets all pipeline runs.

        Args:
            project_name_or_id: If provided, only return runs for this project.
            stack_id: If provided, only return runs for this stack.
            user_name_or_id: If provided, only return runs for this user.
            pipeline_id: If provided, only return runs for this pipeline.
            unlisted: If True, only return unlisted runs that are not
                associated with any pipeline (filter by pipeline_id==None).

        Returns:
            A list of all pipeline runs.
        """
        # TODO: [server] this filters the list by on of the filter parameters,
        #  not all, this might have to be redone
        self._sync_runs()  # Sync with MLMD
        with Session(self.engine) as session:
            query = select(PipelineRunSchema).where(
                PipelineRunSchema.stack_id == StackSchema.id
            )
            if project_name_or_id is not None:
                project = self._get_project_schema(project_name_or_id)
                query = query.where(StackSchema.project_id == project.id)
            if stack_id is not None:
                query = query.where(PipelineRunSchema.stack_id == stack_id)
            if pipeline_id is not None:
                query = query.where(
                    PipelineRunSchema.pipeline_id == pipeline_id
                )
            elif unlisted:
                query = query.where(PipelineRunSchema.pipeline_id == None)
            if user_name_or_id is not None:
                user = self._get_user_schema(user_name_or_id)
                query = query.where(PipelineRunSchema.owner == user.id)
            runs = session.exec(query).all()
            return [run.to_model() for run in runs]

    def update_run(
        self, run_id: UUID, run: PipelineRunModel
    ) -> PipelineRunModel:
        """Updates a pipeline run.

        Args:
            run_id: The ID of the pipeline run to update.
            run: The pipeline run to use for the update.

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
            existing_run.from_update_model(run)

            session.add(existing_run)
            session.commit()

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
            run = session.exec(
                select(PipelineRunSchema).where(PipelineRunSchema.id == run_id)
            ).first()
            if run is None:
                raise KeyError(
                    f"Unable to delete pipeline run with ID {run_id}: "
                    f"No pipeline run with this ID found."
                )

            # Delete the pipeline run
            session.delete(run)  # TODO: this doesn't delete from MLMD
            session.commit()

    # ------------------
    # Pipeline run steps
    # ------------------

    def get_run_step(self, step_id: int) -> StepRunModel:
        """Get a step by ID.

        Args:
            step_id: The ID of the step to get.

        Returns:
            The step.

        Raises:
            KeyError: if the step doesn't exist.
        """
        return self.metadata_store.get_step_by_id(step_id)

    def get_run_step_artifacts(
        self, step: StepRunModel
    ) -> Tuple[Dict[str, ArtifactModel], Dict[str, ArtifactModel]]:
        """Returns input and output artifacts for the given step.

        Args:
            step: The step for which to get the artifacts.

        Returns:
            A tuple (inputs, outputs) where inputs and outputs
            are both Dicts mapping artifact names
            to the input and output artifacts respectively.
        """
        return self.metadata_store.get_step_artifacts(step)

    def get_run_step_status(self, step_id: int) -> ExecutionStatus:
        """Gets the execution status of a single step.

        Args:
            step_id: The ID of the step to get the status for.

        Returns:
            ExecutionStatus: The status of the step.
        """
        return self.metadata_store.get_step_status(step_id=step_id)

    def list_run_steps(self, run_id: int) -> Dict[str, StepRunModel]:
        """Gets all steps in a pipeline run.

        Args:
            run_id: The ID of the pipeline run for which to list runs.

        Returns:
            A mapping from step names to step models for all steps in the run.
        """
        return self.metadata_store.get_pipeline_run_steps(run_id)

    # =======================
    # Internal helper methods
    # =======================

    def _get_schema_by_name_or_id(
        self,
        object_name_or_id: Union[str, UUID],
        schema_class: Type[SQLModel],
        schema_name: str,
    ) -> SQLModel:
        """Query a schema by its 'name' or 'id' field.

        Args:
            object_name_or_id: The name or ID of the object to query.
            schema_class: The schema class to query. E.g., `ProjectSchema`.
            schema_name: The name of the schema used for error messages.
                E.g., "project".

        Returns:
            The schema object.

        Raises:
            KeyError: if the object couldn't be found.
        """
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
        with Session(self.engine) as session:
            schema = session.exec(select(schema_class).where(filter)).first()
            if schema is None:
                raise KeyError(error_msg)
            return schema

    def _get_project_schema(
        self, project_name_or_id: Union[str, UUID]
    ) -> ProjectSchema:
        """Gets a project schema by name or ID.

        This is a helper method that is used in various places to find the
        project associated to some other object.

        Args:
            project_name_or_id: The name or ID of the project to get.

        Returns:
            The project schema.

        Raises:
            KeyError: if the project doesn't exist.
        """
        return cast(
            ProjectSchema,
            self._get_schema_by_name_or_id(
                object_name_or_id=project_name_or_id,
                schema_class=ProjectSchema,
                schema_name="project",
            ),
        )

    def _get_user_schema(self, user_name_or_id: Union[str, UUID]) -> UserSchema:
        """Gets a user schema by name or ID.

        This is a helper method that is used in various places to find the
        user associated to some other object.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The user schema.

        Raises:
            KeyError: if the user doesn't exist.
        """
        return cast(
            UserSchema,
            self._get_schema_by_name_or_id(
                object_name_or_id=user_name_or_id,
                schema_class=UserSchema,
                schema_name="user",
            ),
        )

    def _get_team_schema(self, team_name_or_id: Union[str, UUID]) -> TeamSchema:
        """Gets a team schema by name or ID.

        This is a helper method that is used in various places to find a team
        by its name or ID.

        Args:
            team_name_or_id: The name or ID of the team to get.

        Returns:
            The team schema.

        Raises:
            KeyError: if the team doesn't exist.
        """
        return cast(
            TeamSchema,
            self._get_schema_by_name_or_id(
                object_name_or_id=team_name_or_id,
                schema_class=TeamSchema,
                schema_name="team",
            ),
        )

    def _get_role_schema(self, role_name_or_id: Union[str, UUID]) -> RoleSchema:
        """Gets a role schema by name or ID.

        This is a helper method that is used in various places to find a role
        by its name or ID.

        Args:
            role_name_or_id: The name or ID of the role to get.

        Returns:
            The role schema.

        Raises:
            KeyError: if the role doesn't exist.
        """
        return cast(
            RoleSchema,
            self._get_schema_by_name_or_id(
                object_name_or_id=role_name_or_id,
                schema_class=RoleSchema,
                schema_name="role",
            ),
        )
