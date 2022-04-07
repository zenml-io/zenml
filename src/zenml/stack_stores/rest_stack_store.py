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
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union, cast

import requests
from pydantic import BaseModel

from zenml.constants import (
    IS_EMPTY,
    STACK_COMPONENTS,
    STACK_CONFIGURATIONS,
    STACKS,
)
from zenml.enums import StackComponentType, StoreType
from zenml.exceptions import StackComponentExistsError, StackExistsError
from zenml.logger import get_logger
from zenml.stack_stores import BaseStackStore
from zenml.stack_stores.models import StackComponentWrapper, StackWrapper

logger = get_logger(__name__)

# type alias for possible json payloads (the Anys are recursive Json instances)
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class RestStackStore(BaseStackStore):
    """StackStore implementation for accessing stack data from a REST api."""

    def initialize(
        self,
        url: str,
        *args: Any,
        **kwargs: Any,
    ) -> "RestStackStore":
        """Initializes a local stack store instance.

        Args:
            url: Endpoint URL of the service for stack storage.
            args: additional positional arguments (ignored).
            kwargs: additional keyword arguments (ignored).

        Returns:
            The initialized stack store instance.
        """
        if not self.is_valid_url(url.strip("/")):
            raise ValueError("Invalid URL for REST store: {url}")
        self._url = url.strip("/")
        if "skip_default_stack" not in kwargs:
            kwargs["skip_default_stack"] = True
        # breakpoint()
        super().initialize(url, *args, **kwargs)
        return self

    # Statics:

    @staticmethod
    def get_path_from_url(url: str) -> Optional[Path]:
        """Get the path from a URL, if it points or is backed by a local file.

        Args:
            url: The URL to get the path from.

        Returns:
            None, because there are no local paths from REST urls.
        """
        return None

    @staticmethod
    def get_local_url(path: str) -> str:
        """Get a local URL for a given local path.

        Args:
             path: the path string to build a URL out of.

        Returns:
            Url pointing to the path for the store type.

        Raises:
            NotImplementedError: always
        """
        raise NotImplementedError("Cannot build a REST url from a path.")

    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Check if the given url is a valid local path."""
        scheme = re.search("^([a-z0-9]+://)", url)
        return (
            scheme is not None
            and scheme.group() in ("https://", "http://")
            and url[-1] != "/"
        )

    # Public Interface:

    @property
    def type(self) -> StoreType:
        """The type of stack store."""
        return StoreType.REST

    @property
    def url(self) -> str:
        """Get the stack store URL."""
        return self._url

    @property
    def is_empty(self) -> bool:
        """Check if the store is empty (no stacks are configured).

        The implementation of this method should check if the store is empty
        without having to load all the stacks from the persistent storage.
        """
        empty = self.get(IS_EMPTY)
        if not isinstance(empty, bool):
            raise ValueError(
                f"Bad API Response. Expected boolean, got:\n{empty}"
            )
        return empty

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
        return self._parse_stack_configuration(
            self.get(f"{STACK_CONFIGURATIONS}/{name}")
        )

    @property
    def stack_configurations(self) -> Dict[str, Dict[StackComponentType, str]]:
        """Configurations for all stacks registered in this stack store.

        Returns:
            Dictionary mapping stack names to Dict[StackComponentType, str]'s
        """
        body = self.get(STACK_CONFIGURATIONS)
        if not isinstance(body, dict):
            raise ValueError(
                f"Bad API Response. Expected dict, got {type(body)}"
            )
        return {
            key: self._parse_stack_configuration(value)
            for key, value in body.items()
        }

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
        self.post(STACK_COMPONENTS, body=component)

    def deregister_stack(self, name: str) -> None:
        """Delete a stack from storage.

        Args:
            name: The name of the stack to be deleted.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        self.delete(f"{STACKS}/{name}")

    # Custom implementations:

    @property
    def stacks(self) -> List[StackWrapper]:
        """All stacks registered in this repository."""
        body = self.get(STACKS)
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [StackWrapper.parse_obj(s) for s in body]

    def get_stack(self, name: str) -> StackWrapper:
        """Fetch a stack by name.

        Args:
            name: The name of the stack to retrieve.

        Returns:
            StackWrapper instance if the stack exists.

        Raises:
            KeyError: If no stack exists for the given name.
        """
        return StackWrapper.parse_obj(self.get(f"{STACKS}/{name}"))

    def register_stack(self, stack: StackWrapper) -> Dict[str, str]:
        """Register a stack and its components.

        If any of the stacks' components aren't registered in the stack store
        yet, this method will try to register them as well.

        Args:
            stack: The stack to register.

        Returns:
            metadata dict for telemetry or logging.

        Raises:
            StackExistsError: If a stack with the same name already exists.
            StackComponentExistsError: If a component of the stack wasn't
                registered and a different component with the same name
                already exists.
        """
        body = self.post(STACKS, stack)
        if isinstance(body, dict):
            return cast(Dict[str, str], body)
        else:
            raise ValueError(
                f"Bad API Response. Expected dict, got {type(body)}"
            )

    def get_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> StackComponentWrapper:
        """Get a registered stack component.

        Raises:
            KeyError: If no component with the requested type and name exists.
        """
        return StackComponentWrapper.parse_obj(
            self.get(f"{STACK_COMPONENTS}/{component_type}/{name}")
        )

    def get_stack_components(
        self, component_type: StackComponentType
    ) -> List[StackComponentWrapper]:
        """Fetches all registered stack components of the given type.

        Args:
            component_type: StackComponentType to list members of

        Returns:
            A list of StackComponentConfiguration instances.
        """
        body = self.get(f"{STACK_COMPONENTS}/{component_type}")
        if not isinstance(body, list):
            raise ValueError(
                f"Bad API Response. Expected list, got {type(body)}"
            )
        return [StackComponentWrapper.parse_obj(c) for c in body]

    def deregister_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Deregisters a stack component.

        Args:
            component_type: The type of the component to deregister.
            name: The name of the component to deregister.

        Raises:
            ValueError: if trying to deregister a component that's part
                of a stack.
        """
        self.delete(f"{STACK_COMPONENTS}/{component_type}/{name}")

    # Private interface shall not be implemented for REST store, instead the
    # API only provides all public methods, including the ones that would
    # otherwise be inherited from the BaseStackStore in other implementations.
    # Don't call these! ABC complains that they aren't implemented, but they
    # aren't needed with the custom implementations of base methods.

    def _create_stack(
        self, name: str, stack_configuration: Dict[StackComponentType, str]
    ) -> None:
        """Add a stack to storage"""
        raise NotImplementedError("Not to be accessed directly in client!")

    def _get_component_flavor_and_config(
        self, component_type: StackComponentType, name: str
    ) -> Tuple[str, bytes]:
        """Fetch the flavor and configuration for a stack component."""
        raise NotImplementedError("Not to be accessed directly in client!")

    def _get_stack_component_names(
        self, component_type: StackComponentType
    ) -> List[str]:
        """Get names of all registered stack components of a given type."""
        raise NotImplementedError("Not to be accessed directly in client!")

    def _delete_stack_component(
        self, component_type: StackComponentType, name: str
    ) -> None:
        """Remove a StackComponent from storage."""
        raise NotImplementedError("Not to be accessed directly in client!")

    # Implementation specific methods:

    def _parse_stack_configuration(
        self, to_parse: Json
    ) -> Dict[StackComponentType, str]:
        """Parse an API response into `Dict[StackComponentType, str]`."""
        if not isinstance(to_parse, dict):
            raise ValueError(
                f"Bad API Response. Expected dict, got {type(to_parse)}."
            )
        return {
            StackComponentType(typ): component_name
            for typ, component_name in to_parse.items()
        }

    def _handle_response(self, response: requests.Response) -> Json:
        """Handle API response, translating http status codes to Exception."""
        if response.status_code >= 200 and response.status_code < 300:
            try:
                payload: Json = response.json()
                return payload
            except requests.exceptions.JSONDecodeError:
                raise ValueError(
                    "Bad response from API. Expected json, got\n"
                    f"{response.text}"
                )
        elif response.status_code == 404:
            raise KeyError(*response.json().get("detail", (response.text,)))
        elif response.status_code == 409:
            if "StackComponentExistsError" in response.text:
                raise StackComponentExistsError(
                    *response.json().get("detail", (response.text,))
                )
            elif "StackExistsError" in response.text:
                raise StackExistsError(
                    *response.json().get("detail", (response.text,))
                )
            else:
                raise ValueError(
                    *response.json().get("detail", (response.text,))
                )
        elif response.status_code == 422:
            raise RuntimeError(*response.json().get("detail", (response.text,)))
        else:
            raise RuntimeError(
                "Error retrieving from API. Got response "
                f"{response.status_code} with body:\n{response.text}"
            )

    def get(self, path: str) -> Json:
        """Make a GET request to the given endpoint path."""
        return self._handle_response(requests.get(self.url + path))

    def delete(self, path: str) -> Json:
        """Make a GET request to the given endpoint path."""
        return self._handle_response(requests.delete(self.url + path))

    def post(self, path: str, body: BaseModel) -> Json:
        """Make a POST request to the given endpoint path."""
        endpoint = self.url + path
        return self._handle_response(requests.post(endpoint, data=body.json()))
