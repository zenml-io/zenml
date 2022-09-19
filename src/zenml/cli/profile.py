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
"""CLI for migrating legacy ZenML profiles."""

import base64
import os
from collections import defaultdict
from pathlib import Path
from typing import DefaultDict, Dict, Generator, List, Optional
from uuid import UUID

import click
import yaml
from pydantic import BaseModel, Field, validator

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.console import console
from zenml.enums import CliCategories, StackComponentType
from zenml.exceptions import (
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.models import ComponentModel, ProjectModel, StackModel, UserModel
from zenml.models.flavor_models import FlavorModel
from zenml.repository import Repository
from zenml.utils import yaml_utils
from zenml.utils.io_utils import get_global_config_directory

logger = get_logger(__name__)


class FlavorWrapper(BaseModel):
    """Network serializable wrapper.

    This represents the custom implementation of a stack component flavor.
    """

    name: str
    type: str
    source: str
    integration: Optional[str]


class LocalStore(BaseModel):
    """Pydantic object used for serializing a legacy YAML ZenML store.

    Attributes:
        stacks: Maps stack names to a configuration object containing the
            names and flavors of all stack components.
        stack_components: Contains names and flavors of all registered stack
            components.
        stack_component_flavors: Contains the flavor definitions of each
            stack component type
    """

    stacks: Dict[str, Dict[str, str]] = Field(default_factory=dict)
    stack_components: DefaultDict[str, Dict[str, str]] = Field(
        default=defaultdict(dict)
    )
    stack_component_flavors: List[FlavorWrapper] = Field(default_factory=list)

    _config_file: str

    @validator("stack_components")
    def _construct_stack_components_defaultdict(
        cls, stack_components: Dict[str, Dict[str, str]]
    ) -> DefaultDict[str, Dict[str, str]]:
        """Ensures that `stack_components` is a defaultdict.

        This is so stack components of a new component type can be added without
        issues.

        Args:
            stack_components: the dictionary of stack components

        Returns:
            Stack components dictionary.
        """
        return defaultdict(dict, stack_components)

    def __init__(self, config_file: str) -> None:
        """Create a local store instance initialized from a configuration file on disk.

        Args:
            config_file: configuration file path. If the file exists, the model
                will be initialized with the values from the file.
        """
        config_dict = {}
        if fileio.exists(config_file):
            config_dict = yaml_utils.read_yaml(config_file)

        self._config_file = config_file
        super().__init__(**config_dict)

    def _get_stack_component_config_path(
        self, component_type: str, name: str
    ) -> str:
        """Path to the configuration file of a stack component.

        Args:
            component_type: The type of the stack component.
            name: The name of the stack component.

        Returns:
            The path to the configuration file of the stack component.
        """
        subpath = f"{component_type}s"
        if component_type == StackComponentType.CONTAINER_REGISTRY:
            subpath = "container_registries"

        path = self.root / subpath / f"{name}.yaml"
        return str(path)

    def get_component(
        self, component_type: str, name: str, prefix: str = ""
    ) -> ComponentModel:
        """Fetch the flavor and configuration for a stack component.

        Args:
            component_type: The type of the component to fetch.
            name: The name of the component to fetch.
            prefix: Optional name prefix to use for the returned component.

        Returns:
            A component model for the stack component, containing the component
            information.

        Raises:
            KeyError: If no stack component exists for the given type and name.
        """
        components: Dict[str, str] = self.stack_components[component_type]
        if name not in components:
            raise KeyError(
                f"Unable to find stack component (type: {component_type}) "
                f"with name '{name}'. Available names: {set(components)}."
            )

        component_config_path = self._get_stack_component_config_path(
            component_type=component_type, name=name
        )
        flavor = components[name]
        config_dict = yaml_utils.read_yaml(component_config_path)
        component_name = (prefix + name) if name != "default" else name
        config_dict["name"] = component_name
        # TODO: [server] The Model needs to also set user and project correctly
        return ComponentModel(
            type=component_type,
            name=component_name,
            flavor=flavor,
            id=UUID(config_dict["uuid"]),
            configuration=base64.b64encode(yaml.dump(config_dict).encode()),
        )

    def get_components(self, prefix: str = "") -> List[ComponentModel]:
        """Fetch all stack components.

        The default components are expressly excluded from this list.

        Args:
            prefix: Optional name prefix to use for the returned components.

        Returns:
            A list of component models for all stack components.
        """
        components: List[ComponentModel] = []
        for component_type in self.stack_components:
            if component_type == "metadata_store":
                continue
            for name in self.stack_components[component_type]:
                if name == "default" and component_type in [
                    StackComponentType.ARTIFACT_STORE,
                    StackComponentType.ORCHESTRATOR,
                ]:
                    continue
                components.append(
                    self.get_component(component_type, name, prefix)
                )
        return components

    def get_stack(
        self, name: str, prefix: str = "", project: Optional[str] = None
    ) -> StackModel:
        """Fetch the configuration for a stack.

        For default stack components, the default component in the current
        store is used instead of the one in the legacy profile.

        Args:
            name: The name of the stack to fetch.
            prefix: Optional name prefix to use for the returned stack and its
                components (unless default).
            project: Optional project name to use to fetch the default stack to
                replace the default components in the stack.

        Returns:
            A stack model for the stack.

        Raises:
            KeyError: If no stack exists with the given name.
        """
        stack = self.stacks.get(name)
        if not stack:
            raise KeyError(
                f"Unable to find stack with name '{name}'. Available names: "
                f"{set(self.stacks)}."
            )

        components: Dict[StackComponentType, ComponentModel] = {}
        for component_type, component_name in stack.items():
            if component_type == "metadata_store":
                continue
            component: ComponentModel = self.get_component(
                component_type, component_name, prefix
            )
            if (
                component_name == "default"
                and project
                and component_type
                in [
                    StackComponentType.ARTIFACT_STORE,
                    StackComponentType.ORCHESTRATOR,
                ]
            ):
                zen_store = Repository().zen_store
                # use the component in the active store
                # TODO: [server] make sure this is the intended use
                #  of _get_default_stack
                component = (
                    zen_store._get_default_stack(
                        project_name_or_id=project,
                        user_name_or_id=zen_store.active_user.id,
                    )
                    .to_hydrated_model()
                    .components[StackComponentType(component_type)][0]
                )

            components[StackComponentType(component_type)] = component

        return StackModel(
            name=prefix + name,
            components=components,
            project=project,
        )

    def get_stacks(
        self, prefix: str = "", project: Optional[str] = None
    ) -> List[StackModel]:
        """Fetch all stacks.

        The default stack is expressly excluded from this list.

        Args:
            prefix: Optional name prefix to use for the returned stack and
                stack components.
            project: Optional project name to use to fetch the default stack to
                replace the default components in the stack.

        Returns:
            A list of stack configurations.
        """
        return [
            self.get_stack(name, prefix, project)
            for name in self.stacks
            if name != "default"
        ]

    @property
    def root(self) -> Path:
        """The root directory of the zen store.

        Returns:
            The root directory of the zen store.
        """
        return Path(self._config_file).parent

    def is_empty(self) -> bool:
        """Check if the store is empty.

        Returns:
            True if the store is empty, False otherwise.
        """
        return (
            not self.contains_stacks()
            and not self.contains_stack_components()
            and not len(self.stack_component_flavors)
        )

    def contains_stacks(self) -> bool:
        """Check if the store contains stacks.

        The default stack is expressly excluded from this check.

        Returns:
            True if the store contains stacks, False otherwise.
        """
        return len(self.get_stacks()) > 0

    def contains_stack_components(self) -> bool:
        """Check if the store contains stack components.

        The default stack components are expressly excluded from this check.

        Returns:
            True if the store contains stack components, False otherwise.
        """
        return len(self.get_components()) > 0

    @property
    def config_file(self) -> str:
        """Return the path to the configuration file.

        Returns:
            The path to the configuration file.
        """
        return self._config_file

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes from configs of previous ZenML versions
        extra = "ignore"
        # all attributes with leading underscore are private and therefore
        # are mutable and not included in serialization
        underscore_attrs_are_private = True


def find_profiles(
    path: Optional[str],
) -> Generator[LocalStore, None, None]:
    """Find all local profiles in a directory.

    Point this function to a global config directory or a single profile
    directory to find and load all profiles stored there.

    Args:
        path: The path to search for profiles. If None, the global config
            directory is used.

    Yields:
        A local profile store.
    """
    dirs: List[str] = []
    if path is None:
        path = get_global_config_directory()
    if os.path.isdir(os.path.join(path, "profiles")):
        path = os.path.join(path, "profiles")
        dirs = [os.path.join(path, f) for f in os.listdir(path)]
    else:
        dirs = [path]
    for dir in dirs:
        if os.path.isfile(os.path.join(dir, "stacks.yaml")):
            store = LocalStore(os.path.join(dir, "stacks.yaml"))
            if store.is_empty():
                continue
            yield store


@cli.group(
    cls=TagGroup,
    tag=CliCategories.MANAGEMENT_TOOLS,
    help="Manage legacy profiles",
)
def profile() -> None:
    """Commands for managing legacy profiles."""


@profile.command("list", help="Find and list legacy profiles.")
@click.option("--path", type=str, default=None)
def list_profiles(
    path: Optional[str],
) -> None:
    """Find and list legacy ZenML profiles.

    Args:
        path: Custom path where to look for profiles. The current global
            configuration path is used if not set.
    """
    Repository()
    cli_utils.warning(
        "ZenML profiles have been deprecated and removed in this version of "
        "ZenML. All stacks, stack components, flavors etc. are now stored "
        "and managed globally, either in a local database or on a remote ZenML "
        "server (see the `zenml config` command). As alternatives, you can use "
        "different global configuration paths by setting the `ZENML_CONFIG_PATH` "
        "environment variable to point to a different location, or use projects "
        "as a scoping mechanism for stack and stack components.\n\n"
        "The information stored in legacy profiles is not automatically "
        "migrated. You can do so manually by using the `zenml profile list` and "
        "`zenml profile migrate` commands."
    )
    profiles_found = False
    for store in find_profiles(path):
        console.print(
            f"Found profile with {len(store.stacks)} stacks, "
            f"{len(store.stack_components)} components and "
            f"{len(store.stack_component_flavors)} flavors at: "
            f"{os.path.dirname(store.config_file)}"
        )
        profiles_found = True
    if not profiles_found:
        console.print("No profiles found.")


@profile.command(
    "migrate",
    help="Migrate stacks, components and flavors from a legacy profile.",
)
@click.option(
    "--stacks",
    is_flag=True,
    help="Migrate stacks and stack components from the profile.",
    type=click.BOOL,
)
@click.option(
    "--flavors",
    is_flag=True,
    help="Migrate flavors from the profile.",
    type=click.BOOL,
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Overwrite the existing stacks, stack components and flavors.",
    type=click.BOOL,
)
@click.option(
    "--ignore-errors",
    is_flag=True,
    help=(
        "Continue the migration process if an error is encountered for a "
        "particular entry."
    ),
    type=click.BOOL,
)
@click.option(
    "--prefix",
    type=str,
    default="",
    help=(
        "Use a prefix for the names of migrated stacks, stack components and "
        "flavors."
    ),
)
@click.option(
    "--project",
    "project_name",
    type=str,
    default=None,
    help=(
        "Migrate the stacks, components and flavors to a custom project. If the "
        "project does not exist, it will be created."
    ),
)
@click.argument("profile_path", type=click.STRING)
def migrate_profiles(
    stacks: bool,
    flavors: bool,
    overwrite: bool,
    ignore_errors: bool,
    prefix: str,
    profile_path: str,
    project_name: Optional[str],
) -> None:
    """Migrate stacks, stack components and flavors from a legacy profile.

    Args:
        stacks: Migrate stacks and stack components from the profile.
        flavors: Migrate flavors from the profile.
        overwrite: Overwrite the existing stacks, stack components and flavors.
        ignore_errors: Continue the import process if an error is encountered.
        prefix: Use a prefix for the names of imported stacks, stack components and
            flavors.
        profile_path: Path where the profile files are located.
        project_name: Migrate the stacks, components and flavors to a custom
            project.
    """
    # flake8: noqa: C901
    stores = list(find_profiles(profile_path))
    if not stores:
        cli_utils.error(f"No profiles found at {profile_path}.")
    if len(stores) > 1:
        cli_utils.error(
            f"Found {len(stores)} profiles at {profile_path}. "
            "Please specify a single profile."
        )
    if not stacks and not flavors:
        stacks = flavors = True
    store = stores[0]

    repo = Repository()
    project: Optional[ProjectModel] = None
    if project_name:
        try:
            project = repo.zen_store.get_project(project_name)
        except KeyError:
            cli_utils.declare(f"Creating project {project_name}")
            project = repo.zen_store.create_project(
                ProjectModel(
                    name=project_name,
                    description=(
                        f"Legacy profile migration for profile "
                        f"{os.path.basename(profile_path)}"
                    ),
                )
            )
    else:
        project = repo.active_project

    if not project:
        cli_utils.error("No active project found.")

    user: UserModel = repo.zen_store.active_user
    assert user.id is not None

    if flavors:
        if not store.stack_component_flavors:
            cli_utils.declare(
                f"No component flavors to migrate from {store.config_file}..."
            )
        else:
            cli_utils.declare(
                f"Migrating component flavors from {store.config_file}..."
            )
            for flavor in store.stack_component_flavors:
                name = f"{prefix}{flavor.name}"
                try:
                    repo.zen_store.create_flavor(
                        FlavorModel(
                            source=flavor.source,
                            name=name,
                            type=StackComponentType(flavor.type),
                        )
                    )
                    cli_utils.declare(f"Migrated component flavor '{name}'.")
                except EntityExistsError:
                    msg = (
                        f"Cannot migrate component flavor '{name}. It already "
                        f"exists."
                    )
                    if ignore_errors:
                        cli_utils.warning(msg)
                    else:
                        cli_utils.error(msg)

    if stacks:
        if not store.contains_stack_components():
            cli_utils.declare(
                f"No stack components to migrate from {store.config_file}..."
            )
        else:
            cli_utils.declare(
                f"Migrating stack components from {store.config_file}..."
            )
            for component in store.get_components(
                prefix=prefix,
                project=project.name,
            ):
                try:
                    repo.zen_store.create_stack_component(
                        user_name_or_id=user.id,
                        project_name_or_id=project.name,
                        component=component,
                    )
                    cli_utils.declare(
                        f"Migrated {component.type} '{component.name}' with "
                        f"flavor '{component.flavor_id}'."
                    )
                except StackComponentExistsError:
                    if overwrite:
                        component.user = user.id
                        component.project = project.id
                        repo.zen_store.update_stack_component(
                            component=component,
                        )
                        cli_utils.declare(
                            f"Updated {component.type} '{component.name}' with "
                            f"flavor '{component.flavor}'."
                        )
                    else:
                        msg = (
                            f"Cannot migrate {component.type} "
                            f"'{component.name}'. It already exists."
                        )
                        if ignore_errors:
                            cli_utils.warning(msg)
                        else:
                            cli_utils.error(msg)

        if not store.contains_stacks():
            cli_utils.declare(
                f"No stacks to migrate from {store.config_file}..."
            )
        else:
            cli_utils.declare(f"Migrating stacks from {store.config_file}...")
            for stack in store.get_stacks(prefix=prefix, project=project.name):
                try:
                    stack.project = project.id
                    stack.user = user.id
                    repo.zen_store.create_stack(stack)
                    cli_utils.declare(f"Migrated stack '{stack.name}'.")
                except StackExistsError:
                    if overwrite:
                        assert stack.id is not None
                        stack.project_id = project.id
                        stack.owner = user.id
                        repo.zen_store.update_stack(
                            stack=stack,
                        )
                        cli_utils.declare(f"Updated stack '{stack.name}'.")
                    else:
                        msg = (
                            f"Cannot migrate stack '{stack.name}'. It already "
                            f"exists."
                        )
                        if ignore_errors:
                            cli_utils.warning(msg)
                        else:
                            cli_utils.error(msg)
