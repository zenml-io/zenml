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
"""Unit tests for email template functions."""

from zenml.hooks.templates import (
    get_failure_template,
    get_html_email_template,
    get_success_template,
)


def test_get_html_email_template_basic():
    """Test basic HTML email template generation."""
    html = get_html_email_template(
        title="Test Title",
        table_rows=[
            {"label": "Key1", "value": "Value1"},
            {"label": "Key2", "value": "Value2"},
        ],
        content_sections=[
            {
                "title": "Section 1",
                "content": "This is content",
            }
        ],
    )
    
    # Check that essential elements are present
    assert "<html>" in html
    assert "</html>" in html
    assert "Test Title" in html
    assert "Key1" in html
    assert "Value1" in html
    assert "Key2" in html
    assert "Value2" in html
    assert "Section 1" in html
    assert "This is content" in html
    assert "ZenML Logo" in html
    

def test_get_html_email_template_with_pre_section():
    """Test HTML email template with preformatted content."""
    html = get_html_email_template(
        title="Test",
        table_rows=[],
        content_sections=[
            {
                "content": "def hello():\n    print('world')",
                "is_pre": True,
            }
        ],
    )
    
    # Check for pre tag
    assert "<pre" in html
    assert "</pre>" in html
    assert "def hello():" in html
    assert "print('world')" in html


def test_get_html_email_template_with_custom_colors():
    """Test HTML email template with custom colors."""
    html = get_html_email_template(
        title="Test",
        table_rows=[],
        content_sections=[
            {
                "content": "Custom colored content",
                "bg_color": "#ff0000",
                "text_color": "#0000ff",
            }
        ],
    )
    
    # Check for custom colors
    assert "background-color: #ff0000" in html
    assert "color: #0000ff" in html


def test_get_html_email_template_custom_footer():
    """Test HTML email template with custom footer."""
    custom_footer = "Custom footer text"
    html = get_html_email_template(
        title="Test",
        table_rows=[],
        content_sections=[],
        footer_text=custom_footer,
    )
    
    assert custom_footer in html


def test_get_success_template():
    """Test success template generation."""
    html = get_success_template(
        pipeline_name="test_pipeline",
        step_name="test_step",
        run_name="test_run",
        stack_name="test_stack",
    )
    
    # Check for success-specific elements
    assert "ZenML Pipeline Success" in html
    assert "test_pipeline" in html
    assert "test_step" in html
    assert "test_run" in html
    assert "test_stack" in html
    assert "completed successfully" in html
    assert "#e8f5e9" in html  # Success green background


def test_get_success_template_custom_title_and_message():
    """Test success template with custom title and message."""
    html = get_success_template(
        pipeline_name="test_pipeline",
        step_name="test_step", 
        run_name="test_run",
        stack_name="test_stack",
        title="Custom Success Title",
        status_message="Custom success message!",
    )
    
    assert "Custom Success Title" in html
    assert "Custom success message!" in html


def test_get_success_template_with_additional_content():
    """Test success template with additional content sections."""
    html = get_success_template(
        pipeline_name="test_pipeline",
        step_name="test_step",
        run_name="test_run",
        stack_name="test_stack",
        additional_content=[
            {
                "title": "Extra Info",
                "content": "Some additional information",
            }
        ],
    )
    
    assert "Extra Info" in html
    assert "Some additional information" in html


def test_get_failure_template():
    """Test failure template generation."""
    html = get_failure_template(
        pipeline_name="test_pipeline",
        step_name="test_step",
        run_name="test_run",
        stack_name="test_stack",
        exception_type="ValueError",
        exception_str="Something went wrong",
        traceback="Traceback (most recent call last):\n  File 'test.py', line 1\n    raise ValueError('oops')",
    )
    
    # Check for failure-specific elements
    assert "ZenML Pipeline Failure Alert" in html
    assert "test_pipeline" in html
    assert "test_step" in html
    assert "test_run" in html
    assert "test_stack" in html
    assert "ValueError" in html
    assert "Something went wrong" in html
    assert "Traceback" in html
    assert "#e53935" in html  # Error red color


def test_get_failure_template_custom_title():
    """Test failure template with custom title."""
    html = get_failure_template(
        pipeline_name="test_pipeline",
        step_name="test_step",
        run_name="test_run",
        stack_name="test_stack",
        exception_type="RuntimeError",
        exception_str="Error",
        traceback="trace",
        title="Critical Failure!",
    )
    
    assert "Critical Failure!" in html


def test_get_failure_template_with_additional_content():
    """Test failure template with additional content sections."""
    html = get_failure_template(
        pipeline_name="test_pipeline",
        step_name="test_step",
        run_name="test_run",
        stack_name="test_stack",
        exception_type="Exception",
        exception_str="Error", 
        traceback="trace",
        additional_content=[
            {
                "title": "Debug Info",
                "content": "Additional debugging information",
                "bg_color": "#ffcccc",
            }
        ],
    )
    
    assert "Debug Info" in html
    assert "Additional debugging information" in html
    assert "#ffcccc" in html


def test_empty_table_rows():
    """Test template with no table rows."""
    html = get_html_email_template(
        title="No Table",
        table_rows=[],
        content_sections=[{"content": "Just content"}],
    )
    
    # Should not have table tags if no rows
    assert "<table" not in html


def test_empty_content_sections():
    """Test template with no content sections."""
    html = get_html_email_template(
        title="No Content",
        table_rows=[{"label": "Test", "value": "Value"}],
        content_sections=[],
    )
    
    # Should still have the table
    assert "<table" in html
    assert "Test" in html
    assert "Value" in html