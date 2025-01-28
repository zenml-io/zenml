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
import os
import subprocess
import tempfile
from typing import Any, List, Optional

from kubernetes import client as k8s_client
from kubernetes import config as k8s_config
from pydantic import Field
from urllib3.exceptions import HTTPError

from zenml.constants import KUBERNETES_CLUSTER_RESOURCE_TYPE
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
from zenml.utils.secret_utils import PlainSerializedSecretStr

logger = get_logger(__name__)


class KubernetesServerCredentials(AuthenticationConfig):
    """Kubernetes server authentication config."""

    certificate_authority: Optional[PlainSerializedSecretStr] = Field(
        default=None,
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

    username: PlainSerializedSecretStr = Field(
        title="Kubernetes Username",
    )
    password: PlainSerializedSecretStr = Field(
        title="Kubernetes Password",
    )


class KubernetesBaseConfig(KubernetesServerConfig):
    """Kubernetes basic config."""

    cluster_name: str = Field(
        title="Kubernetes cluster name to be used in the kubeconfig file",
    )


class KubernetesUserPasswordConfig(
    KubernetesBaseConfig,
    KubernetesUserPasswordCredentials,
):
    """Kubernetes user/pass config."""


class KubernetesTokenCredentials(AuthenticationConfig):
    """Kubernetes token authentication config."""

    client_certificate: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        title="Kubernetes Client Certificate (base64 encoded)",
    )
    client_key: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        title="Kubernetes Client Key (base64 encoded)",
    )
    token: Optional[PlainSerializedSecretStr] = Field(
        default=None,
        title="Kubernetes Token",
    )


class KubernetesTokenConfig(KubernetesBaseConfig, KubernetesTokenCredentials):
    """Kubernetes token config."""


KUBERNETES_CONNECTOR_TYPE = "kubernetes"


class KubernetesAuthenticationMethods(StrEnum):
    """Kubernetes Authentication methods."""

    PASSWORD = "password"
    TOKEN = "token"


KUBERNETES_SERVICE_CONNECTOR_TYPE_SPEC = ServiceConnectorTypeModel(
    name="Kubernetes Service Connector",
    connector_type=KUBERNETES_CONNECTOR_TYPE,
    description="""
This ZenML Kubernetes service connector facilitates authenticating and
connecting to a Kubernetes cluster.

The connector can be used to access to any generic Kubernetes cluster by
providing pre-authenticated Kubernetes python clients to Stack Components that
are linked to it and also allows configuring the local Kubernetes CLI
(i.e. `kubectl`).

The Kubernetes Service Connector is part of the Kubernetes ZenML integration.
You can either install the entire integration or use a pypi extra to install it
independently of the integration:

* `pip install "zenml[connectors-kubernetes]"` installs only prerequisites for the
Kubernetes Service Connector Type
* `zenml integration install kubernetes` installs the entire Kubernetes ZenML
integration

A local Kubernetes CLI (i.e. `kubectl` ) and setting up local kubectl
configuration contexts is not required to access Kubernetes clusters in your
Stack Components through the Kubernetes Service Connector.
""",
    supports_auto_configuration=True,
    logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png",
    emoji=":cyclone:",
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
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
            description="""
Kubernetes cluster resource. When used by connector consumers, they are provided
a Kubernetes client pre-configured with credentials required to access a
Kubernetes cluster.
""",
            auth_methods=KubernetesAuthenticationMethods.values(),
            # A Kubernetes connector instance is used to represent a single
            # Kubernetes cluster.
            supports_instances=False,
            logo_url="https://public-flavor-logos.s3.eu-central-1.amazonaws.com/orchestrator/kubernetes.png",
            emoji=":cyclone:",
        ),
    ],
)


class KubernetesServiceConnector(ServiceConnector):
    """Kubernetes service connector."""

    config: KubernetesBaseConfig

    @classmethod
    def _get_connector_type(cls) -> ServiceConnectorTypeModel:
        """Get the service connector type specification.

        Returns:
            The service connector type specification.
        """
        return KUBERNETES_SERVICE_CONNECTOR_TYPE_SPEC

    def _get_default_resource_id(self, resource_type: str) -> str:
        """Get the default resource ID for a resource type.

        Service connector implementations must override this method and provide
        a default resource ID for resources that do not support multiple
        instances.

        Args:
            resource_type: The type of the resource to get a default resource ID
                for. Only called with resource types that do not support
                multiple instances.

        Returns:
            The default resource ID for the resource type.
        """
        # We use the cluster name as the default resource ID.
        return self.config.cluster_name

    @classmethod
    def _write_to_temp_file(cls, content: bytes) -> str:
        """Write content to a secured temporary file.

        Write content to a temporary file that is readable and writable only by
        the creating user ID and return the path to the temporary file.

        Args:
            content: The content to write to the temporary file.

        Returns:
            The path to the temporary file.
        """
        fd, temp_path = tempfile.mkstemp()
        fp = os.fdopen(fd, "wb")
        try:
            fp.write(content)
            fp.flush()
        finally:
            fp.close()

        return temp_path

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
        cfg = self.config
        k8s_conf = k8s_client.Configuration()

        if self.auth_method == KubernetesAuthenticationMethods.PASSWORD:
            assert isinstance(cfg, KubernetesUserPasswordConfig)

            k8s_conf.username = cfg.username.get_secret_value()
            k8s_conf.password = cfg.password.get_secret_value()

        else:
            assert isinstance(cfg, KubernetesTokenConfig)

            if cfg.token:
                k8s_conf.api_key["authorization"] = (
                    cfg.token.get_secret_value()
                )
                k8s_conf.api_key_prefix["authorization"] = "Bearer"

            if cfg.client_certificate is not None:
                client_cert = cfg.client_certificate.get_secret_value()
                client_cert_bs = base64.urlsafe_b64decode(
                    client_cert.encode("utf-8")
                )

                k8s_conf.cert_file = self._write_to_temp_file(client_cert_bs)

            if cfg.client_key is not None:
                client_key = cfg.client_key.get_secret_value()
                client_key_bs = base64.urlsafe_b64decode(
                    client_key.encode("utf-8")
                )

                k8s_conf.key_file = self._write_to_temp_file(client_key_bs)

        k8s_conf.host = cfg.server

        if cfg.certificate_authority is not None:
            ssl_ca_cert = cfg.certificate_authority.get_secret_value()
            cert_bs = base64.urlsafe_b64decode(ssl_ca_cert.encode("utf-8"))

            k8s_conf.ssl_ca_cert = self._write_to_temp_file(cert_bs)

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
        """
        cfg = self.config
        cluster_name = cfg.cluster_name
        delete_files: List[str] = []

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

            add_user_cmd = [
                "kubectl",
                "config",
                "set-credentials",
                cluster_name,
            ]

            if cfg.token:
                token = cfg.token.get_secret_value()
                add_user_cmd += [
                    "--token",
                    token,
                ]

            if cfg.client_certificate and cfg.client_key:
                add_user_cmd += [
                    "--embed-certs",
                ]

                client_cert = cfg.client_certificate.get_secret_value()
                client_cert_bs = base64.urlsafe_b64decode(
                    client_cert.encode("utf-8")
                )

                temp_path = self._write_to_temp_file(client_cert_bs)
                add_user_cmd += [
                    "--client-certificate",
                    temp_path,
                ]
                delete_files.append(temp_path)

                client_key = cfg.client_key.get_secret_value()
                client_key_bs = base64.urlsafe_b64decode(
                    client_key.encode("utf-8")
                )

                temp_path = self._write_to_temp_file(client_key_bs)
                add_user_cmd += [
                    "--client-key",
                    temp_path,
                ]
                delete_files.append(temp_path)

        # add the cluster config to the default kubeconfig
        add_cluster_cmd = [
            "kubectl",
            "config",
            "set-cluster",
            cluster_name,
            "--server",
            cfg.server,
        ]

        if cfg.certificate_authority:
            ssl_ca_cert = cfg.certificate_authority.get_secret_value()
            cert_bs = base64.urlsafe_b64decode(ssl_ca_cert.encode("utf-8"))

            temp_path = self._write_to_temp_file(cert_bs)
            add_cluster_cmd += [
                "--embed-certs",
                "--certificate-authority",
                temp_path,
            ]
            delete_files.append(temp_path)

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

        # delete the temporary files
        for f in delete_files:
            os.unlink(f)

    @classmethod
    def _auto_configure(
        cls,
        auth_method: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        kubernetes_context: Optional[str] = None,
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
            kubernetes_context: The name of the Kubernetes context to use. If
                not specified, the active context will be used.
            kwargs: Additional implementation specific keyword arguments to use.

        Returns:
            A configured Kubernetes connector instance.

        Raises:
            AuthorizationException: If the connector could not be configured.
        """
        kube_config = k8s_client.Configuration()
        try:
            k8s_config.load_kube_config(
                context=kubernetes_context,
                client_configuration=kube_config,
            )
        except k8s_config.ConfigException as e:
            raise AuthorizationException(
                f"Failed to load the Kubernetes configuration: {e}"
            ) from e

        auth_config: KubernetesBaseConfig
        if kube_config.username and kube_config.password:
            auth_method = KubernetesAuthenticationMethods.PASSWORD
            auth_config = KubernetesUserPasswordConfig(
                username=kube_config.username,
                password=kube_config.password,
                server=kube_config.host,
                certificate_authority=base64.urlsafe_b64encode(
                    open(kube_config.ssl_ca_cert, "rb").read()
                ).decode("utf-8")
                if kube_config.ssl_ca_cert
                else None,
                cluster_name=kube_config.host.strip("https://").split(":")[0],
                insecure=kube_config.verify_ssl is False,
            )
        else:
            token: Optional[str] = None
            if kube_config.api_key:
                token = kube_config.api_key["authorization"].strip("Bearer ")

            auth_method = KubernetesAuthenticationMethods.TOKEN
            auth_config = KubernetesTokenConfig(
                token=token,
                server=kube_config.host,
                certificate_authority=base64.urlsafe_b64encode(
                    open(kube_config.ssl_ca_cert, "rb").read()
                ).decode("utf-8"),
                client_certificate=base64.urlsafe_b64encode(
                    open(kube_config.cert_file, "rb").read()
                ).decode("utf-8")
                if kube_config.cert_file
                else None,
                client_key=base64.urlsafe_b64encode(
                    open(kube_config.key_file, "rb").read()
                ).decode("utf-8")
                if kube_config.key_file
                else None,
                cluster_name=kube_config.host.strip("https://").split(":")[0],
                insecure=kube_config.verify_ssl is False,
            )

        return cls(
            auth_method=auth_method,
            resource_type=KUBERNETES_CLUSTER_RESOURCE_TYPE,
            config=auth_config,
        )

    def _verify(
        self,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
    ) -> List[str]:
        """Verify and list all the resources that the connector can access.

        Args:
            resource_type: The type of resource to verify. Always set to the
                Kubernetes resource type.
            resource_id: The ID of the resource to connect to. Always set to
                the Kubernetes cluster name.

        Returns:
            The list of canonical resource IDs that the connector can access,
            meaning only the Kubernetes cluster name.

        Raises:
            AuthorizationException: If the connector cannot authenticate or
                access the Kubernetes cluster API.
        """
        assert resource_id is not None

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
        except (k8s_client.ApiException, HTTPError) as err:
            raise AuthorizationException(
                f"failed to verify Kubernetes cluster access: {err}"
            ) from err

        return [resource_id]
