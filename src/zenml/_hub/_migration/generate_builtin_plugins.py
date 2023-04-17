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
import inspect
import logging
import os
from enum import Enum
from importlib import import_module
from typing import List, Set

from pydantic import BaseModel

from zenml.integrations.integration import Integration
from zenml.steps import BaseStep
from zenml.utils.yaml_utils import write_yaml


class EntityTypes(Enum):
    """Enum for all base entity types."""

    steps = BaseStep

    # materializers: ...
    # flavors: ...

    @classmethod
    def values(cls):
        """Helper method to return all the values."""
        return list(map(lambda c: c.value, cls))


class Plugin(BaseModel):
    """Base model for ZenML Hub Plugin submissions.

    Attributes:
        name: name of the plugin
        src: source paths for implemented entities
        requirements: list of requirements
        logo: URL of the logo
        description: the description of the plugin
        tags: tags associated with the plugin
    """

    name: str
    src: List[str] = []
    requirements: List[str] = []
    logo: str = ""
    description: str = ""
    tags: List[str] = []


def scan_entities(main_module) -> Set[str]:
    """Scanning the module at the given path for ZenML entities.

    Args:
        main_module: The module object.

    Returns:
        list of entities
    """
    entities = set()

    # Walk over the main module
    module_root = os.path.dirname(str(main_module.__file__))
    for root, dirs, files in os.walk(module_root):

        # Skip the pycache folders if they exist
        if root.endswith("__pycache__"):
            continue

        # Go over each file
        for file in files:

            # Skip the non-".py" files
            file_path = os.path.join(root, file)
            if not file_path.endswith(".py"):
                continue

            # Forge the source path
            #
            # Examples:
            #   module.__name__ -> zenml.integrations.X
            #   module_root -> /path/to/zenml/integrations/X
            #   file_path -> /path/to/zenml/integrations/X/steps/my_step.py
            #   path -> zenml.integrations.X.steps.my_step
            #
            #   final_result -> zenml.integrations.X.my_step.MyStep
            path = (
                main_module.__name__
                + "."
                + file_path.replace(module_root, "")
                .replace(".py", "")
                .lstrip("/")
                .replace("/", ".")
            )
            module = import_module(path)

            # Find classes in different modules that are subclasses of
            # different entities.
            for name, cls in inspect.getmembers(module, inspect.isclass):
                if (
                    issubclass(cls, EntityTypes.steps.value)
                    and cls != EntityTypes.steps.value
                ):
                    # entities.add(f"{cls.__module__}.{cls.__name__}")
                    entities.add(file_path)
    return entities


def get_integration_plugins() -> List[Plugin]:
    """Get all the relevant plugins from ZenML integrations.

    Returns:
        list of all plugins
    """
    # Get the root of all integration implementations
    from zenml import integrations

    integrations_root = os.path.dirname(integrations.__file__)

    # Get the names of the integration directories
    _, integration_dirs, _ = next(os.walk(integrations_root))
    integration_dirs.remove("__pycache__")

    # Generate a plugin for each integration
    plugins = []
    for integration in integration_dirs:
        integration_plugin = Plugin(
            name=f"{integration}_steps",
            description=f'Steps using the ZenML integration "{integration}".',
        )
        try:
            # Import the integration and extract the requirements
            module = import_module(f"zenml.integrations.{integration}")

            for name, cls in inspect.getmembers(module, inspect.isclass):
                if issubclass(cls, Integration) and cls != Integration:
                    integration_plugin.requirements = cls.REQUIREMENTS

                    # TODO: Implement a better way to extract the logo url
                    flavors = cls.flavors()
                    if flavors:
                        flavor_sample = flavors[0]()
                        integration_plugin.logo = flavor_sample.logo_url
                    break

            # Fetch all the implementations that subclass base entities
            entities = scan_entities(module)
            if entities:
                integration_plugin.src = list(entities)
                plugins.append(integration_plugin)

        except (ModuleNotFoundError, ImportError) as e:
            logging.debug(
                f"{integration} integration can not be properly imported: {e}"
            )

    return plugins


def scan_zenml_entities() -> List[Plugin]:
    """Scan and generate a plugin for all ZenML-based code."""
    plugin_list = []

    # Fetch all plugins
    plugin_list.extend(get_integration_plugins())
    # TODO: Add examples
    # TODO: Add projects

    return plugin_list


if __name__ == "__main__":
    """Scan and save all ZenML entities."""
    # Scan for implementations
    plugins = scan_zenml_entities()

    # Write the results
    write_yaml("migration_config.yaml", [p.dict() for p in plugins])
