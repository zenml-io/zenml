# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

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

# Minor parts of the  `prepare_or_run_pipeline()` method of this file are
# inspired by the airflow dag runner implementation of tfx
"""Implementation of Airflow orchestrator integration."""

import os
import time
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any, Iterator, Optional, Type

from zenml.constants import (
    ENV_ZENML_SKIP_PIPELINE_REGISTRATION,
    ORCHESTRATOR_DOCKER_IMAGE_KEY,
)
from zenml.integrations.airflow.flavors.airflow_orchestrator_flavor import (
    REQUIRES_LOCAL_STORES,
    AirflowOrchestratorSettings,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.utils import daemon, io_utils
from zenml.utils.pipeline_docker_image_builder import PipelineDockerImageBuilder
from zenml.utils.source_utils import get_source_root_path

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.config.base_settings import BaseSettings
    from zenml.config.pipeline_deployment import PipelineDeployment
    from zenml.stack import Stack

AIRFLOW_ROOT_DIR = "airflow"


@contextmanager
def set_environment_variable(key: str, value: str) -> Iterator[None]:
    """Temporarily sets an environment variable.

    The value will only be set while this context manager is active and will
    be reset to the previous value afterward.

    Args:
        key: The environment variable key.
        value: The environment variable value.

    Yields:
        None.
    """
    old_value = os.environ.get(key, None)
    try:
        os.environ[key] = value
        yield
    finally:
        if old_value:
            os.environ[key] = old_value
        else:
            del os.environ[key]


class AirflowOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Airflow."""

    def __init__(self, **values: Any):
        """Sets environment variables to configure airflow.

        Args:
            **values: Values to set in the orchestrator.
        """
        super().__init__(**values)
        self.airflow_home = os.path.join(
            io_utils.get_global_config_directory(),
            AIRFLOW_ROOT_DIR,
            str(self.id),
        )
        self._set_env()

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Kubeflow orchestrator.

        Returns:
            The settings class.
        """
        return AirflowOrchestratorSettings

    @property
    def dags_directory(self) -> str:
        """Returns path to the airflow dags directory.

        Returns:
            Path to the airflow dags directory.
        """
        return os.path.join(self.airflow_home, "dags")

    @property
    def pid_file(self) -> str:
        """Returns path to the daemon PID file.

        Returns:
            Path to the daemon PID file.
        """
        return os.path.join(self.airflow_home, "airflow_daemon.pid")

    @property
    def log_file(self) -> str:
        """Returns path to the airflow log file.

        Returns:
            str: Path to the airflow log file.
        """
        return os.path.join(self.airflow_home, "airflow_orchestrator.log")

    @property
    def password_file(self) -> str:
        """Returns path to the webserver password file.

        Returns:
            Path to the webserver password file.
        """
        return os.path.join(self.airflow_home, "standalone_admin_password.txt")

    def _set_env(self) -> None:
        """Sets environment variables to configure airflow."""
        os.environ["AIRFLOW_HOME"] = self.airflow_home
        os.environ["AIRFLOW__CORE__DAGS_FOLDER"] = self.dags_directory
        os.environ["AIRFLOW__CORE__DAG_DISCOVERY_SAFE_MODE"] = "false"
        os.environ["AIRFLOW__CORE__LOAD_EXAMPLES"] = "false"
        # check the DAG folder every 10 seconds for new files
        os.environ["AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL"] = "10"

    # def _copy_to_dag_directory_if_necessary(self, dag_filepath: str) -> None:
    #     """Copies DAG module to the Airflow DAGs directory if not already present.

    #     Args:
    #         dag_filepath: Path to the file in which the DAG is defined.
    #     """
    #     dags_directory = io_utils.resolve_relative_path(self.dags_directory)

    #     if dags_directory == os.path.dirname(dag_filepath):
    #         logger.debug("File is already in airflow DAGs directory.")
    #     else:
    #         logger.debug(
    #             "Copying dag file '%s' to DAGs directory.", dag_filepath
    #         )
    #         destination_path = os.path.join(
    #             dags_directory, os.path.basename(dag_filepath)
    #         )
    #         if fileio.exists(destination_path):
    #             logger.info(
    #                 "File '%s' already exists, overwriting with new DAG file",
    #                 destination_path,
    #             )
    #         fileio.copy(dag_filepath, destination_path, overwrite=True)

    def _log_webserver_credentials(self) -> None:
        """Logs URL and credentials to log in to the airflow webserver.

        Raises:
            FileNotFoundError: If the password file does not exist.
        """
        if fileio.exists(self.password_file):
            with open(self.password_file) as file:
                password = file.read().strip()
        else:
            raise FileNotFoundError(
                f"Can't find password file '{self.password_file}'"
            )
        logger.info(
            "To inspect your DAGs, login to http://localhost:8080 "
            "with username: admin password: %s",
            password,
        )

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> None:
        """Checks Airflow is running and copies DAG file to the DAGs directory.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.

        Raises:
            RuntimeError: If Airflow is not running or no DAG filepath runtime
                          option is provided.
        """
        if not self.is_running:
            raise RuntimeError(
                "Airflow orchestrator is currently not running. Run `zenml "
                "stack up` to provision resources for the active stack."
            )

        if self.is_local:
            stack.check_local_paths()
            deployment.add_extra(REQUIRES_LOCAL_STORES, True)

        docker_image_builder = PipelineDockerImageBuilder()
        if stack.container_registry:
            repo_digest = docker_image_builder.build_and_push_docker_image(
                deployment=deployment, stack=stack
            )
            deployment.add_extra(ORCHESTRATOR_DOCKER_IMAGE_KEY, repo_digest)
        else:
            # If there is no container registry, we only build the image
            target_image_name = docker_image_builder.get_target_image_name(
                deployment=deployment
            )
            docker_image_builder.build_docker_image(
                target_image_name=target_image_name,
                deployment=deployment,
                stack=stack,
            )
            deployment.add_extra(
                ORCHESTRATOR_DOCKER_IMAGE_KEY, target_image_name
            )

    @property
    def is_local(self) -> bool:
        return True

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeployment",
        stack: "Stack",
    ) -> Any:
        zenml_dags_dir = os.path.join(self.dags_directory, "zenml")
        yaml_path = os.path.join(
            zenml_dags_dir, f"{deployment.pipeline.name}.yaml"
        )
        io_utils.create_dir_recursive_if_not_exists(zenml_dags_dir)
        with fileio.open(yaml_path, "w") as f:
            f.write(deployment.yaml())

        from zenml.integrations.airflow.orchestrators import dag_generator

        dag_generator_path = os.path.join(
            self.dags_directory, "zenml_dag_generator.py"
        )
        fileio.copy(dag_generator.__file__, dag_generator_path)

    @property
    def is_running(self) -> bool:
        """Returns whether the airflow daemon is currently running.

        Returns:
            True if the daemon is running, False otherwise.

        Raises:
            RuntimeError: If port 8080 is occupied.
        """
        from airflow.cli.commands.standalone_command import StandaloneCommand
        from airflow.jobs.triggerer_job import TriggererJob

        daemon_running = daemon.check_if_daemon_is_running(self.pid_file)

        command = StandaloneCommand()
        webserver_port_open = command.port_open(8080)

        if not daemon_running:
            if webserver_port_open:
                raise RuntimeError(
                    "The airflow daemon does not seem to be running but "
                    "local port 8080 is occupied. Make sure the port is "
                    "available and try again."
                )

            # exit early so we don't check non-existing airflow databases
            return False

        # we can't use StandaloneCommand().is_ready() here as the
        # Airflow SequentialExecutor apparently does not send a heartbeat
        # while running a task which would result in this returning `False`
        # even if Airflow is running.
        airflow_running = webserver_port_open and command.job_running(
            TriggererJob
        )
        return airflow_running

    @property
    def is_provisioned(self) -> bool:
        """Returns whether the airflow daemon is currently running.

        Returns:
            True if the airflow daemon is running, False otherwise.
        """
        return self.is_running

    def provision(self) -> None:
        """Ensures that Airflow is running."""
        if self.is_running:
            logger.info("Airflow is already running.")
            self._log_webserver_credentials()
            return

        if not fileio.exists(self.dags_directory):
            io_utils.create_dir_recursive_if_not_exists(self.dags_directory)

        from airflow.cli.commands.standalone_command import StandaloneCommand

        try:
            command = StandaloneCommand()
            # Skip pipeline registration inside the airflow server process.
            # When searching for DAGs, airflow imports the runner file in a
            # randomly generated module. If we don't skip pipeline registration,
            # it would fail by trying to register a pipeline with an existing
            # name but different module sources for the steps.
            with set_environment_variable(
                key=ENV_ZENML_SKIP_PIPELINE_REGISTRATION, value="True"
            ):
                # Run the daemon with a working directory inside the current
                # zenml repo so the same repo will be used to run the DAGs
                daemon.run_as_daemon(
                    command.run,
                    pid_file=self.pid_file,
                    log_file=self.log_file,
                    working_directory=get_source_root_path(),
                )
            while not self.is_running:
                # Wait until the daemon started all the relevant airflow
                # processes
                time.sleep(0.1)
            self._log_webserver_credentials()
        except Exception as e:
            logger.error(e)
            logger.error(
                "An error occurred while starting the Airflow daemon. If you "
                "want to start it manually, use the commands described in the "
                "official Airflow quickstart guide for running Airflow locally."
            )
            self.deprovision()

    def deprovision(self) -> None:
        """Stops the airflow daemon if necessary and tears down resources."""
        if self.is_running:
            daemon.stop_daemon(self.pid_file)

        fileio.rmtree(self.airflow_home)
        logger.info("Airflow spun down.")
