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

import importlib
import os
import time
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, cast

from zenml.config.base_settings import BaseSettings
from zenml.enums import ExecutionStatus
from zenml.integrations.runai.flavors.runai_orchestrator_flavor import (
    RunAIOrchestratorConfig,
    RunAIOrchestratorSettings,
)
from zenml.logger import get_logger
from zenml.orchestrators import ContainerizedOrchestrator, SubmissionResult
from zenml.orchestrators.utils import get_orchestrator_run_name
from zenml.stack import Stack
from zenml.utils.string_utils import random_str

if TYPE_CHECKING:
    from zenml.models import PipelineRunResponse, PipelineSnapshotResponse

ENV_ZENML_RUNAI_WORKLOAD_ID = "ZENML_RUNAI_WORKLOAD_ID"
ENV_ZENML_RUNAI_PROJECT_ID = "ZENML_RUNAI_PROJECT_ID"
ENV_ZENML_RUNAI_CLUSTER_ID = "ZENML_RUNAI_CLUSTER_ID"
ENV_ZENML_RUNAI_CREDENTIAL_ID = "ZENML_RUNAI_CREDENTIAL_ID"

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

    def _load_runai_module(self, module_path: str) -> Any:
        """Loads a Run:AI SDK module, raising a helpful error if missing."""
        try:
            return importlib.import_module(module_path)
        except ImportError as exc:
            raise RuntimeError(
                "The runapy package is required to use the Run:AI orchestrator. "
                "Please install it with: pip install runapy"
            ) from exc

    def get_orchestrator_run_id(self) -> str:
        """Returns the run id of the active orchestrator run.

        This ID must be unique per pipeline run and identical across all
        steps within a run. For Run:AI, we use the workload ID.

        Returns:
            The orchestrator run id.

        Raises:
            RuntimeError: If running outside a Run:AI environment.
        """
        workload_id = os.environ.get(ENV_ZENML_RUNAI_WORKLOAD_ID)
        if workload_id:
            return workload_id

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
        settings = cast(RunAIOrchestratorSettings, self.get_settings(snapshot))
        runai_client = self._get_runai_client()

        project_id, cluster_id = self._resolve_project_and_cluster(
            runai_client
        )

        credential_id, created_credential, credential_name = (
            self._ensure_registry_credential(
                runai_client=runai_client,
                stack=stack,
                project_id=project_id,
                cluster_id=cluster_id,
            )
        )

        image = self.get_image(snapshot=snapshot)
        workload_name = self._build_workload_name(snapshot)

        runai_models = cast(Any, self._load_runai_module("runai.models"))
        EnvironmentVariable = runai_models.EnvironmentVariable
        SupersetSpecAllOfCompute = runai_models.SupersetSpecAllOfCompute
        TrainingCreationRequest = runai_models.TrainingCreationRequest
        TrainingSpecSpec = runai_models.TrainingSpecSpec

        env_vars = self._build_environment_variables(
            base_environment, settings.environment_variables, runai_models
        )

        env_vars.extend(
            [
                EnvironmentVariable(
                    name=ENV_ZENML_RUNAI_WORKLOAD_ID, value=workload_name
                ),
                EnvironmentVariable(
                    name=ENV_ZENML_RUNAI_PROJECT_ID, value=project_id
                ),
                EnvironmentVariable(
                    name=ENV_ZENML_RUNAI_CLUSTER_ID, value=cluster_id
                ),
                EnvironmentVariable(
                    name=ENV_ZENML_RUNAI_CREDENTIAL_ID,
                    value=credential_id or "",
                ),
            ]
        )

        compute = SupersetSpecAllOfCompute(
            gpu_devices_request=settings.gpu_devices_request,
            gpu_portion_request=settings.gpu_portion_request,
            gpu_request_type=settings.gpu_request_type,
            cpu_core_request=settings.cpu_core_request,
            cpu_memory_request=settings.cpu_memory_request,
        )

        image_pull_secrets = None
        if credential_id and credential_name:
            ImagePullSecret = runai_models.ImagePullSecret
            # Run:AI creates K8s secrets with 'dockerregistry-' prefix
            k8s_secret_name = f"dockerregistry-{credential_name}"
            image_pull_secrets = [
                ImagePullSecret(name=k8s_secret_name, user_credential=False)
            ]
        else:
            logger.warning(
                "No image pull secret will be attached - workload may fail to pull private images. "
                f"credential_id={credential_id}, credential_name={credential_name}"
            )

        from zenml.integrations.runai.orchestrators.runai_orchestrator_entrypoint_configuration import (
            RunAIOrchestratorEntrypointConfiguration,
        )

        command_list = (
            RunAIOrchestratorEntrypointConfiguration.get_entrypoint_command()
        )
        args_list = (
            RunAIOrchestratorEntrypointConfiguration.get_entrypoint_arguments(
                snapshot_id=snapshot.id,
                run_id=placeholder_run.id if placeholder_run else None,
            )
        )

        command_str = " ".join(command_list)
        args_str = " ".join(args_list) if args_list else None

        spec_dict = {
            "image": image,
            "command": command_str,
            "compute": compute,
            "environmentVariables": env_vars,
        }
        if args_str:
            spec_dict["args"] = args_str
        if image_pull_secrets:
            spec_dict["imagePullSecrets"] = image_pull_secrets

        training_request = TrainingCreationRequest(
            name=workload_name,
            projectId=project_id,
            clusterId=cluster_id,
            spec=TrainingSpecSpec(**spec_dict),
        )

        try:
            response = runai_client.workloads.trainings.create_training1(
                training_creation_request=training_request
            )
            workload_id_from_api = None
            if response.data:
                if isinstance(response.data, dict):
                    workload_id_from_api = (
                        response.data.get("workloadId")
                        or response.data.get("id")
                        or response.data.get("workload_id")
                    )
                else:
                    workload_id_from_api = getattr(
                        response.data, "workloadId", None
                    ) or getattr(response.data, "id", None)
        except Exception as exc:
            raise RuntimeError(
                f"Failed to submit Run:AI workload: {exc}"
            ) from exc

        workload_identifier = workload_id_from_api or workload_name

        metadata = {
            ENV_ZENML_RUNAI_WORKLOAD_ID: workload_identifier,
            ENV_ZENML_RUNAI_PROJECT_ID: project_id,
            ENV_ZENML_RUNAI_CLUSTER_ID: cluster_id,
        }
        if credential_id:
            metadata[ENV_ZENML_RUNAI_CREDENTIAL_ID] = credential_id

        if settings.synchronous:
            return SubmissionResult(
                wait_for_completion=lambda: self._wait_for_completion(
                    runai_client=runai_client,
                    workload_id=workload_identifier,
                    credential_id=credential_id
                    if settings.cleanup_created_credentials
                    else None,
                    created_credential=created_credential,
                    cleanup=settings.cleanup_created_credentials,
                ),
                metadata=metadata,
            )

        return SubmissionResult(metadata=metadata)

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
        return self.submit_pipeline(
            snapshot=snapshot,
            stack=stack,
            base_environment=environment,
            step_environments={},
            placeholder_run=placeholder_run,
        )

    def fetch_status(
        self, run: "PipelineRunResponse", include_steps: bool = False
    ) -> Tuple[
        Optional[ExecutionStatus], Optional[Dict[str, ExecutionStatus]]
    ]:
        """Refreshes the status of a specific pipeline run.

        Args:
            run: A pipeline run response to fetch its status.
            include_steps: If True, also fetch step statuses (not supported in MVP).

        Returns:
            Tuple of pipeline status and optional step statuses.

        Raises:
            RuntimeError: If Run:AI client initialization fails.
        """
        workload_id = run.run_metadata.get(ENV_ZENML_RUNAI_WORKLOAD_ID)
        if not workload_id:
            logger.warning(
                f"No Run:AI workload ID found for run {run.id}. "
                "Cannot fetch status."
            )
            return None, None

        runai_client = self._get_runai_client()

        try:
            workload = runai_client.workloads.trainings.get_training(
                workload_id
            )
            status = self._map_runai_status_to_execution_status(
                workload.status
            )

            return status, None

        except Exception as exc:
            logger.error(f"Failed to fetch Run:AI workload status: {exc}")
            return None, None

    def _get_runai_client(self) -> Any:
        """Initializes and returns a Run:AI client.

        Returns:
            Initialized Run:AI client.

        Raises:
            RuntimeError: If client initialization fails.
        """
        api_client_module = cast(
            Any, self._load_runai_module("runai.api_client")
        )
        configuration_module = cast(
            Any, self._load_runai_module("runai.configuration")
        )
        runai_client_module = cast(
            Any, self._load_runai_module("runai.runai_client")
        )

        config = configuration_module.Configuration(
            client_id=self.config.client_id,
            client_secret=self.config.client_secret.get_secret_value(),
            runai_base_url=self.config.runai_base_url,
        )
        return runai_client_module.RunaiClient(
            api_client_module.ApiClient(config)
        )

    def _resolve_project_and_cluster(
        self, runai_client: Any
    ) -> Tuple[str, str]:
        """Resolves Run:AI project and cluster IDs from names.

        Args:
            runai_client: Initialized Run:AI client.

        Returns:
            Tuple of (project_id, cluster_id).

        Raises:
            RuntimeError: If project or cluster cannot be resolved.
        """
        try:
            projects_resp = runai_client.organizations.projects.get_projects(
                search=self.config.project_name
            )

            projects_data = (
                projects_resp.data.get("projects", [])
                if projects_resp.data
                else []
            )

            project_id = None
            cluster_id = None
            for project in projects_data:
                project_name = project.get("name")
                if project_name == self.config.project_name:
                    project_id = str(project.get("id"))
                    cluster_id = project.get("clusterId")
                    break

            if not project_id:
                available_projects = [
                    p.get("name", "unknown") for p in projects_data
                ]
                raise RuntimeError(
                    f"Project '{self.config.project_name}' not found in Run:AI. "
                    f"Available projects: {available_projects}"
                )
            if self.config.cluster_name and cluster_id:
                try:
                    clusters_resp = (
                        runai_client.organizations.clusters.get_clusters()
                    )
                    clusters_data = (
                        clusters_resp.data if clusters_resp.data else []
                    )

                    found_cluster = None
                    for cluster in clusters_data:
                        if cluster.get("id") == cluster_id:
                            found_cluster = cluster
                            break

                    if found_cluster:
                        actual_cluster_name = found_cluster.get("name")
                        if actual_cluster_name != self.config.cluster_name:
                            logger.warning(
                                f"Configured cluster name '{self.config.cluster_name}' "
                                f"does not match project's cluster '{actual_cluster_name}'. "
                                f"Using project's cluster."
                            )

                except Exception as exc:
                    logger.warning(f"Could not verify cluster name: {exc}")

        except Exception as exc:
            raise RuntimeError(
                f"Failed to resolve Run:AI project '{self.config.project_name}': {exc}"
            ) from exc

        if not cluster_id:
            if self.config.cluster_name:
                try:
                    clusters_resp = (
                        runai_client.organizations.clusters.get_clusters()
                    )
                    clusters_data = (
                        clusters_resp.data if clusters_resp.data else []
                    )

                    for cluster in clusters_data:
                        if cluster.get("name") == self.config.cluster_name:
                            cluster_id = cluster.get("id")
                            break

                    if not cluster_id:
                        available_clusters = [
                            c.get("name", "unknown") for c in clusters_data
                        ]
                        raise RuntimeError(
                            f"Cluster '{self.config.cluster_name}' not found in Run:AI. "
                            f"Available clusters: {available_clusters}"
                        )

                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to resolve Run:AI cluster '{self.config.cluster_name}': {exc}"
                    ) from exc
            else:
                try:
                    clusters_resp = (
                        runai_client.organizations.clusters.get_clusters()
                    )
                    clusters_data = (
                        clusters_resp.data if clusters_resp.data else []
                    )

                    if not clusters_data:
                        raise RuntimeError("No Run:AI clusters available")

                    first = clusters_data[0]
                    cluster_id = first.get("id")

                except Exception as exc:
                    raise RuntimeError(
                        f"Failed to get Run:AI clusters: {exc}"
                    ) from exc

        return project_id, cluster_id

    def _get_workload_name(self, snapshot: "PipelineSnapshotResponse") -> str:
        """Generates a Run:AI workload name from the pipeline snapshot.

        Args:
            snapshot: The pipeline snapshot.

        Returns:
            A valid Run:AI workload name.
        """
        base_name = get_orchestrator_run_name(str(snapshot.pipeline.id))

        workload_name = base_name.lower().replace("_", "-")

        if workload_name and not workload_name[0].isalpha():
            workload_name = f"zenml-{workload_name}"

        if len(workload_name) > 50:
            workload_name = workload_name[:50]

        workload_name = workload_name.rstrip("-")

        return workload_name

    def _build_workload_name(
        self, snapshot: "PipelineSnapshotResponse"
    ) -> str:
        """Builds a unique workload name with a random suffix."""
        base_name = self._get_workload_name(snapshot)
        suffix = random_str(8).lower()
        # Run:AI requires max 50 chars, so truncate base_name to leave room for suffix
        max_base_len = 50 - len(suffix) - 1  # -1 for the hyphen
        base_name = base_name[:max_base_len].rstrip("-")
        return f"{base_name}-{suffix}"

    def _build_environment_variables(
        self,
        base_environment: Dict[str, str],
        additional_vars: Dict[str, str],
        runai_models: Any,
    ) -> List[Any]:
        """Builds Run:AI environment variables from dictionaries.

        Args:
            base_environment: Base environment variables.
            additional_vars: Additional environment variables from settings.
            runai_models: Loaded Run:AI models module.

        Returns:
            List of Run:AI EnvironmentVariable objects.
        """
        EnvironmentVariable = runai_models.EnvironmentVariable

        env_vars = [
            EnvironmentVariable(name=key, value=value)
            for key, value in base_environment.items()
        ]

        for key, value in additional_vars.items():
            env_vars = [var for var in env_vars if var.name != key]
            env_vars.append(EnvironmentVariable(name=key, value=value))

        return env_vars

    def _wait_for_completion(
        self,
        runai_client: Any,
        workload_id: str,
        credential_id: Optional[str] = None,
        created_credential: bool = False,
        cleanup: bool = False,
    ) -> None:
        """Waits for a Run:AI workload to complete.

        Args:
            runai_client: Initialized Run:AI client.
            workload_id: The workload ID to wait for.
            credential_id: Optional credential id to cleanup.
            created_credential: Whether the credential was created by this run.
            cleanup: Whether to delete the credential after completion.

        Raises:
            RuntimeError: If the workload fails or times out.
        """
        start_time = time.time()
        timeout = self.config.workload_timeout

        while True:
            if timeout and (time.time() - start_time) > timeout:
                raise RuntimeError(
                    f"Run:AI workload {workload_id} timed out after {timeout} seconds"
                )

            try:
                workload_resp = runai_client.workloads.trainings.get_training(
                    workload_id
                )
                if workload_resp.data and isinstance(workload_resp.data, dict):
                    status = workload_resp.data.get(
                        "actualPhase"
                    ) or workload_resp.data.get("status")
                else:
                    logger.warning(
                        f"Unexpected workload response structure: {workload_resp}"
                    )
                    status = None
                if status and status.lower() in [
                    "succeeded",
                    "completed",
                    "success",
                ]:
                    if cleanup and created_credential and credential_id:
                        self._delete_credential_if_needed(
                            runai_client=runai_client,
                            credential_id=credential_id,
                        )
                    return

                if status and status.lower() in ["failed", "error"]:
                    raise RuntimeError(
                        f"Run:AI workload {workload_id} failed with status: {status}"
                    )
                time.sleep(self.config.monitoring_interval)

            except Exception as exc:
                logger.error(f"Error querying workload status: {exc}")
                raise RuntimeError(
                    f"Failed to query Run:AI workload {workload_id}: {exc}"
                ) from exc

    def _ensure_registry_credential(
        self,
        runai_client: Any,
        stack: Stack,
        project_id: str,
        cluster_id: str,
    ) -> Tuple[Optional[str], bool, Optional[str]]:
        """Ensure a Docker registry credential exists for the stack registry.

        Best-effort: returns (credential_id, created_flag, credential_name). On any failure,
        logs and returns (None, False, None).

        Args:
            runai_client: Run:AI client instance.
            stack: The ZenML stack.
            project_id: Run:AI project ID.
            cluster_id: Run:AI cluster ID.

        Returns:
            Tuple of (credential_id, created_flag, credential_name)
        """
        try:
            container_registry = stack.container_registry
        except Exception as e:
            logger.warning(
                f"No container registry on stack; skipping credential creation. Error: {e}"
            )
            return None, False, None

        if not container_registry:
            logger.warning(
                "No container registry on stack; skipping credential creation."
            )
            return None, False, None

        registry_uri = container_registry.config.uri.rstrip("/")
        registry_host = registry_uri.removeprefix("https://").removeprefix(
            "http://"
        )
        credentials = container_registry.credentials

        if not credentials:
            logger.warning(
                "Container registry credentials not available; skipping Run:AI registry credential creation."
            )
            return None, False, None

        username, password = credentials
        runai_models = cast(Any, self._load_runai_module("runai.models"))
        AssetCreationRequest = runai_models.AssetCreationRequest
        DockerRegistryCreationRequest = runai_models.DockerRegistryCreationRequest
        DockerRegistryCreationSpec = runai_models.DockerRegistryCreationSpec
        Scope = runai_models.Scope

        sanitized_host = registry_host.lower()
        sanitized_host = "".join(
            c if c.isalnum() else "-" for c in sanitized_host
        )
        while "--" in sanitized_host:
            sanitized_host = sanitized_host.replace("--", "-")
        sanitized_host = sanitized_host.strip("-")

        # Include short cluster ID to create cluster-specific credentials
        # This avoids conflicts with stale tenant-scoped credentials
        cluster_suffix = cluster_id[:8] if cluster_id else ""
        credential_name = f"zenml-{cluster_suffix}-{sanitized_host}"
        # Ensure name doesn't exceed limits and is valid
        credential_name = credential_name[:63].rstrip("-")

        scope = Scope.CLUSTER

        try:
            credentials_api = runai_client.workload_assets.credentials
            existing = credentials_api.list_docker_registries(
                name=credential_name
            )

            credentials_list: List[Any] = []
            if existing.data:
                if isinstance(existing.data, list):
                    credentials_list = list(existing.data)
                elif isinstance(existing.data, dict):
                    entries = existing.data.get(
                        "credentials", existing.data.get("entries", [])
                    )
                    if isinstance(entries, list):
                        credentials_list = list(entries)

            logger.debug(
                f"Found {len(credentials_list)} existing docker registry credentials with name filter"
            )

            for cred in credentials_list:
                logger.debug(f"Checking credential: {cred}")
                # Handle both dict and Pydantic model objects
                if isinstance(cred, dict):
                    meta = cred.get("meta", {})
                else:
                    meta = getattr(cred, "meta", None)
                    if meta and not isinstance(meta, dict):
                        # Convert Pydantic model to dict-like access
                        meta = meta.__dict__ if hasattr(meta, "__dict__") else {}

                if not meta:
                    continue

                # Get values supporting both dict and object access
                def get_meta_value(key: str, fallback_key: str = None) -> Any:
                    if isinstance(meta, dict):
                        val = meta.get(key)
                        if val is None and fallback_key:
                            val = meta.get(fallback_key)
                        return val
                    val = getattr(meta, key, None)
                    if val is None and fallback_key:
                        val = getattr(meta, fallback_key, None)
                    return val

                meta_scope = get_meta_value("scope")
                if hasattr(meta_scope, "value"):
                    meta_scope = meta_scope.value
                meta_cluster = get_meta_value("cluster_id", "clusterId")

                # Only accept cluster-scoped credentials matching our cluster
                # Tenant-scoped credentials may have stale tokens
                is_matching_cluster = (
                    meta_scope == "cluster" and meta_cluster == cluster_id
                )

                if is_matching_cluster:
                    credential_id = get_meta_value("id")
                    logger.info(
                        "Reusing existing Run:AI docker registry credential %s (id=%s, scope=%s).",
                        credential_name,
                        credential_id,
                        meta_scope,
                    )
                    return credential_id, False, credential_name
        except Exception as exc:
            logger.warning(
                "Failed to list Run:AI docker registry credentials; will try to create new one. Error: %s",
                exc,
            )

        try:
            meta_dict = {
                "name": credential_name,
                "scope": scope,
            }

            if scope == Scope.CLUSTER:
                meta_dict["clusterId"] = cluster_id
            elif scope == Scope.PROJECT:
                meta_dict["projectId"] = project_id

            create_req = DockerRegistryCreationRequest(
                meta=AssetCreationRequest(**meta_dict),
                spec=DockerRegistryCreationSpec(
                    url=(
                        registry_uri
                        if registry_uri.startswith("http")
                        else f"https://{registry_uri}"
                    ),
                    user=username,
                    password=password,
                ),
            )
            created = credentials_api.create_docker_registry(
                docker_registry_creation_request=create_req
            )
            return created.meta.id, True, credential_name
        except Exception as exc:
            error_str = str(exc)
            if "409" in error_str or "already exists" in error_str.lower():
                logger.info(
                    "Credential %s already exists (409 Conflict), fetching existing credential...",
                    credential_name,
                )
                try:
                    existing_retry = credentials_api.list_docker_registries(
                        name=credential_name
                    )
                    creds_retry: List[Any] = []
                    if existing_retry.data:
                        if isinstance(existing_retry.data, list):
                            creds_retry = list(existing_retry.data)
                        elif isinstance(existing_retry.data, dict):
                            retry_entries = existing_retry.data.get(
                                "credentials",
                                existing_retry.data.get("entries", []),
                            )
                            if isinstance(retry_entries, list):
                                creds_retry = list(retry_entries)

                    for cred in creds_retry:
                        # Handle both dict and Pydantic model objects
                        if isinstance(cred, dict):
                            meta = cred.get("meta", {})
                        else:
                            meta = getattr(cred, "meta", None)
                            if meta and not isinstance(meta, dict):
                                meta = meta.__dict__ if hasattr(meta, "__dict__") else {}

                        if not meta:
                            continue

                        def get_val(key: str, fallback: str = None) -> Any:
                            if isinstance(meta, dict):
                                v = meta.get(key)
                                if v is None and fallback:
                                    v = meta.get(fallback)
                                return v
                            v = getattr(meta, key, None)
                            if v is None and fallback:
                                v = getattr(meta, fallback, None)
                            return v

                        meta_scope = get_val("scope")
                        if hasattr(meta_scope, "value"):
                            meta_scope = meta_scope.value
                        meta_cluster = get_val("cluster_id", "clusterId")

                        # Only accept cluster-scoped credentials matching our cluster
                        is_matching_cluster = (
                            meta_scope == "cluster" and meta_cluster == cluster_id
                        )

                        if is_matching_cluster:
                            credential_id = get_val("id")
                            logger.info(
                                "Found existing credential %s with id=%s, scope=%s",
                                credential_name,
                                credential_id,
                                meta_scope,
                            )
                            return credential_id, False, credential_name

                    logger.warning(
                        "Credential %s exists but no matching cluster-scoped version found for cluster %s",
                        credential_name,
                        cluster_id,
                    )
                except Exception as retry_exc:
                    logger.warning(
                        "Failed to fetch existing credential after 409: %s",
                        retry_exc,
                    )

            logger.warning(
                "Failed to create Run:AI docker registry credential automatically. "
                "Workloads may fail to pull images if registry requires auth. "
                "Error: %s",
                exc,
            )
            return None, False, None

    def _delete_credential_if_needed(
        self, runai_client: Any, credential_id: str
    ) -> None:
        """Delete a Run:AI docker registry credential, ignoring errors."""
        try:
            runai_client.workload_assets.credentials.delete_docker_registry(
                credential_id
            )
        except Exception as exc:
            logger.warning(
                "Failed to delete auto-created Run:AI docker registry credential id=%s: %s",
                credential_id,
                exc,
            )

    def _map_runai_status_to_execution_status(
        self, runai_status: str
    ) -> ExecutionStatus:
        """Maps Run:AI workload status to ZenML ExecutionStatus.

        Args:
            runai_status: The Run:AI workload status string.

        Returns:
            The corresponding ZenML ExecutionStatus.
        """
        if not runai_status:
            return ExecutionStatus.RUNNING

        status = runai_status.lower()

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

        return status_mapping.get(status, ExecutionStatus.RUNNING)
