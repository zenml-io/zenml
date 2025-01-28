#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""CSRF token utilities module for ZenML server."""

from uuid import UUID

from pydantic import BaseModel

from zenml.exceptions import CredentialsNotValid
from zenml.logger import get_logger
from zenml.zen_server.utils import server_config

logger = get_logger(__name__)


class CSRFToken(BaseModel):
    """Pydantic object representing a CSRF token.

    Attributes:
        session_id: The id of the authenticated session.
    """

    session_id: UUID

    @classmethod
    def decode_token(
        cls,
        token: str,
    ) -> "CSRFToken":
        """Decodes a CSRF token.

        Decodes a CSRF access token and returns a `CSRFToken` object with the
        information retrieved from its contents.

        Args:
            token: The encoded CSRF token.

        Returns:
            The decoded CSRF token.

        Raises:
            CredentialsNotValid: If the token is invalid.
        """
        from itsdangerous import BadData, BadSignature, URLSafeSerializer

        config = server_config()

        serializer = URLSafeSerializer(config.jwt_secret_key)
        try:
            # Decode and verify the token
            data = serializer.loads(token)
        except BadSignature as e:
            raise CredentialsNotValid(
                "Invalid CSRF token: signature mismatch"
            ) from e
        except BadData as e:
            raise CredentialsNotValid("Invalid CSRF token") from e

        try:
            return CSRFToken(session_id=UUID(data))
        except ValueError as e:
            raise CredentialsNotValid(
                "Invalid CSRF token: the session ID is not a valid UUID"
            ) from e

    def encode(self) -> str:
        """Creates a CSRF token.

        Encodes, signs and returns a CSRF access token.

        Returns:
            The generated CSRF token.
        """
        from itsdangerous import URLSafeSerializer

        config = server_config()

        serializer = URLSafeSerializer(config.jwt_secret_key)
        token = serializer.dumps(str(self.session_id))
        return token
