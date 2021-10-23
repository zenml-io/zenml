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
from typing import TYPE_CHECKING, Any, Dict, Optional

import click
import psutil
import tfx.orchestration.pipeline as tfx_pipeline
from pydantic import Field, PrivateAttr, root_validator

from zenml.constants import APP_NAME
from zenml.core.component_factory import orchestrator_store_factory
from zenml.enums import OrchestratorTypes
from zenml.logger import get_logger
from zenml.orchestrators.airflow.airflow_dag_runner import (
    AirflowDagRunner,
    AirflowPipelineConfig,
)
from zenml.orchestrators.base_orchestrator import BaseOrchestrator
from zenml.utils import path_utils

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
    pid: Optional[int] = None
    _commander: Optional[Any] = PrivateAttr()

    def __init__(self, **values: Any):
        """Intiailizes the AirflowCommander for the duration of this objects
        existence. Also makes sure env variables are set."""
        super().__init__(**values)
        self._set_env()
        from zenml.orchestrators.airflow.zenml_standalone_command import (
            AirflowCommander,
        )

        self._commander = AirflowCommander()

    @root_validator
    def set_airflow_home(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        if "uuid" not in values:
            raise ValueError("`uuid` needs to exist for AirflowOrchestrator.")
        values["airflow_home"] = os.path.join(
            click.get_app_dir(APP_NAME), AIRFLOW_ROOT_DIR, str(values["uuid"])
        )
        return values

    def _set_env(self) -> None:
        os.environ["AIRFLOW_HOME"] = self.airflow_home
        os.environ["AIRFLOW__CORE__DAGS_FOLDER"] = os.getcwd()
        os.environ["AIRFLOW__CORE__DAG_DISCOVERY_SAFE_MODE"] = "false"

    def is_bootstrapped(self) -> bool:
        """Return True if airflow already bootstrapped, else return False"""
        if path_utils.file_exists(
            os.path.join(self.airflow_home, "airflow.db")
        ):
            logger.info(f"airflow.db already exists at {self.airflow_home}")
            return True
        else:
            return False

    def bootstrap_airflow(self) -> None:
        """Starts Airflow with the standalone command."""
        self._commander.bootstrap()

    def pre_run(self) -> None:
        """Bootstraps Airflow if not done so, and then makes sure its up."""
        self.up()

    def up(self) -> None:
        """This should ensure that Airflow is running."""
        if self._commander.is_ready():
            # If its already up, then go back
            logger.info("Airflow is already up.")
            return

        path_utils.create_dir_recursive_if_not_exists(self.airflow_home)
        logger.info(f"Setting up Airflow at: {self.airflow_home}")
        if not self.is_bootstrapped():
            # Bootstrap airflow if not already done so.
            self.bootstrap_airflow()

        # Now we can run it as its bootstrapped.
        self._commander.up()
        logger.info("Airflow is now up.")

        # Store our own pid for future termination
        self.pid = os.getpid()

        # Persist
        self.update()

    def down(self) -> None:
        """Tears down resources for Airflow. Stops running processes."""
        if self._commander.subcommands:
            # if the _commander state has the subcommands then use them
            self._commander.down()
        else:
            # kill the up process's pid and all children
            if self.pid:
                if psutil.pid_exists(self.pid):  # needs to exist
                    parent = psutil.Process(self.pid)
                    if parent.name() == APP_NAME:
                        # only kill if the thread is called 'zenml'
                        for child in parent.children(recursive=True):
                            child.kill()
                        parent.kill()

        # At this point, we want to reset pids
        self.pid = None
        self.update()

        # Delete the rest
        path_utils.rm_dir(self.airflow_home)
        logger.info("Airflow spun down.")

    def run(
        self, zenml_pipeline: "BasePipeline", **kwargs: Any
    ) -> "airflow.DAG":
        """Prepares the pipeline so it can be run in Airflow.

        Args:
            zenml_pipeline: The pipeline to run.
            **kwargs: Unused argument to conform with base class signature.
        """
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
