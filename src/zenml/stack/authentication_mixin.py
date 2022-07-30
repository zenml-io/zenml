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

from typing import Optional, Type, TypeVar

from pydantic import BaseModel

from zenml.repository import Repository
from zenml.secret import BaseSecretSchema

T = TypeVar("T", bound=BaseSecretSchema)


class AuthenticationMixin(BaseModel):
    """Stack component mixin for authentication.

    Attributes:
        authentication_secret: Name of the secret that stores the
            authentication credentials.
    """

    authentication_secret: Optional[str] = None

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
        if not self.authentication_secret:
            return None

        active_stack = Repository(skip_repository_check=True).active_stack  # type: ignore[call-arg]
        secrets_manager = active_stack.secrets_manager
        if not secrets_manager:
            raise RuntimeError(
                f"Unable to retrieve secret '{self.authentication_secret}' "
                "because the active stack does not have a secrets manager."
            )

        secret = secrets_manager.get_secret(self.authentication_secret)

        if not isinstance(secret, expected_schema_type):
            raise TypeError(
                f"Authentication secret has type {secret.TYPE} but a secret of "
                f"type {expected_schema_type.TYPE} was expected. To solve this "
                f"issue, register a secret with name "
                f"{self.authentication_secret} of type "
                f"{expected_schema_type.TYPE} using the following command: \n "
                f"`zenml secret register {self.authentication_secret} "
                f"--schema={expected_schema_type.TYPE} ...`"
            )

        return secret
