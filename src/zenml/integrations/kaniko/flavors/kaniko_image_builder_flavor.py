#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Kaniko image builder flavor."""

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Type

from pydantic import PositiveInt

from zenml.image_builders import BaseImageBuilderConfig, BaseImageBuilderFlavor
from zenml.integrations.kaniko import KANIKO_IMAGE_BUILDER_FLAVOR

if TYPE_CHECKING:
    from zenml.integrations.kaniko.image_builders import KanikoImageBuilder


KANIKO_EXECUTOR_IMAGE_TAG = "v1.9.1"
DEFAULT_KANIKO_EXECUTOR_IMAGE = (
    f"gcr.io/kaniko-project/executor:{KANIKO_EXECUTOR_IMAGE_TAG}"
)
DEFAULT_KANIKO_POD_RUNNING_TIMEOUT = 300


class KanikoImageBuilderConfig(BaseImageBuilderConfig):
    """Kaniko image builder configuration.

    The `env`, `env_from`, `volume_mounts` and `volumes` attributes will be
    used to generate the container specification. They should be used to
    configure secrets and environment variables so that the Kaniko build
    container is able to push to the container registry (and optionally access
    the artifact store to upload the build context).

    Attributes:
        kubernetes_context: The Kubernetes context in which to run the Kaniko
            pod.
        kubernetes_namespace: The Kubernetes namespace in which to run the
            Kaniko pod. This namespace will not be created and must already
            exist.
        executor_image: The image of the Kaniko executor to use.
        pod_running_timeout: The timeout to wait until the pod is running
            in seconds. Defaults to `300`.
        env: `env` section of the Kubernetes container spec.
        env_from: `envFrom` section of the Kubernetes container spec.
        volume_mounts: `volumeMounts` section of the Kubernetes container spec.
        volumes: `volumes` section of the Kubernetes pod spec.
        service_account_name: Name of the Kubernetes service account to use.
        store_context_in_artifact_store: If `True`, the build context will be
            stored in the artifact store. If `False`, the build context will be
            streamed over stdin of the `kubectl` process that runs the build.
            In case the artifact store is used, the container running the build
            needs read access to the artifact store.
        executor_args: Additional arguments to forward to the Kaniko executor.
            See https://github.com/GoogleContainerTools/kaniko#additional-flags
            for a full list of available arguments.
            Example: `["--compressed-caching=false"]`

    """

    kubernetes_context: str
    kubernetes_namespace: str = "zenml-kaniko"
    executor_image: str = DEFAULT_KANIKO_EXECUTOR_IMAGE
    pod_running_timeout: PositiveInt = DEFAULT_KANIKO_POD_RUNNING_TIMEOUT

    env: List[Dict[str, Any]] = []
    env_from: List[Dict[str, Any]] = []
    volume_mounts: List[Dict[str, Any]] = []
    volumes: List[Dict[str, Any]] = []
    service_account_name: Optional[str] = None

    store_context_in_artifact_store: bool = False

    executor_args: List[str] = []


class KanikoImageBuilderFlavor(BaseImageBuilderFlavor):
    """Kaniko image builder flavor."""

    @property
    def name(self) -> str:
        """The flavor name.

        Returns:
            The flavor name.
        """
        return KANIKO_IMAGE_BUILDER_FLAVOR

    @property
    def docs_url(self) -> Optional[str]:
        """A url to point at docs explaining this flavor.

        Returns:
            A flavor docs url.
        """
        return self.generate_default_docs_url()

    @property
    def sdk_docs_url(self) -> Optional[str]:
        """A url to point at SDK docs explaining this flavor.

        Returns:
            A flavor SDK docs url.
        """
        return self.generate_default_sdk_docs_url()

    @property
    def logo_url(self) -> str:
        """A url to represent the flavor in the dashboard.

        Returns:
            The flavor logo.
        """
        return "https://public-flavor-logos.s3.eu-central-1.amazonaws.com/image_builder/kaniko.png"

    @property
    def config_class(self) -> Type[KanikoImageBuilderConfig]:
        """Config class.

        Returns:
            The config class.
        """
        return KanikoImageBuilderConfig

    @property
    def implementation_class(self) -> Type["KanikoImageBuilder"]:
        """Implementation class.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kaniko.image_builders import KanikoImageBuilder

        return KanikoImageBuilder
