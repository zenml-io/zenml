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

# type: ignore
# ^ this is needed here in order to keep SQLModel from blowing up mypy.
# TODO[HIGH]: Get mypy working on SQLModel. Currently the entire file must be
#  ignored.

import base64
import datetime as dt
import json
from typing import Any, Dict, List, Optional, Tuple

import yaml
from sqlmodel import Field, Session, SQLModel, create_engine, select

from zenml import __version__
from zenml.enums import StackComponentFlavor, StackComponentType
from zenml.exceptions import StackComponentExistsError
from zenml.logger import get_logger
from zenml.stack import StackComponent
from zenml.stack_stores import BaseStackStore
from zenml.stack_stores.models import StackConfiguration

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


class ZenConfig(SQLModel, table=True):
    """ "Singleton" Table with only one row storing config."""

    create_time: Optional[dt.datetime] = Field(
        default_factory=dt.datetime.now, primary_key=True
    )
    version: str
    active_stack: Optional[str]


class SqlStackStore(BaseStackStore):
    """Repository Implementation that uses SQL database backend"""

    def __init__(self, url: str, *args, **kwargs) -> None:
        """Create a new SqlStackStore.

        Args:
            url: odbc path to a database.
        """

        logger.debug("Initializing SqlStackStore at %s", url)
        self.engine = create_engine(url, *args, **kwargs)
        SQLModel.metadata.create_all(self.engine)
        with Session(self.engine) as session:
            if not session.exec(select(ZenConfig)).first():
                session.add(ZenConfig(version=__version__))
            if not session.exec(select(ZenUser)).first():
                session.add(ZenUser(id=1, name="LocalZenUser"))
            session.commit()

    """ Interface: """

    @property
    def version(self) -> str:
        """The version of the repository."""
        with Session(self.engine) as session:
            conf = session.exec(select(ZenConfig)).one()
        return conf.version

    @property
    def active_stack_name(self) -> str:
        """The name of the active stack for this repository."""
        with Session(self.engine) as session:
            conf = session.exec(select(ZenConfig)).first()
        if conf.active_stack is None:
            raise RuntimeError("No active stack")
        return conf.active_stack

    def activate_stack(self, name: str) -> None:
        """Activates the stack for the given name."""
        # modify the single row of ZenConfig in place
        with Session(self.engine) as session:
            conf = session.exec(select(ZenConfig)).one()
            _ = self.get_stack(name)
            conf.active_stack = name
            session.add(conf)
            session.commit()

    def get_stack_configuration(self, name: str) -> StackConfiguration:
        """Fetches a stack.

        Args:
            name: The name of the stack to fetch.

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
                    == ZenStackDefinition.component_type
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
        # finally build a StackConfiguration object from them
        return StackConfiguration(**params)

    @property
    def stack_configurations(self) -> Dict[str, StackConfiguration]:
        """Configuration for all stacks registered in this repository."""
        return {n: self.get_stack_configuration(n) for n in self.stack_names}

    def create_stack(
        self, name: str, stack_configuration: StackConfiguration
    ) -> None:
        with Session(self.engine) as session:
            stack = ZenStack(name=name, created_by=1)
            session.add(stack)
            for ctype, cname in stack_configuration.dict().items():
                if cname is not None:
                    session.add(
                        ZenStackDefinition(
                            stack_name=name,
                            component_type=ctype,  # TODO: should be enum, will this work?
                            component_name=cname,
                        )
                    )
            session.commit()

    def delete_stack(self, name: str) -> None:
        with Session(self.engine) as session:
            stack = session.exec(
                select(ZenStack).where(ZenStack.name == name)
            ).one()
            session.delete(stack)
            session.commit()

    def get_component_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[StackComponentFlavor, Any]:
        """Fetch the flavor and configuration for a stack component."""
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
        config = yaml.safe_load(
            base64.b64decode(component.configuration).decode()
        )
        flavor = StackComponentFlavor.for_type(component_type)(
            component.component_flavor
        )
        return flavor, config

    def get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type."""
        with Session(self.engine) as session:
            statement = select(ZenStackComponent).where(
                ZenStackComponent.component_type == component_type
            )
            return [component.name for component in session.exec(statement)]

    def register_stack_component(
        self,
        component: StackComponent,
    ) -> None:
        """Register a stack component"""
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
            config = base64.b64encode(
                yaml.dump(json.loads(component.json())).encode()
            )
            new_component = ZenStackComponent(
                component_type=component.type,
                name=component.name,
                component_flavor=component.flavor.value,
                configuration=config,
            )
            session.add(new_component)
            session.commit()

    def delete_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Delete a stack component."""
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

    """ Implementation-specific methods: """

    @property
    def stack_names(self) -> List[str]:
        """Names of all stacks registered in this repository."""
        with Session(self.engine) as session:
            return [s.name for s in session.exec(select(ZenStack))]
