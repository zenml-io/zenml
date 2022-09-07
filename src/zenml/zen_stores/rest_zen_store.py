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
"""REST Zen Store implementation."""

import re
from pathlib import Path, PurePath
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type, Union, cast

import requests
from ml_metadata.proto import metadata_store_pb2
from pydantic import BaseModel

from zenml.config.store_config import StoreConfiguration
from zenml.constants import (
    FLAVORS,
    PIPELINE_RUNS,
    PROJECTS,
    ROLE_ASSIGNMENTS,
    ROLES,
    STACK_COMPONENTS,
    STACK_CONFIGURATIONS,
    STACKS,
    STACKS_EMPTY,
    TEAMS,
    USERS,
)
from zenml.enums import ExecutionStatus, StackComponentType, StoreType
from zenml.exceptions import (
    DoesNotExistException,
    EntityExistsError,
    StackComponentExistsError,
    StackExistsError,
)
from zenml.logger import get_logger
from zenml.models import (
    ComponentModel,
    FlavorModel,
    PipelineRunModel,
    ProjectModel,
    RoleAssignmentModel,
    RoleModel,
    StackModel,
    TeamModel,
    UserModel,
)
from zenml.post_execution.artifact import ArtifactView
from zenml.post_execution.pipeline import PipelineView
from zenml.post_execution.pipeline_run import PipelineRunView
from zenml.post_execution.step import StepView
from zenml.zen_stores.base_zen_store import BaseZenStore

logger = get_logger(__name__)

# type alias for possible json payloads (the Anys are recursive Json instances)
Json = Union[Dict[str, Any], List[Any], str, int, float, bool, None]


class RestZenStoreConfiguration(StoreConfiguration):
    """REST ZenML store configuration.

    Attributes:
        username: The username to use to connect to the Zen server.
        password: The password to use to connect to the Zen server.
    """

    type: StoreType = StoreType.REST
    username: str
    password: str = ""

    class Config:
        """Pydantic configuration class."""

        # Validate attributes when assigning them. We need to set this in order
        # to have a mix of mutable and immutable attributes
        validate_assignment = True
        # Ignore extra attributes set in the class.
        extra = "ignore"


class RestZenStore(BaseZenStore):
    """Store implementation for accessing data from a REST API."""

    config: RestZenStoreConfiguration
    TYPE: ClassVar[StoreType] = StoreType.REST
    CONFIG_TYPE: ClassVar[Type[StoreConfiguration]] = RestZenStoreConfiguration

    def _initialize(self) -> None:
        """Initialize the REST store."""
        # try to connect to the server to validate the configuration
        self._handle_response(
            requests.get(self.url + "/", auth=self._get_authentication())
        )

    def _initialize_database(self) -> None:
        """Initialize the database."""
        # don't do anything for a REST store

    # Static methods:

    @staticmethod
    def get_path_from_url(url: str) -> Optional[Path]:
        """Get the path from a URL, if it points or is backed by a local file.

        Args:
            url: The URL to get the path from.

        Returns:
            None, because there are no local paths from REST URLs.
        """
        return None

    @staticmethod
    def get_local_url(path: str) -> str:
        """Get a local URL for a given local path.

        Args:
            path: the path string to build a URL out of.

        Raises:
            NotImplementedError: always
        """
        raise NotImplementedError("Cannot build a REST url from a path.")

    @staticmethod
    def validate_url(url: str) -> str:
        """Check if the given url is a valid REST URL.

        Args:
            url: The url to check.

        Returns:
            The validated url.

        Raises:
            ValueError: If the url is not valid.
        """
        url = url.rstrip("/")
        scheme = re.search("^([a-z0-9]+://)", url)
        if scheme is None or scheme.group() not in ("https://", "http://"):
            raise ValueError(
                "Invalid URL for REST store: {url}. Should be in the form "
                "https://hostname[:port] or http://hostname[:port]."
            )

        return url

    @classmethod
    def copy_local_store(
        cls,
        config: StoreConfiguration,
        path: str,
        load_config_path: Optional[PurePath] = None,
    ) -> StoreConfiguration:
        """Copy a local store to a new location.

        Use this method to create a copy of a store database to a new location
        and return a new store configuration pointing to the database copy. This
        only applies to stores that use the local filesystem to store their
        data. Calling this method for remote stores simply returns the input
        store configuration unaltered.

        Args:
            config: The configuration of the store to copy.
            path: The new local path where the store DB will be copied.
            load_config_path: path that will be used to load the copied store
                database. This can be set to a value different from `path`
                if the local database copy will be loaded from a different
                environment, e.g. when the database is copied to a container
                image and loaded using a different absolute path. This will be
                reflected in the paths and URLs encoded in the copied store
                configuration.

        Returns:
            The store configuration of the copied store.
        """
        # REST zen stores are not backed by local files
        return config

    #  Zen-Store API

    def _list_users(self) -> List[UserModel]:
        """List all users.

        Returns:
            A list of all users.
        """
        return [UserModel.parse_obj(user) for user in self.get(f"{USERS}")]

    def _create_user(self, user: UserModel) -> UserModel:
        """Creates a new user.

        Args:
            user: User to be created.

        Returns:
            The newly created user.

        Raises:
            EntityExistsError: If a user with the given name already exists.
        """
        return UserModel.parse_obj(self.post(USERS, body=user))

    def _get_user(
        self, user_name_or_id: str
    ) -> UserModel:
        """Gets a specific user.

        Args:
            user_name_or_id: The name or ID of the user to get.

        Returns:
            The requested user, if it was found.

        Raises:
            KeyError: If no user with the given name or ID exists.
        """
        return UserModel.parse_obj(self.get(f"{USERS}/{user_name_or_id}"))

    def _update_user(self, user_id: str, user: UserModel) -> UserModel:
        """Updates an existing user.

        Args:
            user_id: The ID of the user to update.
            user: The User model to use for the update.

        Returns:
            The updated user.

        Raises:
            KeyError: If no user with the given name exists.
        """
        return UserModel.parse_obj(self.put(f"{USERS}/{user_id}",
                                            body=user))

    def _delete_user(self, user_id: str) -> None:
        """Deletes a user.

        Args:
            user_id: The ID of the user to delete.

        Raises:
            KeyError: If no user with the given name exists.
        """
        self.delete(f"{USERS}/{user_id}")

    def _handle_response(self, response: requests.Response) -> Json:
        """Handle API response, translating http status codes to Exception.

        Args:
            response: The response to handle.

        Returns:
            The parsed response.

        Raises:
            DoesNotExistException: If the response indicates that the
                requested entity does not exist.
            EntityExistsError: If the response indicates that the requested
                entity already exists.
            HTTPError: If the response indicates that the requested entity
                does not exist.
            KeyError: If the response indicates that the requested entity
                does not exist.
            RuntimeError: If the response indicates that the requested entity
                does not exist.
            StackComponentExistsError: If the response indicates that the
                requested entity already exists.
            StackExistsError: If the response indicates that the requested
                entity already exists.
            ValueError: If the response indicates that the requested entity
                does not exist.
        """
        if response.status_code >= 200 and response.status_code < 300:
            try:
                payload: Json = response.json()
                return payload
            except requests.exceptions.JSONDecodeError:
                raise ValueError(
                    "Bad response from API. Expected json, got\n"
                    f"{response.text}"
                )
        elif response.status_code == 401:
            raise requests.HTTPError(
                f"{response.status_code} Client Error: Unauthorized request to URL {response.url}: {response.json().get('detail')}"
            )
        elif response.status_code == 404:
            if "DoesNotExistException" not in response.text:
                raise KeyError(*response.json().get("detail", (response.text,)))
            message = ": ".join(response.json().get("detail", (response.text,)))
            raise DoesNotExistException(message)
        elif response.status_code == 409:
            if "StackComponentExistsError" in response.text:
                raise StackComponentExistsError(
                    *response.json().get("detail", (response.text,))
                )
            elif "StackExistsError" in response.text:
                raise StackExistsError(
                    *response.json().get("detail", (response.text,))
                )
            elif "EntityExistsError" in response.text:
                raise EntityExistsError(
                    *response.json().get("detail", (response.text,))
                )
            else:
                raise ValueError(
                    *response.json().get("detail", (response.text,))
                )
        elif response.status_code == 422:
            raise RuntimeError(*response.json().get("detail", (response.text,)))
        elif response.status_code == 500:
            raise KeyError(response.text)
        else:
            raise RuntimeError(
                "Error retrieving from API. Got response "
                f"{response.status_code} with body:\n{response.text}"
            )

    def _get_authentication(self) -> Tuple[str, str]:
        """Gets HTTP basic auth credentials.

        Returns:
            A tuple of the username and password.
        """
        return self.config.username, self.config.password

    def get(self, path: str) -> Json:
        """Make a GET request to the given endpoint path.

        Args:
            path: The path to the endpoint.

        Returns:
            The response body.
        """
        return self._handle_response(
            requests.get(self.url + path, auth=self._get_authentication())
        )

    def delete(self, path: str) -> Json:
        """Make a DELETE request to the given endpoint path.

        Args:
            path: The path to the endpoint.

        Returns:
            The response body.
        """
        return self._handle_response(
            requests.delete(self.url + path, auth=self._get_authentication())
        )

    def post(self, path: str, body: BaseModel) -> Json:
        """Make a POST request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            body: The body to send.

        Returns:
            The response body.
        """
        endpoint = self.url + path
        return self._handle_response(
            requests.post(
                endpoint, data=body.json(), auth=self._get_authentication()
            )
        )

    def put(self, path: str, body: BaseModel) -> Json:
        """Make a PUT request to the given endpoint path.

        Args:
            path: The path to the endpoint.
            body: The body to send.

        Returns:
            The response body.
        """
        endpoint = self.url + path
        return self._handle_response(
            requests.put(
                endpoint, data=body.json(), auth=self._get_authentication()
            )
        )
