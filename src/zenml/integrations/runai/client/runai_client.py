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
"""Run:AI API client wrapper with typed responses."""

from typing import Any, List, Optional, cast

from pydantic import BaseModel, ConfigDict, Field
from runai.api_client import ApiClient
from runai.configuration import Configuration
from runai.models.training_creation_request import TrainingCreationRequest
from runai.runai_client import RunaiClient as RunapyClient

from zenml.logger import get_logger

logger = get_logger(__name__)


class RunAIClientError(Exception):
    """Base exception for Run:AI client errors."""


class RunAIAuthenticationError(RunAIClientError):
    """Raised when authentication with Run:AI fails."""


class RunAIConnectionError(RunAIClientError):
    """Raised when connection to Run:AI API fails."""


class RunAIProjectNotFoundError(RunAIClientError):
    """Raised when a Run:AI project cannot be found."""

    def __init__(self, project_name: str, available: List[str]) -> None:
        """Initialize the exception.

        Args:
            project_name: The project name that was not found.
            available: List of available project names.
        """
        self.project_name = project_name
        self.available = available
        super().__init__(
            f"Project '{project_name}' not found in Run:AI. "
            f"Available projects: {available}"
        )


class RunAIClusterNotFoundError(RunAIClientError):
    """Raised when a Run:AI cluster cannot be found."""

    def __init__(self, cluster_name: str, available: List[str]) -> None:
        """Initialize the exception.

        Args:
            cluster_name: The cluster name that was not found.
            available: List of available cluster names.
        """
        self.cluster_name = cluster_name
        self.available = available
        super().__init__(
            f"Cluster '{cluster_name}' not found in Run:AI. "
            f"Available clusters: {available}"
        )


class RunAIWorkloadNotFoundError(RunAIClientError):
    """Raised when a Run:AI workload cannot be found."""

    def __init__(self, workload_id: str) -> None:
        """Initialize the exception.

        Args:
            workload_id: The workload ID that was not found.
        """
        self.workload_id = workload_id
        super().__init__(f"Workload '{workload_id}' not found in Run:AI.")


class RunAIProject(BaseModel):
    """Typed representation of a Run:AI project."""

    id: str
    name: str
    cluster_id: Optional[str] = None


class RunAICluster(BaseModel):
    """Typed representation of a Run:AI cluster."""

    id: str
    name: str


class WorkloadSubmissionResult(BaseModel):
    """Result of submitting a workload to Run:AI."""

    workload_id: str
    workload_name: str


class RunAITrainingWorkload(BaseModel):
    """Typed representation of a Run:AI training workload."""

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    id: Optional[str] = None
    workload_id: Optional[str] = Field(default=None, alias="workloadId")
    name: Optional[str] = None
    actual_phase: Optional[str] = Field(default=None, alias="actualPhase")
    status: Optional[str] = None


class RunAIClient:
    """Wrapper around the runapy SDK providing typed responses.

    This client encapsulates all Run:AI API interactions and provides
    typed dataclasses instead of raw dictionaries.
    """

    def __init__(
        self, client_id: str, client_secret: str, runai_base_url: str
    ) -> None:
        """Initialize the Run:AI client.

        Args:
            client_id: Run:AI client ID for authentication.
            client_secret: Run:AI client secret for authentication.
            runai_base_url: Run:AI control plane base URL.

        Raises:
            RunAIAuthenticationError: If client configuration fails.
        """
        try:
            config = Configuration(
                client_id=client_id,
                client_secret=client_secret,
                runai_base_url=runai_base_url,
            )
            self._raw_client = self._create_raw_client(config)
        except Exception as exc:
            raise RunAIAuthenticationError(
                f"Failed to initialize Run:AI client ({type(exc).__name__}): {exc}. "
                "Verify your client_id, client_secret, and runai_base_url are correct."
            ) from exc

    def _create_raw_client(self, config: Configuration) -> RunapyClient:
        """Create the underlying runapy client.

        The runai SDK does not ship type hints, so keep the untyped call
        isolated to this helper.
        """
        return RunapyClient(ApiClient(config))  # type: ignore[no-untyped-call]

    @property
    def raw_client(self) -> RunapyClient:
        """Access the underlying runapy client for advanced operations.

        Returns:
            The raw runapy client.
        """
        return self._raw_client

    def get_projects(self, search: Optional[str] = None) -> List[RunAIProject]:
        """Get Run:AI projects, optionally filtered by name.

        Args:
            search: Optional search string to filter projects.

        Returns:
            List of RunAIProject objects.

        Raises:
            RunAIClientError: If the API call fails.
        """
        try:
            response = self._raw_client.organizations.projects.get_projects(
                search=search
            )
            projects_data = (
                response.data.get("projects", []) if response.data else []
            )

            return [
                RunAIProject(
                    id=str(p.get("id")),
                    name=p.get("name", ""),
                    cluster_id=p.get("clusterId"),
                )
                for p in projects_data
            ]
        except RunAIClientError:
            raise
        except Exception as exc:
            raise RunAIClientError(
                f"Failed to fetch Run:AI projects ({type(exc).__name__}): {exc}"
            ) from exc

    def get_project_by_name(self, name: str) -> RunAIProject:
        """Get a Run:AI project by exact name match.

        Args:
            name: The project name to find.

        Returns:
            The matching RunAIProject.

        Raises:
            RunAIProjectNotFoundError: If no project matches the name.
        """
        projects = self.get_projects(search=name)

        for project in projects:
            if project.name == name:
                return project

        available = [p.name for p in projects]
        raise RunAIProjectNotFoundError(name, available)

    def get_clusters(self) -> List[RunAICluster]:
        """Get all Run:AI clusters.

        Returns:
            List of RunAICluster objects.

        Raises:
            RunAIClientError: If the API call fails.
        """
        try:
            response = self._raw_client.organizations.clusters.get_clusters()
            clusters_data = response.data if response.data else []

            return [
                RunAICluster(
                    id=c.get("uuid", c.get("id", "")),
                    name=c.get("name", ""),
                )
                for c in clusters_data
            ]
        except RunAIClientError:
            raise
        except Exception as exc:
            raise RunAIClientError(
                f"Failed to fetch Run:AI clusters ({type(exc).__name__}): {exc}"
            ) from exc

    def get_cluster_by_id(self, cluster_id: str) -> Optional[RunAICluster]:
        """Get a Run:AI cluster by ID.

        Args:
            cluster_id: The cluster ID to find.

        Returns:
            The matching RunAICluster or None if not found.
        """
        clusters = self.get_clusters()
        for cluster in clusters:
            if cluster.id == cluster_id:
                return cluster
        return None

    def get_cluster_by_name(self, name: str) -> RunAICluster:
        """Get a Run:AI cluster by exact name match.

        Args:
            name: The cluster name to find.

        Returns:
            The matching RunAICluster.

        Raises:
            RunAIClusterNotFoundError: If no cluster matches the name.
        """
        clusters = self.get_clusters()

        for cluster in clusters:
            if cluster.name == name:
                return cluster

        available = [c.name for c in clusters]
        raise RunAIClusterNotFoundError(name, available)

    def get_first_cluster(self) -> RunAICluster:
        """Get the first available Run:AI cluster.

        Returns:
            The first RunAICluster.

        Raises:
            RunAIClientError: If no clusters are available.
        """
        clusters = self.get_clusters()
        if not clusters:
            raise RunAIClientError("No Run:AI clusters available")
        return clusters[0]

    def create_training_workload(
        self, request: TrainingCreationRequest
    ) -> WorkloadSubmissionResult:
        """Submit a training workload to Run:AI.

        Args:
            request: TrainingCreationRequest from runai.models.

        Returns:
            WorkloadSubmissionResult with the workload ID.

        Raises:
            RunAIClientError: If submission fails.
        """
        try:
            response = self._raw_client.workloads.trainings.create_training1(
                training_creation_request=request
            )
            workload_id = self._extract_workload_id(response)
            return WorkloadSubmissionResult(
                workload_id=workload_id or request.name,
                workload_name=request.name,
            )
        except RunAIClientError:
            raise
        except Exception as exc:
            raise RunAIClientError(
                f"Failed to submit Run:AI workload ({type(exc).__name__}): {exc}"
            ) from exc

    def _extract_workload_id(self, response: Any) -> Optional[str]:
        """Extract workload ID from API response.

        Args:
            response: The API response object.

        Returns:
            The workload ID or None.
        """
        if not response.data:
            return None

        if isinstance(response.data, dict):
            return (
                response.data.get("workloadId")
                or response.data.get("id")
                or response.data.get("workload_id")
            )
        return getattr(response.data, "workloadId", None) or getattr(
            response.data, "id", None
        )

    def get_training_workload_status(self, workload_id: str) -> Optional[str]:
        """Get the status of a training workload.

        Args:
            workload_id: The workload ID to query.

        Returns:
            The workload status string, or None if the response is missing a
            status field.

        Raises:
            RunAIWorkloadNotFoundError: If the workload was not found (404).
            RunAIClientError: If the API call fails for other reasons or the
                response is malformed.
        """
        try:
            response = self._raw_client.workloads.trainings.get_training(
                workload_id
            )
            if not response.data:
                raise RunAIClientError(
                    f"Empty response when querying workload {workload_id}. "
                    "The API returned no data."
                )
            if not isinstance(response.data, dict):
                raise RunAIClientError(
                    f"Unexpected response format for workload {workload_id}. "
                    f"Expected dict, got {type(response.data).__name__}."
                )
            status = response.data.get("actualPhase") or response.data.get(
                "status"
            )
            if status is None:
                logger.warning(
                    f"Workload {workload_id} response has no status field. "
                    "Available keys: %s",
                    list(response.data.keys()),
                )
            return cast(Optional[str], status)
        except RunAIClientError:
            raise
        except Exception as exc:
            error_msg = str(exc).lower()
            if "not found" in error_msg or "404" in error_msg:
                raise RunAIWorkloadNotFoundError(workload_id) from exc
            raise RunAIClientError(
                f"Failed to query workload status ({type(exc).__name__}): {exc}"
            ) from exc

    def get_training_workload(self, workload_id: str) -> RunAITrainingWorkload:
        """Get full training workload details.

        Args:
            workload_id: The workload ID to query.

        Returns:
            The workload details as a typed model.

        Raises:
            RunAIClientError: If the query fails or response is invalid.
        """
        try:
            response = self._raw_client.workloads.trainings.get_training(
                workload_id
            )
            if not response.data:
                raise RunAIClientError(
                    f"Empty response when querying workload {workload_id}. "
                    "The workload may not exist or the API returned no data."
                )
            if not isinstance(response.data, dict):
                raise RunAIClientError(
                    f"Unexpected response format for workload {workload_id}. "
                    f"Expected dict, got {type(response.data).__name__}."
                )
            return RunAITrainingWorkload.model_validate(response.data)
        except RunAIClientError:
            raise
        except Exception as exc:
            raise RunAIClientError(
                f"Failed to query Run:AI workload {workload_id} ({type(exc).__name__}): {exc}"
            ) from exc

    def delete_training_workload(self, workload_id: str) -> None:
        """Delete a training workload.

        Args:
            workload_id: The workload ID to delete.

        Raises:
            RunAIClientError: If deletion fails.
        """
        try:
            self._raw_client.workloads.trainings.delete_training(workload_id)
        except RunAIClientError:
            raise
        except Exception as exc:
            raise RunAIClientError(
                f"Failed to delete Run:AI workload {workload_id} ({type(exc).__name__}): {exc}"
            ) from exc

    def suspend_training_workload(self, workload_id: str) -> None:
        """Suspend a training workload.

        Args:
            workload_id: The workload ID to suspend.

        Raises:
            RunAIClientError: If suspending fails.
        """
        try:
            self._raw_client.workloads.trainings.suspend_training(workload_id)
        except RunAIClientError:
            raise
        except Exception as exc:
            raise RunAIClientError(
                f"Failed to suspend Run:AI workload {workload_id} ({type(exc).__name__}): {exc}"
            ) from exc
