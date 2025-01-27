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
"""ZenML login credentials models."""

from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Union
from urllib.parse import urlparse
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from zenml.login.pro.constants import ZENML_PRO_API_URL, ZENML_PRO_URL
from zenml.login.pro.tenant.models import TenantRead, TenantStatus
from zenml.models import ServerModel
from zenml.models.v2.misc.server_models import ServerDeploymentType
from zenml.services.service_status import ServiceState
from zenml.utils.enum_utils import StrEnum
from zenml.utils.string_utils import get_human_readable_time
from zenml.utils.time_utils import to_local_tz, utc_now


class ServerType(StrEnum):
    """The type of server."""

    PRO_API = "PRO_API"
    PRO = "PRO"
    REMOTE = "REMOTE"
    LOCAL = "LOCAL"


class APIToken(BaseModel):
    """Cached API Token."""

    access_token: str
    expires_in: Optional[int] = None
    expires_at: Optional[datetime] = None
    leeway: Optional[int] = None
    device_id: Optional[UUID] = None
    device_metadata: Optional[Dict[str, Any]] = None

    @property
    def expires_at_with_leeway(self) -> Optional[datetime]:
        """Get the token expiration time with leeway.

        Returns:
            The token expiration time with leeway.
        """
        if not self.expires_at:
            return None
        if not self.leeway:
            return self.expires_at
        return self.expires_at - timedelta(seconds=self.leeway)

    @property
    def expired(self) -> bool:
        """Check if the token is expired.

        Returns:
            bool: True if the token is expired, False otherwise.
        """
        expires_at = self.expires_at_with_leeway
        if not expires_at:
            return False
        return expires_at < utc_now(tz_aware=expires_at)

    model_config = ConfigDict(
        # Allow extra attributes to allow backwards compatibility
        extra="allow",
    )


class ServerCredentials(BaseModel):
    """Cached Server Credentials."""

    url: str
    api_key: Optional[str] = None
    api_token: Optional[APIToken] = None
    username: Optional[str] = None
    password: Optional[str] = None

    # Extra server attributes
    deployment_type: Optional[ServerDeploymentType] = None
    server_id: Optional[UUID] = None
    server_name: Optional[str] = None
    status: Optional[str] = None
    version: Optional[str] = None

    # Pro server attributes
    organization_name: Optional[str] = None
    organization_id: Optional[UUID] = None
    tenant_name: Optional[str] = None
    tenant_id: Optional[UUID] = None
    pro_api_url: Optional[str] = None
    pro_dashboard_url: Optional[str] = None

    @property
    def id(self) -> str:
        """Get the server identifier.

        Returns:
            The server identifier.
        """
        if self.server_id:
            return str(self.server_id)
        return self.url

    @property
    def type(self) -> ServerType:
        """Get the server type.

        Returns:
            The server type.
        """
        if self.deployment_type == ServerDeploymentType.CLOUD:
            return ServerType.PRO
        if self.url == ZENML_PRO_API_URL:
            return ServerType.PRO_API
        if self.url == self.pro_api_url:
            return ServerType.PRO_API
        if self.organization_id or self.tenant_id:
            return ServerType.PRO
        if urlparse(self.url).hostname in [
            "localhost",
            "127.0.0.1",
            "host.docker.internal",
        ]:
            return ServerType.LOCAL
        return ServerType.REMOTE

    def update_server_info(
        self, server_info: Union[ServerModel, TenantRead]
    ) -> None:
        """Update with server information received from the server itself or from a ZenML Pro tenant descriptor.

        Args:
            server_info: The server information to update with.
        """
        if isinstance(server_info, ServerModel):
            # The server ID doesn't change during the lifetime of the server
            self.server_id = self.server_id or server_info.id
            # All other attributes can change during the lifetime of the server
            self.deployment_type = server_info.deployment_type
            server_name = (
                server_info.pro_tenant_name
                or server_info.metadata.get("tenant_name")
                or server_info.name
            )
            if server_name:
                self.server_name = server_name
            if server_info.pro_organization_id:
                self.organization_id = server_info.pro_organization_id
            if server_info.pro_tenant_id:
                self.server_id = server_info.pro_tenant_id
            if server_info.pro_organization_name:
                self.organization_name = server_info.pro_organization_name
            if server_info.pro_tenant_name:
                self.tenant_name = server_info.pro_tenant_name
            if server_info.pro_api_url:
                self.pro_api_url = server_info.pro_api_url
            if server_info.pro_dashboard_url:
                self.pro_dashboard_url = server_info.pro_dashboard_url
            self.version = server_info.version or self.version
            # The server information was retrieved from the server itself, so we
            # can assume that the server is available
            self.status = "available"
        else:
            self.deployment_type = ServerDeploymentType.CLOUD
            self.server_id = server_info.id
            self.server_name = server_info.name
            self.organization_name = server_info.organization_name
            self.organization_id = server_info.organization_id
            self.tenant_name = server_info.name
            self.tenant_id = server_info.id
            self.status = server_info.status
            self.version = server_info.version

    @property
    def is_available(self) -> bool:
        """Check if the server is available (running and authenticated).

        Returns:
            True if the server is available, False otherwise.
        """
        if self.status not in [TenantStatus.AVAILABLE, ServiceState.ACTIVE]:
            return False
        if (
            self.api_key
            or self.api_token
            or self.username
            and self.password is not None
            or self.type in [ServerType.PRO, ServerType.LOCAL]
        ):
            return True
        if self.api_token and not self.api_token.expired:
            return True
        return False

    @property
    def auth_status(self) -> str:
        """Get the authentication status.

        Returns:
            The authentication status.
        """
        if self.api_key:
            return "API key"
        if self.username and self.password is not None:
            return "password"
        if not self.api_token:
            if self.type == ServerType.LOCAL:
                return "no authentication required"
            return "N/A"
        expires_at = self.api_token.expires_at_with_leeway
        if not expires_at:
            return "never expires"
        if expires_at < utc_now(tz_aware=expires_at):
            return "expired at " + self.expires_at

        return f"valid until {self.expires_at} (in {self.expires_in})"

    @property
    def expires_at(self) -> str:
        """Get the expiration time of the token as a string.

        Returns:
            The expiration time of the token as a string.
        """
        if not self.api_token:
            return "N/A"
        expires_at = self.api_token.expires_at_with_leeway
        if not expires_at:
            return "never"

        # Convert the date in the local timezone
        local_expires_at = to_local_tz(expires_at)
        return local_expires_at.strftime("%Y-%m-%d %H:%M:%S %Z")

    @property
    def expires_in(self) -> str:
        """Get the time remaining until the token expires.

        Returns:
            The time remaining until the token expires.
        """
        if not self.api_token:
            return "N/A"
        expires_at = self.api_token.expires_at_with_leeway
        if not expires_at:
            return "never"

        # Get the time remaining until the token expires
        expires_in = expires_at - utc_now(tz_aware=expires_at)
        return get_human_readable_time(expires_in.total_seconds())

    @property
    def dashboard_url(self) -> str:
        """Get the URL to the ZenML dashboard for this server.

        Returns:
            The URL to the ZenML dashboard for this server.
        """
        if self.organization_id and self.server_id:
            return (
                (self.pro_dashboard_url or ZENML_PRO_URL)
                + f"/organizations/{str(self.organization_id)}/tenants/{str(self.server_id)}"
            )

        return self.url

    @property
    def dashboard_organization_url(self) -> str:
        """Get the URL to the ZenML Pro dashboard for this tenant's organization.

        Returns:
            The URL to the ZenML Pro dashboard for this tenant's organization.
        """
        if self.organization_id:
            return (
                self.pro_dashboard_url or ZENML_PRO_URL
            ) + f"/organizations/{str(self.organization_id)}"
        return ""

    @property
    def dashboard_hyperlink(self) -> str:
        """Get the hyperlink to the ZenML dashboard for this tenant.

        Returns:
            The hyperlink to the ZenML dashboard for this tenant.
        """
        return f"[link={self.dashboard_url}]{self.dashboard_url}[/link]"

    @property
    def api_hyperlink(self) -> str:
        """Get the hyperlink to the ZenML OpenAPI dashboard for this tenant.

        Returns:
            The hyperlink to the ZenML OpenAPI dashboard for this tenant.
        """
        api_url = self.url + "/docs"
        return f"[link={api_url}]{self.url}[/link]"

    @property
    def server_name_hyperlink(self) -> str:
        """Get the hyperlink to the ZenML dashboard for this server using its name.

        Returns:
            The hyperlink to the ZenML dashboard for this server using its name.
        """
        if self.server_name is None:
            return "N/A"
        return f"[link={self.dashboard_url}]{self.server_name}[/link]"

    @property
    def server_id_hyperlink(self) -> str:
        """Get the hyperlink to the ZenML dashboard for this server using its ID.

        Returns:
            The hyperlink to the ZenML dashboard for this server using its ID.
        """
        if self.server_id is None:
            return "N/A"
        return f"[link={self.dashboard_url}]{str(self.server_id)}[/link]"

    @property
    def organization_hyperlink(self) -> str:
        """Get the hyperlink to the ZenML Pro dashboard for this server's organization.

        Returns:
            The hyperlink to the ZenML Pro dashboard for this server's
            organization.
        """
        if self.organization_name:
            return self.organization_name_hyperlink
        if self.organization_id:
            return self.organization_id_hyperlink
        return "N/A"

    @property
    def organization_name_hyperlink(self) -> str:
        """Get the hyperlink to the ZenML Pro dashboard for this server's organization using its name.

        Returns:
            The hyperlink to the ZenML Pro dashboard for this server's
            organization using its name.
        """
        if self.organization_name is None:
            return "N/A"
        return f"[link={self.dashboard_organization_url}]{self.organization_name}[/link]"

    @property
    def organization_id_hyperlink(self) -> str:
        """Get the hyperlink to the ZenML Pro dashboard for this tenant's organization using its ID.

        Returns:
            The hyperlink to the ZenML Pro dashboard for this tenant's
            organization using its ID.
        """
        if self.organization_id is None:
            return "N/A"
        return f"[link={self.dashboard_organization_url}]{self.organization_id}[/link]"
