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
"""Unit tests for alerter hooks."""

from unittest.mock import MagicMock, patch

from zenml.hooks.alerter_hooks import (
    alerter_failure_hook,
    alerter_success_hook,
)
from zenml.models.v2.misc.alerter_models import AlerterMessage


class TestAlerterHooks:
    """Test alerter hooks with both AlerterMessage and legacy string formats."""

    @patch("zenml.hooks.alerter_hooks.get_step_context")
    @patch("zenml.hooks.alerter_hooks.Client")
    def test_failure_hook_with_alerter_message(
        self, mock_client, mock_get_context
    ):
        """Test failure hook uses AlerterMessage format."""
        # Setup mocks
        mock_context = MagicMock()
        mock_context.pipeline.name = "test_pipeline"
        mock_context.pipeline_run.name = "test_run"
        mock_context.step_run.name = "test_step"
        mock_context.step_run.config.parameters = {"param": "value"}
        mock_get_context.return_value = mock_context

        mock_alerter = MagicMock()
        mock_client.return_value.active_stack.alerter = mock_alerter
        mock_client.return_value.active_stack.name = "test_stack"

        # Create test exception
        test_exception = ValueError("Test error")

        # Call the hook
        alerter_failure_hook(test_exception)

        # Verify alerter.post was called
        assert mock_alerter.post.called

        # Get the message passed to alerter.post
        call_args = mock_alerter.post.call_args
        message = call_args[0][0]

        # Verify it's an AlerterMessage
        assert isinstance(message, AlerterMessage)
        assert message.title == "Pipeline Failure Alert"
        assert "test_step" in message.body
        assert "test_pipeline" in message.body
        assert "ValueError" in message.body
        assert message.metadata["pipeline_name"] == "test_pipeline"
        assert message.metadata["exception_type"] == "ValueError"

    @patch("zenml.hooks.alerter_hooks.get_step_context")
    @patch("zenml.hooks.alerter_hooks.Client")
    def test_failure_hook_fallback_to_string(
        self, mock_client, mock_get_context
    ):
        """Test failure hook falls back to string format on error."""
        # Setup mocks
        mock_context = MagicMock()
        mock_context.pipeline.name = "test_pipeline"
        mock_context.pipeline_run.name = "test_run"
        mock_context.step_run.name = "test_step"
        mock_context.step_run.config.parameters = {"param": "value"}
        mock_get_context.return_value = mock_context

        mock_alerter = MagicMock()
        # Make AlerterMessage import fail to trigger fallback
        mock_alerter.post.side_effect = [
            ImportError("AlerterMessage not found"),  # First call fails
            None,  # Second call succeeds
        ]
        mock_client.return_value.active_stack.alerter = mock_alerter

        # Create test exception
        test_exception = ValueError("Test error")

        # Call the hook
        alerter_failure_hook(test_exception)

        # Verify alerter.post was called twice (first failed, then fallback)
        assert mock_alerter.post.call_count == 2

        # Get the fallback message
        second_call_args = mock_alerter.post.call_args_list[1]
        message = second_call_args[0][0]

        # Verify it's a string with expected format
        assert isinstance(message, str)
        assert "*Failure Hook Notification! Step failed!*" in message
        assert "`test_pipeline`" in message
        assert "`test_step`" in message

    @patch("zenml.hooks.alerter_hooks.get_step_context")
    @patch("zenml.hooks.alerter_hooks.Client")
    def test_success_hook_with_alerter_message(
        self, mock_client, mock_get_context
    ):
        """Test success hook uses AlerterMessage format."""
        # Setup mocks
        mock_context = MagicMock()
        mock_context.pipeline.name = "test_pipeline"
        mock_context.pipeline_run.name = "test_run"
        mock_context.step_run.name = "test_step"
        mock_context.step_run.config.parameters = {"param": "value"}
        mock_get_context.return_value = mock_context

        mock_alerter = MagicMock()
        mock_client.return_value.active_stack.alerter = mock_alerter
        mock_client.return_value.active_stack.name = "test_stack"

        # Call the hook
        alerter_success_hook()

        # Verify alerter.post was called
        assert mock_alerter.post.called

        # Get the message passed to alerter.post
        call_args = mock_alerter.post.call_args
        message = call_args[0][0]

        # Verify it's an AlerterMessage
        assert isinstance(message, AlerterMessage)
        assert message.title == "Pipeline Success Notification"
        assert "test_step" in message.body
        assert "test_pipeline" in message.body
        assert message.metadata["pipeline_name"] == "test_pipeline"
        assert message.metadata["status"] == "success"

    @patch("zenml.hooks.alerter_hooks.get_step_context")
    @patch("zenml.hooks.alerter_hooks.Client")
    def test_success_hook_fallback_to_string(
        self, mock_client, mock_get_context
    ):
        """Test success hook falls back to string format on error."""
        # Setup mocks
        mock_context = MagicMock()
        mock_context.pipeline.name = "test_pipeline"
        mock_context.pipeline_run.name = "test_run"
        mock_context.step_run.name = "test_step"
        mock_context.step_run.config.parameters = {"param": "value"}
        mock_get_context.return_value = mock_context

        mock_alerter = MagicMock()
        # Make AlerterMessage import fail to trigger fallback
        mock_alerter.post.side_effect = [
            ImportError("AlerterMessage not found"),  # First call fails
            None,  # Second call succeeds
        ]
        mock_client.return_value.active_stack.alerter = mock_alerter

        # Call the hook
        alerter_success_hook()

        # Verify alerter.post was called twice (first failed, then fallback)
        assert mock_alerter.post.call_count == 2

        # Get the fallback message
        second_call_args = mock_alerter.post.call_args_list[1]
        message = second_call_args[0][0]

        # Verify it's a string with expected format
        assert isinstance(message, str)
        assert (
            "*Success Hook Notification! Step completed successfully*"
            in message
        )
        assert "`test_pipeline`" in message
        assert "`test_step`" in message

    @patch("zenml.hooks.alerter_hooks.get_step_context")
    @patch("zenml.hooks.alerter_hooks.Client")
    def test_hooks_with_no_alerter_configured(
        self, mock_client, mock_get_context
    ):
        """Test hooks handle case when no alerter is configured."""
        # Setup mocks with no alerter
        mock_context = MagicMock()
        mock_get_context.return_value = mock_context
        mock_client.return_value.active_stack.alerter = None

        # Test failure hook
        with patch("zenml.hooks.alerter_hooks.logger") as mock_logger:
            alerter_failure_hook(ValueError("Test"))
            mock_logger.warning.assert_called_once_with(
                "Specified standard failure hook but no alerter configured in the stack. Skipping.."
            )

        # Test success hook
        with patch("zenml.hooks.alerter_hooks.logger") as mock_logger:
            alerter_success_hook()
            mock_logger.warning.assert_called_once_with(
                "Specified standard success hook but no alerter configured in the stack. Skipping.."
            )
