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

- AWS secret key (access key, secret key)
- AWS STS tokens (access key, secret key, session token)
- IAM roles (i.e. generating temporary STS tokens on the fly by assuming an
IAM role)

Best practices:

- development: use the AWS secret key associated with your AWS account
- production environment: apply the principle of least privilege by configuring
different IAM roles for each AWS service that you use, and use the IAM role
authentication method to generate temporary STS token credentials. This has the
limitation that STS tokens are only valid for a short period of time,
e.g. 12 hours and need to be refreshed periodically. If the
connector consumer is a long-running process like a kubernetes cluster that
needs authenticated access to the ECR registry, the credentials need to be
refreshed periodically by means outside of the service consumer, or the
consumer needs to poll ZenML for new credentials on every authentication
attempt, or ZenML needs to implement an asynchronous periodic refresh mechanism
outside of the interaction between the service consumer and the service
connector.
"""
import base64
import re
import subprocess
import tempfile
from typing import Any, Dict, List, Optional, Tuple

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
)
from zenml.service_connectors.service_connector import (
    AuthenticationConfig,
    ServiceConnector,
)
from zenml.utils.enum_utils import StrEnum

logger = get_logger(__name__)


class KubernetesCredentials(AuthenticationConfig):
    """Kubernetes authentication config."""

    certificate_authority: SecretStr
    server: SecretStr
    client_certificate: SecretStr
    client_key: SecretStr


KUBERNETES_RESOURCE_TYPE = "kubernetes"
# ----------------------------------

AWS_CONNECTOR_TYPE = "aws"
AWS_RESOURCE_TYPE = "aws"
S3_RESOURCE_TYPE = "s3"


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

    region: Optional[str] = Field(
        default=None,
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


class IAMRoleAuthenticationConfig(AWSSecretKeyConfig):
    """AWS IAM authentication config."""

    role_arn: str = Field(
        title="AWS IAM Role ARN",
    )
    policy_arns: Optional[List[str]] = Field(
        default=None,
        title="ARNs of the IAM managed policies that you want to use as a "
        "managed session policy. The policies must exist in the same account "
        "as the IAM user that is requesting federated access.",
    )
    policy: Optional[str] = Field(
        default=None,
        title="An IAM policy in JSON format that you want to use as an inline "
        "session policy",
    )
    expiration_seconds: Optional[int] = Field(
        default=3600,  # 1 hour
        title="AWS IAM Role Token Expiration in Seconds",
    )


class SessionTokenAuthenticationConfig(AWSSecretKeyConfig):
    """AWS session token authentication config."""

    expiration_seconds: Optional[int] = Field(
        default=43200,  # 12 hours
        title="AWS Session Token Expiration in Seconds",
    )


class FederationTokenAuthenticationConfig(AWSSecretKeyConfig):
    """AWS federation token authentication config."""

    policy_arns: Optional[List[str]] = Field(
        default=None,
        title="ARNs of the IAM managed policies that you want to use as a "
        "managed session policy. The policies must exist in the same account "
        "as the IAM user that is requesting federated access.",
    )
    policy: Optional[str] = Field(
        default=None,
        title="An IAM policy in JSON format that you want to use as an inline "
        "session policy",
    )
    expiration_seconds: Optional[int] = Field(
        default=43200,  # 12 hours
        title="AWS Federation Token Expiration in Seconds",
    )


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

One or more optional IAM managed policies can also be configured to further
restrict the permissions of the generated STS tokens.

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
            min_expiration = 900,  # 15 minutes
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
            min_expiration = 900,  # 15 minutes
            max_expiration = 43200,  # 12 hours
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
GetFederationToken STS API. The connector will then generate new temporary STS
tokens upon request by calling the GetFederationToken STS API. These STS tokens
have an expiration period longer that those issued through the AWS IAM Role
authentication method and are more suitable for long-running processes that
cannot automatically re-generate credentials upon expiration.

One or more IAM managed policies must also be configured to grant permissions
to the generated STS tokens, otherwise the tokens will not be able to access
any AWS resources. If you need a simpler way to generate temporary STS tokens,
you can use the AWS Session Token authentication method.

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

This method is recommended for production use.
""",
            min_expiration = 900,  # 15 minutes
            max_expiration = 43200,  # 12 hours
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
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/aws.png",
        ),
        ResourceTypeModel(
            name="AWS S3 bucket",
            resource_type=S3_RESOURCE_TYPE,
            description="""
Allows users to connect to S3 buckets. When used by connector consumers, they
are provided a pre-configured boto3 S3 client instance.

The resource ID must identify an S3 bucket using one of the following formats:

- S3 bucket ARN: arn:aws:s3:::bucket-name
- S3 bucket URI: s3://bucket-name
- S3 bucket name: bucket-name
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Request an S3 bucket to be configured in the
            # connector or provided by the consumer
            multi_instance=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/aws.png",
        ),
        ResourceTypeModel(
            name="AWS EKS Kubernetes cluster",
            resource_type=KUBERNETES_RESOURCE_TYPE,
            description="""
Allows users to access an EKS registry as a standard Kubernetes cluster
resource. When used by connector consumers, they are provided a
pre-authenticated python-kubernetes client instance.

The resource ID must identify an EKS cluster using one of the following formats:

- EKS cluster ARN: arn:aws:eks:[region]:[account-id]:cluster/[cluster-name]
- ECR cluster name: [cluster-name]

EKS registry names are region scoped. If the region name cannot be inferred
from the resource ID, it must be provided as a configuration parameter.
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Request an EKS cluster name to be configured in the
            # connector or provided by the consumer
            multi_instance=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png",
        ),
        ResourceTypeModel(
            name="AWS ECR container registry",
            resource_type=DOCKER_RESOURCE_TYPE,
            description="""
Allows users to access an ECR repository as a standard Docker registry resource.
When used by connector consumers, they are provided a pre-authenticated
python-docker client instance.

The resource ID must identify an ECR repository using one of the following
formats:
            
- ECR repository ARN: arn:aws:ecr:[region]:[account-id]:repository/[repository-name]
- ECR repository URI: [https://][account-id].dkr.ecr.[region].amazonaws.com/[repository-name]
- ECR repository name: [repository-name]

ECR repository names are region scoped. If the region name cannot be inferred
from the resource ID, it must be provided as a configuration parameter.
""",
            auth_methods=AWSAuthenticationMethods.values(),
            # Request an ECR registry to be configured in the
            # connector or provided by the consumer
            multi_instance=True,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/container_registry/docker.png",
        ),
    ],
)


class AWSServiceConnector(ServiceConnector):
    """AWS service connector."""

    config: AWSBaseConfig

    @classmethod
    def get_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector type specification.

        Returns:
            The service connector type specification.
        """
        return AWS_SERVICE_CONNECTOR_TYPE_SPEC

    def _authenticate(self, auth_method: str) -> boto3.Session:
        """Authenticate to AWS.

        Args:
            auth_method: The authentication method to use.

        Returns:
            An authenticated boto3 session.

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
                region_name=self.config.region,
            )
        elif auth_method == AWSAuthenticationMethods.STS_TOKEN:
            assert isinstance(cfg, STSTokenConfig)
            # Create a boto3 session using a temporary AWS STS token
            session = boto3.Session(
                aws_access_key_id=cfg.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=cfg.aws_secret_access_key.get_secret_value(),
                aws_session_token=cfg.aws_session_token.get_secret_value(),
                region_name=self.config.region,
            )
        elif auth_method == AWSAuthenticationMethods.IAM_ROLE:
            assert isinstance(cfg, IAMRoleAuthenticationConfig)
            # Create a boto3 session using an IAM role
            session = boto3.Session(
                aws_access_key_id=cfg.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=cfg.aws_secret_access_key.get_secret_value(),
                region_name=self.config.region,
            )

            sts = session.client("sts", region_name=self.config.region)
            session_name = "zenml-connector"
            if self.id:
                session_name += f"-{self.id}"

            try:
                response = sts.assume_role(
                    RoleArn=cfg.role_arn, RoleSessionName=session_name
                )
            except ClientError as e:
                raise AuthorizationException(
                    f"Failed to assume IAM role {cfg.role_arn} "
                    f"using the AWS credentials configured in the connector: "
                    f"{e}"
                ) from e

            session = boto3.Session(
                aws_access_key_id=response["Credentials"]["AccessKeyId"],
                aws_secret_access_key=response["Credentials"][
                    "SecretAccessKey"
                ],
                aws_session_token=response["Credentials"]["SessionToken"],
            )
        else:
            raise NotImplementedError(
                f"Authentication method '{auth_method}' is not supported by "
                "the AWS connector."
            )

        return session

    @classmethod
    def _get_eks_bearer_token(
        cls, session: boto3.Session, cluster_id: str, region: str
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
        # TODO: make this configurable
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

    def _get_docker_client_config(
        self,
        ecr_client: BaseClient,
        repository_name: str,
        registry_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Get the Docker client configuration for an ECR repository.

        Args:
            ecr_client: An authenticated boto3 client for the ECR service.
            repository_name: The name of the ECR repository to authenticate
                against.
            registry_id: The ID of the ECR registry to authenticate against.
                If not provided, the registry ID will be retrieved from the
                repository name.

        Returns:
            A dictionary containing configuration parameters for the Docker
            client.

        Raises:
            AuthorizationException: If the authorization token could not be
                retrieved from ECR.
        """
        if not registry_id:
            # Retrieve the registry ID from the repository name
            try:
                repositories = ecr_client.describe_repositories(
                    repositoryNames=[
                        repository_name,
                    ]
                )
            except ClientError as e:
                raise AuthorizationException(
                    "Failed to get ECR registry ID from ECR repository "
                    f"name: {e}"
                ) from e

            registry_id = repositories["repositories"][0]["registryId"]

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
        username, token = base64.b64decode(token).decode("utf-8").split(":")

        return dict(
            username=username,
            password=token,
            registry=endpoint,
            reauth=True,
        )

    def _get_kubernetes_client_config(
        self,
        session: boto3.Session,
        eks_client: BaseClient,
        cluster_name: str,
        region_id: str,
    ) -> Dict[str, Any]:
        """Get the Kubernetes client configuration for an EKS repository.

        Args:
            session: An authenticated boto3 session to use for generating the
                token.
            eks_client: An authenticated boto3 client for the EKS service.
            cluster_name: The name of the EKS cluster to authenticate
                against.
            region_id: The ID of the AWS region the EKS cluster is in.

        Returns:
            A dictionary containing configuration parameters for the Kubernetes
            client.

        Raises:
            AuthorizationException: If the authorization token could not be
                retrieved from EKS.
        """
        try:
            cluster = eks_client.describe_cluster(name=cluster_name)
        except ClientError as e:
            raise AuthorizationException(
                f"Failed to get EKS cluster {cluster_name}: {e}"
            ) from e

        try:
            token = self._get_eks_bearer_token(
                session=session,
                cluster_id=cluster_name,
                region=region_id,
            )
        except ClientError as e:
            raise AuthorizationException(
                f"Failed to get EKS bearer token: {e}"
            ) from e

        # get cluster details
        cluster_arn = cluster["cluster"]["arn"]
        cluster_cert = cluster["cluster"]["certificateAuthority"]["data"]
        cluster_ep = cluster["cluster"]["endpoint"]

        return dict(
            cluster_arn=cluster_arn,
            host=cluster_ep,
            ssl_ca_cert=cluster_cert,
            token=token,
        )

    @classmethod
    def _parse_s3_resource_id(cls, resource_id: str) -> str:
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
                f"S3 bucket ARN: arn:aws:s3:::bucket-name\n"
                f"S3 bucket URI: s3://bucket-name\n"
                f"S3 bucket name: bucket-name"
            )

        return bucket_name

    @classmethod
    def _parse_ecr_resource_id(
        cls, resource_id: str, config_region_id: Optional[str] = None
    ) -> Tuple[str, str, Optional[str]]:
        """Validate and convert an ECR resource ID to an AWS region, ECR registry ID and repository name.

        Args:
            resource_id: The resource ID to convert.
            config_region_id: The AWS region the ECR registry is in, if
                configured explicitly in the connector.

        Returns:
            The AWS region, ECR repository name and (optional) ECR registry ID

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
        registry_id: Optional[str] = None
        repository_name: str
        region_id: Optional[str] = None
        if re.match(
            r"^arn:aws:ecr:[a-z0-9-]+:\d{12}:repository/.*$",
            resource_id,
        ):
            # The resource ID is an ECR repository ARN
            registry_id = resource_id.split(":")[4]
            region_id = resource_id.split(":")[3]
            repository_name = resource_id.split("/")[0]
        elif re.match(
            r"^(https://)?\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com/.*$",
            resource_id,
        ):
            # The resource ID is an ECR repository URI
            registry_id = resource_id.split(".")[0].split("/")[-1]
            region_id = resource_id.split(".")[3]
            repository_name = resource_id.split("/")[4]
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
                f"ECR repository ARN: arn:aws:ecr:[region]:[account-id]:repository/[repository-name]\n"
                f"ECR repository URI: [https://][account-id].dkr.ecr.[region].amazonaws.com/[repository-name]\n"
                f"ECR repository name: [repository-name]"
            )

        # If the connector is configured with a region and the resource ID
        # is an ECR repository ARN or URI that specifies a different region
        # we raise an error
        if config_region_id and region_id and region_id != config_region_id:
            raise ValueError(
                f"The AWS region for the {resource_id} ECR repository "
                f"({region_id}) does not match the region configured in "
                f"the connector ({config_region_id})."
            )

        region_id = region_id or config_region_id
        if not region_id:
            raise ValueError(
                f"The AWS region for the ECR repository was not configured "
                f"in the connector and could not be determined from the "
                f"provided resource ID: {resource_id}"
            )

        return region_id, repository_name, registry_id

    @classmethod
    def _parse_eks_resource_id(
        cls, resource_id: str, config_region_id: Optional[str] = None
    ) -> Tuple[str, str]:
        """Validate and convert an EKS resource ID to an AWS region and EKS cluster name.

        Args:
            resource_id: The resource ID to convert.
            config_region_id: The AWS region the EKS cluster is in, if
                configured explicitly in the connector.

        Returns:
            The AWS region and EKS cluster name.

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
                f"EKS cluster ARN: arn:aws:eks:[region]:[account-id]:cluster/[cluster-name]\n"
                f"ECR cluster name: [cluster-name]"
            )

        # If the connector is configured with a region and the resource ID
        # is an EKS registry ARN or URI that specifies a different region
        # we raise an error
        if config_region_id and region_id and region_id != config_region_id:
            raise ValueError(
                f"The AWS region for the {resource_id} EKS cluster "
                f"({region_id}) does not match the region configured in "
                f"the connector ({config_region_id})."
            )

        region_id = region_id or config_region_id

        if not region_id:
            raise ValueError(
                f"The AWS region for the ECR registry was not configured "
                f"in the connector and could not be determined from the "
                f"provided resource ID: {resource_id}"
            )

        return region_id, cluster_name

    def _connect_to_resource(
        self,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to an AWS resource.

        Initialize and return a session or client object depending on the
        connector configuration:

        - initialize and return a boto3 session if the configured resource type
        is a generic AWS resource
        - initialize and return a boto3 client for an S3 resource type
        - initialize and return a python-docker client if the configured
        resource type is a Docker registry
        - initialize and return a python-kubernetes client if the configured
        resource type is a Kubernetes cluster

        Args:
            resource_id: The ID of the AWS resource to connect to.
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
        # Regardless of the resource type, we must authenticate to AWS first
        # before we can connect to any AWS resource
        resource_type = self.resource_type
        resource_id = resource_id or self.resource_id
        session = self._authenticate(self.auth_method)

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
            return client

        if resource_type == DOCKER_RESOURCE_TYPE:
            from docker.client import DockerClient

            assert resource_id is not None

            (
                region_id,
                repository_name,
                registry_id,
            ) = self._parse_ecr_resource_id(
                resource_id, config_region_id=self.config.region
            )

            client = session.client(
                "ecr",
                region_name=region_id,
                endpoint_url=self.config.endpoint_url,
            )

            assert isinstance(client, BaseClient)
            client_kwargs = self._get_docker_client_config(
                ecr_client=client,
                repository_name=repository_name,
                registry_id=registry_id,
            )

            docker_client = DockerClient.from_env()
            docker_client.login(**client_kwargs)

            return docker_client

        if resource_type == KUBERNETES_RESOURCE_TYPE:
            from kubernetes import client as k8s_client

            assert resource_id is not None

            region_id, cluster_name = self._parse_eks_resource_id(
                resource_id, config_region_id=self.config.region
            )

            client = session.client(
                "eks",
                region_name=region_id,
                endpoint_url=self.config.endpoint_url,
            )

            assert isinstance(client, BaseClient)
            client_kwargs = self._get_kubernetes_client_config(
                session=session,
                eks_client=client,
                cluster_name=cluster_name,
                region_id=region_id,
            )

            ssl_ca_cert = client_kwargs["ssl_ca_cert"]
            host = client_kwargs["host"]
            token = client_kwargs["token"]
            cert_bs = base64.urlsafe_b64decode(ssl_ca_cert.encode("utf-8"))

            # TODO: choose a more secure location for the temporary file
            # and use the right permissions
            with tempfile.NamedTemporaryFile(delete=False) as fp:
                ca_filename = fp.name
                fp.write(cert_bs)

            conf = k8s_client.Configuration()
            conf.host = host
            conf.api_key["authorization"] = token
            conf.api_key_prefix["authorization"] = "Bearer"
            conf.ssl_ca_cert = ca_filename

            return k8s_client.ApiClient(conf)

        # The only remaining resource type is AWS_RESOURCE_TYPE
        assert resource_type != AWS_RESOURCE_TYPE

        return session

    def _configure_local_client(
        self,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Configure a local client to authenticate and connect to a resource.

        This method uses the connector's configuration to configure a local
        client or SDK installed on the localhost for the indicated resource.

        Args:
            resource_id: The ID of the resource to connect to. Omitted if the
                configured resource type does not allow multiple instances.
                Can be different than the resource ID that the connector is
                configured to access if resource ID aliases or wildcards
                are supported.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                local configuration for the configured resource type or
                authentication method.
        """
        resource_type = self.resource_type
        resource_id = resource_id or self.resource_id

        # Verify that the configuration is valid before configuring the local
        # client
        # self._verify(
        #     resource_id=resource_id,
        # )

        if resource_type == DOCKER_RESOURCE_TYPE:
            assert resource_id is not None

            (
                region_id,
                repository_name,
                registry_id,
            ) = self._parse_ecr_resource_id(
                resource_id, config_region_id=self.config.region
            )

            # Get a boto3 session
            session = self._authenticate(self.auth_method)

            # Get an ECR boto3 client
            assert isinstance(session, boto3.Session)
            client = session.client(
                "ecr",
                region_name=region_id,
                endpoint_url=self.config.endpoint_url,
            )

            assert isinstance(client, BaseClient)
            client_kwargs = self._get_docker_client_config(
                ecr_client=client,
                repository_name=repository_name,
                registry_id=registry_id,
            )

            username = client_kwargs["username"]
            password = client_kwargs["password"]
            registry_url = client_kwargs["registry"]

            docker_login_cmd = [
                "docker",
                "login",
                "-u",
                username,
                "--password-stdin",
                registry_url,
            ]
            try:
                subprocess.run(
                    docker_login_cmd,
                    check=True,
                    input=password.encode(),
                )
            except subprocess.CalledProcessError as e:
                raise AuthorizationException(
                    f"Failed to authenticate to Docker registry "
                    f"{registry_url}': {e}"
                ) from e

        elif resource_type == KUBERNETES_RESOURCE_TYPE:

            assert resource_id is not None

            region_id, cluster_name = self._parse_eks_resource_id(
                resource_id, config_region_id=self.config.region
            )

            # Get a boto3 session
            session = self._authenticate(self.auth_method)

            assert isinstance(session, boto3.Session)
            # Get a boto3 EKS client
            client = session.client(
                "eks",
                region_name=region_id,
                endpoint_url=self.config.endpoint_url,
            )

            assert isinstance(client, BaseClient)

            client_kwargs = self._get_kubernetes_client_config(
                session=session,
                eks_client=client,
                cluster_name=cluster_name,
                region_id=region_id,
            )

            cluster_arn = client_kwargs["cluster_arn"]
            ssl_ca_cert = client_kwargs["ssl_ca_cert"]
            host = client_kwargs["host"]
            token = client_kwargs["token"]
            cert_bs = base64.urlsafe_b64decode(ssl_ca_cert.encode("utf-8"))

            with tempfile.NamedTemporaryFile(delete=False) as fp:
                ca_filename = fp.name
                fp.write(cert_bs)
                fp.close()

                # add the cluster config to the default kubeconfig
                add_cluster_cmd = [
                    "kubectl",
                    "config",
                    "set-cluster",
                    cluster_arn,
                    "--embed-certs",
                    "--certificate-authority",
                    ca_filename,
                    "--server",
                    host,
                ]
                add_user_cmd = [
                    "kubectl",
                    "config",
                    "set-credentials",
                    cluster_arn,
                    "--token",
                    token,
                ]
                add_context_cmd = [
                    "kubectl",
                    "config",
                    "set-context",
                    cluster_arn,
                    "--cluster",
                    cluster_arn,
                    "--user",
                    cluster_arn,
                ]
                set_context_cmd = [
                    "kubectl",
                    "config",
                    "use-context",
                    cluster_arn,
                ]
                try:
                    for cmd in [
                        add_cluster_cmd,
                        add_user_cmd,
                        add_context_cmd,
                        set_context_cmd,
                    ]:
                        subprocess.run(
                            cmd,
                            check=True,
                        )
                except subprocess.CalledProcessError as e:
                    raise AuthorizationException(
                        f"Failed to update local kubeconfig with the EKS "
                        f"cluster configuration: {e}"
                    ) from e
                logger.info(
                    f"Updated local kubeconfig with the EKS cluster details. "
                    f"The current kubectl context was set to '{cluster_arn}'."
                )
        else:
            raise NotImplementedError(
                f"Auto-configuration for resource type "
                f"{resource_type} is not supported"
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

        resource_type = resource_type or AWS_RESOURCE_TYPE
        return cls(
            auth_method=auth_method,
            resource_type=resource_type,
            resource_id=resource_id
            if resource_type != AWS_RESOURCE_TYPE
            else None,
            config=auth_config,
        )

    def _verify(
        self,
        resource_id: Optional[str] = None,
    ) -> None:
        """Verify that the connector can authenticate and connect.

        Args:
            resource_id: The ID of the resource to connect to. Omitted if the
                configured resource type does not allow multiple instances.
                Can be different than the resource ID that the connector is
                configured to access if resource ID aliases or wildcards
                are supported.
        """
        resource_type = self.resource_type
        resource_id = resource_id or self.resource_id
        client = self._connect_to_resource(
            resource_id=resource_id,
        )

        if resource_type == AWS_RESOURCE_TYPE:
            # Verify that the AWS account is accessible
            assert isinstance(client, boto3.Session)
            sts_client = client.client("sts")
            try:
                sts_client.get_caller_identity()
            except ClientError as err:
                raise AuthorizationException(
                    f"failed to verify AWS account access: {err}"
                ) from err

        elif resource_type == S3_RESOURCE_TYPE:
            assert isinstance(client, BaseClient)
            assert resource_id is not None

            bucket_name = self._parse_s3_resource_id(resource_id)

            # Verify that the S3 bucket exists
            try:
                client.head_bucket(Bucket=bucket_name)
            except ClientError as err:
                raise AuthorizationException(
                    f"failed to verify S3 bucket access: {err}"
                ) from err
        elif resource_type == DOCKER_RESOURCE_TYPE:
            from docker.client import DockerClient

            assert isinstance(client, DockerClient)

            # Verify that the Docker registry exists and is accessible
            try:
                client.ping()
            except ClientError as err:
                raise AuthorizationException(
                    f"failed to verify Docker registry access: {err}"
                ) from err
        elif resource_type == KUBERNETES_RESOURCE_TYPE:
            from kubernetes import client as k8s_client

            assert isinstance(client, k8s_client.ApiClient)

            # Verify that the Kubernetes cluster exists and is accessible
            try:
                client.call_api(
                    "/version",
                    "GET",
                    auth_settings=["BearerToken"],
                    response_type="VersionInfo",
                )
            except k8s_client.ApiException as err:
                raise AuthorizationException(
                    f"failed to verify Kubernetes cluster access: {err}"
                ) from err
