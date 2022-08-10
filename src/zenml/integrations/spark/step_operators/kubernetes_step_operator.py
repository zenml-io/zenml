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
import json
import os
from typing import (
    ClassVar, List, Optional, Union,
    TYPE_CHECKING, Sequence
)

from pydantic import validator
from pyspark.conf import SparkConf

from zenml.config.docker_configuration import DockerConfiguration
from zenml.integrations.spark import SPARK_KUBERNETES_STEP_OPERATOR
from zenml.integrations.spark.step_operators.spark_step_operator import \
    SparkStepOperator
from zenml.io.fileio import copy
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.runtime_configuration import RuntimeConfiguration
from zenml.step_operators import entrypoint
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder
from zenml.utils.source_utils import get_source_root_path

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

LOCAL_ENTRYPOINT = entrypoint.__file__
APP_DIR = "/app/"
CONTAINER_ZENML_CONFIG_DIR = ".zenconfig"
ENTRYPOINT_NAME = "zenml_spark_entrypoint.py"


class KubernetesSparkStepOperator(
    SparkStepOperator, PipelineDockerImageBuilder
    ):
    """
    MAIN DOCS
    """
    # Parameters for kubernetes
    kubernetes_namespace: Optional[str] = None
    kubernetes_service_account: Optional[str] = None

    # Class configuration
    FLAVOR: ClassVar[str] = SPARK_KUBERNETES_STEP_OPERATOR

    @staticmethod
    def _generate_zenml_pipeline_dockerfile(  # TODO: To be removed
        parent_image: str,
        docker_configuration: DockerConfiguration,
        requirements_files: Sequence[str] = (),
        entrypoint: Optional[str] = None,
    ) -> List[str]:
        dockerfile = PipelineDockerImageBuilder._generate_zenml_pipeline_dockerfile(
            parent_image,
            docker_configuration,
            requirements_files,
            entrypoint,
        )
        return [dockerfile[0]] + [
            "USER root",  # required to install the requirements
            "RUN apt-get -y update",
            "RUN apt-get -y install git",
        ] + dockerfile[1:]

    def _backend_configuration(
        self,
        spark_config: SparkConf,
        docker_configuration: "DockerConfiguration",
        pipeline_name: str,
    ) -> None:
        """Configures Spark to run on Kubernetes.

        This method will build and push a docker image for the drivers and
        executors and adjust the config accordingly.

        spark_config: a SparkConf object which collects all the
                configuration parameters
        docker_configuration: The Docker configuration for this step.
        pipeline_name: Name of the pipeline which the step to be executed
                is part of.
        """
        # Copy the entrypoint
        entrypoint_path = os.path.join(
            get_source_root_path(),
            ENTRYPOINT_NAME
        )
        copy(LOCAL_ENTRYPOINT, entrypoint_path, overwrite=True)

        # Build and push the image
        image_name = self.build_and_push_docker_image(
            pipeline_name=pipeline_name,
            docker_configuration=docker_configuration,
            stack=Repository().active_stack,
            runtime_configuration=RuntimeConfiguration(),
        )

        # Adjust the spark configuration
        spark_config.set(
            "spark.kubernetes.container.image", image_name
        )
        if self.kubernetes_namespace:
            spark_config.set(
                "spark.kubernetes.namespace", self.kubernetes_namespace,

            )
        if self.kubernetes_service_account:
            spark_config.set(
                "spark.kubernetes.authenticate.driver.serviceAccountName",
                self.kubernetes_service_account
            )
