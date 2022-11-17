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
"""KServe model deployer flavor."""

from typing import TYPE_CHECKING, Optional, Type

from zenml.integrations.kserve import KSERVE_MODEL_DEPLOYER_FLAVOR
from zenml.model_deployers.base_model_deployer import (
    BaseModelDeployerConfig,
    BaseModelDeployerFlavor,
)

if TYPE_CHECKING:
    from zenml.integrations.kserve.model_deployers import KServeModelDeployer


class KServeModelDeployerConfig(BaseModelDeployerConfig):
    """Configuration for the KServeModelDeployer.

    Attributes:
        kubernetes_context: the Kubernetes context to use to contact the remote
            KServe installation. If not specified, the current
            configuration is used. Depending on where the KServe model deployer
            is being used, this can be either a locally active context or an
            in-cluster Kubernetes configuration (if running inside a pod).
        kubernetes_namespace: the Kubernetes namespace where the KServe
            inference service CRDs are provisioned and managed by ZenML. If not
            specified, the namespace set in the current configuration is used.
            Depending on where the KServe model deployer is being used, this can
            be either the current namespace configured in the locally active
            context or the namespace in the context of which the pod is running
            (if running inside a pod).
        base_url: the base URL of the Kubernetes ingress used to expose the
            KServe inference services.
        secret: the name of the secret containing the credentials for the
            KServe inference services.
    """

    kubernetes_context: Optional[str]  # TODO: Potential setting
    kubernetes_namespace: Optional[str]
    base_url: str  # TODO: unused?
    secret: Optional[str]
    custom_domain: Optional[str]  # TODO: unused?


class KServeModelDeployerFlavor(BaseModelDeployerFlavor):
    """Flavor for the KServe model deployer."""

    @property
    def name(self) -> str:
        """Name of the flavor.

        Returns:
            Name of the flavor.
        """
        return KSERVE_MODEL_DEPLOYER_FLAVOR

    @property
    def config_class(self) -> Type[KServeModelDeployerConfig]:
        """Returns `KServeModelDeployerConfig` config class.

        Returns:
                The config class.
        """
        return KServeModelDeployerConfig

    @property
    def implementation_class(self) -> Type["KServeModelDeployer"]:
        """Implementation class for this flavor.

        Returns:
            The implementation class.
        """
        from zenml.integrations.kserve.model_deployers import (
            KServeModelDeployer,
        )

        return KServeModelDeployer
