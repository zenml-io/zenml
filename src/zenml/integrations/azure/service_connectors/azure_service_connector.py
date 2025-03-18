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
"""Azure Service Connector."""

import datetime
import json
import logging
import re
import subprocess
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import requests
import yaml
from azure.core.credentials import AccessToken, TokenCredential
from azure.core.exceptions import AzureError
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.containerregistry import ContainerRegistryManagementClient
from azure.mgmt.containerservice import ContainerServiceClient
from azure.mgmt.resource import SubscriptionClient
from azure.mgmt.storage import StorageManagementClient
from azure.storage.blob import BlobServiceClient
from pydantic import Field

from zenml.constants import (
    DOCKER_REGISTRY_RESOURCE_TYPE,
    KUBERNETES_CLUSTER_RESOURCE_TYPE,
)
from zenml.exceptions import AuthorizationException
from zenml.integrations.azure import (
    AZURE_CONNECTOR_TYPE,
    AZURE_RESOURCE_TYPE,
    BLOB_RESOURCE_TYPE,
)
from zenml.logger import get_logger
from zenml.models import (
    AuthenticationMethodModel,
    ResourceTypeModel,
    ServiceConnectorTypeModel,
)
from zenml.service_connectors.docker_service_connector import (
    DockerAuthenticationMethods,
    DockerConfiguration,
    DockerServiceConnector,
)
from zenml.service_connectors.service_connector import (
    AuthenticationConfig,
    ServiceConnector,
)
from zenml.utils.enum_utils import StrEnum
from zenml.utils.secret_utils import PlainSerializedSecretStr
from zenml.utils.time_utils import to_local_tz, to_utc_timezone, utc_now

# Configure the logging level for azure.identity
logging.getLogger("azure.identity").setLevel(logging.WARNING)

logger = get_logger(__name__)


AZURE_MANAGEMENT_TOKEN_SCOPE = "https://management.azure.com/.default"
AZURE_SESSION_TOKEN_DEFAULT_EXPIRATION_TIME = 60 * 60  # 1 hour
AZURE_SESSION_EXPIRATION_BUFFER = 15  # 15 minutes
AZURE_ACR_OAUTH_SCOPE = "repository:*:*"


class AzureBaseConfig(AuthenticationConfig):
    """Azure base configuration."""

    subscription_id: Optional[UUID] = Field(
        default=None,
        title="Azure Subscription ID",
        description="The subscription ID of the Azure account. If not "
        "specified, ZenML will attempt to retrieve the subscription ID from "
        "Azure using the configured credentials.",
    )
    tenant_id: Optional[UUID] = Field(
        default=None,
        title="Azure Tenant ID",
        description="The tenant ID of the Azure account. If not specified, "
        "ZenML will attempt to retrieve the tenant from Azure using the "
        "configured credentials.",
    )
    resource_group: Optional[str] = Field(
        default=None,
        title="Azure Resource Group",
        description="A resource group may be used to restrict the scope of "
        "Azure resources like AKS clusters and ACR repositories. If not "
        "specified, ZenML will retrieve resources from all resource groups "
        "accessible with the configured credentials.",
    )
    storage_account: Optional[str] = Field(
        default=None,
        title="Azure Storage Account",
        description="The name of an Azure storage account may be used to "
        "restrict the scope of Azure Blob storage containers. If not "
        "specified, ZenML will retrieve blob containers from all storage "
        "accounts accessible with the configured credentials.",
    )


class AzureClientSecret(AuthenticationConfig):
    """Azure client secret credentials."""

    client_secret: PlainSerializedSecretStr = Field(
        title="Service principal client secret",
        description="The client secret of the service principal",
    )


class AzureClientConfig(AzureBaseConfig):
    """Azure client configuration."""

    client_id: UUID = Field(
        title="Azure Client ID",
        description="The service principal's client ID",
    )
    tenant_id: UUID = Field(
        title="Azure Tenant ID",
        description="ID of the service principal's tenant. Also called its "
        "'directory' ID.",
    )


class AzureAccessToken(AuthenticationConfig):
    """Azure access token credentials."""

    token: PlainSerializedSecretStr = Field(
        title="Azure Access Token",
        description="The Azure access token to use for authentication",
    )


class AzureServicePrincipalConfig(AzureClientConfig, AzureClientSecret):
    """Azure service principal configuration."""


class AzureAccessTokenConfig(AzureBaseConfig, AzureAccessToken):
    """Azure token configuration."""


class AzureAuthenticationMethods(StrEnum):
    """Azure Authentication methods."""

    IMPLICIT = "implicit"
    SERVICE_PRINCIPAL = "service-principal"
    ACCESS_TOKEN = "access-token"


class ZenMLAzureTokenCredential(TokenCredential):
    """ZenML Azure token credential.

    This class is used to provide a pre-configured token credential to Azure
    clients. Tokens are generated from other Azure credentials and are served
    to Azure clients to authenticate requests.
    """

    def __init__(self, token: str, expires_at: datetime.datetime):
        """Initialize ZenML Azure token credential.

        Args:
            token: The token to use for authentication
            expires_at: The expiration time of the token
        """
        self.token = token

        # Convert the expiration time from UTC to local time
        self.expires_on = int(to_local_tz(expires_at).timestamp())

    def get_token(self, *scopes: str, **kwargs: Any) -> Any:
        """Get token.

        Args:
            *scopes: Scopes
            **kwargs: Keyword arguments

        Returns:
            Token
        """
        return AccessToken(token=self.token, expires_on=self.expires_on)


AZURE_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="Azure Service Connector",
    connector_type=AZURE_CONNECTOR_TYPE,
    description="""
The ZenML Azure Service Connector facilitates the authentication and access to
managed Azure services and resources. These encompass a range of resources,
including blob storage containers, ACR repositories, and AKS clusters.

This connector also supports automatic configuration and detection of
credentials locally configured through the Azure CLI.

This connector serves as a general means of accessing any Azure service by
issuing credentials to clients. Additionally, the connector can handle
specialized authentication for Azure blob storage, Docker and Kubernetes Python
clients. It also allows for the configuration of local Docker and Kubernetes
CLIs.

The Azure Service Connector is part of the Azure ZenML integration. You can
either install the entire integration or use a pypi extra to install it
independently of the integration:

* `pip install "zenml[connectors-azure]"` installs only prerequisites for the
Azure Service Connector Type
* `zenml integration install azure` installs the entire Azure ZenML integration

It is not required to [install and set up the Azure CLI](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli)
on your local machine to use the Azure Service Connector to link Stack
Components to Azure resources and services. However, it is recommended to do so
if you are looking for a quick setup that includes using the auto-configuration
Service Connector features.
""",
    supports_auto_configuration=True,
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/azure/azure.png",
    emoji=":regional_indicator_a: ",
    auth_methods=[
        AuthenticationMethodModel(
            name="Azure Implicit Authentication",
            auth_method=AzureAuthenticationMethods.IMPLICIT,
            description="""
Implicit authentication to Azure services using environment variables, local
configuration files, workload or managed identities. This authentication method
doesn't require any credentials to be explicitly configured. It automatically
discovers and uses credentials from one of the following sources:

- [environment variables](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme?view=azure-python#environment-variables)
- workload identity - if the application is deployed to an Azure Kubernetes
Service with Managed Identity enabled. This option can only be used when running
the ZenML server on an AKS cluster.
- managed identity - if the application is deployed to an Azure host with
Managed Identity enabled. This option can only be used when running the ZenML client or server on
an Azure host.
- Azure CLI - if a user has signed in via [the Azure CLI `az login` command](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli).

This is the quickest and easiest way to authenticate to Azure services. However,
the results depend on how ZenML is deployed and the environment where it is used
and is thus not fully reproducible:

- when used with the default local ZenML deployment or a local ZenML server, the
credentials are the same as those used by the Azure CLI or extracted from local
environment variables.
- when connected to a ZenML server, this method only works if the ZenML server
is deployed in Azure and will use the workload identity attached to the Azure
resource where the ZenML server is running (e.g. an AKS cluster). The
permissions of the managed identity may need to be adjusted to allow listing
and accessing/describing the Azure resources that the connector is configured to
access.

Note that the discovered credentials inherit the full set of permissions of the
local Azure CLI configuration, environment variables or remote Azure managed
identity. Depending on the extent of those permissions, this authentication
method might not be recommended for production use, as it can lead to accidental
privilege escalation. Instead, it is recommended to use the Azure service
principal authentication method to limit the validity and/or permissions of the
credentials being issued to connector clients.
""",
            config_class=AzureBaseConfig,
        ),
        AuthenticationMethodModel(
            name="Azure Service Principal",
            auth_method=AzureAuthenticationMethods.SERVICE_PRINCIPAL,
            description="""
Azure service principal credentials consisting of an Azure client ID and
client secret. These credentials are used to authenticate clients to Azure
services.

For this authentication method, the Azure Service Connector requires
[an Azure service principal to be created](https://learn.microsoft.com/en-us/azure/developer/python/sdk/authentication-on-premises-apps?tabs=azure-portal)
and a client secret to be generated.
""",
            config_class=AzureServicePrincipalConfig,
        ),
        AuthenticationMethodModel(
            name="Azure Access Token",
            auth_method=AzureAuthenticationMethods.ACCESS_TOKEN,
            description="""
Uses temporary Azure access tokens explicitly configured by the user or
auto-configured from a local environment. This method has the major limitation
that the user must regularly generate new tokens and update the connector
configuration as API tokens expire. On the other hand, this method is ideal in
cases where the connector only needs to be used for a short period of time, such
as sharing access temporarily with someone else in your team.

This is the authentication method used during auto-configuration, if you have
[the local Azure CLI set up with credentials](https://learn.microsoft.com/en-us/cli/azure/authenticate-azure-cli).
The connector will generate an access token from the Azure CLI credentials and
store it in the connector configuration.

Given that Azure access tokens are scoped to a particular Azure resource and the
access token generated during auto-configuration is scoped to the Azure
Management API, this method does not work with Azure blob storage resources. You
should use the Azure service principal authentication method for blob storage
resources instead.
""",
            config_class=AzureAccessTokenConfig,
            default_expiration_seconds=AZURE_SESSION_TOKEN_DEFAULT_EXPIRATION_TIME,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="Generic Azure resource",
            resource_type=AZURE_RESOURCE_TYPE,
            description="""
Multi-purpose Azure resource type. It allows Stack Components to use the
connector to connect to any Azure service. When used by Stack Components, they
are provided generic azure-identity credentials that can be used to create
Azure python clients for any particular Azure service.

This generic Azure resource type is meant to be used with Stack Components that
are not represented by other, more specific resource types, like Azure blob
storage containers, Kubernetes clusters or Docker registries. It should be
accompanied by a matching set of Azure permissions that allow access to the set
of remote resources required by the client(s).

The resource name represents the name of the Azure subscription that the
connector is authorized to access.
""",
            auth_methods=AzureAuthenticationMethods.values(),
            # Don't request an Azure specific resource instance ID.
            supports_instances=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/azure/azure.png",
            emoji=":regional_indicator_a: ",
        ),
        ResourceTypeModel(
            name="Azure Blob Storage Container",
            resource_type=BLOB_RESOURCE_TYPE,
            description="""
Allows Stack Components to connect to Azure Blob containers. When used by Stack
Components, they are provided a pre-configured Azure Blob Storage client.

The configured credentials must have at least the following
Azure IAM permissions associated with the blob storage account or containers
that the connector that the connector will be allowed to access:

- allow read and write access to blobs (e.g. the `Storage Blob Data Contributor`
role)
- allow listing the storage accounts (e.g. the `Reader and Data
Access` role). This is only required if a storage account is not configured in
the connector.
- allow listing the containers in a storage account (e.g. the `Reader and Data
Access` role)

If set, the resource name must identify an Azure blob container using one of the following
formats:

- Azure blob container URI (canonical resource name): `{az|abfs}://{container-name}`
- Azure blob container name: `{container-name}`

If a storage account is configured in the connector, only blob storage
containers in that storage account will be accessible. Otherwise, if a resource
group is configured in the connector, only blob storage containers
in storage accounts in that resource group will be accessible. Finally, if
neither a storage account nor a resource group is configured in the connector,
all blob storage containers in all accessible storage accounts will be
accessible.

The only Azure authentication methods that work with Azure blob storage resources are the implicit 
authentication and the service principal authentication method.
""",
            auth_methods=AzureAuthenticationMethods.values(),
            # Request a blob container to be configured in the
            # connector or provided by the consumer
            supports_instances=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/azure.png",
            emoji=":package:",
        ),
        ResourceTypeModel(
            name="AKS Kubernetes cluster",
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
            description="""
Allows Stack Components to access an AKS cluster as a standard Kubernetes
cluster resource. When used by Stack Components, they are provided a
pre-authenticated python-kubernetes client instance.

The configured credentials must have at least the following
Azure IAM permissions associated with the AKS clusters
that the connector will be allowed to access:

- allow listing the AKS clusters and fetching their credentials (e.g. the
`Azure Kubernetes Service Cluster Admin Role` role)

If set, the resource name must identify an EKS cluster using one of the
following formats:

- resource group scoped AKS cluster name (canonical): `[{resource-group}/]{cluster-name}`
- AKS cluster name: `{cluster-name}`

Given that the AKS cluster name is unique within a resource group, the
resource group name may be included in the resource name to avoid ambiguity. If
a resource group is configured in the connector, the resource group name
in the resource name must match the configured resource group. If no resource
group is configured in the connector and a resource group name is not included
in the resource name, the connector will attempt to find the AKS cluster in
any resource group.

If a resource group is configured in the connector, only AKS clusters in that
resource group will be accessible.
""",
            auth_methods=AzureAuthenticationMethods.values(),
            # Request an AKS cluster name to be configured in the
            # connector or provided by the consumer
            supports_instances=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png",
            emoji=":cyclone:",
        ),
        ResourceTypeModel(
            name="ACR container registry",
            resource_type=DOCKER_REGISTRY_RESOURCE_TYPE,
            description="""
Allows Stack Components to access one or more ACR registries as a standard
Docker registry resource. When used by Stack Components, they are provided a
pre-authenticated python-docker client instance.

The configured credentials must have at least the following
Azure IAM permissions associated with the ACR registries
that the connector that the connector will be allowed to access:

- allow access to pull and push images (e.g. the `AcrPull` and `AcrPush` roles)
- allow access to list registries (e.g. the `Contributor` role)

If set, the resource name must identify an ACR registry using one of the
following formats:

- ACR registry URI (canonical resource name): `[https://]{registry-name}.azurecr.io`
- ACR registry name: `{registry-name}`

If a resource group is configured in the connector, only ACR registries in that
resource group will be accessible.

If an authentication method other than the Azure service principal is used, Entra ID authentication is used.
This requires the configured identity to have the `AcrPush` role to be configured.
If this fails, admin account authentication is tried. For this the admin account must be enabled for the registry.
See the official Azure[documentation on the admin account](https://docs.microsoft.com/en-us/azure/container-registry/container-registry-authentication#admin-account) for more information. 
""",
            auth_methods=AzureAuthenticationMethods.values(),
            supports_instances=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png",
            emoji=":whale:",
        ),
    ],
)


class AzureServiceConnector(ServiceConnector):
    """Azure service connector."""

    config: AzureBaseConfig

    _subscription_id: Optional[str] = None
    _subscription_name: Optional[str] = None
    _tenant_id: Optional[str] = None
    _session_cache: Dict[
        str,
        Tuple[TokenCredential, Optional[datetime.datetime]],
    ] = {}

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector type specification.

        Returns:
            The service connector type specification.
        """
        return AZURE_SERVICE_CONNECTOR_TYPE_SPEC

    @property
    def subscription(self) -> Tuple[str, str]:
        """Get the Azure subscription ID and name.

        Returns:
            The Azure subscription ID and name.

        Raises:
            AuthorizationException: If the Azure subscription could not be
                determined or doesn't match the configured subscription ID.
        """
        if self._subscription_id is None or self._subscription_name is None:
            logger.debug("Getting subscription from Azure...")
            try:
                credential, _ = self.get_azure_credential(self.auth_method)
                subscription_client = SubscriptionClient(credential)
                if self.config.subscription_id is not None:
                    subscription = subscription_client.subscriptions.get(
                        str(self.config.subscription_id)
                    )
                    self._subscription_name = subscription.display_name
                    self._subscription_id = subscription.subscription_id
                else:
                    subscriptions = list(
                        subscription_client.subscriptions.list()
                    )
                    if len(subscriptions) == 0:
                        raise AuthorizationException(
                            "no Azure subscriptions found for the configured "
                            "credentials."
                        )
                    if len(subscriptions) > 1:
                        raise AuthorizationException(
                            "multiple Azure subscriptions found for the "
                            "configured credentials. Please configure the "
                            "subscription ID explicitly in the connector."
                        )

                    subscription = subscriptions[0]
                    self._subscription_id = subscription.subscription_id
                    self._subscription_name = subscription.display_name
            except AzureError as e:
                raise AuthorizationException(
                    f"failed to fetch the Azure subscription: {e}"
                ) from e

        assert self._subscription_id is not None
        assert self._subscription_name is not None
        return self._subscription_id, self._subscription_name

    @property
    def tenant_id(self) -> str:
        """Get the Azure tenant ID.

        Returns:
            The Azure tenant ID.

        Raises:
            AuthorizationException: If the Azure tenant ID could not be
                determined or doesn't match the configured tenant ID.
        """
        if self._tenant_id is None:
            logger.debug("Getting tenant ID from Azure...")
            try:
                credential, _ = self.get_azure_credential(self.auth_method)
                subscription_client = SubscriptionClient(credential)
                tenants = subscription_client.tenants.list()

                if self.config.tenant_id is not None:
                    for tenant in tenants:
                        if str(tenant.tenant_id) == str(self.config.tenant_id):
                            self._tenant_id = str(tenant.tenant_id)
                            break
                    else:
                        raise AuthorizationException(
                            "the configured tenant ID is not associated with "
                            "the configured credentials."
                        )
                else:
                    tenants = list(tenants)
                    if len(tenants) == 0:
                        raise AuthorizationException(
                            "no Azure tenants found for the configured "
                            "credentials."
                        )
                    if len(tenants) > 1:
                        raise AuthorizationException(
                            "multiple Azure tenants found for the "
                            "configured credentials. Please configure the "
                            "tenant ID explicitly in the connector."
                        )

                    tenant = tenants[0]
                    self._tenant_id = tenant.tenant_id
            except AzureError as e:
                raise AuthorizationException(
                    f"failed to fetch the Azure tenant: {e}"
                ) from e
        assert self._tenant_id is not None
        return self._tenant_id

    def get_azure_credential(
        self,
        auth_method: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Tuple[TokenCredential, Optional[datetime.datetime]]:
        """Get an Azure credential for the specified resource.

        Args:
            auth_method: The authentication method to use.
            resource_type: The resource type to get a credential for.
            resource_id: The resource ID to get a credential for.

        Returns:
            An Azure credential for the specified resource and its expiration
            timestamp, if applicable.
        """
        # We maintain a cache of all sessions to avoid re-authenticating
        # multiple times for the same resource
        key = auth_method
        if key in self._session_cache:
            session, expires_at = self._session_cache[key]
            if expires_at is None:
                return session, None

            # Refresh expired sessions

            # check if the token expires in the near future
            if expires_at > utc_now(tz_aware=expires_at) + datetime.timedelta(
                minutes=AZURE_SESSION_EXPIRATION_BUFFER
            ):
                return session, expires_at

        logger.debug(
            f"Creating Azure credential for auth method '{auth_method}', "
            f"resource type '{resource_type}' and resource ID "
            f"'{resource_id}'..."
        )
        session, expires_at = self._authenticate(
            auth_method, resource_type, resource_id
        )
        self._session_cache[key] = (session, expires_at)
        return session, expires_at

    def _authenticate(
        self,
        auth_method: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Tuple[TokenCredential, Optional[datetime.datetime]]:
        """Authenticate to Azure and return a token credential.

        Args:
            auth_method: The authentication method to use.
            resource_type: The resource type to authenticate for.
            resource_id: The resource ID to authenticate for.

        Returns:
            An Azure token credential and the expiration time of the
            temporary credentials if applicable.

        Raises:
            NotImplementedError: If the authentication method is not supported.
            AuthorizationException: If the authentication failed.
        """
        cfg = self.config
        credential: TokenCredential
        if auth_method == AzureAuthenticationMethods.IMPLICIT:
            self._check_implicit_auth_method_allowed()

            try:
                credential = DefaultAzureCredential()
            except AzureError as e:
                raise AuthorizationException(
                    f"Failed to authenticate to Azure using implicit "
                    f"authentication. Please check your local Azure CLI "
                    f"configuration or managed identity setup: {e}"
                )

            return credential, None

        if auth_method == AzureAuthenticationMethods.SERVICE_PRINCIPAL:
            assert isinstance(cfg, AzureServicePrincipalConfig)
            try:
                credential = ClientSecretCredential(
                    tenant_id=str(cfg.tenant_id),
                    client_id=str(cfg.client_id),
                    client_secret=cfg.client_secret.get_secret_value(),
                )
            except AzureError as e:
                raise AuthorizationException(
                    f"Failed to authenticate to Azure using the provided "
                    f"service principal credentials. Please check your Azure "
                    f"configuration: {e}"
                )

            return credential, None

        if auth_method == AzureAuthenticationMethods.ACCESS_TOKEN:
            assert isinstance(cfg, AzureAccessTokenConfig)

            expires_at = self.expires_at
            assert expires_at is not None

            credential = ZenMLAzureTokenCredential(
                token=cfg.token.get_secret_value(),
                expires_at=expires_at,
            )

            return credential, expires_at

        raise NotImplementedError(
            f"Authentication method '{auth_method}' is not supported by "
            "the Azure connector."
        )

    def _parse_blob_container_resource_id(self, resource_id: str) -> str:
        """Validate and convert an Azure blob resource ID to a container name.

        The resource ID could mean different things:

        - Azure blob container URI: `{az|abfs}://{container-name}`
        - Azure blob container name: `{container-name}`

        This method extracts the container name from the provided resource ID.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The container name.

        Raises:
            ValueError: If the provided resource ID is not a valid Azure blob
                resource ID.
        """
        container_name: Optional[str] = None
        if re.match(
            r"^(az|abfs)://[a-z0-9](?!.*--)[a-z0-9-]{1,61}[a-z0-9](/.*)*$",
            resource_id,
        ):
            # The resource ID is an Azure blob container URI
            container_name = resource_id.split("/")[2]
        elif re.match(
            r"^[a-z0-9](?!.*--)[a-z0-9-]{1,61}[a-z0-9]$",
            resource_id,
        ):
            # The resource ID is the Azure blob container name
            container_name = resource_id
        else:
            raise ValueError(
                f"Invalid resource ID for an Azure blob storage container: "
                f"{resource_id}. "
                "Supported formats are:\n"
                "Azure blob container URI: {az|abfs}://<container-name>\n"
                "Azure blob container name: <container-name>"
            )

        return container_name

    def _parse_acr_resource_id(
        self,
        resource_id: str,
    ) -> str:
        """Validate and convert an ACR resource ID to an ACR registry name.

        The resource ID could mean different things:

        - ACR registry URI: `[https://]{registry-name}.azurecr.io`
        - ACR registry name: `{registry-name}`

        This method extracts the registry name from the provided resource ID.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The ACR registry name.

        Raises:
            ValueError: If the provided resource ID is not a valid ACR
                resource ID.
        """
        registry_name: Optional[str] = None
        if re.match(
            r"^(https?://)?[a-zA-Z0-9]+\.azurecr\.io(/.+)*$",
            resource_id,
        ):
            # The resource ID is an ACR registry URI
            registry_name = resource_id.split(".")[0].split("/")[-1]
        elif re.match(
            r"^[a-zA-Z0-9]+$",
            resource_id,
        ):
            # The resource ID is an ACR registry name
            registry_name = resource_id
        else:
            raise ValueError(
                f"Invalid resource ID for a ACR registry: {resource_id}. "
                f"Supported formats are:\n"
                "ACR registry URI: [https://]{registry-name}.azurecr.io\n"
                "ACR registry name: {registry-name}"
            )

        return registry_name

    def _parse_aks_resource_id(
        self, resource_id: str
    ) -> Tuple[Optional[str], str]:
        """Validate and convert an AKS resource ID to an AKS cluster name.

        The resource ID could mean different things:

        - resource group scoped AKS cluster name (canonical): `{resource-group}/{cluster-name}`
        - AKS cluster name: `{cluster-name}`

        This method extracts the resource group name and cluster name from the
        provided resource ID.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The Azure resource group and AKS cluster name.

        Raises:
            ValueError: If the provided resource ID is not a valid AKS cluster
                name.
        """
        resource_group: Optional[str] = self.config.resource_group
        if re.match(
            r"^[a-zA-Z0-9_.()-]+/[a-zA-Z0-9]+[a-zA-Z0-9_-]*[a-zA-Z0-9]+$",
            resource_id,
        ):
            # The resource ID is an AKS cluster name including the resource
            # group
            resource_group, cluster_name = resource_id.split("/")
        elif re.match(
            r"^[a-zA-Z0-9]+[a-zA-Z0-9_-]*[a-zA-Z0-9]+$",
            resource_id,
        ):
            # The resource ID is an AKS cluster name without the resource group
            cluster_name = resource_id
        else:
            raise ValueError(
                f"Invalid resource ID for a AKS cluster: {resource_id}. "
                f"Supported formats are:\n"
                "resource group scoped AKS cluster name (canonical): {resource-group}/{cluster-name}\n"
                "AKS cluster name: {cluster-name}"
            )

        if (
            self.config.resource_group
            and self.config.resource_group != resource_group
        ):
            raise ValueError(
                f"Invalid resource ID for an AKS cluster: {resource_id}. "
                f"The resource group '{resource_group}' does not match the "
                f"resource group configured in the connector: "
                f"'{self.config.resource_group}'."
            )

        return resource_group, cluster_name

    def _canonical_resource_id(
        self, resource_type: str, resource_id: str
    ) -> str:
        """Convert a resource ID to its canonical form.

        Args:
            resource_type: The resource type to canonicalize.
            resource_id: The resource ID to canonicalize.

        Returns:
            The canonical resource ID.
        """
        if resource_type == BLOB_RESOURCE_TYPE:
            container_name = self._parse_blob_container_resource_id(
                resource_id
            )
            return f"az://{container_name}"
        elif resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            resource_group, cluster_name = self._parse_aks_resource_id(
                resource_id
            )
            if resource_group:
                return f"{resource_group}/{cluster_name}"
            return cluster_name
        elif resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            registry_name = self._parse_acr_resource_id(
                resource_id,
            )
            return f"{registry_name}.azurecr.io"
        else:
            return resource_id

    def _get_default_resource_id(self, resource_type: str) -> str:
        """Get the default resource ID for a resource type.

        Args:
            resource_type: The type of the resource to get a default resource ID
                for. Only called with resource types that do not support
                multiple instances.

        Returns:
            The default resource ID for the resource type.

        Raises:
            RuntimeError: If the ECR registry ID (Azure account ID)
                cannot be retrieved from Azure because the connector is not
                authorized.
        """
        if resource_type == AZURE_RESOURCE_TYPE:
            _, subscription_name = self.subscription
            return subscription_name

        raise RuntimeError(
            f"Default resource ID for '{resource_type}' not available."
        )

    def _connect_to_resource(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to an Azure resource.

        Initialize and return a session or client object depending on the
        connector configuration:

        - initialize and return an Azure TokenCredential if the resource type
        is a generic Azure resource
        - initialize and return an Azure BlobServiceClient for an Azure blob
        storage container resource type

        For the Docker and Kubernetes resource types, the connector does not
        support connecting to the resource directly. Instead, the connector
        supports generating a connector client object for the resource type
        in question.

        Args:
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            A TokenCredential for Azure generic resources and a
            BlobServiceClient client for an Azure blob storage container.

        Raises:
            NotImplementedError: If the connector instance does not support
                directly connecting to the indicated resource type.
        """
        resource_type = self.resource_type
        resource_id = self.resource_id

        assert resource_type is not None
        assert resource_id is not None

        # Regardless of the resource type, we must authenticate to Azure first
        # before we can connect to any Azure resource
        credential, _ = self.get_azure_credential(
            self.auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if resource_type == BLOB_RESOURCE_TYPE:
            container_name = self._parse_blob_container_resource_id(
                resource_id
            )

            containers = self._list_blob_containers(
                credential,
                container_name=container_name,
            )

            container_name, storage_account = containers.popitem()
            account_url = f"https://{storage_account}.blob.core.windows.net/"

            blob_client = BlobServiceClient(
                account_url=account_url,
                credential=credential,
            )

            return blob_client

        if resource_type == AZURE_RESOURCE_TYPE:
            return credential

        raise NotImplementedError(
            f"Connecting to {resource_type} resources is not directly "
            "supported by the Azure connector. Please call the "
            f"`get_connector_client` method to get a {resource_type} connector "
            "instance for the resource."
        )

    def _configure_local_client(
        self,
        **kwargs: Any,
    ) -> None:
        """Configure a local client to authenticate and connect to a resource.

        This method uses the connector's configuration to configure a local
        client or SDK installed on the localhost for the indicated resource.

        Args:
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            NotImplementedError: If the connector instance does not support
                local configuration for the configured resource type or
                authentication method.registry
            AuthorizationException: If the connector instance does not support
                local configuration for the configured authentication method.
        """
        resource_type = self.resource_type

        if resource_type in [AZURE_RESOURCE_TYPE, BLOB_RESOURCE_TYPE]:
            if (
                self.auth_method
                == AzureAuthenticationMethods.SERVICE_PRINCIPAL
            ):
                # Use the service principal credentials to configure the local
                # Azure CLI
                assert isinstance(self.config, AzureServicePrincipalConfig)

                command = [
                    "az",
                    "login",
                    "--service-principal",
                    "-u",
                    str(self.config.client_id),
                    "-p",
                    self.config.client_secret.get_secret_value(),
                    "--tenant",
                    str(self.config.tenant_id),
                ]

                try:
                    subprocess.run(command, check=True)
                except subprocess.CalledProcessError as e:
                    raise AuthorizationException(
                        f"Failed to update the local Azure CLI with the "
                        f"connector service principal credentials: {e}"
                    ) from e

                logger.info(
                    "Updated the local Azure CLI configuration with the "
                    "connector's service principal credentials."
                )

                return

            raise NotImplementedError(
                f"Local Azure client configuration for resource type "
                f"{resource_type} is only supported if the "
                f"'{AzureAuthenticationMethods.SERVICE_PRINCIPAL}' "
                f"authentication method is used."
            )

        raise NotImplementedError(
            f"Configuring the local client for {resource_type} resources is "
            "not directly supported by the Azure connector. Please call the "
            f"`get_connector_client` method to get a {resource_type} connector "
            "instance for the resource."
        )

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        resource_group: Optional[str] = None,
        storage_account: Optional[str] = None,
        **kwargs: Any,
    ) -> "AzureServiceConnector":
        """Auto-configure the connector.

        Instantiate an Azure connector with a configuration extracted from the
        authentication configuration available in the environment (e.g.
        environment variables or local Azure client/SDK configuration files).

        Args:
            auth_method: The particular authentication method to use. If not
                specified, the connector implementation must decide which
                authentication method to use or raise an exception.
            resource_type: The type of resource to configure.
            resource_id: The ID of the resource to configure. The implementation
                may choose to either require or ignore this parameter if it does
                not support or detect an resource type that supports multiple
                instances.
            resource_group: A resource group may be used to restrict the scope
                of Azure resources like AKS clusters and ACR repositories. If
                not specified, ZenML will retrieve resources from all resource
                groups accessible with the discovered credentials.
            storage_account: The name of an Azure storage account may be used to
                restrict the scope of Azure Blob storage containers. If not
                specified, ZenML will retrieve blob containers from all storage
                accounts accessible with the discovered credentials.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            An Azure connector instance configured with authentication
            credentials automatically extracted from the environment.

        Raises:
            NotImplementedError: If the connector implementation does not
                support auto-configuration for the specified authentication
                method.
            AuthorizationException: If no Azure credentials can be loaded from
                the environment.
        """
        auth_config: AzureBaseConfig
        expiration_seconds: Optional[int] = None
        expires_at: Optional[datetime.datetime] = None
        if auth_method == AzureAuthenticationMethods.IMPLICIT:
            auth_config = AzureBaseConfig(
                resource_group=resource_group,
                storage_account=storage_account,
            )
        else:
            # Initialize an Azure credential with the default configuration
            # loaded from the environment.
            try:
                credential = DefaultAzureCredential()
            except AzureError as e:
                raise AuthorizationException(
                    f"Failed to authenticate to Azure using implicit "
                    f"authentication. Please check your local Azure CLI "
                    f"configuration: {e}"
                )

            if (
                auth_method
                and auth_method != AzureAuthenticationMethods.ACCESS_TOKEN
            ):
                raise NotImplementedError(
                    f"The specified authentication method '{auth_method}' "
                    "could not be used to auto-configure the connector. "
                )
            auth_method = AzureAuthenticationMethods.ACCESS_TOKEN

            if resource_type == BLOB_RESOURCE_TYPE:
                raise AuthorizationException(
                    f"Auto-configuration for {resource_type} resources is not "
                    "supported by the Azure connector."
                )
            else:
                token = credential.get_token(
                    AZURE_MANAGEMENT_TOKEN_SCOPE,
                )

            # Convert the expiration timestamp from Unix time to datetime
            # format.
            expires_at = datetime.datetime.fromtimestamp(token.expires_on)
            # Convert the expiration timestamp from local time to UTC time.
            expires_at = to_utc_timezone(expires_at)

            auth_config = AzureAccessTokenConfig(
                token=token.token,
                resource_group=resource_group,
                storage_account=storage_account,
            )

        return cls(
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id
            if resource_type not in [AZURE_RESOURCE_TYPE, None]
            else None,
            expiration_seconds=expiration_seconds,
            expires_at=expires_at,
            config=auth_config,
        )

    @classmethod
    def _get_resource_group(cls, resource_id: str) -> str:
        """Get the resource group of an Azure resource.

        Args:
            resource_id: The ID of the Azure resource.

        Returns:
            The resource group of the Azure resource.
        """
        # The resource group is the fourth component of the resource ID.
        return resource_id.split("/")[4]

    def _list_blob_containers(
        self, credential: TokenCredential, container_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Get the list of blob storage containers that the connector can access.

        Args:
            credential: The Azure credential to use to access the blob storage
                containers.
            container_name: The name of the blob container to get. If omitted,
                all accessible blob containers are returned.

        Returns:
            The list of blob storage containers that the connector can access
            as a dictionary mapping container names to their corresponding
            storage account names. If the `container_name` argument was
            specified, the dictionary will contain a single entry.

        Raises:
            AuthorizationException: If the connector does not have access to
                access the target blob storage containers.
        """
        subscription_id, _ = self.subscription
        # Azure blob storage containers are scoped to a storage account. We
        # need to figure out which storage accounts the connector can access
        # and then list the containers in each of them. If a container name
        # is provided, we only need to find the storage account that contains
        # it.

        storage_accounts: List[str] = []
        if self.config.storage_account:
            storage_accounts = [self.config.storage_account]
        else:
            try:
                storage_client = StorageManagementClient(
                    credential, subscription_id
                )
                accounts = list(storage_client.storage_accounts.list())
            except AzureError as e:
                raise AuthorizationException(
                    f"failed to list available Azure storage accounts. Please "
                    f"check that the credentials have permissions to list "
                    f"storage accounts or consider configuring a storage "
                    f"account in the connector: {e}"
                ) from e

            if not accounts:
                raise AuthorizationException(
                    "no storage accounts were found. Please check that the "
                    "credentials have permissions to access one or more "
                    "storage accounts."
                )

            if self.config.resource_group:
                # Keep only the storage accounts in the specified resource
                # group.
                accounts = [
                    account
                    for account in accounts
                    if self._get_resource_group(account.id)
                    == self.config.resource_group
                ]
                if not accounts:
                    raise AuthorizationException(
                        f"no storage accounts were found in the "
                        f"'{self.config.resource_group}' resource group "
                        f"specified in the connector configuration. Please "
                        f"check that resource group contains one or more "
                        f"storage accounts and that the connector credentials "
                        f"have permissions to access them."
                    )

            storage_accounts = [
                account.name for account in accounts if account.name
            ]

        containers: Dict[str, str] = {}
        for storage_account in storage_accounts:
            account_url = f"https://{storage_account}.blob.core.windows.net/"

            try:
                blob_client = BlobServiceClient(
                    account_url, credential=credential
                )
                response = blob_client.list_containers()
                account_containers = [
                    container.name for container in response if container.name
                ]
            except AzureError as e:
                raise AuthorizationException(
                    f"failed to fetch Azure blob storage containers in the "
                    f"'{storage_account}' storage account. Please check that "
                    f"the credentials have permissions to list containers in "
                    f"that storage account: {e}"
                ) from e

            if container_name:
                if container_name not in account_containers:
                    continue
                containers = {container_name: storage_account}
                break

            containers.update(
                {
                    container: storage_account
                    for container in account_containers
                }
            )

        if not containers:
            if container_name:
                if self.config.storage_account:
                    raise AuthorizationException(
                        f"the '{container_name}' container was not found in "
                        f"the '{self.config.storage_account}' storage "
                        f"account. Please check that container exists and the "
                        f"credentials have permissions to access that "
                        f"container."
                    )

                raise AuthorizationException(
                    f"the '{container_name}' container was not found in any "
                    f"of the storage accounts accessible to the connector. "
                    f"Please check that container exists and the credentials "
                    f"have permissions to access the storage account it "
                    f"belongs to."
                )

            raise AuthorizationException(
                "no Azure blob storage containers were found in any of the "
                "storage accounts accessible to the connector. Please check "
                "that the credentials have permissions to access one or more "
                "storage accounts."
            )

        return containers

    def _list_acr_registries(
        self, credential: TokenCredential, registry_name: Optional[str] = None
    ) -> Dict[str, str]:
        """Get the list of ACR registries that the connector can access.

        Args:
            credential: The Azure credential to use.
            registry_name: The name of the registry to get. If omitted,
                all accessible registries are returned.

        Returns:
            The list of ACR registries that the connector can access as a
            dictionary mapping registry names to their corresponding
            resource group names. If the `registry_name` argument was
            specified, the dictionary will contain a single entry.

        Raises:
            AuthorizationException: If the connector does not have access to
                access the target ACR registries.
        """
        subscription_id, _ = self.subscription

        container_registries: Dict[str, str] = {}
        if registry_name and self.config.resource_group:
            try:
                container_client = ContainerRegistryManagementClient(
                    credential, subscription_id
                )
                registry = container_client.registries.get(
                    resource_group_name=self.config.resource_group,
                    registry_name=registry_name,
                )
                if registry.name:
                    container_registries = {
                        registry.name: self.config.resource_group
                    }
            except AzureError as e:
                raise AuthorizationException(
                    f"failed to fetch the Azure container registry "
                    f"'{registry_name}' in the '{self.config.resource_group}' "
                    f"resource group specified in the connector configuration. "
                    f"Please check that the registry exists in that resource "
                    f"group and that the connector credentials have "
                    f"permissions to access that registry: {e}"
                ) from e
        else:
            try:
                container_client = ContainerRegistryManagementClient(
                    credential, subscription_id
                )
                registries = list(container_client.registries.list())
            except AzureError as e:
                raise AuthorizationException(
                    "failed to list available Azure container registries. "
                    "Please check that the credentials have permissions to "
                    f"list container registries: {e}"
                ) from e

            if not registries:
                raise AuthorizationException(
                    "no container registries were found. Please check that the "
                    "credentials have permissions to access one or more "
                    "container registries."
                )

            if self.config.resource_group:
                # Keep only the registries in the specified resource
                # group.
                registries = [
                    registry
                    for registry in registries
                    if self._get_resource_group(registry.id)
                    == self.config.resource_group
                ]

                if not registries:
                    raise AuthorizationException(
                        f"no container registries were found in the "
                        f"'{self.config.resource_group}' resource group "
                        f"specified in the connector configuration. Please "
                        f"check that resource group contains one or more "
                        f"container registries and that the connector "
                        f"credentials have permissions to access them."
                    )

            container_registries = {
                registry.name: self._get_resource_group(registry.id)
                for registry in registries
                if registry.name
            }

            if registry_name:
                if registry_name not in container_registries:
                    if self.config.resource_group:
                        raise AuthorizationException(
                            f"the '{registry_name}' registry was not found in "
                            f"the '{self.config.resource_group}' resource "
                            f"group specified in the connector configuration. "
                            f"Please check that registry exists in that "
                            f"resource group and that the connector "
                            f"credentials have permissions to access that "
                            f"registry."
                        )

                    raise AuthorizationException(
                        f"the '{registry_name}' registry was not found or is "
                        "not accessible. Please check that registry exists and "
                        "the credentials have permissions to access it."
                    )

                container_registries = {
                    registry_name: container_registries[registry_name]
                }

        return container_registries

    def _list_aks_clusters(
        self,
        credential: TokenCredential,
        cluster_name: Optional[str] = None,
        resource_group: Optional[str] = None,
    ) -> List[Tuple[str, str]]:
        """Get the list of AKS clusters that the connector can access.

        Args:
            credential: The Azure credential to use.
            cluster_name: The name of the cluster to get. If omitted,
                all accessible clusters are returned.
            resource_group: The name of the resource group to which the
                search should be limited. If omitted, all accessible
                clusters are returned.

        Returns:
            The list of AKS clusters that the connector can access as a
            list of cluster names and their corresponding resource group names.
            If the `cluster_name` argument was specified, the dictionary will
            contain a single entry.

        Raises:
            AuthorizationException: If the connector does not have access to
                access the target AKS clusters.
        """
        subscription_id, _ = self.subscription

        clusters: List[Tuple[str, str]] = []
        if cluster_name and resource_group:
            try:
                container_client = ContainerServiceClient(
                    credential, subscription_id
                )
                cluster = container_client.managed_clusters.get(
                    resource_group_name=resource_group,
                    resource_name=cluster_name,
                )
                if cluster.name:
                    clusters = [(cluster.name, resource_group)]
            except AzureError as e:
                raise AuthorizationException(
                    f"failed to fetch the Azure AKS cluster '{cluster_name}' "
                    f"in the '{resource_group}' resource group. Please check "
                    f"that the cluster exists in that resource group and that "
                    f"the connector credentials have permissions to access "
                    f"that cluster: {e}"
                ) from e
        else:
            try:
                container_client = ContainerServiceClient(
                    credential, subscription_id
                )
                aks_clusters = list(container_client.managed_clusters.list())
            except AzureError as e:
                raise AuthorizationException(
                    f"failed to list available Azure AKS clusters. Please "
                    f"check that the credentials have permissions to list "
                    f"AKS clusters: {e}"
                ) from e

            if not aks_clusters:
                raise AuthorizationException(
                    "no AKS clusters were found. Please check that the "
                    "credentials have permissions to access one or more "
                    "AKS clusters."
                )

            if self.config.resource_group:
                # Keep only the clusters in the specified resource
                # group.
                aks_clusters = [
                    cluster
                    for cluster in aks_clusters
                    if self._get_resource_group(cluster.id)
                    == self.config.resource_group
                ]

                if not aks_clusters:
                    raise AuthorizationException(
                        f"no AKS clusters were found in the "
                        f"'{self.config.resource_group}' resource group "
                        f"specified in the connector configuration. Please "
                        f"check that resource group contains one or more "
                        f"AKS clusters and that the connector credentials "
                        f"have permissions to access them."
                    )

            clusters = [
                (cluster.name, self._get_resource_group(cluster.id))
                for cluster in aks_clusters
                if cluster.name
                and (not cluster_name or cluster.name == cluster_name)
            ]

            if cluster_name:
                if not clusters:
                    if self.config.resource_group:
                        raise AuthorizationException(
                            f"the '{cluster_name}' AKS cluster was not found "
                            f"in the '{self.config.resource_group}' resource "
                            f"group specified in the connector configuration. "
                            f"Please check that cluster exists in that "
                            f"resource group and that the connector "
                            f"credentials have permissions to access that "
                            f"cluster."
                        )

                    raise AuthorizationException(
                        f"the '{cluster_name}' AKS cluster was not found or "
                        "is not accessible. Please check that cluster exists "
                        "and the credentials have permissions to access it."
                    )

                if len(clusters) > 1:
                    resource_groups = [cluster[1] for cluster in clusters]
                    raise AuthorizationException(
                        f"the '{cluster_name}' AKS cluster was found in "
                        f"multiple resource groups: "
                        f"{', '.join(resource_groups)}. "
                        f"Please specify a resource group in the connector "
                        f"configuration or include the resource group in the "
                        "resource name to disambiguate."
                    )

        return clusters

    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """Verify and list all the resources that the connector can access.

        Args:
            resource_type: The type of the resource to verify. If omitted and
                if the connector supports multiple resource types, the
                implementation must verify that it can authenticate and connect
                to any and all of the supported resource types.
            resource_id: The ID of the resource to connect to. Omitted if a
                resource type is not specified. It has the same value as the
                default resource ID if the supplied resource type doesn't
                support multiple instances. If the supplied resource type does
                allows multiple instances, this parameter may still be omitted
                to fetch a list of resource IDs identifying all the resources
                of the indicated type that the connector can access.

        Returns:
            The list of resources IDs in canonical format identifying the
            resources that the connector can access. This list is empty only
            if the resource type is not specified (i.e. for multi-type
            connectors).

        Raises:
            AuthorizationException: If the connector cannot authenticate or
                access the specified resource.
        """
        # If the resource type is not specified, treat this the
        # same as a generic Azure connector.
        if not resource_type:
            # fetch the Azure subscription and tenant IDs to verify the
            # credentials globally
            subscription_id, subscription_name = self.subscription
            return []

        if resource_type == AZURE_RESOURCE_TYPE:
            assert resource_id is not None
            return [resource_id]

        credential, _ = self.get_azure_credential(
            self.auth_method,
            resource_type=resource_type or AZURE_RESOURCE_TYPE,
            resource_id=resource_id,
        )

        if resource_type == BLOB_RESOURCE_TYPE:
            if self.auth_method == AzureAuthenticationMethods.ACCESS_TOKEN:
                raise AuthorizationException(
                    f"the '{self.auth_method}' authentication method is not "
                    "supported for blob storage resources"
                )

            container_name: Optional[str] = None
            if resource_id:
                container_name = self._parse_blob_container_resource_id(
                    resource_id
                )

            containers = self._list_blob_containers(
                credential,
                container_name=container_name,
            )

            return [f"az://{container}" for container in containers.keys()]

        if resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            registry_name: Optional[str] = None
            if resource_id:
                registry_name = self._parse_acr_resource_id(resource_id)

            registries = self._list_acr_registries(
                credential,
                registry_name=registry_name,
            )

            return [f"{registry}.azurecr.io" for registry in registries.keys()]

        if resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            cluster_name: Optional[str] = None
            resource_group = self.config.resource_group
            if resource_id:
                resource_group, cluster_name = self._parse_aks_resource_id(
                    resource_id
                )

            clusters = self._list_aks_clusters(
                credential,
                cluster_name=cluster_name,
                resource_group=resource_group,
            )

            return [
                f"{resource_group}/{cluster_name}"
                for cluster_name, resource_group in clusters
            ]

        return []

    def _get_connector_client(
        self,
        resource_type: str,
        resource_id: str,
    ) -> "ServiceConnector":
        """Get a connector instance that can be used to connect to a resource.

        This method generates a client-side connector instance that can be used
        to connect to a resource of the given type. The client-side connector
        is configured with temporary Azure credentials extracted from the
        current connector and, depending on resource type, it may also be
        of a different connector type:

        - a Kubernetes connector for Kubernetes clusters
        - a Docker connector for Docker registries

        Args:
            resource_type: The type of the resources to connect to.
            resource_id: The ID of a particular resource to connect to.

        Returns:
            An Azure, Kubernetes or Docker connector instance that can be used to
            connect to the specified resource.

        Raises:
            AuthorizationException: If authentication failed.
            ValueError: If the resource type is not supported.
            RuntimeError: If the Kubernetes connector is not installed and the
                resource type is Kubernetes.
        """
        connector_name = ""
        if self.name:
            connector_name = self.name
        if resource_id:
            connector_name += f" ({resource_type} | {resource_id} client)"
        else:
            connector_name += f" ({resource_type} client)"

        logger.debug(f"Getting connector client for {connector_name}")

        if resource_type in [AZURE_RESOURCE_TYPE, BLOB_RESOURCE_TYPE]:
            auth_method = self.auth_method
            if (
                self.resource_type == resource_type
                and self.resource_id == resource_id
            ):
                # If the requested type and resource ID are the same as
                # those configured, we can return the current connector
                # instance because it's fully formed and ready to use
                # to connect to the specified resource
                return self

            config = self.config
            expires_at = self.expires_at

            # Create a client-side Azure connector instance that is fully formed
            # and ready to use to connect to the specified resource (i.e. has
            # all the necessary configuration and credentials, a resource type
            # and a resource ID where applicable)
            return AzureServiceConnector(
                id=self.id,
                name=connector_name,
                auth_method=auth_method,
                resource_type=resource_type,
                resource_id=resource_id,
                config=config,
                expires_at=expires_at,
            )

        subscription_id, _ = self.subscription
        credential, expires_at = self.get_azure_credential(
            self.auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        resource_group: Optional[str]
        registry_name: str
        cluster_name: str

        if resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            registry_name = self._parse_acr_resource_id(resource_id)
            registry_domain = f"{registry_name}.azurecr.io"

            # If a service principal is used for authentication, the client ID
            # and client secret can be used to authenticate to the registry, if
            # configured.
            # https://learn.microsoft.com/en-us/azure/container-registry/container-registry-auth-service-principal#authenticate-with-the-service-principal
            if (
                self.auth_method
                == AzureAuthenticationMethods.SERVICE_PRINCIPAL
            ):
                assert isinstance(self.config, AzureServicePrincipalConfig)
                username = str(self.config.client_id)
                password = self.config.client_secret.get_secret_value()

            # Without a service principal, we try to use the AzureDefaultCredentials to authenticate against the ACR.
            # If this fails, we try to use the admin account.
            # This has to be enabled for the registry, but this is not recommended and disabled by default.
            # https://docs.microsoft.com/en-us/azure/container-registry/container-registry-authentication#admin-account
            else:
                registries = self._list_acr_registries(
                    credential,
                    registry_name=registry_name,
                )
                registry_name, resource_group = registries.popitem()

                try:
                    username = "00000000-0000-0000-0000-000000000000"
                    password = _ACRTokenExchangeClient(
                        credential
                    ).get_acr_access_token(
                        registry_domain, AZURE_ACR_OAUTH_SCOPE
                    )
                except AuthorizationException:
                    logger.warning(
                        "Falling back to admin credentials for ACR authentication. Be sure to assign AcrPush role to the configured identity."
                    )
                    try:
                        client = ContainerRegistryManagementClient(
                            credential, subscription_id
                        )

                        registry_credentials = (
                            client.registries.list_credentials(
                                resource_group, registry_name
                            )
                        )
                        username = registry_credentials.username
                        password = registry_credentials.passwords[0].value
                    except AzureError as e:
                        raise AuthorizationException(
                            f"failed to list admin credentials for Azure Container "
                            f"Registry '{registry_name}' in resource group "
                            f"'{resource_group}'. Make sure the registry is "
                            f"configured with an admin account: {e}"
                        ) from e

            # Create a client-side Docker connector instance with the temporary
            # Docker credentials
            return DockerServiceConnector(
                id=self.id,
                name=connector_name,
                auth_method=DockerAuthenticationMethods.PASSWORD,
                resource_type=resource_type,
                config=DockerConfiguration(
                    username=username,
                    password=password,
                    registry=registry_domain,
                ),
                expires_at=expires_at,
            )

        if resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            resource_group, cluster_name = self._parse_aks_resource_id(
                resource_id
            )
            clusters = self._list_aks_clusters(
                credential,
                cluster_name=cluster_name,
                resource_group=resource_group,
            )
            cluster_name, resource_group = clusters[0]

            try:
                client = ContainerServiceClient(credential, subscription_id)

                creds = client.managed_clusters.list_cluster_admin_credentials(
                    resource_group_name=resource_group,
                    resource_name=cluster_name,
                )

                kubeconfig_yaml = creds.kubeconfigs[0].value.decode(
                    encoding="UTF-8"
                )
            except AzureError as e:
                raise AuthorizationException(
                    f"failed to list credentials for Azure Kubernetes "
                    f"Service cluster '{cluster_name}' in resource group "
                    f"'{resource_group}': {e}"
                ) from e

            kubeconfig = yaml.safe_load(kubeconfig_yaml)

            # Create a client-side Kubernetes connector instance with the
            # Kubernetes credentials
            try:
                # Import libraries only when needed
                from zenml.integrations.kubernetes.service_connectors.kubernetes_service_connector import (
                    KubernetesAuthenticationMethods,
                    KubernetesServiceConnector,
                    KubernetesTokenConfig,
                )
            except ImportError as e:
                raise RuntimeError(
                    f"The Kubernetes Service Connector functionality could not "
                    f"be used due to missing dependencies: {e}"
                )
            cluster_name = kubeconfig["clusters"][0]["name"]
            cluster = kubeconfig["clusters"][0]["cluster"]
            user = kubeconfig["users"][0]["user"]
            return KubernetesServiceConnector(
                id=self.id,
                name=connector_name,
                auth_method=KubernetesAuthenticationMethods.TOKEN,
                resource_type=resource_type,
                config=KubernetesTokenConfig(
                    cluster_name=cluster_name,
                    certificate_authority=cluster.get(
                        "certificate-authority-data"
                    ),
                    server=cluster["server"],
                    token=user["token"],
                    client_certificate=user.get("client-certificate-data"),
                    client_key=user.get("client-key-data"),
                ),
                expires_at=expires_at,
            )

        raise ValueError(f"Unsupported resource type: {resource_type}")


class _ACRTokenExchangeClient:
    def __init__(self, credential: TokenCredential):
        self._credential = credential

    def _get_aad_access_token(self) -> str:
        aad_access_token: str = self._credential.get_token(
            AZURE_MANAGEMENT_TOKEN_SCOPE
        ).token
        return aad_access_token

    # https://github.com/Azure/acr/blob/main/docs/AAD-OAuth.md#authenticating-docker-with-an-acr-refresh-token
    def get_acr_refresh_token(self, acr_url: str) -> str:
        try:
            aad_access_token = self._get_aad_access_token()

            headers = {
                "Content-Type": "application/x-www-form-urlencoded",
            }

            data = {
                "grant_type": "access_token",
                "service": acr_url,
                "access_token": aad_access_token,
            }

            response = requests.post(
                f"https://{acr_url}/oauth2/exchange",
                headers=headers,
                data=data,
                timeout=5,
            )

            if response.status_code != 200:
                raise AuthorizationException(
                    f"failed to get refresh token for Azure Container "
                    f"Registry '{acr_url}' in resource group. "
                    f"Be sure to assign AcrPush to the configured principal. "
                    f"The token exchange returned status {response.status_code} "
                    f"with body '{response.content.decode()}'"
                )

            acr_refresh_token_response = json.loads(response.content)
            acr_refresh_token: str = acr_refresh_token_response[
                "refresh_token"
            ]
            return acr_refresh_token

        except (AzureError, requests.exceptions.RequestException) as e:
            raise AuthorizationException(
                f"failed to get refresh token for Azure Container "
                f"Registry '{acr_url}' in resource group. "
                f"Make sure the implicit authentication identity "
                f"has access to the configured registry: {e}"
            ) from e

    # https://github.com/Azure/acr/blob/main/docs/AAD-OAuth.md#calling-post-oauth2token-to-get-an-acr-access-token
    def get_acr_access_token(self, acr_url: str, scope: str) -> str:
        acr_refresh_token = self.get_acr_refresh_token(acr_url)

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
        }

        data = {
            "grant_type": "refresh_token",
            "service": acr_url,
            "scope": scope,
            "refresh_token": acr_refresh_token,
        }

        try:
            response = requests.post(
                f"https://{acr_url}/oauth2/token",
                headers=headers,
                data=data,
                timeout=5,
            )

            if response.status_code != 200:
                raise AuthorizationException(
                    f"failed to get access token for Azure Container "
                    f"Registry '{acr_url}' in resource group. "
                    f"Be sure to assign AcrPush to the configured principal. "
                    f"The token exchange returned status {response.status_code} "
                    f"with body '{response.content.decode()}'"
                )

            acr_access_token_response = json.loads(response.content)
            acr_access_token: str = acr_access_token_response["access_token"]
            return acr_access_token

        except (AzureError, requests.exceptions.RequestException) as e:
            raise AuthorizationException(
                f"failed to get access token for Azure Container "
                f"Registry '{acr_url}' in resource group. "
                f"Make sure the implicit authentication identity "
                f"has access to the configured registry: {e}"
            ) from e
