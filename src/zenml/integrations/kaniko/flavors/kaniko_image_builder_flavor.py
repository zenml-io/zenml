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

from pydantic import Field, PositiveInt

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
    """

    kubernetes_context: str = Field(
        ...,
        description="The Kubernetes context in which to run the Kaniko pod.",
    )
    kubernetes_namespace: str = Field(
        "zenml-kaniko",
        description="The Kubernetes namespace in which to run the Kaniko pod. "
        "This namespace will not be created and must already exist.",
    )
    executor_image: str = Field(
        DEFAULT_KANIKO_EXECUTOR_IMAGE,
        description="The image of the Kaniko executor to use for building container images.",
    )
    pod_running_timeout: PositiveInt = Field(
        DEFAULT_KANIKO_POD_RUNNING_TIMEOUT,
        description="The timeout to wait until the pod is running in seconds.",
    )

    env: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Environment variables section of the Kubernetes container spec. "
        "Used to configure secrets and environment variables for registry access.",
    )
    env_from: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="EnvFrom section of the Kubernetes container spec. "
        "Used to load environment variables from ConfigMaps or Secrets.",
    )
    volume_mounts: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="VolumeMounts section of the Kubernetes container spec. "
        "Used to mount volumes containing credentials or other data.",
    )
    volumes: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Volumes section of the Kubernetes pod spec. "
        "Used to define volumes for credentials or other data.",
    )
    service_account_name: Optional[str] = Field(
        None,
        description="Name of the Kubernetes service account to use for the Kaniko pod. "
        "This service account should have the necessary permissions for building and pushing images.",
    )

    store_context_in_artifact_store: bool = Field(
        False,
        description="If `True`, the build context will be stored in the artifact store. "
        "If `False`, the build context will be streamed over stdin of the kubectl process.",
    )

    executor_args: List[str] = Field(
        default_factory=list,
        description="Additional arguments to forward to the Kaniko executor. "
        "See Kaniko documentation for available flags, e.g. ['--compressed-caching=false'].",
    )


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
