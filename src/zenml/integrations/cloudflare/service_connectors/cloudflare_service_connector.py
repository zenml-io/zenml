#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Cloudflare service connector.

The Cloudflare service connector brokers authenticated access to Cloudflare
resources for ZenML stack components. It supports two resource types:

- ``cloudflare-generic``: hands back account-scoped Cloudflare API credentials
  (a bearer API token + account ID) for arbitrary Cloudflare REST API calls.
- ``r2-bucket``: hands back a pre-configured, S3-compatible boto3 client scoped
  to a Cloudflare R2 bucket. This is what an R2 artifact store links to.

The two resource types are intentionally tied to the auth method that can serve
them: R2's data plane is the S3 API and needs SigV4 access-key credentials, while
the Cloudflare control plane uses a scoped bearer API token.
"""

from typing import Any, List, Optional, cast

import boto3
import requests
from botocore.exceptions import BotoCoreError, ClientError
from pydantic import Field

from zenml.exceptions import AuthorizationException
from zenml.integrations.cloudflare import (
    CLOUDFLARE_CONNECTOR_TYPE,
    CLOUDFLARE_GENERIC_RESOURCE_TYPE,
    CLOUDFLARE_R2_RESOURCE_TYPE,
)
from zenml.logger import get_logger
from zenml.models import (
    AuthenticationMethodModel,
    ResourceTypeModel,
    ServiceConnectorTypeModel,
)
from zenml.service_connectors.service_connector import (
    AuthenticationConfig,
    ServiceConnector,
)
from zenml.utils.enum_utils import StrEnum
from zenml.utils.secret_utils import PlainSerializedSecretStr

logger = get_logger(__name__)

CLOUDFLARE_API_BASE_URL = "https://api.cloudflare.com/client/v4"
R2_ENDPOINT_TEMPLATE = "https://{account_id}.r2.cloudflarestorage.com"


class CloudflareBaseConfig(AuthenticationConfig):
    """Base configuration shared by all Cloudflare auth methods."""

    account_id: str = Field(
        title="Cloudflare Account ID",
        description="Cloudflare account ID that scopes the connector. Found in "
        "the Cloudflare dashboard URL or account settings. Example: "
        "'a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6'",
    )


class CloudflareApiTokenConfig(CloudflareBaseConfig):
    """Configuration for scoped Cloudflare API token authentication."""

    api_token: PlainSerializedSecretStr = Field(
        title="Cloudflare API Token",
        description="Scoped Cloudflare API token (bearer token) with the "
        "permissions required by the consuming component, e.g. R2 read/write "
        "or Workers Scripts write. Created from the Cloudflare dashboard under "
        "My Profile > API Tokens or Account API Tokens",
    )


class CloudflareR2Config(CloudflareBaseConfig):
    """Configuration for R2 S3-compatible credentials."""

    aws_access_key_id: PlainSerializedSecretStr = Field(
        title="R2 Access Key ID",
        description="R2 S3-compatible Access Key ID, generated from an R2 API "
        "token in the Cloudflare dashboard (R2 > Manage API Tokens)",
    )
    aws_secret_access_key: PlainSerializedSecretStr = Field(
        title="R2 Secret Access Key",
        description="R2 S3-compatible Secret Access Key that pairs with the "
        "Access Key ID. Only shown once when the R2 API token is created",
    )


class CloudflareAuthenticationMethods(StrEnum):
    """Cloudflare authentication methods."""

    API_TOKEN = "api-token"
    R2_CREDENTIALS = "r2-credentials"


CLOUDFLARE_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="Cloudflare Service Connector",
    connector_type=CLOUDFLARE_CONNECTOR_TYPE,
    description="""
The ZenML Cloudflare Service Connector facilitates authenticating and
connecting to Cloudflare resources. It brokers two distinct planes:

- Cloudflare R2 object storage (the S3-compatible data plane), used by the R2
  Artifact Store.
- The Cloudflare account API (control plane), used by components that call the
  Cloudflare REST API directly.

Because R2's data plane is S3-compatible, the `r2-bucket` resource type hands
back a regular boto3 S3 client pointed at the account's R2 endpoint, while the
`cloudflare-generic` resource type hands back the API token and account ID for
arbitrary Cloudflare API calls.
""",
    supports_auto_configuration=False,
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/cloudflare/cloudflare.png",
    emoji=":cloud:",
    auth_methods=[
        AuthenticationMethodModel(
            name="Cloudflare API Token",
            auth_method=CloudflareAuthenticationMethods.API_TOKEN,
            description="""
Authenticate with a scoped Cloudflare API token. Recommended for control-plane
access. Apply least privilege by granting only the permissions the consuming
component needs. The token is validated server-side against the Cloudflare API.
""",
            config_class=CloudflareApiTokenConfig,
        ),
        AuthenticationMethodModel(
            name="R2 S3 Credentials",
            auth_method=CloudflareAuthenticationMethods.R2_CREDENTIALS,
            description="""
Authenticate to Cloudflare R2 with S3-compatible credentials (Access Key ID and
Secret Access Key) generated from an R2 API token. Used for the `r2-bucket`
resource type, which serves the S3 data plane.
""",
            config_class=CloudflareR2Config,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="Generic Cloudflare resource",
            resource_type=CLOUDFLARE_GENERIC_RESOURCE_TYPE,
            description="""
Multi-purpose Cloudflare resource type. Hands back the account-scoped API token
and account ID so consumers can construct their own Cloudflare API clients for
arbitrary services (Workers, Containers, Workflows, account management). Only
the `api-token` authentication method is supported.
""",
            auth_methods=[CloudflareAuthenticationMethods.API_TOKEN],
            supports_instances=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/cloudflare/cloudflare.png",
            emoji=":cloud:",
        ),
        ResourceTypeModel(
            name="Cloudflare R2 bucket",
            resource_type=CLOUDFLARE_R2_RESOURCE_TYPE,
            description="""
Allows access to a Cloudflare R2 bucket through an S3-compatible client. When
linked to an R2 Artifact Store, the connector brokers the S3 credentials while
the artifact store supplies the R2 endpoint (derived from its account ID).
Resource IDs are R2 bucket URIs of the form `r2://{bucket-name}`. Only the
`r2-credentials` authentication method is supported.
""",
            auth_methods=[CloudflareAuthenticationMethods.R2_CREDENTIALS],
            supports_instances=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/cloudflare/cloudflare.png",
            emoji=":package:",
        ),
    ],
)


class CloudflareServiceConnector(ServiceConnector):
    """Cloudflare service connector."""

    config: CloudflareBaseConfig

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector type specification.

        Returns:
            The service connector type specification.
        """
        return CLOUDFLARE_SERVICE_CONNECTOR_TYPE_SPEC

    @property
    def r2_endpoint_url(self) -> str:
        """The R2 S3 API endpoint for the configured account.

        Returns:
            The R2 S3-compatible endpoint URL.
        """
        return R2_ENDPOINT_TEMPLATE.format(account_id=self.config.account_id)

    @staticmethod
    def _parse_r2_resource_id(resource_id: str) -> str:
        """Extract the bare bucket name from an R2 resource ID.

        Args:
            resource_id: An R2 bucket URI or bare bucket name (e.g.
                `r2://my-bucket`, `s3://my-bucket` or `my-bucket`).

        Returns:
            The bare bucket name.

        Raises:
            ValueError: If the resource ID is not a valid R2 bucket reference.
        """
        for prefix in ("r2://", "s3://"):
            if resource_id.startswith(prefix):
                resource_id = resource_id[len(prefix) :]
                break
        bucket = resource_id.strip("/")
        if not bucket or "/" in bucket:
            raise ValueError(
                f"Invalid R2 bucket resource ID: '{resource_id}'. Expected a "
                "bucket name or a URI of the form 'r2://my-bucket'."
            )
        return bucket

    def _canonical_resource_id(
        self, resource_type: str, resource_id: str
    ) -> str:
        """Convert a resource ID to its canonical form.

        Args:
            resource_type: The resource type.
            resource_id: The resource ID.

        Returns:
            The canonical resource ID.
        """
        if resource_type == CLOUDFLARE_R2_RESOURCE_TYPE:
            return f"r2://{self._parse_r2_resource_id(resource_id)}"
        return resource_id

    def _get_default_resource_id(self, resource_type: str) -> str:
        """Get the default resource ID for a resource type.

        Args:
            resource_type: The resource type.

        Returns:
            The default resource ID.

        Raises:
            RuntimeError: If the resource type does not have a default
                resource ID.
        """
        if resource_type == CLOUDFLARE_GENERIC_RESOURCE_TYPE:
            return self.config.account_id
        raise RuntimeError(
            f"The resource type '{resource_type}' does not support a default "
            "resource ID."
        )

    def _r2_client(self) -> Any:
        """Build a boto3 S3 client for the configured R2 account.

        Returns:
            A boto3 S3 client pointed at the R2 endpoint.
        """
        config = cast(CloudflareR2Config, self.config)
        session = boto3.Session(
            aws_access_key_id=config.aws_access_key_id.get_secret_value(),
            aws_secret_access_key=config.aws_secret_access_key.get_secret_value(),
            # R2 ignores the region, but botocore's SigV4 signer requires one.
            region_name="auto",
        )
        client = session.client("s3", endpoint_url=self.r2_endpoint_url)
        # Consumers (e.g. the S3/R2 artifact store) read credentials off the
        # client object to configure third-party filesystems.
        client.credentials = session.get_credentials()
        return client

    def _verify_api_token(self) -> None:
        """Verify the Cloudflare API token against the Cloudflare API.

        Raises:
            AuthorizationException: If the token is invalid or the request
                fails.
        """
        config = cast(CloudflareApiTokenConfig, self.config)
        try:
            response = requests.get(
                f"{CLOUDFLARE_API_BASE_URL}/user/tokens/verify",
                headers={
                    "Authorization": f"Bearer {config.api_token.get_secret_value()}"
                },
                timeout=30,
            )
        except requests.RequestException as e:
            raise AuthorizationException(
                f"Failed to reach the Cloudflare API to verify the token: {e}"
            ) from e

        if not response.ok or not response.json().get("success", False):
            raise AuthorizationException(
                "Failed to verify Cloudflare API token: the token is invalid "
                "or lacks the required permissions."
            )

    def _connect_to_resource(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a Cloudflare resource.

        Args:
            kwargs: Additional implementation specific keyword arguments.

        Returns:
            For `r2-bucket`, a boto3 S3 client scoped to the R2 endpoint. For
            `cloudflare-generic`, the API token and account ID for building
            Cloudflare API clients.

        Raises:
            NotImplementedError: If the resource type is not supported.
        """
        resource_type = self.resource_type
        assert resource_type is not None

        if resource_type == CLOUDFLARE_R2_RESOURCE_TYPE:
            return self._r2_client()

        if resource_type == CLOUDFLARE_GENERIC_RESOURCE_TYPE:
            config = cast(CloudflareApiTokenConfig, self.config)
            return {
                "account_id": config.account_id,
                "api_token": config.api_token.get_secret_value(),
            }

        raise NotImplementedError(
            f"Connecting to {resource_type} resources is not supported by the "
            "Cloudflare connector."
        )

    def _configure_local_client(
        self,
        **kwargs: Any,
    ) -> None:
        """Configure a local client to connect to a Cloudflare resource.

        Args:
            kwargs: Additional implementation specific keyword arguments.

        Raises:
            NotImplementedError: Local client configuration is not supported.
        """
        raise NotImplementedError(
            "Local client configuration is not supported by the Cloudflare "
            "connector. Configure your client directly with the brokered "
            "credentials instead."
        )

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "CloudflareServiceConnector":
        """Auto-configure a connector instance.

        Args:
            auth_method: The authentication method to use.
            resource_type: The resource type to configure.
            resource_id: The resource ID to configure.
            kwargs: Additional implementation specific keyword arguments.

        Returns:
            A configured connector instance (never returned; always raises).

        Raises:
            NotImplementedError: Auto-configuration is not supported.
        """
        raise NotImplementedError(
            "Auto-configuration is not supported by the Cloudflare connector. "
            "Please provide the account ID and credentials explicitly."
        )

    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """Verify and list the resources the connector can access.

        Args:
            resource_type: The resource type to verify.
            resource_id: The specific resource ID to verify.

        Returns:
            The list of canonical resource IDs the connector can access. Empty
            if no resource type is specified.

        Raises:
            AuthorizationException: If the connector cannot authenticate or
                access the specified resource.
        """
        if resource_type == CLOUDFLARE_GENERIC_RESOURCE_TYPE:
            self._verify_api_token()
            return [self.config.account_id]

        if resource_type == CLOUDFLARE_R2_RESOURCE_TYPE:
            client = self._r2_client()
            if not resource_id:
                try:
                    response = client.list_buckets()
                except (ClientError, BotoCoreError) as e:
                    msg = f"failed to list R2 buckets: {e}"
                    logger.error(msg)
                    raise AuthorizationException(msg) from e
                return [
                    f"r2://{bucket['Name']}"
                    for bucket in response.get("Buckets", [])
                ]

            bucket_name = self._parse_r2_resource_id(resource_id)
            try:
                client.head_bucket(Bucket=bucket_name)
            except (ClientError, BotoCoreError) as e:
                msg = f"failed to access R2 bucket '{bucket_name}': {e}"
                logger.error(msg)
                raise AuthorizationException(msg) from e
            return [f"r2://{bucket_name}"]

        # No resource type specified: verify we can authenticate at all using
        # whichever auth method is configured.
        if isinstance(self.config, CloudflareR2Config):
            client = self._r2_client()
            try:
                client.list_buckets()
            except (ClientError, BotoCoreError) as e:
                raise AuthorizationException(
                    f"failed to verify R2 credentials: {e}"
                ) from e
        else:
            self._verify_api_token()
        return []
