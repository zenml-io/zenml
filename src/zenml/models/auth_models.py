#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Models representing OAuth2 requests and responses."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel

from zenml.enums import OAuthGrantTypes

# ------- #
# REQUEST #
# ------- #


class OAuthDeviceAuthorizationRequest(BaseModel):
    """OAuth2 device authorization grant request."""

    client_id: UUID


class OAuthDeviceVerificationRequest(BaseModel):
    """OAuth2 device authorization verification request."""

    user_code: str
    trusted_device: bool = False


class OAuthDeviceTokenRequest(BaseModel):
    """OAuth2 device authorization grant request."""

    grant_type: str = OAuthGrantTypes.OAUTH_DEVICE_CODE
    client_id: UUID
    device_code: str


class OAuthDeviceUserAgentHeader(BaseModel):
    """OAuth2 device user agent header."""

    hostname: Optional[str] = None
    os: Optional[str] = None
    python_version: Optional[str] = None
    zenml_version: Optional[str] = None

    @classmethod
    def decode(cls, header_str: str) -> "OAuthDeviceUserAgentHeader":
        """Decode the user agent header.

        Args:
            header_str: The user agent header string value.

        Returns:
            The decoded user agent header.
        """
        header = cls()
        properties = header_str.strip().split(" ")
        for property in properties:
            try:
                key, value = property.split("/", maxsplit=1)
            except ValueError:
                continue
            if key == "Host":
                header.hostname = value
            elif key == "ZenML":
                header.zenml_version = value
            elif key == "Python":
                header.python_version = value
            elif key == "OS":
                header.os = value
        return header

    def encode(self) -> str:
        """Encode the user agent header.

        Returns:
            The encoded user agent header.
        """
        return (
            f"Host/{self.hostname} "
            f"ZenML/{self.zenml_version} "
            f"Python/{self.python_version} "
            f"OS/{self.os}"
        )


# -------- #
# RESPONSE #
# -------- #


class OAuthDeviceAuthorizationResponse(BaseModel):
    """OAuth2 device authorization grant response."""

    device_code: str
    user_code: str
    verification_uri: str
    verification_uri_complete: Optional[str] = None
    expires_in: int
    interval: int


class OAuthTokenResponse(BaseModel):
    """OAuth2 device authorization token response."""

    access_token: str
    token_type: str
    expires_in: Optional[int] = None
    refresh_token: Optional[str] = None
    scope: Optional[str] = None


class OAuthRedirectResponse(BaseModel):
    """Redirect response."""

    authorization_url: str
