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

import os
from collections import defaultdict
from pathlib import Path
from typing import (
    TYPE_CHECKING,
    Any,
    DefaultDict,
    Dict,
    Generator,
    List,
    Optional,
    Tuple,
)
from uuid import UUID

import click
from pydantic import BaseModel, Field
from pydantic import ValidationError as PydanticValidationError
from pydantic import validator

from zenml.cli import utils as cli_utils
from zenml.cli.cli import TagGroup, cli
from zenml.client import Client
from zenml.console import console
from zenml.enums import CliCategories, StackComponentType
from zenml.exceptions import EntityExistsError, ValidationError
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.utils import yaml_utils
from zenml.utils.io_utils import get_global_config_directory

if TYPE_CHECKING:
    from zenml.models import ComponentModel, StackModel

logger = get_logger(__name__)


class LegacyFlavorModel(BaseModel):
    """Legacy flavor model."""

    name: str
    type: str
    source: str
    integration: Optional[str]


class LegacyComponentModel(BaseModel):
    """Legacy stack component model."""

    name: str
    type: StackComponentType
    flavor: str
    configuration: Dict[str, Any]

    def to_model(self, project_id: UUID, user_id: UUID) -> "ComponentModel":
        """Converts to a component model.

        Args:
            project_id: The project id.
            user_id: The user id.

        Returns:
            The component model.
        """
        from zenml.models import ComponentModel

        return ComponentModel(
            name=self.name,
            type=self.type,
            flavor=self.flavor,
            configuration=self.configuration,
            project=project_id,
            user=user_id,
        )


class LegacyStackModel(BaseModel):
    """Legacy stack model."""

    name: str
    components: Dict[StackComponentType, str]

    def to_model(
        self,
        project_id: UUID,
        user_id: UUID,
        components: List["ComponentModel"],
    ) -> "StackModel":
        """Converts to a stack model.

        Args:
            project_id: The project id.
            user_id: The user id.
            components: The components that are part of the stack.

        Returns:
            The stack model.
        """
        from zenml.models import StackModel

        return StackModel(
            name=self.name,
            components={c.type: [c.id] for c in components},
            project=project_id,
            user=user_id,
        )


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
    stack_component_flavors: List[LegacyFlavorModel] = Field(
        default_factory=list
    )

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
        """Create a local store instance from a configuration file on disk.

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
        self,
        component_type: str,
        name: str,
        prefix: str = "",
    ) -> LegacyComponentModel:
        """Fetch the flavor and configuration for a stack component.

        Args:
            component_type: The type of the component to fetch.
            name: The name of the component to fetch.
            prefix: Optional name prefix to use for the returned component.

        Returns:
            A legacy component model for the stack component.

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
        config_dict: Dict[str, Any] = yaml_utils.read_yaml(
            component_config_path
        )
        component_name = (prefix + name) if name != "default" else name
        config_dict.pop("uuid")
        config_dict.pop("name")
        # filter out empty values to avoid validation errors
        config_dict = dict(
            filter(lambda x: x[1] is not None, config_dict.items())
        )

        return LegacyComponentModel(
            name=component_name,
            type=component_type,
            flavor=flavor,
            configuration=config_dict,
        )

    def get_components(self, prefix: str = "") -> List[LegacyComponentModel]:
        """Fetch all stack components.

        The default components are expressly excluded from this list.

        Args:
            prefix: Optional name prefix to use for the returned components.

        Returns:
            A list of component models for all stack components.
        """
        components: List[LegacyComponentModel] = []
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
                    self.get_component(
                        component_type,
                        name,
                        prefix=prefix,
                    )
                )
        return components

    def get_stack(self, name: str, prefix: str = "") -> LegacyStackModel:
        """Fetch the configuration for a stack.

        For default stack components, the default component in the current
        store is used instead of the one in the legacy profile.

        Args:
            name: The name of the stack to fetch.
            prefix: Optional name prefix to use for the returned stack and its
                components (unless default).

        Returns:
            A legacy stack model for the stack.

        Raises:
            KeyError: If no stack exists with the given name.
        """
        stack = self.stacks.get(name)
        if not stack:
            raise KeyError(
                f"Unable to find stack with name '{name}'. Available names: "
                f"{set(self.stacks)}."
            )

        components: Dict[StackComponentType, str] = {}
        for component_type, component_name in stack.items():
            if component_type == "metadata_store":
                continue
            components[StackComponentType(component_type)] = (
                (prefix + component_name)
                if component_name != "default"
                else component_name
            )

        return LegacyStackModel(
            name=prefix + name,
            components=components,
        )

    def get_stacks(self, prefix: str = "") -> List[LegacyStackModel]:
        """Fetch all stacks.

        The default stack is expressly excluded from this list.

        Args:
            prefix: Optional name prefix to use for the returned stack and
                stack components.

        Returns:
            A list of stacks.
        """
        return [
            self.get_stack(name, prefix=prefix)
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
        Client()
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
    Client()
    cli_utils.warning(
        "ZenML profiles have been deprecated and removed in this version of "
        "ZenML. All stacks, stack components, flavors etc. are now stored "
        "and managed globally, either in a local database or on a remote ZenML "
        "server (see the `zenml up` and `zenml connect` commands). As an "
        "alternative to profiles, you can use projects as a scoping mechanism "
        "for stacks, stack components and other ZenML objects.\n\n"
        "The information stored in legacy profiles is not automatically "
        "migrated. You can do so manually by using the `zenml profile list` "
        "and `zenml profile migrate` commands."
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
    help="""Migrate stacks, components and flavors from a legacy profile. 
    
    Use this command to import the stacks, stack components and flavors from a
    legacy profile path into the active project or a specified project.

    If no project is specified, the active project is used. A different project
    can be specified with the `--project` argument and the project will be
    created if it does not exist yet.
    
    If your migrated stack components have configurations that are no longer
    valid, you can pass the `--skip-validation` flag to import them anyway.
    The invalid configurations can be fixed manually afterwards by using the
    `zenml <component-type> update` and 
    `zenml <component-type> remove-attribute` commands.

    To avoid name clashes, you can specify a prefix value that will be prepended
    to the names of all migrated stacks, stack components and flavors.
    Alternatively, you can pass the `--overwrite` flag to overwrite existing
    objects.
    """,
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
    help="Continue the migration process if an error is encountered for a "
    "particular entry.",
    type=click.BOOL,
)
@click.option(
    "--skip-validation",
    is_flag=True,
    help="Don't validate the migrated stack component configurations.",
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
    help="Migrate the stacks, components and flavors to a custom project. "
    "If the project does not exist, it will be created.",
)
@click.argument("profile_path", type=click.STRING)
def migrate_profiles(
    stacks: bool,
    flavors: bool,
    overwrite: bool,
    ignore_errors: bool,
    skip_validation: bool,
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
        skip_validation: Don't validate the migrated stack component
            configurations.
        prefix: Use a prefix for the names of imported stacks, stack components
            and flavors.
        profile_path: Path where the profile files are located.
        project_name: Migrate the stacks, components and flavors to a custom
            project.

    Raises:
        PydanticValidationError: If a migrated stack component configuration
            is invalid.
        ValidationError: If a migrated stack or stack component is invalid.
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

    client = Client()
    user = client.active_user
    if project_name:
        try:
            project = client.zen_store.get_project(project_name)
        except KeyError:
            cli_utils.declare(f"Creating project {project_name}")
            from zenml.models import ProjectModel

            project = client.zen_store.create_project(
                ProjectModel(
                    name=project_name,
                    description=(
                        f"Legacy profile migration for profile "
                        f"{os.path.basename(profile_path)}"
                    ),
                )
            )
            client.zen_store._create_default_stack(
                project_name_or_id=project_name,
                user_name_or_id=user.id,
            )
    else:
        project = client.active_project

    if not project:
        cli_utils.error("No active project found.")

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
                    from zenml.models import FlavorModel

                    client.zen_store.create_flavor(
                        FlavorModel(
                            source=flavor.source,
                            name=name,
                            type=StackComponentType(flavor.type),
                            user=user.id,
                            project=project.id,
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
                except Exception as e:
                    msg = f"Failed to migrate component flavor '{name}': {e}"
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
            for legacy_component in store.get_components(prefix=prefix):
                component = legacy_component.to_model(
                    user_id=user.id, project_id=project.id
                )

                existing_components = client.zen_store.list_stack_components(
                    project_name_or_id=project.id,
                    user_name_or_id=user.id,
                    type=legacy_component.type,
                    name=legacy_component.name,
                    is_shared=False,
                )

                if existing_components:
                    if not overwrite:
                        msg = (
                            f"Cannot migrate stack component "
                            f"'{component.name}'. It already exists."
                        )
                        if ignore_errors:
                            cli_utils.warning(msg)
                        else:
                            cli_utils.error(msg)
                        continue
                    component.id = existing_components[0].id

                try:
                    try:
                        if not existing_components:
                            client.register_stack_component(component=component)
                        else:
                            client.update_stack_component(component=component)
                    except (ValidationError, PydanticValidationError) as e:
                        if not skip_validation:
                            raise e
                        cli_utils.warning(
                            f"Validation error ignored while migrating "
                            f"{component.type} '{component.name}': {e}"
                        )
                        if not existing_components:
                            client.zen_store.create_stack_component(
                                component=component
                            )
                        else:
                            client.zen_store.update_stack_component(
                                component=component
                            )
                    operation = "Migrated" if existing_components else "Created"
                    cli_utils.declare(
                        f"{operation} {component.type} '{component.name}' with "
                        f"flavor '{component.flavor}'."
                    )
                except Exception as e:
                    msg = (
                        f"Failed to migrate {component.type} "
                        f"'{component.name}': {e}"
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
            for legacy_stack in store.get_stacks(prefix=prefix):

                # resolve components
                missing_components: List[Tuple[StackComponentType, str]] = []
                components: List["ComponentModel"] = []
                for c_type, name in legacy_stack.components.items():
                    existing_components = (
                        client.zen_store.list_stack_components(
                            project_name_or_id=project.id,
                            user_name_or_id=user.id,
                            name=name,
                            type=c_type,
                            is_shared=False,
                        )
                    )
                    if not existing_components:
                        missing_components.append((c_type, name))
                        continue

                    components.append(existing_components[0])

                if missing_components:
                    missing_msg = ", ".join(
                        f"{c_type} '{name}'"
                        for c_type, name in missing_components
                    )
                    msg = (
                        f"Cannot migrate stack '{legacy_stack.name}'. The "
                        f"following components could not be found: "
                        f"{missing_msg}"
                    )
                    if ignore_errors:
                        cli_utils.warning(msg)
                    else:
                        cli_utils.error(msg)
                    continue

                stack = legacy_stack.to_model(
                    user_id=user.id,
                    project_id=project.id,
                    components=components,
                )

                existing_stacks = client.zen_store.list_stacks(
                    project_name_or_id=project.id,
                    user_name_or_id=user.id,
                    name=legacy_stack.name,
                    is_shared=False,
                )

                if existing_stacks:
                    if not overwrite:
                        msg = (
                            f"Cannot migrate stack "
                            f"'{stack.name}'. It already exists."
                        )
                        if ignore_errors:
                            cli_utils.warning(msg)
                        else:
                            cli_utils.error(msg)
                        continue
                    stack.id = existing_stacks[0].id

                try:
                    try:
                        if not existing_stacks:
                            client.register_stack(stack=stack)
                        else:
                            client.update_stack(stack=stack)
                    except (ValidationError, PydanticValidationError) as e:
                        if not skip_validation:
                            raise e
                        cli_utils.warning(
                            f"Validation error encountered while migrating "
                            f"stack '{stack.name}': {e}"
                        )
                        if not existing_stacks:
                            client.zen_store.create_stack(stack=stack)
                        else:
                            client.zen_store.update_stack(stack=stack)

                    operation = "Updated" if existing_stacks else "Created"
                    cli_utils.declare(f"{operation} stack '{stack.name}'.")
                except Exception as e:
                    msg = f"Failed to migrate stack '{stack.name}': {e}"
                    if ignore_errors:
                        cli_utils.warning(msg)
                    else:
                        cli_utils.error(msg)
