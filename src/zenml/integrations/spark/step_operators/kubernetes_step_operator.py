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
import os
from typing import TYPE_CHECKING, Any, Optional, Tuple, cast

from pyspark.conf import SparkConf

from zenml.entrypoints import entrypoint
from zenml.enums import StackComponentType
from zenml.integrations.spark.flavors.spark_on_kubernetes_step_operator_flavor import (
    KubernetesSparkStepOperatorConfig,
)
from zenml.integrations.spark.step_operators.spark_step_operator import (
    SparkStepOperator,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.stack import Stack, StackValidator
from zenml.utils.pipeline_docker_image_builder import (
    DOCKER_IMAGE_WORKDIR,
    PipelineDockerImageBuilder,
)
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.config.step_configurations import StepConfiguration

logger = get_logger(__name__)

LOCAL_ENTRYPOINT = entrypoint.__file__
ENTRYPOINT_NAME = "zenml_spark_entrypoint.py"

SPARK_DOCKER_IMAGE_KEY = "spark_docker_image"


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
            required_components={StackComponentType.CONTAINER_REGISTRY},
            custom_validation_function=_validate_remote_components,
        )

    @property
    def application_path(self) -> Any:
        """Provides the application path in the corresponding docker image.

        Returns:
            The path to the application entrypoint within the docker image
        """
        return f"local://{DOCKER_IMAGE_WORKDIR}/{ENTRYPOINT_NAME}"

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> None:
        """Build a Docker image and push it to the container registry.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.

        Raises:
            FileExistsError: If the entrypoint file already exists.
        """
        steps_to_run = [
            step
            for step in deployment.steps.values()
            if step.config.step_operator == self.name
        ]
        if not steps_to_run:
            return

        entrypoint_path = os.path.join(get_source_root_path(), ENTRYPOINT_NAME)

        try:
            fileio.copy(LOCAL_ENTRYPOINT, entrypoint_path, overwrite=False)
        except OSError:
            raise FileExistsError(
                f"The Kubernetes Spark step operator needs to copy the step "
                f"entrypoint to {entrypoint_path}, however a file with this "
                f"path already exists."
            )

        try:
            # Build and push the image
            docker_image_builder = PipelineDockerImageBuilder()
            image_digest = docker_image_builder.build_and_push_docker_image(
                deployment=deployment, stack=stack
            )
        finally:
            fileio.remove(entrypoint_path)

        for step in steps_to_run:
            step.config.extra[SPARK_DOCKER_IMAGE_KEY] = image_digest

    def _backend_configuration(
        self,
        spark_config: SparkConf,
        step_config: "StepConfiguration",
    ) -> None:
        """Configures Spark to run on Kubernetes.

        This method will build and push a docker image for the drivers and
        executors and adjust the config accordingly.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            step_config: Configuration of the step to run.
        """
        docker_image = step_config.extra[SPARK_DOCKER_IMAGE_KEY]
        # Adjust the spark configuration
        spark_config.set("spark.kubernetes.container.image", docker_image)
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
