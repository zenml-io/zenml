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
"""Implementation of a base container registry class."""

import re
from typing import ClassVar, Optional, Tuple

from pydantic import validator

from zenml.enums import StackComponentType
from zenml.secret.schemas import BasicAuthSecretSchema
from zenml.stack import StackComponent
from zenml.stack.authentication_mixin import AuthenticationMixin
from zenml.utils import docker_utils


class BaseContainerRegistry(StackComponent, AuthenticationMixin):
    """Base class for all ZenML container registries.

    Attributes:
        uri: The URI of the container registry.
    """

    uri: str

    # Class Configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.CONTAINER_REGISTRY

    @validator("uri")
    def strip_trailing_slash(cls, uri: str) -> str:
        """Removes trailing slashes from the URI.

        Args:
            uri: The URI to be stripped.

        Returns:
            The URI without trailing slashes.
        """
        return uri.rstrip("/")

    @property
    def requires_authentication(self) -> bool:
        """Returns whether the container registry requires authentication.

        Returns:
            `True` if the container registry requires authentication,
            `False` otherwise.
        """
        return bool(self.authentication_secret)

    @property
    def credentials(self) -> Optional[Tuple[str, str]]:
        """Username and password to authenticate with this container registry.

        Returns:
            Tuple with username and password if this container registry
            requires authentication, `None` otherwise.
        """
        secret = self.get_authentication_secret(
            expected_schema_type=BasicAuthSecretSchema
        )
        if secret:
            return secret.username, secret.password

        return None

    @property
    def is_local(self) -> bool:
        """Returns whether the container registry is local or not.

        Returns:
            True if the container registry is local, False otherwise.
        """
        return bool(re.fullmatch(r"localhost:[0-9]{4,5}", self.uri))

    def prepare_image_push(self, image_name: str) -> None:
        """Preparation before an image gets pushed.

        Subclasses can overwrite this to do any necessary checks or
        preparations before an image gets pushed.

        Args:
            image_name: Name of the docker image that will be pushed.
        """

    def push_image(self, image_name: str) -> str:
        """Pushes a docker image.

        Args:
            image_name: Name of the docker image that will be pushed.

        Returns:
            The Docker repository digest of the pushed image.

        Raises:
            ValueError: If the image name is not associated with this
                container registry.
        """
        if not image_name.startswith(self.uri):
            raise ValueError(
                f"Docker image `{image_name}` does not belong to container "
                f"registry `{self.uri}`."
            )

        self.prepare_image_push(image_name)
        return docker_utils.push_image(image_name)
