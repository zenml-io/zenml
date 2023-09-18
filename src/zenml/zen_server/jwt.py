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
"""Authentication module for ZenML server."""

from datetime import datetime, timedelta
from typing import (
    Any,
    Dict,
    List,
    Union,
    cast,
)
from uuid import UUID

import jwt
from pydantic import BaseModel

from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.zen_server.utils import server_config

logger = get_logger(__name__)


class JWTToken(BaseModel):
    """Pydantic object representing a JWT token.

    Attributes:
        user_id: The id of the authenticated User.
        permissions: The permissions scope of the authenticated user.
        claims: The original token claims.
    """

    user_id: Union[UUID, str]
    permissions: List[str]
    claims: Dict[str, Any] = {}

    @classmethod
    def decode_token(
        cls,
        token: str,
        verify: bool = True,
    ) -> "JWTToken":
        """Decodes a JWT access token.

        Decodes a JWT access token and returns a `JWTToken` object with the
        information retrieved from its subject claim.

        Args:
            token: The encoded JWT token.
            verify: Whether to verify the signature of the token.

        Returns:
            The decoded JWT access token.

        Raises:
            AuthorizationException: If the token is invalid.
        """
        config = server_config()

        try:
            claims_data = jwt.decode(
                token,
                config.jwt_secret_key,
                algorithms=[config.jwt_token_algorithm],
                audience=config.jwt_token_audience,
                issuer=config.jwt_token_issuer,
                verify=verify,
                leeway=timedelta(seconds=config.jwt_token_leeway_seconds),
            )
            claims = cast(Dict[str, Any], claims_data)
        except (
            jwt.PyJWTError,
            jwt.exceptions.DecodeError,
            jwt.exceptions.PyJWKClientError,
        ) as e:
            raise AuthorizationException(f"Invalid JWT token: {e}") from e

        subject: str = claims.get("sub", "")
        if not subject:
            raise AuthorizationException(
                "Invalid JWT token: the subject claim is missing"
            )
        permissions: List[str] = claims.get("permissions", [])

        user_id: Union[UUID, str] = subject
        try:
            user_id = UUID(subject)
        except ValueError:
            pass

        return JWTToken(
            user_id=user_id,
            permissions=list(set(permissions)),
            claims=claims,
        )

    def encode(self) -> str:
        """Creates a JWT access token.

        Encodes, signs and returns a JWT access token.

        Args:
            token: The token to encode.

        Returns:
            The generated access token.
        """
        config = server_config()

        claims: Dict[str, Any] = dict(
            sub=str(self.user_id),
            permissions=list(self.permissions),
        )
        if config.jwt_token_issuer:
            claims["iss"] = config.jwt_token_issuer
        if config.jwt_token_audience:
            claims["aud"] = config.jwt_token_audience
        if config.jwt_token_expire_minutes:
            expire = datetime.utcnow() + timedelta(
                minutes=config.jwt_token_expire_minutes
            )
            claims["exp"] = expire

        # Apply custom claims
        claims.update(self.claims)

        return jwt.encode(
            claims,
            config.jwt_secret_key,
            algorithm=config.jwt_token_algorithm,
        )
