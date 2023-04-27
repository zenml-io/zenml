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
"""Kubernetes Service Connector.

The Kubernetes Service Connector implements various authentication methods for
Kubernetes clusters.
"""
import base64
import subprocess
import tempfile
from typing import Any, List, Optional

from pydantic import Field, SecretStr

from zenml.exceptions import AuthorizationException
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

logger = get_logger(__name__)


class KubernetesServerCredentials(AuthenticationConfig):
    """Kubernetes server authentication config."""

    certificate_authority: SecretStr = Field(
        title="Kubernetes CA Certificate (base64 encoded)",
    )


class KubernetesServerConfig(KubernetesServerCredentials):
    """Kubernetes server config."""

    server: str = Field(
        title="Kubernetes Server URL",
    )
    insecure: bool = Field(
        default=False,
        title="Skip TLS verification for the server certificate",
    )


class KubernetesUserPasswordCredentials(AuthenticationConfig):
    """Kubernetes user/pass authentication config."""

    username: SecretStr = Field(
        title="Kubernetes Username",
    )
    password: SecretStr = Field(
        title="Kubernetes Password",
    )


class KubernetesBaseConfig(KubernetesServerConfig):
    """Kubernetes basic config."""

    cluster_name: str = Field(
        title="Kubernetes cluster name",
    )


class KubernetesUserPasswordConfig(
    KubernetesBaseConfig,
    KubernetesUserPasswordCredentials,
):
    """Kubernetes user/pass config."""


class KubernetesTokenCredentials(AuthenticationConfig):
    """Kubernetes token authentication config."""

    client_certificate: Optional[SecretStr] = Field(
        default=None,
        title="Kubernetes Client Certificate (base64 encoded)",
    )
    client_key: Optional[SecretStr] = Field(
        default=None,
        title="Kubernetes Client Key (base64 encoded)",
    )
    token: SecretStr = Field(
        title="Kubernetes Token",
    )


class KubernetesTokenConfig(KubernetesBaseConfig, KubernetesTokenCredentials):
    """Kubernetes token config."""


KUBERNETES_CONNECTOR_TYPE = "kubernetes"
KUBERNETES_RESOURCE_TYPE = "kubernetes"


class KubernetesAuthenticationMethods(StrEnum):
    """Kubernetes Authentication methods."""

    PASSWORD = "password"
    TOKEN = "token"


KUBERNETES_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="Kubernetes Service Connector",
    type=KUBERNETES_CONNECTOR_TYPE,
    description="""
This ZenML Kubernetes service connector facilitates authenticating and
connecting to a Kubernetes cluster.

The connector can be used to access to any generic Kubernetes cluster by
providing pre-authenticated Kubernetes python clients and also
allows configuration of local Kubernetes clients.
""",
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png",
    auth_methods=[
        AuthenticationMethodModel(
            name="Kubernetes Username and Password",
            auth_method=KubernetesAuthenticationMethods.PASSWORD,
            description="""
Use a username and password to authenticate to the Kubernetes cluster.
            
For production, it is recommended to use the Kubernetes Token
authentication method instead.
""",
            config_class=KubernetesUserPasswordConfig,
        ),
        AuthenticationMethodModel(
            name="Kubernetes Token",
            auth_method=KubernetesAuthenticationMethods.TOKEN,
            description="""
Use a token to authenticate to the Kubernetes cluster.
""",
            config_class=KubernetesTokenConfig,
        ),
    ],
    resource_types=[
        ResourceTypeModel(
            name="Kubernetes cluster",
            resource_type=KUBERNETES_RESOURCE_TYPE,
            description="""
Kubernetes cluster resource. When used by connector consumers, they are provided
a Kubernetes client pre-configured with AWS credentials.
""",
            auth_methods=KubernetesAuthenticationMethods.values(),
            # A Kubernetes connector instance is used to represent a single
            # Kubernetes cluster
            multi_instance=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png",
        ),
    ],
)


class KubernetesServiceConnector(ServiceConnector):
    """Kubernetes service connector."""

    config: KubernetesBaseConfig

    @classmethod
    def get_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector type specification.

        Returns:
            The service connector type specification.
        """
        return KUBERNETES_SERVICE_CONNECTOR_TYPE_SPEC

    def _canonical_resource_id(
        self, resource_type: str, resource_id: str
    ) -> str:
        """Convert a resource ID to its canonical form.

        Args:
            resource_type: The resource type to canonicalize.
            resource_id: The resource ID to canonicalize.

        Returns:
            The canonical resource ID.

        Raises:
            NotImplementedError: If multiple instances are not supported.
        """
        raise NotImplementedError(
            "A Kubernetes service connector instance can only be used to "
            "connect to a single cluster."
        )

    def _connect_to_resource(
        self,
        **kwargs: Any,
    ) -> Any:
        """Authenticate and connect to a Kubernetes cluster.

        Args:
            kwargs: Additional implementation specific keyword arguments to pass
                to the session or client constructor.

        Returns:
            A python-kubernetes client object.
        """
        from kubernetes import client as k8s_client

        cfg = self.config
        k8s_conf = k8s_client.Configuration()

        if self.auth_method == KubernetesAuthenticationMethods.PASSWORD:

            assert isinstance(cfg, KubernetesUserPasswordConfig)

            k8s_conf.username = cfg.username.get_secret_value()
            k8s_conf.password = cfg.password.get_secret_value()

        else:

            assert isinstance(cfg, KubernetesTokenConfig)

            k8s_conf.api_key["authorization"] = cfg.token.get_secret_value()
            k8s_conf.api_key_prefix["authorization"] = "Bearer"

            # TODO: client cert/key support

        k8s_conf.host = cfg.server

        ssl_ca_cert = cfg.certificate_authority.get_secret_value()
        cert_bs = base64.urlsafe_b64decode(ssl_ca_cert.encode("utf-8"))

        # TODO: choose a more secure location for the temporary file
        # and use the right permissions
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            fp.write(cert_bs)
            k8s_conf.ssl_ca_cert = fp.name

        return k8s_client.ApiClient(k8s_conf)

    def _configure_local_client(
        self,
        **kwargs: Any,
    ) -> None:
        """Configure a local Kubernetes client to authenticate and connect to a cluster.

        This method uses the connector's configuration to configure the local
        Kubernetes client (kubectl).

        Args:
            kwargs: Additional implementation specific keyword arguments to use
                to configure the client.

        Raises:
            AuthorizationException: If authentication failed.
            NotImplementedError: If the connector instance does not support
                local configuration for the configured resource type or
                authentication method.
        """
        cfg = self.config
        cluster_name = cfg.cluster_name

        if self.auth_method == KubernetesAuthenticationMethods.PASSWORD:

            assert isinstance(cfg, KubernetesUserPasswordConfig)

            username = cfg.username.get_secret_value()
            password = cfg.password.get_secret_value()

            add_user_cmd = [
                "kubectl",
                "config",
                "set-credentials",
                cluster_name,
                "--username",
                username,
                "--password",
                password,
            ]

        else:

            assert isinstance(cfg, KubernetesTokenConfig)

            token = cfg.token.get_secret_value()

            add_user_cmd = [
                "kubectl",
                "config",
                "set-credentials",
                cluster_name,
                "--token",
                token,
            ]

            # TODO: client cert/key support

        ssl_ca_cert = cfg.certificate_authority.get_secret_value()
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
                cluster_name,
                "--embed-certs",
                "--certificate-authority",
                ca_filename,
                "--server",
                cfg.server,
            ]
            add_context_cmd = [
                "kubectl",
                "config",
                "set-context",
                cluster_name,
                "--cluster",
                cluster_name,
                "--user",
                cluster_name,
            ]
            set_context_cmd = [
                "kubectl",
                "config",
                "use-context",
                cluster_name,
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
                    f"Failed to update local kubeconfig with the "
                    f"cluster configuration: {e}"
                ) from e
            logger.info(
                f"Updated local kubeconfig with the cluster details. "
                f"The current kubectl context was set to '{cluster_name}'."
            )

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        **kwargs: Any,
    ) -> "KubernetesServiceConnector":
        """Auto-configure the connector.

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
            A Kubernetes connector instance configured with authentication
            credentials automatically extracted from the environment.
        """
        raise NotImplementedError(
            "Auto-configuration of Kubernetes connectors is not supported."
        )

    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Verify that the connector can authenticate and connect.

        Args:
            resource_type: The type of resource to verify. Must be set to the
                Kubernetes resource type.
            resource_id: The ID of the resource to connect to. Not applicable
                to Kubernetes connectors.
        """
        from kubernetes import client as k8s_client

        client = self._connect_to_resource()
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

    def _list_resource_ids(
        self,
        resource_type: str,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """List the Kubernetes clusters that the connector can access.

        Args:
            resource_type: The type of the resources to list.
            resource_id: The ID of a particular resource to filter by.
        """
        raise NotImplementedError(
            "A Kubernetes service connector instance can only be used to "
            "connect to a single cluster."
        )
