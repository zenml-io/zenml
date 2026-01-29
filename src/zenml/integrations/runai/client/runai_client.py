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

import importlib
from typing import Any, Dict, List, Optional, cast

from pydantic import BaseModel

from zenml.logger import get_logger

logger = get_logger(__name__)


class RunAIClientError(Exception):
    """Base exception for Run:AI client errors."""


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
            RuntimeError: If the runapy package is not installed.
        """
        self._raw_client = self._create_client(
            client_id, client_secret, runai_base_url
        )

    def _load_module(self, module_path: str) -> Any:
        """Load a Run:AI SDK module.

        Args:
            module_path: The module path to import.

        Returns:
            The imported module.

        Raises:
            RuntimeError: If the runapy package is not installed.
        """
        try:
            return importlib.import_module(module_path)
        except ImportError as exc:
            raise RuntimeError(
                "The runapy package is required to use the Run:AI client. "
                "Please install it with: pip install runapy"
            ) from exc

    def _create_client(
        self, client_id: str, client_secret: str, runai_base_url: str
    ) -> Any:
        """Create the underlying runapy client.

        Args:
            client_id: Run:AI client ID.
            client_secret: Run:AI client secret.
            runai_base_url: Run:AI base URL.

        Returns:
            Initialized runapy client.
        """
        api_client_module = self._load_module("runai.api_client")
        configuration_module = self._load_module("runai.configuration")
        runai_client_module = self._load_module("runai.runai_client")

        config = configuration_module.Configuration(
            client_id=client_id,
            client_secret=client_secret,
            runai_base_url=runai_base_url,
        )
        return runai_client_module.RunaiClient(
            api_client_module.ApiClient(config)
        )

    @property
    def raw_client(self) -> Any:
        """Access the underlying runapy client for advanced operations.

        Returns:
            The raw runapy client.
        """
        return self._raw_client

    @property
    def models(self) -> Any:
        """Load the runai.models module.

        Returns:
            The runai.models module.
        """
        return self._load_module("runai.models")

    def get_projects(self, search: Optional[str] = None) -> List[RunAIProject]:
        """Get Run:AI projects, optionally filtered by name.

        Args:
            search: Optional search string to filter projects.

        Returns:
            List of RunAIProject objects.
        """
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
        """
        response = self._raw_client.organizations.clusters.get_clusters()
        clusters_data = response.data if response.data else []

        return [
            RunAICluster(
                id=c.get("uuid", c.get("id", "")),
                name=c.get("name", ""),
            )
            for c in clusters_data
        ]

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
        self, request: Any
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
        except Exception as exc:
            raise RunAIClientError(
                f"Failed to submit Run:AI workload: {exc}"
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
            The workload status string or None.
        """
        try:
            response = self._raw_client.workloads.trainings.get_training(
                workload_id
            )
            if response.data and isinstance(response.data, dict):
                status = response.data.get("actualPhase") or response.data.get(
                    "status"
                )
                return cast(Optional[str], status)
            return None
        except Exception as exc:
            logger.error(f"Failed to get workload status: {exc}")
            return None

    def get_training_workload(self, workload_id: str) -> Dict[str, Any]:
        """Get full training workload details.

        Args:
            workload_id: The workload ID to query.

        Returns:
            The workload data dictionary.

        Raises:
            RunAIClientError: If the query fails.
        """
        try:
            response = self._raw_client.workloads.trainings.get_training(
                workload_id
            )
            if response.data and isinstance(response.data, dict):
                return cast(Dict[str, Any], response.data)
            return {}
        except Exception as exc:
            raise RunAIClientError(
                f"Failed to query Run:AI workload {workload_id}: {exc}"
            ) from exc