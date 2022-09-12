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
"""Implementation of the Spark Step Operator."""

import json
import subprocess
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from pydantic import validator
from pyspark.conf import SparkConf

from zenml.config.docker_configuration import DockerConfiguration
from zenml.logger import get_logger
from zenml.repository import Repository
from zenml.step_operators import BaseStepOperator

logger = get_logger(__name__)
if TYPE_CHECKING:
    from zenml.config.resource_configuration import ResourceConfiguration


class SparkStepOperator(BaseStepOperator):
    """Base class for all Spark-related step operators.

    Attributes:
        master: is the master URL for the cluster. You might see different
            schemes for different cluster managers which are supported by Spark
            like Mesos, YARN, or Kubernetes. Within the context of this PR,
            the implementation supports Kubernetes as a cluster manager.
        deploy_mode: can either be 'cluster' (default) or 'client' and it
            decides where the driver node of the application will run.
        submit_kwargs: is the JSON string of a dict, which will be used
            to define additional params if required (Spark has quite a
            lot of different parameters, so including them, all in the step
            operator was not implemented).
    """

    # Instance parameters
    master: str
    deploy_mode: str = "cluster"
    submit_kwargs: Optional[Dict[str, Any]] = None

    @property
    def application_path(self) -> Optional[str]:
        """Optional method for providing the application path.

        This is especially critical when using 'spark-submit' as it defines the
        path (to the application in the environment where Spark is running)
        which is used within the command.

        For more information on how to set this property please check:

        https://spark.apache.org/docs/latest/submitting-applications.html#advanced-dependency-management

        Returns:
            The path to the application entrypoint
        """
        return None

    @validator("submit_kwargs", pre=True)
    def _convert_json_string(
        cls, value: Union[None, str, Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Converts potential JSON strings passed via the CLI to dictionaries.

        Args:
            value: The value to convert.

        Returns:
            The converted value.

        Raises:
            TypeError: If the value is not a `str`, `Dict` or `None`.
            ValueError: If the value is an invalid json string or a json string
                that does not decode into a dictionary.
        """
        if isinstance(value, str):
            try:
                dict_ = json.loads(value)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid json string '{value}'") from e

            if not isinstance(dict_, Dict):
                raise ValueError(
                    f"Json string '{value}' did not decode into a dictionary."
                )

            return dict_
        elif isinstance(value, Dict) or value is None:
            return value
        else:
            raise TypeError(f"{value} is not a json string or a dictionary.")

    def _resource_configuration(
        self,
        spark_config: SparkConf,
        resource_configuration: "ResourceConfiguration",
    ) -> None:
        """Configures Spark to handle the resource configuration.

        This should serve as the layer between our ResourceConfigurations
        and Spark's own ways of configuring its resources.

        Note: This is still work-in-progress. In the future, we would like to
        enable much more than executor cores and memory with a dedicated
        ResourceConfiguration object.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            resource_configuration: the resource configuration for this step
        """
        if resource_configuration.cpu_count:
            spark_config.set(
                "spark.executor.cores",
                str(int(resource_configuration.cpu_count)),
            )

        if resource_configuration.memory:
            # TODO[LOW]: Fix the conversion of the memory unit with a new
            #   type of resource configuration.
            spark_config.set(
                "spark.executor.memory",
                resource_configuration.memory.lower().strip("b"),
            )

    def _backend_configuration(
        self,
        spark_config: SparkConf,
        docker_configuration: "DockerConfiguration",
        pipeline_name: str,
    ) -> None:
        """Configures Spark to handle backends like YARN, Mesos or Kubernetes.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            pipeline_name: name of the pipeline which the step to be executed
                is part of
            docker_configuration: the Docker configuration for this step
        """

    def _io_configuration(self, spark_config: SparkConf) -> None:
        """Configures Spark to handle different input/output sources.

        When you work with the Spark integration, you get materializers
        such as SparkDataFrameMaterializer, SparkModelMaterializer. However, in
        many cases, these materializer work only if the environment, where
        Spark is running, is configured according to the artifact store.

        Take s3 as an example. When you want to save a dataframe to an S3
        artifact store, you need to provide configuration parameters such as,
        '"spark.hadoop.fs.s3.impl=org.apache.hadoop.fs.s3a.S3AFileSystem" to
        Spark. This method aims to provide these configuration parameters.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters

        Raises:
            RuntimeError: when the step operator is being used with an S3
                artifact store and the artifact store does not have the
                required authentication
        """
        # Get active artifact store
        repo = Repository()
        artifact_store = repo.active_stack.artifact_store

        from zenml.integrations.s3 import S3_ARTIFACT_STORE_FLAVOR

        # If S3, preconfigure the spark session
        if artifact_store.FLAVOR == S3_ARTIFACT_STORE_FLAVOR:
            (
                key,
                secret,
                _,
            ) = artifact_store._get_credentials()  # type:ignore[attr-defined]
            if key and secret:
                spark_config.setAll(
                    [
                        ("spark.hadoop.fs.s3a.fast.upload", "true"),
                        (
                            "spark.hadoop.fs.s3.impl",
                            "org.apache.hadoop.fs.s3a.S3AFileSystem",
                        ),
                        (
                            "spark.hadoop.fs.AbstractFileSystem.s3.impl",
                            "org.apache.hadoop.fs.s3a.S3A",
                        ),
                        (
                            "spark.hadoop.fs.s3a.aws.credentials.provider",
                            "com.amazonaws.auth.DefaultAWSCredentialsProviderChain",
                        ),
                        ("spark.hadoop.fs.s3a.access.key", f"{key}"),
                        ("spark.hadoop.fs.s3a.secret.key", f"{secret}"),
                    ]
                )
            else:
                raise RuntimeError(
                    "When you use an Spark step operator with an S3 artifact "
                    "store, please make sure that your artifact store has"
                    "defined the required credentials namely the access key "
                    "and the secret access key."
                )
        else:
            logger.warning(
                "In most cases, the Spark step operator requires additional "
                "configuration based on the artifact store flavor you are "
                "using. That also means, that when you use this step operator "
                "with certain artifact store flavor, ZenML can take care of "
                "the pre-configuration. However, the artifact store flavor "
                f"'{artifact_store.FLAVOR}' featured in this stack is not "
                f"known to this step operator and it might require additional "
                f"configuration."
            )

    def _additional_configuration(self, spark_config: SparkConf) -> None:
        """Appends the user-defined configuration parameters.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
        """
        # Add the additional parameters
        if self.submit_kwargs:
            for k, v in self.submit_kwargs.items():
                spark_config.set(k, v)

    def _launch_spark_job(
        self, spark_config: SparkConf, entrypoint_command: List[str]
    ) -> None:
        """Generates and executes a spark-submit command.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            entrypoint_command: a list of strings which is normally used to
                execute the step as a module. However, in the context of this
                step operator, this list is used to form the application
                parameters for spark-submit.

        Raises:
            RuntimeError: if the spark-submit fails
        """
        # Base spark-submit command
        command = [
            f"spark-submit "
            f"--master {self.master} "
            f"--deploy-mode {self.deploy_mode}"
        ]

        # Add the configuration parameters
        command += [f"--conf {c[0]}={c[1]}" for c in spark_config.getAll()]

        # Add the application path
        command.append(self.application_path)  # type: ignore[arg-type]

        # Add the application parameters
        for arg in [
            "--main_module",
            "--step_source_path",
            "--execution_info_path",
            "--input_artifact_types_path",
        ]:
            i = entrypoint_command.index(arg)
            command.extend([arg, entrypoint_command[i + 1]])

        final_command = " ".join(command)

        # Execute the spark-submit
        process = subprocess.Popen(
            final_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True,
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            raise RuntimeError(stderr)
        print(stdout)

    def launch(
        self,
        pipeline_name: str,
        run_name: str,
        docker_configuration: "DockerConfiguration",
        entrypoint_command: List[str],
        resource_configuration: "ResourceConfiguration",
    ) -> None:
        """Launches the step on Spark.

        Args:
            pipeline_name: Name of the pipeline which the step to be executed
                is part of.
            run_name: Name of the pipeline run which the step to be executed
                is part of.
            docker_configuration: The Docker configuration for this step.
            entrypoint_command: Command that executes the step.
            resource_configuration: The resource configuration for this step.
        """
        # Start off with an empty configuration
        conf = SparkConf()

        # Add the resource configuration such as cores, memory.
        self._resource_configuration(
            spark_config=conf,
            resource_configuration=resource_configuration,
        )

        # Add the backend configuration such as namespace, docker images names.
        self._backend_configuration(
            spark_config=conf,
            docker_configuration=docker_configuration,
            pipeline_name=pipeline_name,
        )

        # Add the IO configuration for the inputs and the outputs
        self._io_configuration(
            spark_config=conf,
        )

        # Add any additional configuration given by the user.
        self._additional_configuration(
            spark_config=conf,
        )

        # Generate a spark-submit command given the configuration
        self._launch_spark_job(
            spark_config=conf,
            entrypoint_command=entrypoint_command,
        )
