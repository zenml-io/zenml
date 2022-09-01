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
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union
from uuid import UUID

from ml_metadata.proto import metadata_store_pb2
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
from zenml.models.pipeline_models import PipelineModel, StepModel
from zenml.post_execution.artifact import ArtifactView
from zenml.post_execution.pipeline import PipelineView
from zenml.post_execution.pipeline_run import PipelineRunView
from zenml.post_execution.step import StepView
from zenml.stack.flavor_registry import flavor_registry
from zenml.utils import io_utils, uuid_utils
from zenml.zen_stores.base_zen_store import DEFAULT_USERNAME, BaseZenStore

# Enable SQL compilation caching to remove the https://sqlalche.me/e/14/cprf
# warning
from zenml.zen_stores.schemas.schemas import (
    CodeRepositorySchema,
    FlavorSchema,
    PipelineRunSchema,
    PipelineSchema,
    ProjectSchema,
    RoleSchema,
    StackComponentSchema,
    StackSchema,
    StepSchema,
    TeamAssignmentSchema,
    TeamRoleAssignmentSchema,
    TeamSchema,
    UserRoleAssignmentSchema,
    UserSchema,
)

SelectOfScalar.inherit_cache = True  # type: ignore
Select.inherit_cache = True  # type: ignore

logger = get_logger(__name__)


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

    # Static methods:

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
        return f"sqlite:///{path}/zenml.db"

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

    # Public interface:

    # .--------.
    # | STACKS |
    # '--------'

    @property
    def stacks_empty(self) -> bool:
        """Check if the store is empty (no stacks are configured).

        The implementation of this method should check if the store is empty
        without having to load all the stacks from the persistent storage.

        Returns:
            True if the store is empty, False otherwise.
        """
        with Session(self.engine) as session:
            return not session.exec(select(StackSchema)).first()

    @property
    def stack_names(self) -> List[str]:
        """Names of all stacks registered in this ZenStore.

        Returns:
            List of all stack names.
        """
        with Session(self.engine) as session:
            return [s.name for s in session.exec(select(StackSchema))]

    def _list_stacks(
        self,
        project_id: UUID,
        user_id: Optional[UUID] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[StackModel]:
        """List all stacks within the filter.

        Args:
            project_id: Id of the Project containing the stack components
            user_id: Optionally filter stack components by the owner
            name: Optionally filter stack component by name
            is_shared: Optionally filter out stack component by the `is_shared`
                       flag
        Returns:
            A list of all stacks.
        """
        with Session(self.engine) as session:

            # Get a list of all stacks
            query = select(StackSchema)
            # TODO: prettify
            if user_id:
                query = query.where(StackSchema.owner == user_id)
            if name:
                query = query.where(StackSchema.name == name)
            if is_shared is not None:
                query = query.where(StackSchema.is_shared == is_shared)
            stacks = session.exec(query).all()

            return [stack.to_model() for stack in stacks]

    def _get_stack(self, stack_id: UUID) -> StackModel:
        """Get a stack by id.

        Args:
            stack_id: The id of the stack to get.

        Returns:
            The stack with the given id.
        """
        with Session(self.engine) as session:
            stack = session.exec(
                select(StackSchema).where(StackSchema.id == stack_id)
            ).first()

            if stack is None:
                raise KeyError(f"Stack with ID {stack_id} not found.")
            return stack.to_model()

    def _register_stack(
        self,
        user_id: UUID,
        project_id: UUID,
        stack: StackModel
    ) -> StackModel:
        """Register a new stack.

        Args:
            stack: The stack to register.
            user_id: The user that is registering this stack
            project_id: The project within which that stack is registered

        Returns:
            The registered stack.

        Raises:
            StackExistsError: In case a stack with that name is already owned
                by this user on this project.
        """
        with Session(self.engine) as session:
            # Check if stack with the domain key (name, prj, owner) already
            #  exists
            existing_stack = session.exec(
                select(StackSchema)
                .where(StackSchema.name == stack.name)
                .where(StackSchema.project_id == project_id)
                .where(StackSchema.owner == user_id)
            ).first()
            # TODO: verify if is_shared status needs to be checked here
            if existing_stack is not None:
                raise StackExistsError(
                    f"Unable to register stack with name "
                    f"'{stack.name}': Found "
                    f"existing stack with this name. in the project for "
                    f"this user."
                )

            # Get the Schemas of all components mentioned in the stack model
            component_ids = [c.id for c in stack.components.values()]
            defined_components = session.exec(
                select(StackComponentSchema).where(
                    or_(
                        StackComponentSchema.id == component_ids[0],
                        StackComponentSchema.id == component_ids[1],
                    )
                )
            ).all()
            # TODO: Make this work for arbitrary amounts of components
            # Create the stack
            stack_in_db = StackSchema.from_create_model(
                project_id=project_id,
                user_id=user_id,
                defined_components=defined_components,
                stack=stack,
            )
            session.add(stack_in_db)
            session.commit()

            return stack_in_db.to_model()

    def _update_stack(self,
                      stack_id: str,
                      user_id: str,
                      project_id: UUID,
                      stack: StackModel) -> StackModel:
        """Update an existing stack.

        Args:
            stack_id: The id of the stack to update.
            user_id: The user that created the stack
            project_id: The project the user created this stack within
            stack: The stack to update.

        Returns:
            The updated stack.
        """
        with Session(self.engine) as session:
            # Check if stack with the domain key (name, prj, owner) already
            #  exists
            existing_stack = session.exec(
                select(StackSchema).where(StackSchema.id == stack_id)
            ).first()
            # TODO: verify if is_shared status needs to be checked here
            if existing_stack is None:
                raise KeyError(
                    f"Unable to update stack with id "
                    f"'{stack_id}': Found no"
                    f"existing stack with this id."
                )

            # TODO: validate the the composition of components is a valid stack
            # Get the Schemas of all components mentioned
            defined_components = session.exec(
                select(StackComponentSchema).where(
                    StackComponentSchema.id in stack.components.values()
                )
            ).all

            # Create the stack
            stack_in_db = StackSchema(
                id=stack_id,
                name=stack.name,
                project_id=project_id,
                owner=user_id,
                components=defined_components,
            )
            session.add(stack_in_db)
            session.commit()

            components_in_model = {c.type: c.id for c in defined_components}

            # TODO: [ALEXEJ] verify that the stack_in_db instance is actually
            #  updated automatically after the session commit
            return stack_in_db.to_model(components_in_model)

    def _delete_stack(self, stack_id: str) -> None:
        """Delete a stack.

        Args:
            stack_id: The id of the stack to delete.
        """
        with Session(self.engine) as session:
            try:
                stack = session.exec(
                    select(StackSchema).where(StackSchema.id == id)
                ).one()
                session.delete(stack)
            except NoResultFound as error:
                raise KeyError from error

            session.commit()

    #  .-----------------.
    # | STACK COMPONENTS |
    # '------------------'

    def _list_stack_components(
        self,
        project_id: UUID,
        type: Optional[str] = None,
        flavor_name: Optional[str] = None,
        user_id: Optional[str] = None,
        name: Optional[str] = None,
        is_shared: Optional[bool] = None,
    ) -> List[ComponentModel]:
        """List all stack components within the filter.

        Args:
            project_id: Id of the Project containing the stack components
            type: Optionally filter by type of stack component
            flavor_name: Optionally filter by flavor
            user_id: Optionally filter stack components by the owner
            name: Optionally filter stack component by name
            is_shared: Optionally filter out stack component by the `is_shared`
                       flag

        Returns:
            All stack components currently registered.
        """
        with Session(self.engine) as session:

            query = select(StackComponentSchema).where(
                StackComponentSchema.project_id == project_id
            )

            # TODO: [ALEXEJ] prettify this
            if type:
                 query = query.where(StackComponentSchema.type == type)
            if flavor_name:
                 query = query.where(StackComponentSchema.flavor_name == flavor_name)
            if user_id:
                query = query.where(StackComponentSchema.owner == user_id)
            if name:
                query = query.where(StackComponentSchema.name == name)
            if is_shared is not None:
                query = query.where(StackComponentSchema.is_shared == is_shared)

            list_of_stack_components_in_db = session.exec(query).all()

        return [comp.to_model() for comp in list_of_stack_components_in_db]

    def _get_stack_component(self, component_id: UUID) -> ComponentModel:
        """Get a stack component by id.

        Args:
            component_id: The id of the stack component to get.

        Returns:
            The stack component with the given id.
        """
        with Session(self.engine) as session:
            stack_component = session.exec(
                select(StackComponentSchema).where(
                    StackComponentSchema.id == component_id
                )
            ).first()

        return stack_component.to_model()

    def _register_stack_component(
        self,
        user_id: str,
        project_id: UUID,
        component: ComponentModel
    ) -> ComponentModel:
        """Create a stack component.

        Args:
            user_id: The user that created the stack component.
            project_id: The project the stack component is created in.
            component: The stack component to create.

        Returns:
            The created stack component.
        """
        with Session(self.engine) as session:
            # Check if component with the domain key (name, prj, owner) already
            #  exists
            existing_component = session.exec(
                select(StackComponentSchema)
                .where(StackComponentSchema.name == component.name)
                .where(StackComponentSchema.project_id == project_id)
                .where(StackComponentSchema.owner == user_id)
                .where(StackComponentSchema.type == component.type)
            ).first()
            # TODO: verify if is_shared status needs to be checked here
            if existing_component is not None:
                raise StackComponentExistsError(
                    f"Unable to register component with name "
                    f"'{component.name}': Found "
                    f"existing component with this name. in the project for "
                    f"this user."
                )

            # Create the component
            component_in_db = StackComponentSchema.from_create_model(
                user_id=user_id, project_id=project_id, component=component
            )

            session.add(component_in_db)
            session.commit()

            # TODO: [ALEXEJ] verify that the component_in_db instance is actually
            # updated automatically after the session commit
            return component_in_db.to_model()

    def _update_stack_component(
        self,
        user_id: str,
        project_id: UUID,
        component_id: str,
        component: ComponentModel,
    ) -> ComponentModel:
        """Update an existing stack component.

        Args:
            user_id: The user that created the stack component.
            project_id: The project the stack component is created in.
            component_id: The id of the stack component to update.
            component: The stack component to use for the update.

        Returns:
            The updated stack component.
        """
        # TODO: implement this

    def _delete_stack_component(self, component_id: str) -> None:
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

    def _get_stack_component_side_effects(
        self, component_id: str, run_id: str, pipeline_id: str, stack_id: str
    ) -> Dict[Any, Any]:
        """Get the side effects of a stack component.

        Args:
            component_id: The id of the stack component to get side effects for.
            run_id: The id of the run to get side effects for.
            pipeline_id: The id of the pipeline to get side effects for.
            stack_id: The id of the stack to get side effects for.
        """
        # TODO: implement this

    def _list_stack_component_types(self) -> List[str]:
        """List all stack component types.

        Returns:
            A list of all stack component types.
        """
        # TODO: This does not belong in the Zen Store
        return StackComponentType.values()

    def _list_stack_component_flavors_by_type(
        self,
        component_type: StackComponentType,
    ) -> List[FlavorModel]:
        """List all stack component flavors by type.

        Args:
            component_type: The stack component for which to get flavors.

        Returns:
            List of stack component flavors.
        """

        # List all the flavors of the component type
        zenml_flavors = [
            f
            for f in flavor_registry.get_flavors_by_type(
                component_type=component_type
            ).values()
        ]

        custom_flavors = self.get_flavors_by_type(component_type=component_type)

        return zenml_flavors + custom_flavors

    #  .------.
    # | USERS |
    # '-------'

    @property
    def active_user_name(self) -> str:
        """Gets the active username.

        Returns:
            The active username.
        """
        return DEFAULT_USERNAME

    def _list_users(self, invite_token: str = None) -> List[UserModel]:
        """List all users.

        Args:
            invite_token: The invite token to filter by.

        Returns:
            A list of all users.
        """
        with Session(self.engine) as session:
            users = session.exec(select(UserSchema)).all()

        return [user.to_model() for user in users]

    def _create_user(self, user: UserModel) -> UserModel:
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
            new_user = UserSchema.from_model(user)
            session.add(new_user)
            session.commit()

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

            return new_user.to_model()

    def _get_user(
        self, user_name_or_id: str, invite_token: str = None
    ) -> UserModel:
        """Gets a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.
            invite_token: Token to use for the invitation.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name or ID exists.
        """
        is_uuid = uuid_utils.is_valid_uuid(user_name_or_id)

        query = select(UserSchema)
        if is_uuid:
            query = query.where(UserSchema.id == user_name_or_id)
        else:
            query = query.where(UserSchema.name == user_name_or_id)

        with Session(self.engine) as session:
            user = session.exec(query).first()
            if user is None and is_uuid:
                raise KeyError(f"No user with ID '{user_name_or_id}' found.")
            if user is None:
                raise KeyError(
                    f"The given user name or ID '{user_name_or_id}' is not a "
                    "valid ID and no user with this name exists either."
                )
            return user.to_model()

    def _update_user(self, user_id: str, user: UserModel) -> UserModel:
        """Updates an existing user.

        Args:
            user_id: The ID of the user to update.
            user: The User model to use for the update.

        Returns:
            The updated user.

        Raises:
            KeyError: If no user with the given name exists.
        """
        with Session(self.engine) as session:
            existing_user = session.exec(
                select(UserSchema).where(UserSchema.id == user_id)
            ).first()
            if user is None:
                raise KeyError(
                    f"Unable to update user with id '{user_id}': "
                    "No user found with this id."
                )
            existing_user.name = user.name  # other attributes are not updatable
            session.add(existing_user)
            session.commit()
            return existing_user.to_model()

    def _delete_user(self, user_id: str) -> None:
        """Deletes a user.

        Args:
            user_id: The ID of the user to delete.

        Raises:
            KeyError: If no user with the given name exists.
        """
        with Session(self.engine) as session:
            user = session.exec(
                select(UserSchema).where(UserSchema.id == user_id)
            ).first()
            if user is None:
                raise KeyError(
                    f"Unable to delete user with id '{user_id}': "
                    "No user found with this id."
                )
            session.delete(user)
            session.commit()

    def get_invite_token(self, user_id: str) -> str:
        """Gets an invite token for a user.

        Args:
            user_id: ID of the user.

        Returns:
            The invite token for the specific user.
        """
        raise NotImplementedError()  # TODO

    def invalidate_invite_token(self, user_id: str) -> None:
        """Invalidates an invite token for a user.

        Args:
            user_id: ID of the user.
        """
        raise NotImplementedError()  # TODO

    #  .------.
    # | TEAMS |
    # '-------'

    def _list_teams(self) -> List[TeamModel]:
        """List all teams.

        Returns:
            A list of all teams.
        """
        with Session(self.engine) as session:
            teams = session.exec(select(TeamSchema)).all()
            return [team.to_model() for team in teams]

    def _create_team(self, team: TeamModel) -> TeamModel:
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
            new_team = TeamSchema.from_model(team)
            session.add(new_team)
            session.commit()

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

            return new_team.to_model()

    def _get_team(self, team_name_or_id: str) -> TeamModel:
        """Gets a specific team.

        Args:
            team_name_or_id: Name or ID of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name or ID exists.
        """
        is_uuid = uuid_utils.is_valid_uuid(team_name_or_id)

        query = select(TeamSchema)
        if is_uuid:
            query = query.where(TeamSchema.id == team_name_or_id)
        else:
            query = query.where(TeamSchema.name == team_name_or_id)

        with Session(self.engine) as session:
            team = session.exec(query).first()
            if team is None and is_uuid:
                raise KeyError(f"No team with ID '{team_name_or_id}' found.")
            if team is None:
                raise KeyError(
                    f"The given team name or ID '{team_name_or_id}' is not a "
                    "valid ID and no team with this name exists either."
                )
            return team.to_model()

    def _delete_team(self, team_id: str) -> None:
        """Deletes a team.

        Args:
            team_id: ID of the team to delete.

        Raises:
            KeyError: If no team with the given ID exists.
        """
        with Session(self.engine) as session:
            team = session.exec(
                select(TeamSchema).where(TeamSchema.id == team_id)
            ).first()
            if team is None:
                raise KeyError(
                    f"Unable to delete team with id '{team_id}': "
                    "No team found with this id."
                )
            session.delete(team)
            session.commit()

    def add_user_to_team(self, user_id: str, team_id: str) -> None:
        """Adds a user to a team.

        Args:
            user_id: ID of the user to add to the team.
            team_id: ID of the team to which to add the user to.

        Raises:
            KeyError: If the team or user does not exist.
            EntityExistsError: If the user is already a member of the team.
        """
        with Session(self.engine) as session:
            # Check if team with the given ID exists
            team = session.exec(
                select(TeamSchema).where(TeamSchema.id == team_id)
            ).first()
            if team is None:
                raise KeyError(
                    f"Unable to add user with id '{user_id}' to team with id "
                    f"'{team_id}': No team found with this id."
                )

            # Check if user with the given ID exists
            user = session.exec(
                select(UserSchema).where(UserSchema.id == user_id)
            ).first()
            if user is None:
                raise KeyError(
                    f"Unable to add user with id '{user_id}' to team with id "
                    f"'{team_id}': No user found with this id."
                )

            # Check if user is already in the team
            existing_user_in_team = session.exec(
                select(TeamAssignmentSchema)
                .where(TeamAssignmentSchema.user_id == user_id)
                .where(TeamAssignmentSchema.team_id == team_id)
            ).first()
            if existing_user_in_team is not None:
                raise EntityExistsError(
                    f"Unable to add user with id '{user_id}' to team with id "
                    f"'{team_id}': User is already in the team."
                )

            # Add user to team
            team.users = team.users + [user]
            session.add(team)
            session.commit()

    def remove_user_from_team(self, user_id: str, team_id: str) -> None:
        """Removes a user from a team.

        Args:
            user_id: ID of the user to remove from the team.
            team_id: ID of the team from which to remove the user.

        Raises:
            KeyError: If the team or user does not exist.
        """
        with Session(self.engine) as session:
            # Check if team with the given ID exists
            team = session.exec(
                select(TeamSchema).where(TeamSchema.id == team_id)
            ).first()
            if team is None:
                raise KeyError(
                    f"Unable to remove user with id '{user_id}' from team with "
                    f"id '{team_id}': No team found with this id."
                )

            # Check if user with the given ID exists
            user = session.exec(
                select(UserSchema).where(UserSchema.id == user_id)
            ).first()
            if user is None:
                raise KeyError(
                    f"Unable to remove user with id '{user_id}' from team with "
                    f"id '{team_id}': No user found with this id."
                )

            # Remove user from team
            team.users = [user_ for user_ in team.users if user_.id != user_id]
            session.add(team)
            session.commit()

    def get_users_for_team(self, team_id: str) -> List[UserModel]:
        """Fetches all users of a team.

        Args:
            team_id: The ID of the team for which to get users.

        Returns:
            A list of all users that are part of the team.

        Raises:
            KeyError: If no team with the given ID exists.
        """
        with Session(self.engine) as session:
            team = session.exec(
                select(TeamSchema).where(TeamSchema.id == team_id)
            ).first()
            if team is None:
                raise KeyError(
                    f"Unable to get users for team with id '{team_id}': "
                    "No team found with this id."
                )
            return [user.to_model() for user in team.users]

    def get_teams_for_user(self, user_id: str) -> List[TeamModel]:
        """Fetches all teams for a user.

        Args:
            user_id: The ID of the user for which to get all teams.

        Returns:
            A list of all teams that the user is part of.

        Raises:
            KeyError: If no user with the given ID exists.
        """
        with Session(self.engine) as session:
            user = session.exec(
                select(UserSchema).where(UserSchema.id == user_id)
            ).first()
            if user is None:
                raise KeyError(
                    f"Unable to get teams for user with id '{user_id}': "
                    "No user found with this id."
                )
            return [team.to_model() for team in user.teams]

    #  .------.
    # | ROLES |
    # '-------'

    def list_roles(self) -> List[RoleModel]:
        """List all roles.

        Returns:
            A list of all roles.
        """
        with Session(self.engine) as session:
            roles = session.exec(select(RoleSchema)).all()

        return [role.to_model() for role in roles]

    def _get_role_assignments_for_user(self, user_id: str) -> List[RoleModel]:
        """Fetches all role assignments for a user.

        Args:
            user_id: ID of the user.

        Returns:
            List of role assignments for this user.

        Raises:
            KeyError: If no user or project with the given names exists.
        """
        with Session(self.engine) as session:
            roles = session.exec(
                select(RoleSchema)
                .where(UserRoleAssignmentSchema.role_id == RoleSchema.id)
                .where(UserRoleAssignmentSchema.user_id == user_id)
            ).all()

        return [role.to_model() for role in roles]

    def _assign_role(self, user_id: str, role_id: str, project_id: str) -> None:
        """Assigns a role to a user or team, scoped to a specific project.

        Args:
            user_id: ID of the user.
            role_id: ID of the role to assign to the user.
            project_id: ID of the project in which to assign the role to the
                user.

        Raises:
            KeyError: If no user, role, or project with the given IDs exists.
        """
        with Session(self.engine) as session:
            # Check if user with the given name already exists
            user = session.exec(
                select(UserSchema).where(UserSchema.id == user_id)
            ).first()
            if user is None:
                raise KeyError(
                    f"Unable to assign role to user with id '{user_id}': "
                    "No user with this id found."
                )

            # Check if role with the given name already exists
            role = session.exec(
                select(RoleSchema).where(RoleSchema.id == role_id)
            ).first()
            if role is None:
                raise KeyError(
                    f"Unable to assign role with id '{role_id}': "
                    "No role with this id found."
                )

            # Check if project with the given name already exists
            project = session.exec(
                select(ProjectSchema).where(ProjectSchema.id == project_id)
            ).first()
            if project is None:
                raise KeyError(
                    f"Unable to assign role in project with id "
                    f"'{project_id}': No project with this id found."
                )

            # Create the user role assignment
            user_role_assignment = UserRoleAssignmentSchema(
                user_id=user_id, role_id=role_id, project_id=project_id
            )
            session.add(user_role_assignment)
            session.commit()

    def _unassign_role(
        self, user_id: str, role_id: str, project_id: str
    ) -> None:
        """Unassigns a role from a user or team for a given project.

        Args:
            user_id: ID of the user.
            role_id: ID of the role to unassign.
            project_id: ID of the project in which to unassign the role from the
                user.

        Raises:
            KeyError: If the role was not assigned to the user in the given
                project.
        """
        with Session(self.engine) as session:
            # Check if role with the given name already exists
            role = session.exec(
                select(UserRoleAssignmentSchema)
                .where(UserRoleAssignmentSchema.user_id == user_id)
                .where(UserRoleAssignmentSchema.role_id == role_id)
                .where(UserRoleAssignmentSchema.project_id == project_id)
            ).first()
            if role is None:
                raise KeyError(
                    f"Unable to unassign role {role_id} from user {user_id} in "
                    f"project {project_id}: The role is currently not assigned "
                    "to the user."
                )

            session.delete(role)
            session.commit()

    #  .----------------.
    # | METADATA_CONFIG |
    # '-----------------'

    def get_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Get the TFX metadata config of this ZenStore.

        Returns:
            The TFX metadata config of this ZenStore.
        """
        return self.metadata_store.get_tfx_metadata_config()

    #  .---------.
    # | PROJECTS |
    # '----------'

    def _list_projects(self) -> List[ProjectModel]:
        """List all projects.

        Returns:
            A list of all projects.
        """
        with Session(self.engine) as session:
            projects = session.exec(select(ProjectSchema)).all()
            return [project.to_model() for project in projects]

    def _create_project(self, project: ProjectModel) -> ProjectModel:
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
            new_project = ProjectSchema.from_model(project)
            session.add(new_project)
            session.commit()

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

            return new_project.to_model()

    def _get_project(self, project_name_or_id: str) -> ProjectModel:
        """Get an existing project by name or ID.

        Args:
            project_name_or_id: Name or ID of the project to get.

        Returns:
            The requested project if one was found.

        Raises:
            KeyError: If there is no such project.
        """
        is_uuid = uuid_utils.is_valid_uuid(project_name_or_id)

        query = select(ProjectSchema)
        if is_uuid:
            query = query.where(ProjectSchema.id == project_name_or_id)
        else:
            query = query.where(ProjectSchema.name == project_name_or_id)

        with Session(self.engine) as session:
            project = session.exec(query).first()
            if project is None and is_uuid:
                raise KeyError(
                    f"No project with ID '{project_name_or_id}' found."
                )
            if project is None:
                raise KeyError(
                    f"The given project name or ID '{project_name_or_id}' is "
                    "not a valid ID and no project with this name exists "
                    "either."
                )
            return project.to_model()

    def _update_project(
        self, project_name: str, project: ProjectModel
    ) -> ProjectModel:
        """Update an existing project.

        Args:
            project_name: Name of the project to update.
            project: The project to use for the update.

        Returns:
            The updated project.

        Raises:
            KeyError: if the project does not exist.
        """
        with Session(self.engine) as session:
            # Check if project with the given name already exists
            existing_project = session.exec(
                select(ProjectSchema).where(ProjectSchema.name == project_name)
            ).first()
            if existing_project is None:
                raise KeyError(
                    f"Unable to update project {project_name}: "
                    "No project with this name found."
                )

            # Update the project
            existing_project.name = project.name
            existing_project.description = project.description
            # other fields are not updatable
            session.add(existing_project)
            session.commit()

            return existing_project.to_model()

    def _delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """
        with Session(self.engine) as session:
            # Check if project with the given name already exists
            project = session.exec(
                select(ProjectSchema).where(ProjectSchema.name == project_name)
            ).first()
            if project is None:
                raise KeyError(
                    f"Unable to delete project {project_name}: "
                    "No project with this name found."
                )

            session.delete(project)  # TODO: cascade delete
            session.commit()

    def _get_default_stack(self, project_name: str) -> StackModel:
        """Gets the default stack in a project.

        Args:
            project_name: Name of the project to get.

        Returns:
            The default stack in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        pass  # TODO

    def _set_default_stack(
        self, project_name: str, stack_id: str
    ) -> StackModel:
        """Sets the default stack in a project.

        Args:
            project_name: Name of the project to set.
            stack_id: The ID of the stack to set as the default.

        Raises:
            KeyError: if the project or stack doesn't exist.
        """
        pass  # TODO

    #  .-------------.
    # | REPOSITORIES |
    # '--------------'

    # TODO: create repos?

    def _list_project_repositories(
        self, project_name: str
    ) -> List[CodeRepositoryModel]:
        """Get all repositories in the project.

        Args:
            project_name: The name of the project.

        Returns:
            A list of all repositories in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if project with the given name already exists
            project = session.exec(
                select(ProjectSchema).where(ProjectSchema.name == project_name)
            ).first()
            if project is None:
                raise KeyError(
                    f"Unable to list repositories in project {project_name}: "
                    "No project with this name found."
                )

            # Get all repositories in the project
            repositories = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.project_id == project.id
                )
            ).all()

        return [repository.to_model() for repository in repositories]

    def _connect_project_repository(
        self, project_name: str, repository: CodeRepositoryModel
    ) -> CodeRepositoryModel:
        """Connects a repository to a project.

        Args:
            project_name: Name of the project to connect the repository to.
            repository: The repository to connect.

        Returns:
            The connected repository.

        Raises:
            KeyError: if the project or repository doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if project with the given name already exists
            project = session.exec(
                select(ProjectSchema).where(ProjectSchema.name == project_name)
            ).first()
            if project is None:
                raise KeyError(
                    f"Unable to connect repository with ID {repository.id} to "
                    f"project {project_name}: No project with this name found."
                )

            # Check if repository with the given name already exists
            existing_repository = session.exec(
                select(CodeRepositorySchema).where(
                    CodeRepositorySchema.id == repository.id
                )
            ).first()
            if existing_repository is None:
                raise KeyError(
                    f"Unable to connect repository with ID {repository.id} to "
                    f"project {project_name}: No repository with this ID found."
                )

            # Connect the repository to the project
            existing_repository.project_id = project.id
            session.add(existing_repository)
            session.commit()

            return existing_repository.to_model()

    def _get_repository(self, repository_id: str) -> CodeRepositoryModel:
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

    def _update_repository(
        self, repository_id: str, repository: CodeRepositoryModel
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
            existing_repository.name = repository.name
            # project_id is updated in `_connect_project_repository`
            # other fields are not updatable
            session.add(existing_repository)
            session.commit()

            return existing_repository.to_model()

    def _delete_repository(self, repository_id: str) -> None:
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

    #  .----------.
    # | PIPELINES |
    # '-----------'

    def _list_pipelines(self, project_name: str) -> List[PipelineModel]:
        """List all pipelines in the project.

        Args:
            project_name: Name of the project.

        Returns:
            A list of pipelines.

        Raises:
            KeyError: if the project does not exist.
        """
        with Session(self.engine) as session:
            # Check if project with the given name exists
            project = session.exec(
                select(ProjectSchema).where(ProjectSchema.name == project_name)
            ).first()
            if project is None:
                raise KeyError(
                    f"Unable to list pipelines in project {project_name}: "
                    f"No project with this name found."
                )

            # Get all pipelines in the project
            pipelines = session.exec(
                select(PipelineSchema).where(
                    PipelineSchema.project_id == project.id
                )
            ).all()

        return [pipeline.to_model() for pipeline in pipelines]

    def _create_pipeline(
        self, project_name: str, pipeline: PipelineModel
    ) -> PipelineModel:
        """Creates a new pipeline in a project.

        Args:
            project_name: Name of the project to create the pipeline in.
            pipeline: The pipeline to create.

        Returns:
            The newly created pipeline.

        Raises:
            KeyError: if the project does not exist.
            EntityExistsError: If an identical pipeline already exists.
        """
        with Session(self.engine) as session:
            # Check if project with the given name exists
            project = session.exec(
                select(ProjectSchema).where(ProjectSchema.name == project_name)
            ).first()
            if project is None:
                raise KeyError(
                    f"Unable to create pipeline in project {project_name}: "
                    f"No project with this name found."
                )

            # Check if pipeline with the given name already exists
            existing_pipeline = session.exec(
                select(PipelineSchema).where(
                    PipelineSchema.name == pipeline.name
                )
            ).first()
            if existing_pipeline is not None:
                raise EntityExistsError(
                    f"Unable to create pipeline in project {project_name}: "
                    f"A pipeline with this name already exists."
                )

            # Create the pipeline
            new_pipeline = PipelineSchema.from_model(pipeline)
            session.add(new_pipeline)
            session.commit()

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

            return new_pipeline.to_model()

    def get_pipeline(self, pipeline_id: str) -> Optional[PipelineModel]:
        """Returns a pipeline for the given name.

        Args:
            pipeline_id: ID of the pipeline.

        Returns:
            PipelineModel if found, None otherwise.
        """
        with Session(self.engine) as session:
            # Check if pipeline with the given ID exists
            pipeline = session.exec(
                select(PipelineSchema).where(PipelineSchema.id == pipeline_id)
            ).first()
            if pipeline is None:
                return None

            return pipeline.to_model()

    def _update_pipeline(
        self, pipeline_id: str, pipeline: PipelineModel
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
            existing_pipeline.name = pipeline.name
            existing_pipeline.docstring = pipeline.docstring
            existing_pipeline.configuration = pipeline.configuration
            existing_pipeline.git_sha = pipeline.git_sha
            # Other fields are not updatable

            session.add(existing_pipeline)
            session.commit()

            return existing_pipeline.to_model()

    def _delete_pipeline(self, pipeline_id: str) -> None:
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

            session.delete(pipeline)  # TODO: cascade? what about runs?
            session.commit()

    def _get_pipeline_configuration(self, pipeline_id: str) -> Dict[Any, Any]:
        """Gets the pipeline configuration.

        Args:
            pipeline_id: The ID of the pipeline to get.

        Returns:
            The pipeline configuration.

        Raises:
            KeyError: if the pipeline doesn't exist.
        """
        pass  # TODO

    def _list_steps(self, pipeline_id: str) -> List[StepModel]:
        """List all steps.

        Args:
            pipeline_id: The ID of the pipeline to list steps for.

        Returns:
            A list of all steps.
        """
        pass  # TODO

    #  .-----.
    # | RUNS |
    # '------'

    def _get_pipeline_runs(self, pipeline_id: str) -> List[PipelineRunModel]:
        """Gets all pipeline runs in a pipeline.

        Args:
            pipeline_id: The ID of the pipeline to get.

        Returns:
            A list of all pipeline runs in the pipeline.

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
                    f"Unable to get pipeline runs for pipeline with ID "
                    f"{pipeline_id}: No pipeline with this ID found."
                )

            # Get all pipeline runs in the pipeline
            pipeline_runs = session.exec(
                select(PipelineRunSchema).where(
                    PipelineRunSchema.pipeline_id == pipeline.id
                )
            ).all()

        return [pipeline_run.to_model() for pipeline_run in pipeline_runs]

    def _create_pipeline_run(
        self, pipeline_id: str, pipeline_run: PipelineRunModel
    ) -> PipelineRunModel:
        """Creates a pipeline run.

        Args:
            pipeline_id: The ID of the pipeline to create the run in.
            pipeline_run: The pipeline run to create.

        Returns:
            The created pipeline run.

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
                    f"Unable to create pipeline run in pipeline with ID "
                    f"{pipeline_id}: No pipeline with this ID found."
                )

            # Create the pipeline run
            new_pipeline_run = PipelineRunSchema.from_model(pipeline_run)
            session.add(new_pipeline_run)
            session.commit()

            # After committing the model, sqlmodel takes care of updating the
            # object with id, created_at, etc ...

            return new_pipeline_run.to_model()

    def _list_pipeline_runs(
        self,
        project_name: Optional[str] = None,
        stack_id: Optional[str] = None,
        pipeline_id: Optional[str] = None,
        trigger_id: Optional[str] = None,
    ) -> List[PipelineRunModel]:
        """Gets all pipeline runs in a project.

        Args:
            project_name: Name of the project to get.
            stack_id: ID of the stack to get.
            pipeline_id: ID of the pipeline to get.
            trigger_id: ID of the trigger to get.

        Returns:
            A list of all pipeline runs in the project.

        Raises:
            KeyError: if the project doesn't exist.
        """
        # TODO: remove? Seems redundant with get_pipeline_runs()

    def _get_run(self, run_id: str) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The pipeline run.

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
                    f"Unable to get pipeline run with ID {run_id}: "
                    f"No pipeline run with this ID found."
                )

            return run.to_model()

    def _update_run(
        self, run_id: str, run: PipelineRunModel
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
            existing_run.name = run.name
            existing_run.runtime_configuration = run.runtime_configuration
            existing_run.git_sha = run.git_sha
            existing_run.zenml_version = run.zenml_version
            # Other fields are not updatable

            session.add(existing_run)
            session.commit()

            return existing_run.to_model()

    def _delete_run(self, run_id: str) -> None:
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
            session.delete(run)
            session.commit()

    def _get_run_dag(self, run_id: str) -> str:
        """Gets the DAG for a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The DAG for the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        pass  # TODO

    def _get_run_runtime_configuration(self, run_id: str) -> Dict:
        """Gets the runtime configuration for a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            The runtime configuration for the pipeline run.

        Raises:
            KeyError: if the pipeline run doesn't exist.
        """
        run = self._get_run(run_id)
        return run.runtime_configuration

    def _get_run_component_side_effects(
        self,
        run_id: str,
        component_id: Optional[str] = None,
        component_type: Optional[StackComponentType] = None,
    ) -> Dict:
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

    #  .------.
    # | STEPS |
    # '-------'

    def _list_run_steps(self, run_id: str) -> List[StepModel]:
        """Gets all steps in a pipeline run.

        Args:
            run_id: The ID of the pipeline run to get.

        Returns:
            A list of all steps in the pipeline run.

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
                    f"Unable to get steps for pipeline run with ID {run_id}: "
                    f"No pipeline run with this ID found."
                )

            # Get the steps
            steps = session.exec(
                select(StepSchema).where(StepSchema.pipeline_run_id == run_id)
            )
            return [step.to_model() for step in steps]

    def _get_run_step(self, step_id: str) -> StepModel:
        """Get a step by ID.

        Args:
            step_id: The ID of the step to get.

        Returns:
            The step.

        Raises:
            KeyError: if the step doesn't exist.
        """
        with Session(self.engine) as session:
            # Check if step with the given ID exists
            step = session.exec(
                select(StepSchema).where(StepSchema.id == step_id)
            ).first()
            if step is None:
                raise KeyError(
                    f"Unable to get step with ID {step_id}: "
                    f"No step with this ID found."
                )
            return step.to_model()

    def _get_run_step_outputs(self, step_id: str) -> Dict[str, ArtifactView]:
        """Get the outputs of a step.

        Args:
            step_id: The ID of the step to get outputs for.

        Returns:
            The outputs of the step.
        """
        pass  # TODO: currently not saved in DB

    def _get_run_step_inputs(self, step_id: str) -> Dict[str, ArtifactView]:
        """Get the inputs of a step.

        Args:
            step_id: The ID of the step to get inputs for.

        Returns:
            The inputs of the step.
        """
        pass  # TODO: currently not saved in DB

    # LEGACY CODE FROM THE PREVIOUS VERSION OF BASEZENSTORE

    # Private interface implementations:

    def _get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type.

        Args:
            component_type: The type of the component to list names for.

        Returns:
            A list of names as strings.
        """
        with Session(self.engine) as session:
            statement = select(StackComponentSchema).where(
                StackComponentSchema.type == component_type
            )
            return [component.name for component in session.exec(statement)]

    # User, project and role management

    @property
    def role_assignments(self) -> List[RoleAssignmentModel]:
        """All registered role assignments.

        Returns:
            A list of all registered role assignments.
        """
        with Session(self.engine) as session:
            user_roles = session.exec(select(UserRoleAssignmentSchema)).all()
            team_roles = session.exec(select(TeamRoleAssignmentSchema)).all()
            return [
                RoleAssignmentModel(**assignment.dict())
                for assignment in [*user_roles, *team_roles]
            ]

    def _get_role(self, role_name: str) -> RoleModel:
        """Gets a specific role.

        Args:
            role_name: Name of the role to get.

        Returns:
            The requested role.

        Raises:
            KeyError: If no role with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                role = session.exec(
                    select(RoleSchema).where(RoleSchema.name == role_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            return RoleModel(**role.dict())

    def _create_role(self, role_name: str) -> RoleModel:
        """Creates a new role.

        Args:
            role_name: Unique role name.

        Returns:
            The newly created role.

        Raises:
            EntityExistsError: If a role with the given name already exists.
        """
        with Session(self.engine) as session:
            existing_role = session.exec(
                select(RoleSchema).where(RoleSchema.name == role_name)
            ).first()
            if existing_role:
                raise EntityExistsError(
                    f"Role with name '{role_name}' already exists."
                )
            sql_role = RoleSchema(name=role_name)
            role = RoleModel(**sql_role.dict())
            session.add(sql_role)
            session.commit()
        return role

    def _delete_role(self, role_name: str) -> None:
        """Deletes a role.

        Args:
            role_name: Name of the role to delete.

        Raises:
            KeyError: If no role with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                role = session.exec(
                    select(RoleSchema).where(RoleSchema.name == role_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(role)
            session.commit()
            self._delete_query_results(
                select(UserRoleAssignmentSchema).where(
                    UserRoleAssignmentSchema.role_id == role.id
                )
            )
            self._delete_query_results(
                select(TeamRoleAssignmentSchema).where(
                    TeamRoleAssignmentSchema.role_id == role.id
                )
            )

    def assign_role(
        self,
        role_name: str,
        entity_name: str,
        project_name: Optional[str] = None,
        is_user: bool = True,
    ) -> None:
        """Assigns a role to a user or team.

        Args:
            role_name: Name of the role to assign.
            entity_name: User or team name.
            project_name: Optional project name.
            is_user: Boolean indicating whether the given `entity_name` refers
                to a user.

        Raises:
            KeyError: If no role, entity or project with the given names exists.
        """
        with Session(self.engine) as session:
            user_id: Optional[UUID] = None
            team_id: Optional[UUID] = None
            project_id: Optional[UUID] = None

            try:
                role_id = session.exec(
                    select(RoleSchema.id).where(RoleSchema.name == role_name)
                ).one()

                if project_name:
                    project_id = session.exec(
                        select(ProjectSchema.id).where(
                            ProjectSchema.name == project_name
                        )
                    ).one()

                if is_user:
                    user_id = session.exec(
                        select(UserSchema.id).where(
                            UserSchema.name == entity_name
                        )
                    ).one()
                    assignment = UserRoleAssignmentSchema(
                        role_id=role_id,
                        project_id=project_id,
                        user_id=user_id,
                    )
                    session.add(assignment)
                    session.commit()
                else:
                    team_id = session.exec(
                        select(TeamSchema.id).where(
                            TeamSchema.name == entity_name
                        )
                    ).one()
                    assignment = TeamRoleAssignmentSchema(
                        role_id=role_id,
                        project_id=project_id,
                        team_id=team_id,
                    )
                    session.add(assignment)
                    session.commit()
            except NoResultFound as error:
                raise KeyError from error

    def revoke_role(
        self,
        role_name: str,
        entity_name: str,
        project_name: Optional[str] = None,
        is_user: bool = True,
    ) -> None:
        """Revokes a role from a user or team.

        Args:
            role_name: Name of the role to revoke.
            entity_name: User or team name.
            project_name: Optional project name.
            is_user: Boolean indicating whether the given `entity_name` refers
                to a user.

        Raises:
            KeyError: If no role, entity or project with the given names exists.
        """
        with Session(self.engine) as session:

            if is_user:
                statement = (
                    select(UserRoleAssignmentSchema)
                    .where(UserRoleAssignmentSchema.role_id == RoleSchema.id)
                    .where(RoleSchema.name == role_name)
                    .where(UserRoleAssignmentSchema.user_id == UserSchema.id)
                    .where(UserSchema.name == entity_name)
                )
                if project_name:
                    statement = statement.where(
                        UserRoleAssignmentSchema.project_id == ProjectSchema.id
                    ).where(ProjectSchema.name == project_name)
            else:
                statement = (
                    select(TeamRoleAssignmentSchema)
                    .where(TeamRoleAssignmentSchema.role_id == RoleSchema.id)
                    .where(RoleSchema.name == role_name)
                    .where(TeamRoleAssignmentSchema.team_id == TeamSchema.id)
                    .where(TeamSchema.name == entity_name)
                )
                if project_name:
                    statement = statement.where(
                        TeamRoleAssignmentSchema.project_id == ProjectSchema.id
                    ).where(ProjectSchema.name == project_name)

            try:
                assignment = session.exec(statement).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(assignment)
            session.commit()

    def get_role_assignments_for_user(
        self,
        user_name: str,
        project_name: Optional[str] = None,
        include_team_roles: bool = True,
    ) -> List[RoleAssignmentModel]:
        """Fetches all role assignments for a user.

        Args:
            user_name: Name of the user.
            project_name: Optional filter to only return roles assigned for
                this project.
            include_team_roles: If `True`, includes roles for all teams that
                the user is part of.

        Returns:
            List of role assignments for this user.

        Raises:
            KeyError: If no user or project with the given names exists.
        """
        with Session(self.engine) as session:
            try:
                user_id = session.exec(
                    select(UserSchema.id).where(UserSchema.name == user_name)
                ).one()
                statement = select(UserRoleAssignmentSchema).where(
                    UserRoleAssignmentSchema.user_id == user_id
                )
                if project_name:
                    project_id = session.exec(
                        select(ProjectSchema.id).where(
                            ProjectSchema.name == project_name
                        )
                    ).one()
                    statement = statement.where(
                        UserRoleAssignmentSchema.project_id == project_id
                    )
            except NoResultFound as error:
                raise KeyError from error

            assignments = [
                RoleAssignmentModel(**assignment.dict())
                for assignment in session.exec(statement).all()
            ]
            if include_team_roles:
                for team in self.get_teams_for_user(user_name):
                    assignments += self.get_role_assignments_for_team(
                        team.name, project_name=project_name
                    )

            return assignments

    def get_role_assignments_for_team(
        self,
        team_name: str,
        project_name: Optional[str] = None,
    ) -> List[RoleAssignmentModel]:
        """Fetches all role assignments for a team.

        Args:
            team_name: Name of the user.
            project_name: Optional filter to only return roles assigned for
                this project.

        Returns:
            List of role assignments for this team.

        Raises:
            KeyError: If no team or project with the given names exists.
        """
        with Session(self.engine) as session:
            try:
                team_id = session.exec(
                    select(TeamSchema.id).where(TeamSchema.name == team_name)
                ).one()

                statement = select(TeamRoleAssignmentSchema).where(
                    TeamRoleAssignmentSchema.team_id == team_id
                )
                if project_name:
                    project_id = session.exec(
                        select(ProjectSchema.id).where(
                            ProjectSchema.name == project_name
                        )
                    ).one()
                    statement = statement.where(
                        TeamRoleAssignmentSchema.project_id == project_id
                    )
            except NoResultFound as error:
                raise KeyError from error

            return [
                RoleAssignmentModel(**assignment.dict())
                for assignment in session.exec(statement).all()
            ]

    # Pipelines and pipeline runs

    def get_pipeline(self, pipeline_name: str) -> Optional[PipelineView]:
        """Returns a pipeline for the given name.

        Args:
            pipeline_name: Name of the pipeline.

        Returns:
            PipelineView if found, None otherwise.
        """
        return self.metadata_store.get_pipeline(pipeline_name)

    def get_pipelines(self) -> List[PipelineView]:
        """Returns a list of all pipelines stored in this ZenStore.

        Returns:
            A list of all pipelines stored in this ZenStore.
        """
        return self.metadata_store.get_pipelines()

    def get_pipeline_run(
        self, pipeline: PipelineView, run_name: str
    ) -> Optional[PipelineRunView]:
        """Gets a specific run for the given pipeline.

        Args:
            pipeline: The pipeline for which to get the run.
            run_name: The name of the run to get.

        Returns:
            The pipeline run with the given name.
        """
        return self.metadata_store.get_pipeline_run(pipeline, run_name)

    def get_pipeline_runs(
        self, pipeline: PipelineView
    ) -> Dict[str, PipelineRunView]:
        """Gets all runs for the given pipeline.

        Args:
            pipeline: a Pipeline object for which you want the runs.

        Returns:
            A dictionary of pipeline run names to PipelineRunView.
        """
        return self.metadata_store.get_pipeline_runs(pipeline)

    def get_pipeline_run_wrapper(
        self,
        pipeline_name: str,
        run_name: str,
        project_name: Optional[str] = None,
    ) -> PipelineRunModel:
        """Gets a pipeline run.

        Args:
            pipeline_name: Name of the pipeline for which to get the run.
            run_name: Name of the pipeline run to get.
            project_name: Optional name of the project from which to get the
                pipeline run.

        Returns:
            Pipeline run.

        Raises:
            KeyError: If no pipeline run (or project) with the given name
                exists.
        """
        with Session(self.engine) as session:
            try:
                statement = (
                    select(PipelineRunSchema)
                    .where(PipelineRunSchema.name == run_name)
                    .where(PipelineRunSchema.pipeline_name == pipeline_name)
                )

                if project_name:
                    statement = statement.where(
                        PipelineRunSchema.project_name == project_name
                    )

                run = session.exec(statement).one()
                return run.to_model()
            except NoResultFound as error:
                raise KeyError from error

    def get_pipeline_run_wrappers(
        self, pipeline_name: str, project_name: Optional[str] = None
    ) -> List[PipelineRunModel]:
        """Gets pipeline runs.

        Args:
            pipeline_name: Name of the pipeline for which to get runs.
            project_name: Optional name of the project from which to get the
                pipeline runs.

        Returns:
            List of pipeline runs.

        Raises:
            KeyError: If no pipeline with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                statement = select(PipelineRunSchema).where(
                    PipelineRunSchema.pipeline_name == pipeline_name
                )

                if project_name:
                    statement = statement.where(
                        PipelineRunSchema.project_name == project_name
                    )
                return [run.to_model() for run in session.exec(statement).all()]
            except NoResultFound as error:
                raise KeyError from error

    def get_pipeline_run_steps(
        self, pipeline_run: PipelineRunView
    ) -> Dict[str, StepView]:
        """Gets all steps for the given pipeline run.

        Args:
            pipeline_run: The pipeline run to get the steps for.

        Returns:
            A dictionary of step names to step views.
        """
        return self.metadata_store.get_pipeline_run_steps(pipeline_run)

    def get_step_by_id(self, step_id: int) -> StepView:
        """Gets a `StepView` by its ID.

        Args:
            step_id (int): The ID of the step to get.

        Returns:
            StepView: The `StepView` with the given ID.
        """
        return self.metadata_store.get_step_by_id(step_id)

    def get_step_status(self, step: StepView) -> ExecutionStatus:
        """Gets the execution status of a single step.

        Args:
            step (StepView): The step to get the status for.

        Returns:
            ExecutionStatus: The status of the step.
        """
        return self.metadata_store.get_step_status(step)

    def get_step_artifacts(
        self, step: StepView
    ) -> Tuple[Dict[str, ArtifactView], Dict[str, ArtifactView]]:
        """Returns input and output artifacts for the given step.

        Args:
            step: The step for which to get the artifacts.

        Returns:
            A tuple (inputs, outputs) where inputs and outputs
            are both Dicts mapping artifact names
            to the input and output artifacts respectively.
        """
        return self.metadata_store.get_step_artifacts(step)

    def get_producer_step_from_artifact(self, artifact_id: int) -> StepModel:
        """Returns original StepView from an ArtifactView.

        Args:
            artifact_id: ID of the ArtifactView to be queried.

        Returns:
            Original StepView that produced the artifact.
        """
        return self.metadata_store.get_producer_step_from_artifact(artifact_id)

    def register_pipeline_run(
        self,
        pipeline_run: PipelineRunModel,
    ) -> None:
        """Registers a pipeline run.

        Args:
            pipeline_run: The pipeline run to register.

        Raises:
            EntityExistsError: If a pipeline run with the same name already
                exists.
        """
        with Session(self.engine) as session:
            existing_run = session.exec(
                select(PipelineRunSchema).where(
                    PipelineRunSchema.name == pipeline_run.name
                )
            ).first()
            if existing_run:
                raise EntityExistsError(
                    f"Pipeline run with name '{pipeline_run.name}' already"
                    "exists. Please make sure your pipeline run names are "
                    "unique."
                )

            sql_run = PipelineRunSchema.from_model(pipeline_run)
            session.add(sql_run)
            session.commit()

    # Handling stack component flavors

    @property
    def flavors(self) -> List[FlavorModel]:
        """All registered flavors.

        Returns:
            A list of all registered flavors.
        """
        with Session(self.engine) as session:
            return [
                FlavorModel(**flavor.dict())
                for flavor in session.exec(select(FlavorSchema)).all()
            ]

    def _create_flavor(
        self,
        source: str,
        name: str,
        stack_component_type: StackComponentType,
    ) -> FlavorModel:
        """Creates a new flavor.

        Args:
            source: the source path to the implemented flavor.
            name: the name of the flavor.
            stack_component_type: the corresponding StackComponentType.

        Returns:
            The newly created flavor.

        Raises:
            EntityExistsError: If a flavor with the given name and type
                already exists.
        """
        with Session(self.engine) as session:
            existing_flavor = session.exec(
                select(FlavorSchema).where(
                    FlavorSchema.name == name,
                    FlavorSchema.type == stack_component_type,
                )
            ).first()
            if existing_flavor:
                raise EntityExistsError(
                    f"A {stack_component_type} with '{name}' flavor already "
                    f"exists."
                )
            sql_flavor = FlavorSchema(
                name=name,
                source=source,
                type=stack_component_type,
            )
            flavor_wrapper = FlavorModel(**sql_flavor.dict())
            session.add(sql_flavor)
            session.commit()
        return flavor_wrapper

    def get_flavors_by_type(
        self, component_type: StackComponentType
    ) -> List[FlavorModel]:
        """Fetch all flavor defined for a specific stack component type.

        Args:
            component_type: The type of the stack component.

        Returns:
            List of all the flavors for the given stack component type.
        """
        # TODO: [ALEXEJ] This should be list_flavors with a filter
        with Session(self.engine) as session:
            flavors = session.exec(
                select(FlavorSchema).where(FlavorSchema.type == component_type)
            ).all()
        return [
            FlavorModel(
                name=f.name,
                source=f.source,
                type=f.type,
                integration=f.integration,
            )
            for f in flavors
        ]

    def get_flavor_by_name_and_type(
        self,
        flavor_name: str,
        component_type: StackComponentType,
    ) -> FlavorModel:
        """Fetch a flavor by a given name and type.

        Args:
            flavor_name: The name of the flavor.
            component_type: Optional, the type of the component.

        Returns:
            Flavor instance if it exists

        Raises:
            KeyError: If no flavor exists with the given name and type
                or there are more than one instances
        """
        with Session(self.engine) as session:
            try:
                flavor = session.exec(
                    select(FlavorSchema).where(
                        FlavorSchema.name == flavor_name,
                        FlavorSchema.type == component_type,
                    )
                ).one()
                return FlavorModel(
                    name=flavor.name,
                    source=flavor.source,
                    type=flavor.type,
                    integration=flavor.integration,
                )
            except NoResultFound as error:
                raise KeyError from error

    # TODO: [ALEXEJ] This should be list_flavors with a filter

    # Implementation-specific internal methods:

    def _delete_query_results(self, query: Any) -> None:
        """Deletes all rows returned by the input query.

        Args:
            query: The query to execute.
        """
        with Session(self.engine) as session:
            for result in session.exec(query).all():
                session.delete(result)
            session.commit()
