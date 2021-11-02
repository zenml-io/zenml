#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.

import datetime
import os
import shutil
import sys
import time
from typing import TYPE_CHECKING, Any, Dict, Optional

import click
import tfx.orchestration.pipeline as tfx_pipeline
from pydantic import Field, root_validator

from zenml.constants import APP_NAME
from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.logger import get_logger
from zenml.orchestrators.airflow.airflow_dag_runner import (
    AirflowDagRunner,
    AirflowPipelineConfig,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.utils import daemon, path_utils

logger = get_logger(__name__)

if TYPE_CHECKING:
    import airflow

    from zenml.pipelines.base_pipeline import BasePipeline

AIRFLOW_ROOT_DIR = "airflow_root"


def default_airflow_home() -> str:
    """Returns a default airflow home in the global directory"""
    return os.path.join(click.get_app_dir(APP_NAME), AIRFLOW_ROOT_DIR)


@orchestrator_store_factory.register(OrchestratorTypes.airflow)
class AirflowOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Airflow."""

    airflow_home: str = Field(default_factory=default_airflow_home)
    airflow_config: Optional[Dict[str, Any]] = {}
    schedule_interval_minutes: int = 1

    def __init__(self, **values: Any):
        """Sets environment variables to configure airflow."""
        super().__init__(**values)
        self._set_env()

    @root_validator
    def set_airflow_home(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Sets airflow home according to orchestrator UUID."""
        if "uuid" not in values:
            raise ValueError("`uuid` needs to exist for AirflowOrchestrator.")
        values["airflow_home"] = os.path.join(
            click.get_app_dir(APP_NAME), AIRFLOW_ROOT_DIR, str(values["uuid"])
        )
        return values

    @property
    def dags_directory(self) -> str:
        """Returns path to the airflow dags directory."""
        return os.path.join(self.airflow_home, "dags")

    @property
    def pid_file(self) -> str:
        """Returns path to the daemon PID file."""
        return os.path.join(self.airflow_home, "airflow_daemon.pid")

    @property
    def log_file(self) -> str:
        """Returns path to the airflow log file."""
        return os.path.join(self.airflow_home, "airflow_orchestrator.log")

    @property
    def password_file(self) -> str:
        """Returns path to the webserver password file."""
        return os.path.join(self.airflow_home, "standalone_admin_password.txt")

    @property
    def is_running(self) -> bool:
        """Returns whether the airflow daemon is currently running."""
        from airflow.cli.commands.standalone_command import StandaloneCommand

        airflow_running = StandaloneCommand().is_ready()
        daemon_running = daemon.check_if_daemon_is_running(self.pid_file)

        return airflow_running and daemon_running

    def _set_env(self) -> None:
        """Sets environment variables to configure airflow."""
        os.environ["AIRFLOW_HOME"] = self.airflow_home
        os.environ["AIRFLOW__CORE__DAGS_FOLDER"] = self.dags_directory
        os.environ["AIRFLOW__CORE__DAG_DISCOVERY_SAFE_MODE"] = "false"

    def _copy_to_dag_directory_if_necessary(self):
        """Copies the __main__ module to the airflow DAGs directory if it's not
        already located there."""
        # TODO [HIGH]: This assumes the airflow DAG is in the __main__ module,
        #  not sure if that's a reasonable assumption. An alternative way of
        #  getting the file could be
        #   `filepath = inspect.currentframe().f_back.f_back.f_code.co_filename`
        dag_filepath = path_utils.resolve_relative_path(
            sys.modules["__main__"].__file__
        )
        dags_directory = path_utils.resolve_relative_path(self.dags_directory)

        if dags_directory == os.path.dirname(dag_filepath):
            logger.debug("File is already in airflow DAGs directory.")
        else:
            logger.debug(
                "Copying dag file '%s' to DAGs directory.", dag_filepath
            )
            destination_path = os.path.join(
                dags_directory, os.path.basename(dag_filepath)
            )
            if path_utils.file_exists(destination_path):
                logger.info(
                    "File '{%s}' already exists, overwriting with new DAG file",
                    destination_path,
                )
            shutil.copy2(dag_filepath, dags_directory)

    def _log_webserver_credentials(self):
        """Logs URL and credentials to login to the airflow webserver.

        Raises:
            FileNotFoundError: If the password file does not exist.
        """
        if path_utils.file_exists(self.password_file):
            with open(self.password_file) as file:
                password = file.read().strip()
        else:
            raise FileNotFoundError(
                f"Can't find password file '{self.password_file}'"
            )
        logger.info(
            "To inspect your DAGs, login to http://0.0.0.0:8080 "
            "with username: admin password: %s",
            password,
        )

    def pre_run(self) -> None:
        """Checks whether airflow is running and copies the DAG file to the
        airflow DAGs directory.

        Raises:
            RuntimeError: If airflow is not running.
        """
        if not self.is_running:
            raise RuntimeError(
                "Airflow orchestrator is currently not running. "
                "Run `zenml orchestrator up` to start the "
                "orchestrator of the active stack."
            )

        self._copy_to_dag_directory_if_necessary()

    def up(self) -> None:
        """Ensures that Airflow is running."""
        if self.is_running:
            logger.info("Airflow is already running.")
            self._log_webserver_credentials()
            return

        if not path_utils.file_exists(self.dags_directory):
            path_utils.create_dir_recursive_if_not_exists(self.dags_directory)

        from airflow.cli.commands.standalone_command import StandaloneCommand

        command = StandaloneCommand()
        daemon.run_as_daemon(command.run, self.pid_file, self.log_file)

        while not self.is_running:
            # Wait until the daemon started all the relevant airflow processes
            time.sleep(0.1)

        self._log_webserver_credentials()

    def down(self) -> None:
        """Stops the airflow daemon if necessary and tears down resources."""
        if self.is_running:
            daemon.stop_daemon(self.pid_file, kill_children=True)

        path_utils.rm_dir(self.airflow_home)
        logger.info("Airflow spun down.")

    def run(
        self,
        zenml_pipeline: "BasePipeline",
        run_name: Optional[str] = None,
        **kwargs: Any,
    ) -> "airflow.DAG":
        """Prepares the pipeline so it can be run in Airflow.

        Args:
            zenml_pipeline: The pipeline to run.
            run_name: Optional name for the run.
            **kwargs: Unused argument to conform with base class signature.
        """
        # TODO [HIGH]: set the run name
        self.airflow_config = {
            "schedule_interval": datetime.timedelta(
                minutes=self.schedule_interval_minutes
            ),
            # We set this in the past and turn catchup off and then it works
            "start_date": datetime.datetime(2019, 1, 1),
        }

        runner = AirflowDagRunner(AirflowPipelineConfig(self.airflow_config))

        # Establish the connections between the components
        zenml_pipeline.connect(**zenml_pipeline.steps)

        # Create the final step list and the corresponding pipeline
        steps = [s.component for s in zenml_pipeline.steps.values()]

        artifact_store = zenml_pipeline.stack.artifact_store
        metadata_store = zenml_pipeline.stack.metadata_store

        created_pipeline = tfx_pipeline.Pipeline(
            pipeline_name=zenml_pipeline.name,
            components=steps,  # type: ignore[arg-type]
            pipeline_root=artifact_store.path,
            metadata_connection_config=metadata_store.get_tfx_metadata_config(),
            enable_cache=zenml_pipeline.enable_cache,
        )

        return runner.run(created_pipeline)
