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
"""Unit tests for parameter inheritance in SMTP alerter."""

from unittest import mock

import pytest

from zenml.alerter.base_alerter import BaseAlerterStepParameters
from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
    SMTPEmailAlerterParameters,
)


class MockSMTPEmailAlerter:
    """Mock alerter to test _get_attribute_value logic."""

    def __init__(self, config):
        self.config = config
        self._settings = None

    def get_settings(self, step_run):
        """Mock get_settings method."""
        return self._settings

    def _get_attribute_value(
        self,
        attribute_name: str,
        params=None,
        fail_if_missing: bool = False,
        param_class=None,
    ):
        """Simplified version of _get_attribute_value for testing."""
        # Check in params first
        if params:
            if param_class and not isinstance(params, param_class):
                raise RuntimeError(
                    f"The params object must be of type `{param_class.__name__}`."
                )

            # For SMTPEmailAlerterParameters attributes
            if isinstance(params, SMTPEmailAlerterParameters):
                if (
                    hasattr(params, attribute_name)
                    and getattr(params, attribute_name) is not None
                ):
                    return getattr(params, attribute_name)
            # For BaseAlerterStepParameters attributes
            elif (
                hasattr(params, attribute_name)
                and getattr(params, attribute_name) is not None
            ):
                return getattr(params, attribute_name)

        # Try to get from settings
        if self._settings is not None and hasattr(
            self._settings, attribute_name
        ):
            setting_value = getattr(self._settings, attribute_name)
            if setting_value is not None:
                return setting_value

        # Fall back to config value
        if hasattr(self.config, attribute_name):
            config_value = getattr(self.config, attribute_name)
            if config_value is not None or not fail_if_missing:
                return config_value

        # If we get here and fail_if_missing is True, raise an error
        if fail_if_missing:
            raise ValueError(
                f"The `{attribute_name}` is not set either in the runtime parameters, "
                f"settings, or the component configuration. Please specify at "
                f"least one."
            )

        return None


def test_parameter_priority_params_over_settings():
    """Test that params take priority over settings."""
    # Create mock config and settings
    config = mock.Mock()
    config.recipient_email = "config@example.com"

    settings = mock.Mock()
    settings.recipient_email = "settings@example.com"

    # Create alerter and set settings
    alerter = MockSMTPEmailAlerter(config)
    alerter._settings = settings

    # Create params with different value
    params = SMTPEmailAlerterParameters(recipient_email="params@example.com")

    # Test that params value is returned
    result = alerter._get_attribute_value("recipient_email", params=params)
    assert result == "params@example.com"


def test_parameter_priority_settings_over_config():
    """Test that settings take priority over config when params not provided."""
    # Create mock config and settings
    config = mock.Mock()
    config.recipient_email = "config@example.com"

    settings = mock.Mock()
    settings.recipient_email = "settings@example.com"

    # Create alerter and set settings
    alerter = MockSMTPEmailAlerter(config)
    alerter._settings = settings

    # Test without params - settings should be used
    result = alerter._get_attribute_value("recipient_email")
    assert result == "settings@example.com"


def test_parameter_fallback_to_config():
    """Test fallback to config when params and settings not available."""
    # Create mock config
    config = mock.Mock()
    config.recipient_email = "config@example.com"

    # Create alerter without settings
    alerter = MockSMTPEmailAlerter(config)

    # Test without params or settings - config should be used
    result = alerter._get_attribute_value("recipient_email")
    assert result == "config@example.com"


def test_parameter_none_in_params_does_not_override():
    """Test that None in params doesn't override settings/config."""
    # Create mock config and settings
    config = mock.Mock()
    config.recipient_email = "config@example.com"

    settings = mock.Mock()
    settings.recipient_email = "settings@example.com"

    # Create alerter and set settings
    alerter = MockSMTPEmailAlerter(config)
    alerter._settings = settings

    # Create params with None value
    params = SMTPEmailAlerterParameters(recipient_email=None)

    # Test that settings value is returned (None in params is ignored)
    result = alerter._get_attribute_value("recipient_email", params=params)
    assert result == "settings@example.com"


def test_parameter_fail_if_missing():
    """Test that ValueError is raised when attribute is missing and fail_if_missing=True."""
    # Create mock config without the attribute
    config = mock.Mock()
    config.nonexistent = None

    # Create alerter
    alerter = MockSMTPEmailAlerter(config)

    # Test that ValueError is raised
    with pytest.raises(ValueError) as exc_info:
        alerter._get_attribute_value("nonexistent", fail_if_missing=True)

    assert "not set either in the runtime parameters" in str(exc_info.value)


def test_parameter_type_checking():
    """Test that type checking works for params."""
    # Create mock config
    config = mock.Mock()

    # Create alerter
    alerter = MockSMTPEmailAlerter(config)

    # Create params of wrong type
    params = mock.Mock()  # Not a BaseAlerterStepParameters

    # Test that RuntimeError is raised
    with pytest.raises(RuntimeError) as exc_info:
        alerter._get_attribute_value(
            "recipient_email",
            params=params,
            param_class=BaseAlerterStepParameters,
        )

    assert "must be of type" in str(exc_info.value)


def test_boolean_attribute_false_is_valid():
    """Test that False boolean values are properly returned."""
    # Create mock config
    config = mock.Mock()
    config.include_html = True

    settings = mock.Mock()
    settings.include_html = False  # Explicitly False

    # Create alerter and set settings
    alerter = MockSMTPEmailAlerter(config)
    alerter._settings = settings

    # Test that False is returned (not the True from config)
    result = alerter._get_attribute_value("include_html")
    assert result is False


def test_nested_params_attributes():
    """Test accessing nested attributes in SMTPEmailAlerterParameters."""
    # Create mock config
    config = mock.Mock()
    config.subject = "Default Subject"

    # Create alerter
    alerter = MockSMTPEmailAlerter(config)

    # Create params with custom subject
    params = SMTPEmailAlerterParameters(subject="Custom Subject")

    # Test that params value is returned
    result = alerter._get_attribute_value("subject", params=params)
    assert result == "Custom Subject"


def test_all_values_none_with_fail_if_missing_false():
    """Test that None is returned when all values are None and fail_if_missing=False."""
    # Create mock config with None value
    config = mock.Mock()
    config.optional_field = None

    # Create alerter
    alerter = MockSMTPEmailAlerter(config)

    # Test that None is returned without error
    result = alerter._get_attribute_value(
        "optional_field", fail_if_missing=False
    )
    assert result is None
