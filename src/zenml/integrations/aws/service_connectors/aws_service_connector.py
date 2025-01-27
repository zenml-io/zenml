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
"""AWS Service Connector.

The AWS Service Connector implements various authentication methods for AWS
services:

- Explicit AWS secret key (access key, secret key)
- Explicit  AWS STS tokens (access key, secret key, session token)
- IAM roles (i.e. generating temporary STS tokens on the fly by assuming an
IAM role)
- IAM user federation tokens
- STS Session tokens

"""

import base64
import datetime
import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple, cast

import boto3
from aws_profile_manager import Common  # type: ignore[import-untyped]
from botocore.client import BaseClient
from botocore.exceptions import BotoCoreError, ClientError
from botocore.signers import RequestSigner
from pydantic import Field

from zenml.constants import (
    DOCKER_REGISTRY_RESOURCE_TYPE,
    KUBERNETES_CLUSTER_RESOURCE_TYPE,
)
from zenml.exceptions import AuthorizationException
from zenml.integrations.aws import (
    AWS_CONNECTOR_TYPE,
    AWS_RESOURCE_TYPE,
    S3_RESOURCE_TYPE,
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
from zenml.utils.time_utils import utc_now_tz_aware

logger = get_logger(__name__)

EKS_KUBE_API_TOKEN_EXPIRATION = 15  # 15 minutes
DEFAULT_IAM_ROLE_TOKEN_EXPIRATION = 3600  # 1 hour
DEFAULT_STS_TOKEN_EXPIRATION = 43200  # 12 hours
BOTO3_SESSION_EXPIRATION_BUFFER = 15  # 15 minutes


class AWSSecretKey(AuthenticationConfig):
    """AWS secret key credentials."""

    aws_access_key_id: PlainSerializedSecretStr = Field(
        title="AWS Access Key ID",
        description="An AWS access key ID associated with an AWS account or IAM user.",
    )
    aws_secret_access_key: PlainSerializedSecretStr = Field(
        title="AWS Secret Access Key",
    )


class STSToken(AWSSecretKey):
    """AWS STS token."""

    aws_session_token: PlainSerializedSecretStr = Field(
        title="AWS Session Token",
    )


class AWSBaseConfig(AuthenticationConfig):
    """AWS base configuration."""

    region: str = Field(
        title="AWS Region",
    )
    endpoint_url: Optional[str] = Field(
        default=None,
        title="AWS Endpoint URL",
    )


class AWSSessionPolicy(AuthenticationConfig):
    """AWS session IAM policy configuration."""

    policy_arns: Optional[List[str]] = Field(
        default=None,
        title="ARNs of the IAM managed policies that you want to use as a "
        "managed session policy. The policies must exist in the same account "
        "as the IAM user that is requesting temporary credentials.",
    )
    policy: Optional[str] = Field(
        default=None,
        title="An IAM policy in JSON format that you want to use as an inline "
        "session policy",
    )


class AWSImplicitConfig(AWSBaseConfig, AWSSessionPolicy):
    """AWS implicit configuration."""

    profile_name: Optional[str] = Field(
        default=None,
        title="AWS Profile Name",
    )
    role_arn: Optional[str] = Field(
        default=None,
        title="Optional AWS IAM Role ARN to assume",
    )


class AWSSecretKeyConfig(AWSBaseConfig, AWSSecretKey):
    """AWS secret key authentication configuration."""


class STSTokenConfig(AWSBaseConfig, STSToken):
    """AWS STS token authentication configuration."""


class IAMRoleAuthenticationConfig(AWSSecretKeyConfig, AWSSessionPolicy):
    """AWS IAM authentication config."""

    role_arn: str = Field(
        title="AWS IAM Role ARN",
    )


class SessionTokenAuthenticationConfig(AWSSecretKeyConfig):
    """AWS session token authentication config."""


class FederationTokenAuthenticationConfig(
    AWSSecretKeyConfig, AWSSessionPolicy
):
    """AWS federation token authentication config."""


class AWSAuthenticationMethods(StrEnum):
    """AWS Authentication methods."""

    IMPLICIT = "implicit"
    SECRET_KEY = "secret-key"
    STS_TOKEN = "sts-token"
    IAM_ROLE = "iam-role"
    SESSION_TOKEN = "session-token"
    FEDERATION_TOKEN = "federation-token"


AWS_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="AWS Service Connector",
    connector_type=AWS_CONNECTOR_TYPE,
    description="""
The ZenML AWS Service Connector facilitates the authentication and access to
managed AWS services and resources. These encompass a range of resources,
including S3 buckets, ECR repositories, and EKS clusters. The connector
provides support for various authentication methods, including explicit
long-lived AWS secret keys, IAM roles, short-lived STS tokens and implicit
authentication.

To ensure heightened security measures, this connector also enables the
generation of temporary STS security tokens that are scoped down to the
minimum permissions necessary for accessing the intended resource. Furthermore,
it includes automatic configuration and detection of credentials locally
configured through the AWS CLI.

This connector serves as a general means of accessing any AWS service by
issuing pre-authenticated boto3 sessions to clients. Additionally, the connector
can handle specialized authentication for S3, Docker and Kubernetes Python
clients. It also allows for the configuration of local Docker and Kubernetes
CLIs.

The AWS Service Connector is part of the AWS ZenML integration. You can either
install the entire integration or use a pypi extra to install it independently
of the integration:

* `pip install "zenml[connectors-aws]"` installs only prerequisites for the AWS
Service Connector Type
* `zenml integration install aws` installs the entire AWS ZenML integration

It is not required to [install and set up the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
on your local machine to use the AWS Service Connector to link Stack Components
to AWS resources and services. However, it is recommended to do so if you are
looking for a quick setup that includes using the auto-configuration Service
Connector features.
""",
    supports_auto_configuration=True,
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/aws/aws.png",
    emoji=":large_orange_diamond:",
    auth_methods=[
        AuthenticationMethodModel(
            name="AWS Implicit Authentication",
            auth_method=AWSAuthenticationMethods.IMPLICIT,
            description="""
Implicit authentication to AWS services using environment variables, local
configuration files or IAM roles. This authentication method doesn't require
any credentials to be explicitly configured. It automatically discovers and uses
credentials from one of the following sources:

- environment variables (AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
AWS_SESSION_TOKEN, AWS_DEFAULT_REGION)
- local configuration files [set up through the AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-configure.html)
(~/aws/credentials, ~/.aws/config)
- IAM roles for Amazon EC2, ECS, EKS, Lambda, etc. Only works when running
the ZenML server on an AWS resource with an IAM role attached to it.

This is the quickest and easiest way to authenticate to AWS services. However,
the results depend on how ZenML is deployed and the environment where it is used
and is thus not fully reproducible:

- when used with the default local ZenML deployment or a local ZenML server, the
credentials are the same as those used by the AWS CLI or extracted from local
environment variables.
- when connected to a ZenML server, this method only works if the ZenML server
is deployed in AWS and will use the IAM role attached to the AWS resource where
the ZenML server is running (e.g. an EKS cluster). The IAM role permissions may
need to be adjusted to allows listing and accessing/describing the AWS resources
that the connector is configured to access.

An IAM role may optionally be specified to be assumed by the connector on top of
the implicit credentials. This is only possible when the implicit credentials
have permissions to assume the target IAM role. Configuring an IAM role has all
the advantages of the AWS IAM Role authentication method plus the added benefit
of not requiring any explicit credentials to be configured and stored:

* The connector will generate temporary STS tokens upon request by
[calling the AssumeRole STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_assumerole).
* Allows implementing a two layer authentication scheme that keeps the set of
permissions associated with implicit credentials down to the bare minimum and
grants permissions to the privilege-bearing IAM role instead.
* One or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html#policies_session)
may also be configured to further restrict the permissions of the generated
STS tokens. If not specified, IAM session policies are automatically configured
for the generated STS tokens to restrict them to the minimum set of permissions
required to access the target resource. Refer to the documentation for each
supported Resource Type for the complete list of AWS permissions automatically
granted to the generated STS tokens.
* The default expiration period for generated STS tokens is 1 hour with a
minimum of 15 minutes up to the maximum session duration setting configured for
the IAM role (default is 1 hour). If you need longer-lived tokens, you can
configure the IAM role to use a higher maximum expiration value (up to 12 hours)
or use the AWS Federation Token or AWS Session Token authentication methods.

Note that the discovered credentials inherit the full set of permissions of the
local AWS client configuration, environment variables or attached AWS IAM role.
Depending on the extent of those permissions, this authentication method might
not be recommended for production use, as it can lead to accidental privilege
escalation. It is recommended to also configure an IAM role when using
the implicit authentication method, or to use the AWS IAM Role, AWS Session
Token or AWS Federation Token authentication methods instead to limit the
validity and/or permissions of the credentials being issued to connector
clients.

If you need to access an EKS kubernetes cluster with this authentication method,
please be advised that the EKS cluster's aws-auth ConfigMap may need to be
manually configured to allow authentication with the implicit IAM user or role
picked up by the Service Connector. For more information,
[see this documentation](https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html).

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.
""",
            min_expiration_seconds=900,  # 15 minutes
            default_expiration_seconds=DEFAULT_IAM_ROLE_TOKEN_EXPIRATION,  # 1 hour
            config_class=AWSImplicitConfig,
        ),
        AuthenticationMethodModel(
            name="AWS Secret Key",
            auth_method=AWSAuthenticationMethods.SECRET_KEY,
            description="""
Long-lived AWS credentials consisting of an AWS access key ID and secret access
key associated with an AWS IAM user or AWS account root user (not recommended).

This method is preferred during development and testing due to its simplicity
and ease of use. It is not recommended as a direct authentication method for
production use cases because the clients have direct access to long-lived
credentials and are granted the full set of permissions of the IAM user or AWS
account root user associated with the credentials. For production, it is
recommended to use the AWS IAM Role, AWS Session Token or AWS Federation Token
authentication method instead.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.

If you already have the local AWS CLI set up with these credentials, they will
be automatically picked up when auto-configuration is used.
""",
            config_class=AWSSecretKeyConfig,
        ),
        AuthenticationMethodModel(
            name="AWS STS Token",
            auth_method=AWSAuthenticationMethods.STS_TOKEN,
            description="""
Uses temporary STS tokens explicitly configured by the user or auto-configured
from a local environment. This method has the major limitation that the user
must regularly generate new tokens and update the connector configuration as STS
tokens expire. On the other hand, this method is ideal in cases where the
connector only needs to be used for a short period of time, such as sharing
access temporarily with someone else in your team.

Using other authentication methods like IAM role, Session Token or Federation
Token will automatically generate and refresh STS tokens for clients upon
request.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.
""",
            config_class=STSTokenConfig,
        ),
        AuthenticationMethodModel(
            name="AWS IAM Role",
            auth_method=AWSAuthenticationMethods.IAM_ROLE,
            description="""
Generates temporary STS credentials by assuming an AWS IAM role.
The connector needs to be configured with the IAM role to be assumed accompanied
by an AWS secret key associated with an IAM user or an STS token associated with
another IAM role. The IAM user or IAM role must have permissions to assume the
target IAM role. The connector will generate temporary STS tokens upon
request by [calling the AssumeRole STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_assumerole).

This authentication method still requires credentials to be explicitly
configured. If your ZenML server is running in AWS and you're looking for an
alternative that uses implicit credentials while at the same time benefits from
all the security advantages of assuming an IAM role, you should use the implicit
authentication method with a configured IAM role instead.

The best practice implemented with this authentication scheme is to keep the set
of permissions associated with the primary IAM user or IAM role down to the bare
minimum and grant permissions to the privilege bearing IAM role instead.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.

One or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html#policies_session)
may also be configured to further restrict the permissions of the generated STS
tokens. If not specified, IAM session policies are automatically configured for
the generated STS tokens to restrict them to the minimum set of permissions
required to access the target resource. Refer to the documentation for each
supported Resource Type for the complete list of AWS permissions automatically
granted to the generated STS tokens.

The default expiration period for generated STS tokens is 1 hour with a minimum
of 15 minutes up to the maximum session duration setting configured for the IAM
role (default is 1 hour). If you need longer-lived tokens, you can configure the
IAM role to use a higher maximum expiration value (up to 12 hours) or use the
AWS Federation Token or AWS Session Token authentication methods.

For more information on IAM roles and the AssumeRole AWS API, see
[the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_assumerole).

For more information about the difference between this method and the AWS
Federation Token authentication method,
[consult this AWS documentation page](https://aws.amazon.com/blogs/security/understanding-the-api-options-for-securely-delegating-access-to-your-aws-account/). 
""",
            min_expiration_seconds=900,  # 15 minutes
            default_expiration_seconds=DEFAULT_IAM_ROLE_TOKEN_EXPIRATION,  # 1 hour
            config_class=IAMRoleAuthenticationConfig,
        ),
        AuthenticationMethodModel(
            name="AWS Session Token",
            auth_method=AWSAuthenticationMethods.SESSION_TOKEN,
            description="""
Generates temporary session STS tokens for IAM users.
The connector needs to be configured with an AWS secret key associated with an
IAM user or AWS account root user (not recommended). The connector will generate
temporary STS tokens upon request by calling [the GetSessionToken STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_getsessiontoken).

These STS tokens have an expiration period longer that those issued through the
AWS IAM Role authentication method and are more suitable for long-running
processes that cannot automatically re-generate credentials upon expiration.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.

The default expiration period for generated STS tokens is 12 hours with a
minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained
by using the AWS account root user credentials (not recommended) have a maximum
duration of 1 hour.

As a precaution, when long-lived credentials (i.e. AWS Secret Keys) are detected
on your environment by the Service Connector during auto-configuration, this
authentication method is automatically chosen instead of the AWS Secret Key
authentication method alternative.

Generated STS tokens inherit the full set of permissions of the IAM user or
AWS account root user that is calling the GetSessionToken API. Depending on your
security needs, this may not be suitable for production use, as it can lead to
accidental privilege escalation. Instead, it is recommended to use the AWS
Federation Token or AWS IAM Role authentication methods to restrict the
permissions of the generated STS tokens.

For more information on session tokens and the GetSessionToken AWS API, see:
[the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_getsessiontoken).
""",
            min_expiration_seconds=900,  # 15 minutes
            max_expiration_seconds=129600,  # 36 hours
            default_expiration_seconds=DEFAULT_STS_TOKEN_EXPIRATION,  # 12 hours
            config_class=SessionTokenAuthenticationConfig,
        ),
        AuthenticationMethodModel(
            name="AWS Federation Token",
            auth_method=AWSAuthenticationMethods.FEDERATION_TOKEN,
            description="""
Generates temporary STS tokens for federated users.
The connector needs to be configured with an AWS secret key associated with an
IAM user or AWS account root user (not recommended). The IAM user must have
permissions to call [the GetFederationToken STS API](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_getfederationtoken)
(i.e. allow the `sts:GetFederationToken` action on the `*` IAM resource). The
connector will generate temporary STS tokens upon request by calling the
GetFederationToken STS API.

These STS tokens have an expiration period longer that those issued through the AWS IAM Role
authentication method and are more suitable for long-running processes that
cannot automatically re-generate credentials upon expiration.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.

One or more optional [IAM session policies](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html#policies_session)
may also be configured to further restrict the permissions of the generated STS
tokens. If not specified, IAM session policies are automatically configured for
the generated STS tokens to restrict them to the minimum set of permissions
required to access the target resource. Refer to the documentation for each
supported Resource Type for the complete list of AWS permissions automatically
granted to the generated STS tokens.

If this authentication method is used with the generic AWS resource type, a
session policy MUST be explicitly specified, otherwise the generated STS tokens
will not have any permissions.

The default expiration period for generated STS tokens is 12 hours with a
minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained
by using the AWS account root user credentials (not recommended) have a maximum
duration of 1 hour.

If you need to access an EKS kubernetes cluster with this authentication method,
please be advised that the EKS cluster's aws-auth ConfigMap may need to be
manually configured to allow authentication with the federated user. For more
information, [see this documentation](https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html).

For more information on user federation tokens, session policies and the
GetFederationToken AWS API, see [the official AWS documentation on the subject](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_getfederationtoken).

For more information about the difference between this method and the AWS
IAM Role authentication method,
[consult this AWS documentation page](https://aws.amazon.com/blogs/security/understanding-the-api-options-for-securely-delegating-access-to-your-aws-account/).
""",
            min_expiration_seconds=900,  # 15 minutes
            max_expiration_seconds=129600,  # 36 hours
            default_expiration_seconds=DEFAULT_STS_TOKEN_EXPIRATION,  # 12 hours
            config_class=FederationTokenAuthenticationConfig,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="Generic AWS resource",
            resource_type=AWS_RESOURCE_TYPE,
            description="""
Multi-purpose AWS resource type. It allows Stack Components to use the connector
to connect to any AWS service. When used by Stack Components, they are provided
a generic Python boto3 session instance pre-configured with AWS credentials.
This session can then be used to create boto3 clients for any particular AWS
service.

This generic AWS resource type is meant to be used with Stack Components that
are not represented by other, more specific resource type, like S3 buckets,
Kubernetes clusters or Docker registries. It should be accompanied by a matching
set of AWS permissions that allow access to the set of remote resources required
by the client(s).

The resource name represents the AWS region that the connector is authorized to
access.
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Don't request an AWS specific resource instance ID, given that
            # the connector provides a generic boto3 session instance.
            supports_instances=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/connectors/aws/aws.png",
            emoji=":large_orange_diamond:",
        ),
        ResourceTypeModel(
            name="AWS S3 bucket",
            resource_type=S3_RESOURCE_TYPE,
            description="""
Allows users to connect to S3 buckets. When used by Stack Components, they
are provided a pre-configured boto3 S3 client instance.

The configured credentials must have at least the following
[AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html)
associated with the [ARNs of S3 buckets](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-arn-format.html)
that the connector will be allowed to access (e.g. `arn:aws:s3:::*` and
`arn:aws:s3:::*/*` represent all the available S3 buckets).

- `s3:ListBucket`
- `s3:GetObject`
- `s3:PutObject`
- `s3:DeleteObject`
- `s3:ListAllMyBuckets`
- `s3:GetBucketVersioning`
- `s3:ListBucketVersions`
- `s3:DeleteObjectVersion`

If set, the resource name must identify an S3 bucket using one of the following
formats:

- S3 bucket URI (canonical resource name): `s3://{bucket-name}`
- S3 bucket ARN: `arn:aws:s3:::{bucket-name}`
- S3 bucket name: `{bucket-name}`
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Request an S3 bucket to be configured in the
            # connector or provided by the consumer
            supports_instances=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/artifact_store/aws.png",
            emoji=":package:",
        ),
        ResourceTypeModel(
            name="AWS EKS Kubernetes cluster",
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
            description="""
Allows users to access an EKS cluster as a standard Kubernetes cluster
resource. When used by Stack Components, they are provided a
pre-authenticated python-kubernetes client instance.

The configured credentials must have at least the following
[AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html)
associated with the [ARNs of EKS clusters](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html)
that the connector will be allowed to access (e.g.
`arn:aws:eks:{region}:{account}:cluster/*` represents all the EKS clusters
available in the target AWS region).

- `eks:ListClusters`
- `eks:DescribeCluster`

In addition to the above permissions, if the credentials are not associated
with the same IAM user or role that created the EKS cluster, the IAM principal
must be manually added to the EKS cluster's `aws-auth` ConfigMap, otherwise the
Kubernetes client will not be allowed to access the cluster's resources. This
makes it more challenging to use the AWS Implicit and AWS Federation Token
authentication methods for this resource. For more information,
[see this documentation](https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html).

If set, the resource name must identify an EKS cluster using one of the
following formats:

- EKS cluster name (canonical resource name): `{cluster-name}`
- EKS cluster ARN: `arn:aws:eks:{region}:{account}:cluster/{cluster-name}`

EKS cluster names are region scoped. The connector can only be used to access
EKS clusters in the AWS region that it is configured to use.
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Request an EKS cluster name to be configured in the
            # connector or provided by the consumer
            supports_instances=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png",
            emoji=":cyclone:",
        ),
        ResourceTypeModel(
            name="AWS ECR container registry",
            resource_type=DOCKER_REGISTRY_RESOURCE_TYPE,
            description="""
Allows users to access one or more ECR repositories as a standard Docker
registry resource. When used by Stack Components, they are provided a
pre-authenticated python-docker client instance.

The configured credentials must have at least the following
[AWS IAM permissions](https://docs.aws.amazon.com/IAM/latest/UserGuide/access_policies.html)
associated with the [ARNs of one or more ECR repositories](https://docs.aws.amazon.com/IAM/latest/UserGuide/reference-arns.html)
that the connector will be allowed to access (e.g.
`arn:aws:ecr:{region}:{account}:repository/*` represents all the ECR
repositories available in the target AWS region).

- `ecr:DescribeRegistry`
- `ecr:DescribeRepositories`
- `ecr:ListRepositories`
- `ecr:BatchGetImage`
- `ecr:DescribeImages`
- `ecr:BatchCheckLayerAvailability`
- `ecr:GetDownloadUrlForLayer`
- `ecr:InitiateLayerUpload`
- `ecr:UploadLayerPart`
- `ecr:CompleteLayerUpload`
- `ecr:PutImage`
- `ecr:GetAuthorizationToken`

This resource type is not scoped to a single ECR repository. Instead,
a connector configured with this resource type will grant access to all the
ECR repositories that the credentials are allowed to access under the configured
AWS region (i.e. all repositories under the Docker registry URL
`https://{account-id}.dkr.ecr.{region}.amazonaws.com`).

The resource name associated with this resource type uniquely identifies an ECR
registry using one of the following formats (the repository name is ignored,
only the registry URL/ARN is used):
            
- ECR repository URI (canonical resource name):
`[https://]{account}.dkr.ecr.{region}.amazonaws.com[/{repository-name}]`
- ECR repository ARN: `arn:aws:ecr:{region}:{account-id}:repository[/{repository-name}]`

ECR repository names are region scoped. The connector can only be used to access
ECR repositories in the AWS region that it is configured to use.
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Does not support instances, given that the connector
            # provides access to all permitted ECR repositories under the
            # same ECR registry in the configured AWS region.
            supports_instances=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png",
            emoji=":whale:",
        ),
    ],
)


class AWSServiceConnector(ServiceConnector):
    """AWS service connector."""

    config: AWSBaseConfig

    _account_id: Optional[str] = None
    _session_cache: Dict[
        Tuple[str, Optional[str], Optional[str]],
        Tuple[boto3.Session, Optional[datetime.datetime]],
    ] = {}

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector type specification.

        Returns:
            The service connector type specification.
        """
        return AWS_SERVICE_CONNECTOR_TYPE_SPEC

    @property
    def account_id(self) -> str:
        """Get the AWS account ID.

        Returns:
            The AWS account ID.

        Raises:
            AuthorizationException: If the AWS account ID could not be
                determined.
        """
        if self._account_id is None:
            logger.debug("Getting account ID from AWS...")
            try:
                session, _ = self.get_boto3_session(self.auth_method)
                sts_client = session.client("sts")
                response = sts_client.get_caller_identity()
            except (ClientError, BotoCoreError) as e:
                raise AuthorizationException(
                    f"Failed to fetch the AWS account ID: {e}"
                ) from e

            self._account_id = response["Account"]

        return self._account_id

    def get_boto3_session(
        self,
        auth_method: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Tuple[boto3.Session, Optional[datetime.datetime]]:
        """Get a boto3 session for the specified resource.

        Args:
            auth_method: The authentication method to use.
            resource_type: The resource type to get a boto3 session for.
            resource_id: The resource ID to get a boto3 session for.

        Returns:
            A boto3 session for the specified resource and its expiration
            timestamp, if applicable.
        """
        # We maintain a cache of all sessions to avoid re-authenticating
        # multiple times for the same resource
        key = (auth_method, resource_type, resource_id)
        if key in self._session_cache:
            session, expires_at = self._session_cache[key]
            if expires_at is None:
                return session, None

            # Refresh expired sessions
            now = utc_now_tz_aware()
            expires_at = expires_at.replace(tzinfo=datetime.timezone.utc)
            # check if the token expires in the near future
            if expires_at > now + datetime.timedelta(
                minutes=BOTO3_SESSION_EXPIRATION_BUFFER
            ):
                return session, expires_at

        logger.debug(
            f"Creating boto3 session for auth method '{auth_method}', "
            f"resource type '{resource_type}' and resource ID "
            f"'{resource_id}'..."
        )
        session, expires_at = self._authenticate(
            auth_method, resource_type, resource_id
        )
        self._session_cache[key] = (session, expires_at)
        return session, expires_at

    def get_ecr_client(self) -> BaseClient:
        """Get an ECR client.

        Raises:
            ValueError: If the service connector is not able to instantiate an
                ECR client.

        Returns:
            An ECR client.
        """
        if self.resource_type and self.resource_type not in {
            AWS_RESOURCE_TYPE,
            DOCKER_REGISTRY_RESOURCE_TYPE,
        }:
            raise ValueError(
                f"Unable to instantiate ECR client for a connector that is "
                f"configured to provide access to a '{self.resource_type}' "
                "resource type."
            )

        session, _ = self.get_boto3_session(
            auth_method=self.auth_method,
            resource_type=DOCKER_REGISTRY_RESOURCE_TYPE,
            resource_id=self.config.region,
        )
        return session.client(
            "ecr",
            region_name=self.config.region,
            endpoint_url=self.config.endpoint_url,
        )

    def _get_iam_policy(
        self,
        region_id: str,
        resource_type: Optional[str],
        resource_id: Optional[str] = None,
    ) -> Optional[str]:
        """Get the IAM inline policy to use for the specified resource.

        Args:
            region_id: The AWS region ID to get the IAM inline policy for.
            resource_type: The resource type to get the IAM inline policy for.
            resource_id: The resource ID to get the IAM inline policy for.

        Returns:
            The IAM inline policy to use for the specified resource.
        """
        if resource_type == S3_RESOURCE_TYPE:
            if resource_id:
                bucket = self._parse_s3_resource_id(resource_id)
                resource = [
                    f"arn:aws:s3:::{bucket}",
                    f"arn:aws:s3:::{bucket}/*",
                ]
            else:
                resource = ["arn:aws:s3:::*", "arn:aws:s3:::*/*"]
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowS3BucketAccess",
                        "Effect": "Allow",
                        "Action": [
                            "s3:ListBucket",
                            "s3:GetObject",
                            "s3:PutObject",
                            "s3:DeleteObject",
                            "s3:ListAllMyBuckets",
                            "s3:GetBucketVersioning",
                            "s3:ListBucketVersions",
                            "s3:DeleteObjectVersion",
                        ],
                        "Resource": resource,
                    },
                ],
            }
            return json.dumps(policy)
        elif resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            if resource_id:
                cluster_name = self._parse_eks_resource_id(resource_id)
                resource = [
                    f"arn:aws:eks:{region_id}:*:cluster/{cluster_name}",
                ]
            else:
                resource = [f"arn:aws:eks:{region_id}:*:cluster/*"]
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowEKSClusterAccess",
                        "Effect": "Allow",
                        "Action": [
                            "eks:ListClusters",
                            "eks:DescribeCluster",
                        ],
                        "Resource": resource,
                    },
                ],
            }
            return json.dumps(policy)
        elif resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            resource = [
                f"arn:aws:ecr:{region_id}:*:repository/*",
                f"arn:aws:ecr:{region_id}:*:repository",
            ]
            policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "AllowECRRepositoryAccess",
                        "Effect": "Allow",
                        "Action": [
                            "ecr:DescribeRegistry",
                            "ecr:DescribeRepositories",
                            "ecr:ListRepositories",
                            "ecr:BatchGetImage",
                            "ecr:DescribeImages",
                            "ecr:BatchCheckLayerAvailability",
                            "ecr:GetDownloadUrlForLayer",
                            "ecr:InitiateLayerUpload",
                            "ecr:UploadLayerPart",
                            "ecr:CompleteLayerUpload",
                            "ecr:PutImage",
                        ],
                        "Resource": resource,
                    },
                    {
                        "Sid": "AllowECRRepositoryGetToken",
                        "Effect": "Allow",
                        "Action": [
                            "ecr:GetAuthorizationToken",
                        ],
                        "Resource": ["*"],
                    },
                ],
            }
            return json.dumps(policy)

        return None

    def _authenticate(
        self,
        auth_method: str,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> Tuple[boto3.Session, Optional[datetime.datetime]]:
        """Authenticate to AWS and return a boto3 session.

        Args:
            auth_method: The authentication method to use.
            resource_type: The resource type to authenticate for.
            resource_id: The resource ID to authenticate for.

        Returns:
            An authenticated boto3 session and the expiration time of the
            temporary credentials if applicable.

        Raises:
            AuthorizationException: If the IAM role authentication method is
                used and the role cannot be assumed.
            NotImplementedError: If the authentication method is not supported.
        """
        cfg = self.config
        policy_kwargs: Dict[str, Any] = {}

        if auth_method == AWSAuthenticationMethods.IMPLICIT:
            self._check_implicit_auth_method_allowed()

            assert isinstance(cfg, AWSImplicitConfig)
            # Create a boto3 session and use the default credentials provider
            session = boto3.Session(
                profile_name=cfg.profile_name, region_name=cfg.region
            )

            if cfg.role_arn:
                # If an IAM role is configured, assume it
                policy = cfg.policy
                if not cfg.policy and not cfg.policy_arns:
                    policy = self._get_iam_policy(
                        region_id=cfg.region,
                        resource_type=resource_type,
                        resource_id=resource_id,
                    )
                if policy:
                    policy_kwargs["Policy"] = policy
                elif cfg.policy_arns:
                    policy_kwargs["PolicyArns"] = cfg.policy_arns

                sts = session.client("sts", region_name=cfg.region)
                session_name = "zenml-connector"
                if self.id:
                    session_name += f"-{self.id}"

                try:
                    response = sts.assume_role(
                        RoleArn=cfg.role_arn,
                        RoleSessionName=session_name,
                        DurationSeconds=self.expiration_seconds,
                        **policy_kwargs,
                    )
                except (ClientError, BotoCoreError) as e:
                    raise AuthorizationException(
                        f"Failed to assume IAM role {cfg.role_arn} "
                        f"using the implicit AWS credentials: {e}"
                    ) from e

                session = boto3.Session(
                    aws_access_key_id=response["Credentials"]["AccessKeyId"],
                    aws_secret_access_key=response["Credentials"][
                        "SecretAccessKey"
                    ],
                    aws_session_token=response["Credentials"]["SessionToken"],
                )
                expiration = response["Credentials"]["Expiration"]
                # Add the UTC timezone to the expiration time
                expiration = expiration.replace(tzinfo=datetime.timezone.utc)
                return session, expiration

            credentials = session.get_credentials()
            if not credentials:
                raise AuthorizationException(
                    "Failed to get AWS credentials from the default provider. "
                    "Please check your AWS configuration or attached IAM role."
                )
            if credentials.token:
                # Temporary credentials were generated. It's not possible to
                # determine the expiration time of the temporary credentials
                # from the boto3 session, so we assume the default IAM role
                # expiration date is used
                expiration_time = utc_now_tz_aware() + datetime.timedelta(
                    seconds=DEFAULT_IAM_ROLE_TOKEN_EXPIRATION
                )
                return session, expiration_time

            return session, None
        elif auth_method == AWSAuthenticationMethods.SECRET_KEY:
            assert isinstance(cfg, AWSSecretKeyConfig)
            # Create a boto3 session using long-term AWS credentials
            session = boto3.Session(
                aws_access_key_id=cfg.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=cfg.aws_secret_access_key.get_secret_value(),
                region_name=cfg.region,
            )
            return session, None
        elif auth_method == AWSAuthenticationMethods.STS_TOKEN:
            assert isinstance(cfg, STSTokenConfig)
            # Create a boto3 session using a temporary AWS STS token
            session = boto3.Session(
                aws_access_key_id=cfg.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=cfg.aws_secret_access_key.get_secret_value(),
                aws_session_token=cfg.aws_session_token.get_secret_value(),
                region_name=cfg.region,
            )
            return session, self.expires_at
        elif auth_method in [
            AWSAuthenticationMethods.IAM_ROLE,
            AWSAuthenticationMethods.SESSION_TOKEN,
            AWSAuthenticationMethods.FEDERATION_TOKEN,
        ]:
            assert isinstance(cfg, AWSSecretKey)

            # Create a boto3 session
            session = boto3.Session(
                aws_access_key_id=cfg.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=cfg.aws_secret_access_key.get_secret_value(),
                region_name=cfg.region,
            )

            sts = session.client("sts", region_name=cfg.region)
            session_name = "zenml-connector"
            if self.id:
                session_name += f"-{self.id}"

            # Next steps are different for each authentication method

            # The IAM role and federation token authentication methods
            # accept a managed IAM policy that restricts/grants permissions.
            # If one isn't explicitly configured, we generate one based on the
            # resource specified by the resource type and ID (if present).
            if auth_method in [
                AWSAuthenticationMethods.IAM_ROLE,
                AWSAuthenticationMethods.FEDERATION_TOKEN,
            ]:
                assert isinstance(cfg, AWSSessionPolicy)
                policy = cfg.policy
                if not cfg.policy and not cfg.policy_arns:
                    policy = self._get_iam_policy(
                        region_id=cfg.region,
                        resource_type=resource_type,
                        resource_id=resource_id,
                    )
                if policy:
                    policy_kwargs["Policy"] = policy
                elif cfg.policy_arns:
                    policy_kwargs["PolicyArns"] = cfg.policy_arns

                if auth_method == AWSAuthenticationMethods.IAM_ROLE:
                    assert isinstance(cfg, IAMRoleAuthenticationConfig)

                    try:
                        response = sts.assume_role(
                            RoleArn=cfg.role_arn,
                            RoleSessionName=session_name,
                            DurationSeconds=self.expiration_seconds,
                            **policy_kwargs,
                        )
                    except (ClientError, BotoCoreError) as e:
                        raise AuthorizationException(
                            f"Failed to assume IAM role {cfg.role_arn} "
                            f"using the AWS credentials configured in the "
                            f"connector: {e}"
                        ) from e

                else:
                    assert isinstance(cfg, FederationTokenAuthenticationConfig)

                    try:
                        response = sts.get_federation_token(
                            Name=session_name[:32],
                            DurationSeconds=self.expiration_seconds,
                            **policy_kwargs,
                        )
                    except (ClientError, BotoCoreError) as e:
                        raise AuthorizationException(
                            "Failed to get federation token "
                            "using the AWS credentials configured in the "
                            f"connector: {e}"
                        ) from e

            else:
                assert isinstance(cfg, SessionTokenAuthenticationConfig)
                try:
                    response = sts.get_session_token(
                        DurationSeconds=self.expiration_seconds,
                    )
                except (ClientError, BotoCoreError) as e:
                    raise AuthorizationException(
                        "Failed to get session token "
                        "using the AWS credentials configured in the "
                        f"connector: {e}"
                    ) from e

            session = boto3.Session(
                aws_access_key_id=response["Credentials"]["AccessKeyId"],
                aws_secret_access_key=response["Credentials"][
                    "SecretAccessKey"
                ],
                aws_session_token=response["Credentials"]["SessionToken"],
            )
            expiration = response["Credentials"]["Expiration"]
            # Add the UTC timezone to the expiration time
            expiration = expiration.replace(tzinfo=datetime.timezone.utc)
            return session, expiration

        raise NotImplementedError(
            f"Authentication method '{auth_method}' is not supported by "
            "the AWS connector."
        )

    @classmethod
    def _get_eks_bearer_token(
        cls,
        session: boto3.Session,
        cluster_id: str,
        region: str,
    ) -> str:
        """Generate a bearer token for authenticating to the EKS API server.

        Based on: https://github.com/kubernetes-sigs/aws-iam-authenticator/blob/master/README.md#api-authorization-from-outside-a-cluster

        Args:
            session: An authenticated boto3 session to use for generating the
                token.
            cluster_id: The name of the EKS cluster.
            region: The AWS region the EKS cluster is in.

        Returns:
            A bearer token for authenticating to the EKS API server.
        """
        STS_TOKEN_EXPIRES_IN = 60

        client = session.client("sts", region_name=region)
        service_id = client.meta.service_model.service_id

        signer = RequestSigner(
            service_id,
            region,
            "sts",
            "v4",
            session.get_credentials(),
            session.events,
        )

        params = {
            "method": "GET",
            "url": f"https://sts.{region}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15",
            "body": {},
            "headers": {"x-k8s-aws-id": cluster_id},
            "context": {},
        }

        signed_url = signer.generate_presigned_url(
            params,
            region_name=region,
            expires_in=STS_TOKEN_EXPIRES_IN,
            operation_name="",
        )

        base64_url = base64.urlsafe_b64encode(
            signed_url.encode("utf-8")
        ).decode("utf-8")

        # remove any base64 encoding padding:
        return "k8s-aws-v1." + re.sub(r"=*", "", base64_url)

    def _parse_s3_resource_id(self, resource_id: str) -> str:
        """Validate and convert an S3 resource ID to an S3 bucket name.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The S3 bucket name.

        Raises:
            ValueError: If the provided resource ID is not a valid S3 bucket
                name, ARN or URI.
        """
        # The resource ID could mean different things:
        #
        # - an S3 bucket ARN
        # - an S3 bucket URI
        # - the S3 bucket name
        #
        # We need to extract the bucket name from the provided resource ID
        bucket_name: Optional[str] = None
        if re.match(
            r"^arn:aws:s3:::[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9](/.*)*$",
            resource_id,
        ):
            # The resource ID is an S3 bucket ARN
            bucket_name = resource_id.split(":")[-1].split("/")[0]
        elif re.match(
            r"^s3://[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9](/.*)*$",
            resource_id,
        ):
            # The resource ID is an S3 bucket URI
            bucket_name = resource_id.split("/")[2]
        elif re.match(
            r"^[a-z0-9][a-z0-9\-\.]{1,61}[a-z0-9]$",
            resource_id,
        ):
            # The resource ID is the S3 bucket name
            bucket_name = resource_id
        else:
            raise ValueError(
                f"Invalid resource ID for an S3 bucket: {resource_id}. "
                f"Supported formats are:\n"
                f"S3 bucket ARN: arn:aws:s3:::<bucket-name>\n"
                f"S3 bucket URI: s3://<bucket-name>\n"
                f"S3 bucket name: <bucket-name>"
            )

        return bucket_name

    def _parse_ecr_resource_id(
        self,
        resource_id: str,
    ) -> str:
        """Validate and convert an ECR resource ID to an ECR registry ID.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The ECR registry ID (AWS account ID).

        Raises:
            ValueError: If the provided resource ID is not a valid ECR
                repository ARN or URI.
        """
        # The resource ID could mean different things:
        #
        # - an ECR repository ARN
        # - an ECR repository URI
        #
        # We need to extract the region ID and registry ID from
        # the provided resource ID
        config_region_id = self.config.region
        region_id: Optional[str] = None
        if re.match(
            r"^arn:aws:ecr:[a-z0-9-]+:\d{12}:repository(/.+)*$",
            resource_id,
        ):
            # The resource ID is an ECR repository ARN
            registry_id = resource_id.split(":")[4]
            region_id = resource_id.split(":")[3]
        elif re.match(
            r"^(http[s]?://)?\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com(/.+)*$",
            resource_id,
        ):
            # The resource ID is an ECR repository URI
            registry_id = resource_id.split(".")[0].split("/")[-1]
            region_id = resource_id.split(".")[3]
        else:
            raise ValueError(
                f"Invalid resource ID for a ECR registry: {resource_id}. "
                f"Supported formats are:\n"
                f"ECR repository ARN: arn:aws:ecr:<region>:<account-id>:repository[/<repository-name>]\n"
                f"ECR repository URI: [https://]<account-id>.dkr.ecr.<region>.amazonaws.com[/<repository-name>]"
            )

        # If the connector is configured with a region and the resource ID
        # is an ECR repository ARN or URI that specifies a different region
        # we raise an error
        if region_id and region_id != config_region_id:
            raise ValueError(
                f"The AWS region for the {resource_id} ECR repository region "
                f"'{region_id}' does not match the region configured in "
                f"the connector: '{config_region_id}'."
            )

        return registry_id

    def _parse_eks_resource_id(self, resource_id: str) -> str:
        """Validate and convert an EKS resource ID to an AWS region and EKS cluster name.

        Args:
            resource_id: The resource ID to convert.

        Returns:
            The EKS cluster name.

        Raises:
            ValueError: If the provided resource ID is not a valid EKS cluster
                name or ARN.
        """
        # The resource ID could mean different things:
        #
        # - an EKS cluster ARN
        # - an EKS cluster ID
        #
        # We need to extract the cluster name and region ID from the
        # provided resource ID
        config_region_id = self.config.region
        cluster_name: Optional[str] = None
        region_id: Optional[str] = None
        if re.match(
            r"^arn:aws:eks:[a-z0-9-]+:\d{12}:cluster/[0-9A-Za-z][A-Za-z0-9\-_]*$",
            resource_id,
        ):
            # The resource ID is an EKS cluster ARN
            cluster_name = resource_id.split("/")[-1]
            region_id = resource_id.split(":")[3]
        elif re.match(
            r"^[0-9A-Za-z][A-Za-z0-9\-_]*$",
            resource_id,
        ):
            # Assume the resource ID is an EKS cluster name
            cluster_name = resource_id
        else:
            raise ValueError(
                f"Invalid resource ID for a EKS cluster: {resource_id}. "
                f"Supported formats are:\n"
                f"EKS cluster ARN: arn:aws:eks:<region>:<account-id>:cluster/<cluster-name>\n"
                f"ECR cluster name: <cluster-name>"
            )

        # If the connector is configured with a region and the resource ID
        # is an EKS registry ARN or URI that specifies a different region
        # we raise an error
        if region_id and region_id != config_region_id:
            raise ValueError(
                f"The AWS region for the {resource_id} EKS cluster "
                f"({region_id}) does not match the region configured in "
                f"the connector ({config_region_id})."
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
        if resource_type == S3_RESOURCE_TYPE:
            bucket = self._parse_s3_resource_id(resource_id)
            return f"s3://{bucket}"
        elif resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            cluster_name = self._parse_eks_resource_id(resource_id)
            return cluster_name
        elif resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            registry_id = self._parse_ecr_resource_id(
                resource_id,
            )
            return f"{registry_id}.dkr.ecr.{self.config.region}.amazonaws.com"
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
            RuntimeError: If the ECR registry ID (AWS account ID)
                cannot be retrieved from AWS because the connector is not
                authorized.
        """
        if resource_type == AWS_RESOURCE_TYPE:
            return self.config.region
        elif resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            # we need to get the account ID (same as registry ID) from the
            # caller identity AWS service
            account_id = self.account_id

            return f"{account_id}.dkr.ecr.{self.config.region}.amazonaws.com"

        raise RuntimeError(
            f"Default resource ID for '{resource_type}' not available."
        )

    def _connect_to_resource(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to an AWS resource.

        Initialize and return a session or client object depending on the
        connector configuration:

        - initialize and return a boto3 session if the resource type
        is a generic AWS resource
        - initialize and return a boto3 client for an S3 resource type

        For the Docker and Kubernetes resource types, the connector does not
        support connecting to the resource directly. Instead, the connector
        supports generating a connector client object for the resource type
        in question.

        Args:
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            A boto3 session for AWS generic resources and a boto3 S3 client for
            S3 resources.

        Raises:
            NotImplementedError: If the connector instance does not support
                directly connecting to the indicated resource type.
        """
        resource_type = self.resource_type
        resource_id = self.resource_id

        assert resource_type is not None
        assert resource_id is not None

        # Regardless of the resource type, we must authenticate to AWS first
        # before we can connect to any AWS resource
        session, _ = self.get_boto3_session(
            self.auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if resource_type == S3_RESOURCE_TYPE:
            # Validate that the resource ID is a valid S3 bucket name
            self._parse_s3_resource_id(resource_id)

            # Create an S3 client for the bucket
            client = session.client(
                "s3",
                region_name=self.config.region,
                endpoint_url=self.config.endpoint_url,
            )

            # There is no way to retrieve the credentials from the S3 client
            # but some consumers need them to configure 3rd party services.
            # We therefore store the credentials in the client object so that
            # they can be retrieved later.
            client.credentials = session.get_credentials()
            return client

        if resource_type == AWS_RESOURCE_TYPE:
            return session

        raise NotImplementedError(
            f"Connecting to {resource_type} resources is not directly "
            "supported by the AWS connector. Please call the "
            f"`get_connector_client` method to get a {resource_type} connector "
            "instance for the resource."
        )

    def _configure_local_client(
        self,
        profile_name: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Configure a local client to authenticate and connect to a resource.

        This method uses the connector's configuration to configure a local
        client or SDK installed on the localhost for the indicated resource.

        Args:
            profile_name: The name of the AWS profile to use. If not specified,
                a profile name is generated based on the first 8 digits of the
                connector's UUID in the form 'zenml-<uuid[:8]>'. If a profile
                with the given or generated name already exists, the profile is
                overwritten.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            NotImplementedError: If the connector instance does not support
                local configuration for the configured resource type or
                authentication method.registry
        """
        resource_type = self.resource_type

        if resource_type in [AWS_RESOURCE_TYPE, S3_RESOURCE_TYPE]:
            session, _ = self.get_boto3_session(
                self.auth_method,
                resource_type=resource_type,
                resource_id=self.resource_id,
            )

            # Configure a new AWS SDK profile with the credentials
            # from the session using the aws-profile-manager package

            # Generate a profile name based on the first 8 digits from the
            # connector UUID, if one is not supplied
            aws_profile_name = profile_name or f"zenml-{str(self.id)[:8]}"
            common = Common()
            users_home = common.get_users_home()
            all_profiles = common.get_all_profiles(users_home)

            credentials = session.get_credentials()
            all_profiles[aws_profile_name] = {
                "region": self.config.region,
                "aws_access_key_id": credentials.access_key,
                "aws_secret_access_key": credentials.secret_key,
            }

            if credentials.token:
                all_profiles[aws_profile_name]["aws_session_token"] = (
                    credentials.token
                )

            aws_credentials_path = os.path.join(
                users_home, ".aws", "credentials"
            )

            # Create the file as well as the parent dir if needed.
            dirname = os.path.split(aws_credentials_path)[0]
            if not os.path.isdir(dirname):
                os.makedirs(dirname)
            with os.fdopen(
                os.open(aws_credentials_path, os.O_WRONLY | os.O_CREAT, 0o600),
                "w",
            ):
                pass

            # Write the credentials to the file
            common.rewrite_credentials_file(all_profiles, users_home)

            logger.info(
                f"Configured local AWS SDK profile '{aws_profile_name}'."
            )

            return

        raise NotImplementedError(
            f"Configuring the local client for {resource_type} resources is "
            "not directly supported by the AWS connector. Please call the "
            f"`get_connector_client` method to get a {resource_type} connector "
            "instance for the resource."
        )

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        role_arn: Optional[str] = None,
        **kwargs: Any,
    ) -> "AWSServiceConnector":
        """Auto-configure the connector.

        Instantiate an AWS connector with a configuration extracted from the
        authentication configuration available in the environment (e.g.
        environment variables or local AWS client/SDK configuration files).

        Args:
            auth_method: The particular authentication method to use. If not
                specified, the connector implementation must decide which
                authentication method to use or raise an exception.
            resource_type: The type of resource to configure.
            resource_id: The ID of the resource to configure. The
                implementation may choose to either require or ignore this
                parameter if it does not support or detect an resource type that
                supports multiple instances.
            region_name: The name of the AWS region to use. If not specified,
                the implicit region is used.
            profile_name: The name of the AWS profile to use. If not specified,
                the implicit profile is used.
            role_arn: The ARN of the AWS role to assume. Applicable only if the
                IAM role authentication method is specified or long-term
                credentials are discovered.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            An AWS connector instance configured with authentication credentials
            automatically extracted from the environment.

        Raises:
            NotImplementedError: If the connector implementation does not
                support auto-configuration for the specified authentication
                method.
            ValueError: If the supplied arguments are not valid.
            AuthorizationException: If no AWS credentials can be loaded from
                the environment.
        """
        auth_config: AWSBaseConfig
        expiration_seconds: Optional[int] = None
        expires_at: Optional[datetime.datetime] = None
        if auth_method == AWSAuthenticationMethods.IMPLICIT:
            if region_name is None:
                raise ValueError(
                    "The AWS region name must be specified when using the "
                    "implicit authentication method"
                )
            auth_config = AWSImplicitConfig(
                profile_name=profile_name,
                region=region_name,
            )
        else:
            # Initialize an AWS session with the default configuration loaded
            # from the environment.
            session = boto3.Session(
                profile_name=profile_name, region_name=region_name
            )

            region_name = region_name or session.region_name
            if not region_name:
                raise ValueError(
                    "The AWS region name was not specified and could not "
                    "be determined from the AWS session"
                )
            endpoint_url = session._session.get_config_variable("endpoint_url")

            # Extract the AWS credentials from the session and store them in
            # the connector secrets.
            credentials = session.get_credentials()
            if not credentials:
                raise AuthorizationException(
                    "Could not determine the AWS credentials from the "
                    "environment"
                )
            if credentials.token:
                # The session picked up temporary STS credentials
                if auth_method and auth_method not in [
                    None,
                    AWSAuthenticationMethods.STS_TOKEN,
                    AWSAuthenticationMethods.IAM_ROLE,
                ]:
                    raise NotImplementedError(
                        f"The specified authentication method '{auth_method}' "
                        "could not be used to auto-configure the connector. "
                    )

                if (
                    credentials.method == "assume-role"
                    and auth_method != AWSAuthenticationMethods.STS_TOKEN
                ):
                    # In the special case of IAM role authentication, the
                    # credentials in the boto3 session are the temporary STS
                    # credentials instead of the long-lived credentials, and the
                    # role ARN is not known. We have to dig deeper into the
                    # botocore session internals to retrieve the role ARN and
                    # the original long-lived credentials.

                    botocore_session = session._session
                    profile_config = botocore_session.get_scoped_config()
                    source_profile = profile_config.get("source_profile")
                    role_arn = profile_config.get("role_arn")
                    profile_map = botocore_session._build_profile_map()
                    if not (
                        role_arn
                        and source_profile
                        and source_profile in profile_map
                    ):
                        raise AuthorizationException(
                            "Could not determine the IAM role ARN and source "
                            "profile credentials from the environment"
                        )

                    auth_method = AWSAuthenticationMethods.IAM_ROLE
                    source_profile_config = profile_map[source_profile]
                    auth_config = IAMRoleAuthenticationConfig(
                        region=region_name,
                        endpoint_url=endpoint_url,
                        aws_access_key_id=source_profile_config.get(
                            "aws_access_key_id"
                        ),
                        aws_secret_access_key=source_profile_config.get(
                            "aws_secret_access_key",
                        ),
                        role_arn=role_arn,
                    )
                    expiration_seconds = DEFAULT_IAM_ROLE_TOKEN_EXPIRATION

                else:
                    if auth_method == AWSAuthenticationMethods.IAM_ROLE:
                        raise NotImplementedError(
                            f"The specified authentication method "
                            f"'{auth_method}' could not be used to "
                            "auto-configure the connector."
                        )

                    # Temporary credentials were picked up from the local
                    # configuration. It's not possible to determine the
                    # expiration time of the temporary credentials from the
                    # boto3 session, so we assume the default IAM role
                    # expiration period is used
                    expires_at = utc_now_tz_aware() + datetime.timedelta(
                        seconds=DEFAULT_IAM_ROLE_TOKEN_EXPIRATION
                    )

                    auth_method = AWSAuthenticationMethods.STS_TOKEN
                    auth_config = STSTokenConfig(
                        region=region_name,
                        endpoint_url=endpoint_url,
                        aws_access_key_id=credentials.access_key,
                        aws_secret_access_key=credentials.secret_key,
                        aws_session_token=credentials.token,
                    )
            else:
                # The session picked up long-lived credentials
                if not auth_method:
                    if role_arn:
                        auth_method = AWSAuthenticationMethods.IAM_ROLE
                    else:
                        # If no authentication method was specified, use the
                        # session token as a default recommended authentication
                        # method to be used with long-lived credentials.
                        auth_method = AWSAuthenticationMethods.SESSION_TOKEN

                region_name = region_name or session.region_name
                if not region_name:
                    raise ValueError(
                        "The AWS region name was not specified and could not "
                        "be determined from the AWS session"
                    )

                if auth_method == AWSAuthenticationMethods.STS_TOKEN:
                    # Generate a session token from the long-lived credentials
                    # and store it in the connector secrets.
                    sts_client = session.client("sts")
                    response = sts_client.get_session_token(
                        DurationSeconds=DEFAULT_STS_TOKEN_EXPIRATION
                    )
                    credentials = response["Credentials"]
                    auth_config = STSTokenConfig(
                        region=region_name,
                        endpoint_url=endpoint_url,
                        aws_access_key_id=credentials["AccessKeyId"],
                        aws_secret_access_key=credentials["SecretAccessKey"],
                        aws_session_token=credentials["SessionToken"],
                    )
                    expires_at = utc_now_tz_aware() + datetime.timedelta(
                        seconds=DEFAULT_STS_TOKEN_EXPIRATION
                    )

                elif auth_method == AWSAuthenticationMethods.IAM_ROLE:
                    if not role_arn:
                        raise ValueError(
                            "The ARN of the AWS role to assume must be "
                            "specified when using the IAM role authentication "
                            "method."
                        )
                    auth_config = IAMRoleAuthenticationConfig(
                        region=region_name,
                        endpoint_url=endpoint_url,
                        aws_access_key_id=credentials.access_key,
                        aws_secret_access_key=credentials.secret_key,
                        role_arn=role_arn,
                    )
                    expiration_seconds = DEFAULT_IAM_ROLE_TOKEN_EXPIRATION

                elif auth_method == AWSAuthenticationMethods.SECRET_KEY:
                    auth_config = AWSSecretKeyConfig(
                        region=region_name,
                        endpoint_url=endpoint_url,
                        aws_access_key_id=credentials.access_key,
                        aws_secret_access_key=credentials.secret_key,
                    )

                elif auth_method == AWSAuthenticationMethods.SESSION_TOKEN:
                    auth_config = SessionTokenAuthenticationConfig(
                        region=region_name,
                        endpoint_url=endpoint_url,
                        aws_access_key_id=credentials.access_key,
                        aws_secret_access_key=credentials.secret_key,
                    )
                    expiration_seconds = DEFAULT_STS_TOKEN_EXPIRATION

                else:  # auth_method is AWSAuthenticationMethods.FEDERATION_TOKEN
                    auth_config = FederationTokenAuthenticationConfig(
                        region=region_name,
                        endpoint_url=endpoint_url,
                        aws_access_key_id=credentials.access_key,
                        aws_secret_access_key=credentials.secret_key,
                    )
                    expiration_seconds = DEFAULT_STS_TOKEN_EXPIRATION

        return cls(
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id
            if resource_type not in [AWS_RESOURCE_TYPE, None]
            else None,
            expiration_seconds=expiration_seconds,
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
        # same as a generic AWS connector.
        session, _ = self.get_boto3_session(
            self.auth_method,
            resource_type=resource_type or AWS_RESOURCE_TYPE,
            resource_id=resource_id,
        )

        # Verify that the AWS account is accessible
        assert isinstance(session, boto3.Session)
        sts_client = session.client("sts")
        try:
            sts_client.get_caller_identity()
        except (ClientError, BotoCoreError) as err:
            msg = f"failed to verify AWS account access: {err}"
            logger.debug(msg)
            raise AuthorizationException(msg) from err

        if not resource_type:
            return []

        if resource_type == AWS_RESOURCE_TYPE:
            assert resource_id is not None
            return [resource_id]

        if resource_type == S3_RESOURCE_TYPE:
            s3_client = session.client(
                "s3",
                region_name=self.config.region,
                endpoint_url=self.config.endpoint_url,
            )
            if not resource_id:
                # List all S3 buckets
                try:
                    response = s3_client.list_buckets()
                except (ClientError, BotoCoreError) as e:
                    msg = f"failed to list S3 buckets: {e}"
                    logger.error(msg)
                    raise AuthorizationException(msg) from e

                return [
                    f"s3://{bucket['Name']}" for bucket in response["Buckets"]
                ]
            else:
                # Check if the specified S3 bucket exists
                bucket_name = self._parse_s3_resource_id(resource_id)
                try:
                    s3_client.head_bucket(Bucket=bucket_name)
                    return [resource_id]
                except (ClientError, BotoCoreError) as e:
                    msg = f"failed to fetch S3 bucket {bucket_name}: {e}"
                    logger.error(msg)
                    raise AuthorizationException(msg) from e

        if resource_type == DOCKER_REGISTRY_RESOURCE_TYPE:
            assert resource_id is not None

            ecr_client = session.client(
                "ecr",
                region_name=self.config.region,
                endpoint_url=self.config.endpoint_url,
            )
            # List all ECR repositories
            try:
                repositories = ecr_client.describe_repositories()
            except (ClientError, BotoCoreError) as e:
                msg = f"failed to list ECR repositories: {e}"
                logger.error(msg)
                raise AuthorizationException(msg) from e

            if len(repositories["repositories"]) == 0:
                raise AuthorizationException(
                    "the AWS connector does not have access to any ECR "
                    "repositories. Please adjust the AWS permissions "
                    "associated with the authentication credentials to "
                    "include access to at least one ECR repository."
                )

            return [resource_id]

        if resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            eks_client = session.client(
                "eks",
                region_name=self.config.region,
                endpoint_url=self.config.endpoint_url,
            )
            if not resource_id:
                # List all EKS clusters
                try:
                    clusters = eks_client.list_clusters()
                except (ClientError, BotoCoreError) as e:
                    msg = f"Failed to list EKS clusters: {e}"
                    logger.error(msg)
                    raise AuthorizationException(msg) from e

                return cast(List[str], clusters["clusters"])
            else:
                # Check if the specified EKS cluster exists
                cluster_name = self._parse_eks_resource_id(resource_id)
                try:
                    clusters = eks_client.describe_cluster(name=cluster_name)
                except (ClientError, BotoCoreError) as e:
                    msg = f"Failed to fetch EKS cluster {cluster_name}: {e}"
                    logger.error(msg)
                    raise AuthorizationException(msg) from e

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
        is configured with temporary AWS credentials extracted from the
        current connector and, depending on resource type, it may also be
        of a different connector type:

        - a Kubernetes connector for Kubernetes clusters
        - a Docker connector for Docker registries

        Args:
            resource_type: The type of the resources to connect to.
            resource_id: The ID of a particular resource to connect to.

        Returns:
            An AWS, Kubernetes or Docker connector instance that can be used to
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

        if resource_type in [AWS_RESOURCE_TYPE, S3_RESOURCE_TYPE]:
            auth_method = self.auth_method
            if self.auth_method in [
                AWSAuthenticationMethods.SECRET_KEY,
                AWSAuthenticationMethods.STS_TOKEN,
            ]:
                if (
                    self.resource_type == resource_type
                    and self.resource_id == resource_id
                ):
                    # If the requested type and resource ID are the same as
                    # those configured, we can return the current connector
                    # instance because it's fully formed and ready to use
                    # to connect to the specified resource
                    return self

                # The secret key and STS token authentication methods do not
                # involve generating temporary credentials, so we can just
                # use the current connector configuration
                config = self.config
                expires_at = self.expires_at
            else:
                # Get an authenticated boto3 session
                session, expires_at = self.get_boto3_session(
                    self.auth_method,
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                assert isinstance(session, boto3.Session)
                credentials = session.get_credentials()

                if (
                    self.auth_method == AWSAuthenticationMethods.IMPLICIT
                    and credentials.token is None
                ):
                    # The implicit authentication method may involve picking up
                    # long-lived credentials from the environment
                    auth_method = AWSAuthenticationMethods.SECRET_KEY
                    config = AWSSecretKeyConfig(
                        region=self.config.region,
                        endpoint_url=self.config.endpoint_url,
                        aws_access_key_id=credentials.access_key,
                        aws_secret_access_key=credentials.secret_key,
                    )
                else:
                    assert credentials.token is not None

                    # Use the temporary credentials extracted from the boto3
                    # session
                    auth_method = AWSAuthenticationMethods.STS_TOKEN
                    config = STSTokenConfig(
                        region=self.config.region,
                        endpoint_url=self.config.endpoint_url,
                        aws_access_key_id=credentials.access_key,
                        aws_secret_access_key=credentials.secret_key,
                        aws_session_token=credentials.token,
                    )

            # Create a client-side AWS connector instance that is fully formed
            # and ready to use to connect to the specified resource (i.e. has
            # all the necessary configuration and credentials, a resource type
            # and a resource ID where applicable)
            return AWSServiceConnector(
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

            # Get an authenticated boto3 session
            session, expires_at = self.get_boto3_session(
                self.auth_method,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            assert isinstance(session, boto3.Session)

            registry_id = self._parse_ecr_resource_id(resource_id)

            ecr_client = session.client(
                "ecr",
                region_name=self.config.region,
                endpoint_url=self.config.endpoint_url,
            )

            assert isinstance(ecr_client, BaseClient)
            assert registry_id is not None

            try:
                auth_token = ecr_client.get_authorization_token(
                    registryIds=[
                        registry_id,
                    ]
                )
            except (ClientError, BotoCoreError) as e:
                raise AuthorizationException(
                    f"Failed to get authorization token from ECR: {e}"
                ) from e

            token = auth_token["authorizationData"][0]["authorizationToken"]
            endpoint = auth_token["authorizationData"][0]["proxyEndpoint"]
            # The token is base64 encoded and has the format
            # "username:password"
            username, token = (
                base64.b64decode(token).decode("utf-8").split(":")
            )

            # Create a client-side Docker connector instance with the temporary
            # Docker credentials
            return DockerServiceConnector(
                id=self.id,
                name=connector_name,
                auth_method=DockerAuthenticationMethods.PASSWORD,
                resource_type=resource_type,
                config=DockerConfiguration(
                    username=username,
                    password=token,
                    registry=endpoint,
                ),
                expires_at=expires_at,
            )

        if resource_type == KUBERNETES_CLUSTER_RESOURCE_TYPE:
            assert resource_id is not None

            # Get an authenticated boto3 session
            session, _ = self.get_boto3_session(
                self.auth_method,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            assert isinstance(session, boto3.Session)

            cluster_name = self._parse_eks_resource_id(resource_id)

            # Get a boto3 EKS client
            eks_client = session.client(
                "eks",
                region_name=self.config.region,
                endpoint_url=self.config.endpoint_url,
            )

            assert isinstance(eks_client, BaseClient)

            try:
                cluster = eks_client.describe_cluster(name=cluster_name)
            except (ClientError, BotoCoreError) as e:
                raise AuthorizationException(
                    f"Failed to get EKS cluster {cluster_name}: {e}"
                ) from e

            try:
                user_token = self._get_eks_bearer_token(
                    session=session,
                    cluster_id=cluster_name,
                    region=self.config.region,
                )
            except (ClientError, BotoCoreError) as e:
                raise AuthorizationException(
                    f"Failed to get EKS bearer token: {e}"
                ) from e

            # Kubernetes authentication tokens issued by AWS EKS have a fixed
            # expiration time of 15 minutes
            # source: https://aws.github.io/aws-eks-best-practices/security/docs/iam/#controlling-access-to-eks-clusters
            expires_at = utc_now_tz_aware() + datetime.timedelta(
                minutes=EKS_KUBE_API_TOKEN_EXPIRATION
            )

            # get cluster details
            cluster_arn = cluster["cluster"]["arn"]
            cluster_ca_cert = cluster["cluster"]["certificateAuthority"][
                "data"
            ]
            cluster_server = cluster["cluster"]["endpoint"]

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
                    cluster_name=cluster_arn,
                    certificate_authority=cluster_ca_cert,
                    server=cluster_server,
                    token=user_token,
                ),
                expires_at=expires_at,
            )

        raise ValueError(f"Unsupported resource type: {resource_type}")
