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
"""Seldon model deployer flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.seldon import SELDON_MODEL_DEPLOYER_FLAVOR
from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.seldon.model_deployers import SeldonModelDeployer


class SeldonModelDeployerConfig(BaseModelDeployerConfig):
    """Config for the Seldon Model Deployer.

    Attributes:
        kubernetes_context: the Kubernetes context to use to contact the remote
            Seldon Core installation. If not specified, the current
            configuration is used. Depending on where the Seldon model deployer
            is being used, this can be either a locally active context or an
            in-cluster Kubernetes configuration (if running inside a pod).
        kubernetes_namespace: the Kubernetes namespace where the Seldon Core
            deployment servers are provisioned and managed by ZenML. If not
            specified, the namespace set in the current configuration is used.
            Depending on where the Seldon model deployer is being used, this can
            be either the current namespace configured in the locally active
            context or the namespace in the context of which the pod is running
            (if running inside a pod).
        base_url: the base URL of the Kubernetes ingress used to expose the
            Seldon Core deployment servers.
        secret: the name of a ZenML secret containing the credentials used by
            Seldon Core storage initializers to authenticate to the Artifact
            Store (i.e. the storage backend where models are stored - see
            https://docs.seldon.io/projects/seldon-core/en/latest/servers/overview.html#handling-credentials).
    """

    kubernetes_context: Optional[str]  # TODO: Potential setting
    kubernetes_namespace: Optional[str]
    base_url: str  # TODO: unused?
    secret: Optional[str]


class SeldonModelDeployerFlavor(BaseModelDeployerFlavor):
    """Seldon Core model deployer flavor."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            The name of the flavor.
        """
        return SELDON_MODEL_DEPLOYER_FLAVOR

    @property
    def config_class(self) -> Type[SeldonModelDeployerConfig]:
        """Returns `SeldonModelDeployerConfig` config class.

        Returns:
                The config class.
        """
        return SeldonModelDeployerConfig

    @property
    def implementation_class(self) -> Type["SeldonModelDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.seldon.model_deployers import (
            SeldonModelDeployer,
        )

        return SeldonModelDeployer
