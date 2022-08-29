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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from ml_metadata.proto import metadata_store_pb2
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError, NoResultFound
from sqlmodel import Session, SQLModel, create_engine, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.exceptions import EntityExistsError, StackComponentExistsError, \
    StackExistsError
from zenml.logger import get_logger
from zenml.metadata_stores.sqlite_metadata_store import SQLiteMetadataStore
from zenml.models import (
    ComponentModel,
    FlavorModel,
    PipelineRunModel,
    Project,
    Role,
    RoleAssignment,
    Team,
    User, StackModel,
)
from zenml.post_execution.artifact import ArtifactView
from zenml.post_execution.pipeline import PipelineView
from zenml.post_execution.pipeline_run import PipelineRunView
from zenml.post_execution.step import StepView
from zenml.utils import io_utils
from zenml.zen_stores.base_zen_store import (
    DEFAULT_PROJECT_NAME,
    DEFAULT_USERNAME,
    BaseZenStore,
)

# Enable SQL compilation caching to remove the https://sqlalche.me/e/14/cprf
# warning
from zenml.zen_stores.schemas.schemas import (
    FlavorSchema,
    PipelineRunSchema,
    ProjectSchema,
    RoleSchema,
    StackComponentSchema,
    StackCompositionSchema,
    StackSchema,
    TeamAssignmentSchema,
    TeamRoleAssignmentSchema,
    TeamSchema,
    UserRoleAssignmentSchema,
    UserSchema,
)

SelectOfScalar.inherit_cache = True  # type: ignore
Select.inherit_cache = True  # type: ignore

logger = get_logger(__name__)


class SqlZenStore(BaseZenStore):
    """Repository Implementation that uses SQL database backend."""

    def initialize(
        self,
        url: str,
        *args: Any,
        **kwargs: Any,
    ) -> "SqlZenStore":
        """Initialize a new SqlZenStore.

        Args:
            url: odbc path to a database.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            The initialized zen store instance.

        Raises:
            ValueError: If the database is not found.
        """
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL for SQL store: {url}")

        logger.debug("Initializing SqlZenStore at %s", url)
        self._url = url

        local_path = self.get_path_from_url(url)
        if local_path:
            io_utils.create_dir_recursive_if_not_exists(str(local_path.parent))

        metadata_store_path = os.path.join(
            os.path.dirname(str(local_path)), "metadata.db"
        )
        self._metadata_store = SQLiteMetadataStore(uri=metadata_store_path)

        # we need to remove `skip_default_registrations` from the kwargs,
        # because SQLModel will raise an error if it is present
        sql_kwargs = kwargs.copy()
        sql_kwargs.pop("skip_default_registrations", False)
        sql_kwargs.pop("track_analytics", False)
        sql_kwargs.pop("skip_migration", False)
        self.engine = create_engine(url, *args, **sql_kwargs)
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            if not session.exec(select(UserSchema)).first():
                session.add(UserSchema(name=DEFAULT_USERNAME))
                session.add(ProjectSchema(name=DEFAULT_PROJECT_NAME))
            session.commit()

        super().initialize(url, *args, **kwargs)
        return self

    # Public interface implementations:

    @property
    def type(self) -> StoreType:
        """The type of zen store.

        Returns:
            The type of zen store.
        """
        return StoreType.SQL

    @property
    def url(self) -> str:
        """URL of the repository.

        Returns:
            The URL of the repository.

        Raises:
            RuntimeError: If the SQL zen store is not initialized.
        """
        if not self._url:
            raise RuntimeError(
                "SQL zen store has not been initialized. Call `initialize` "
                "before using the store."
            )
        return self._url

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

        Raises:
            ValueError: If the URL is not a valid SQLite URL.
        """
        if not SqlZenStore.is_valid_url(url):
            raise ValueError(f"Invalid URL for SQL store: {url}")
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
    def is_valid_url(url: str) -> bool:
        """Check if the given url is a valid SQL url.

        Args:
            url: The url to check.

        Returns:
            True if the url is a valid SQL url, False otherwise.
        """
        try:
            make_url(url)
        except ArgumentError:
            logger.debug("Invalid SQL URL: %s", url)
            return False

        return True

    @property
    def stacks_empty(self) -> bool:
        """Check if the zen store is empty.

        Returns:
            True if the zen store is empty, False otherwise.
        """
        with Session(self.engine) as session:
            return session.exec(select(StackSchema)).first() is None

    #  .--------.
    # | STACKS |
    # '--------'

    def _list_stacks(self) -> List[StackModel]:
        """List all stacks.

        Returns:
            A list of all stacks.
        """
        # TODO: apply filters
        with Session(self.engine) as session:
            list_of_stacks_and_components = session.exec(
                select(StackSchema, StackComponentSchema)
                .where(StackSchema.id == StackCompositionSchema.stack_id)
                .where(StackComponentSchema.id == StackCompositionSchema.component_id)
            ).all()

        for stack, components in list_of_stacks_and_components:
            # TODO: construct StackModel
            return None

    def _get_stack(self, stack_id: str) -> StackModel:
        """Get a stack by id.

        Args:
            stack_id: The id of the stack to get.

        Returns:
            The stack with the given id.
        """
        with Session(self.engine) as session:
            list_of_stacks_and_components = session.exec(
                select(StackSchema, StackComponentSchema)
                .where(StackSchema.id == stack_id)
                .where(StackSchema.id == StackCompositionSchema.stack_id)
                .where(StackComponentSchema.id == StackCompositionSchema.component_id)
            ).all()

        for stack, components in list_of_stacks_and_components:
            # TODO: construct StackModel from Stack and corresponding Components
            return None

    def _register_stack(self, stack: StackModel, user: User) -> StackModel:
        """Register a new stack.

        Args:
            stack: The stack to register.

        Returns:
            The registered stack.
        """
        with Session(self.engine) as session:
            # Check if stack with the domain key (name, prj, owner) already
            #  exists
            existing_stack = session.exec(
                select(StackSchema)
                .where(StackSchema.name == stack.name)
                .where(StackSchema.project_id == stack.project)
                .where(StackSchema.owner == user.id)
            ).first()
            # TODO: verify if is_shared status needs to be checked here
            if existing_stack is not None:
                raise StackExistsError(
                    f"Unable to register stack with name "
                    f"'{stack.name}': Found "
                    f"existing stack with this name. in the project for"
                    f"this user."
                )

            # TODO: validate the the composition of components is a valid stack
            # Get the Schemas of all components mentioned
            defined_components = session.exec(
                select(StackComponentSchema)
                .where(StackComponentSchema.id in stack.components.values())
            ).all

            # Create the stack
            stack_in_db = StackSchema(name=stack.name,
                                      project_id=stack.project,
                                      owner=user.id,
                                      components=defined_components)
            session.add(stack_in_db)
            session.commit()

            # After committing the model, sqlmodel takes care of updating the
            #  object with id, created_at, etc ...
            # TODO: construct StackModel
            return None


    def _update_stack(self, stack_id: str, stack: StackModel) -> StackModel:
        """Update an existing stack.

        Args:
            stack_id: The id of the stack to update.
            stack: The stack to update.

        Returns:
            The updated stack.
        """
        with Session(self.engine) as session:
            # Check if stack with the domain key (name, prj, owner) already
            #  exists
            existing_stack = session.exec(
                select(StackSchema)
                .where(StackSchema.name == stack.name)
                .where(StackSchema.project_id == stack.project)
                .where(StackSchema.owner == user.id)
            ).first()
            # TODO: verify if is_shared status needs to be checked here
            if existing_stack is not None:
                raise StackExistsError(
                    f"Unable to register stack with name "
                    f"'{stack.name}': Found "
                    f"existing stack with this name. in the project for"
                    f"this user."
                )

            # TODO: validate the the composition of components is a valid stack
            # Get the Schemas of all components mentioned
            defined_components = session.exec(
                select(StackComponentSchema)
                .where(StackComponentSchema.id in stack.components.values())
            ).all

            # Create the stack
            stack_in_db = StackSchema(name=stack.name,
                                      project_id=stack.project,
                                      owner=user.id,
                                      components=defined_components)
            session.add(stack_in_db)
            session.commit()

            # After committing the model, sqlmodel takes care of updating the
            #  object with id, created_at, etc ...
            # TODO: construct StackModel
            return None

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

            # TODO: verify this is actually necessary, this might already
            #  be handled by sqlmodel
            definitions = session.exec(
                select(StackCompositionSchema)
                .where(StackCompositionSchema.stack_id == StackSchema.id)
            ).all()
            for definition in definitions:
                session.delete(definition)

            session.commit()


# OLD STUFF BELOW HERE #############################################################################################################################

    def get_stack_configuration(
        self, name: str
    ) -> Dict[StackComponentType, str]:
        """Fetches a stack configuration by name.

        Args:
            name: The name of the stack to fetch.

        Returns:
            Dict[StackComponentType, str] for the requested stack name.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        logger.debug("Fetching stack with name '%s'.", name)
        # first check that the stack exists
        with Session(self.engine) as session:
            maybe_stack = session.exec(
                select(StackSchema).where(StackSchema.name == name)
            ).first()
        if maybe_stack is None:
            raise KeyError(
                f"Unable to find stack with name '{name}'. Available names: "
                f"{set(self.stack_names)}."
            )
        # then get all components assigned to that stack
        with Session(self.engine) as session:
            definitions_and_components = session.exec(
                select(StackCompositionSchema, StackComponentSchema)
                .where(
                    StackCompositionSchema.component_id
                    == StackComponentSchema.id
                )
                .where(StackCompositionSchema.stack_id == StackSchema.id)
                .where(StackSchema.name == name)
            )
            params = {
                component.type: component.name
                for _, component in definitions_and_components
            }
        return {StackComponentType(typ): name for typ, name in params.items()}

    @property
    def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
        """Configuration for all stacks registered in this zen store.

        Returns:
            Dictionary mapping stack names to Dict[StackComponentType, str]
        """
        return {n: self.get_stack_configuration(n) for n in self.stack_names}

    def get_stack_component_type(self, name: str) -> List[str]:
        """Fetches all available stack component types.

        Returns:
            List of available stack component types.
        """
        # TODO: leave this to later in the process
        return NotImplementedError

    @property
    def stack_component_types(self) -> List[StackComponentType]:
        """List of stack component types.

        Returns:
            List of stack component types.
        """
        # get all stack components
        # get the component for each type
        # return them as a list
        # TODO: leave this to later in the process
        return NotImplementedError

    def _register_stack_component(
        self,
        component: ComponentModel,
    ) -> None:
        """Register a stack component.

        Args:
            component: The component to register.

        Raises:
            StackComponentExistsError: If a stack component with the same type
                and name already exists.
        """
        with Session(self.engine) as session:
            existing_component = session.exec(
                select(StackComponentSchema)
                .where(StackComponentSchema.name == component.name)
                .where(StackComponentSchema.type == component.type)
            ).first()
            if existing_component is not None:
                raise StackComponentExistsError(
                    f"Unable to register stack component (type: "
                    f"{component.type}) with name '{component.name}': Found "
                    f"existing stack component with this name."
                )
            new_component = StackComponentSchema(
                type=component.type,
                name=component.name,
                flavor=component.flavor,
                configuration=component.config,
            )  # TODO: update
            session.add(new_component)
            session.commit()

    def _update_stack_component(
        self,
        name: str,
        component_type: StackComponentType,
        component: ComponentModel,
    ) -> Dict[str, str]:
        """Update a stack component.

        Args:
            name: The original name of the stack component.
            component_type: The type of the stack component to update.
            component: The new component to update with.

        Returns:
            The updated stack component.

        Raises:
            KeyError: If no stack component exists with the given name.
            StackComponentExistsError: If a stack component with the same type
                and name already exists.
        """
        with Session(self.engine) as session:
            updated_component = session.exec(
                select(StackComponentSchema)
                .where(StackComponentSchema.type == component_type)
                .where(StackComponentSchema.name == name)
            ).first()

            if not updated_component:
                raise KeyError(
                    f"Unable to update stack component (type: "
                    f"{component.type}) with name '{component.name}': No "
                    f"existing stack component found with this name."
                )

            new_name_component = session.exec(
                select(StackComponentSchema)
                .where(StackComponentSchema.type == component_type)
                .where(StackComponentSchema.name == component.name)
            ).first()
            if (name != component.name) and new_name_component is not None:
                raise StackComponentExistsError(
                    f"Unable to update stack component (type: "
                    f"{component.type}) with name '{component.name}': Found "
                    f"existing stack component with this name."
                )

            updated_component.configuration = component.config

            # handle any potential renamed component
            updated_component.name = component.name

            session.add(updated_component)
            session.commit()
        logger.info(
            "Updated stack component with type '%s' and name '%s'.",
            component_type,
            component.name,
        )
        return {component.type.value: component.flavor}

    def _deregister_stack(self, name: str) -> None:
        """Delete a stack from storage.

        Args:
            name: The name of the stack to be deleted.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        with Session(self.engine) as session:
            try:
                stack = session.exec(
                    select(StackSchema).where(StackSchema.name == name)
                ).one()
                session.delete(stack)
            except NoResultFound as error:
                raise KeyError from error
            definitions = session.exec(
                select(StackCompositionSchema)
                .where(StackCompositionSchema.stack_id == StackSchema.id)
                .where(StackSchema.name == name)
            ).all()
            for definition in definitions:
                session.delete(definition)
            session.commit()

    # Private interface implementations:

    def _get_tfx_metadata_config(
        self,
    ) -> Union[
        metadata_store_pb2.ConnectionConfig,
        metadata_store_pb2.MetadataStoreClientConfig,
    ]:
        """Get the TFX metadata config of this ZenStore.

        Returns:
            The TFX metadata config of this ZenStore.
        """
        return self._metadata_store.get_tfx_metadata_config()

    def _save_stack(
        self,
        name: str,
        stack_configuration: Dict[StackComponentType, str],
    ) -> None:
        """Save a stack.

        Args:
            name: The name to save the stack as.
            stack_configuration: Dict[StackComponentType, str] to persist.
        """
        with Session(self.engine) as session:
            stack = session.exec(
                select(StackSchema).where(StackSchema.name == name)
            ).first()
            if stack is None:
                stack = StackSchema(name=name, created_by=1)
                session.add(stack)
            else:
                # clear the existing stack definitions for a stack
                # that is about to be updated
                query = select(StackCompositionSchema).where(
                    StackCompositionSchema.stack_id == stack.id
                )
                for result in session.exec(query).all():
                    session.delete(result)

            for ctype, cname in stack_configuration.items():
                # get all stack composition schemas for a stack and check if
                # a stack component with the given type already exists connected
                # to the stack
                statement = (
                    select(StackCompositionSchema)
                    .where(StackCompositionSchema.stack_id == stack.id)
                    .where(
                        StackCompositionSchema.component_id
                        == StackComponentSchema.id
                    )
                    .where(StackComponentSchema.type == ctype)
                )
                results = session.exec(statement)
                composition = results.one_or_none()

                component = session.exec(
                    select(StackComponentSchema)
                    .where(StackComponentSchema.name == cname)
                    .where(StackComponentSchema.type == ctype)
                ).first()
                if composition is None:
                    session.add(
                        StackCompositionSchema(
                            stack_id=stack.id, component_id=component.id
                        )
                    )
                else:
                    composition.component_id = component.id
                    session.add(composition)
            session.commit()

    def _get_component_flavor_and_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[str, str]:
        """Fetch the flavor and configuration for a stack component.

        Args:
            component_type: The type of the component to fetch.
            name: The name of the component to fetch.

        Returns:
            Pair of (flavor, configuration) for stack component, as string and
            base64-encoded yaml document, respectively

        Raises:
            KeyError: If no stack component exists for the given type and name.
        """
        with Session(self.engine) as session:
            component_and_flavor = session.exec(
                select(StackComponentSchema, FlavorSchema)
                .where(StackComponentSchema.type == component_type)
                .where(StackComponentSchema.name == name)
                .where(StackComponentSchema.flavor_id == FlavorSchema.id)
            ).one_or_none()
            if component_and_flavor is None:
                raise KeyError(
                    f"Unable to find stack component (type: {component_type}) "
                    f"with name '{name}'."
                )
        return (
            component_and_flavor[1].name,
            component_and_flavor[0].configuration,
        )

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

    def _delete_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Remove a StackComponent from storage.

        Args:
            component_type: The type of component to delete.
            name: Then name of the component to delete.

        Raises:
            KeyError: If no component exists for given type and name.
        """
        with Session(self.engine) as session:
            component = session.exec(
                select(StackComponentSchema)
                .where(StackComponentSchema.type == component_type)
                .where(StackComponentSchema.name == name)
            ).first()
            if component is not None:
                session.delete(component)
                session.commit()
            else:
                raise KeyError(
                    "Unable to deregister stack component (type: "
                    f"{component_type.value}) with name '{name}': No stack "
                    "component exists with this name."
                )

    # User, project and role management

    @property
    def users(self) -> List[User]:
        """All registered users.

        Returns:
            A list of all registered users.
        """
        with Session(self.engine) as session:
            return [
                User(**user.dict())
                for user in session.exec(select(UserSchema)).all()
            ]

    def _get_user(self, user_name: str) -> User:
        """Get a specific user by name.

        Args:
            user_name: Name of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                user = session.exec(
                    select(UserSchema).where(UserSchema.name == user_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            return User(**user.dict())

    def _create_user(self, user_name: str) -> User:
        """Creates a new user.

        Args:
            user_name: Unique username.

        Returns:
            The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """
        with Session(self.engine) as session:
            existing_user = session.exec(
                select(UserSchema).where(UserSchema.name == user_name)
            ).first()
            if existing_user:
                raise EntityExistsError(
                    f"User with name '{user_name}' already exists."
                )
            sql_user = UserSchema(name=user_name)
            user = User(**sql_user.dict())
            session.add(sql_user)
            session.commit()
        return user

    def _delete_user(self, user_name: str) -> None:
        """Deletes a user.

        Args:
            user_name: Name of the user to delete.

        Raises:
            KeyError: If no user with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                user = session.exec(
                    select(UserSchema).where(UserSchema.name == user_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(user)
            session.commit()
            self._delete_query_results(
                select(UserRoleAssignmentSchema).where(
                    UserRoleAssignmentSchema.user_id == user.id
                )
            )
            self._delete_query_results(
                select(TeamAssignmentSchema).where(
                    TeamAssignmentSchema.user_id == user.id
                )
            )

    @property
    def teams(self) -> List[Team]:
        """All registered teams.

        Returns:
            A list of all registered teams.
        """
        with Session(self.engine) as session:
            return [
                Team(**team.dict())
                for team in session.exec(select(TeamSchema)).all()
            ]

    def _get_team(self, team_name: str) -> Team:
        """Gets a specific team.

        Args:
            team_name: Name of the team to get.

        Returns:
            The requested team.

        Raises:
            KeyError: If no team with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                team = session.exec(
                    select(TeamSchema).where(TeamSchema.name == team_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            return Team(**team.dict())

    def _create_team(self, team_name: str) -> Team:
        """Creates a new team.

        Args:
            team_name: Unique team name.

        Returns:
            The newly created team.

        Raises:
            EntityExistsError: If a team with the given name already exists.
        """
        with Session(self.engine) as session:
            existing_team = session.exec(
                select(TeamSchema).where(TeamSchema.name == team_name)
            ).first()
            if existing_team:
                raise EntityExistsError(
                    f"Team with name '{team_name}' already exists."
                )
            sql_team = TeamSchema(name=team_name)
            team = Team(**sql_team.dict())
            session.add(sql_team)
            session.commit()
        return team

    def _delete_team(self, team_name: str) -> None:
        """Deletes a team.

        Args:
            team_name: Name of the team to delete.

        Raises:
            KeyError: If no team with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                team = session.exec(
                    select(TeamSchema).where(TeamSchema.name == team_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(team)
            session.commit()
            self._delete_query_results(
                select(TeamRoleAssignmentSchema).where(
                    TeamRoleAssignmentSchema.team_id == team.id
                )
            )
            self._delete_query_results(
                select(TeamAssignmentSchema).where(
                    TeamAssignmentSchema.team_id == team.id
                )
            )

    def add_user_to_team(self, team_name: str, user_name: str) -> None:
        """Adds a user to a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.

        Raises:
            KeyError: If no user and team with the given names exists.
        """
        with Session(self.engine) as session:
            try:
                team = session.exec(
                    select(TeamSchema).where(TeamSchema.name == team_name)
                ).one()
                user = session.exec(
                    select(UserSchema).where(UserSchema.name == user_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            assignment = TeamAssignmentSchema(user_id=user.id, team_id=team.id)
            session.add(assignment)
            session.commit()

    def remove_user_from_team(self, team_name: str, user_name: str) -> None:
        """Removes a user from a team.

        Args:
            team_name: Name of the team.
            user_name: Name of the user.

        Raises:
            KeyError: If no user and team with the given names exists.
        """
        with Session(self.engine) as session:
            try:
                assignment = session.exec(
                    select(TeamAssignmentSchema)
                    .where(TeamAssignmentSchema.team_id == TeamSchema.id)
                    .where(TeamAssignmentSchema.user_id == UserSchema.id)
                    .where(UserSchema.name == user_name)
                    .where(TeamSchema.name == team_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(assignment)
            session.commit()

    @property
    def projects(self) -> List[Project]:
        """All registered projects.

        Returns:
            A list of all registered projects.
        """
        with Session(self.engine) as session:
            return [
                Project(**project.dict())
                for project in session.exec(select(ProjectSchema)).all()
            ]

    def _get_project(self, project_name: str) -> Project:
        """Get an existing project by name.

        Args:
            project_name: Name of the project to get.

        Returns:
            The requested project if one was found.

        Raises:
            KeyError: If there is no such project.
        """
        with Session(self.engine) as session:
            try:
                project = session.exec(
                    select(ProjectSchema).where(
                        ProjectSchema.name == project_name
                    )
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            return Project(**project.dict())

    def _create_project(
        self, project_name: str, description: Optional[str] = None
    ) -> Project:
        """Creates a new project.

        Args:
            project_name: Unique project name.
            description: Optional project description.

        Returns:
            The newly created project.

        Raises:
            EntityExistsError: If a project with the given name already exists.
        """
        with Session(self.engine) as session:
            existing_project = session.exec(
                select(ProjectSchema).where(ProjectSchema.name == project_name)
            ).first()
            if existing_project:
                raise EntityExistsError(
                    f"Project with name '{project_name}' already exists."
                )
            sql_project = ProjectSchema(name=project_name)
            project = Project(**sql_project.dict())
            session.add(sql_project)
            session.commit()
        return project

    def _delete_project(self, project_name: str) -> None:
        """Deletes a project.

        Args:
            project_name: Name of the project to delete.

        Raises:
            KeyError: If no project with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                project = session.exec(
                    select(ProjectSchema).where(
                        ProjectSchema.name == project_name
                    )
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(project)
            session.commit()
            self._delete_query_results(
                select(UserRoleAssignmentSchema).where(
                    UserRoleAssignmentSchema.project_id == project.id
                )
            )
            self._delete_query_results(
                select(TeamRoleAssignmentSchema).where(
                    TeamRoleAssignmentSchema.project_id == project.id
                )
            )

    @property
    def roles(self) -> List[Role]:
        """All registered roles.

        Returns:
            A list of all registered roles.
        """
        with Session(self.engine) as session:
            return [
                Role(**role.dict())
                for role in session.exec(select(RoleSchema)).all()
            ]

    @property
    def role_assignments(self) -> List[RoleAssignment]:
        """All registered role assignments.

        Returns:
            A list of all registered role assignments.
        """
        with Session(self.engine) as session:
            user_roles = session.exec(select(UserRoleAssignmentSchema)).all()
            team_roles = session.exec(select(TeamRoleAssignmentSchema)).all()
            return [
                RoleAssignment(**assignment.dict())
                for assignment in [*user_roles, *team_roles]
            ]

    def _get_role(self, role_name: str) -> Role:
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

            return Role(**role.dict())

    def _create_role(self, role_name: str) -> Role:
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
            role = Role(**sql_role.dict())
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

    def get_users_for_team(self, team_name: str) -> List[User]:
        """Fetches all users of a team.

        Args:
            team_name: Name of the team.

        Returns:
            List of users that are part of the team.

        Raises:
            KeyError: If no team with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                team_id = session.exec(
                    select(TeamSchema.id).where(TeamSchema.name == team_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            users = session.exec(
                select(UserSchema)
                .where(UserSchema.id == TeamAssignmentSchema.user_id)
                .where(TeamAssignmentSchema.team_id == team_id)
            ).all()
            return [User(**user.dict()) for user in users]

    def get_teams_for_user(self, user_name: str) -> List[Team]:
        """Fetches all teams for a user.

        Args:
            user_name: Name of the user.

        Returns:
            List of teams that the user is part of.

        Raises:
            KeyError: If no user with the given name exists.
        """
        with Session(self.engine) as session:
            try:
                user_id = session.exec(
                    select(UserSchema.id).where(UserSchema.name == user_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            teams = session.exec(
                select(TeamSchema)
                .where(TeamSchema.id == TeamAssignmentSchema.team_id)
                .where(TeamAssignmentSchema.user_id == user_id)
            ).all()
            return [Team(**team.dict()) for team in teams]

    def get_role_assignments_for_user(
        self,
        user_name: str,
        project_name: Optional[str] = None,
        include_team_roles: bool = True,
    ) -> List[RoleAssignment]:
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
                RoleAssignment(**assignment.dict())
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
    ) -> List[RoleAssignment]:
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
                RoleAssignment(**assignment.dict())
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
        return self._metadata_store.get_pipeline(pipeline_name)

    def get_pipelines(self) -> List[PipelineView]:
        """Returns a list of all pipelines stored in this ZenStore.

        Returns:
            A list of all pipelines stored in this ZenStore.
        """
        return self._metadata_store.get_pipelines()

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
        return self._metadata_store.get_pipeline_run(pipeline, run_name)

    def get_pipeline_runs(
        self, pipeline: PipelineView
    ) -> Dict[str, PipelineRunView]:
        """Gets all runs for the given pipeline.

        Args:
            pipeline: a Pipeline object for which you want the runs.

        Returns:
            A dictionary of pipeline run names to PipelineRunView.
        """
        return self._metadata_store.get_pipeline_runs(pipeline)

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
                return run.to_pipeline_run_wrapper()
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
                return [
                    run.to_pipeline_run_wrapper()
                    for run in session.exec(statement).all()
                ]
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
        return self._metadata_store.get_pipeline_run_steps(pipeline_run)

    def get_step_by_id(self, step_id: int) -> StepView:
        """Gets a `StepView` by its ID.

        Args:
            step_id (int): The ID of the step to get.

        Returns:
            StepView: The `StepView` with the given ID.
        """
        return self._metadata_store.get_step_by_id(step_id)

    def get_step_status(self, step: StepView) -> ExecutionStatus:
        """Gets the execution status of a single step.

        Args:
            step (StepView): The step to get the status for.

        Returns:
            ExecutionStatus: The status of the step.
        """
        return self._metadata_store.get_step_status(step)

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
        return self._metadata_store.get_step_artifacts(step)

    def get_producer_step_from_artifact(self, artifact_id: int) -> StepView:
        """Returns original StepView from an ArtifactView.

        Args:
            artifact_id: ID of the ArtifactView to be queried.

        Returns:
            Original StepView that produced the artifact.
        """
        return self._metadata_store.get_producer_step_from_artifact(artifact_id)

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

            sql_run = PipelineRunSchema.from_pipeline_run_wrapper(pipeline_run)
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

    # Implementation-specific internal methods:

    @property
    def stack_names(self) -> List[str]:
        """Names of all stacks registered in this ZenStore.

        Returns:
            List of all stack names.
        """
        with Session(self.engine) as session:
            return [s.name for s in session.exec(select(StackSchema))]

    def _delete_query_results(self, query: Any) -> None:
        """Deletes all rows returned by the input query.

        Args:
            query: The query to execute.
        """
        with Session(self.engine) as session:
            for result in session.exec(query).all():
                session.delete(result)
            session.commit()
