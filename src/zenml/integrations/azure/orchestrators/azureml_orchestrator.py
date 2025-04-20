#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Implementation of the AzureML Orchestrator."""

import json
import os
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterator,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    cast,
)
from uuid import UUID

from azure.ai.ml import Input, MLClient, Output
from azure.ai.ml.constants import TimeZone
from azure.ai.ml.dsl import pipeline
from azure.ai.ml.entities import (
    CommandComponent,
    CronTrigger,
    Environment,
    JobSchedule,
    RecurrenceTrigger,
)
from azure.core.exceptions import (
    HttpResponseError,
    ResourceExistsError,
)
from azure.identity import DefaultAzureCredential

from zenml.config.base_settings import BaseSettings
from zenml.config.step_configurations import Step
from zenml.constants import (
    METADATA_ORCHESTRATOR_RUN_ID,
    METADATA_ORCHESTRATOR_URL,
)
from zenml.enums import ExecutionStatus, StackComponentType
from zenml.integrations.azure.azureml_utils import create_or_get_compute
from zenml.integrations.azure.flavors.azureml import AzureMLComputeTypes
from zenml.integrations.azure.flavors.azureml_orchestrator_flavor import (
    AzureMLOrchestratorConfig,
    AzureMLOrchestratorSettings,
)
from zenml.integrations.azure.orchestrators.azureml_orchestrator_entrypoint_config import (
    AzureMLEntrypointConfiguration,
)
from zenml.logger import get_logger
from zenml.metadata.metadata_types import MetadataType, Uri
from zenml.orchestrators import ContainerizedOrchestrator
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import StackValidator
from zenml.utils.string_utils import b64_encode

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentResponse, PipelineRunResponse
    from zenml.stack import Stack

logger = get_logger(__name__)

ENV_ZENML_AZUREML_RUN_ID = "AZUREML_ROOT_RUN_ID"


class AzureMLOrchestrator(ContainerizedOrchestrator):
    """Orchestrator responsible for running pipelines on AzureML."""

    @property
    def config(self) -> AzureMLOrchestratorConfig:
        """Returns the `AzureMLOrchestratorConfig` config.

        Returns:
            The configuration.
        """
        return cast(AzureMLOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[Type["BaseSettings"]]:
        """Settings class for the AzureML orchestrator.

        Returns:
            The settings class.
        """
        return AzureMLOrchestratorSettings

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
                if not component.config.is_local:
                    continue

                return False, (
                    f"The AzureML orchestrator runs pipelines remotely, "
                    f"but the '{component.name}' {component.type.value} is "
                    "a local stack component and will not be available in "
                    "the AzureML step.\nPlease ensure that you always "
                    "use non-local stack components with the AzureML "
                    "orchestrator."
                )

            return True, ""

        return StackValidator(
            required_components={
                StackComponentType.CONTAINER_REGISTRY,
                StackComponentType.IMAGE_BUILDER,
            },
            custom_validation_function=_validate_remote_components,
        )

    def get_orchestrator_run_id(self) -> str:
        """Returns the run id of the active orchestrator run.

        Important: This needs to be a unique ID and return the same value for
        all steps of a pipeline run.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If the run id cannot be read from the environment.
        """
        try:
            return os.environ[ENV_ZENML_AZUREML_RUN_ID]
        except KeyError:
            raise RuntimeError(
                "Unable to read run id from environment variable "
                f"{ENV_ZENML_AZUREML_RUN_ID}."
            )

    @staticmethod
    def _create_command_component(
        step: Step,
        step_name: str,
        env_name: str,
        image: str,
        command: List[str],
        arguments: List[str],
    ) -> CommandComponent:
        """Creates a CommandComponent to run on AzureML Pipelines.

        Args:
            step: The step definition in ZenML.
            step_name: The name of the step.
            env_name: The name of the environment.
            image: The image to use in the environment
            command: The command to execute the entrypoint with.
            arguments: The arguments to pass into the command.

        Returns:
            the generated AzureML CommandComponent.
        """
        env = Environment(name=env_name, image=image)

        outputs = {"completed": Output(type="uri_file")}

        inputs = {}
        if step.spec.upstream_steps:
            inputs = {
                f"{upstream_step}": Input(type="uri_file")
                for upstream_step in step.spec.upstream_steps
            }

        return CommandComponent(
            name=step_name,
            display_name=step_name,
            description=f"AzureML CommandComponent for {step_name}.",
            inputs=inputs,
            outputs=outputs,
            environment=env,
            command=" ".join(command + arguments),
        )

    def prepare_or_run_pipeline(
        self,
        deployment: "PipelineDeploymentResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Iterator[Dict[str, MetadataType]]:
        """Prepares or runs a pipeline on AzureML.

        Args:
            deployment: The deployment to prepare or run.
            stack: The stack to run on.
            environment: Environment variables to set in the orchestration
                environment.
            placeholder_run: An optional placeholder run for the deployment.

        Raises:
            RuntimeError: If the creation of the schedule fails.

        Yields:
            A dictionary of metadata related to the pipeline run.
        """
        # Authentication
        if connector := self.get_connector():
            credentials = connector.connect()
        else:
            credentials = DefaultAzureCredential()

        # Settings
        settings = cast(
            AzureMLOrchestratorSettings,
            self.get_settings(deployment),
        )

        # Client creation
        ml_client = MLClient(
            credential=credentials,
            subscription_id=self.config.subscription_id,
            resource_group_name=self.config.resource_group,
            workspace_name=self.config.workspace,
        )

        # Create components
        components = {}
        for step_name, step in deployment.step_configurations.items():
            # Get the image for each step
            image = self.get_image(deployment=deployment, step_name=step_name)

            # Get the command and arguments
            command = AzureMLEntrypointConfiguration.get_entrypoint_command()
            arguments = (
                AzureMLEntrypointConfiguration.get_entrypoint_arguments(
                    step_name=step_name,
                    deployment_id=deployment.id,
                    zenml_env_variables=b64_encode(json.dumps(environment)),
                )
            )

            # Generate an AzureML CommandComponent
            components[step_name] = self._create_command_component(
                step=step,
                step_name=step_name,
                env_name=deployment.pipeline_configuration.name,
                image=image,
                command=command,
                arguments=arguments,
            )

        # Pipeline definition
        pipeline_args = dict()
        run_name = get_orchestrator_run_name(
            pipeline_name=deployment.pipeline_configuration.name
        )
        pipeline_args["name"] = run_name

        if compute_target := create_or_get_compute(
            ml_client, settings, default_compute_name=f"zenml_{self.id}"
        ):
            pipeline_args["compute"] = compute_target

        @pipeline(force_rerun=True, **pipeline_args)  # type: ignore[call-overload, misc]
        def azureml_pipeline() -> None:
            """Create an AzureML pipeline."""
            # Here we have to track the inputs and outputs so that we can bind
            # the components to each other to execute them in a specific order.
            component_outputs: Dict[str, Any] = {}
            for component_name, component in components.items():
                # Inputs
                component_inputs = {}
                if component.inputs:
                    component_inputs.update(
                        {i: component_outputs[i] for i in component.inputs}
                    )

                # Job
                component_job = component(**component_inputs)

                # Outputs
                if component_job.outputs:
                    component_outputs[component_name] = (
                        component_job.outputs.completed
                    )

        # Create and execute the pipeline job
        pipeline_job = azureml_pipeline()

        if settings.mode == AzureMLComputeTypes.SERVERLESS:
            pipeline_job.settings.default_compute = "serverless"

        # Scheduling
        if schedule := deployment.schedule:
            try:
                schedule_trigger: Optional[
                    Union[CronTrigger, RecurrenceTrigger]
                ] = None

                start_time = None
                if schedule.start_time is not None:
                    start_time = schedule.start_time.isoformat()

                end_time = None
                if schedule.end_time is not None:
                    end_time = schedule.end_time.isoformat()

                if schedule.cron_expression:
                    # If we are working with a cron expression
                    schedule_trigger = CronTrigger(
                        expression=schedule.cron_expression,
                        start_time=start_time,
                        end_time=end_time,
                        time_zone=TimeZone.UTC,
                    )

                elif schedule.interval_second:
                    # If we are working with intervals
                    interval = schedule.interval_second.total_seconds()

                    if interval % 60 != 0:
                        logger.warning(
                            "The ZenML AzureML orchestrator only works with "
                            "time intervals defined over minutes. Will "
                            f"use a schedule over {int(interval // 60)}."
                        )

                    if interval < 60:
                        raise RuntimeError(
                            "Can not create a schedule with an interval less "
                            "than 60 secs."
                        )

                    frequency = "minute"
                    interval = int(interval // 60)

                    schedule_trigger = RecurrenceTrigger(
                        frequency=frequency,
                        interval=interval,
                        start_time=start_time,
                        end_time=end_time,
                        time_zone=TimeZone.UTC,
                    )

                if schedule_trigger:
                    # Create and execute the job schedule
                    job_schedule = JobSchedule(
                        name=run_name,
                        trigger=schedule_trigger,
                        create_job=pipeline_job,
                    )
                    ml_client.schedules.begin_create_or_update(
                        job_schedule
                    ).result()
                    logger.info(
                        f"Scheduled pipeline '{run_name}' with recurrence "
                        "or cron expression."
                    )
                else:
                    raise RuntimeError(
                        "No valid scheduling configuration found for "
                        f"pipeline '{run_name}'."
                    )

            except (HttpResponseError, ResourceExistsError) as e:
                raise RuntimeError(
                    "Failed to create schedule for the pipeline "
                    f"'{run_name}': {str(e)}"
                )

        else:
            job = ml_client.jobs.create_or_update(pipeline_job)
            logger.info(f"Pipeline {run_name} has been started.")

            # Yield metadata based on the generated job object
            yield from self.compute_metadata(job)

            assert job.services is not None
            assert job.name is not None

            logger.info(
                f"Pipeline {run_name} is running. "
                "You can view the pipeline in the AzureML portal at "
                f"{job.services['Studio'].endpoint}"
            )

            if settings.synchronous:
                logger.info("Waiting for pipeline to finish...")
                ml_client.jobs.stream(job.name)

    def get_pipeline_run_metadata(
        self, run_id: UUID
    ) -> Dict[str, "MetadataType"]:
        """Get general component-specific metadata for a pipeline run.

        Args:
            run_id: The ID of the pipeline run.

        Returns:
            A dictionary of metadata.
        """
        try:
            if connector := self.get_connector():
                credentials = connector.connect()
            else:
                credentials = DefaultAzureCredential()

            ml_client = MLClient(
                credential=credentials,
                subscription_id=self.config.subscription_id,
                resource_group_name=self.config.resource_group,
                workspace_name=self.config.workspace,
            )

            azureml_root_run_id = os.environ[ENV_ZENML_AZUREML_RUN_ID]
            azureml_job = ml_client.jobs.get(azureml_root_run_id)

            return {
                METADATA_ORCHESTRATOR_URL: Uri(azureml_job.studio_url),
            }
        except Exception as e:
            logger.warning(
                f"Failed to fetch the Studio URL of the AzureML pipeline "
                f"job: {e}"
            )
            return {}

    def fetch_status(self, run: "PipelineRunResponse") -> ExecutionStatus:
        """Refreshes the status of a specific pipeline run.

        Args:
            run: The run that was executed by this orchestrator.

        Returns:
            the actual status of the pipeline execution.

        Raises:
            AssertionError: If the run was not executed by to this orchestrator.
            ValueError: If it fetches an unknown state or if we can not fetch
                the orchestrator run ID.
        """
        # Make sure that the stack exists and is accessible
        if run.stack is None:
            raise ValueError(
                "The stack that the run was executed on is not available "
                "anymore."
            )

        # Make sure that the run belongs to this orchestrator
        assert (
            self.id
            == run.stack.components[StackComponentType.ORCHESTRATOR][0].id
        )

        # Initialize the AzureML client
        if connector := self.get_connector():
            credentials = connector.connect()
        else:
            credentials = DefaultAzureCredential()

        ml_client = MLClient(
            credential=credentials,
            subscription_id=self.config.subscription_id,
            resource_group_name=self.config.resource_group,
            workspace_name=self.config.workspace,
        )

        # Fetch the status of the PipelineJob
        if METADATA_ORCHESTRATOR_RUN_ID in run.run_metadata:
            run_id = run.run_metadata[METADATA_ORCHESTRATOR_RUN_ID]
        elif run.orchestrator_run_id is not None:
            run_id = run.orchestrator_run_id
        else:
            raise ValueError(
                "Can not find the orchestrator run ID, thus can not fetch "
                "the status."
            )
        status = ml_client.jobs.get(run_id).status

        # Map the potential outputs to ZenML ExecutionStatus. Potential values:
        # https://learn.microsoft.com/en-us/python/api/azure-ai-ml/azure.ai.ml.entities.pipelinejob?view=azure-python#azure-ai-ml-entities-pipelinejob-status
        if status in [
            "NotStarted",
            "Starting",
            "Provisioning",
            "Preparing",
            "Queued",
        ]:
            return ExecutionStatus.INITIALIZING
        elif status in ["Running", "Finalizing"]:
            return ExecutionStatus.RUNNING
        elif status in [
            "CancelRequested",
            "Failed",
            "Canceled",
            "NotResponding",
        ]:
            return ExecutionStatus.FAILED
        elif status in ["Completed"]:
            return ExecutionStatus.COMPLETED
        else:
            raise ValueError("Unknown status for the pipeline job.")

    def compute_metadata(self, job: Any) -> Iterator[Dict[str, MetadataType]]:
        """Generate run metadata based on the generated AzureML PipelineJob.

        Args:
            job: The corresponding PipelineJob object.

        Yields:
            A dictionary of metadata related to the pipeline run.
        """
        # Metadata
        metadata: Dict[str, MetadataType] = {}

        # Orchestrator Run ID
        if run_id := self._compute_orchestrator_run_id(job):
            metadata[METADATA_ORCHESTRATOR_RUN_ID] = run_id

        # URL to the AzureML's pipeline view
        if orchestrator_url := self._compute_orchestrator_url(job):
            metadata[METADATA_ORCHESTRATOR_URL] = Uri(orchestrator_url)

        yield metadata

    @staticmethod
    def _compute_orchestrator_url(job: Any) -> Optional[str]:
        """Generate the Orchestrator Dashboard URL upon pipeline execution.

        Args:
            job: The corresponding PipelineJob object.

        Returns:
             the URL to the dashboard view in AzureML.
        """
        try:
            if job.studio_url:
                return str(job.studio_url)

            return None

        except Exception as e:
            logger.warning(
                f"There was an issue while extracting the pipeline url: {e}"
            )
            return None

    @staticmethod
    def _compute_orchestrator_run_id(job: Any) -> Optional[str]:
        """Generate the Orchestrator Dashboard URL upon pipeline execution.

        Args:
            job: The corresponding PipelineJob object.

        Returns:
             the URL to the dashboard view in AzureML.
        """
        try:
            if job.name:
                return str(job.name)

            return None

        except Exception as e:
            logger.warning(
                f"There was an issue while extracting the pipeline run ID: {e}"
            )
            return None
