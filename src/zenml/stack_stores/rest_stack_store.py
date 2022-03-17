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
from typing import Any, Dict, List, Tuple, cast

import requests
from pydantic import BaseModel

from zenml.enums import StackComponentFlavor, StackComponentType
from zenml.logger import get_logger
from zenml.stack_stores import BaseStackStore
from zenml.stack_stores.models import (
    StackComponentWrapper,
    StackWrapper,
    Version,
)

logger = get_logger(__name__)


class RestStackStore(BaseStackStore):
    """StackStore implementation for accessing stack data from a REST api."""

    def __init__(self, endpoint: str = "http://localhost:8000") -> None:
        if not (
            endpoint.startswith("http://") or endpoint.startswith("https://")
        ):
            endpoint = "https://" + endpoint
        self.endpoint = endpoint

    # Public+Inheritance Interface:

    @property
    def version(self) -> str:
        """Get the ZenML version."""
        return Version.parse_obj(self.get("/version")).version

    def get_stack_configuration(
        self, name: str
    ) -> Dict[StackComponentType, str]:
        """Fetches a stack configuration."""
        return self._parse_stack_configuration(
            self.get(f"/stacks/configuration/{name}").items()
        )

    @property
    def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
        """Configuration for all stacks registered in this repository."""
        return {
            key: self._parse_stack_configuration(value)
            for key, value in self.get("/stacks/configurations/")
        }

    def register_stack_component(
        self,
        component: StackComponentWrapper,
    ) -> None:
        """Registers a stack component."""
        self.post("/components/register", body=component)

    # Custom implementations:

    @property
    def stacks(self) -> List[StackWrapper]:
        """All stacks registered in this repository."""
        return [StackWrapper.parse_obj(s) for s in self.get("/stacks")]

    def get_stack(self, name: str) -> StackWrapper:
        """Fetches a stack."""
        return StackWrapper.parse_obj(self.get(f"/stacks/{name}"))

    def register_stack(self, stack: StackWrapper) -> Dict[str, str]:
        """Registers a stack and its components."""
        return cast(Dict[str, str], self.post("/stacks/register", stack))

    def deregister_stack(self, name: str) -> None:
        """Deregisters a stack."""
        self.get(f"stacks/{name}/deregister")

    def get_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> StackComponentWrapper:
        """Fetches a registered stack component."""
        return StackComponentWrapper.parse_obj(
            self.get(f"/components/{component_type}/{name}")
        )

    def get_stack_components(
        self, component_type: StackComponentType
    ) -> List[StackComponentWrapper]:
        """Fetches all registered stack components of the given type."""
        return [
            StackComponentWrapper.parse_obj(c)
            for c in self.get(f"/components/{component_type}")
        ]

    def deregister_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Deregisters a stack component."""
        self.get(f"/components/deregister/{component_type}/{name}")

    # don't call these! ABC complains that they aren't implemented, but they
    # aren't needed with custom implementations of the above:

    def _create_stack(
        self, name: str, stack_configuration: Dict[StackComponentType, str]
    ) -> None:
        """Add a stack to storage"""
        raise NotImplementedError("Not to be accessed direclty in client!")

    def _delete_stack(self, name: str) -> None:
        """Delete a stack from storage."""
        raise NotImplementedError("Not to be accessed direclty in client!")

    def _get_component_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[StackComponentFlavor, Any]:
        """Fetch the flavor and configuration for a stack component."""
        raise NotImplementedError("Not to be accessed direclty in client!")

    def _get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type."""
        raise NotImplementedError("Not to be accessed direclty in client!")

    def _delete_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Remove a StackComponent from storage."""
        raise NotImplementedError("Not to be accessed direclty in client!")

    # Implementation specific methods:

    def _parse_stack_configuration(
        self, to_parse: Any
    ) -> Dict[StackComponentType, str]:
        """Parse an API response into `Dict[StackComponentType, str]`."""
        return {
            StackComponentType(typ): component_name
            for typ, component_name in to_parse.items()
        }

    def get(self, path: str) -> Any:
        return requests.get(self.endpoint + path).json()

    def post(self, path: str, body: BaseModel) -> Any:
        return requests.post(self.endpoint + path, json=body.json()).json()
