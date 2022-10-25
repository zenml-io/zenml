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
"""Stack component mixin for authentication."""

from typing import Optional, Type, TypeVar, cast

from zenml.client import Client
from zenml.secret import BaseSecretSchema
from zenml.stack.stack_component import StackComponent, StackComponentConfig

T = TypeVar("T", bound=BaseSecretSchema)


class AuthenticationConfigMixin(StackComponentConfig):
    """Base config for authentication mixins.

    Any stack component that implements `AuthenticationMixin` should have a
    config that inherits from this class.

    Attributes:
        authentication_secret: Name of the secret that stores the
            authentication credentials.
    """

    authentication_secret: Optional[str] = None


class AuthenticationMixin(StackComponent):
    """Stack component mixin for authentication.

    Any stack component that implements this mixin should have a config that
    inherits from `AuthenticationConfigMixin`.
    """

    @property
    def config(self) -> AuthenticationConfigMixin:
        """Returns the `AuthenticationConfigMixin` config.

        Returns:
            The configuration.
        """
        return cast(AuthenticationConfigMixin, self._config)

    def get_authentication_secret(
        self, expected_schema_type: Type[T]
    ) -> Optional[T]:
        """Gets the secret referred to by the authentication secret attribute.

        Args:
            expected_schema_type: The expected secret schema class.

        Returns:
            The secret object if the `authentication_secret` attribute is set,
            `None` otherwise.

        Raises:
            RuntimeError: If no secrets manager exists in the active stack.
            TypeError: If the secret is not of the expected schema type.
        """
        if not self.config.authentication_secret:
            return None

        active_stack = Client().active_stack
        secrets_manager = active_stack.secrets_manager
        if not secrets_manager:
            raise RuntimeError(
                f"Unable to retrieve secret '{self.config.authentication_secret}' "
                "because the active stack does not have a secrets manager."
            )

        secret = secrets_manager.get_secret(self.config.authentication_secret)

        if not isinstance(secret, expected_schema_type):
            raise TypeError(
                f"Authentication secret has type {secret.TYPE} but a secret of "
                f"type {expected_schema_type.TYPE} was expected. To solve this "
                f"issue, register a secret with name "
                f"{self.config.authentication_secret} of type "
                f"{expected_schema_type.TYPE} using the following command: \n "
                f"`zenml secrets-manager secret register {self.config.authentication_secret} "
                f"--schema={expected_schema_type.TYPE} ...`"
            )

        return secret
