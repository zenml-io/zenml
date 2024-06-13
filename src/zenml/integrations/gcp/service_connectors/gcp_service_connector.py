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
"""GCP Service Connector.

The GCP Service Connector implements various authentication methods for GCP
services:

- Explicit GCP service account key

"""

import datetime
import json
import os
import re
import shutil
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

import google.api_core.exceptions
import google.auth
import google.auth.exceptions
import requests
from google.auth import aws as gcp_aws
from google.auth import external_account as gcp_external_account
from google.auth import (
    impersonated_credentials as gcp_impersonated_credentials,
)
from google.auth._default import (
    _AWS_SUBJECT_TOKEN_TYPE,
    _get_external_account_credentials,
)
from google.auth.transport.requests import Request
from google.cloud import container_v1, storage
from google.oauth2 import credentials as gcp_credentials
from google.oauth2 import service_account as gcp_service_account
from pydantic import Field, field_validator, model_validator

from zenml.constants import (
    DOCKER_REGISTRY_RESOURCE_TYPE,
    KUBERNETES_CLUSTER_RESOURCE_TYPE,
)
from zenml.exceptions import AuthorizationException
from zenml.integrations.gcp import (
    GCP_CONNECTOR_TYPE,
    GCP_RESOURCE_TYPE,
    GCS_RESOURCE_TYPE,
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
from zenml.utils.pydantic_utils import before_validator_handler
from zenml.utils.secret_utils import PlainSerializedSecretStr

logger = get_logger(__name__)

GKE_KUBE_API_TOKEN_EXPIRATION = 60
DEFAULT_IMPERSONATE_TOKEN_EXPIRATION = 3600  # 1 hour
GCP_SESSION_EXPIRATION_BUFFER = 15  # 15 minutes


class GCPUserAccountCredentials(AuthenticationConfig):
    """GCP user account credentials."""

    user_account_json: PlainSerializedSecretStr = Field(
        title="GCP User Account Credentials JSON",
    )

    generate_temporary_tokens: bool = Field(
        default=True,
        title="Generate temporary OAuth 2.0 tokens",
        description="Whether to generate temporary OAuth 2.0 tokens from the "
        "user account credentials JSON. If set to False, the connector will "
        "distribute the user account credentials JSON to clients instead.",
    )

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def validate_user_account_dict(
        cls, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert the user account credentials to JSON if given in dict format.

        Args:
            data: The configuration values.

        Returns:
            The validated configuration values.
        """
        if isinstance(data.get("user_account_json"), dict):
            data["user_account_json"] = json.dumps(data["user_account_json"])
        return data

    @field_validator("user_account_json")
    @classmethod
    def validate_user_account_json(
        cls, value: PlainSerializedSecretStr
    ) -> PlainSerializedSecretStr:
        """Validate the user account credentials JSON.

        Args:
            value: The user account credentials JSON.

        Returns:
            The validated user account credentials JSON.

        Raises:
            ValueError: If the user account credentials JSON is invalid.
        """
        try:
            user_account_info = json.loads(value.get_secret_value())
        except json.JSONDecodeError as e:
            raise ValueError(
                f"GCP user account credentials is not a valid JSON: {e}"
            )

        # Check that all fields are present
        required_fields = [
            "type",
            "refresh_token",
            "client_secret",
            "client_id",
        ]
        # Compute missing fields
        missing_fields = set(required_fields) - set(user_account_info.keys())
        if missing_fields:
            raise ValueError(
                f"GCP user account credentials JSON is missing required "
                f'fields: {", ".join(list(missing_fields))}'
            )

        if user_account_info["type"] != "authorized_user":
            raise ValueError(
                "The JSON does not contain GCP user account credentials. The "
                f'"type" field is set to {user_account_info["type"]} '
                "instead of 'authorized_user'."
            )

        return value


class GCPServiceAccountCredentials(AuthenticationConfig):
    """GCP service account credentials."""

    service_account_json: PlainSerializedSecretStr = Field(
        title="GCP Service Account Key JSON",
    )

    generate_temporary_tokens: bool = Field(
        default=True,
        title="Generate temporary OAuth 2.0 tokens",
        description="Whether to generate temporary OAuth 2.0 tokens from the "
        "service account key JSON. If set to False, the connector will "
        "distribute the service account key JSON to clients instead.",
    )

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def validate_service_account_dict(
        cls, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert the service account credentials to JSON if given in dict format.

        Args:
            data: The configuration values.

        Returns:
            The validated configuration values.
        """
        if isinstance(data.get("service_account_json"), dict):
            data["service_account_json"] = json.dumps(
                data["service_account_json"]
            )
        return data

    @field_validator("service_account_json")
    @classmethod
    def validate_service_account_json(
        cls, value: PlainSerializedSecretStr
    ) -> PlainSerializedSecretStr:
        """Validate the service account credentials JSON.

        Args:
            value: The service account credentials JSON.

        Returns:
            The validated service account credentials JSON.

        Raises:
            ValueError: If the service account credentials JSON is invalid.
        """
        try:
            service_account_info = json.loads(value.get_secret_value())
        except json.JSONDecodeError as e:
            raise ValueError(
                f"GCP service account credentials is not a valid JSON: {e}"
            )

        # Check that all fields are present
        required_fields = [
            "type",
            "project_id",
            "private_key_id",
            "private_key",
            "client_email",
            "client_id",
            "auth_uri",
            "token_uri",
            "auth_provider_x509_cert_url",
            "client_x509_cert_url",
        ]
        # Compute missing fields
        missing_fields = set(required_fields) - set(
            service_account_info.keys()
        )
        if missing_fields:
            raise ValueError(
                f"GCP service account credentials JSON is missing required "
                f'fields: {", ".join(list(missing_fields))}'
            )

        if service_account_info["type"] != "service_account":
            raise ValueError(
                "The JSON does not contain GCP service account credentials. "
                f'The "type" field is set to {service_account_info["type"]} '
                "instead of 'service_account'."
            )

        return value


class GCPExternalAccountCredentials(AuthenticationConfig):
    """GCP external account credentials."""

    external_account_json: PlainSerializedSecretStr = Field(
        title="GCP External Account JSON",
    )

    generate_temporary_tokens: bool = Field(
        default=True,
        title="Generate temporary OAuth 2.0 tokens",
        description="Whether to generate temporary OAuth 2.0 tokens from the "
        "external account key JSON. If set to False, the connector will "
        "distribute the external account JSON to clients instead.",
    )

    @model_validator(mode="before")
    @classmethod
    @before_validator_handler
    def validate_service_account_dict(
        cls, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Convert the external account credentials to JSON if given in dict format.

        Args:
            data: The configuration values.

        Returns:
            The validated configuration values.
        """
        if isinstance(data.get("external_account_json"), dict):
            data["external_account_json"] = json.dumps(
                data["external_account_json"]
            )
        return data

    @field_validator("external_account_json")
    @classmethod
    def validate_external_account_json(
        cls, value: PlainSerializedSecretStr
    ) -> PlainSerializedSecretStr:
        """Validate the external account credentials JSON.

        Args:
            value: The external account credentials JSON.

        Returns:
            The validated external account credentials JSON.

        Raises:
            ValueError: If the external account credentials JSON is invalid.
        """
        try:
            external_account_info = json.loads(value.get_secret_value())
        except json.JSONDecodeError as e:
            raise ValueError(
                f"GCP external account credentials is not a valid JSON: {e}"
            )

        # Check that all fields are present
        required_fields = [
            "type",
            "subject_token_type",
            "token_url",
        ]
        # Compute missing fields
        missing_fields = set(required_fields) - set(
            external_account_info.keys()
        )
        if missing_fields:
            raise ValueError(
                f"GCP external account credentials JSON is missing required "
                f'fields: {", ".join(list(missing_fields))}'
            )

        if external_account_info["type"] != "external_account":
            raise ValueError(
                "The JSON does not contain GCP external account credentials. "
                f'The "type" field is set to {external_account_info["type"]} '
                "instead of 'external_account'."
            )

        return value


class GCPOAuth2Token(AuthenticationConfig):
    """GCP OAuth 2.0 token credentials."""

    token: PlainSerializedSecretStr = Field(
        title="GCP OAuth 2.0 Token",
    )


class GCPBaseConfig(AuthenticationConfig):
    """GCP base configuration."""

    project_id: str = Field(
        title="GCP Project ID where the target resource is located.",
    )


class GCPUserAccountConfig(GCPBaseConfig, GCPUserAccountCredentials):
    """GCP user account configuration."""


class GCPServiceAccountConfig(GCPBaseConfig, GCPServiceAccountCredentials):
    """GCP service account configuration."""


class GCPExternalAccountConfig(GCPBaseConfig, GCPExternalAccountCredentials):
    """GCP external account configuration."""


class GCPOAuth2TokenConfig(GCPBaseConfig, GCPOAuth2Token):
    """GCP OAuth 2.0 configuration."""

    service_account_email: Optional[str] = Field(
        default=None,
        title="GCP Service Account Email",
        description="The email address of the service account that signed the "
        "token. If not provided, the token is assumed to be issued for a user "
        "account.",
    )


class GCPServiceAccountImpersonationConfig(GCPServiceAccountConfig):
    """GCP service account impersonation configuration."""

    target_principal: str = Field(
        title="GCP Service Account Email to impersonate",
    )


class GCPAuthenticationMethods(StrEnum):
    """GCP Authentication methods."""

    IMPLICIT = "implicit"
    USER_ACCOUNT = "user-account"
    SERVICE_ACCOUNT = "service-account"
    EXTERNAL_ACCOUNT = "external-account"
    OAUTH2_TOKEN = "oauth2-token"
    IMPERSONATION = "impersonation"


class ZenMLGCPAWSExternalAccountCredentials(gcp_aws.Credentials):  # type: ignore[misc]
    """An improved version of the GCP external account credential for AWS.

    The original GCP external account credential only provides rudimentary
    support for extracting AWS credentials from environment variables or the
    AWS metadata service. This version improves on that by using the boto3
    library itself (if available), which uses the entire range of implicit
    authentication features packed into it.

    Without this improvement, `sts.AssumeRoleWithWebIdentity` authentication is
    not supported for EKS pods and the EC2 attached role credentials are
    used instead (see: https://medium.com/@derek10cloud/gcp-workload-identity-federation-doesnt-yet-support-eks-irsa-in-aws-a3c71877671a).
    """

    def _get_security_credentials(
        self, request: Any, imdsv2_session_token: Any
    ) -> Dict[str, Any]:
        """Get the security credentials from the local environment.

        This method is a copy of the original method from the
        `google.auth._default` module. It has been modified to use the boto3
        library to extract the AWS credentials from the local environment.

        Args:
            request: The request to use to get the security credentials.
            imdsv2_session_token: The IMDSv2 session token to use to get the
                security credentials.

        Returns:
            The AWS temporary security credentials.
        """
        try:
            import boto3

            session = boto3.Session()
            credentials = session.get_credentials()
            if credentials is not None:
                creds = credentials.get_frozen_credentials()
                return {
                    "access_key_id": creds.access_key,
                    "secret_access_key": creds.secret_key,
                    "security_token": creds.token,
                }
        except Exception:
            logger.debug(
                "Failed to extract AWS credentials from the local environment "
                "using the boto3 library. Falling back to the original "
                "implementation."
            )

        return super()._get_security_credentials(  # type: ignore[no-any-return]
            request, imdsv2_session_token
        )


GCP_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="GCP Service Connector",
    connector_type=GCP_CONNECTOR_TYPE,
    description="""
The ZenML GCP Service Connector facilitates the authentication and access to
managed GCP services and resources. These encompass a range of resources,
including GCS buckets, GCR container repositories and GKE clusters. The
connector provides support for various authentication methods, including GCP
user accounts, service accounts, short-lived OAuth 2.0 tokens and implicit
authentication.

To ensure heightened security measures, this connector always issues short-lived
OAuth 2.0 tokens to clients instead of long-lived credentials unless explicitly
configured to do otherwise. Furthermore, it includes automatic configuration and
detection of credentials locally configured through the GCP CLI.

This connector serves as a general means of accessing any GCP service by issuing
OAuth 2.0 credential objects to clients. Additionally, the connector can handle
specialized authentication for GCS, Docker and Kubernetes Python clients. It
also allows for the configuration of local Docker and Kubernetes CLIs.

The GCP Service Connector is part of the GCP ZenML integration. You can either
install the entire integration or use a pypi extra to install it independently
of the integration:

* `pip install "zenml[connectors-gcp]"` installs only prerequisites for the GCP
Service Connector Type
* `zenml integration install gcp` installs the entire GCP ZenML integration

It is not required to install and set up [the GCP CLI](https://cloud.google.com/sdk/gcloud)
on your local machine to use the GCP Service Connector to link Stack Components
to GCP resources and services. However, it is recommended to do so if you are
looking for a quick setup that includes using the auto-configuration Service
Connector features.
""",
    supports_auto_configuration=True,
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/gcp/gcp.png",
    emoji=":blue_circle:",
    auth_methods=[
        AuthenticationMethodModel(
            name="GCP Implicit Authentication",
            auth_method=GCPAuthenticationMethods.IMPLICIT,
            description="""
Implicit authentication to GCP services using [Application Default Credentials](https://cloud.google.com/docs/authentication/provide-credentials-adc).
This authentication method doesn't require any credentials to be explicitly
configured. It automatically discovers and uses credentials from one of the
following sources:

- environment variables (`GOOGLE_APPLICATION_CREDENTIALS`)
- local ADC credential files set up by running `gcloud auth application-default
login` (e.g. `~/.config/gcloud/application_default_credentials.json`).
- GCP service account attached to the resource where the ZenML server is running.
Only works when running the ZenML server on a GCP resource with an service
account attached to it or when using Workload Identity (e.g. GKE cluster).

This is the quickest and easiest way to authenticate to GCP services. However,
the results depend on how ZenML is deployed and the environment where it is used
and is thus not fully reproducible:

- when used with the default local ZenML deployment or a local ZenML server, the
credentials are those set up on your machine (i.e. by running
`gcloud auth application-default login` or setting the
`GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to a service
account key JSON file).
- when connected to a ZenML server, this method only works if the ZenML server
is deployed in GCP and will use the service account attached to the GCP resource
where the ZenML server is running (e.g. an GKE cluster). The service account
permissions may need to be adjusted to allow listing and accessing/describing
the GCP resources that the connector is configured to access.

Note that the discovered credentials inherit the full set of permissions of the
local GCP CLI credentials or service account attached to the ZenML server GCP
workload. Depending on the extent of those permissions, this authentication
method might not be suitable for production use, as it can lead to accidental
privilege escalation. Instead, it is recommended to use the Service Account Key
or Service Account Impersonation authentication methods to restrict the
permissions that are granted to the connector clients.

To find out more about Application Default Credentials,
[see the GCP ADC documentation](https://cloud.google.com/docs/authentication/provide-credentials-adc).

A GCP project is required and the connector may only be used to access GCP
resources in the specified project. When used remotely in a GCP workload, the
configured project has to be the same as the project of the attached service
account.
""",
            config_class=GCPBaseConfig,
        ),
        AuthenticationMethodModel(
            name="GCP User Account",
            auth_method=GCPAuthenticationMethods.USER_ACCOUNT,
            description="""
Use a GCP user account and its credentials to authenticate to GCP services.

This method requires GCP user account credentials like those generated by
the `gcloud auth application-default login` command.

By default, the GCP connector generates temporary OAuth 2.0 tokens from the user
account credentials and distributes them to clients. The tokens have a limited
lifetime of 1 hour. This behavior can be disabled by setting the
`generate_temporary_tokens` configuration option to `False`, in which case, the
connector will distribute the user account credentials JSON to clients instead
(not recommended).

This method is preferred during development and testing due to its simplicity
and ease of use. It is not recommended as a direct authentication method for
production use cases because the clients are granted the full set of permissions
of the GCP user account. For production, it is recommended to use the GCP
Service Account or GCP Service Account Impersonation authentication methods.

A GCP project is required and the connector may only be used to access GCP
resources in the specified project.

If you already have the local GCP CLI set up with these credentials, they will
be automatically picked up when auto-configuration is used.
""",
            config_class=GCPUserAccountConfig,
        ),
        AuthenticationMethodModel(
            name="GCP Service Account",
            auth_method=GCPAuthenticationMethods.SERVICE_ACCOUNT,
            description="""
Use a GCP service account and its credentials to authenticate to GCP services.
This method requires a [GCP service account](https://cloud.google.com/iam/docs/service-account-overview)
and [a service account key JSON](https://cloud.google.com/iam/docs/service-account-creds#key-types)
created for it.

By default, the GCP connector generates temporary OAuth 2.0 tokens from the
service account credentials and distributes them to clients. The tokens have a
limited lifetime of 1 hour. This behavior can be disabled by setting the
`generate_temporary_tokens` configuration option to `False`, in which case, the
connector will distribute the service account credentials JSON to clients
instead (not recommended).

A GCP project is required and the connector may only be used to access GCP
resources in the specified project.

If you already have the GOOGLE_APPLICATION_CREDENTIALS environment variable
configured to point to a service account key JSON file, it will be automatically
picked up when auto-configuration is used.
""",
            config_class=GCPServiceAccountConfig,
        ),
        AuthenticationMethodModel(
            name="GCP External Account",
            auth_method=GCPAuthenticationMethods.EXTERNAL_ACCOUNT,
            description="""
Use [GCP workload identity federation](https://cloud.google.com/iam/docs/workload-identity-federation)
to authenticate to GCP services using AWS IAM credentials, Azure Active
Directory credentials or generic OIDC tokens.

This authentication method only requires a GCP workload identity external
account JSON file that only contains the configuration for the external account
without any sensitive credentials. It allows implementing a two layer
authentication scheme that keeps the set of permissions associated with implicit
credentials down to the bare minimum and grants permissions to the
privilege-bearing GCP service account instead.

This authentication method can be used to authenticate to GCP services using
credentials from other cloud providers or identity providers. When used with
workloads running on AWS or Azure, it involves automatically picking up
credentials from the AWS IAM or Azure AD identity associated with the workload
and using them to authenticate to GCP services. This means that the result
depends on the environment where the ZenML server is deployed and is thus not
fully reproducible.

By default, the GCP connector generates temporary OAuth 2.0 tokens from the
external account credentials and distributes them to clients. The tokens have a
limited lifetime of 1 hour. This behavior can be disabled by setting the
`generate_temporary_tokens` configuration option to `False`, in which case, the
connector will distribute the external account credentials JSON to clients
instead (not recommended).

A GCP project is required and the connector may only be used to access GCP
resources in the specified project. This project must be the same as the one
for which the external account was configured.

If you already have the GOOGLE_APPLICATION_CREDENTIALS environment variable
configured to point to an external account key JSON file, it will be
automatically picked up when auto-configuration is used.
""",
            config_class=GCPExternalAccountConfig,
        ),
        AuthenticationMethodModel(
            name="GCP Oauth 2.0 Token",
            auth_method=GCPAuthenticationMethods.OAUTH2_TOKEN,
            description="""
Uses temporary OAuth 2.0 tokens explicitly configured by the user.
This method has the major limitation that the user must regularly generate new
tokens and update the connector configuration as OAuth 2.0 tokens expire. On the
other hand, this method is ideal in cases where the connector only needs to be
used for a short period of time, such as sharing access temporarily with someone
else in your team.

Using any of the other authentication methods will automatically generate and
refresh OAuth 2.0 tokens for clients upon request.

A GCP project is required and the connector may only be used to access GCP
resources in the specified project.
""",
            config_class=GCPOAuth2TokenConfig,
        ),
        AuthenticationMethodModel(
            name="GCP Service Account Impersonation",
            auth_method=GCPAuthenticationMethods.IMPERSONATION,
            description="""
Generates temporary STS credentials by [impersonating another GCP service account](https://cloud.google.com/iam/docs/create-short-lived-credentials-direct#sa-impersonation).

The connector needs to be configured with the email address of the target GCP
service account to be impersonated, accompanied by a GCP service account key
JSON for the primary service account. The primary service account must have
permissions to generate tokens for the target service account (i.e. the
[Service Account Token Creator role](https://cloud.google.com/iam/docs/service-account-permissions#directly-impersonate)).
The connector will generate temporary OAuth 2.0 tokens upon request by using
[GCP direct service account impersonation](https://cloud.google.com/iam/docs/create-short-lived-credentials-direct#sa-impersonation).

The tokens have a configurable limited lifetime of up to 1 hour.

The best practice implemented with this authentication scheme is to keep the set
of permissions associated with the primary service account down to the bare
minimum and grant permissions to the privilege bearing service account instead.

A GCP project is required and the connector may only be used to access GCP
resources in the specified project.

If you already have the `GOOGLE_APPLICATION_CREDENTIALS` environment variable
configured to point to the primary service account key JSON file, it will be
automatically picked up when auto-configuration is used.
""",
            default_expiration_seconds=DEFAULT_IMPERSONATE_TOKEN_EXPIRATION,  # 1 hour
            max_expiration_seconds=DEFAULT_IMPERSONATE_TOKEN_EXPIRATION,  # 1 hour
            config_class=GCPServiceAccountImpersonationConfig,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="Generic GCP resource",
            resource_type=GCP_RESOURCE_TYPE,
            description="""
This resource type allows Stack Components to use the GCP Service Connector to
connect to any GCP service or resource. When used by Stack Components, they are
provided a Python google-auth credentials object populated with a GCP OAuth
2.0 token. This credentials object can then be used to create GCP Python clients
for any particular GCP service.

This generic GCP resource type is meant to be used with Stack Components that
are not represented by other, more specific resource type, like GCS buckets,
Kubernetes clusters or Docker registries. For example, it can be used with the
Google Cloud Builder Image Builder stack component, or the Vertex AI
Orchestrator and Step Operator. It should be accompanied by a matching set of
GCP permissions that allow access to the set of remote resources required by the
client and Stack Component.

The resource name represents the GCP project that the connector is authorized to
access.
""",
            auth_methods=GCPAuthenticationMethods.values(),
            # Don't request a GCP specific resource instance ID, given that
            # the connector provides a generic OAuth2 token.
            supports_instances=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/gcp/gcp.png",
            emoji=":blue_circle:",
        ),
        ResourceTypeModel(
            name="GCP GCS bucket",
            resource_type=GCS_RESOURCE_TYPE,
            description="""
Allows Stack Components to connect to GCS buckets. When used by Stack
Components, they are provided a pre-configured GCS Python client instance.

The configured credentials must have at least the following [GCP permissions](https://cloud.google.com/iam/docs/permissions-reference)
associated with the GCS buckets that it can access:

- `storage.buckets.list`
- `storage.buckets.get`
- `storage.objects.create`	
- `storage.objects.delete`	
- `storage.objects.get`	
- `storage.objects.list`	
- `storage.objects.update`

For example, the GCP Storage Admin role includes all of the required
permissions, but it also includes additional permissions that are not required
by the connector.

If set, the resource name must identify a GCS bucket using one of the following
formats:

- GCS bucket URI: gs://{bucket-name}
- GCS bucket name: {bucket-name}
""",
            auth_methods=GCPAuthenticationMethods.values(),
            # Request an GCS bucket to be configured in the
            # connector or provided by the consumer
            supports_instances=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/gcp.png",
            emoji=":package:",
        ),
        ResourceTypeModel(
            name="GCP GKE Kubernetes cluster",
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
            description="""
Allows Stack Components to access a GKE registry as a standard Kubernetes
cluster resource. When used by Stack Components, they are provided a
pre-authenticated Python Kubernetes client instance.

The configured credentials must have at least the following [GCP permissions](https://cloud.google.com/iam/docs/permissions-reference)
associated with the GKE clusters that it can access:

- `container.clusters.list`
- `container.clusters.get`

In addition to the above permissions, the credentials should include permissions
to connect to and use the GKE cluster (i.e. some or all permissions in the
Kubernetes Engine Developer role).

If set, the resource name must identify an GKE cluster using one of the
following formats:

- GKE cluster name: `{cluster-name}`

GKE cluster names are project scoped. The connector can only be used to access
GKE clusters in the GCP project that it is configured to use.
""",
            auth_methods=GCPAuthenticationMethods.values(),
            # Request an GKE cluster name to be configured in the
            # connector or provided by the consumer
            supports_instances=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png",
            emoji=":cyclone:",
        ),
        ResourceTypeModel(
            name="GCP GCR container registry",
            resource_type=DOCKER_REGISTRY_RESOURCE_TYPE,
            description="""
Allows Stack Components to access a GCR registry as a standard
Docker registry resource. When used by Stack Components, they are provided a
pre-authenticated Python Docker client instance.

The configured credentials must have at least the following [GCP permissions](https://cloud.google.com/iam/docs/permissions-reference):

- `storage.buckets.get`
- `storage.multipartUploads.abort`
- `storage.multipartUploads.create`
- `storage.multipartUploads.list`
- `storage.multipartUploads.listParts`
- `storage.objects.create`
- `storage.objects.delete`
- `storage.objects.list`

The Storage Legacy Bucket Writer role includes all of the above permissions
while at the same time restricting access to only the GCR buckets.

The resource name associated with this resource type identifies the GCR
container registry associated with the GCP project (the repository name is
optional):

- GCR repository URI: `[https://]gcr.io/{project-id}[/{repository-name}]
""",
            auth_methods=GCPAuthenticationMethods.values(),
            # Does not support instances, given that the connector
            # provides access to the entire GCR container registry
            # for the configured GCP project.
            supports_instances=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png",
            emoji=":whale:",
        ),
    ],
)


class GCPServiceConnector(ServiceConnector):
    """GCP service connector."""

    config: GCPBaseConfig

    _session_cache: Dict[
        Tuple[str, Optional[str], Optional[str]],
        Tuple[
            gcp_credentials.Credentials,
            Optional[datetime.datetime],
        ],
    ] = {}

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector type specification.

        Returns:
            The service connector type specification.
        """
        return GCP_SERVICE_CONNECTOR_TYPE_SPEC

    def get_session(
        self,
        auth_method: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Tuple[gcp_credentials.Credentials, Optional[datetime.datetime]]:
        """Get a GCP session object with credentials for the specified resource.

        Args:
            auth_method: The authentication method to use.
            resource_type: The resource type to get credentials for.
            resource_id: The resource ID to get credentials for.

        Returns:
            GCP session with credentials for the specified resource and its
            expiration timestamp, if applicable.
        """
        # We maintain a cache of all sessions to avoid re-authenticating
        # multiple times for the same resource
        key = (auth_method, resource_type, resource_id)
        if key in self._session_cache:
            session, expires_at = self._session_cache[key]
            if expires_at is None:
                return session, None

            # Refresh expired sessions
            now = datetime.datetime.now(datetime.timezone.utc)
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
            # check if the token expires in the near future
            if expires_at > now + datetime.timedelta(
                minutes=GCP_SESSION_EXPIRATION_BUFFER
            ):
                return session, expires_at

        logger.debug(
            f"Creating GCP authentication session for auth method "
            f"'{auth_method}', resource type '{resource_type}' and resource ID "
            f"'{resource_id}'..."
        )
        session, expires_at = self._authenticate(
            auth_method, resource_type, resource_id
        )
        self._session_cache[key] = (session, expires_at)
        return session, expires_at

    @classmethod
    def _get_scopes(
        cls,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """Get the OAuth 2.0 scopes to use for the specified resource type.

        Args:
            resource_type: The resource type to get scopes for.
            resource_id: The resource ID to get scopes for.

        Returns:
            OAuth 2.0 scopes to use for the specified resource type.
        """
        return [
            "https://www.googleapis.com/auth/cloud-platform",
        ]

    def _authenticate(
        self,
        auth_method: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Tuple[
        gcp_credentials.Credentials,
        Optional[datetime.datetime],
    ]:
        """Authenticate to GCP and return a session with credentials.

        Args:
            auth_method: The authentication method to use.
            resource_type: The resource type to authenticate for.
            resource_id: The resource ID to authenticate for.

        Returns:
            GCP OAuth 2.0 credentials and their expiration time if applicable.

        Raises:
            AuthorizationException: If the authentication fails.
        """
        cfg = self.config
        scopes = self._get_scopes(resource_type, resource_id)
        expires_at: Optional[datetime.datetime] = None
        if auth_method == GCPAuthenticationMethods.IMPLICIT:
            self._check_implicit_auth_method_allowed()

            # Determine the credentials from the environment
            # Override the project ID if specified in the config
            credentials, project_id = google.auth.default(
                scopes=scopes,
            )

        elif auth_method == GCPAuthenticationMethods.OAUTH2_TOKEN:
            assert isinstance(cfg, GCPOAuth2TokenConfig)

            expires_at = self.expires_at
            if expires_at:
                # Remove the UTC timezone
                expires_at = expires_at.replace(tzinfo=None)

            credentials = gcp_credentials.Credentials(
                token=cfg.token.get_secret_value(),
                expiry=expires_at,
                scopes=scopes,
            )

            if cfg.service_account_email:
                credentials.signer_email = cfg.service_account_email
        else:
            if auth_method == GCPAuthenticationMethods.USER_ACCOUNT:
                assert isinstance(cfg, GCPUserAccountConfig)
                credentials = (
                    gcp_credentials.Credentials.from_authorized_user_info(
                        json.loads(cfg.user_account_json.get_secret_value()),
                        scopes=scopes,
                    )
                )
            elif auth_method == GCPAuthenticationMethods.EXTERNAL_ACCOUNT:
                self._check_implicit_auth_method_allowed()

                assert isinstance(cfg, GCPExternalAccountConfig)

                # As a special case, for the AWS external account credential,
                # we use a custom credential class that supports extracting
                # the AWS credentials from the local environment, metadata
                # service or IRSA (if running on AWS EKS).
                account_info = json.loads(
                    cfg.external_account_json.get_secret_value()
                )
                if (
                    account_info.get("subject_token_type")
                    == _AWS_SUBJECT_TOKEN_TYPE
                ):
                    credentials = (
                        ZenMLGCPAWSExternalAccountCredentials.from_info(
                            account_info,
                            scopes=scopes,
                        )
                    )
                else:
                    credentials, _ = _get_external_account_credentials(
                        json.loads(
                            cfg.external_account_json.get_secret_value()
                        ),
                        filename="",  # Not used
                        scopes=scopes,
                    )

            else:
                # Service account or impersonation (which is a special case of
                # service account authentication)

                assert isinstance(cfg, GCPServiceAccountConfig)
                credentials = (
                    gcp_service_account.Credentials.from_service_account_info(
                        json.loads(
                            cfg.service_account_json.get_secret_value()
                        ),
                        scopes=scopes,
                    )
                )

                if auth_method == GCPAuthenticationMethods.IMPERSONATION:
                    assert isinstance(
                        cfg, GCPServiceAccountImpersonationConfig
                    )

                    try:
                        credentials = gcp_impersonated_credentials.Credentials(
                            source_credentials=credentials,
                            target_principal=cfg.target_principal,
                            target_scopes=scopes,
                            lifetime=self.expiration_seconds,
                        )
                    except google.auth.exceptions.GoogleAuthError as e:
                        raise AuthorizationException(
                            f"Failed to impersonate service account "
                            f"'{cfg.target_principal}': {e}"
                        )

        if not credentials.valid:
            try:
                with requests.Session() as session:
                    req = Request(session)
                    credentials.refresh(req)
            except google.auth.exceptions.GoogleAuthError as e:
                raise AuthorizationException(
                    f"Could not fetch GCP OAuth2 token: {e}"
                )

        if credentials.expiry:
            # Add the UTC timezone to the expiration time
            expires_at = credentials.expiry.replace(
                tzinfo=datetime.timezone.utc
            )

        return credentials, expires_at

    def _parse_gcs_resource_id(self, resource_id: str) -> str:
        """Validate and convert an GCS resource ID to an GCS bucket name.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The GCS bucket name.

        Raises:
            ValueError: If the provided resource ID is not a valid GCS bucket
                name or URI.
        """
        # The resource ID could mean different things:
        #
        # - an GCS bucket URI
        # - the GCS bucket name
        #
        # We need to extract the bucket name from the provided resource ID
        bucket_name: Optional[str] = None
        if re.match(
            r"^gs://[a-z0-9][a-z0-9_-]{1,61}[a-z0-9](/.*)*$",
            resource_id,
        ):
            # The resource ID is an GCS bucket URI
            bucket_name = resource_id.split("/")[2]
        elif re.match(
            r"^[a-z0-9][a-z0-9_-]{1,61}[a-z0-9]$",
            resource_id,
        ):
            # The resource ID is the GCS bucket name
            bucket_name = resource_id
        else:
            raise ValueError(
                f"Invalid resource ID for an GCS bucket: {resource_id}. "
                f"Supported formats are:\n"
                f"GCS bucket URI: gs://<bucket-name>\n"
                f"GCS bucket name: <bucket-name>"
            )

        return bucket_name

    def _parse_gcr_resource_id(
        self,
        resource_id: str,
    ) -> str:
        """Validate and convert an GCR resource ID to an GCR registry ID.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The GCR registry ID.

        Raises:
            ValueError: If the provided resource ID is not a valid GCR
                repository URI.
        """
        # The resource ID could mean different things:
        #
        # - an GCR repository URI
        #
        # We need to extract the project ID and registry ID from
        # the provided resource ID
        config_project_id = self.config.project_id
        project_id: Optional[str] = None
        # A GCR repository URI uses one of several hostnames (gcr.io, us.gcr.io,
        # eu.gcr.io, asia.gcr.io etc.) and the project ID is the first part of
        # the URL path
        if re.match(
            r"^(https://)?([a-z]+.)*gcr.io/[a-z0-9-]+(/.+)*$",
            resource_id,
        ):
            # The resource ID is a GCR repository URI
            if resource_id.startswith("https://"):
                project_id = resource_id.split("/")[3]
            else:
                project_id = resource_id.split("/")[1]
        else:
            raise ValueError(
                f"Invalid resource ID for a GCR registry: {resource_id}. "
                f"Supported formats are:\n"
                f"GCR repository URI: [https://][us.|eu.|asia.]gcr.io/<project-id>[/<repository-name>]"
            )

        # If the connector is configured with a project and the resource ID
        # is an GCR repository URI that specifies a different project,
        # we raise an error
        if project_id and project_id != config_project_id:
            raise ValueError(
                f"The GCP project for the {resource_id} GCR repository "
                f"'{project_id}' does not match the project configured in "
                f"the connector: '{config_project_id}'."
            )

        return f"gcr.io/{project_id}"

    def _parse_gke_resource_id(self, resource_id: str) -> str:
        """Validate and convert an GKE resource ID to a GKE cluster name.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The GKE cluster name.

        Raises:
            ValueError: If the provided resource ID is not a valid GKE cluster
                name.
        """
        if re.match(
            r"^[a-z0-9]+[a-z0-9_-]*$",
            resource_id,
        ):
            # Assume the resource ID is an GKE cluster name
            cluster_name = resource_id
        else:
            raise ValueError(
                f"Invalid resource ID for a GKE cluster: {resource_id}. "
                f"Supported formats are:\n"
                f"GKE cluster name: <cluster-name>"
            )

        return cluster_name

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
        if resource_type == GCS_RESOURCE_TYPE:
            bucket = self._parse_gcs_resource_id(resource_id)
            return f"gs://{bucket}"
        elif resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            cluster_name = self._parse_gke_resource_id(resource_id)
            return cluster_name
        elif resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            registry_id = self._parse_gcr_resource_id(
                resource_id,
            )
            return registry_id
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
            RuntimeError: If the GCR registry ID (GCP account ID)
                cannot be retrieved from GCP because the connector is not
                authorized.
        """
        if resource_type == GCP_RESOURCE_TYPE:
            return self.config.project_id
        elif resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            return f"gcr.io/{self.config.project_id}"

        raise RuntimeError(
            f"Default resource ID not supported for '{resource_type}' resource "
            "type."
        )

    def _connect_to_resource(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a GCP resource.

        Initialize and return a session or client object depending on the
        connector configuration:

        - initialize and return generic google-auth credentials if the resource
        type is a generic GCP resource
        - initialize and return a google-storage client for an GCS resource type

        For the Docker and Kubernetes resource types, the connector does not
        support connecting to the resource directly. Instead, the connector
        supports generating a connector client object for the resource type
        in question.

        Args:
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            Generic GCP credentials for GCP generic resources and a
            google-storage GCS client for GCS resources.

        Raises:
            NotImplementedError: If the connector instance does not support
                directly connecting to the indicated resource type.
        """
        resource_type = self.resource_type
        resource_id = self.resource_id

        assert resource_type is not None
        assert resource_id is not None

        # Regardless of the resource type, we must authenticate to GCP first
        # before we can connect to any GCP resource
        credentials, _ = self.get_session(
            self.auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if resource_type == GCS_RESOURCE_TYPE:
            # Validate that the resource ID is a valid GCS bucket name
            self._parse_gcs_resource_id(resource_id)

            # Create an GCS client for the bucket
            client = storage.Client(
                project=self.config.project_id, credentials=credentials
            )
            return client

        if resource_type == GCP_RESOURCE_TYPE:
            return credentials

        raise NotImplementedError(
            f"Connecting to {resource_type} resources is not directly "
            "supported by the GCP connector. Please call the "
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
            AuthorizationException: If the local client configuration fails.
        """
        resource_type = self.resource_type

        if resource_type in [GCP_RESOURCE_TYPE, GCS_RESOURCE_TYPE]:
            gcloud_config_json: Optional[str] = None

            # There is no way to configure the local gcloud CLI to use
            # temporary OAuth 2.0 tokens. However, we can configure it to use
            # the service account or external account credentials
            if self.auth_method == GCPAuthenticationMethods.SERVICE_ACCOUNT:
                assert isinstance(self.config, GCPServiceAccountConfig)
                # Use the service account credentials JSON to configure the
                # local gcloud CLI
                gcloud_config_json = (
                    self.config.service_account_json.get_secret_value()
                )
            elif self.auth_method == GCPAuthenticationMethods.EXTERNAL_ACCOUNT:
                assert isinstance(self.config, GCPExternalAccountConfig)
                # Use the external account credentials JSON to configure the
                # local gcloud CLI
                gcloud_config_json = (
                    self.config.external_account_json.get_secret_value()
                )

            if gcloud_config_json:
                from google.auth import _cloud_sdk

                if not shutil.which("gcloud"):
                    raise AuthorizationException(
                        "The local gcloud CLI is not installed. Please "
                        "install the gcloud CLI to use this feature."
                    )

                # Write the credentials JSON to a temporary file
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=True
                ) as f:
                    f.write(gcloud_config_json)
                    f.flush()
                    adc_path = f.name

                    try:
                        # Run the gcloud CLI command to configure the local
                        # gcloud CLI to use the credentials JSON
                        subprocess.run(
                            [
                                "gcloud",
                                "auth",
                                "login",
                                "--quiet",
                                "--cred-file",
                                adc_path,
                            ],
                            check=True,
                            stderr=subprocess.STDOUT,
                            encoding="utf-8",
                            stdout=subprocess.PIPE,
                        )
                    except subprocess.CalledProcessError as e:
                        raise AuthorizationException(
                            f"Failed to configure the local gcloud CLI to use "
                            f"the credentials JSON: {e}\n"
                            f"{e.stdout.decode()}"
                        )

                try:
                    # Run the gcloud CLI command to configure the local gcloud
                    # CLI to use the credentials project ID
                    subprocess.run(
                        [
                            "gcloud",
                            "config",
                            "set",
                            "project",
                            self.config.project_id,
                        ],
                        check=True,
                        stderr=subprocess.STDOUT,
                        stdout=subprocess.PIPE,
                    )
                except subprocess.CalledProcessError as e:
                    raise AuthorizationException(
                        f"Failed to configure the local gcloud CLI to use "
                        f"the project ID: {e}\n"
                        f"{e.stdout.decode()}"
                    )

                # Dump the service account credentials JSON to
                # the local gcloud application default credentials file
                adc_path = (
                    _cloud_sdk.get_application_default_credentials_path()
                )
                with open(adc_path, "w") as f:
                    f.write(gcloud_config_json)

                logger.info(
                    "Updated the local gcloud CLI and application default "
                    f"credentials file ({adc_path})."
                )

                return

            raise NotImplementedError(
                f"Local gcloud client configuration for resource type "
                f"{resource_type} is only supported if the "
                f"'{GCPAuthenticationMethods.SERVICE_ACCOUNT}' or "
                f"'{GCPAuthenticationMethods.EXTERNAL_ACCOUNT}' "
                f"authentication method is used and only if the generation of "
                f"temporary OAuth 2.0 tokens is disabled by setting the "
                f"'generate_temporary_tokens' option to 'False' in the "
                f"service connector configuration."
            )

        raise NotImplementedError(
            f"Configuring the local client for {resource_type} resources is "
            "not directly supported by the GCP connector. Please call the "
            f"`get_connector_client` method to get a {resource_type} connector "
            "instance for the resource."
        )

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "GCPServiceConnector":
        """Auto-configure the connector.

        Instantiate a GCP connector with a configuration extracted from the
        authentication configuration available in the environment (e.g.
        environment variables or local GCP client/SDK configuration files).

        Args:
            auth_method: The particular authentication method to use. If not
                specified, the connector implementation must decide which
                authentication method to use or raise an exception.
            resource_type: The type of resource to configure.
            resource_id: The ID of the resource to configure. The
                implementation may choose to either require or ignore this
                parameter if it does not support or detect an resource type that
                supports multiple instances.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            A GCP connector instance configured with authentication credentials
            automatically extracted from the environment.

        Raises:
            NotImplementedError: If the connector implementation does not
                support auto-configuration for the specified authentication
                method.
            AuthorizationException: If no GCP credentials can be loaded from
                the environment.
        """
        auth_config: GCPBaseConfig

        scopes = cls._get_scopes()
        expires_at: Optional[datetime.datetime] = None

        try:
            # Determine the credentials from the environment
            credentials, project_id = google.auth.default(
                scopes=scopes,
            )
        except google.auth.exceptions.GoogleAuthError as e:
            raise AuthorizationException(
                f"No GCP credentials could be detected: {e}"
            )

        if project_id is None:
            raise AuthorizationException(
                "No GCP project ID could be detected. Please set the active "
                "GCP project ID by running 'gcloud config set project'."
            )

        if auth_method == GCPAuthenticationMethods.IMPLICIT:
            auth_config = GCPBaseConfig(
                project_id=project_id,
            )
        elif auth_method == GCPAuthenticationMethods.OAUTH2_TOKEN:
            # Refresh the credentials if necessary, to fetch the access token
            if not credentials.valid or not credentials.token:
                try:
                    with requests.Session() as session:
                        req = Request(session)
                        credentials.refresh(req)
                except google.auth.exceptions.GoogleAuthError as e:
                    raise AuthorizationException(
                        f"Could not fetch GCP OAuth2 token: {e}"
                    )

            if not credentials.token:
                raise AuthorizationException(
                    "Could not fetch GCP OAuth2 token"
                )

            auth_config = GCPOAuth2TokenConfig(
                project_id=project_id,
                token=credentials.token,
                service_account_email=credentials.signer_email
                if hasattr(credentials, "signer_email")
                else None,
            )
            if credentials.expiry:
                # Add the UTC timezone to the expiration time
                expires_at = credentials.expiry.replace(
                    tzinfo=datetime.timezone.utc
                )
        else:
            # Check if user account credentials are available
            if isinstance(credentials, gcp_credentials.Credentials):
                if auth_method not in [
                    GCPAuthenticationMethods.USER_ACCOUNT,
                    None,
                ]:
                    raise NotImplementedError(
                        f"Could not perform auto-configuration for "
                        f"authentication method {auth_method}. Only "
                        f"GCP user account credentials have been detected."
                    )
                auth_method = GCPAuthenticationMethods.USER_ACCOUNT
                user_account_json = json.dumps(
                    dict(
                        type="authorized_user",
                        client_id=credentials._client_id,
                        client_secret=credentials._client_secret,
                        refresh_token=credentials.refresh_token,
                    )
                )
                auth_config = GCPUserAccountConfig(
                    project_id=project_id,
                    user_account_json=user_account_json,
                )
            # Check if service account credentials are available
            elif isinstance(credentials, gcp_service_account.Credentials):
                if auth_method not in [
                    GCPAuthenticationMethods.SERVICE_ACCOUNT,
                    None,
                ]:
                    raise NotImplementedError(
                        f"Could not perform auto-configuration for "
                        f"authentication method {auth_method}. Only "
                        f"GCP service account credentials have been detected."
                    )

                auth_method = GCPAuthenticationMethods.SERVICE_ACCOUNT
                service_account_json_file = os.environ.get(
                    "GOOGLE_APPLICATION_CREDENTIALS"
                )
                if service_account_json_file is None:
                    # No explicit service account JSON file was specified in the
                    # environment, meaning that the credentials were loaded from
                    # the GCP application default credentials (ADC) file.
                    from google.auth import _cloud_sdk

                    # Use the location of the gcloud application default
                    # credentials file
                    service_account_json_file = (
                        _cloud_sdk.get_application_default_credentials_path()
                    )

                if not service_account_json_file or not os.path.isfile(
                    service_account_json_file
                ):
                    raise AuthorizationException(
                        "No GCP service account credentials were found in the "
                        "environment or the application default credentials "
                        "path. Please set the GOOGLE_APPLICATION_CREDENTIALS "
                        "environment variable to the path of the service "
                        "account JSON file or run 'gcloud auth application-"
                        "default login' to generate a new ADC file."
                    )
                with open(service_account_json_file, "r") as f:
                    service_account_json = f.read()
                auth_config = GCPServiceAccountConfig(
                    project_id=project_id,
                    service_account_json=service_account_json,
                )
            # Check if external account credentials are available
            elif isinstance(credentials, gcp_external_account.Credentials):
                if auth_method not in [
                    GCPAuthenticationMethods.EXTERNAL_ACCOUNT,
                    None,
                ]:
                    raise NotImplementedError(
                        f"Could not perform auto-configuration for "
                        f"authentication method {auth_method}. Only "
                        f"GCP external account credentials have been detected."
                    )

                auth_method = GCPAuthenticationMethods.EXTERNAL_ACCOUNT
                external_account_json_file = os.environ.get(
                    "GOOGLE_APPLICATION_CREDENTIALS"
                )
                if external_account_json_file is None:
                    # No explicit service account JSON file was specified in the
                    # environment, meaning that the credentials were loaded from
                    # the GCP application default credentials (ADC) file.
                    from google.auth import _cloud_sdk

                    # Use the location of the gcloud application default
                    # credentials file
                    external_account_json_file = (
                        _cloud_sdk.get_application_default_credentials_path()
                    )

                if not external_account_json_file or not os.path.isfile(
                    external_account_json_file
                ):
                    raise AuthorizationException(
                        "No GCP service account credentials were found in the "
                        "environment or the application default credentials "
                        "path. Please set the GOOGLE_APPLICATION_CREDENTIALS "
                        "environment variable to the path of the external "
                        "account JSON file or run 'gcloud auth application-"
                        "default login' to generate a new ADC file."
                    )
                with open(external_account_json_file, "r") as f:
                    external_account_json = f.read()
                auth_config = GCPExternalAccountConfig(
                    project_id=project_id,
                    external_account_json=external_account_json,
                )
            else:
                raise AuthorizationException(
                    "No valid GCP credentials could be detected."
                )

        return cls(
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id
            if resource_type not in [GCP_RESOURCE_TYPE, None]
            else None,
            expires_at=expires_at,
            config=auth_config,
        )

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
        # same as a generic GCP connector.
        credentials, _ = self.get_session(
            self.auth_method,
            resource_type=resource_type or GCP_RESOURCE_TYPE,
            resource_id=resource_id,
        )

        if not resource_type:
            return []

        if resource_type == GCP_RESOURCE_TYPE:
            assert resource_id is not None
            return [resource_id]

        if resource_type == GCS_RESOURCE_TYPE:
            gcs_client = storage.Client(
                project=self.config.project_id, credentials=credentials
            )
            if not resource_id:
                # List all GCS buckets
                try:
                    buckets = gcs_client.list_buckets()
                    bucket_names = [bucket.name for bucket in buckets]
                except google.api_core.exceptions.GoogleAPIError as e:
                    msg = f"failed to list GCS buckets: {e}"
                    logger.error(msg)
                    raise AuthorizationException(msg) from e

                return [f"gs://{bucket}" for bucket in bucket_names]
            else:
                # Check if the specified GCS bucket exists
                bucket_name = self._parse_gcs_resource_id(resource_id)
                try:
                    gcs_client.get_bucket(bucket_name)
                    return [resource_id]
                except google.api_core.exceptions.GoogleAPIError as e:
                    msg = f"failed to fetch GCS bucket {bucket_name}: {e}"
                    logger.error(msg)
                    raise AuthorizationException(msg) from e

        if resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            assert resource_id is not None

            # No way to verify a GCR registry without attempting to
            # connect to it via Docker/OCI, so just return the resource ID.
            return [resource_id]

        if resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            gke_client = container_v1.ClusterManagerClient(
                credentials=credentials
            )

            # List all GKE clusters
            try:
                clusters = gke_client.list_clusters(
                    parent=f"projects/{self.config.project_id}/locations/-"
                )
                cluster_names = [cluster.name for cluster in clusters.clusters]
            except google.api_core.exceptions.GoogleAPIError as e:
                msg = f"Failed to list GKE clusters: {e}"
                logger.error(msg)
                raise AuthorizationException(msg) from e

            if not resource_id:
                return cluster_names
            else:
                # Check if the specified GKE cluster exists
                cluster_name = self._parse_gke_resource_id(resource_id)
                if cluster_name not in cluster_names:
                    raise AuthorizationException(
                        f"GKE cluster '{cluster_name}' not found or not "
                        "accessible."
                    )

                return [resource_id]

        return []

    def _get_connector_client(
        self,
        resource_type: str,
        resource_id: str,
    ) -> "ServiceConnector":
        """Get a connector instance that can be used to connect to a resource.

        This method generates a client-side connector instance that can be used
        to connect to a resource of the given type. The client-side connector
        is configured with temporary GCP credentials extracted from the
        current connector and, depending on resource type, it may also be
        of a different connector type:

        - a Kubernetes connector for Kubernetes clusters
        - a Docker connector for Docker registries

        Args:
            resource_type: The type of the resources to connect to.
            resource_id: The ID of a particular resource to connect to.

        Returns:
            A GCP, Kubernetes or Docker connector instance that can be used to
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

        credentials, expires_at = self.get_session(
            self.auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if resource_type in [GCP_RESOURCE_TYPE, GCS_RESOURCE_TYPE]:
            # By default, use the token extracted from the google credentials
            # object
            auth_method: str = GCPAuthenticationMethods.OAUTH2_TOKEN
            config: GCPBaseConfig = GCPOAuth2TokenConfig(
                project_id=self.config.project_id,
                token=credentials.token,
                service_account_email=credentials.signer_email
                if hasattr(credentials, "signer_email")
                else None,
            )

            # If the connector is explicitly configured to not generate
            # temporary tokens, use the original config
            if self.auth_method == GCPAuthenticationMethods.USER_ACCOUNT:
                assert isinstance(self.config, GCPUserAccountConfig)
                if not self.config.generate_temporary_tokens:
                    config = self.config
                    auth_method = self.auth_method
                    expires_at = None
            elif self.auth_method == GCPAuthenticationMethods.SERVICE_ACCOUNT:
                assert isinstance(self.config, GCPServiceAccountConfig)
                if not self.config.generate_temporary_tokens:
                    config = self.config
                    auth_method = self.auth_method
                    expires_at = None
            elif self.auth_method == GCPAuthenticationMethods.EXTERNAL_ACCOUNT:
                assert isinstance(self.config, GCPExternalAccountConfig)
                if not self.config.generate_temporary_tokens:
                    config = self.config
                    auth_method = self.auth_method
                    expires_at = None

            # Create a client-side GCP connector instance that is fully formed
            # and ready to use to connect to the specified resource (i.e. has
            # all the necessary configuration and credentials, a resource type
            # and a resource ID where applicable)
            return GCPServiceConnector(
                id=self.id,
                name=connector_name,
                auth_method=auth_method,
                resource_type=resource_type,
                resource_id=resource_id,
                config=config,
                expires_at=expires_at,
            )

        if resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            assert resource_id is not None

            registry_id = self._parse_gcr_resource_id(resource_id)

            # Create a client-side Docker connector instance with the temporary
            # Docker credentials
            return DockerServiceConnector(
                id=self.id,
                name=connector_name,
                auth_method=DockerAuthenticationMethods.PASSWORD,
                resource_type=resource_type,
                config=DockerConfiguration(
                    username="oauth2accesstoken",
                    password=credentials.token,
                    registry=registry_id,
                ),
                expires_at=expires_at,
            )

        if resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            assert resource_id is not None

            cluster_name = self._parse_gke_resource_id(resource_id)

            gke_client = container_v1.ClusterManagerClient(
                credentials=credentials
            )

            # List all GKE clusters
            try:
                clusters = gke_client.list_clusters(
                    parent=f"projects/{self.config.project_id}/locations/-"
                )
                cluster_map = {
                    cluster.name: cluster for cluster in clusters.clusters
                }
            except google.api_core.exceptions.GoogleAPIError as e:
                msg = f"Failed to list GKE clusters: {e}"
                logger.error(msg)
                raise AuthorizationException(msg) from e

            # Find the cluster with the specified name
            if cluster_name not in cluster_map:
                raise AuthorizationException(
                    f"GKE cluster '{cluster_name}' not found or not "
                    "accessible."
                )

            cluster = cluster_map[cluster_name]

            # get cluster details
            cluster_server = cluster.endpoint
            cluster_ca_cert = cluster.master_auth.cluster_ca_certificate
            bearer_token = credentials.token

            # Create a client-side Kubernetes connector instance with the
            # temporary Kubernetes credentials
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
            return KubernetesServiceConnector(
                id=self.id,
                name=connector_name,
                auth_method=KubernetesAuthenticationMethods.TOKEN,
                resource_type=resource_type,
                config=KubernetesTokenConfig(
                    cluster_name=f"gke_{self.config.project_id}_{cluster_name}",
                    certificate_authority=cluster_ca_cert,
                    server=f"https://{cluster_server}",
                    token=bearer_token,
                ),
                expires_at=expires_at,
            )

        raise ValueError(f"Unsupported resource type: {resource_type}")
