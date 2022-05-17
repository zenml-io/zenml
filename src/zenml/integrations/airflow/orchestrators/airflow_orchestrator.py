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

import datetime
import functools
import os
import time
from typing import TYPE_CHECKING, Any, ClassVar, Dict, List, Optional

from pydantic import root_validator
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline

import zenml.io.utils
from zenml.integrations.airflow import AIRFLOW_ORCHESTRATOR_FLAVOR
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import BaseOrchestrator
from zenml.pipelines import Schedule
from zenml.steps import BaseStep
from zenml.utils import daemon
from zenml.utils.source_utils import get_source_root_path

logger = get_logger(__name__)

if TYPE_CHECKING:
    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack

AIRFLOW_ROOT_DIR = "airflow_root"
DAG_FILEPATH_OPTION_KEY = "dag_filepath"


class AirflowOrchestrator(BaseOrchestrator):
    """Orchestrator responsible for running pipelines using Airflow."""

    airflow_home: str = ""

    # Class Configuration
    FLAVOR: ClassVar[str] = AIRFLOW_ORCHESTRATOR_FLAVOR

    def __init__(self, **values: Any):
        """Sets environment variables to configure airflow."""
        super().__init__(**values)
        self._set_env()

    @staticmethod
    def _translate_schedule(
        schedule: Optional[Schedule] = None,
    ) -> Dict[str, Any]:
        """Convert ZenML schedule into airflow schedule which uses slightly
        different naming and needs some default entries for execution without a
        schedule.

        Args:
            schedule: Containing the interval, start and end date and
                a boolean flag that defines if past runs should be caught up
                on
        Returns:
            Airflow configuration dict.
        """
        if schedule:
            return {
                "schedule_interval": schedule.interval_second,
                "start_date": schedule.start_time,
                "end_date": schedule.end_time,
                "catchup": schedule.catchup,
            }
        return {
            "schedule_interval": "@once",
            # set the a start time in the past and disable catchup so airflow runs the dag immediately
            "start_date": datetime.datetime.now() - datetime.timedelta(7),
            "catchup": False,
        }

    def prepare_or_run_pipeline(
        self,
        sorted_steps: List[BaseStep],
        pipeline: "BasePipeline",
        pb2_pipeline: Pb2Pipeline,
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> Any:
        """Create an airflow dag as the intermediate representation for the
        pipeline. This dag will be loaded by airflow in the target environment
        and used for orchestration of the pipeline.

        How it works:
        -------------
        A new airflow_dag is instantiated with the pipeline name and among
        others things the run schedule.

        For each step of the pipeline a callable is created. This callable
        uses the run_step() method to execute the step. The parameters of
        this callable are pre-filled and an airflow step_operator is created
        within the dag. The dependencies to upstream steps are then
        configured.

        Finally, the dag is fully complete and can be returned.
        """

        import airflow
        from airflow.operators import python as airflow_python

        # Instantiate and configure airflow Dag with name and schedule
        airflow_dag = airflow.DAG(
            dag_id=pipeline.name,
            is_paused_upon_creation=False,
            **self._translate_schedule(runtime_configuration.schedule),
        )

        # Dictionary mapping step names to airflow_operators. This will be needed
        # to configure airflow operator dependencies
        step_name_to_airflow_operator = {}

        for step in sorted_steps:
            # Create callable that will be used by airflow to execute the step
            # within the orchestrated environment
            def _step_callable(step_instance: "BaseStep", **kwargs):
                # Extract run name for the kwargs that will be passed to the
                # callable
                run_name = kwargs["ti"].get_dagrun().run_id
                self.run_step(
                    step=step_instance,
                    run_name=run_name,
                    pb2_pipeline=pb2_pipeline,
                )

            # Create airflow python operator that contains the step callable
            airflow_operator = airflow_python.PythonOperator(
                dag=airflow_dag,
                task_id=step.name,
                provide_context=True,
                python_callable=functools.partial(
                    _step_callable, step_instance=step
                ),
            )

            # Configure the current airflow operator to run after all upstream
            # operators finished executing
            step_name_to_airflow_operator[step.name] = airflow_operator
            upstream_step_names = self.get_upstream_step_names(
                step=step, pb2_pipeline=pb2_pipeline
            )
            for upstream_step_name in upstream_step_names:
                airflow_operator.set_upstream(
                    step_name_to_airflow_operator[upstream_step_name]
                )

        # Return the finished airflow dag
        return airflow_dag

    @root_validator(skip_on_failure=True)
    def set_airflow_home(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Sets airflow home according to orchestrator UUID."""
        if "uuid" not in values:
            raise ValueError("`uuid` needs to exist for AirflowOrchestrator.")
        values["airflow_home"] = os.path.join(
            zenml.io.utils.get_global_config_directory(),
            AIRFLOW_ROOT_DIR,
            str(values["uuid"]),
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

    def _set_env(self) -> None:
        """Sets environment variables to configure airflow."""
        os.environ["AIRFLOW_HOME"] = self.airflow_home
        os.environ["AIRFLOW__CORE__DAGS_FOLDER"] = self.dags_directory
        os.environ["AIRFLOW__CORE__DAG_DISCOVERY_SAFE_MODE"] = "false"
        os.environ["AIRFLOW__CORE__LOAD_EXAMPLES"] = "false"
        # check the DAG folder every 10 seconds for new files
        os.environ["AIRFLOW__SCHEDULER__DAG_DIR_LIST_INTERVAL"] = "10"

    def _copy_to_dag_directory_if_necessary(self, dag_filepath: str) -> None:
        """Copies the DAG module to the airflow DAGs directory if it's not
        already located there.

        Args:
            dag_filepath: Path to the file in which the DAG is defined.
        """
        dags_directory = zenml.io.utils.resolve_relative_path(
            self.dags_directory
        )

        if dags_directory == os.path.dirname(dag_filepath):
            logger.debug("File is already in airflow DAGs directory.")
        else:
            logger.debug(
                "Copying dag file '%s' to DAGs directory.", dag_filepath
            )
            destination_path = os.path.join(
                dags_directory, os.path.basename(dag_filepath)
            )
            if fileio.exists(destination_path):
                logger.info(
                    "File '%s' already exists, overwriting with new DAG file",
                    destination_path,
                )
            fileio.copy(dag_filepath, destination_path, overwrite=True)

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
            "To inspect your DAGs, login to http://0.0.0.0:8080 "
            "with username: admin password: %s",
            password,
        )

    def runtime_options(self) -> Dict[str, Any]:
        """Runtime options for the airflow orchestrator."""
        return {DAG_FILEPATH_OPTION_KEY: None}

    def prepare_pipeline_deployment(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> None:
        """Checks whether airflow is running and copies the DAG file to the
        airflow DAGs directory.

        Raises:
            RuntimeError: If airflow is not running or no DAG filepath runtime
                          option is provided.
        """
        if not self.is_running:
            raise RuntimeError(
                "Airflow orchestrator is currently not running. Run `zenml "
                "stack up` to provision resources for the active stack."
            )

        try:
            dag_filepath = runtime_configuration[DAG_FILEPATH_OPTION_KEY]
        except KeyError:
            raise RuntimeError(
                f"No DAG filepath found in runtime configuration. Make sure "
                f"to add the filepath to your airflow DAG file as a runtime "
                f"option (key: '{DAG_FILEPATH_OPTION_KEY}')."
            )

        self._copy_to_dag_directory_if_necessary(dag_filepath=dag_filepath)

    @property
    def is_running(self) -> bool:
        """Returns whether the airflow daemon is currently running."""
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
        """Returns whether the airflow daemon is currently running."""
        return self.is_running

    def provision(self) -> None:
        """Ensures that Airflow is running."""
        if self.is_running:
            logger.info("Airflow is already running.")
            self._log_webserver_credentials()
            return

        if not fileio.exists(self.dags_directory):
            zenml.io.utils.create_dir_recursive_if_not_exists(
                self.dags_directory
            )

        from airflow.cli.commands.standalone_command import StandaloneCommand

        try:
            command = StandaloneCommand()
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
