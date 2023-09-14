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
    Optional,
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


class JWTTokenAuthenticator(BaseModel):
    """JWT token authenticator.

    Class responsible for issuing and/or verifying JWT tokens for all
    possible authentication schemes.

    Attributes:
        algorithm: The algorithm to use for signing tokens.
        issuer: The token issuer. If not provided, the tokens will not be
            checked for the issuer claim.
        audience: The token audience. If not provided, the tokens will not be
            checked for the audience claim.
        leeway_seconds: The number of seconds of leeway to accept when verifying
            the validity of tokens. If not provided, the default value of 0 will
            be used.
        expire_minutes: Number of minutes the token should be valid. If not
            provided, the generated tokens will not be set to expire.
        jwks_uri: The URI of the JWKS endpoint to use for verifying the
            signature of tokens. If not provided, the tokens will be verified
            using the secret key. Either this or `secret_key` must be provided.
        secret_key: The secret key to use for signing and verifying tokens. If
            not provided, the tokens will be verified using the JWKS endpoint.
            Either this or `jwks_uri` must be provided.
    """

    _jwks_client: Optional[jwt.PyJWKClient] = None

    @property
    def jwks_client(self) -> Optional[jwt.PyJWKClient]:
        """Initializes and returns the JWK client.

        Returns:
            The JWK client.
        """
        if self._jwks_client:
            return self._jwks_client

        jwks_uri = server_config().jwks_uri

        if not jwks_uri:
            return None

        # Create a JWK client to manage the keys
        self._jwks_client = jwt.PyJWKClient(
            jwks_uri, cache_keys=True, cache_jwk_set=True
        )

        return self._jwks_client

    def decode_token(
        self,
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

        if self.jwks_client:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token).key
        else:
            signing_key = config.jwt_secret_key

        try:
            claims_data = jwt.decode(
                token,
                signing_key,
                algorithms=[config.jwt_token_algorithm],
                audience=config.jwt_token_audience,
                issuer=config.jwt_token_issuer,
                verify=verify,
                leeway=timedelta(seconds=config.jwt_token_leeway_seconds),
            )
            claims = cast(Dict[str, Any], claims_data)
        except jwt.PyJWTError as e:
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

    def encode(self, token: JWTToken) -> str:
        """Creates a JWT access token.

        Encodes, signs and returns a JWT access token.

        Args:
            token: The token to encode.

        Returns:
            The generated access token.
        """
        config = server_config()

        claims: Dict[str, Any] = dict(
            sub=str(token.user_id),
            permissions=list(token.permissions),
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
        claims.update(token.claims)

        return jwt.encode(
            claims,
            config.jwt_secret_key,
            algorithm=config.jwt_token_algorithm,
        )

    class Config:
        """Pydantic model configuration."""

        # treat underscore prefixed attributes as private
        underscore_attrs_are_private = True


_jwt_token_authenticator: Optional[JWTTokenAuthenticator] = None


def get_token_authenticator() -> JWTTokenAuthenticator:
    """Initialize and/or return the JWT token authenticator.

    Returns:
        The JWT token authenticator.
    """
    global _jwt_token_authenticator
    if _jwt_token_authenticator is None:
        _jwt_token_authenticator = JWTTokenAuthenticator()

    return _jwt_token_authenticator
