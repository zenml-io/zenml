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
"""Implementation of Airflow orchestrator integration."""

import datetime
import importlib
import os
import zipfile
from typing import (
    TYPE_CHECKING,
    Any,
    ClassVar,
    Dict,
    NamedTuple,
    Optional,
    Tuple,
    Type,
    cast,
)

from zenml.config.global_config import GlobalConfiguration
from zenml.entrypoints import StepEntrypointConfiguration
from zenml.enums import StackComponentType
from zenml.integrations.airflow.flavors.airflow_orchestrator_flavor import (
    AirflowOrchestratorConfig,
    AirflowOrchestratorSettings,
    OperatorType,
)
from zenml.io import fileio
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator
from zenml.utils import io_utils

if TYPE_CHECKING:
    from zenml.config import ResourceSettings
    from zenml.config.base_settings import BaseSettings
    from zenml.integrations.airflow.orchestrators.dag_generator import (
        DagConfiguration,
        TaskConfiguration,
    )
    from zenml.models import PipelineDeploymentResponse
    from zenml.pipelines import Schedule
    from zenml.stack import Stack

logger = get_logger(__name__)


class DagGeneratorValues(NamedTuple):
    """Values from the DAG generator module."""

    file: str
    config_file_name: str
    run_id_env_variable_name: str
    dag_configuration_class: Type["DagConfiguration"]
    task_configuration_class: Type["TaskConfiguration"]


def get_dag_generator_values(
    custom_dag_generator_source: Optional[str] = None,
) -> DagGeneratorValues:
    """Gets values from the DAG generator module.

    Args:
        custom_dag_generator_source: Source of a custom DAG generator module.

    Returns:
        DAG generator module values.
    """
    if custom_dag_generator_source:
        module = importlib.import_module(custom_dag_generator_source)
    else:
        from zenml.integrations.airflow.orchestrators import dag_generator

        module = dag_generator

    assert module.__file__
    return DagGeneratorValues(
        file=module.__file__,
        config_file_name=module.CONFIG_FILENAME,
        run_id_env_variable_name=module.ENV_ZENML_AIRFLOW_RUN_ID,
        dag_configuration_class=module.DagConfiguration,
        task_configuration_class=module.TaskConfiguration,
    )


class AirflowOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running pipelines using Airflow."""

    supports_scheduling: ClassVar[bool] = True

    def __init__(self, **values: Any):
        """Initialize the orchestrator.

        Args:
            **values: Values to set in the orchestrator.
        """
        super().__init__(**values)
        self.dags_directory = os.path.join(
            io_utils.get_global_config_directory(),
            "airflow",
            str(self.id),
            "dags",
        )

    @property
    def config(self) -> AirflowOrchestratorConfig:
        """Returns the orchestrator config.

        Returns:
            The configuration.
        """
        return cast(AirflowOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the Kubeflow orchestrator.

        Returns:
            The settings class.
        """
        return AirflowOrchestratorSettings

    @property
    def validator(self) -> Optional["StackValidator"]:
        """Validates the stack.

        In the remote case, checks that the stack contains a container registry
        and only remote components.

        Returns:
            A `StackValidator` instance.
        """
        if self.config.local:
            # No container registry required if just running locally.
            return None
        else:

            def _validate_remote_components(
                stack: "Stack",
            ) -> Tuple[bool, str]:
                for component in stack.components.values():
                    if not component.config.is_local:
                        continue

                    return False, (
                        f"The Airflow orchestrator is configured to run "
                        f"pipelines remotely, but the '{component.name}' "
                        f"{component.type.value} is a local stack component "
                        f"and will not be available in the Airflow "
                        f"task.\nPlease ensure that you always use non-local "
                        f"stack components with a remote Airflow orchestrator, "
                        f"otherwise you may run into pipeline execution "
                        f"problems."
                    )

                return True, ""

            return StackValidator(
                required_components={
                    StackComponentType.CONTAINER_REGISTRY,
                    StackComponentType.IMAGE_BUILDER,
                },
                custom_validation_function=_validate_remote_components,
            )

    def prepare_pipeline_deployment(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
    ) -> None:
        """Builds a Docker image to run pipeline steps.

        Args:
            deployment: The pipeline deployment configuration.
            stack: The stack on which the pipeline will be deployed.
        """
        if self.config.local:
            stack.check_local_paths()

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
    ) -> Any:
        """Creates and writes an Airflow DAG zip file.

        Args:
            deployment: The pipeline deployment to prepare or run.
            stack: The stack the pipeline will run on.
            environment: Environment variables to set in the orchestration
                environment.

        """
        pipeline_settings = cast(
            AirflowOrchestratorSettings, self.get_settings(deployment)
        )

        dag_generator_values = get_dag_generator_values(
            custom_dag_generator_source=pipeline_settings.custom_dag_generator
        )

        command = StepEntrypointConfiguration.get_entrypoint_command()

        tasks = []
        for step_name, step in deployment.step_configurations.items():
            settings = cast(
                AirflowOrchestratorSettings, self.get_settings(step)
            )
            image = self.get_image(deployment=deployment, step_name=step_name)
            arguments = StepEntrypointConfiguration.get_entrypoint_arguments(
                step_name=step_name, deployment_id=deployment.id
            )
            operator_args = settings.operator_args.copy()
            if self.requires_resources_in_orchestration_environment(step=step):
                if settings.operator == OperatorType.KUBERNETES_POD.source:
                    self._apply_resource_settings(
                        resource_settings=step.config.resource_settings,
                        operator_args=operator_args,
                    )
                else:
                    logger.warning(
                        "Specifying step resources is only supported when "
                        "using KubernetesPodOperators, ignoring resource "
                        "configuration for step %s.",
                        step_name,
                    )

            task = dag_generator_values.task_configuration_class(
                id=step_name,
                zenml_step_name=step_name,
                upstream_steps=step.spec.upstream_steps,
                docker_image=image,
                command=command,
                arguments=arguments,
                environment=environment,
                operator_source=settings.operator,
                operator_args=operator_args,
            )
            tasks.append(task)

        local_stores_path = (
            os.path.expanduser(GlobalConfiguration().local_stores_path)
            if self.config.local
            else None
        )

        dag_id = pipeline_settings.dag_id or get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        )
        dag_config = dag_generator_values.dag_configuration_class(
            id=dag_id,
            local_stores_path=local_stores_path,
            tasks=tasks,
            tags=pipeline_settings.dag_tags,
            dag_args=pipeline_settings.dag_args,
            **self._translate_schedule(deployment.schedule),
        )

        self._write_dag(
            dag_config,
            dag_generator_values=dag_generator_values,
            output_dir=pipeline_settings.dag_output_dir or self.dags_directory,
        )

    def _apply_resource_settings(
        self,
        resource_settings: "ResourceSettings",
        operator_args: Dict[str, Any],
    ) -> None:
        """Adds resource settings to the operator args.

        Args:
            resource_settings: The resource settings to add.
            operator_args: The operator args which will get modified in-place.
        """
        if "container_resources" in operator_args:
            logger.warning(
                "Received duplicate resources from ResourceSettings: `%s`"
                "and operator_args: `%s`. Ignoring the resources defined by "
                "the ResourceSettings.",
                resource_settings,
                operator_args["container_resources"],
            )
        else:
            limits = {}

            if resource_settings.cpu_count is not None:
                limits["cpu"] = str(resource_settings.cpu_count)

            if resource_settings.memory is not None:
                memory_limit = resource_settings.memory[:-1]
                limits["memory"] = memory_limit

            if resource_settings.gpu_count is not None:
                logger.warning(
                    "Specifying GPU resources is not supported for the Airflow "
                    "orchestrator."
                )

            operator_args["container_resources"] = {"limits": limits}

    def _write_dag(
        self,
        dag_config: "DagConfiguration",
        dag_generator_values: DagGeneratorValues,
        output_dir: str,
    ) -> None:
        """Writes an Airflow DAG to disk.

        Args:
            dag_config: Configuration of the DAG to write.
            dag_generator_values: Values of the DAG generator to use.
            output_dir: The directory in which to write the DAG.
        """
        io_utils.create_dir_recursive_if_not_exists(output_dir)

        if self.config.local and output_dir == self.dags_directory:
            logger.warning(
                "You're using a local Airflow orchestrator but have not "
                "specified a custom DAG output directory. Unless you've "
                "configured your Airflow server to look for DAGs in this "
                "directory (%s), this DAG will not be found automatically "
                "by your local Airflow server.",
                output_dir,
            )

        def _write_zip(path: str) -> None:
            with zipfile.ZipFile(path, mode="w") as z:
                z.write(dag_generator_values.file, arcname="dag.py")
                z.writestr(
                    dag_generator_values.config_file_name,
                    dag_config.model_dump_json(),
                )

            logger.info("Writing DAG definition to `%s`.", path)

        dag_filename = f"{dag_config.id}.zip"
        if io_utils.is_remote(output_dir):
            io_utils.create_dir_recursive_if_not_exists(self.dags_directory)
            local_zip_path = os.path.join(self.dags_directory, dag_filename)
            remote_zip_path = os.path.join(output_dir, dag_filename)
            _write_zip(local_zip_path)
            try:
                fileio.copy(local_zip_path, remote_zip_path)
                logger.info("Copied DAG definition to `%s`.", remote_zip_path)
            except Exception as e:
                logger.exception(e)
                logger.error(
                    "Failed to upload DAG to remote path `%s`. To run the "
                    "pipeline in Airflow, please manually copy the file `%s` "
                    "to your Airflow DAG directory.",
                    remote_zip_path,
                    local_zip_path,
                )
        else:
            zip_path = os.path.join(output_dir, dag_filename)
            _write_zip(zip_path)

    def get_orchestrator_run_id(self) -> str:
        """Returns the active orchestrator run id.

        Raises:
            RuntimeError: If the environment variable specifying the run id
                is not set.

        Returns:
            The orchestrator run id.
        """
        from zenml.integrations.airflow.orchestrators.dag_generator import (
            ENV_ZENML_AIRFLOW_RUN_ID,
        )

        try:
            return os.environ[ENV_ZENML_AIRFLOW_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_AIRFLOW_RUN_ID}."
            )

    @staticmethod
    def _translate_schedule(
        schedule: Optional["Schedule"] = None,
    ) -> Dict[str, Any]:
        """Convert ZenML schedule into Airflow schedule.

        The Airflow schedule uses slightly different naming and needs some
        default entries for execution without a schedule.

        Args:
            schedule: Containing the interval, start and end date and
                a boolean flag that defines if past runs should be caught up
                on

        Returns:
            Airflow configuration dict.
        """
        if schedule:
            if schedule.cron_expression:
                start_time = schedule.start_time or (
                    datetime.datetime.utcnow() - datetime.timedelta(7)
                )
                return {
                    "schedule": schedule.cron_expression,
                    "start_date": start_time,
                    "end_date": schedule.end_time,
                    "catchup": schedule.catchup,
                }
            else:
                return {
                    "schedule": schedule.interval_second,
                    "start_date": schedule.start_time,
                    "end_date": schedule.end_time,
                    "catchup": schedule.catchup,
                }

        return {
            "schedule": "@once",
            # set a start time in the past and disable catchup so airflow
            # runs the dag immediately
            "start_date": datetime.datetime.utcnow() - datetime.timedelta(7),
            "catchup": False,
        }
