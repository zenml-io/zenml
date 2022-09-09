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

from datetime import datetime, timedelta
import os
from typing import Dict, Optional
from uuid import UUID

from fastapi import Depends, HTTPException, status
from jose import JWTError, jwt
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel

from zenml.constants import LOGIN, VERSION_1
from zenml.logger import get_logger
from zenml.zen_server.utils import (
    zen_store,
)

logger = get_logger(__name__)

JWT_SECRET_KEY = os.environ.get(
    "ZENML_JWT_SECRET_KEY",
    "d38d1a44ae024c21534021d4b208323a8af0f844360a2dc96322056aeab286ff",
)
JWT_ALGORITHM = "HS256"
JWT_ACCESS_TOKEN_EXPIRE_MINUTES = 30


# the 'tokenUrl' path is the endpoint where the client is redirected to
# to authenticate with username/password and get a token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=VERSION_1 + LOGIN)


class AuthContext(BaseModel):
    user_id: UUID
    username: str


def authenticate_user(
    username: str, password: Optional[str] = None
) -> Optional[AuthContext]:
    """Verify if authentication credentials are valid.

    Args:
        username: The username.
        password: The password. If not provided, only the username is
            verified.

    Returns:
        The authenticated account details, if the account is valid, otherwise
        None.
    """
    logger.info(
        f"Authenticating user {username} with password supplied: {bool(password)}"
    )
    try:
        user = zen_store.get_user(username)
    except KeyError:
        return None
    if password and not user.verify_password(password):
        return None

    return AuthContext(user_id=user.id, username=user.name)


def decode_token(token: Dict[str, str]) -> Optional[AuthContext]:
    """Decodes a JWT token and returns the authentication context.

    Args:
        token: The JWT token to be decoded.

    Returns:
        The authentication context reflecting the information in the token, or
        None if the token is invalid or could not be authenticated.
    """
    subject: str = token.get("sub")
    if subject is None:
        return None
    subject_parts = subject.split(":")
    if len(subject_parts) != 2 or subject_parts[0] != "username":
        return None
    username = subject_parts[1]
    return authenticate_user(username=username)


def create_access_token(auth_context: AuthContext) -> str:
    """Creates an access token for the given authentication context.

    Args:
        auth_context: The authentication context.

    Returns:
        The generated access token.
    """
    expire = datetime.utcnow() + timedelta(
        minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES
    )
    token_data = {
        "sub": f"username:{auth_context.username}",
        "exp": expire,
    }
    token = jwt.encode(token_data, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
    return token


async def authorize(token: str = Depends(oauth2_scheme)) -> AuthContext:
    """Authorizes any request to the ZenML server with JWT.

    Args:
        token: The JWT bearer token to be authenticated.

    Returns:
        The authentication context reflecting the authenticated user.
    """
    # We have to return an additional WWW-Authenticate header here with the
    # value Bearer to be compliant with the OAuth2 spec.
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise credentials_exception
    auth_context = decode_token(payload)
    if auth_context is None:
        raise credentials_exception

    return auth_context
