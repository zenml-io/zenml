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
"""Tests for the LangFuse trace collector."""

from datetime import datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from zenml.integrations.langfuse.flavors.langfuse_trace_collector_flavor import (
    LangFuseTraceCollectorConfig,
)
from zenml.integrations.langfuse.trace_collectors.langfuse_trace_collector import (
    LangFuseTraceCollector,
)
from zenml.trace_collectors.models import (
    Trace,
    TraceAnnotation,
)


class TestLangFuseTraceCollector:
    """Test the LangFuse trace collector."""

    @pytest.fixture
    def config(self):
        """Create a test config."""
        return LangFuseTraceCollectorConfig(
            public_key="test_public_key",
            secret_key="test_secret_key",
            host="https://test.langfuse.com",
        )

    @pytest.fixture
    def collector(self, config):
        """Create a test collector."""
        return LangFuseTraceCollector(uuid=str(uuid4()), config=config)

    def test_config_property(self, collector, config):
        """Test that the config property returns the correct config."""
        assert collector.config == config
        assert collector.config.public_key == "test_public_key"
        assert collector.config.secret_key == "test_secret_key"

    @patch(
        "zenml.integrations.langfuse.trace_collectors.langfuse_trace_collector.Langfuse"
    )
    def test_client_initialization(self, mock_langfuse, collector):
        """Test that the client is initialized correctly."""
        # Access the client property to trigger initialization
        client = collector.client

        # Verify Langfuse was called with correct parameters
        mock_langfuse.assert_called_once_with(
            host="https://test.langfuse.com",
            public_key="test_public_key",
            secret_key="test_secret_key",
            release=None,
            debug=False,
            enabled=True,
        )

        # Verify client is cached
        assert collector._client is not None
        client2 = collector.client
        assert client is client2

    @patch(
        "zenml.integrations.langfuse.trace_collectors.langfuse_trace_collector.Langfuse"
    )
    def test_client_import_error(self, mock_langfuse):
        """Test ImportError handling when LangFuse is not installed."""
        mock_langfuse.side_effect = ImportError("No module named 'langfuse'")

        config = LangFuseTraceCollectorConfig(
            public_key="test_key",
            secret_key="test_secret",
        )
        collector = LangFuseTraceCollector(uuid=str(uuid4()), config=config)

        with pytest.raises(ImportError, match="LangFuse is not installed"):
            _ = collector.client

    @patch(
        "zenml.integrations.langfuse.trace_collectors.langfuse_trace_collector.Langfuse"
    )
    def test_get_trace(self, mock_langfuse_class, collector):
        """Test getting a single trace."""
        # Mock the LangFuse client
        mock_client = MagicMock()
        mock_langfuse_class.return_value = mock_client

        # Mock trace data
        mock_trace = MagicMock()
        mock_trace.id = "test_trace_id"
        mock_trace.timestamp = datetime.now()
        mock_trace.name = "test_trace"
        mock_trace.metadata = {"key": "value"}
        mock_trace.input = "test input"
        mock_trace.output = "test output"
        mock_trace.tags = ["tag1", "tag2"]
        mock_trace.user_id = "test_user"
        mock_trace.session_id = "test_session"
        mock_trace.observations = []
        mock_trace.scores = []

        mock_client.api.trace.get.return_value = mock_trace

        # Test the method
        result = collector.get_trace("test_trace_id")

        # Verify the call
        mock_client.api.trace.get.assert_called_once_with("test_trace_id")

        # Verify the result
        assert isinstance(result, Trace)
        assert result.id == "test_trace_id"
        assert result.name == "test_trace"
        assert result.metadata == {"key": "value"}

    @patch(
        "zenml.integrations.langfuse.trace_collectors.langfuse_trace_collector.Langfuse"
    )
    def test_get_traces_with_filters(self, mock_langfuse_class, collector):
        """Test getting traces with filters."""
        # Mock the LangFuse client
        mock_client = MagicMock()
        mock_langfuse_class.return_value = mock_client

        # Mock traces response
        mock_trace_data = MagicMock()
        mock_trace_data.id = "test_trace_id"

        mock_traces_response = MagicMock()
        mock_traces_response.data = [mock_trace_data]
        mock_client.api.trace.list.return_value = mock_traces_response

        # Mock full trace
        mock_full_trace = MagicMock()
        mock_full_trace.id = "test_trace_id"
        mock_full_trace.timestamp = datetime.now()
        mock_full_trace.observations = []
        mock_full_trace.scores = []
        mock_client.api.trace.get.return_value = mock_full_trace

        # Test with filters
        start_time = datetime.now()
        result = collector.get_traces(
            start_time=start_time, session_id="test_session", limit=10
        )

        # Verify the call
        mock_client.api.trace.list.assert_called_once_with(
            from_timestamp=start_time, session_id="test_session", limit=10
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1

    @patch(
        "zenml.integrations.langfuse.trace_collectors.langfuse_trace_collector.Langfuse"
    )
    def test_add_annotations(self, mock_langfuse_class, collector):
        """Test adding annotations to a trace."""
        # Mock the LangFuse client
        mock_client = MagicMock()
        mock_langfuse_class.return_value = mock_client

        # Create test annotations
        annotations = [
            TraceAnnotation(
                id="ann1",
                name="quality",
                value=0.8,
                comment="Good quality",
                created_at=datetime.now(),
            ),
            TraceAnnotation(
                id="ann2",
                name="accuracy",
                value=0.9,
                created_at=datetime.now(),
            ),
        ]

        # Test the method
        collector.add_annotations("test_trace_id", annotations)

        # Verify the calls
        assert mock_client.score.call_count == 2
        mock_client.score.assert_any_call(
            trace_id="test_trace_id",
            name="quality",
            value=0.8,
            comment="Good quality",
        )
        mock_client.score.assert_any_call(
            trace_id="test_trace_id", name="accuracy", value=0.9, comment=None
        )

    @patch(
        "zenml.integrations.langfuse.trace_collectors.langfuse_trace_collector.Langfuse"
    )
    def test_get_session(self, mock_langfuse_class, collector):
        """Test getting traces for a session."""
        # Mock the LangFuse client
        mock_client = MagicMock()
        mock_langfuse_class.return_value = mock_client

        # Mock session traces response
        mock_trace_data = MagicMock()
        mock_trace_data.id = "trace1"

        mock_session_response = MagicMock()
        mock_session_response.data = [mock_trace_data]
        mock_client.api.trace.list.return_value = mock_session_response

        # Mock full trace
        mock_full_trace = MagicMock()
        mock_full_trace.id = "trace1"
        mock_full_trace.timestamp = datetime.now()
        mock_full_trace.observations = []
        mock_full_trace.scores = []
        mock_client.api.trace.get.return_value = mock_full_trace

        # Test the method
        result = collector.get_session("test_session_id")

        # Verify the call
        mock_client.api.trace.list.assert_called_once_with(
            session_id="test_session_id"
        )

        # Verify the result
        assert isinstance(result, list)
        assert len(result) == 1

    def test_error_handling(self, collector):
        """Test error handling in various methods."""
        # Test with uninitialized client that will fail
        with patch.object(collector, "client") as mock_client:
            mock_client.api.trace.get.side_effect = Exception("API Error")

            with pytest.raises(Exception):
                collector.get_trace("test_trace_id")
