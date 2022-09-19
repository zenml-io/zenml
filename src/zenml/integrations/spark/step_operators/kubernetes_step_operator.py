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
from typing import Any

from pyspark.conf import SparkConf

from zenml.config.docker_configuration import DockerConfiguration
from zenml.integrations.spark.step_operators import spark_entrypoint
from zenml.integrations.spark.step_operators.spark_step_operator import (
    SparkStepOperator,
)
from zenml.io.fileio import copy, remove
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.runtime_configuration import RuntimeConfiguration
from zenml.utils.pipeline_docker_image_builder import (
    DOCKER_IMAGE_WORKDIR,
    PipelineDockerImageBuilder,
)
from zenml.utils.source_utils import get_source_root_path

logger = get_logger(__name__)

LOCAL_ENTRYPOINT = spark_entrypoint.__file__
ENTRYPOINT_NAME = "zenml_spark_entrypoint.py"


class KubernetesSparkStepOperator(SparkStepOperator):
    """Step operator which runs Steps with Spark on Kubernetes."""

    @property
    def application_path(self) -> Any:
        """Provides the application path in the corresponding docker image.

        Returns:
            The path to the application entrypoint within the docker image
        """
        return f"local://{DOCKER_IMAGE_WORKDIR}/{ENTRYPOINT_NAME}"

    def _backend_configuration(
        self,
        spark_config: SparkConf,
        docker_configuration: "DockerConfiguration",
        pipeline_name: str,
    ) -> None:
        """Configures Spark to run on Kubernetes.

        This method will build and push a docker image for the drivers and
        executors and adjust the config accordingly.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            docker_configuration: the Docker configuration for this step
            pipeline_name: name of the pipeline which the step to be executed
                is part of

        Raises:
            FileExistsError: if the path where the entrypoint is copied to is
                already occupied
        """
        # Copy the entrypoint
        entrypoint_path = os.path.join(get_source_root_path(), ENTRYPOINT_NAME)

        try:
            copy(LOCAL_ENTRYPOINT, entrypoint_path, overwrite=False)
        except OSError:
            raise FileExistsError(
                f"The Kubernetes Spark step operator needs to copy the step "
                f"entrypoint to {entrypoint_path}, however a file with this "
                f"path already exists."
            )

        try:
            # Build and push the image
            docker_image_builder = PipelineDockerImageBuilder()
            image_name = docker_image_builder.build_and_push_docker_image(
                pipeline_name=pipeline_name,
                docker_configuration=docker_configuration,
                stack=Repository().active_stack,
                runtime_configuration=RuntimeConfiguration(),
            )
        finally:
            remove(entrypoint_path)

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
