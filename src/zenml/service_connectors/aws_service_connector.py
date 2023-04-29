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
import re
from typing import Any, List, Optional, Tuple

import boto3
from botocore.client import BaseClient
from botocore.exceptions import ClientError
from botocore.signers import RequestSigner
from pydantic import Field, SecretStr

from zenml.exceptions import AuthorizationException
from zenml.logger import get_logger
from zenml.models import (
    AuthenticationMethodModel,
    ResourceTypeModel,
    ServiceConnectorTypeModel,
)
from zenml.service_connectors.docker_service_connector import (
    DOCKER_RESOURCE_TYPE,
    DockerAuthenticationMethods,
    DockerCredentials,
    DockerServiceConnector,
)
from zenml.service_connectors.kubernetes_service_connector import (
    KUBERNETES_RESOURCE_TYPE,
    KubernetesAuthenticationMethods,
    KubernetesServiceConnector,
    KubernetesTokenConfig,
)
from zenml.service_connectors.service_connector import (
    AuthenticationConfig,
    ServiceConnector,
)
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)


AWS_CONNECTOR_TYPE = "aws"
AWS_RESOURCE_TYPE = "aws"
S3_RESOURCE_TYPE = "s3"
EKS_KUBE_API_TOKEN_EXPIRATION = 60


class AWSSecretKey(AuthenticationConfig):
    """AWS secret key credentials."""

    aws_access_key_id: SecretStr = Field(
        title="AWS Access Key ID",
    )
    aws_secret_access_key: SecretStr = Field(
        title="AWS Secret Access Key",
    )


class STSToken(AWSSecretKey):
    """AWS STS token."""

    aws_session_token: SecretStr = Field(
        title="AWS Session Token",
    )


class AWSBaseConfig(AWSSecretKey):
    """AWS base configuration."""

    region: str = Field(
        title="AWS Region",
    )
    endpoint_url: Optional[str] = Field(
        default=None,
        title="AWS Endpoint URL",
    )


class AWSSecretKeyConfig(AWSBaseConfig, AWSSecretKey):
    """AWS secret key authentication configuration."""


class STSTokenConfig(AWSBaseConfig, STSToken):
    """AWS STS token authentication configuration."""

    expires: Optional[datetime.datetime] = Field(
        default=None,
        title="AWS STS Token Expiration",
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

    SECRET_KEY = "secret-key"
    STS_TOKEN = "sts-token"
    IAM_ROLE = "iam-role"
    SESSION_TOKEN = "session-token"
    FEDERATION_TOKEN = "federation-token"


AWS_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="AWS Service Connector",
    type=AWS_CONNECTOR_TYPE,
    description="""
This ZenML AWS service connector facilitates connecting to, authenticating to
and accessing managed AWS services, such as S3 buckets, ECR repositories and EKS
clusters. Explicit long-lived AWS credentials are supported, as well as
temporary STS security tokens. The connector also supports auto-configuration
by discovering and using credentials configured on a local environment.

The connector can be used to access to any generic AWS service, such as S3, ECR,
EKS, EC2, etc. by providing pre-authenticated boto3 sessions for these services.
In addition to authenticating to AWS services, the connector is able to manage
specialized authentication for Docker and Kubernetes python clients and also
allows configuration of local Docker and Kubernetes clients.
""",
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/aws.png",
    auth_methods=[
        AuthenticationMethodModel(
            name="AWS Secret Key",
            auth_method=AWSAuthenticationMethods.SECRET_KEY,
            description="""
Long-lived AWS credentials consisting of an access key ID and secret access key
associated with an IAM user or AWS account root user (not recommended). This
method is preferred during development and testing due to its simplicity and
ease of use. It is not recommended as a direct authentication method for
production use cases because the clients are granted the full set of permissions
of the IAM user or AWS account root user associated with the credentials.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.

For production, it is recommended to use the AWS IAM Role, AWS Session Token
or AWS Federation Token authentication method.
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
tokens expire. This method is best used in cases where the connector only needs
to be used for a short period of time.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.
""",
            config_class=STSTokenConfig,
        ),
        AuthenticationMethodModel(
            name="AWS IAM Role",
            auth_method=AWSAuthenticationMethods.IAM_ROLE,
            description="""
Generates temporary STS credentials by assuming an IAM role.
The connector needs to be configured with an IAM role accompanied by an access
key ID and secret access key associated with an IAM user or an STS token
associated with another IAM role. The IAM user or IAM role must have permissions
to assume the IAM role. The connector will then generate new temporary STS
tokens upon request by calling the AssumeRole STS API.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.

One or more optional IAM managed policies may also be configured to further
restrict the permissions of the generated STS tokens. If not specified, the
connector will automatically configure policies according to the resource
type and resource ID that the connector is configured to access.

The default expiration period for generated STS tokens is 1 hour with a
minimum of 15 minutes up to the maximum session duration setting configured for
the IAM role (default is 1 hour). If you need longer-lived tokens, you can
configure the IAM role to use a higher maximum expiration value (up to 12 hours)
or use the AWS Federation Token or AWS Session Token authentication methods.

For more information on IAM roles and the AssumeRole AWS API, see:
https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_assumerole

For more information about the difference between this method and the AWS
Federation Token authentication method, see:
https://aws.amazon.com/blogs/security/understanding-the-api-options-for-securely-delegating-access-to-your-aws-account/

This method might not be suitable for consumers that cannot automatically
re-generate temporary credentials upon expiration (e.g. an external clients or
long-running process).
""",
            min_expiration_seconds=900,  # 15 minutes
            default_expiration_seconds=3600,  # 1 hour
            config_class=IAMRoleAuthenticationConfig,
        ),
        AuthenticationMethodModel(
            name="AWS Session Token",
            auth_method=AWSAuthenticationMethods.SESSION_TOKEN,
            description="""
Generates temporary session STS tokens for IAM users.
The connector needs to be configured with a key ID and secret access key
associated with an IAM user or AWS account root user (not recommended). The
connector will then generate new temporary STS tokens upon request by calling
the GetSessionToken STS API. These STS tokens have an expiration period longer
that those issued through the AWS IAM Role authentication method and are more
suitable for long-running processes that cannot automatically re-generate
credentials upon expiration.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.

The default expiration period for generated STS tokens is 12 hours with a
minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained
by using the AWS account root user credentials (not recommended) have a maximum
duration of 1 hour.

Generated STS tokens inherit the full set of permissions of the IAM user or
AWS account root user that is calling the GetSessionToken. This is not
recommended for production use, as it can lead to accidental privilege
escalation. Instead, it is recommended to use the AWS Federation Token or AWS
IAM Role authentication methods with additional session policies to restrict
the permissions of the generated STS tokens.

For more information on session tokens and the GetSessionToken AWS API, see:
https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_getsessiontoken

This method might not be suitable for consumers that cannot automatically
re-generate temporary credentials upon expiration (e.g. an external clients or
long-running process).
""",
            min_expiration_seconds=900,  # 15 minutes
            max_expiration_seconds=43200,  # 12 hours
            default_expiration_seconds=43200,  # 12 hours
            config_class=SessionTokenAuthenticationConfig,
        ),
        AuthenticationMethodModel(
            name="AWS Federation Token",
            auth_method=AWSAuthenticationMethods.FEDERATION_TOKEN,
            description="""
Generates temporary STS tokens for federated users.
The connector needs to be configured with a key ID and secret access key
associated with an IAM user or AWS account root user (not recommended) and one
or more session policies. The IAM user must have permissions to call the
GetFederationToken STS API (i.e. allow the `sts:GetFederationToken` action on
the `*` IAM resource). The connector will then generate new temporary STS
tokens upon request by calling the GetFederationToken STS API. These STS tokens
have an expiration period longer that those issued through the AWS IAM Role
authentication method and are more suitable for long-running processes that
cannot automatically re-generate credentials upon expiration.

An AWS region is required and the connector may only be used to access AWS
resources in the specified region.

One or more IAM managed policies may also be configured to grant permissions
to the generated STS tokens. If not specified, the connector will automatically
configure policies according to the resource type and resource ID that the
connector is configured to access. If this authentication method is used with
the generic AWS resource type, a session policy MUST be explicitly specified,
otherwise the generated STS tokens will not have any permissions.

The default expiration period for generated STS tokens is 12 hours with a
minimum of 15 minutes and a maximum of 36 hours. Temporary credentials obtained
by using the AWS account root user credentials (not recommended) have a maximum
duration of 1 hour.

For more information on user federation tokens, session policies and the
GetFederationToken AWS API, see:
https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp_request.html#api_getfederationtoken

For more information about the difference between this method and the AWS
IAM Role authentication method, see:
https://aws.amazon.com/blogs/security/understanding-the-api-options-for-securely-delegating-access-to-your-aws-account/

This method might not be suitable for consumers that cannot automatically
re-generate temporary credentials upon expiration (e.g. an external clients or
long-running process).
""",
            min_expiration_seconds=900,  # 15 minutes
            max_expiration_seconds=43200,  # 12 hours
            default_expiration_seconds=43200,  # 12 hours
            config_class=FederationTokenAuthenticationConfig,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="Generic AWS resource",
            resource_type=AWS_RESOURCE_TYPE,
            description="""
Multi-purpose AWS resource type. It allows consumers to use the connector to
connect to any AWS service. When used by connector consumers, they are provided
a generic boto3 session instance pre-configured with AWS credentials. This
session can then be used to create boto3 clients for any particular AWS service.
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Don't request an AWS specific resource instance ID, given that
            # the connector provides a generic boto3 session instance.
            multi_instance=False,
            instance_discovery=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/aws.png",
        ),
        ResourceTypeModel(
            name="AWS S3 bucket",
            resource_type=S3_RESOURCE_TYPE,
            description="""
Allows users to connect to S3 buckets. When used by connector consumers, they
are provided a pre-configured boto3 S3 client instance.

The configured credentials must have at least the following S3 permissions:

- s3:ListBucket
- s3:GetObject
- s3:PutObject
- s3:DeleteObject
- s3:ListAllMyBuckets

If set, the resource ID must identify an S3 bucket using one of the following
formats:

- S3 bucket URI: s3://<bucket-name>
- S3 bucket ARN: arn:aws:s3:::<bucket-name>
- S3 bucket name: <bucket-name>
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Request an S3 bucket to be configured in the
            # connector or provided by the consumer
            multi_instance=True,
            # Supports listing all S3 buckets that can be accessed with a given
            # set of credentials
            instance_discovery=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/aws.png",
        ),
        ResourceTypeModel(
            name="AWS EKS Kubernetes cluster",
            resource_type=KUBERNETES_RESOURCE_TYPE,
            description="""
Allows users to access an EKS registry as a standard Kubernetes cluster
resource. When used by connector consumers, they are provided a
pre-authenticated python-kubernetes client instance.

The configured credentials must have at least the following EKS permissions:

- eks:ListClusters
- eks:DescribeCluster

In addition to the above permissions, if the credentials are not associated
with the same IAM user or role that created the EKS cluster, the IAM principal
must be manually added to the EKS cluster's `aws-auth` ConfigMap. This makes
it more difficult to use the AWS Federation Token authentication method for
this resource. For more information, see:
https://docs.aws.amazon.com/eks/latest/userguide/add-user-role.html

If set, the resource ID must identify an EKS cluster using one of the following
formats:

- ECR cluster name: <cluster-name>
- EKS cluster ARN: arn:aws:eks:<region>:<account-id>:cluster/<cluster-name>

EKS registry names are region scoped. The connector can only be used to access
EKS clusters in the AWS region that it is configured to use.
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Request an EKS cluster name to be configured in the
            # connector or provided by the consumer
            multi_instance=True,
            # Supports listing all EKS clusters that can be accessed with a
            # given set of credentials
            instance_discovery=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png",
        ),
        ResourceTypeModel(
            name="AWS ECR container repository",
            resource_type=DOCKER_RESOURCE_TYPE,
            description="""
Allows users to access an ECR repository as a standard Docker registry resource.
When used by connector consumers, they are provided a pre-authenticated
python-docker client instance.

The configured credentials must have at least the following ECR permissions:

- ecr:DescribeRegistry
- ecr:DescribeRepositories
- ecr:ListRepositories
- ecr:BatchGetImage
- ecr:DescribeImages
- ecr:BatchCheckLayerAvailability
- ecr:GetDownloadUrlForLayer
- ecr:InitiateLayerUpload
- ecr:UploadLayerPart
- ecr:CompleteLayerUpload
- ecr:PutImage
- ecr:GetAuthorizationToken

If set, the resource ID must identify an ECR repository using one of the
following formats:
            
- ECR repository URI: [https://]<account-id>.dkr.ecr.<region>.amazonaws.com/<repository-name>
- ECR repository ARN: arn:aws:ecr:<region>:<account-id>:repository/<repository-name>
- ECR repository name: <repository-name>

ECR repository names are region scoped. The connector can only be used to access
ECR repositories in the AWS region that it is configured to use.
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Request an ECR repository to be configured in the
            # connector or provided by the consumer
            multi_instance=True,
            # Supports listing all ECR repositories that can be accessed with a
            # given set of credentials
            instance_discovery=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png",
        ),
    ],
)


class AWSServiceConnector(ServiceConnector):
    """AWS service connector."""

    config: AWSBaseConfig

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector type specification.

        Returns:
            The service connector type specification.
        """
        return AWS_SERVICE_CONNECTOR_TYPE_SPEC

    def _get_iam_policy(
        self,
        resource_type: Optional[str],
        resource_id: Optional[str] = None,
    ) -> Optional[str]:
        """Get the IAM inline policy to use for the specified resource.

        Args:
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
                        ],
                        "Resource": resource,
                    },
                ],
            }
            return json.dumps(policy)
        elif resource_type == KUBERNETES_RESOURCE_TYPE:
            if resource_id:
                cluster_name = self._parse_eks_resource_id(resource_id)
                resource = [
                    f"arn:aws:eks:{self.config.region}:*:cluster/{cluster_name}",
                ]
            else:
                resource = [f"arn:aws:eks:{self.config.region}:*:cluster/*"]
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
        elif resource_type == DOCKER_RESOURCE_TYPE:
            if resource_id:
                repo_name, _ = self._parse_ecr_resource_id(
                    resource_id,
                    need_registry_id=False,
                )
                resource = [
                    f"arn:aws:ecr:{self.config.region}:*:repository/{repo_name}",
                ]
            else:
                resource = [
                    f"arn:aws:ecr:{self.config.region}:*:repository/*",
                    f"arn:aws:ecr:{self.config.region}:*:repository",
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
            AuthenticationError: If the IAM role authentication method is used
                and the role cannot be assumed.
            NotImplementedError: If the authentication method is not supported.
        """
        cfg = self.config
        if auth_method == AWSAuthenticationMethods.SECRET_KEY:
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
            return session, None
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
                policy_kwargs = {}
                policy = cfg.policy
                if not cfg.policy and not cfg.policy_arns:
                    policy = self._get_iam_policy(
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
                    except ClientError as e:
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
                    except ClientError as e:
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
                except ClientError as e:
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
            expires_in=EKS_KUBE_API_TOKEN_EXPIRATION,
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
            r"^arn:aws:s3:::[a-z0-9-]+(/.*)*$",
            resource_id,
        ):
            # The resource ID is an S3 bucket ARN
            bucket_name = resource_id.split(":")[-1].split("/")[0]
        elif re.match(
            r"^s3://[a-z0-9-]+(/.*)*$",
            resource_id,
        ):
            # The resource ID is an S3 bucket URI
            bucket_name = resource_id.split("/")[2]
        elif re.match(
            r"^[a-z0-9][a-z0-9-]{1,61}[a-z0-9]$",
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
        need_registry_id: bool = True,
    ) -> Tuple[str, Optional[str]]:
        """Validate and convert an ECR resource ID to an ECR registry ID and repository name.

        Args:
            resource_id: The resource ID to convert.
            need_registry_id: Whether the registry ID is required.

        Returns:
            The ECR repository name and ECR registry ID

        Raises:
            ValueError: If the provided resource ID is not a valid ECR
                repository ARN, URI or repository name.
        """
        # The resource ID could mean different things:
        #
        # - an ECR repository ARN
        # - an ECR repository URI
        # - the ECR repository name
        #
        # We need to extract the region ID, registry ID and repository name from
        # the provided resource ID
        config_region_id = self.config.region
        registry_id: Optional[str] = None
        repository_name: str
        region_id: Optional[str] = None
        if re.match(
            r"^arn:aws:ecr:[a-z0-9-]+:\d{12}:repository/.+$",
            resource_id,
        ):
            # The resource ID is an ECR repository ARN
            registry_id = resource_id.split(":")[4]
            region_id = resource_id.split(":")[3]
            repository_name = resource_id.split("/")[0]
        elif re.match(
            r"^(http[s]?://)?\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/.+$",
            resource_id,
        ):
            # The resource ID is an ECR repository URI
            registry_id = resource_id.split(".")[0].split("/")[-1]
            region_id = resource_id.split(".")[3]
            if resource_id.startswith("https://") or resource_id.startswith(
                "http://"
            ):
                repository_name = resource_id.split("/")[4]
            else:
                repository_name = resource_id.split("/")[1]
        elif re.match(
            r"^([a-z0-9]+([._-][a-z0-9]+)*/)*[a-z0-9]+([._-][a-z0-9]+)*$",
            resource_id,
        ):
            # Assume the resource ID is an ECR repository name
            repository_name = resource_id
        else:
            raise ValueError(
                f"Invalid resource ID for a ECR registry: {resource_id}. "
                f"Supported formats are:\n"
                f"ECR repository ARN: arn:aws:ecr:<region>:<account-id>:repository/<repository-name>\n"
                f"ECR repository URI: [https://]<account-id>.dkr.ecr.<region>.amazonaws.com/<repository-name>\n"
                f"ECR repository name: <repository-name>"
            )

        # If the connector is configured with a region and the resource ID
        # is an ECR repository ARN or URI that specifies a different region
        # we raise an error
        if region_id and region_id != config_region_id:
            raise ValueError(
                f"The AWS region for the {resource_id} ECR repository "
                f"({region_id}) does not match the region configured in "
                f"the connector ({config_region_id})."
            )

        if not registry_id and need_registry_id:
            # If the registry ID is not specified in the resource ID, we need
            # to get it from the caller identity
            try:
                session, _ = self._authenticate(self.auth_method)
                sts_client = session.client("sts")
                response = sts_client.get_caller_identity()
            except ClientError as e:
                raise AuthorizationException(
                    "Failed to get ECR registry ID from ECR repository "
                    f"name: {e}"
                ) from e

            registry_id = response["Account"]

        return repository_name, registry_id

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
            r"^arn:aws:eks:[a-z0-9-]+:\d{12}:cluster/.+$",
            resource_id,
        ):
            # The resource ID is an EKS cluster ARN
            cluster_name = resource_id.split("/")[-1]
            region_id = resource_id.split(":")[3]
        elif re.match(
            r"^[a-z0-9]+[a-z0-9_-]*$",
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
        elif resource_type == KUBERNETES_RESOURCE_TYPE:
            cluster_name = self._parse_eks_resource_id(resource_id)
            return cluster_name
        elif resource_type == DOCKER_RESOURCE_TYPE:
            repository_name, registry_id = self._parse_ecr_resource_id(
                resource_id,
            )
            return (
                f"{registry_id}.dkr.ecr.{self.config.region}.amazonaws.com/"
                f"{repository_name}"
            )
        else:
            return resource_id

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
        - initialize and return a python-docker client if the resource type is
        a Docker registry
        - initialize and return a python-kubernetes client if the resource type
        is a Kubernetes cluster

        Args:
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            A boto3 session for AWS resources, a python-docker client object for
            Docker registries, and a python-kubernetes client object for
            Kubernetes clusters.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                connecting to the indicated resource type or client type.
        """
        resource_type = self.resource_type
        resource_id = self.resource_id

        assert resource_type is not None

        # Regardless of the resource type, we must authenticate to AWS first
        # before we can connect to any AWS resource
        session, _ = self._authenticate(
            self.auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
        )

        if resource_type == S3_RESOURCE_TYPE:
            assert resource_id is not None

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
            f"`get_client_connector` method to get a {resource_type} connector "
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
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                local configuration for the configured resource type or
                authentication method.registry
        """
        resource_type = self.resource_type

        if resource_type in [AWS_RESOURCE_TYPE, S3_RESOURCE_TYPE]:
            raise NotImplementedError(
                f"Local client configuration for resource type "
                f"{resource_type} is not supported"
            )

        raise NotImplementedError(
            f"Configuring the local client for {resource_type} resources is "
            "not directly supported by the AWS connector. Please call the "
            f"`get_client_connector` method to get a {resource_type} connector "
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
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            An AWS connector instance configured with authentication credentials
            automatically extracted from the environment.
        """
        # Initialize an AWS session with the default configuration loaded
        # from the environment.
        session = boto3.Session(
            profile_name=profile_name, region_name=region_name
        )

        # Extract the AWS credentials from the session and store them in
        # the connector secrets.
        credentials = session.get_credentials()
        auth_config: AWSBaseConfig
        if credentials.token:
            if (
                auth_method
                and auth_method != AWSAuthenticationMethods.STS_TOKEN
            ):
                raise NotImplementedError(
                    f"The specified authentication method '{auth_method}' "
                    "could not be used to auto-configure the connector. "
                )
            auth_method = AWSAuthenticationMethods.STS_TOKEN
            auth_config = STSTokenConfig(
                region=session.region_name,
                endpoint_url=session._session.get_config_variable(
                    "endpoint_url"
                ),
                aws_access_key_id=credentials.access_key,
                aws_secret_access_key=credentials.secret_key,
                aws_session_token=credentials.token,
            )
        else:
            if (
                auth_method
                and auth_method != AWSAuthenticationMethods.SECRET_KEY
            ):
                raise NotImplementedError(
                    f"The specified authentication method '{auth_method}' "
                    "could not be used to auto-configure the connector. "
                )
            auth_method = AWSAuthenticationMethods.SECRET_KEY
            auth_config = AWSSecretKeyConfig(
                region=session.region_name,
                endpoint_url=session._session.get_config_variable(
                    "endpoint_url"
                ),
                aws_access_key_id=credentials.access_key,
                aws_secret_access_key=credentials.secret_key,
            )

        return cls(
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id
            if resource_type not in [AWS_RESOURCE_TYPE, None]
            else None,
            config=auth_config,
        )

    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Verify that the connector can authenticate and connect.

        Args:
            resource_type: The type of resource to connect to. Omitted if
                verification is performed for multiple resource types.
            resource_id: The ID of the resource to connect to. Omitted if the
                supplied resource type does not allow multiple instances or
                if verification is performed for multiple resource types.
        """
        # If the resource type or resource ID are not specified, treat this as
        # a generic AWS connector.
        if resource_type is None:
            resource_type = AWS_RESOURCE_TYPE

            session, _ = self._authenticate(
                self.auth_method,
                resource_type=resource_type,
                resource_id=resource_id,
            )

            # Verify that the AWS account is accessible
            assert isinstance(session, boto3.Session)
            sts_client = session.client("sts")
            try:
                sts_client.get_caller_identity()
            except ClientError as err:
                raise AuthorizationException(
                    f"failed to verify AWS account access: {err}"
                ) from err

        else:
            # Verify by checking that the resource exists
            resource_ids = self._list_resource_ids(
                resource_type=resource_type,
                resource_id=resource_id,
            )
            if resource_id and resource_id not in resource_ids:
                raise AuthorizationException(
                    f"the specified resource ID '{resource_id}' of type "
                    f"'{resource_type}' does not exist or cannot be accessed"
                )

    def _list_resource_ids(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """List the resource IDs for the given resource type.

        This method uses the connector's configuration to retrieve a list with
        the IDs of all resource instances of the given type that the connector
        can access. An empty list is returned for generic AWS resources.

        Args:
            resource_type: The type of the resources to list.
            resource_id: The ID of a particular resource to filter by.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                listing resource IDs for the configured resource type or
                authentication method.
        """
        # Get an authenticated boto3 session
        session, _ = self._authenticate(
            self.auth_method,
            resource_type=resource_type,
            resource_id=resource_id,
        )
        assert isinstance(session, boto3.Session)

        if resource_type == AWS_RESOURCE_TYPE:
            return []

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
                except ClientError as e:
                    logger.error(f"Failed to list S3 buckets: {e}")
                    return []

                return [
                    f"s3://{bucket['Name']}" for bucket in response["Buckets"]
                ]
            else:
                # Check if the specified S3 bucket exists
                bucket_name = self._parse_s3_resource_id(resource_id)
                try:
                    s3_client.head_bucket(Bucket=bucket_name)
                    return [resource_id]
                except ClientError as e:
                    logger.error(
                        f"Failed to fetch S3 bucket {bucket_name}: {e}"
                    )
                    return []

        if resource_type == DOCKER_RESOURCE_TYPE:
            ecr_client = session.client(
                "ecr",
                region_name=self.config.region,
                endpoint_url=self.config.endpoint_url,
            )
            if not resource_id:
                # List all ECR repositories
                try:
                    repositories = ecr_client.describe_repositories()
                except ClientError as e:
                    logger.error(f"Failed to list ECR repositories name: {e}")
                    return []

                repo_list: List[str] = []
                for repo in repositories["repositories"]:
                    repo_list.append(repo["repositoryUri"].lstrip("https://"))
                return repo_list
            else:
                # Check if the specified ECR repository exists
                registry_name, registry_id = self._parse_ecr_resource_id(
                    resource_id
                )
                try:
                    repositories = ecr_client.describe_repositories(
                        repositoryNames=[
                            registry_name,
                        ]
                    )
                except ClientError as e:
                    logger.error(
                        f"Failed to fetch ECR repository {registry_name}: {e}"
                    )
                    return []

                return [resource_id]

        if resource_type == KUBERNETES_RESOURCE_TYPE:
            eks_client = session.client(
                "eks",
                region_name=self.config.region,
                endpoint_url=self.config.endpoint_url,
            )
            if not resource_id:
                # List all EKS clusters
                try:
                    clusters = eks_client.list_clusters()
                except ClientError as e:
                    logger.error(f"Failed to list EKS clusters name: {e}")
                    return []

                return clusters["clusters"]
            else:
                # Check if the specified EKS cluster exists
                cluster_name = self._parse_eks_resource_id(resource_id)
                try:
                    clusters = eks_client.describe_cluster(name=cluster_name)
                except ClientError as e:
                    logger.error(
                        f"Failed to fetch EKS cluster {cluster_name}: {e}"
                    )
                    return []

                return [resource_id]

        return []

    def _get_client_connector(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
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

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                connecting to the configured resource type or authentication
                method.
        """
        connector_name = ""
        if self.name:
            connector_name = self.name
        if resource_id:
            connector_name += f" ({resource_type} | {resource_id} client)"
        else:
            connector_name += f" ({resource_type} client)"

        logger.debug(f"Getting client connector for {connector_name}")

        if resource_type in [AWS_RESOURCE_TYPE, S3_RESOURCE_TYPE]:
            if self.auth_method in [
                AWSAuthenticationMethods.SECRET_KEY,
                AWSAuthenticationMethods.STS_TOKEN,
            ]:
                # The secret key and STS token authentication methods do not
                # involve generating temporary credentials, so we can just
                # use the current connector configuration
                config = self.config

                if resource_type == AWS_RESOURCE_TYPE or resource_id:
                    # If the resource type is AWS or a specific resource ID
                    # is specified, we can even return the current connector
                    # instance because it's fully formed and ready to use
                    # to connect to the specified resource
                    return self
                expires_at = self.expires_at
            else:
                # Get an authenticated boto3 session
                session, expires_at = self._authenticate(
                    self.auth_method,
                    resource_type=resource_type,
                    resource_id=resource_id,
                )
                assert isinstance(session, boto3.Session)
                credentials = session.get_credentials()
                assert credentials.token is not None

                # Use the temporary credentials extracted from the boto3 session
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
                auth_method=AWSAuthenticationMethods.STS_TOKEN,
                resource_type=resource_type,
                resource_id=resource_id,
                config=config,
                expires_at=expires_at,
            )

        if resource_type == DOCKER_RESOURCE_TYPE:
            assert resource_id is not None

            # Get an authenticated boto3 session
            session, expires_at = self._authenticate(
                self.auth_method,
                resource_type=resource_type,
                resource_id=resource_id,
            )
            assert isinstance(session, boto3.Session)

            repository_name, registry_id = self._parse_ecr_resource_id(
                resource_id
            )

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
            except ClientError as e:
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
                resource_id=f"{endpoint}/{repository_name}",
                config=DockerCredentials(
                    username=username,
                    password=token,
                ),
                expires_at=expires_at,
            )

        if resource_type == KUBERNETES_RESOURCE_TYPE:
            assert resource_id is not None

            # Get an authenticated boto3 session
            session, expires_at = self._authenticate(
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
            except ClientError as e:
                raise AuthorizationException(
                    f"Failed to get EKS cluster {cluster_name}: {e}"
                ) from e

            try:
                user_token = self._get_eks_bearer_token(
                    session=session,
                    cluster_id=cluster_name,
                    region=self.config.region,
                )
            except ClientError as e:
                raise AuthorizationException(
                    f"Failed to get EKS bearer token: {e}"
                ) from e

            # get cluster details
            cluster_arn = cluster["cluster"]["arn"]
            cluster_ca_cert = cluster["cluster"]["certificateAuthority"][
                "data"
            ]
            cluster_server = cluster["cluster"]["endpoint"]

            # Create a client-side Kubernetes connector instance with the
            # temporary Kubernetes credentials
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
