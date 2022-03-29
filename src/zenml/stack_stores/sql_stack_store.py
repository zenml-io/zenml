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
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import ArgumentError
from sqlmodel import Field, Session, SQLModel, create_engine, select

from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import StackComponentExistsError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.stack_stores import BaseStackStore
from zenml.stack_stores.models import StackComponentWrapper

logger = get_logger(__name__)


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


class ZenStackDefinition(SQLModel, table=True):
    """Join table between Stacks and StackComponents"""

    stack_name: str = Field(primary_key=True, foreign_key="zenstack.name")
    component_type: StackComponentType = Field(
        primary_key=True, foreign_key="zenstackcomponent.component_type"
    )
    component_name: str = Field(
        primary_key=True, foreign_key="zenstackcomponent.name"
    )


class SqlStackStore(BaseStackStore):
    """Repository Implementation that uses SQL database backend"""

    def initialize(
        self,
        url: str,
        *args: Any,
        **kwargs: Any,
    ) -> "SqlStackStore":
        """Initialize a new SqlStackStore.

        Args:
            url: odbc path to a database.
            args, kwargs: additional parameters for SQLModel.

        Returns:
            The initialized stack store instance.
        """
        if not self.is_valid_url(url):
            raise ValueError(f"Invalid URL for SQL store: {url}")

        logger.debug("Initializing SqlStackStore at %s", url)
        self._url = url

        local_path = self.get_path_from_url(url)
        if local_path:
            fileio.create_dir_recursive_if_not_exists(str(local_path.parent))

        self.engine = create_engine(url, *args, **kwargs)
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
        """The type of stack store."""
        return StoreType.SQL

    @property
    def url(self) -> str:
        """URL of the repository."""
        if not self._url:
            raise RuntimeError(
                "SQL stack store has not been initialized. Call `initialize` "
                "before using the store."
            )
        return self._url

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
        if not SqlStackStore.is_valid_url(url):
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

    def is_empty(self) -> bool:
        """Check if the stack store is empty."""
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
        """Configuration for all stacks registered in this stack store.

        Returns:
            Dictionary mapping stack names to Dict[StackComponentType, str]
        """
        return {n: self.get_stack_configuration(n) for n in self.stack_names}

    def register_stack_component(
        self,
        component: StackComponentWrapper,
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

    def deregister_stack(self, name: str) -> None:
        """Delete a stack from storage.

        Args:
            name: The name of the stack to be deleted.
        """
        with Session(self.engine) as session:
            stack = session.exec(
                select(ZenStack).where(ZenStack.name == name)
            ).one()
            session.delete(stack)
            definitions = session.exec(
                select(ZenStackDefinition).where(
                    ZenStackDefinition.stack_name == name
                )
            ).all()
            for definition in definitions:
                session.delete(definition)
            session.commit()

    # Private interface implementations:

    def _create_stack(
        self, name: str, stack_configuration: Dict[StackComponentType, str]
    ) -> None:
        """Add a stack to storage.

        Args:
            name: The name to save the stack as.
            stack_configuration: Dict[StackComponentType, str] to persist.
        """
        with Session(self.engine) as session:
            stack = ZenStack(name=name, created_by=1)
            session.add(stack)
            for ctype, cname in stack_configuration.items():
                if cname is not None:
                    session.add(
                        ZenStackDefinition(
                            stack_name=name,
                            component_type=ctype,
                            component_name=cname,
                        )
                    )
            session.commit()

    def _get_component_flavor_and_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[str, bytes]:
        """Fetch the flavor and configuration for a stack component.

        Args:
            component_type: The type of the component to fetch.
            name: The name of the component to fetch.

        Returns:
            Pair of (flavor, congfiguration) for stack component, as string and
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
                logger.info(
                    "Deregistered stack component (type: %s) with name '%s'.",
                    component_type.value,
                    name,
                )
            else:
                logger.warning(
                    "Unable to deregister stack component (type: %s) with name "
                    "'%s': No stack component exists with this name.",
                    component_type.value,
                    name,
                )

    # Implementation-specific internal methods:

    @property
    def stack_names(self) -> List[str]:
        """Names of all stacks registered in this StackStore."""
        with Session(self.engine) as session:
            return [s.name for s in session.exec(select(ZenStack))]
