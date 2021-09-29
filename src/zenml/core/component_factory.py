#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Factory to register all components."""
from typing import Any, Callable, Dict, Text

from zenml.logger import get_logger

logger = get_logger(__name__)

# TODO [LOW]: Type hints need improving here but need to avoid circular
#  dependencies


class ComponentFactory:
    """Definition of ComponentFactory to track all BaseComponent subclasses.

    All BaseComponents (including custom ones) are to be
    registered here.
    """

    def __init__(self, name: Text):
        """Constructor for the factory.

        Args:
            name: Unique name for the factory.
        """
        self.name = name
        self.components: Dict[Text, Any] = {}

    def get_components(self) -> Dict[Any, Any]:
        """Return all components"""
        return self.components

    def get_single_component(self, key: Text) -> Any:
        """Get a registered component from a key."""
        if key in self.components:
            return self.components[key]
        raise AssertionError(
            f"Type {key} does not exist! Available options: "
            f"{[k for k in self.components.keys()]}"
        )

    def register_component(self, key: Text, component: Any):
        self.components[key] = component

    def register(self, name: str) -> Callable:
        """Class method to register Executor class to the internal registry.

        Args:
            name (str): The name of the executor.

        Returns:
            The Executor class itself.
        """

        def inner_wrapper(wrapped_class: Any) -> Callable:
            """Inner wrapper for decorator."""
            if name in self.components:
                logger.debug(
                    f"Executor {name} already exists for factory {self.name}. Will replace it"
                )
            self.register_component(name, wrapped_class)
            return wrapped_class

        return inner_wrapper


artifact_store_factory = ComponentFactory(name="artifact")
metadata_store_factory = ComponentFactory(name="metadata")
orchestrator_store_factory = ComponentFactory(name="orchestrator")
