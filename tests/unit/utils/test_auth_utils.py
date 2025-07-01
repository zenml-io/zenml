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
"""Unit tests for auth_utils module."""

import os
from unittest.mock import MagicMock, PropertyMock, patch

import pytest

from zenml.exceptions import AuthorizationException, CredentialsNotValid
from zenml.utils.auth_utils import (
    cli_require_login,
    require_pipeline_execution_authentication,
    require_user_authentication,
)


class TestRequireUserAuthentication:
    """Test require_user_authentication function."""

    @patch.dict(os.environ, {"ZENML_DISABLE_LOGIN_REQUIREMENT": "true"})
    def test_bypass_via_environment_variable(self):
        """Test that authentication can be bypassed via environment variable."""
        # Should not raise any exception
        require_user_authentication()

    @patch.dict(os.environ, {"ZENML_DISABLE_LOGIN_REQUIREMENT": "1"})
    def test_bypass_via_environment_variable_numeric(self):
        """Test that authentication can be bypassed via numeric env var."""
        # Should not raise any exception
        require_user_authentication()

    @patch.dict(os.environ, {"ZENML_DISABLE_LOGIN_REQUIREMENT": "yes"})
    def test_bypass_via_environment_variable_yes(self):
        """Test that authentication can be bypassed via 'yes' env var."""
        # Should not raise any exception
        require_user_authentication()

    @patch("zenml.utils.auth_utils.Client")
    @patch("zenml.utils.auth_utils.GlobalConfiguration")
    def test_local_sqlite_store_bypass(self, mock_global_config, mock_client):
        """Test that local SQLite stores bypass authentication check."""
        mock_config = MagicMock()
        mock_config.store_configuration.url = "sqlite:///path/to/local.db"
        mock_global_config.return_value = mock_config

        # Should not raise any exception
        require_user_authentication()

    @patch("zenml.utils.auth_utils.Client")
    @patch("zenml.utils.auth_utils.GlobalConfiguration")
    def test_local_stores_path_bypass(self, mock_global_config, mock_client):
        """Test that stores in local_stores path bypass authentication check."""
        mock_config = MagicMock()
        mock_config.store_configuration.url = "/path/to/local_stores/store.db"
        # Configure as property
        type(mock_config).local_stores_path = "/path/to/local_stores"
        mock_global_config.return_value = mock_config

        # Should not raise any exception
        require_user_authentication()

    @patch("zenml.utils.auth_utils.Client")
    @patch("zenml.utils.auth_utils.GlobalConfiguration")
    def test_successful_authentication(self, mock_global_config, mock_client):
        """Test successful authentication with valid user."""
        mock_config = MagicMock()
        mock_config.store_configuration.url = "https://server.example.com"
        # Configure as property
        type(mock_config).local_stores_path = "/different/path"
        mock_global_config.return_value = mock_config

        mock_client_instance = MagicMock()
        mock_user = MagicMock()
        mock_user.name = "testuser"
        mock_client_instance.active_user = mock_user
        mock_client.return_value = mock_client_instance

        # Should not raise any exception
        require_user_authentication()

    @patch("zenml.utils.auth_utils.Client")
    @patch("zenml.utils.auth_utils.GlobalConfiguration")
    def test_no_auth_server_bypass(self, mock_global_config, mock_client):
        """Test that servers with NO_AUTH scheme bypass authentication."""
        mock_config = MagicMock()
        mock_config.store_configuration.url = "https://server.example.com"
        type(mock_config).local_stores_path = "/completely/different/path"
        mock_global_config.return_value = mock_config

        mock_client_instance = MagicMock()
        # Simulate AuthorizationException when getting active_user
        type(mock_client_instance).active_user = PropertyMock(
            side_effect=AuthorizationException("No auth required")
        )
        # But zen_store.get_store_info() succeeds (indicating NO_AUTH server)
        mock_client_instance.zen_store.get_store_info.return_value = {
            "server": "info"
        }
        mock_client.return_value = mock_client_instance

        # Should not raise any exception
        require_user_authentication()

    @patch.dict(os.environ, {}, clear=True)
    @patch("zenml.utils.auth_utils.Client")
    @patch("zenml.utils.auth_utils.GlobalConfiguration")
    def test_credentials_not_valid_error(
        self, mock_global_config, mock_client
    ):
        """Test proper error handling for invalid credentials."""
        mock_config = MagicMock()
        mock_config.store_configuration.url = "https://server.example.com"
        type(mock_config).local_stores_path = "/completely/different/path"
        mock_global_config.return_value = mock_config

        mock_client_instance = MagicMock()
        type(mock_client_instance).active_user = PropertyMock(
            side_effect=CredentialsNotValid("No valid credentials found")
        )
        mock_client.return_value = mock_client_instance

        with pytest.raises(CredentialsNotValid) as exc_info:
            require_user_authentication()

        assert "You must be logged in to run pipelines" in str(exc_info.value)
        assert "zenml login" in str(exc_info.value)

    @patch.dict(os.environ, {}, clear=True)
    @patch("zenml.utils.auth_utils.Client")
    @patch("zenml.utils.auth_utils.GlobalConfiguration")
    def test_credentials_expired_error(self, mock_global_config, mock_client):
        """Test proper error handling for expired credentials."""
        mock_config = MagicMock()
        mock_config.store_configuration.url = "https://server.example.com"
        type(mock_config).local_stores_path = "/completely/different/path"
        mock_global_config.return_value = mock_config

        mock_client_instance = MagicMock()
        type(mock_client_instance).active_user = PropertyMock(
            side_effect=CredentialsNotValid(
                "authentication to the current server has expired"
            )
        )
        mock_client.return_value = mock_client_instance

        with pytest.raises(CredentialsNotValid) as exc_info:
            require_user_authentication()

        assert "authentication has expired" in str(exc_info.value)
        assert "re-authenticate" in str(exc_info.value)

    @patch.dict(os.environ, {}, clear=True)
    @patch("zenml.utils.auth_utils.Client")
    @patch("zenml.utils.auth_utils.GlobalConfiguration")
    def test_generic_authentication_error(
        self, mock_global_config, mock_client
    ):
        """Test proper error handling for generic authentication errors."""
        mock_config = MagicMock()
        mock_config.store_configuration.url = "https://server.example.com"
        type(mock_config).local_stores_path = "/completely/different/path"
        mock_global_config.return_value = mock_config

        mock_client_instance = MagicMock()
        type(mock_client_instance).active_user = PropertyMock(
            side_effect=Exception("Connection error")
        )
        mock_client.return_value = mock_client_instance

        with pytest.raises(CredentialsNotValid) as exc_info:
            require_user_authentication()

        assert "Unable to verify authentication status" in str(exc_info.value)
        assert "Connection error" in str(exc_info.value)

    @patch.dict(os.environ, {}, clear=True)
    def test_bypass_local_check_parameter(self):
        """Test that bypass_local_check parameter works correctly."""
        with (
            patch("zenml.utils.auth_utils.Client") as mock_client,
            patch(
                "zenml.utils.auth_utils.GlobalConfiguration"
            ) as mock_global_config,
        ):
            mock_config = MagicMock()
            mock_config.store_configuration.url = "sqlite:///local.db"
            type(mock_config).local_stores_path = "/completely/different/path"
            mock_global_config.return_value = mock_config

            mock_client_instance = MagicMock()
            type(mock_client_instance).active_user = PropertyMock(
                side_effect=CredentialsNotValid("No credentials")
            )
            mock_client.return_value = mock_client_instance

            # Should raise error when bypass_local_check=True, even for SQLite
            with pytest.raises(CredentialsNotValid):
                require_user_authentication(bypass_local_check=True)

    @patch.dict(os.environ, {}, clear=True)
    def test_context_parameter_in_error_message(self):
        """Test that context parameter is included in error messages."""
        with (
            patch("zenml.utils.auth_utils.Client") as mock_client,
            patch(
                "zenml.utils.auth_utils.GlobalConfiguration"
            ) as mock_global_config,
        ):
            mock_config = MagicMock()
            mock_config.store_configuration.url = "https://server.example.com"
            type(mock_config).local_stores_path = "/different/path"
            mock_global_config.return_value = mock_config

            mock_client_instance = MagicMock()
            type(mock_client_instance).active_user = PropertyMock(
                side_effect=CredentialsNotValid("No valid credentials found")
            )
            mock_client.return_value = mock_client_instance

            with pytest.raises(CredentialsNotValid) as exc_info:
                require_user_authentication(context="access model registry")

            assert "access model registry" in str(exc_info.value)


class TestRequirePipelineExecutionAuthentication:
    """Test require_pipeline_execution_authentication function."""

    @patch("zenml.utils.auth_utils.require_user_authentication")
    def test_calls_require_user_authentication(self, mock_require_user_auth):
        """Test that it properly calls require_user_authentication."""
        require_pipeline_execution_authentication()
        mock_require_user_auth.assert_called_once_with(context="run pipelines")


class TestCliRequireLogin:
    """Test cli_require_login function."""

    @patch("zenml.utils.auth_utils.require_user_authentication")
    def test_successful_authentication(self, mock_require_user_auth):
        """Test successful authentication doesn't raise CLI error."""
        mock_require_user_auth.return_value = None

        # Should not raise any exception
        cli_require_login()

    @patch("zenml.utils.auth_utils.require_user_authentication")
    def test_credentials_not_valid_converts_to_click_exception(
        self, mock_require_user_auth
    ):
        """Test that CredentialsNotValid is converted to ClickException."""
        mock_require_user_auth.side_effect = CredentialsNotValid(
            "Authentication failed"
        )

        with pytest.raises(Exception) as exc_info:
            cli_require_login()

        # Should be a ClickException (testing by checking the message attribute)
        assert hasattr(exc_info.value, "message")
        assert "Authentication failed" in str(exc_info.value)

    @patch("zenml.utils.auth_utils.require_user_authentication")
    def test_bypass_local_check_parameter_passed(self, mock_require_user_auth):
        """Test that bypass_local_check parameter is passed through."""
        cli_require_login(bypass_local_check=True)
        mock_require_user_auth.assert_called_once_with(
            bypass_local_check=True, context="run pipelines"
        )
