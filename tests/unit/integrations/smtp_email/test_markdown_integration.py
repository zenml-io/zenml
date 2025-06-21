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
"""Unit tests for markdown integration in SMTP alerter."""

from zenml.utils.markdown_utils import (
    EMAIL_MARKDOWN_OPTIONS,
    MarkdownOutputFormat,
    format_markdown,
)


def test_smtp_alerter_markdown_integration():
    """Test that SMTP alerter uses the correct markdown options."""
    # Test message with markdown and potential XSS
    message = 'This is **bold**, `code`, and <script>alert("xss")</script>'

    # Process using EMAIL_MARKDOWN_OPTIONS like the SMTP alerter does
    result = format_markdown(
        message,
        output_format=MarkdownOutputFormat.HTML,
        options=EMAIL_MARKDOWN_OPTIONS,
    )

    # Verify markdown processing - use ** for bold, not *
    assert "<strong>bold</strong>" in result
    assert "<code" in result

    # Verify XSS protection
    assert "&lt;script&gt;" in result
    assert "<script>" not in result


def test_smtp_alerter_traceback_handling():
    """Test that SMTP alerter properly handles tracebacks."""
    message = """Error occurred:
Traceback (most recent call last):
  File "test.py", line 1
ValueError: Something <bad> happened"""

    # Process using EMAIL_MARKDOWN_OPTIONS
    result = format_markdown(
        message,
        output_format=MarkdownOutputFormat.HTML,
        options=EMAIL_MARKDOWN_OPTIONS,
    )

    # Should detect and format traceback
    assert "Traceback" in result
    assert "ValueError" in result
    # HTML in traceback should be escaped
    assert "&lt;bad&gt;" in result
    assert "<bad>" not in result


def test_smtp_alerter_email_options_config():
    """Test that EMAIL_MARKDOWN_OPTIONS has the expected configuration."""
    # Verify that EMAIL_MARKDOWN_OPTIONS enables the features needed for email
    assert EMAIL_MARKDOWN_OPTIONS.inline_code is True
    assert EMAIL_MARKDOWN_OPTIONS.bold is True
    assert EMAIL_MARKDOWN_OPTIONS.italic is True
    assert EMAIL_MARKDOWN_OPTIONS.traceback_detection is True
    assert EMAIL_MARKDOWN_OPTIONS.html_escaping is True
    assert EMAIL_MARKDOWN_OPTIONS.paragraphs is True
    assert EMAIL_MARKDOWN_OPTIONS.code_blocks is True
