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
"""Unit tests for email validation in SMTP alerter."""

import pytest
from pydantic import ValidationError

from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
    SMTPEmailAlerterParameters,
)
from zenml.integrations.smtp_email.flavors.smtp_email_alerter_flavor import (
    SMTPEmailAlerterConfig,
    SMTPEmailAlerterSettings,
)
from zenml.integrations.smtp_email.utils import validate_email


def test_validate_email_valid():
    """Test validate_email with valid email addresses."""
    valid_emails = [
        "test@example.com",
        "user.name@example.com",
        "user+tag@example.co.uk",
        "test_email@subdomain.example.com",
        "123@example.com",
        "a@b.co",
    ]

    for email in valid_emails:
        assert validate_email(email) == email


def test_validate_email_invalid():
    """Test validate_email with invalid email addresses."""
    invalid_emails = [
        "not-an-email",
        "@example.com",
        "user@",
        "user@@example.com",
        "user@example",
        "user space@example.com",
        "user@.com",
        "",
        "user@example.",
        "user..name@example.com",
    ]

    for email in invalid_emails:
        try:
            with pytest.raises(ValueError) as exc_info:
                validate_email(email)
            assert "Invalid email address format" in str(exc_info.value)
        except AssertionError:
            pytest.fail(
                f"Email '{email}' did not raise ValueError as expected"
            )


def test_smtp_email_alerter_parameters_validation():
    """Test email validation in SMTPEmailAlerterParameters."""
    # Valid email should work
    params = SMTPEmailAlerterParameters(recipient_email="test@example.com")
    assert params.recipient_email == "test@example.com"

    # None should be allowed
    params = SMTPEmailAlerterParameters(recipient_email=None)
    assert params.recipient_email is None

    # Invalid email should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        SMTPEmailAlerterParameters(recipient_email="invalid-email")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "Invalid email address format" in str(errors[0]["ctx"]["error"])


def test_smtp_email_alerter_settings_validation():
    """Test email validation in SMTPEmailAlerterSettings."""
    # Valid email should work
    settings = SMTPEmailAlerterSettings(recipient_email="test@example.com")
    assert settings.recipient_email == "test@example.com"

    # None should be allowed (optional field)
    settings = SMTPEmailAlerterSettings(recipient_email=None)
    assert settings.recipient_email is None

    # Invalid email should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        SMTPEmailAlerterSettings(recipient_email="not-an-email")

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "Invalid email address format" in str(errors[0]["ctx"]["error"])


def test_smtp_email_alerter_config_validation():
    """Test email validation in SMTPEmailAlerterConfig."""
    # Valid sender email should work
    config = SMTPEmailAlerterConfig(
        smtp_server="smtp.gmail.com",
        sender_email="sender@example.com",
        password="secret",
    )
    assert config.sender_email == "sender@example.com"

    # Invalid sender email should raise ValidationError
    with pytest.raises(ValidationError) as exc_info:
        SMTPEmailAlerterConfig(
            smtp_server="smtp.gmail.com",
            sender_email="invalid@",
            password="secret",
        )

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "Invalid email address format" in str(errors[0]["ctx"]["error"])

    # Test recipient email validation through inheritance
    with pytest.raises(ValidationError) as exc_info:
        SMTPEmailAlerterConfig(
            smtp_server="smtp.gmail.com",
            sender_email="valid@example.com",
            password="secret",
            recipient_email="@invalid.com",
        )

    errors = exc_info.value.errors()
    assert len(errors) == 1
    assert "Invalid email address format" in str(errors[0]["ctx"]["error"])


def test_email_validation_edge_cases():
    """Test edge cases for email validation."""
    # Test with special but valid characters
    assert validate_email("user+tag@example.com") == "user+tag@example.com"
    assert validate_email("user.name@example.com") == "user.name@example.com"
    assert validate_email("user_name@example.com") == "user_name@example.com"

    # Test with numbers
    assert validate_email("user123@example.com") == "user123@example.com"
    assert validate_email("123user@example.com") == "123user@example.com"

    # Test with hyphens in domain
    assert (
        validate_email("user@sub-domain.example.com")
        == "user@sub-domain.example.com"
    )

    # Test minimum valid email
    assert validate_email("a@b.co") == "a@b.co"
