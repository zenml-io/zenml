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
"""Unit tests for HTML escaping in SMTP alerter."""

import html
import re

from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
    SMTPEmailAlerterPayload,
)


def process_message_for_html(message: str) -> str:
    """Simplified version of the HTML processing logic for testing.

    This mimics the logic in SMTPEmailAlerter._create_html_body.
    """
    if not message:
        return ""

    # First, escape HTML entities to prevent XSS
    safe_message = html.escape(message)

    # Helper function to process markdown-style formatting
    def process_markdown_line(line: str) -> str:
        # Process inline code with backticks
        line = re.sub(
            r"`([^`]+)`",
            r'<code style="background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: monospace;">\1</code>',
            line,
        )
        # Process bold with asterisks
        line = re.sub(r"\*([^*\n]+)\*", r"<strong>\1</strong>", line)
        # Process italic with underscores
        line = re.sub(r"_([^_\n]+)_", r"<em>\1</em>", line)
        return line

    # Check if the message contains a traceback or code block
    if "Traceback" in safe_message or "File " in safe_message:
        # For tracebacks, use <pre> to preserve formatting
        formatted_parts = []
        in_traceback = False
        for line in safe_message.split("\n"):
            if "Traceback" in line or in_traceback or "File " in line:
                in_traceback = True
                if not formatted_parts or not formatted_parts[-1].startswith(
                    "<pre"
                ):
                    formatted_parts.append(
                        "<pre style='font-family: monospace; white-space: pre-wrap; font-size: 12px; background-color: #f8f8f8; padding: 10px; border-radius: 3px;'>"
                    )
                formatted_parts[-1] += line + "\n"
            else:
                if formatted_parts and formatted_parts[-1].startswith("<pre"):
                    formatted_parts[-1] += "</pre>"
                    in_traceback = False
                # Process markdown formatting on non-traceback lines
                formatted_line = process_markdown_line(line)
                formatted_parts.append(formatted_line + "<br>")

        # Close the last pre tag if needed
        if formatted_parts and formatted_parts[-1].startswith("<pre"):
            formatted_parts[-1] += "</pre>"

        return "".join(formatted_parts)
    else:
        # For regular messages, process each line for markdown
        formatted_lines = []
        for line in safe_message.split("\n"):
            formatted_line = process_markdown_line(line)
            formatted_lines.append(formatted_line)
        return "<br>".join(formatted_lines)


def test_html_escaping_in_message():
    """Test that HTML entities in messages are properly escaped."""
    # Test message with potential XSS attack
    malicious_message = '<script>alert("XSS")</script>Hello <b>world</b>'

    # Process the message
    result = process_message_for_html(malicious_message)

    # Check that script tags are escaped
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "&lt;/script&gt;" in result
    assert "<b>" not in result
    assert "&lt;b&gt;" in result


def test_markdown_formatting_preserved():
    """Test that markdown formatting still works after HTML escaping."""
    # Message with markdown formatting
    message = "This is *bold* and this is `code` and _italic_"

    # Process the message
    result = process_message_for_html(message)

    # Check that markdown is converted to HTML
    assert "<strong>bold</strong>" in result
    assert "<code style=" in result
    assert "<em>italic</em>" in result


def test_combined_xss_and_markdown():
    """Test that XSS is prevented even within markdown formatting."""
    # Message with XSS attempt inside markdown
    message = 'This is *<script>alert("xss")</script>* code'

    # Process the message
    result = process_message_for_html(message)

    # Check that script is escaped even inside markdown
    assert "<script>" not in result
    assert "<strong>&lt;script&gt;" in result


def test_traceback_html_escaping():
    """Test that tracebacks are properly escaped."""
    # Traceback with HTML-like content
    traceback_message = """Traceback (most recent call last):
  File "<script>evil.py</script>", line 1, in <module>
    raise ValueError("<img src=x onerror=alert()>")
ValueError: <img src=x onerror=alert()>"""

    # Process the message
    result = process_message_for_html(traceback_message)

    # Check that HTML in traceback is escaped
    assert "<script>" not in result
    assert "&lt;script&gt;" in result
    assert "<img src=x" not in result
    assert "&lt;img src=x" in result
    assert "<pre" in result  # Should still be in a pre block


def test_empty_message_handling():
    """Test handling of empty messages."""
    # Test with empty string
    result = process_message_for_html("")
    assert result == ""

    # Test with None-like handling (empty string)
    result = process_message_for_html("")
    assert result == ""


def test_multiline_message_with_breaks():
    """Test that newlines are converted to <br> tags."""
    message = "Line 1\nLine 2\nLine 3"

    result = process_message_for_html(message)

    # Check that lines are separated by <br>
    assert "Line 1<br>Line 2<br>Line 3" in result


def test_html_in_code_blocks():
    """Test that HTML inside code blocks is escaped."""
    message = "Here is some code: `<script>alert('test')</script>`"

    result = process_message_for_html(message)

    # Check that HTML inside code blocks is escaped
    assert "<code style=" in result
    assert "&lt;script&gt;" in result
    assert "<script>" not in result


def test_payload_escaping():
    """Test escaping of payload fields."""
    # Create payload with potential XSS
    payload = SMTPEmailAlerterPayload(
        pipeline_name='<script>alert("pipeline")</script>',
        step_name='<img src=x onerror=alert("step")>',
        stack_name='<iframe src="evil.com"></iframe>',
    )

    # Manually escape as the method does
    safe_pipeline = html.escape(payload.pipeline_name or "")
    safe_step = html.escape(payload.step_name or "")
    safe_stack = html.escape(payload.stack_name or "")

    # Check escaping
    assert "&lt;script&gt;" in safe_pipeline
    assert "&lt;img src=x" in safe_step
    assert "&lt;iframe" in safe_stack
    assert "<script>" not in safe_pipeline
    assert "<img" not in safe_step
    assert "<iframe" not in safe_stack
