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
from enum import Enum
from typing import Any, Dict, Text


# TODO [LOW]: Type hints need improving here but need to avoid circular
#  dependencies
class ComponentFactory:
    """Definition of ComponentFactory to track all BaseComponent subclasses.

    All BaseComponents (including custom ones) are to be
    registered here.
    """

    def __init__(self):
        self.components: Dict[Any, Any] = {}

    def get_components(self) -> Dict[Any, Any]:
        """Return all components"""
        return self.components

    def get_single_component(self, key: Text, enum: Enum) -> Any:
        """Get a registered component from a key and a defined enum space."""
        for e in enum:
            if key == e:
                return self.components[e]
        return self.components[key]

    def register_component(self, key: Any, component: Any):
        self.components[key] = component


component_factory = ComponentFactory()
