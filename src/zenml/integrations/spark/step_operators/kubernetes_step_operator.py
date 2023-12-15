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
"""Implementation of the Kubernetes Spark Step Operator."""
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from pyspark.conf import SparkConf

from zenml.entrypoints import entrypoint
from zenml.enums import StackComponentType
from zenml.integrations.spark.flavors.spark_on_kubernetes_step_operator_flavor import (
    KubernetesSparkStepOperatorConfig,
)
from zenml.integrations.spark.step_operators.spark_step_operator import (
    SparkStepOperator,
)
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.utils.pipeline_docker_image_builder import (
    DOCKER_IMAGE_WORKDIR,
)

if TYPE_CHECKING:
    from zenml.config.build_configuration import BuildConfiguration
    from zenml.config.step_run_info import StepRunInfo
    from zenml.models import PipelineDeploymentBase

logger = get_logger(__name__)

LOCAL_ENTRYPOINT = entrypoint.__file__
ENTRYPOINT_NAME = "zenml_spark_entrypoint.py"

SPARK_DOCKER_IMAGE_KEY = "spark_step_operator"


class KubernetesSparkStepOperator(SparkStepOperator):
    """Step operator which runs Steps with Spark on Kubernetes."""

    @property
    def config(self) -> KubernetesSparkStepOperatorConfig:
        """Returns the `KubernetesSparkStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(KubernetesSparkStepOperatorConfig, self._config)

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        Returns:
            A validator that checks that the stack contains a remote container
            registry and a remote artifact store.
        """

        def _validate_remote_components(stack: "Stack") -> Tuple[bool, str]:
            if stack.artifact_store.config.is_local:
                return False, (
                    "The Spark step operator runs code remotely and "
                    "needs to write files into the artifact store, but the "
                    f"artifact store `{stack.artifact_store.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote artifact store when using the Spark "
                    "step operator."
                )

            container_registry = stack.container_registry
            assert container_registry is not None

            if container_registry.config.is_local:
                return False, (
                    "The Spark step operator runs code remotely and "
                    "needs to push/pull Docker images, but the "
                    f"container registry `{container_registry.name}` of the "
                    "active stack is local. Please ensure that your stack "
                    "contains a remote container registry when using the "
                    "Spark step operator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    @property
    def application_path(self) -> Any:
        """Provides the application path in the corresponding docker image.

        Returns:
            The path to the application entrypoint within the docker image
        """
        return f"local://{DOCKER_IMAGE_WORKDIR}/{ENTRYPOINT_NAME}"

    def get_docker_builds(
        self, deployment: "PipelineDeploymentBase"
    ) -> List["BuildConfiguration"]:
        """Gets the Docker builds required for the component.

        Args:
            deployment: The pipeline deployment for which to get the builds.

        Returns:
            The required Docker builds.
        """
        from zenml.config.build_configuration import BuildConfiguration

        builds = []
        extra_files = {ENTRYPOINT_NAME: LOCAL_ENTRYPOINT}
        for step_name, step in deployment.step_configurations.items():
            if step.config.step_operator == self.name:
                build = BuildConfiguration(
                    key=SPARK_DOCKER_IMAGE_KEY,
                    settings=step.config.docker_settings,
                    step_name=step_name,
                    extra_files=extra_files,
                )
                builds.append(build)

        return builds

    def _backend_configuration(
        self,
        spark_config: SparkConf,
        info: "StepRunInfo",
        environment: Dict[str, str],
    ) -> None:
        """Configures Spark to run on Kubernetes.

        This method will build and push a docker image for the drivers and
        executors and adjust the config accordingly.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            info: Information about the step run.
            environment: Environment variables to set in the executor
                environment.
        """
        image_name = info.get_image(key=SPARK_DOCKER_IMAGE_KEY)

        # Adjust the spark configuration
        spark_config.set("spark.kubernetes.container.image", image_name)
        if self.config.namespace:
            spark_config.set(
                "spark.kubernetes.namespace",
                self.config.namespace,
            )
        if self.config.service_account:
            spark_config.set(
                "spark.kubernetes.authenticate.driver.serviceAccountName",
                self.config.service_account,
            )

        for key, value in environment.items():
            spark_config.set(f"spark.executorEnv.{key}", value)
