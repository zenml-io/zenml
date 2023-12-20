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

from pydantic import BaseModel

from zenml.client import Client
from zenml.models import SecretResponseModel
from zenml.stack.stack_component import StackComponent, StackComponentConfig

T = TypeVar("T", bound=BaseModel)


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
        self,
    ) -> Optional[SecretResponseModel]:
        """Gets the secret referred to by the authentication secret attribute.

        Returns:
            The secret if the `authentication_secret` attribute is set,
            `None` otherwise.

        Raises:
            KeyError: If the secret does not exist.
        """
        if not self.config.authentication_secret:
            return None

        # Try to resolve the secret using the secret store
        try:
            return Client().get_secret_by_name_and_scope(
                name=self.config.authentication_secret,
            )
        except (KeyError, NotImplementedError):
            raise KeyError(
                f"The authentication secret {self.config.authentication_secret} "
                f"referenced by the `{self.name}` `{self.type}` stack "
                "component does not exist."
            )

    def get_typed_authentication_secret(
        self, expected_schema_type: Type[T]
    ) -> Optional[T]:
        """Gets a typed secret referred to by the authentication secret attribute.

        Args:
            expected_schema_type: A Pydantic model class that represents the
                expected schema type of the secret.

        Returns:
            The secret values extracted from the secret and converted into the
            indicated Pydantic type, if the `authentication_secret` attribute is
            set, `None` otherwise.

        Raises:
            TypeError: If the secret cannot be converted into the indicated
                Pydantic type.
        """
        secret = self.get_authentication_secret()

        if not secret:
            return None

        try:
            typed_secret = expected_schema_type(
                **secret.secret_values,
            )
        except (TypeError, ValueError) as e:
            raise TypeError(
                f"Authentication secret `{self.config.authentication_secret}` "
                f"referenced by the `{self.name}` `{self.type}` stack component"
                f"could not be converted to {expected_schema_type}: {e}"
            )

        return typed_secret
