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


from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from zenml.enums import StackComponentType
from zenml.integrations.aws.flavors import SagemakerOrchestratorFlavor
from zenml.integrations.aws.flavors.sagemaker_orchestrator_flavor import (
    SagemakerOrchestratorSettings,
)
from zenml.integrations.aws.orchestrators.sagemaker_orchestrator import (
    SagemakerOrchestrator,
)


def test_sagemaker_orchestrator_flavor_attributes():
    """Tests that the basic attributes of the sagemaker orchestrator flavor are
    set correctly."""
    flavor = SagemakerOrchestratorFlavor()
    assert flavor.type == StackComponentType.ORCHESTRATOR
    assert flavor.name == "sagemaker"


def test_compute_schedule_metadata():
    """Tests that schedule metadata is computed correctly."""
    # Setup
    orchestrator = SagemakerOrchestrator(
        name="test_orchestrator",
        id="test-id",
        config={},
        flavor="sagemaker",
        type="orchestrator",
        user="test-user",
        workspace="test-workspace",
        created="2023-01-01",
        updated="2023-01-01",
    )
    settings = SagemakerOrchestratorSettings()

    # Mock schedule info with timezone-aware datetime in UTC
    next_execution = datetime.now(timezone.utc) + timedelta(hours=1)
    schedule_info = {
        "rule_name": "test-rule",
        "schedule_type": "rate",
        "schedule_expr": "rate(1 hour)",
        "pipeline_name": "test-pipeline",
        "next_execution": next_execution,
        "region": "us-west-2",
        "account_id": "123456789012",
    }

    # Mock boto3 session and SageMaker client
    mock_sagemaker_client = MagicMock()
    mock_sagemaker_client.list_domains.return_value = {
        "Domains": [{"DomainId": "d-test123"}]
    }

    with patch("boto3.Session") as mock_session:
        mock_session.return_value.client.return_value = mock_sagemaker_client

        # Get metadata
        metadata = next(
            orchestrator.compute_metadata(
                execution=schedule_info,
                settings=settings,
            )
        )

    # Verify schedule-specific metadata
    assert metadata["schedule_rule_name"] == "test-rule"
    assert metadata["schedule_type"] == "rate"
    assert metadata["schedule_expression"] == "rate(1 hour)"
    assert metadata["pipeline_name"] == "test-pipeline"
    assert metadata["next_execution_time"] == next_execution.isoformat()


def test_compute_schedule_metadata_error_handling():
    """Tests error handling in schedule metadata computation."""
    orchestrator = SagemakerOrchestrator(
        name="test_orchestrator",
        id="test-id",
        config={},
        flavor="sagemaker",
        type="orchestrator",
        user="test-user",
        workspace="test-workspace",
        created="2023-01-01",
        updated="2023-01-01",
    )
    settings = SagemakerOrchestratorSettings()

    # Invalid schedule info missing required fields
    schedule_info = {
        "rule_name": "test-rule",
        "schedule_type": "rate",  # Add minimum required fields
        "schedule_expr": "rate(1 hour)",
        "pipeline_name": "test-pipeline",
    }

    with patch("boto3.Session") as mock_session:
        mock_session.side_effect = Exception("Failed to create session")

        # Get metadata - should not raise exception
        metadata = next(
            orchestrator.compute_metadata(
                execution=schedule_info,
                settings=settings,
            )
        )

        # Basic metadata should still be present
        assert metadata["schedule_rule_name"] == "test-rule"
        assert metadata["schedule_type"] == "rate"
        assert metadata["schedule_expression"] == "rate(1 hour)"
        assert metadata["pipeline_name"] == "test-pipeline"
