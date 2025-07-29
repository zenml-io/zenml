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
"""Tests for the base trace collector."""

import pytest

from zenml.enums import StackComponentType
from zenml.trace_collectors.base_trace_collector import (
    BaseTraceCollector,
    BaseTraceCollectorConfig,
    BaseTraceCollectorFlavor,
)


class MockTraceCollectorConfig(BaseTraceCollectorConfig):
    """Mock trace collector config for testing."""

    test_param: str = "test_value"


class MockTraceCollector(BaseTraceCollector):
    """Mock trace collector for testing."""

    def get_session(self, session_id: str):
        """Mock implementation."""
        return []

    def get_trace(self, trace_id: str):
        """Mock implementation."""
        return None

    def get_traces(self, **kwargs):
        """Mock implementation."""
        return []

    def get_span(self, span_id: str):
        """Mock implementation."""
        return None

    def add_annotations(self, trace_id: str, annotations):
        """Mock implementation."""
        pass

    def log_metadata(self, trace_id: str, metadata, **kwargs):
        """Mock implementation."""
        pass


class MockTraceCollectorFlavor(BaseTraceCollectorFlavor):
    """Mock trace collector flavor for testing."""

    @property
    def name(self) -> str:
        """Name of the flavor."""
        return "mock"

    @property
    def config_class(self):
        """Config class."""
        return MockTraceCollectorConfig

    @property
    def implementation_class(self):
        """Implementation class."""
        return MockTraceCollector


class TestBaseTraceCollector:
    """Test the base trace collector."""

    def test_config_property(self):
        """Test that the config property returns the correct config."""
        config = MockTraceCollectorConfig(test_param="custom_value")
        collector = MockTraceCollector(uuid="test", config=config)

        assert collector.config.test_param == "custom_value"

    def test_abstract_methods_must_be_implemented(self):
        """Test that abstract methods must be implemented."""

        class IncompleteTraceCollector(BaseTraceCollector):
            """Incomplete implementation for testing."""

            pass

        with pytest.raises(TypeError):
            IncompleteTraceCollector(
                uuid="test", config=BaseTraceCollectorConfig()
            )


class TestBaseTraceCollectorFlavor:
    """Test the base trace collector flavor."""

    def test_flavor_type(self):
        """Test that the flavor type is correct."""
        flavor = MockTraceCollectorFlavor()
        assert flavor.type == StackComponentType.TRACE_COLLECTOR

    def test_config_class(self):
        """Test the config class property."""
        flavor = MockTraceCollectorFlavor()
        assert flavor.config_class == MockTraceCollectorConfig

    def test_implementation_class(self):
        """Test the implementation class property."""
        flavor = MockTraceCollectorFlavor()
        assert flavor.implementation_class == MockTraceCollector

    def test_name_property(self):
        """Test the name property."""
        flavor = MockTraceCollectorFlavor()
        assert flavor.name == "mock"
