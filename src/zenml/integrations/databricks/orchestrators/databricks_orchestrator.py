#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Implementation of the Databricks orchestrator."""

import itertools
import os
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast
from uuid import UUID

from databricks.sdk import WorkspaceClient as DatabricksClient
from databricks.sdk.service.compute import (
    AutoScale,
    ClientsTypes,
    ClusterSpec,
    WorkloadType,
)
from databricks.sdk.service.jobs import CronSchedule, JobCluster
from databricks.sdk.service.jobs import Task as DatabricksTask

from zenml.client import Client
from zenml.constants import METADATA_ORCHESTRATOR_URL
from zenml.integrations.databricks.flavors.databricks_orchestrator_flavor import (
    DatabricksOrchestratorConfig,
    DatabricksOrchestratorSettings,
)
from zenml.integrations.databricks.orchestrators.databricks_orchestrator_entrypoint_config import (
    ENV_ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID,
    DatabricksEntrypointConfiguration,
)
from zenml.integrations.databricks.utils.databricks_utils import (
    convert_step_to_task,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType, Uri
from zenml.models.v2.core.schedule import ScheduleResponse
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.orchestrators.wheeled_orchestrator import WheeledOrchestrator
from zenml.stack import StackValidator
from zenml.utils import io_utils
from zenml.utils.pipeline_docker_image_builder import (
    PipelineDockerImageBuilder,
)

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse
    from zenml.stack import Stack


logger = get_logger(__name__)

ZENML_STEP_DEFAULT_ENTRYPOINT_COMMAND = "entrypoint.main"
DATABRICKS_WHEELS_DIRECTORY_PREFIX = "dbfs:/FileStore/zenml"
DATABRICKS_LOCAL_FILESYSTEM_PREFIX = "file:/"
DATABRICKS_CLUSTER_DEFAULT_NAME = "zenml-databricks-cluster"
DATABRICKS_SPARK_DEFAULT_VERSION = "15.3.x-scala2.12"
DATABRICKS_JOB_ID_PARAMETER_REFERENCE = "{{job.id}}"


class DatabricksOrchestrator(WheeledOrchestrator):
    """Base class for Orchestrator responsible for running pipelines remotely in a VM.

    This orchestrator does not support running on a schedule.
    """

    # The default instance type to use if none is specified in settings
    DEFAULT_INSTANCE_TYPE: Optional[str] = None

    @property
    def validator(self) -> Optional[StackValidator]:
        """Validates the stack.

        In the remote case, checks that the stack contains a container registry,
        image builder and only remote components.

        Returns:
            A `StackValidator` instance.
        """

        def _validate_remote_components(
            stack: "Stack",
        ) -> Tuple[bool, str]:
            for component in stack.components.values():
                continue  # TODO: Remove this line
                if not component.config.is_local:
                    continue

                return False, (
                    f"The Databricks orchestrator runs pipelines remotely, "
                    f"but the '{component.name}' {component.type.value} is "
                    "a local stack component and will not be available in "
                    "the Databricks step.\nPlease ensure that you always "
                    "use non-local stack components with the Databricks "
                    "orchestrator."
                )

            return True, ""

        return StackValidator(
            custom_validation_function=_validate_remote_components,
        )

    def _get_databricks_client(
        self,
    ) -> DatabricksClient:
        """Creates a Databricks client.

        Returns:
            The Databricks client.
        """
        return DatabricksClient(
            host=self.config.host,
            client_id=self.config.client_id,
            client_secret=self.config.client_secret,
        )

    @property
    def config(self) -> DatabricksOrchestratorConfig:
        """Returns the `DatabricksOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(DatabricksOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Type[DatabricksOrchestratorSettings]:
        """Settings class for the Databricks orchestrator.

        Returns:
            The settings class.
        """
        return DatabricksOrchestratorSettings

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If no run id exists. This happens when this method
                gets called while the orchestrator is not running a pipeline.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If the run id cannot be read from the environment.
        """
        try:
            return os.environ[ENV_ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID}."
            )

    @property
    def root_directory(self) -> str:
        """Path to the root directory for all files concerning this orchestrator.

        Returns:
            Path to the root directory.
        """
        return os.path.join(
            io_utils.get_global_config_directory(),
            "databricks",
            str(self.id),
        )

    @property
    def pipeline_directory(self) -> str:
        """Returns path to a directory in which the kubeflow pipeline files are stored.

        Returns:
            Path to the pipeline directory.
        """
        return os.path.join(self.root_directory, "pipelines")

    def setup_credentials(self) -> None:
        """Set up credentials for the orchestrator."""
        connector = self.get_connector()
        assert connector is not None
        connector.configure_local_client()

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> Any:
        """Creates a wheel and uploads the pipeline to Databricks.

        This functions as an intermediary representation of the pipeline which
        is then deployed to the kubeflow pipelines instance.

        How it works:
        -------------
        Before this method is called the `prepare_pipeline_deployment()`
        method builds a docker image that contains the code for the
        pipeline, all steps the context around these files.

        Based on this docker image a callable is created which builds
        task for each step (`_construct_databricks_pipeline`).
        To do this the entrypoint of the docker image is configured to
        run the correct step within the docker image. The dependencies
        between these task are then also configured onto each
        task by pointing at the downstream steps.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            RuntimeError: If trying to run a pipeline in a notebook
                environment.
            ValueError: If the schedule is not set or if the cron expression
                is not set.
        """
        if deployment.schedule:
            if (
                deployment.schedule.catchup
                or deployment.schedule.interval_second
            ):
                logger.warning(
                    "Databricks orchestrator only uses schedules with the "
                    "`cron_expression` property, with optional `start_time` and/or `end_time`. "
                    "All other properties are ignored."
                )
            if deployment.schedule.cron_expression is None:
                raise ValueError(
                    "Property `cron_expression` must be set when passing "
                    "schedule to a Databricks orchestrator."
                )
            if (
                deployment.schedule.cron_expression
                and self.settings_class().schedule_timezone is None
            ):
                raise ValueError(
                    "Property `schedule_timezone` must be set when passing "
                    "`cron_expression` to a Databricks orchestrator."
                    "Databricks orchestrator requires a Java Timezone ID to run the pipeline on schedule."
                    "Please refer to https://docs.oracle.com/middleware/1221/wcs/tag-ref/MISC/TimeZones.html for more information."
                )

        # Get deployment id
        deployment_id = deployment.id

        # Create a callable for future compilation into a dsl.Pipeline.
        def _construct_databricks_pipeline(
            zenml_project_wheel: str, job_cluster_key: str
        ) -> List[DatabricksTask]:
            """Create a databrcks task for each step.

            This should contain the name of the step or task and configures the
            entrypoint of the task to run the step.

            Additionally, this gives each task information about its
            direct downstream steps.

            Args:
                zenml_project_wheel: The wheel package containing the ZenML
                    project.
                job_cluster_key: The ID of the Databricks job cluster.

            Returns:
                A list of Databricks tasks.
            """
            tasks = []
            for step_name, step in deployment.step_configurations.items():
                # The arguments are passed to configure the entrypoint of the
                # docker container when the step is called.
                arguments = DatabricksEntrypointConfiguration.get_entrypoint_arguments(
                    step_name=step_name,
                    deployment_id=deployment_id,
                    wheel_package=self.package_name,
                    databricks_job_id=DATABRICKS_JOB_ID_PARAMETER_REFERENCE,
                )

                # Find the upstream container ops of the current step and
                # configure the current container op to run after them
                upstream_steps = [
                    f"{deployment_id}_{upstream_step_name}"
                    for upstream_step_name in step.spec.upstream_steps
                ]

                docker_settings = step.config.docker_settings
                docker_image_builder = PipelineDockerImageBuilder()
                # Gather the requirements files
                requirements_files = (
                    docker_image_builder.gather_requirements_files(
                        docker_settings=docker_settings,
                        stack=Client().active_stack,
                        log=False,
                    )
                )

                # Extract and clean the requirements
                requirements = list(
                    itertools.chain.from_iterable(
                        r[1].strip().split("\n") for r in requirements_files
                    )
                )

                # Remove empty items and duplicates
                requirements = sorted(set(filter(None, requirements)))

                task = convert_step_to_task(
                    f"{deployment_id}_{step_name}",
                    ZENML_STEP_DEFAULT_ENTRYPOINT_COMMAND,
                    arguments,
                    requirements,
                    depends_on=upstream_steps,
                    zenml_project_wheel=zenml_project_wheel,
                    job_cluster_key=job_cluster_key,
                )
                tasks.append(task)
            return tasks

        # Get the orchestrator run name
        orchestrator_run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        )
        # Get a filepath to use to save the finished yaml to
        fileio.makedirs(self.pipeline_directory)
        pipeline_file_path = os.path.join(
            self.pipeline_directory, f"{orchestrator_run_name}.yaml"
        )

        # Copy the repository to a temporary directory and add a setup.py file
        repository_temp_dir = (
            self.copy_repository_to_temp_dir_and_add_setup_py()
        )

        # Create a wheel for the package in the temporary directory
        wheel_path = self.create_wheel(temp_dir=repository_temp_dir)

        databricks_client = self._get_databricks_client()

        # Create an empty folder in a volume.
        deployment_name = (
            deployment.pipeline.name if deployment.pipeline else "default"
        )
        databricks_directory = f"{DATABRICKS_WHEELS_DIRECTORY_PREFIX}/{deployment_name}/{orchestrator_run_name}"
        databricks_wheel_path = (
            f"{databricks_directory}/{wheel_path.rsplit('/', 1)[-1]}"
        )

        databricks_client.dbutils.fs.mkdirs(databricks_directory)
        databricks_client.dbutils.fs.cp(
            f"{DATABRICKS_LOCAL_FILESYSTEM_PREFIX}/{wheel_path}",
            databricks_wheel_path,
        )

        # Construct the env variables for the pipeline
        env_vars = environment.copy()
        spark_env_vars = self.settings_class().spark_env_vars
        if spark_env_vars:
            for key, value in spark_env_vars.items():
                env_vars[key] = value

        fileio.rmtree(repository_temp_dir)

        logger.info(
            "Writing Databricks workflow definition to `%s`.",
            pipeline_file_path,
        )

        # using the databricks client uploads the pipeline to databricks
        job_cluster_key = self.sanitize_name(f"{deployment_id}")
        self._upload_and_run_pipeline(
            pipeline_name=orchestrator_run_name,
            tasks=_construct_databricks_pipeline(
                databricks_wheel_path, job_cluster_key
            ),
            env_vars=env_vars,
            job_cluster_key=job_cluster_key,
            schedule=deployment.schedule,
        )

    def _upload_and_run_pipeline(
        self,
        pipeline_name: str,
        tasks: List[DatabricksTask],
        env_vars: Dict[str, str],
        job_cluster_key: str,
        schedule: Optional["ScheduleResponse"] = None,
    ) -> None:
        """Uploads and run the pipeline on the Databricks jobs.

        Args:
            pipeline_name: The name of the pipeline.
            tasks: The list of tasks to run.
            env_vars: The environment variables.
            job_cluster_key: The ID of the Databricks job cluster.
            schedule: The schedule to run the pipeline

        Raises:
            ValueError: If the `Job Compute` policy is not found.
            ValueError: If the `schedule_timezone` is not set when passing

        """
        databricks_client = self._get_databricks_client()
        spark_conf = self.settings_class().spark_conf or {}
        spark_conf[
            "spark.databricks.driver.dbfsLibraryInstallationAllowed"
        ] = "true"

        policy_id = self.settings_class().policy_id or None
        for policy in databricks_client.cluster_policies.list():
            if policy.name == "Job Compute":
                policy_id = policy.policy_id
        if policy_id is None:
            raise ValueError(
                "Could not find the `Job Compute` policy in Databricks."
            )
        job_cluster = JobCluster(
            job_cluster_key=job_cluster_key,
            new_cluster=ClusterSpec(
                spark_version=self.settings_class().spark_version
                or DATABRICKS_SPARK_DEFAULT_VERSION,
                num_workers=self.settings_class().num_workers,
                node_type_id=self.settings_class().node_type_id
                or "Standard_D4s_v5",
                policy_id=policy_id,
                autoscale=AutoScale(
                    min_workers=self.settings_class().autoscale[0],
                    max_workers=self.settings_class().autoscale[1],
                ),
                single_user_name=self.settings_class().single_user_name,
                spark_env_vars=env_vars,
                spark_conf=spark_conf,
                workload_type=WorkloadType(
                    clients=ClientsTypes(jobs=True, notebooks=False)
                ),
            ),
        )
        if schedule and schedule.cron_expression:
            schedule_timezone = self.settings_class().schedule_timezone
            if schedule_timezone:
                databricks_schedule = CronSchedule(
                    quartz_cron_expression=schedule.cron_expression,
                    timezone_id=schedule_timezone,
                )
            else:
                raise ValueError(
                    "Property `schedule_timezone` must be set when passing "
                    "`cron_expression` to a Databricks orchestrator. "
                    "Databricks orchestrator requires a Java Timezone ID to run the pipeline on schedule. "
                    "Please refer to https://docs.oracle.com/middleware/1221/wcs/tag-ref/MISC/TimeZones.html for more information."
                )
        else:
            databricks_schedule = None

        job = databricks_client.jobs.create(
            name=pipeline_name,
            tasks=tasks,
            job_clusters=[job_cluster],
            schedule=databricks_schedule,
        )
        if job.job_id:
            databricks_client.jobs.run_now(job_id=job.job_id)
        else:
            raise ValueError("An error accured while getting the job id.")

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        """Get general component-specific metadata for a pipeline run.

        Args:
            run_id: The ID of the pipeline run.

        Returns:
            A dictionary of metadata.
        """
        run_url = (
            f"{self.config.host}/jobs/" f"{self.get_orchestrator_run_id()}"
        )
        return {
            METADATA_ORCHESTRATOR_URL: Uri(run_url),
        }
