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
import datetime as dt
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError, NoResultFound
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlmodel.sql.expression import Select, SelectOfScalar

from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import EntityExistsError, StackComponentExistsError
from zenml.io import utils
from zenml.logger import get_logger
from zenml.zen_stores import BaseZenStore
from zenml.zen_stores.models import (
    ComponentWrapper,
    FlavorWrapper,
    Project,
    Role,
    RoleAssignment,
    StackWrapper,
    Team,
    User,
)
from zenml.zen_stores.models.pipeline_models import (
    PipelineRunWrapper,
    PipelineWrapper,
)

# Enable SQL compilation caching to remove the https://sqlalche.me/e/14/cprf
# warning
SelectOfScalar.inherit_cache = True  # type: ignore
Select.inherit_cache = True  # type: ignore

logger = get_logger(__name__)


def _sqlmodel_uuid() -> UUID:
    """Generates a UUID whose hex string does not start with a '0'."""
    # SQLModel crashes when a UUID hex string starts with '0'
    # (see: https://github.com/tiangolo/sqlmodel/issues/25)
    uuid = uuid4()
    while uuid.hex[0] == "0":
        uuid = uuid4()
    return uuid


class ZenUser(SQLModel, table=True):
    id: int = Field(primary_key=True)
    name: str


class ZenStack(SQLModel, table=True):
    name: str = Field(primary_key=True)
    created_by: int
    create_time: Optional[dt.datetime] = Field(default_factory=dt.datetime.now)


class ZenStackComponent(SQLModel, table=True):
    component_type: StackComponentType = Field(primary_key=True)
    name: str = Field(primary_key=True)
    component_flavor: str
    configuration: bytes  # e.g. base64 encoded json string


class ZenFlavor(SQLModel, table=True):
    type: StackComponentType = Field(primary_key=True)
    name: str = Field(primary_key=True)
    source: str
    integration: Optional[str]


class ZenStackDefinition(SQLModel, table=True):
    """Join table between Stacks and StackComponents"""

    stack_name: str = Field(primary_key=True, foreign_key="zenstack.name")
    component_type: StackComponentType = Field(
        primary_key=True, foreign_key="zenstackcomponent.component_type"
    )
    component_name: str = Field(
        primary_key=True, foreign_key="zenstackcomponent.name"
    )


class UserTable(User, SQLModel, table=True):
    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)


class TeamTable(Team, SQLModel, table=True):
    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)


class ProjectTable(Project, SQLModel, table=True):
    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    creation_date: datetime = Field(default_factory=datetime.now)


class RoleTable(SQLModel, table=True):
    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    creation_date: datetime = Field(default_factory=datetime.now)
    name: str


class TeamAssignmentTable(SQLModel, table=True):
    user_id: UUID = Field(primary_key=True, foreign_key="usertable.id")
    team_id: UUID = Field(primary_key=True, foreign_key="teamtable.id")


class RoleAssignmentTable(RoleAssignment, SQLModel, table=True):
    id: UUID = Field(primary_key=True, default_factory=_sqlmodel_uuid)
    role_id: UUID = Field(foreign_key="roletable.id")
    user_id: Optional[UUID] = Field(default=None, foreign_key="usertable.id")
    team_id: Optional[UUID] = Field(default=None, foreign_key="teamtable.id")
    project_id: Optional[UUID] = Field(
        default=None, foreign_key="projecttable.id"
    )


class PipelineRunTable(SQLModel, table=True):
    name: str = Field(primary_key=True)
    zenml_version: str
    git_sha: Optional[str]

    pipeline_name: str
    pipeline: str
    stack: str
    runtime_configuration: str

    user_id: UUID = Field(foreign_key="usertable.id")
    project_name: Optional[str] = Field(
        default=None, foreign_key="projecttable.name"
    )

    @classmethod
    def from_pipeline_run_wrapper(
        cls, wrapper: PipelineRunWrapper
    ) -> "PipelineRunTable":
        return PipelineRunTable(
            name=wrapper.name,
            zenml_version=wrapper.zenml_version,
            git_sha=wrapper.git_sha,
            pipeline_name=wrapper.pipeline.name,
            pipeline=wrapper.pipeline.json(),
            stack=wrapper.stack.json(),
            runtime_configuration=json.dumps(wrapper.runtime_configuration),
            user_id=wrapper.user_id,
            project_name=wrapper.project_name,
        )

    def to_pipeline_run_wrapper(self) -> PipelineRunWrapper:
        return PipelineRunWrapper(
            name=self.name,
            zenml_version=self.zenml_version,
            git_sha=self.git_sha,
            pipeline=PipelineWrapper.parse_raw(self.pipeline),
            stack=StackWrapper.parse_raw(self.stack),
            runtime_configuration=json.loads(self.runtime_configuration),
            user_id=self.user_id,
            project_name=self.project_name,
        )


class SqlZenStore(BaseZenStore):
    """Repository Implementation that uses SQL database backend"""

    def initialize(
        self,
        url: str,
        *args: Any,
        **kwargs: Any,
    ) -> "SqlZenStore":
        """Initialize a new SqlZenStore.

        Args:
            url: odbc path to a database.
            args, kwargs: additional parameters for SQLModel.
        Returns:
            The initialized zen store instance.
        """
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL for SQL store: {url}")

        logger.debug("Initializing SqlZenStore at %s", url)
        self._url = url

        local_path = self.get_path_from_url(url)
        if local_path:
            utils.create_dir_recursive_if_not_exists(str(local_path.parent))

        # we need to remove `skip_default_registrations` from the kwargs,
        # because SQLModel will raise an error if it is present
        sql_kwargs = kwargs.copy()
        sql_kwargs.pop("skip_default_registrations", False)
        sql_kwargs.pop("track_analytics", False)
        sql_kwargs.pop("skip_migration", False)
        self.engine = create_engine(url, *args, **sql_kwargs)
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            if not session.exec(select(ZenUser)).first():
                session.add(ZenUser(id=1, name="LocalZenUser"))
            session.commit()

        super().initialize(url, *args, **kwargs)
        return self

    # Public interface implementations:

    @property
    def type(self) -> StoreType:
        """The type of zen store."""
        return StoreType.SQL

    @property
    def url(self) -> str:
        """URL of the repository."""
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
        """
        if not SqlZenStore.is_valid_url(url):
            raise ValueError(f"Invalid URL for SQL store: {url}")
        if not url.startswith("sqlite:///"):
            return None
        url = url.replace("sqlite:///", "")
        return Path(url)

    @staticmethod
    def get_local_url(path: str) -> str:
        """Get a local SQL url for a given local path."""
        return f"sqlite:///{path}/zenml.db"

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if the given url is a valid SQL url."""
        try:
            make_url(url)
        except ArgumentError:
            logger.debug("Invalid SQL URL: %s", url)
            return False

        return True

    @property
    def stacks_empty(self) -> bool:
        """Check if the zen store is empty."""
        with Session(self.engine) as session:
            return session.exec(select(ZenStack)).first() is None

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
                select(ZenStack).where(ZenStack.name == name)
            ).first()
        if maybe_stack is None:
            raise KeyError(
                f"Unable to find stack with name '{name}'. Available names: "
                f"{set(self.stack_names)}."
            )
        # then get all components assigned to that stack
        with Session(self.engine) as session:
            definitions_and_components = session.exec(
                select(ZenStackDefinition, ZenStackComponent)
                .where(
                    ZenStackDefinition.component_type
                    == ZenStackComponent.component_type
                )
                .where(
                    ZenStackDefinition.component_name == ZenStackComponent.name
                )
                .where(ZenStackDefinition.stack_name == name)
            )
            params = {
                component.component_type: component.name
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

    def _register_stack_component(
        self,
        component: ComponentWrapper,
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
                select(ZenStackComponent)
                .where(ZenStackComponent.name == component.name)
                .where(ZenStackComponent.component_type == component.type)
            ).first()
            if existing_component is not None:
                raise StackComponentExistsError(
                    f"Unable to register stack component (type: "
                    f"{component.type}) with name '{component.name}': Found "
                    f"existing stack component with this name."
                )
            new_component = ZenStackComponent(
                component_type=component.type,
                name=component.name,
                component_flavor=component.flavor,
                configuration=component.config,
            )
            session.add(new_component)
            session.commit()

    def _update_stack_component(
        self,
        name: str,
        component_type: StackComponentType,
        component: ComponentWrapper,
    ) -> Dict[str, str]:
        """Update a stack component.

        Args:
            name: The original name of the stack component.
            component_type: The type of the stack component to update.
            component: The new component to update with.

        Raises:
            KeyError: If no stack component exists with the given name.
        """
        with Session(self.engine) as session:
            updated_component = session.exec(
                select(ZenStackComponent)
                .where(ZenStackComponent.component_type == component_type)
                .where(ZenStackComponent.name == name)
            ).first()

            if not updated_component:
                raise KeyError(
                    f"Unable to update stack component (type: "
                    f"{component.type}) with name '{component.name}': No "
                    f"existing stack component found with this name."
                )

            new_name_component = session.exec(
                select(ZenStackComponent)
                .where(ZenStackComponent.component_type == component_type)
                .where(ZenStackComponent.name == component.name)
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

            # rename components inside stacks
            updated_stack_definitions = session.exec(
                select(ZenStackDefinition)
                .where(ZenStackDefinition.component_type == component_type)
                .where(ZenStackDefinition.component_name == name)
            ).all()
            for stack_definition in updated_stack_definitions:
                stack_definition.component_name = component.name
                session.add(stack_definition)

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
                    select(ZenStack).where(ZenStack.name == name)
                ).one()
                session.delete(stack)
            except NoResultFound as error:
                raise KeyError from error
            definitions = session.exec(
                select(ZenStackDefinition).where(
                    ZenStackDefinition.stack_name == name
                )
            ).all()
            for definition in definitions:
                session.delete(definition)
            session.commit()

    # Private interface implementations:

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
                select(ZenStack).where(ZenStack.name == name)
            ).first()
            if stack is None:
                stack = ZenStack(name=name, created_by=1)
                session.add(stack)
            else:
                # clear the existing stack definitions for a stack
                # that is about to be updated
                query = select(ZenStackDefinition).where(
                    ZenStackDefinition.stack_name == name
                )
                for result in session.exec(query).all():
                    session.delete(result)

            for ctype, cname in stack_configuration.items():
                statement = (
                    select(ZenStackDefinition)
                    .where(ZenStackDefinition.stack_name == name)
                    .where(ZenStackDefinition.component_type == ctype)
                )
                results = session.exec(statement)
                component = results.one_or_none()
                if component is None:
                    session.add(
                        ZenStackDefinition(
                            stack_name=name,
                            component_type=ctype,
                            component_name=cname,
                        )
                    )
                else:
                    component.component_name = cname
                    component.component_type = ctype
                    session.add(component)
            session.commit()

    def _get_component_flavor_and_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[str, bytes]:
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
            component = session.exec(
                select(ZenStackComponent)
                .where(ZenStackComponent.component_type == component_type)
                .where(ZenStackComponent.name == name)
            ).one_or_none()
            if component is None:
                raise KeyError(
                    f"Unable to find stack component (type: {component_type}) "
                    f"with name '{name}'."
                )
        return component.component_flavor, component.configuration

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
            statement = select(ZenStackComponent).where(
                ZenStackComponent.component_type == component_type
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
                select(ZenStackComponent)
                .where(ZenStackComponent.component_type == component_type)
                .where(ZenStackComponent.name == name)
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
                for user in session.exec(select(UserTable)).all()
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
                    select(UserTable).where(UserTable.name == user_name)
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
                select(UserTable).where(UserTable.name == user_name)
            ).first()
            if existing_user:
                raise EntityExistsError(
                    f"User with name '{user_name}' already exists."
                )
            sql_user = UserTable(name=user_name)
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
                    select(UserTable).where(UserTable.name == user_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(user)
            session.commit()
            self._delete_query_results(
                select(RoleAssignmentTable).where(
                    RoleAssignmentTable.user_id == user.id
                )
            )
            self._delete_query_results(
                select(TeamAssignmentTable).where(
                    TeamAssignmentTable.user_id == user.id
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
                for team in session.exec(select(TeamTable)).all()
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
                    select(TeamTable).where(TeamTable.name == team_name)
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
                select(TeamTable).where(TeamTable.name == team_name)
            ).first()
            if existing_team:
                raise EntityExistsError(
                    f"Team with name '{team_name}' already exists."
                )
            sql_team = TeamTable(name=team_name)
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
                    select(TeamTable).where(TeamTable.name == team_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(team)
            session.commit()
            self._delete_query_results(
                select(RoleAssignmentTable).where(
                    RoleAssignmentTable.team_id == team.id
                )
            )
            self._delete_query_results(
                select(TeamAssignmentTable).where(
                    TeamAssignmentTable.team_id == team.id
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
                    select(TeamTable).where(TeamTable.name == team_name)
                ).one()
                user = session.exec(
                    select(UserTable).where(UserTable.name == user_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            assignment = TeamAssignmentTable(user_id=user.id, team_id=team.id)
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
                    select(TeamAssignmentTable)
                    .where(TeamAssignmentTable.team_id == TeamTable.id)
                    .where(TeamAssignmentTable.user_id == UserTable.id)
                    .where(UserTable.name == user_name)
                    .where(TeamTable.name == team_name)
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
                for project in session.exec(select(ProjectTable)).all()
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
                    select(ProjectTable).where(
                        ProjectTable.name == project_name
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
                select(ProjectTable).where(ProjectTable.name == project_name)
            ).first()
            if existing_project:
                raise EntityExistsError(
                    f"Project with name '{project_name}' already exists."
                )
            sql_project = ProjectTable(name=project_name)
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
                    select(ProjectTable).where(
                        ProjectTable.name == project_name
                    )
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(project)
            session.commit()
            self._delete_query_results(
                select(RoleAssignmentTable).where(
                    RoleAssignmentTable.project_id == project.id
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
                for role in session.exec(select(RoleTable)).all()
            ]

    @property
    def role_assignments(self) -> List[RoleAssignment]:
        """All registered role assignments.

        Returns:
            A list of all registered role assignments.
        """
        with Session(self.engine) as session:
            return [
                RoleAssignment(**assignment.dict())
                for assignment in session.exec(
                    select(RoleAssignmentTable)
                ).all()
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
                    select(RoleTable).where(RoleTable.name == role_name)
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
                select(RoleTable).where(RoleTable.name == role_name)
            ).first()
            if existing_role:
                raise EntityExistsError(
                    f"Role with name '{role_name}' already exists."
                )
            sql_role = RoleTable(name=role_name)
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
                    select(RoleTable).where(RoleTable.name == role_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            session.delete(role)
            session.commit()
            self._delete_query_results(
                select(RoleAssignmentTable).where(
                    RoleAssignmentTable.role_id == role.id
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
                    select(RoleTable.id).where(RoleTable.name == role_name)
                ).one()

                if project_name:
                    project_id = session.exec(
                        select(ProjectTable.id).where(
                            ProjectTable.name == project_name
                        )
                    ).one()

                if is_user:
                    user_id = session.exec(
                        select(UserTable.id).where(
                            UserTable.name == entity_name
                        )
                    ).one()
                else:
                    team_id = session.exec(
                        select(TeamTable.id).where(
                            TeamTable.name == entity_name
                        )
                    ).one()
            except NoResultFound as error:
                raise KeyError from error

            assignment = RoleAssignmentTable(
                role_id=role_id,
                project_id=project_id,
                user_id=user_id,
                team_id=team_id,
            )
            session.add(assignment)
            session.commit()

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
            statement = (
                select(RoleAssignmentTable)
                .where(RoleAssignmentTable.role_id == RoleTable.id)
                .where(RoleTable.name == role_name)
            )

            if project_name:
                statement = statement.where(
                    RoleAssignmentTable.project_id == ProjectTable.id
                ).where(ProjectTable.name == project_name)

            if is_user:
                statement = statement.where(
                    RoleAssignmentTable.user_id == UserTable.id
                ).where(UserTable.name == entity_name)
            else:
                statement = statement.where(
                    RoleAssignmentTable.team_id == TeamTable.id
                ).where(TeamTable.name == entity_name)

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
                    select(TeamTable.id).where(TeamTable.name == team_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            users = session.exec(
                select(UserTable)
                .where(UserTable.id == TeamAssignmentTable.user_id)
                .where(TeamAssignmentTable.team_id == team_id)
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
                    select(UserTable.id).where(UserTable.name == user_name)
                ).one()
            except NoResultFound as error:
                raise KeyError from error

            teams = session.exec(
                select(TeamTable)
                .where(TeamTable.id == TeamAssignmentTable.team_id)
                .where(TeamAssignmentTable.user_id == user_id)
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
                    select(UserTable.id).where(UserTable.name == user_name)
                ).one()
                statement = select(RoleAssignmentTable).where(
                    RoleAssignmentTable.user_id == user_id
                )
                if project_name:
                    project_id = session.exec(
                        select(ProjectTable.id).where(
                            ProjectTable.name == project_name
                        )
                    ).one()
                    statement = statement.where(
                        RoleAssignmentTable.project_id == project_id
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
                    select(TeamTable.id).where(TeamTable.name == team_name)
                ).one()

                statement = select(RoleAssignmentTable).where(
                    RoleAssignmentTable.team_id == team_id
                )
                if project_name:
                    project_id = session.exec(
                        select(ProjectTable.id).where(
                            ProjectTable.name == project_name
                        )
                    ).one()
                    statement = statement.where(
                        RoleAssignmentTable.project_id == project_id
                    )
            except NoResultFound as error:
                raise KeyError from error

            return [
                RoleAssignment(**assignment.dict())
                for assignment in session.exec(statement).all()
            ]

    # Pipelines and pipeline runs

    def get_pipeline_run(
        self,
        pipeline_name: str,
        run_name: str,
        project_name: Optional[str] = None,
    ) -> PipelineRunWrapper:
        """Gets a pipeline run.

        Args:
            pipeline_name: Name of the pipeline for which to get the run.
            run_name: Name of the pipeline run to get.
            project_name: Optional name of the project from which to get the
                pipeline run.

        Raises:
            KeyError: If no pipeline run (or project) with the given name
                exists.
        """
        with Session(self.engine) as session:
            try:
                statement = (
                    select(PipelineRunTable)
                    .where(PipelineRunTable.name == run_name)
                    .where(PipelineRunTable.pipeline_name == pipeline_name)
                )

                if project_name:
                    statement = statement.where(
                        PipelineRunTable.project_name == project_name
                    )

                run = session.exec(statement).one()
                return run.to_pipeline_run_wrapper()
            except NoResultFound as error:
                raise KeyError from error

    def get_pipeline_runs(
        self, pipeline_name: str, project_name: Optional[str] = None
    ) -> List[PipelineRunWrapper]:
        """Gets pipeline runs.

        Args:
            pipeline_name: Name of the pipeline for which to get runs.
            project_name: Optional name of the project from which to get the
                pipeline runs.
        """
        with Session(self.engine) as session:
            try:
                statement = select(PipelineRunTable).where(
                    PipelineRunTable.pipeline_name == pipeline_name
                )

                if project_name:
                    statement = statement.where(
                        PipelineRunTable.project_name == project_name
                    )
                return [
                    run.to_pipeline_run_wrapper()
                    for run in session.exec(statement).all()
                ]
            except NoResultFound as error:
                raise KeyError from error

    def register_pipeline_run(
        self,
        pipeline_run: PipelineRunWrapper,
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
                select(PipelineRunTable).where(
                    PipelineRunTable.name == pipeline_run.name
                )
            ).first()
            if existing_run:
                raise EntityExistsError(
                    f"Pipeline run with name '{pipeline_run.name}' already"
                    "exists. Please make sure your pipeline run names are "
                    "unique."
                )

            sql_run = PipelineRunTable.from_pipeline_run_wrapper(pipeline_run)
            session.add(sql_run)
            session.commit()

    # Handling stack component flavors

    @property
    def flavors(self) -> List[FlavorWrapper]:
        """All registered flavors.

        Returns:
            A list of all registered flavors.
        """
        with Session(self.engine) as session:
            return [
                FlavorWrapper(**flavor.dict())
                for flavor in session.exec(select(ZenFlavor)).all()
            ]

    def _create_flavor(
        self,
        source: str,
        name: str,
        stack_component_type: StackComponentType,
    ) -> FlavorWrapper:
        """Creates a new flavor.

        Args:
            source: the source path to the implemented flavor.
            name: the name of the flavor.
            stack_component_type: the corresponding StackComponentType.
            integration: the name of the integration.

        Returns:
             The newly created flavor.

        Raises:
            EntityExistsError: If a flavor with the given name and type
                already exists.
        """
        with Session(self.engine) as session:
            existing_flavor = session.exec(
                select(ZenFlavor).where(
                    ZenFlavor.name == name,
                    ZenFlavor.type == stack_component_type,
                )
            ).first()
            if existing_flavor:
                raise EntityExistsError(
                    f"A {stack_component_type} with '{name}' flavor already "
                    f"exists."
                )
            sql_flavor = ZenFlavor(
                name=name,
                source=source,
                type=stack_component_type,
            )
            flavor_wrapper = FlavorWrapper(**sql_flavor.dict())
            session.add(sql_flavor)
            session.commit()
        return flavor_wrapper

    def get_flavors_by_type(
        self, component_type: StackComponentType
    ) -> List[FlavorWrapper]:
        """Fetch all flavor defined for a specific stack component type.

        Args:
            component_type: The type of the stack component.

        Returns:
            List of all the flavors for the given stack component type.
        """
        with Session(self.engine) as session:
            flavors = session.exec(
                select(ZenFlavor).where(ZenFlavor.type == component_type)
            ).all()
        return [
            FlavorWrapper(
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
    ) -> FlavorWrapper:
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
                    select(ZenFlavor).where(
                        ZenFlavor.name == flavor_name,
                        ZenFlavor.type == component_type,
                    )
                ).one()
                return FlavorWrapper(
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
        """Names of all stacks registered in this ZenStore."""
        with Session(self.engine) as session:
            return [s.name for s in session.exec(select(ZenStack))]

    def _delete_query_results(self, query: Any) -> None:
        """Deletes all rows returned by the input query."""
        with Session(self.engine) as session:
            for result in session.exec(query).all():
                session.delete(result)
            session.commit()
