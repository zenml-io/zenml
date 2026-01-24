#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Implementation of the Run:AI orchestrator."""

import os
import time
from typing import TYPE_CHECKING, Dict, Optional, Tuple, cast

from zenml.config.base_settings import BaseSettings
from zenml.enums import ExecutionStatus
from zenml.integrations.runai.flavors.runai_orchestrator_flavor import (
    RunAIOrchestratorConfig,
    RunAIOrchestratorSettings,
)
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.utils.string_utils import random_str

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, PipelineSnapshotResponse
    from zenml.stack import Stack

ENV_ZENML_RUNAI_WORKLOAD_ID = "ZENML_RUNAI_WORKLOAD_ID"
ENV_ZENML_RUNAI_PROJECT_ID = "ZENML_RUNAI_PROJECT_ID"
ENV_ZENML_RUNAI_CLUSTER_ID = "ZENML_RUNAI_CLUSTER_ID"

logger = get_logger(__name__)


class RunAIOrchestrator(ContainerizedOrchestrator):
    """Orchestrator for running pipelines on Run:AI clusters.

    This orchestrator submits ZenML pipelines as Run:AI training or inference
    workloads, enabling fractional GPU allocation and efficient resource sharing.
    """

    @property
    def config(self) -> RunAIOrchestratorConfig:
        """Returns the orchestrator config.

        Returns:
            The configuration.
        """
        return cast(RunAIOrchestratorConfig, self._config)

    @property
    def settings_class(self) -> Optional[type[BaseSettings]]:
        """Settings class for the Run:AI orchestrator.

        Returns:
            The settings class.
        """
        return RunAIOrchestratorSettings

    def get_orchestrator_run_id(self) -> str:
        """Returns the run id of the active orchestrator run.

        This ID must be unique per pipeline run and identical across all
        steps within a run. For Run:AI, we use the workload ID.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If running outside a Run:AI environment.
        """
        # Check if we're running inside a Run:AI workload
        workload_id = os.environ.get(ENV_ZENML_RUNAI_WORKLOAD_ID)
        if workload_id:
            return workload_id

        # Fallback for local development/testing
        # In production, this should always be set by the workload
        return f"runai-local-{random_str(8)}"

    def submit_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        base_environment: Dict[str, str],
        step_environments: Dict[str, Dict[str, str]],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a pipeline to Run:AI as a training workload.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            base_environment: Base environment variables for all steps.
            step_environments: Step-specific environment variables.
            placeholder_run: An optional placeholder run for the snapshot.

        Returns:
            Optional submission result with wait function if synchronous.

        Raises:
            RuntimeError: If Run:AI client initialization or submission fails.
        """
        # Import here to avoid requiring runapy at import time
        try:
            from runapy import Configuration, RunAI
            from runapy.models import (
                ComputeFields,
                EnvironmentVariable,
                TrainingCreationRequest,
                TrainingSpecSpec,
            )
        except ImportError as exc:
            raise RuntimeError(
                "The runapy package is required to use the Run:AI orchestrator. "
                "Please install it with: pip install runapy"
            ) from exc

        settings = cast(RunAIOrchestratorSettings, self.get_settings(snapshot))

        # Initialize Run:AI client
        logger.info("Initializing Run:AI client...")
        config = Configuration(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret.get_secret_value(),
            runai_base_url=self.config.runai_base_url,
        )
        runai_client = RunAI(configuration=config)

        # Resolve project and cluster IDs
        project_id, cluster_id = self._resolve_project_and_cluster(runai_client)

        # Get the Docker image for the pipeline
        image = self.get_image(snapshot=snapshot)
        logger.info(f"Using Docker image: {image}")

        # Build workload name
        workload_name = self._get_workload_name(snapshot)

        # Build environment variables
        env_vars = self._build_environment_variables(
            base_environment, settings.environment_variables
        )

        # Add ZenML-specific environment variables
        workload_id = f"{workload_name}-{random_str(8)}"
        env_vars.extend(
            [
                EnvironmentVariable(name=ENV_ZENML_RUNAI_WORKLOAD_ID, value=workload_id),
                EnvironmentVariable(name=ENV_ZENML_RUNAI_PROJECT_ID, value=project_id),
                EnvironmentVariable(name=ENV_ZENML_RUNAI_CLUSTER_ID, value=cluster_id),
            ]
        )

        # Build compute configuration
        compute = ComputeFields(
            gpuDevicesRequest=settings.gpu_devices_request,
            gpuPortionRequest=settings.gpu_portion_request,
            gpuRequestType=settings.gpu_request_type,
            cpuCoreRequest=settings.cpu_core_request,
            cpuMemoryRequest=settings.cpu_memory_request,
        )

        # Create training workload request
        logger.info(f"Creating Run:AI training workload: {workload_name}")
        training_request = TrainingCreationRequest(
            name=workload_name,
            projectId=project_id,
            clusterId=cluster_id,
            spec=TrainingSpecSpec(
                image=image,
                compute=compute,
                environmentVariables=env_vars,
            ),
        )

        # Submit the workload
        try:
            response = runai_client.workloads.trainings.create_training1(
                training_creation_request=training_request
            )
            logger.info(
                f"Successfully submitted Run:AI workload. "
                f"Workload ID: {response.workload_id}, "
                f"Project: {self.config.project_name}"
            )
        except Exception as exc:
            raise RuntimeError(
                f"Failed to submit Run:AI workload: {exc}"
            ) from exc

        # Return submission result with wait function if synchronous
        if settings.synchronous:
            return SubmissionResult(
                wait_for_completion=lambda: self._wait_for_completion(
                    runai_client, response.workload_id
                )
            )

        return None

    def submit_dynamic_pipeline(
        self,
        snapshot: "PipelineSnapshotResponse",
        stack: "Stack",
        environment: Dict[str, str],
        placeholder_run: Optional["PipelineRunResponse"] = None,
    ) -> Optional[SubmissionResult]:
        """Submits a dynamic pipeline to Run:AI.

        For the MVP, dynamic pipelines use the same submission logic as
        regular pipelines, creating a single Run:AI training workload.

        Args:
            snapshot: The pipeline snapshot to submit.
            stack: The stack the pipeline will run on.
            environment: Environment variables for the orchestration environment.
            placeholder_run: An optional placeholder run.

        Returns:
            Optional submission result.
        """
        # For MVP, we submit dynamic pipelines the same way as regular ones
        # Future: Consider separate handling for dynamic orchestration
        return self.submit_pipeline(
            snapshot=snapshot,
            stack=stack,
            base_environment=environment,
            step_environments={},
            placeholder_run=placeholder_run,
        )

    def fetch_status(
        self, run: "PipelineRunResponse", include_steps: bool = False
    ) -> Tuple[Optional[ExecutionStatus], Optional[Dict[str, ExecutionStatus]]]:
        """Refreshes the status of a specific pipeline run.

        Args:
            run: A pipeline run response to fetch its status.
            include_steps: If True, also fetch step statuses (not supported in MVP).

        Returns:
            Tuple of pipeline status and optional step statuses.

        Raises:
            RuntimeError: If Run:AI client initialization fails.
        """
        # Import here to avoid requiring runapy at import time
        try:
            from runapy import Configuration, RunAI
        except ImportError as exc:
            raise RuntimeError(
                "The runapy package is required to use the Run:AI orchestrator. "
                "Please install it with: pip install runapy"
            ) from exc

        # Get workload ID from run metadata
        workload_id = run.run_metadata.get(ENV_ZENML_RUNAI_WORKLOAD_ID)
        if not workload_id:
            logger.warning(
                f"No Run:AI workload ID found for run {run.id}. "
                "Cannot fetch status."
            )
            return None, None

        # Initialize Run:AI client
        config = Configuration(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret.get_secret_value(),
            runai_base_url=self.config.runai_base_url,
        )
        runai_client = RunAI(configuration=config)

        try:
            # Query workload status
            workload = runai_client.workloads.trainings.get_training(workload_id)
            status = self._map_runai_status_to_execution_status(workload.status)
            logger.debug(f"Run:AI workload {workload_id} status: {workload.status}")

            # For MVP, we don't fetch individual step statuses
            return status, None

        except Exception as exc:
            logger.error(f"Failed to fetch Run:AI workload status: {exc}")
            return None, None

    def _get_runai_client(self) -> "RunAI":  # type: ignore[name-defined]
        """Initializes and returns a Run:AI client.

        Returns:
            Initialized Run:AI client.

        Raises:
            RuntimeError: If client initialization fails.
        """
        try:
            from runapy import Configuration, RunAI
        except ImportError as exc:
            raise RuntimeError(
                "The runapy package is required to use the Run:AI orchestrator. "
                "Please install it with: pip install runapy"
            ) from exc

        config = Configuration(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret.get_secret_value(),
            runai_base_url=self.config.runai_base_url,
        )
        return RunAI(configuration=config)

    def _resolve_project_and_cluster(
        self, runai_client: "RunAI",  # type: ignore[name-defined]
    ) -> Tuple[str, str]:
        """Resolves Run:AI project and cluster IDs from names.

        Args:
            runai_client: Initialized Run:AI client.

        Returns:
            Tuple of (project_id, cluster_id).

        Raises:
            RuntimeError: If project or cluster cannot be resolved.
        """
        # Get project ID from project name
        try:
            projects = runai_client.projects.list_projects()
            project_id = None
            for project in projects:
                if project.name == self.config.project_name:
                    project_id = project.id
                    break

            if not project_id:
                raise RuntimeError(
                    f"Project '{self.config.project_name}' not found in Run:AI"
                )

            logger.info(
                f"Resolved project '{self.config.project_name}' to ID: {project_id}"
            )

        except Exception as exc:
            raise RuntimeError(
                f"Failed to resolve Run:AI project '{self.config.project_name}': {exc}"
            ) from exc

        # Get cluster ID
        if self.config.cluster_name:
            # Use specified cluster
            try:
                clusters = runai_client.clusters.list_clusters()
                cluster_id = None
                for cluster in clusters:
                    if cluster.name == self.config.cluster_name:
                        cluster_id = cluster.id
                        break

                if not cluster_id:
                    raise RuntimeError(
                        f"Cluster '{self.config.cluster_name}' not found in Run:AI"
                    )

                logger.info(
                    f"Resolved cluster '{self.config.cluster_name}' to ID: {cluster_id}"
                )

            except Exception as exc:
                raise RuntimeError(
                    f"Failed to resolve Run:AI cluster '{self.config.cluster_name}': {exc}"
                ) from exc
        else:
            # Use first available cluster
            try:
                clusters = runai_client.clusters.list_clusters()
                if not clusters:
                    raise RuntimeError("No Run:AI clusters available")

                cluster_id = clusters[0].id
                logger.info(f"Using first available cluster: {clusters[0].name}")

            except Exception as exc:
                raise RuntimeError(f"Failed to get Run:AI clusters: {exc}") from exc

        return project_id, cluster_id

    def _get_workload_name(self, snapshot: "PipelineSnapshotResponse") -> str:
        """Generates a Run:AI workload name from the pipeline snapshot.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            A valid Run:AI workload name.
        """
        # Use ZenML's orchestrator run name utility
        base_name = get_orchestrator_run_name(str(snapshot.pipeline.id))

        # Ensure name is valid for Run:AI (lowercase, alphanumeric, hyphens)
        workload_name = base_name.lower().replace("_", "-")

        # Run:AI workload names have length limits
        if len(workload_name) > 50:
            workload_name = workload_name[:50]

        return workload_name

    def _build_environment_variables(
        self,
        base_environment: Dict[str, str],
        additional_vars: Dict[str, str],
    ) -> list:  # type: ignore[type-arg]
        """Builds Run:AI environment variables from dictionaries.

        Args:
            base_environment: Base environment variables.
            additional_vars: Additional environment variables from settings.

        Returns:
            List of Run:AI EnvironmentVariable objects.
        """
        from runapy.models import EnvironmentVariable

        env_vars = []

        # Add base environment variables
        for key, value in base_environment.items():
            env_vars.append(EnvironmentVariable(name=key, value=value))

        # Add additional variables (override base if duplicate keys)
        for key, value in additional_vars.items():
            # Remove any existing variable with the same key
            env_vars = [var for var in env_vars if var.name != key]
            env_vars.append(EnvironmentVariable(name=key, value=value))

        return env_vars

    def _wait_for_completion(
        self, runai_client: "RunAI", workload_id: str  # type: ignore[name-defined]
    ) -> None:
        """Waits for a Run:AI workload to complete.

        Args:
            runai_client: Initialized Run:AI client.
            workload_id: The workload ID to wait for.

        Raises:
            RuntimeError: If the workload fails or times out.
        """
        logger.info(f"Waiting for Run:AI workload {workload_id} to complete...")

        start_time = time.time()
        timeout = self.config.workload_timeout

        while True:
            # Check timeout
            if timeout and (time.time() - start_time) > timeout:
                raise RuntimeError(
                    f"Run:AI workload {workload_id} timed out after {timeout} seconds"
                )

            # Query workload status
            try:
                workload = runai_client.workloads.trainings.get_training(workload_id)
                status = workload.status

                logger.debug(f"Workload {workload_id} status: {status}")

                # Check if workload is in terminal state
                if status.lower() in ["succeeded", "completed", "success"]:
                    logger.info(f"Workload {workload_id} completed successfully")
                    return

                if status.lower() in ["failed", "error"]:
                    raise RuntimeError(
                        f"Run:AI workload {workload_id} failed with status: {status}"
                    )

                # For running/pending states, continue waiting
                # Sleep before next poll
                time.sleep(self.config.monitoring_interval)

            except Exception as exc:
                logger.error(f"Error querying workload status: {exc}")
                raise RuntimeError(
                    f"Failed to query Run:AI workload {workload_id}: {exc}"
                ) from exc

    def _map_runai_status_to_execution_status(
        self, runai_status: str
    ) -> ExecutionStatus:
        """Maps Run:AI workload status to ZenML ExecutionStatus.

        Args:
            runai_status: The Run:AI workload status string.

        Returns:
            The corresponding ZenML ExecutionStatus.
        """
        # Normalize status to lowercase for comparison
        status = runai_status.lower()

        # Map Run:AI statuses to ZenML execution statuses
        status_mapping = {
            "pending": ExecutionStatus.INITIALIZING,
            "running": ExecutionStatus.RUNNING,
            "succeeded": ExecutionStatus.COMPLETED,
            "completed": ExecutionStatus.COMPLETED,
            "success": ExecutionStatus.COMPLETED,
            "failed": ExecutionStatus.FAILED,
            "error": ExecutionStatus.FAILED,
            "stopped": ExecutionStatus.FAILED,  # Treat stopped as failed for MVP
            "stopping": ExecutionStatus.STOPPING,
        }

        mapped_status = status_mapping.get(status, ExecutionStatus.RUNNING)
        return cast(ExecutionStatus, mapped_status)
