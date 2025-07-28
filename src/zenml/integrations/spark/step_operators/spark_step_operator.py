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

import subprocess
from typing import TYPE_CHECKING, Dict, List, Optional, Type, cast

from pyspark.conf import SparkConf

from zenml.client import Client
from zenml.integrations.spark.flavors.spark_step_operator_flavor import (
    SparkStepOperatorConfig,
    SparkStepOperatorSettings,
)
from zenml.integrations.spark.step_operators.spark_entrypoint_configuration import (
    SparkEntrypointConfiguration,
)
from zenml.logger import get_logger
from zenml.step_operators import BaseStepOperator

logger = get_logger(__name__)
if TYPE_CHECKING:
    from zenml.config import ResourceSettings
    from zenml.config.base_settings import BaseSettings
    from zenml.config.step_run_info import StepRunInfo


class SparkStepOperator(BaseStepOperator):
    """Base class for all Spark-related step operators."""

    @property
    def config(self) -> SparkStepOperatorConfig:
        """Returns the `SparkStepOperatorConfig` config.

        Returns:
            The configuration.
        """
        return cast(SparkStepOperatorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Spark step operator.

        Returns:
            The settings class.
        """
        return SparkStepOperatorSettings

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

    def _resource_configuration(
        self,
        spark_config: SparkConf,
        resource_settings: "ResourceSettings",
    ) -> None:
        """Configures Spark to handle the resource settings.

        This should serve as the layer between our ResourceSettings
        and Spark's own ways of configuring its resources.

        Note: This is still work-in-progress. In the future, we would like to
        enable much more than executor cores and memory with a dedicated
        ResourceSettings object.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            resource_settings: the resource settings for this step
        """
        if resource_settings.cpu_count:
            spark_config.set(
                "spark.executor.cores",
                str(int(resource_settings.cpu_count)),
            )

        if resource_settings.memory:
            # TODO[LOW]: Fix the conversion of the memory unit with a new
            #   type of resource configuration.
            spark_config.set(
                "spark.executor.memory",
                resource_settings.memory.lower().strip("b"),
            )

    def _backend_configuration(
        self,
        spark_config: SparkConf,
        info: "StepRunInfo",
        environment: Dict[str, str],
    ) -> None:
        """Configures Spark to handle backends like YARN, Mesos or Kubernetes.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            info: Information about the step run.
            environment: Environment variables to set.
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
        client = Client()
        artifact_store = client.active_stack.artifact_store

        from zenml.integrations.s3 import S3_ARTIFACT_STORE_FLAVOR

        # If S3, preconfigure the spark session
        if artifact_store.flavor == S3_ARTIFACT_STORE_FLAVOR:
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
                f"'{artifact_store.flavor}' featured in this stack is not "
                f"known to this step operator and it might require additional "
                f"configuration."
            )

    def _additional_configuration(
        self, spark_config: SparkConf, settings: SparkStepOperatorSettings
    ) -> None:
        """Appends the user-defined configuration parameters.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            settings: Step operator settings for the current step run.
        """
        # Add the additional parameters
        if settings.submit_kwargs:
            for k, v in settings.submit_kwargs.items():
                spark_config.set(k, v)

    def _launch_spark_job(
        self,
        spark_config: SparkConf,
        deploy_mode: str,
        entrypoint_command: List[str],
    ) -> None:
        """Generates and executes a spark-submit command.

        Args:
            spark_config: a SparkConf object which collects all the
                configuration parameters
            deploy_mode: The spark deploy mode to use.
            entrypoint_command: The entrypoint command to run.

        Raises:
            RuntimeError: if the spark-submit fails
        """
        # Base spark-submit command
        command = [
            f"spark-submit "
            f"--master {self.config.master} "
            f"--deploy-mode {deploy_mode}"
        ]

        # Add the configuration parameters
        command += [f"--conf {c[0]}={c[1]}" for c in spark_config.getAll()]

        # Add the application path
        command.append(self.application_path)  # type: ignore[arg-type]

        # Update the default step operator command to use the spark entrypoint
        # configuration
        original_args = SparkEntrypointConfiguration._parse_arguments(
            entrypoint_command
        )
        command += SparkEntrypointConfiguration.get_entrypoint_arguments(
            **original_args
        )

        final_command = " ".join(command)

        # Execute the spark-submit
        process = subprocess.Popen(
            final_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            shell=True,  # nosec
        )
        stdout, stderr = process.communicate()

        if process.returncode != 0:
            raise RuntimeError(stderr)
        print(stdout)

    def launch(
        self,
        info: "StepRunInfo",
        entrypoint_command: List[str],
        environment: Dict[str, str],
    ) -> None:
        """Launches a step on Spark.

        Args:
            info: Information about the step run.
            entrypoint_command: Command that executes the step.
            environment: Environment variables to set in the step operator
                environment.
        """
        settings = cast(SparkStepOperatorSettings, self.get_settings(info))
        # Start off with an empty configuration
        conf = SparkConf()

        # Add the resource configuration such as cores, memory.
        self._resource_configuration(
            spark_config=conf,
            resource_settings=info.config.resource_settings,
        )

        # Add the backend configuration such as namespace, docker images names.
        self._backend_configuration(
            spark_config=conf, info=info, environment=environment
        )

        # Add the IO configuration for the inputs and the outputs
        self._io_configuration(
            spark_config=conf,
        )

        # Add any additional configuration given by the user.
        self._additional_configuration(spark_config=conf, settings=settings)

        info.force_write_logs()

        # Generate a spark-submit command given the configuration
        self._launch_spark_job(
            spark_config=conf,
            deploy_mode=settings.deploy_mode,
            entrypoint_command=entrypoint_command,
        )
