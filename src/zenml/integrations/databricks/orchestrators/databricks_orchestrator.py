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
import re
from datetime import datetime as dt
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Type, cast

from databricks.sdk import WorkspaceClient as DatabricksClient
from databricks.sdk.service.compute import AutoScale, ClusterDetails, State
from databricks.sdk.service.jobs import Task as DatabricksTask

from zenml.client import Client
from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.environment import Environment
from zenml.integrations.databricks.flavors.databricks_orchestrator_flavor import (
    DatabricksOrchestratorConfig,
    DatabricksOrchestratorSettings,
)
from zenml.integrations.databricks.utils.databricks_utils import (
    convert_step_to_task,
)
from zenml.io import fileio
from zenml.logger import get_logger
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

ENV_ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID = (
    "ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID"
)
ZENML_STEP_DEFAULT_ENTRYPOINT_COMMAND = "entrypoint.main"
DATABRICKS_WHEELS_DIRECTORY_PREFIX = "dbfs:/FileStore/zenml"
DATABRICKS_LOCAL_FILESYSTEM_PREFIX = "file:/"
DATABRICKS_CLUSTER_DEFAULT_NAME = "zenml-databricks-cluster"
DATABRICKS_SPARK_DEFAULT_VERSION = "15.3.x-scala2.12"


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
        settings: DatabricksOrchestratorSettings,
    ) -> DatabricksClient:
        """Creates a Databricks client.

        Args:
            settings: The orchestrator settings.

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
        """
        return os.getenv(ENV_ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID) or ""

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
        """Creates a databricks yaml file.

        This functions as an intermediary representation of the pipeline which
        is then deployed to the kubeflow pipelines instance.

        How it works:
        -------------
        Before this method is called the `prepare_pipeline_deployment()`
        method builds a docker image that contains the code for the
        pipeline, all steps the context around these files.

        Based on this docker image a callable is created which builds
        container_ops for each step (`_construct_databricks_pipeline`).
        To do this the entrypoint of the docker image is configured to
        run the correct step within the docker image. The dependencies
        between these container_ops are then also configured onto each
        container_op by pointing at the downstream steps.

        This callable is then compiled into a databricks yaml file that is used as
        the intermediary representation of the kubeflow pipeline.

        This file, together with some metadata, runtime configurations is
        then uploaded into the kubeflow pipelines cluster for execution.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        Raises:
            RuntimeError: If trying to run a pipeline in a notebook
                environment.
        """
        # First check whether the code running in a notebook
        if Environment.in_notebook():
            raise RuntimeError(
                "The Kubeflow orchestrator cannot run pipelines in a notebook "
                "environment. The reason is that it is non-trivial to create "
                "a Docker image of a notebook. Please consider refactoring "
                "your notebook cells into separate scripts in a Python module "
                "and run the code outside of a notebook when using this "
                "orchestrator."
            )

        # Get deployment id
        deployment_id = deployment.id

        # Set environment
        os.environ[ENV_ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID] = str(
            deployment_id
        )
        environment[ENV_ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID] = str(
            deployment_id
        )

        # Create a callable for future compilation into a dsl.Pipeline.
        def _construct_databricks_pipeline(
            zenml_project_wheel: str, cluster_id: str
        ) -> List[DatabricksTask]:
            """Create a databrcks task for each step.

            This should contain the name of the step or task and configures the
            entrypoint of the task to run the step.

            Additionally, this gives each task information about its
            direct downstream steps.
            """
            tasks = []
            for step_name, step in deployment.step_configurations.items():
                # image = self.get_image(
                #    deployment=deployment, step_name=step_name
                # )

                # The arguments are passed to configure the entrypoint of the
                # docker container when the step is called.
                arguments = (
                    StepEntrypointConfiguration.get_entrypoint_arguments(
                        step_name=step_name, deployment_id=deployment_id
                    )
                )

                # Construct the --env argument
                env_vars = []
                for key, value in environment.items():
                    env_vars.append(f"{key}={value}")
                env_vars.append(
                    f"ZENML_DATABRICKS_SOURCE_PREFIX={self.package_name}"
                )
                env_vars.append(
                    f"ZENML_DATABRICKS_ORCHESTRATOR_RUN_ID={deployment_id}"
                )
                env_arg = ",".join(env_vars)

                arguments.extend(["--env", env_arg])

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
                    cluster_id=cluster_id,
                )
                tasks.append(task)
                # Create a container_op - the kubeflow equivalent of a step. It
                # contains the name of the step, the name of the docker image,
                # the command to use to run the step entrypoint
                # (e.g. `python -m zenml.entrypoints.step_entrypoint`)
                # and the arguments to be passed along with the command. Find
                # out more about how these arguments are parsed and used
                # in the base entrypoint `run()` method.
                # settings = cast(
                #    DatabricksOrchestratorSettings, self.get_settings(step)
                # )
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

        databricks_client = self._get_databricks_client(
            cast(DatabricksOrchestratorSettings, self.get_settings(deployment))
        )

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

        cluster = self.create_or_use_cluster()
        fileio.rmtree(repository_temp_dir)

        logger.info(
            "Writing Databricks workflow definition to `%s`.", pipeline_file_path
        )

        # using the databricks client uploads the pipeline to kubeflow pipelines and
        # runs it there
        assert cluster.cluster_id is not None
        self._upload_and_run_pipeline(
            pipeline_name=orchestrator_run_name,
            tasks=_construct_databricks_pipeline(
                databricks_wheel_path, cluster.cluster_id
            ),
            run_name=orchestrator_run_name,
            settings=cast(
                DatabricksOrchestratorSettings, self.get_settings(deployment)
            ),
        )

        # databricks_client.clusters.delete_and_wait(
        #    cluster_id=cluster.cluster_id
        # )
        # databricks_client.cluster_policies.delete(policy_id=policy.policy_id)

    def _upload_and_run_pipeline(
        self,
        pipeline_name: str,
        tasks: List[DatabricksTask],
        run_name: str,
        settings: DatabricksOrchestratorSettings,
        schedule: Optional["ScheduleResponse"] = None,
    ) -> None:
        """Uploads and run the pipeline on the Databricks jobs.

        Args:
            pipeline_name: Name of the pipeline.
            tasks: List of tasks to run.
            run_name: Orchestrator run name.
            settings: Pipeline level settings for this orchestrator.
            schedule: The schedule the pipeline will run on.
        """
        databricks_client = self._get_databricks_client(settings)

        job = databricks_client.jobs.create(
            name=pipeline_name,
            tasks=tasks,
        )
        assert job.job_id is not None
        databricks_client.jobs.run_now(job_id=job.job_id)

    def sanitize_cluster_name(self, name: str) -> str:
        """Sanitize the value to be used in a cluster name.

        Args:
            name: Arbitrary input cluster name.

        Returns:
            Sanitized cluster name.
        """
        name = re.sub(
            r"[^a-z0-9-]", "-", name.lower()
        )  # replaces any character that is not a lowercase letter, digit, or hyphen with a hyphen
        name = re.sub(r"^[-]+", "", name)  # trim leading hyphens
        name = re.sub(r"[-]+$", "", name)  # trim trailing hyphens
        return name

    def create_or_use_cluster(self) -> ClusterDetails:
        """Create or use an existing Databricks cluster."""
        databricks_client = self._get_databricks_client(self.settings_class())

        spark_conf = self.settings_class().spark_conf or {}
        spark_conf[
            "spark.databricks.driver.dbfsLibraryInstallationAllowed"
        ] = "true"

        policy_id = self.settings_class().policy_id or None
        for policy in databricks_client.cluster_policies.list():
            if policy.name == "Power User Compute":
                policy_id = policy.policy_id
        if policy_id is None:
            raise ValueError(
                "Could not find the 'Power User Compute' policy in Databricks."
            )
        cluster_config = {
            "spark_version": self.settings_class().spark_version
            or DATABRICKS_SPARK_DEFAULT_VERSION,
            "num_workers": self.settings_class().num_workers,
            "node_type_id": self.settings_class().node_type_id
            or "Standard_D8ads_v5",
            "cluster_name": self.settings_class().cluster_name
            or f"{DATABRICKS_CLUSTER_DEFAULT_NAME}_{dt.now().strftime('%Y_%m_%d_%H_%M_%S')}",
            "policy_id": policy_id,
            "autotermination_minutes": self.settings_class().autotermination_minutes
            or 30,
            "autoscale": AutoScale(
                min_workers=self.settings_class().autoscale[0],
                max_workers=self.settings_class().autoscale[1],
            ),
            "single_user_name": self.settings_class().single_user_name,
            "spark_env_vars": self.settings_class().spark_env_vars,
            "spark_conf": spark_conf,
        }

        # Check for existing clusters with the same configuration
        for existing_cluster in databricks_client.clusters.list():
            if existing_cluster.cluster_name == cluster_config["cluster_name"]:
                # Compare configurations
                if self._compare_cluster_configs(
                    existing_cluster, cluster_config
                ):
                    # If configurations match, use the existing cluster
                    if (
                        existing_cluster.state
                        and existing_cluster.state != State.RUNNING
                    ):
                        # Start the cluster if it's terminated
                        databricks_client.clusters.start_and_wait(
                            existing_cluster.cluster_id
                        )
        # If no matching cluster found, create a new one
        return databricks_client.clusters.create_and_wait(**cluster_config)

    def _compare_cluster_configs(
        self, existing_cluster: Any, new_config: Dict[str, Any]
    ) -> bool:
        """Compare existing cluster configuration with new configuration.

        Args:
            existing_cluster: Existing cluster configuration.
            new_config: New cluster configuration.

        Returns:
            True if configurations are equivalent, False otherwise.
        """
        # Compare basic cluster properties
        if (
            existing_cluster.spark_version != new_config["spark_version"]
            or existing_cluster.num_workers != new_config["num_workers"]
            or existing_cluster.node_type_id != new_config["node_type_id"]
            or existing_cluster.cluster_name != new_config["cluster_name"]
            or existing_cluster.policy_id != new_config["policy_id"]
            or existing_cluster.autotermination_minutes
            != new_config["autotermination_minutes"]
            or existing_cluster.single_user_name
            != new_config["single_user_name"]
        ):
            return False

        # Compare autoscale settings
        if existing_cluster.autoscale:
            if not new_config["autoscale"]:
                return False
            if (
                existing_cluster.autoscale.min_workers
                != new_config["autoscale"].min_workers
                or existing_cluster.autoscale.max_workers
                != new_config["autoscale"].max_workers
            ):
                return False
        elif new_config["autoscale"]:
            return False

        # Compare spark environment variables
        if existing_cluster.spark_env_vars != new_config["spark_env_vars"]:
            return False

        # Compare spark configuration
        if existing_cluster.spark_conf != new_config["spark_conf"]:
            return False

        # If all checks pass, configurations are considered equivalent
        return True
