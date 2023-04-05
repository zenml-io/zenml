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

The AWS ServiceConnector implements various authentication methods for AWS
services:

- AWS secret key (access key, secret key)
- AWS STS tokens (access key, secret key, session token)
- IAM roles (i.e. generating temporary STS tokens on the fly by assuming an
IAM role)

Best practices:

- development: use the AWS secret key associated with your AWS account
- production environment: apply the principle of least privilege by configuring
different IAM roles for each AWS service that you use, and use the IAM role
authentication method to generate temporary STS token credentials (with the
limitation that these credentials are only valid for a short period of time,
e.g. 1 hour, 12 hours, etc. and need to be refreshed periodically; if the
service consumer is a long-running process, e.g. a kubernetes cluster that
needs authenticated access to the ECR registry, the credentials need to be
refreshed periodically by means outside of the service consumer, or the
consumer needs to poll ZenML for new credentials on every authentication
attempt, or ZenML needs to implement an asynchronous periodic refresh mechanism
outside of the interaction between the service consumer and the service
connector).

Functionality and workflow:

- registration: you can register an AWSServiceConnector with a chosen
authentication method configuration (e.g. AWS credentials, IAM role, ZenML
secrets etc.)
    - if credentials are provided, they are validated against the required
    schema in addition to non-credentials configuration
    - if a reference to an existing secret is provided, the secret contents is
    validated against the required schema
    - if a new secret is provided alongside credentials, the secret is created
    - if a secret is not provided and credentials are provided, a new secret
    with a random name is created and referenced in the saved configuration.
    - the saved connector instance doesn't contain any credentials, only
    references to secrets that contain the credentials
    - an optional validation is performed to ensure that the credentials are
    valid and can be used to authenticate against AWS services (TBD: how)
    - a default method/list of methods is chosen by the connector
    instance if none are provided
        - the first one that already works without credentials ? all of them ?

- discovery: stack components find and instantiate one (or more ?) connectors
that they need for their functionality
    - the definition or implementation of each component can declare a list of
    supported connectors and authentication methods
    - when a component is registered/updated, it can be configured to reference a
    particular registered connector (by name/ID) or it can be configured to
    perform dynamic discovery of an connector that supports the required
    type / authentication methods and is otherwise accessible to the component
    (e.g. in the same namespace, in the same project, etc.)
    - when an explicit connector is referenced, validation is performed to
    ensure that the connector supports the required type / authentication
    methods and that it is accessible to the component
    
- instantiation: you can instantiate an existing AWSServiceConnector and optionally
provide an authentication method or a list of authentication methods to try in
order. If no list is provided, the saved list of methods is used.

- credentials update: you can update the credentials of an existing
AWSServiceConnector by providing new credentials or a reference to a new secret
    - the new credentials are validated against the required schema/method
    - much of what happens during registration happens during update as well,
    but only needs to happen for a single method

- resolution (after instantiation): the connector tries to resolve credentials using the provided
methods in order and uses the first successful method/result.
    - in the simplest case, it only supports one method (explicit long-term
    credentials) and extracts the credentials contained in the referenced secret
    - more complex cases involve trying multiple methods in order and remembering
    the first successful method/result
    - the credentials fetched from secrets are validated against the required
    schema (to prevent tampering with the secret contents)
    - TBD: do we also validate that the credentials themselves haven't been
    tampered with? (e.g. by keeping a hash and checking it against the secret
    contents or by keeping/checking the last update timestamp) 
    - the instance is context aware, e.g. depending on the context (local,
    remote, container registry, kubernetes, etc.) it will try to resolve
    credentials using the provided methods in order and return the first
    successful result.

- validity check (after resolution): you can check if a registered AWSServiceConnector is still valid
    - the check is performed by trying to resolve credentials using the
    registered methods in order and returning the first successful method/result
    - if the check fails, the connector is deemed invalid
    - an optional validation is performed to ensure that the credentials are
    valid and can be used to authenticate against AWS services (TBD: how)
    - must be able to detect expired temporary credentials (e.g. STS tokens)

- consume (after resolution): the connector provides authentication
configuration and credentials or authenticated clients for third-party consumers.
    - can optionally include running the validity check
    - in the simplest case, returns the same authentication configuration and
    credentials that were registered
    - more complex cases involve returning authenticated clients (e.g. boto3
    clients, kubernetes clients, etc.) that are configured to use the resolved
    credentials) or generating different credentials (e.g. STS tokens) from the
    configuration and credentials resolved by the connector  
        - for a method that uses temporary credentials, the credentials resolved
        by the connector can be used to generate temporary credentials (e.g.
        STS tokens)
        - for different services, the credentials resolved by the connector
        can be used to generate different credentials (e.g. IAM role credentials
        STS tokens for ECR, Kubernetes credentials for EKS.)
        - various other contexts require generating credentials resolved with
        an authentication method to be used by a different method (e.g. local
        implicit credentials converted into environment variables to be used
        by the same connector in a remote context)
    - the consumer must be aware of which authentication methods/clients it
    needs to use
    (e.g. the S3 artifact store needs to use the credentials or S3 client provided
    by the connector to access S3) and even which authentication method or
    credential types are/are not supported for the service it needs to access
    (e.g. authenticating to a private ECR container registry only supports STS
    tokens generated with an IAM role, not long-term credentials)
    - in some cases, the consumer can be configured with additional configuration
    needed in the authentication process (e.g. the ECR container registry needs
    to be configured with the AWS region to use and an optional role to assume
    if the credentials are temporary)


Q: how are connectors scoped ? project, user, global ? what about scoping
an connector to be used only by a specific stack component ? can a user scoped
connector reference a project scoped secret and vice versa ? are secrets
referenced in the connector by ID or by name ? what about their contents, do
they have to conform to the connector schema 1:1 or can they contain additional
fields that are ignored by the connector ?

"""
import base64
import re
from typing import Any, List, Optional

import boto3
from botocore.exceptions import ClientError
from pydantic import SecretStr

from zenml.exceptions import AuthorizationException
from zenml.service_connectors.service_connector import (
    AuthenticationConfig,
    AuthenticationMethodSpecification,
    AuthenticationSecrets,
    ServiceConnector,
    ServiceConnectorConfig,
    ServiceConnectorSpecification,
)
from zenml.utils.enum_utils import StrEnum

# TODO: use "resource" instead of service:
# resource connector, resource type, resource name
# allow the resource ID/name to be supplied as a generic parameter during
# authentication, either configured in the connector or supplied by the user
# during authentication (e.g. ECR repository name, S3 bucket name, etc.)


class DockerCredentials(AuthenticationSecrets):
    """Docker authentication secrets."""

    username: SecretStr
    password: SecretStr


DOCKER_RESOURCE_TYPE = "docker"


class KubernetesCredentials(AuthenticationSecrets):
    """Kubernetes authentication config."""

    certificate_authority: SecretStr
    server: SecretStr
    client_certificate: SecretStr
    client_key: SecretStr


KUBERNETES_RESOURCE_TYPE = "kubernetes"
# ----------------------------------

AWS_CONNECTOR_TYPE = "AWS"
AWS_RESOURCE_TYPE = "aws"


class AWSAuthenticationConfig(AuthenticationConfig):
    """AWS authentication configuration."""

    region: Optional[str] = None
    endpoint_url: Optional[str] = None


class AWSSecretKey(AuthenticationSecrets):
    """AWS credentials authentication secrets."""

    aws_access_key_id: SecretStr
    aws_secret_access_key: SecretStr


class IAMRoleAuthenticationConfig(AWSAuthenticationConfig):
    """AWS IAM authentication config."""

    role_arn: str
    expiration_seconds: Optional[int] = None


class STSToken(AWSSecretKey):
    """AWS STS token."""

    aws_session_token: SecretStr


class AWSAuthenticationMethods(StrEnum):
    """AWS Authentication methods."""

    SECRET_KEY = "AWS secret key"
    STS_TOKEN = "AWS STS token"
    IAM_ROLE = "AWS IAM role"


class AWSServiceConnectorSpecification(ServiceConnectorSpecification):
    """AWS service connector specification."""

    @classmethod
    def get_equivalent_resource_types(cls, resource_type: str) -> List[str]:
        """Get a list of AWS resource types that are equivalent to the given one.

        This method is an override of the base class method and is used to
        model the following:

        * `aws` is a wildcard that matches all AWS resource types: if a
        connector is configured to provide `aws` resources, it will match
        queries for any AWS resource type
        * `eks` is a specialization of `kubernetes`: if a connector is
        configured to provide `eks` resources, it will match queries for
        `kubernetes` resources as well as `eks` resources (but not vice-versa)
        * `ecr` is a specialization of `docker`: if a connector is configured
        to provide `ecr` resources, it will match queries for `docker`
        resources as well as `ecr` resources (but not vice-versa)

        Args:
            resource_type: The resource type identifier to match.

        Returns:
            A list of resource type identifiers that are equivalent or
            subordinate to the given one.
        """
        if resource_type == AWS_RESOURCE_TYPE:
            return [
                AWS_RESOURCE_TYPE,
                *boto3.Session().get_available_services(),
            ]
        if resource_type == KUBERNETES_RESOURCE_TYPE:
            return [KUBERNETES_RESOURCE_TYPE, "eks"]
        if resource_type == DOCKER_RESOURCE_TYPE:
            return [DOCKER_RESOURCE_TYPE, "ecr"]
        return [resource_type]


class AWSServiceConnector(ServiceConnector):
    """AWS service connector."""

    config: ServiceConnectorConfig

    @classmethod
    def get_specification(cls) -> ServiceConnectorSpecification:
        """Get AWS connector specification.

        Returns:
            AWS connector specification.
        """
        return AWSServiceConnectorSpecification(
            connector_type=AWS_CONNECTOR_TYPE,
            description="""
This ZenML AWS service connector facilitates connecting to, authenticating to
and accessing AWS services, from S3 buckets to EKS clusters. Explicit long-term
AWS credentials are supported, as well as temporary credentials such as STS
tokens or IAM roles. The connector also allows configuration of local Docker and
Kubernetes clients as well as auto-configuration by discovering and loading
credentials stored on a local environment.

The connector supports the following authentication methods:

- `AWS secret key`: uses long-term AWS credentials consisting of an access key
ID and secret access key. This method is preferred during development and testing
due to its simplicity and ease of use. It is not recommended for production
use due to the risk of long-term credentials being exposed. The IAM roles method
is preferred for production, unless there are specific reasons to use
long-term credentials (e.g. an external client or long-running process is
involved and it is not possible to periodically regenerate temporary credentials
upon expiration).

- `AWS STS token`: uses temporary STS tokens explicitly generated by the user or
auto-configured from a local environment. This method has the major limitation
that the user must regularly generate new tokens and update the connector
configuration as STS tokens expire. This method is best used in cases where the
connector only needs to be used for a short period of time.

- `AWS IAM role`: generates temporary STS credentials by assuming an IAM role.
This is the recommended method for production use. The connector needs to be
configured with an IAM role accompanied by an access key ID and secret access
key that have permission to assume the IAM role. The connector will then
generate new temporary STS tokens upon request. This method might not be
suitable in cases where the consumer cannot re-generate temporary credentials
upon expiration (e.g. an external client or long-running process is involved).

The connector facilitates access to any AWS service, including S3, ECR, EKS,
EC2, etc. by providing pre-configured boto3 clients for these services. In
addition to multi-purpose AWS authentication, the connector also supports
authentication for Docker and Kubernetes clients. This is reflected in the range
of resource types supported by the connector:

- `aws`: this is used as a wildcard resource type indicating that the connector
can be used to access any of the AWS services. When this resource type is
used, connector consumers are handed in a general purpose pre-authenticated
boto3 session instead of a particular boto3 client.
- in addition to the generic AWS resource type, the connector also supports any
of the well known AWS service names as a resource type. The AWS service name
must be one of the values listed in the boto3 documentation (e.g. "s3",
"secretsmanager", "sagemaker"):
https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/index.html
When this resource type is used, the connector provides to consumers a boto3
client specifically configured for the specified service.
- `docker`: this is an alias for the AWS ECR service that allows consumers to
discover this connector as a Docker client provider. When used by connector
consumers, then are provided a pre-authenticated python-docker client instance
instead of a boto3 client.
- `kubernetes`: this is an alias for the AWS EKS service that allows consumers
to discover this connector as a Docker client provider. When used by connector
consumers, they are issued a pre-authenticated python-kubernetes client instance
instead of a boto3 client.

Some AWS resources are region-specific, e.g. S3 buckets, ECR repositories, etc.
For these resources, the connector allows the user to specify the region in the
connector config if it cannot be inferred from the resource ID.
""",
            supports_resource_types=True,
            # Allow arbitrary resource types to be specified, e.g. "S3", "ECR",
            arbitrary_resource_types=False,
            resource_types=[
                AWS_RESOURCE_TYPE,
                *boto3.Session().get_available_services(),
            ],
            auth_methods=[
                AuthenticationMethodSpecification(
                    auth_method=AWSAuthenticationMethods.SECRET_KEY,
                    resource_types=[DOCKER_RESOURCE_TYPE],
                    # Request an ECR registry to be configured in the
                    # connector or provided by the consumer
                    supports_resource_ids=True,
                    auth_config=AWSAuthenticationConfig,
                    auth_secrets=AWSSecretKey,
                ),
                AuthenticationMethodSpecification(
                    auth_method=AWSAuthenticationMethods.STS_TOKEN,
                    resource_types=[DOCKER_RESOURCE_TYPE],
                    # Request an ECR registry to be configured in the
                    # connector or provided by the consumer
                    supports_resource_ids=True,
                    auth_config=AWSAuthenticationConfig,
                    auth_secrets=STSToken,
                ),
                AuthenticationMethodSpecification(
                    auth_method=AWSAuthenticationMethods.IAM_ROLE,
                    resource_types=[DOCKER_RESOURCE_TYPE],
                    # Request an ECR registry to be configured in the
                    # connector or provided by the consumer
                    supports_resource_ids=True,
                    auth_config=IAMRoleAuthenticationConfig,
                    auth_secrets=AWSSecretKey,
                ),
                AuthenticationMethodSpecification(
                    auth_method=AWSAuthenticationMethods.SECRET_KEY,
                    resource_types=[KUBERNETES_RESOURCE_TYPE],
                    # Request an EKS cluster name to be configured in the
                    # connector or provided by the consumer
                    supports_resource_ids=True,
                    auth_config=AWSAuthenticationConfig,
                    auth_secrets=AWSSecretKey,
                ),
                AuthenticationMethodSpecification(
                    auth_method=AWSAuthenticationMethods.STS_TOKEN,
                    resource_types=[KUBERNETES_RESOURCE_TYPE],
                    # Request an EKS cluster name to be configured in the
                    # connector or provided by the consumer
                    supports_resource_ids=True,
                    auth_config=AWSAuthenticationConfig,
                    auth_secrets=STSToken,
                ),
                AuthenticationMethodSpecification(
                    auth_method=AWSAuthenticationMethods.IAM_ROLE,
                    resource_types=[KUBERNETES_RESOURCE_TYPE],
                    # Request an EKS cluster name to be configured in the
                    # connector or provided by the consumer
                    supports_resource_ids=True,
                    auth_config=IAMRoleAuthenticationConfig,
                    auth_secrets=AWSSecretKey,
                ),
                AuthenticationMethodSpecification(
                    auth_method=AWSAuthenticationMethods.SECRET_KEY,
                    # Request an AWS specific resource instance ID (e.g. an S3
                    # bucket name, ECR repository name) to be configured in the
                    # connector or provided by the consumer
                    supports_resource_ids=True,
                    auth_config=AWSAuthenticationConfig,
                    auth_secrets=AWSSecretKey,
                    description="Configure long-term AWS credentials "
                    "consisting of an access key ID and secret access key "
                    "associated with an AWS user account.",
                ),
                AuthenticationMethodSpecification(
                    auth_method=AWSAuthenticationMethods.STS_TOKEN,
                    # Request an AWS specific resource instance ID (e.g. an S3
                    # bucket name, ECR repository name) to be configured in the
                    # connector or provided by the consumer
                    supports_resource_ids=True,
                    auth_config=AWSAuthenticationConfig,
                    auth_secrets=STSToken,
                    description="Configure a temporary AWS STS token.",
                ),
                AuthenticationMethodSpecification(
                    auth_method=AWSAuthenticationMethods.IAM_ROLE,
                    # Request an AWS specific resource instance ID (e.g. an S3
                    # bucket name, ECR repository name) to be configured in the
                    # connector or provided by the consumer
                    supports_resource_ids=True,
                    auth_config=IAMRoleAuthenticationConfig,
                    auth_secrets=AWSSecretKey,
                ),
            ],
        )

    def _connect_to_resource(
        self,
        config: ServiceConnectorConfig,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_type: Optional[str] = None,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to an AWS resource.

        Initialize and return a session or client object depending on the
        connector configuration and the requested resource type:

        - initialize and return a boto3 session for a generic AWS resource
        - initialize and return a boto3 client for a specific AWS service
        - initialize and return a python-docker client if the requested resource
        type is a Docker registry
        - initialize and return a python-kubernetes client if the requested
        resource type is a Kubernetes cluster

        Args:
            config: The connector configuration.
            resource_type: The type of resource to connect to.
            resource_id: The ID of the AWS resource to connect to.
            client_type: The type of client to instantiate, configure and
                return.
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            A boto3 session or client object for AWS resources, a python-docker
            client object for Docker registries, or a python-kubernetes client
            object for Kubernetes clusters.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                connecting to the indicated resource type or client type.
        """
        # Regardless of the resource type, we must authenticate to AWS first
        # before we can connect to any AWS resource
        auth_method = config.auth_method
        if auth_method == AWSAuthenticationMethods.SECRET_KEY:
            assert isinstance(config.auth_config, AWSAuthenticationConfig)
            assert isinstance(config.auth_secrets, AWSSecretKey)
            # Create a boto3 session using long-term AWS credentials
            s = config.auth_secrets
            session = boto3.Session(
                aws_access_key_id=s.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=s.aws_secret_access_key.get_secret_value(),
                region_name=config.auth_config.region,
            )
        elif auth_method == AWSAuthenticationMethods.STS_TOKEN:
            assert isinstance(config.auth_config, AWSAuthenticationConfig)
            assert isinstance(config.auth_secrets, STSToken)
            # Create a boto3 session using a temporary AWS STS token
            s = config.auth_secrets
            session = boto3.Session(
                aws_access_key_id=s.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=s.aws_secret_access_key.get_secret_value(),
                aws_session_token=s.aws_session_token.get_secret_value(),
                region_name=config.auth_config.region,
            )
        elif auth_method == AWSAuthenticationMethods.IAM_ROLE:
            assert isinstance(config.auth_config, IAMRoleAuthenticationConfig)
            assert isinstance(config.auth_secrets, AWSSecretKey)
            # Create a boto3 session using an IAM role
            s = config.auth_secrets
            session = boto3.Session(
                aws_access_key_id=s.aws_access_key_id.get_secret_value(),
                aws_secret_access_key=s.aws_secret_access_key.get_secret_value(),
                region_name=config.auth_config.region,
            )

            sts = session.client("sts")
            try:
                response = sts.assume_role(
                    RoleArn=config.auth_config.role_arn,
                )
            except ClientError as e:
                raise AuthorizationException(
                    f"Failed to assume IAM role {config.auth_config.role_arn} "
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
                f"Authentication method {auth_method} is not supported by the "
                f"AWS connector."
            )

        if resource_type == AWS_RESOURCE_TYPE:
            return session

        if resource_type == DOCKER_RESOURCE_TYPE:
            from docker import DockerClient

            resource_id = resource_id or self.config.resource_id
            if not resource_id:
                raise ValueError(
                    "The AWS connector was not configured with a Docker "
                    "registry ID and one was not provided at runtime."
                )

            # The resource ID could mean different things:
            #
            # - an ECR repository ARN
            # - an ECR repository URI
            # - an ECR registry ID
            # - the ECR repository name
            #
            # We need to extract the registry ID and region ID from the provided
            # resource ID
            registry_id: Optional[str] = None
            registry_name: Optional[str] = None
            region_id: Optional[str] = None
            if re.match(
                r"^arn:aws:ecr:[a-z0-9-]+:\d{12}:repository(/.*)*$",
                resource_id,
            ):
                # The resource ID is an ECR repository ARN
                registry_id = resource_id.split(":")[4]
                region_id = resource_id.split(":")[3]
            elif re.match(
                r"^(https://)?\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com(/.*)*$",
                resource_id,
            ):
                # The resource ID is an ECR repository URI
                registry_id = resource_id.split(".")[0].split("/")[-1]
                region_id = resource_id.split(".")[3]
            elif re.match(r"^\d{12}$", resource_id):
                # The resource ID is an ECR registry ID
                registry_id = resource_id
                region_id = config.auth_config.region
            elif re.match(
                r"^([a-z0-9]+([._-][a-z0-9]+)*/)*[a-z0-9]+([._-][a-z0-9]+)*$",
                resource_id,
            ):
                # Assume the resource ID is an ECR repository name
                region_id = config.auth_config.region
                registry_name = resource_id
            else:
                raise ValueError(
                    f"Invalid resource ID for a ECR registry: {resource_id}. "
                    f"Supported formats are:\n"
                    f"ECR repository ARN: arn:aws:ecr:[region]:[account-id]:repository/[repository-name]\n"
                    f"ECR repository URI: [https://][account-id].dkr.ecr.[region].amazonaws.com/[repository-name]\n"
                    f"ECR registry ID: [account-id]\n"
                    f"ECR repository name: [repository-name]"
                )

            # TODO: what do we do if the connector is configured with a region
            # and the resource ID is an ECR repository ARN or URI that specifies
            # a different region?

            if not region_id:
                raise ValueError(
                    f"The AWS region for the ECR registry was not configured "
                    f"in the connector and could not be determined from the "
                    f"provided resource ID: {resource_id}"
                )

            client = session.client(
                "ecr", region_name=config.auth_config.region
            )

            if registry_name:
                # Get the registry ID from the repository name
                try:
                    repositories = client.describe_repositories(
                        repositoryNames=[
                            registry_name,
                        ]
                    )
                except ClientError as e:
                    raise AuthorizationException(
                        f"Failed to get ECR registry ID from ECR repository name: {e}"
                    ) from e

                registry_id = repositories["repositories"][0]["registryId"]

            try:
                auth_token = client.get_authorization_token(
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
            print(f"username: {username}")
            print(f"token: {token}")
            docker_client = DockerClient.from_env()
            docker_client.login(
                username=username,
                password=token,
                registry=endpoint,
                reauth=True,
            )
            return docker_client

        if resource_type == KUBERNETES_RESOURCE_TYPE:
            from kubernetes import client as k8s_client
            from kubernetes import config as k8s_config

            # The resource ID could mean different things:
            #
            # - an EKS cluster ARN
            # - an EKS cluster name
            # - an EKS cluster endpoint
            # - an EKS cluster ID
            # - an EKS cluster OIDC issuer URL
            #
            # We need to extract the registry ID and region ID from the provided
            # resource ID
            # cluster_id: Optional[str] = None
            # registry_name: Optional[str] = None
            # region_id: Optional[str] = None
            # if re.match(
            #     r"^arn:aws:ecr:[a-z0-9-]+:\d{12}:repository(/.*)*$",
            #     resource_id,
            # ):
            #     # The resource ID is an ECR repository ARN
            #     registry_id = resource_id.split(":")[4]
            #     region_id = resource_id.split(":")[3]
            # elif re.match(
            #     r"^(https://)?\d{12}\.dkr\.ecr\.[a-z0-9-]+\.amazonaws\.com(/.*)*$",
            #     resource_id,
            # ):
            #     # The resource ID is an ECR repository URI
            #     registry_id = resource_id.split(".")[0].split("/")[-1]
            #     region_id = resource_id.split(".")[3]
            # elif re.match(r"^\d{12}$", resource_id):
            #     # The resource ID is an ECR registry ID
            #     registry_id = resource_id
            #     region_id = config.auth_config.region
            # elif re.match(
            #     r"^([a-z0-9]+([._-][a-z0-9]+)*/)*[a-z0-9]+([._-][a-z0-9]+)*$",
            #     resource_id,
            # ):
            #     # Assume the resource ID is an ECR repository name
            #     region_id = config.auth_config.region
            #     registry_name = resource_id
            # else:
            #     raise ValueError(
            #         f"Invalid resource ID for a ECR registry: {resource_id}. "
            #         f"Supported formats are:\n"
            #         f"ECR repository ARN: arn:aws:ecr:[region]:[account-id]:repository/[repository-name]\n"
            #         f"ECR repository URI: [https://][account-id].dkr.ecr.[region].amazonaws.com/[repository-name]\n"
            #         f"ECR registry ID: [account-id]\n"
            #         f"ECR repository name: [repository-name]"
            #     )

            # TODO: what do we do if the connector is configured with a region
            # and the resource ID is an ECR repository ARN or URI that specifies
            # a different region?


            region_id = config.auth_config.region

            if not region_id:
                raise ValueError(
                    f"The AWS region for the ECR registry was not configured "
                    f"in the connector and could not be determined from the "
                    f"provided resource ID: {resource_id}"
                )

            client = session.client('eks', region_name=config.auth_config.region)
            try:
                cluster = client.describe_cluster(
                    name=resource_id
                )
            except ClientError as e:
                raise AuthorizationException(
                    f"Failed to get EKS cluster: {e}"
                ) from e

            # endpoint = response["cluster"]["endpoint"]
            # cert = response["cluster"]["certificateAuthority"]["data"]
            # k8s_config.load_kube_config()
            # k8s_config.kube_config.KUBE_CONFIG_DEFAULT_LOCATION = "/tmp/kubeconfig"

            # # get cluster details
            cluster_cert = cluster["cluster"]["certificateAuthority"]["data"]
            cluster_ep = cluster["cluster"]["endpoint"]

            # # build the cluster config hash
            cluster_config = {
                    "apiVersion": "v1",
                    "kind": "Config",
                    "clusters": [
                        {
                            "cluster": {
                                "server": str(cluster_ep),
                                "certificate-authority-data": str(cluster_cert)
                            },
                            "name": "kubernetes"
                        }
                    ],
                    "contexts": [
                        {
                            "context": {
                                "cluster": "kubernetes",
                                "user": "aws"
                            },
                            "name": "aws"
                        }
                    ],
                    "current-context": "aws",
                    "preferences": {},
                    "users": [
                        {
                            "name": "aws",
                            "user": {
                                "exec": {
                                    "apiVersion": "client.authentication.k8s.io/v1alpha1",
                                    "command": "heptio-authenticator-aws",
                                    "args": [
                                        "token", "-i", cluster_name
                                    ]
                                }
                            }
                        }
                    ]
                }

            # # Write in YAML.
            # config_text=yaml.dump(cluster_config, default_flow_style=False)
            # open(config_file, "w").write(config_text)

            # eks = boto3.client(
            #     "eks",
            #     aws_session_token=session_token,
            #     aws_access_key_id=access_key_id,
            #     aws_secret_access_key=secret_access_key,
            #     region_name=region_name,
            # )

            # clusters = eks.list_clusters()["clusters"]
            # if cluster_name not in clusters:
            #     raise RuntimeError(f"configured cluster: {cluster_name} not found among {clusters}")

            # with TemporaryDirectory() as kube:
            #     kubeconfig_path = Path(kube) / "config"

            #     # let awscli generate the kubeconfig
            #     result = aws(
            #         "eks",
            #         "update-kubeconfig",
            #         "--name",
            #         cluster_name,
            #         _env={
            #             "AWS_ACCESS_KEY_ID": access_key_id,
            #             "AWS_SECRET_ACCESS_KEY": secret_access_key,
            #             "AWS_SESSION_TOKEN": session_token,
            #             "AWS_DEFAULT_REGION": region_name,
            #             "KUBECONFIG": str(kubeconfig_path),
            #         },
            #     )

            #     # read the generated file
            #     with open(kubeconfig_path, "r") as f:
            #         kubeconfig_str = f.read()
            #     kubeconfig = yaml.load(kubeconfig_str, Loader=yaml.SafeLoader)

            #     # the generated kubeconfig assumes that upon use it will have access to
            #     # `~/.aws/credentials`, but maybe this filesystem is ephemeral,
            #     # so add the creds as env vars on the aws command in the kubeconfig
            #     # so that even if the kubeconfig is separated from ~/.aws it is still
            #     # useful
            #     users = kubeconfig["users"]
            #     for i in range(len(users)):
            #         kubeconfig["users"][i]["user"]["exec"]["env"] = [
            #             {"name": "AWS_ACCESS_KEY_ID", "value": access_key_id},
            #             {"name": "AWS_SECRET_ACCESS_KEY", "value": secret_access_key},
            #             {"name": "AWS_SESSION_TOKEN", "value": session_token},
            #         ]

            #     # write the updates to disk
            #     with open(kubeconfig_path, "w") as f:
            #         f.write(yaml.dump(kubeconfig))

            #     awsclipath = str(Path(sh("-c", "which aws").stdout.decode()).parent)
            #     kubectlpath = str(Path(sh("-c", "which kubectl").stdout.decode()).parent)
            #     pathval = f"{awsclipath}:{kubectlpath}"

            # return self.connect_to_kubernetes(auth_method, **kwargs)
            return None

        if not resource_type:
            # If no AWS resource type is specified, return the generic boto3
            # session
            return session

        return session.client(
            resource_type,
            region_name=config.auth_config.region,
            endpoint_url=config.auth_config.endpoint_url,
        )

    def _configure_local_client(
        self,
        config: ServiceConnectorConfig,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_type: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        """Configure a local client for a service using the specified authentication method.

        This method uses the connector's configuration to configure a local
        client or SDK installed on the localhost for the indicated resource.

        Args:
            config: The connector configuration.
            resource_type: The type of resource to connect to. Omitted if the
                connector does not support multiple resource types.
            resource_id: The ID of the resource to connect to. Omitted if the
                configured authentication method does not require a resource ID.
            client_type: The type of client to configure. If not specified,
                the connector implementation must decide which client to
                configure or raise an exception. For connectors and resources
                that do not support multiple client types, this parameter may be
                omitted.
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                local configuration for the indicated resource type or client
                type.
        """


    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        client_type: Optional[str] = None,
        region_name: Optional[str] = None,
        profile_name: Optional[str] = None,
        **kwargs: Any,
    ) -> ServiceConnectorConfig:
        """Auto-configure the connector.

        Auto-configure the AWS connector by looking for authentication
        configuration in the environment (e.g. environment variables or
        configuration files) and storing it in the connector configuration.

        Args:
            auth_method: The particular authentication method to use. If not
                specified, the connector implementation must decide which
                authentication method to use or raise an exception.
            resource_type: The type of resource to configure. Omitted if the
                connector does not support resource types.
            resource_id: The ID of the resource to connect to. The
                implementation may choose to either require or ignore this
                parameter if it does not support or detect an authentication
                methods that uses a resource ID.
            client_type: The type of client to configure. Omitted if the
                connector does not support multiple client types.
            region_name: The name of the AWS region to use. If not specified,
                the implicit region is used.
            profile_name: The name of the AWS profile to use. If not specified,
                the implicit profile is used.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            The connector configuration populated with auto-configured
            authentication credentials.

        Raises:
            NotImplementedError: If the connector does not support
                auto-configuration.
        """
        # Initialize an AWS session with the default configuration loaded
        # from the environment.
        session = boto3.Session(
            profile_name=profile_name, region_name=region_name
        )

        # Extract the AWS configuration from the session and store it in
        # the connector configuration.
        auth_config = AWSAuthenticationConfig(
            region=session.region_name,
            endpoint_url=session._session.get_config_variable("endpoint_url"),
        )

        # Extract the AWS credentials from the session and store them in
        # the connector secrets.
        credentials = session.get_credentials()
        auth_method = AWSAuthenticationMethods.SECRET_KEY
        if credentials.token:
            auth_method = AWSAuthenticationMethods.STS_TOKEN
            auth_secrets = STSToken(
                aws_access_key_id=credentials.access_key,
                aws_secret_access_key=credentials.secret_key,
                aws_session_token=credentials.token,
            )
        else:
            auth_secrets = AWSSecretKey(
                aws_access_key_id=credentials.access_key,
                aws_secret_access_key=credentials.secret_key,
            )

        return ServiceConnectorConfig(
            auth_method=auth_method,
            resource_types=[resource_type] if resource_type else None,
            resource_id=resource_id,
            auth_config=auth_config,
            auth_secrets=auth_secrets,
        )
