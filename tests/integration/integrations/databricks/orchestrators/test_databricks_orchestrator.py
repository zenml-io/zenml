#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Tests for the Databricks orchestrator."""

import importlib.util
from datetime import datetime
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest

from zenml.enums import StackComponentType

DATABRICKS_INSTALLED = importlib.util.find_spec("databricks") is not None
pytestmark = pytest.mark.skipif(
    not DATABRICKS_INSTALLED, reason="databricks dependency is not installed."
)

if DATABRICKS_INSTALLED:
    from zenml.integrations.databricks.flavors.databricks_orchestrator_flavor import (
        DatabricksOrchestratorConfig,
        DatabricksOrchestratorSettings,
    )
    from zenml.integrations.databricks.orchestrators.databricks_orchestrator import (
        DatabricksOrchestrator,
    )
else:
    DatabricksOrchestrator = Any
    DatabricksOrchestratorConfig = Any
    DatabricksOrchestratorSettings = Any


def _get_databricks_orchestrator() -> DatabricksOrchestrator:
    """Create a Databricks orchestrator for testing."""
    return DatabricksOrchestrator(
        name="databricks",
        id=uuid4(),
        config=DatabricksOrchestratorConfig(
            host="https://workspace.cloud.databricks.com",
            client_id="client-id",
            client_secret="client-secret",
        ),
        flavor="databricks",
        type=StackComponentType.ORCHESTRATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )


def _get_databricks_client(job_id: int = 123) -> SimpleNamespace:
    """Create a mock Databricks workspace client."""
    return SimpleNamespace(
        config=SimpleNamespace(host="https://workspace.cloud.databricks.com"),
        cluster_policies=SimpleNamespace(list=lambda: []),
        jobs=SimpleNamespace(
            create=lambda **kwargs: SimpleNamespace(job_id=job_id),
            run_now=lambda **kwargs: None,
        ),
    )


def test_upload_and_run_pipeline_forwards_settings_to_job_payload(
    mocker: Any,
) -> None:
    """Tests orchestrator Databricks job and cluster payload construction."""
    orchestrator = _get_databricks_orchestrator()
    databricks_client = _get_databricks_client()
    databricks_client.jobs.create = mocker.Mock(
        return_value=SimpleNamespace(job_id=123)
    )
    databricks_client.jobs.run_now = mocker.Mock()
    mocker.patch.object(
        orchestrator,
        "_get_databricks_client",
        return_value=databricks_client,
    )
    settings = DatabricksOrchestratorSettings(
        access_control_list=[
            {
                "group_name": "data-science",
                "permission_level": "CAN_VIEW",
            }
        ],
        availability_type="SPOT",
        custom_tags={"cluster-owner": "ml-team"},
        docker_image_url="registry.example.com/ml:latest",
        docker_image_username="docker-user",
        docker_image_password="docker-password",
        init_scripts=["dbfs:/scripts/install_dependencies.sh"],
        job_tags={"project": "recommender"},
        max_concurrent_runs=3,
        max_retries=2,
        min_retry_interval_millis=60000,
        retry_on_timeout=True,
        task_timeout_seconds=3600,
        timeout_seconds=7200,
    )
    task = SimpleNamespace(
        task_key="step",
        as_dict=lambda: {},
    )

    orchestrator._upload_and_run_pipeline(
        pipeline_name="training-pipeline",
        settings=settings,
        tasks=[task],
        env_vars={"ENV_KEY": "ENV_VALUE"},
        job_cluster_key="job-cluster",
    )

    databricks_client.jobs.create.assert_called_once()
    payload = databricks_client.jobs.create.call_args.kwargs
    cluster_payload = payload["job_clusters"][0].new_cluster.as_dict()
    access_control_payload = [
        access_control.as_dict()
        for access_control in payload["access_control_list"]
    ]

    assert payload["name"] == "training-pipeline"
    assert payload["tasks"] == [task]
    assert payload["tags"] == {"project": "recommender"}
    assert payload["timeout_seconds"] == 7200
    assert payload["max_concurrent_runs"] == 3
    assert access_control_payload == [
        {"group_name": "data-science", "permission_level": "CAN_VIEW"}
    ]
    assert cluster_payload["spark_env_vars"] == {"ENV_KEY": "ENV_VALUE"}
    assert cluster_payload["custom_tags"] == {"cluster-owner": "ml-team"}
    assert cluster_payload["aws_attributes"]["availability"] == "SPOT"
    assert cluster_payload["docker_image"] == {
        "url": "registry.example.com/ml:latest",
        "basic_auth": {
            "username": "docker-user",
            "password": "docker-password",
        },
    }
    assert cluster_payload["init_scripts"] == [
        {"dbfs": {"destination": "dbfs:/scripts/install_dependencies.sh"}}
    ]
    databricks_client.jobs.run_now.assert_called_once_with(job_id=123)
