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
    Optional,
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
        device_id: The id of the authenticated device.
        api_key_id: The id of the authenticated API key for which this token
            was issued.
        pipeline_id: The id of the pipeline for which the token was issued.
        schedule_id: The id of the schedule for which the token was issued.
        claims: The original token claims.
    """

    user_id: UUID
    device_id: Optional[UUID] = None
    api_key_id: Optional[UUID] = None
    pipeline_id: Optional[UUID] = None
    schedule_id: Optional[UUID] = None
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
                audience=config.get_jwt_token_audience(),
                issuer=config.get_jwt_token_issuer(),
                verify=verify,
                leeway=timedelta(seconds=config.jwt_token_leeway_seconds),
            )
            claims = cast(Dict[str, Any], claims_data)
        except jwt.PyJWTError as e:
            raise AuthorizationException(f"Invalid JWT token: {e}") from e

        subject: str = claims.pop("sub", "")
        if not subject:
            raise AuthorizationException(
                "Invalid JWT token: the subject claim is missing"
            )

        try:
            user_id = UUID(subject)
        except ValueError:
            raise AuthorizationException(
                "Invalid JWT token: the subject claim is not a valid UUID"
            )

        device_id: Optional[UUID] = None
        if "device_id" in claims:
            try:
                device_id = UUID(claims.pop("device_id"))
            except ValueError:
                raise AuthorizationException(
                    "Invalid JWT token: the device_id claim is not a valid "
                    "UUID"
                )

        api_key_id: Optional[UUID] = None
        if "api_key_id" in claims:
            try:
                api_key_id = UUID(claims.pop("api_key_id"))
            except ValueError:
                raise AuthorizationException(
                    "Invalid JWT token: the api_key_id claim is not a valid "
                    "UUID"
                )

        pipeline_id: Optional[UUID] = None
        if "pipeline_id" in claims:
            try:
                pipeline_id = UUID(claims.pop("pipeline_id"))
            except ValueError:
                raise AuthorizationException(
                    "Invalid JWT token: the pipeline_id claim is not a valid "
                    "UUID"
                )

        schedule_id: Optional[UUID] = None
        if "schedule_id" in claims:
            try:
                schedule_id = UUID(claims.pop("schedule_id"))
            except ValueError:
                raise AuthorizationException(
                    "Invalid JWT token: the schedule_id claim is not a valid "
                    "UUID"
                )

        return JWTToken(
            user_id=user_id,
            device_id=device_id,
            api_key_id=api_key_id,
            pipeline_id=pipeline_id,
            schedule_id=schedule_id,
            claims=claims,
        )

    def encode(self, expires: Optional[datetime] = None) -> str:
        """Creates a JWT access token.

        Encodes, signs and returns a JWT access token.

        Args:
            expires: Datetime after which the token will expire. If not
                provided, the JWT token will not be set to expire.

        Returns:
            The generated access token.
        """
        config = server_config()

        claims: Dict[str, Any] = self.claims.copy()

        claims["sub"] = str(self.user_id)
        claims["iss"] = config.get_jwt_token_issuer()
        claims["aud"] = config.get_jwt_token_audience()

        if expires:
            claims["exp"] = expires
        else:
            claims.pop("exp", None)

        if self.device_id:
            claims["device_id"] = str(self.device_id)
        if self.api_key_id:
            claims["api_key_id"] = str(self.api_key_id)
        if self.pipeline_id:
            claims["pipeline_id"] = str(self.pipeline_id)
        if self.schedule_id:
            claims["schedule_id"] = str(self.schedule_id)

        return jwt.encode(
            claims,
            config.jwt_secret_key,
            algorithm=config.jwt_token_algorithm,
        )
