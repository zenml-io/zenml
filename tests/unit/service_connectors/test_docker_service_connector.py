"""Tests for the Docker Service Connector."""

import pytest
from unittest.mock import patch, MagicMock
from docker.errors import DockerException

from zenml.service_connectors.docker_service_connector import (
    DockerServiceConnector,
    DockerConfiguration,
)
from zenml.utils.secret_utils import PlainSerializedSecretStr

class TestDockerServiceConnector:
    """Test for the Docker service connector."""

    @pytest.fixture
    def docker_connector(self):
        """Create a Docker service connector for testing."""
        config = DockerConfiguration(
            username=PlainSerializedSecretStr("test-user"),
            password=PlainSerializedSecretStr("test-password"),
            registry="docker.io",
        )
        return DockerServiceConnector(
            auth_method="password", 
            config=config
        )

    @patch("zenml.service_connectors.docker_service_connector.DockerClient")
    def test_verify_with_resource_id(self, mock_docker_client, docker_connector):
        """Test the _verify method when a resource ID is provided."""
        # Setup
        mock_client = MagicMock()
        mock_docker_client.from_env.return_value = mock_client
        
        # Test
        resource_ids = docker_connector._verify(
            resource_type="docker-registry",
            resource_id="docker.io"
        )
        
        # Assert
        assert resource_ids == ["docker.io"]
        mock_client.login.assert_called_once()
        mock_client.close.assert_called_once()

    @patch("zenml.service_connectors.docker_service_connector.DockerClient")
    def test_verify_without_resource_id(self, mock_docker_client, docker_connector):
        """Test the _verify method when no resource ID is provided.
        
        This tests our fix for the assertion issue.
        """
        # Setup
        mock_client = MagicMock()
        mock_docker_client.from_env.return_value = mock_client
        
        # Test
        resource_ids = docker_connector._verify(
            resource_type="docker-registry",
            resource_id=None
        )
        
        # Assert
        assert resource_ids == []
        mock_client.login.assert_not_called()
        mock_client.close.assert_not_called()

    @patch("zenml.service_connectors.docker_service_connector.DockerClient")
    def test_verify_with_docker_exception(self, mock_docker_client, docker_connector):
        """Test the _verify method when Docker client raises an exception."""
        # Setup
        mock_docker_client.from_env.side_effect = DockerException("Docker not available")
        
        # Test
        resource_ids = docker_connector._verify(
            resource_type="docker-registry",
            resource_id="docker.io"
        )
        
        # Assert - should still return the resource ID despite the exception
        assert resource_ids == ["docker.io"]

if __name__ == "__main__":
    pytest.main(["-xvs", __file__])