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
"""Tests for ModalSandboxExecutor pipeline and step resource merging."""

from unittest.mock import Mock, patch
from uuid import uuid4

from zenml.config.resource_settings import ResourceSettings
from zenml.integrations.modal.flavors.modal_orchestrator_flavor import (
    ModalOrchestratorSettings,
)


class TestModalSandboxExecutorResourceMerging:
    """Test resource merging between pipeline and step settings."""

    def setup_method(self):
        """Set up test fixtures."""
        # Mock Modal library
        self.modal_patcher = patch(
            "zenml.integrations.modal.orchestrators.modal_sandbox_executor.modal"
        )
        self.modal_patcher.start()

        # Mock utils functions
        self.utils_patcher = patch(
            "zenml.integrations.modal.orchestrators.modal_sandbox_executor.get_resource_settings_from_deployment"
        )
        self.mock_get_resource_settings = self.utils_patcher.start()

        # Create mock deployment
        self.mock_deployment = Mock()
        self.mock_deployment.id = uuid4()
        self.mock_deployment.build = Mock()
        self.mock_deployment.build.id = uuid4()
        self.mock_deployment.pipeline_configuration = Mock()
        self.mock_deployment.pipeline_configuration.name = "test_pipeline"

        # Pipeline-level settings
        self.pipeline_settings = ModalOrchestratorSettings(
            gpu="A100", timeout=3600, cloud="aws", region="us-east-1"
        )

    def teardown_method(self):
        """Clean up after each test method."""
        self.modal_patcher.stop()
        self.utils_patcher.stop()

    def _create_executor(self, **kwargs):
        """Helper to create ModalSandboxExecutor with mocked dependencies."""
        from zenml.integrations.modal.orchestrators.modal_sandbox_executor import (
            ModalSandboxExecutor,
        )

        return ModalSandboxExecutor(
            deployment=self.mock_deployment,
            stack=Mock(),
            environment={},
            settings=self.pipeline_settings,
            **kwargs,
        )

    def test_step_resources_override_pipeline_resources(self):
        """Test that step-level resources override pipeline-level resources."""
        step_name = "test_step"

        # Step has specific resource requirements
        step_resources = ResourceSettings(
            cpu_count=8, memory="16GB", gpu_count=2
        )
        mock_step_config = Mock()
        mock_step_config.resource_settings = step_resources
        mock_step_config.settings = {}

        self.mock_deployment.step_configurations = {
            step_name: Mock(config=mock_step_config)
        }

        # Pipeline has different defaults
        pipeline_resources = ResourceSettings(
            cpu_count=4, memory="8GB", gpu_count=1
        )
        self.mock_get_resource_settings.return_value = pipeline_resources

        executor = self._create_executor()

        # Step should get its specific resources, not pipeline defaults
        step_result = executor._get_resource_settings(step_name)
        pipeline_result = executor._get_resource_settings(None)

        assert step_result == step_resources
        assert pipeline_result == pipeline_resources
        assert step_result.cpu_count == 8  # Step override
        assert pipeline_result.cpu_count == 4  # Pipeline default

    def test_step_modal_settings_override_pipeline_settings(self):
        """Test that step-level Modal settings override pipeline settings."""
        step_name = "test_step"

        # Step overrides GPU and region
        step_modal_settings = Mock()
        step_modal_settings.model_dump.return_value = {
            "gpu": "V100",
            "region": "us-west-2",
        }

        mock_step_config = Mock()
        mock_step_config.settings = {"orchestrator.modal": step_modal_settings}

        self.mock_deployment.step_configurations = {
            step_name: Mock(config=mock_step_config)
        }

        executor = self._create_executor()
        result = executor._get_settings(step_name)

        # Step overrides should take precedence
        assert result.gpu == "V100"  # Step override
        assert result.region == "us-west-2"  # Step override
        assert result.cloud == "aws"  # Pipeline default (not overridden)
        assert result.timeout == 3600  # Pipeline default (not overridden)

    def test_partial_step_overrides_preserve_pipeline_defaults(self):
        """Test that partial step overrides preserve non-overridden pipeline settings."""
        step_name = "test_step"

        # Step only overrides GPU
        step_modal_settings = Mock()
        step_modal_settings.model_dump.return_value = {"gpu": "T4"}

        mock_step_config = Mock()
        mock_step_config.settings = {"orchestrator.modal": step_modal_settings}

        self.mock_deployment.step_configurations = {
            step_name: Mock(config=mock_step_config)
        }

        executor = self._create_executor()
        result = executor._get_settings(step_name)

        assert result.gpu == "T4"  # Step override
        assert result.cloud == "aws"  # Pipeline default preserved
        assert result.region == "us-east-1"  # Pipeline default preserved
        assert result.timeout == 3600  # Pipeline default preserved

    @patch(
        "zenml.integrations.modal.orchestrators.modal_sandbox_executor.get_gpu_values"
    )
    @patch(
        "zenml.integrations.modal.orchestrators.modal_sandbox_executor.get_resource_values"
    )
    def test_complete_resource_merging_integration(
        self, mock_get_resource_values, mock_get_gpu_values
    ):
        """Integration test for complete resource merging between pipeline and step."""
        step_name = "integration_step"

        # Step has specific resources and Modal settings
        step_resources = ResourceSettings(
            cpu_count=16, memory="32GB", gpu_count=4
        )
        step_modal_settings = Mock()
        step_modal_settings.model_dump.return_value = {
            "gpu": "A100",
            "cloud": "gcp",
            "region": "us-central1",
        }

        mock_step_config = Mock()
        mock_step_config.resource_settings = step_resources
        mock_step_config.settings = {"orchestrator.modal": step_modal_settings}

        self.mock_deployment.step_configurations = {
            step_name: Mock(config=mock_step_config)
        }

        # Mock utility function returns
        mock_get_gpu_values.return_value = "A100:4"
        mock_get_resource_values.return_value = (16, 32000)

        executor = self._create_executor()

        # Test resource configuration
        gpu_values, cpu_count, memory_mb = executor._get_resource_config(
            step_name
        )

        # Test step settings
        step_settings = executor._get_settings(step_name)

        # Assert step resources are used
        assert gpu_values == "A100:4"
        assert cpu_count == 16
        assert memory_mb == 32000

        # Assert step Modal settings override pipeline where specified
        assert step_settings.gpu == "A100"  # Step override
        assert step_settings.cloud == "gcp"  # Step override
        assert step_settings.region == "us-central1"  # Step override
        assert (
            step_settings.timeout == 3600
        )  # Pipeline default (not overridden)

        # Verify utility functions called with step resources
        mock_get_gpu_values.assert_called_once_with("A100", step_resources)
        mock_get_resource_values.assert_called_once_with(step_resources)

    def test_fallback_to_pipeline_when_no_step_config(self):
        """Test fallback to pipeline settings when step has no specific configuration."""
        step_name = "minimal_step"

        # Step has no resource settings or Modal settings
        mock_step_config = Mock()
        mock_step_config.resource_settings = None
        mock_step_config.settings = {}

        self.mock_deployment.step_configurations = {
            step_name: Mock(config=mock_step_config)
        }

        executor = self._create_executor()

        # Should get empty ResourceSettings (fallback)
        step_resources = executor._get_resource_settings(step_name)
        assert isinstance(step_resources, ResourceSettings)
        assert step_resources.cpu_count is None

        # Should get pipeline Modal settings (fallback)
        step_settings = executor._get_settings(step_name)
        assert step_settings.gpu == "A100"  # Pipeline setting
        assert step_settings.cloud == "aws"  # Pipeline setting
        assert step_settings.region == "us-east-1"  # Pipeline setting
