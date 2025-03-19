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
"""Templates for email notifications and other formatted outputs."""

from typing import Any, Dict, List, Optional


def get_html_email_template(
    title: str,
    table_rows: List[Dict[str, str]],
    content_sections: List[Dict[str, Any]],
    footer_text: str = "This is an automated message from ZenML. Please do not reply to this email.",
) -> str:
    """Generate a standard HTML email template.

    Args:
        title: The title to display at the top of the email
        table_rows: List of dictionaries, each with 'label' and 'value' keys for the info table
        content_sections: List of content section dictionaries, each with:
            - 'title' (optional): Section title
            - 'content': The content to display
            - 'bg_color' (optional): Background color for the section
            - 'text_color' (optional): Text color for the section
            - 'is_pre' (optional): Whether to render as preformatted text
        footer_text: Text to display in the footer

    Returns:
        HTML string for the email template
    """
    # Start with the base template
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 20px; border-radius: 5px;">
          <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://zenml-strapi-media.s3.eu-central-1.amazonaws.com/03_Zen_ML_Logo_Square_White_efefc24ae7.png" alt="ZenML Logo" width="100" style="background-color: #361776; padding: 10px; border-radius: 10px;">
          </div>
          <h2 style="color: #361776; margin-bottom: 20px;">{title}</h2>
    """

    # Add the info table
    if table_rows:
        html += """
          <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
        """
        for row in table_rows:
            label = row.get("label", "")
            value = row.get("value", "")
            html += f"""
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd; width: 30%;"><strong>{label}:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{value}</td>
            </tr>
            """
        html += """
          </table>
        """

    # Add content sections
    for section in content_sections:
        bg_color = section.get("bg_color", "#f3f3f3")
        text_color = section.get("text_color", "inherit")
        section_title = section.get("title", "")
        content = section.get("content", "")
        is_pre = section.get("is_pre", False)

        html += f"""
          <div style="background-color: {bg_color}; padding: 15px; border-radius: 5px; margin-bottom: 20px; overflow-x: auto;">
        """

        if section_title:
            html += f"""
            <p style="margin: 0;"><strong>{section_title}:</strong></p>
            """

        if is_pre:
            html += f"""
            <pre style="margin: 0; font-family: monospace; white-space: pre-wrap; font-size: 12px; padding: 10px; background-color: #f0f0f0; border-radius: 3px;">{content}</pre>
            """
        else:
            html += f"""
            <p style="margin-top: 10px; color: {text_color};">{content}</p>
            """

        html += """
          </div>
        """

    # Add the footer
    html += f"""
          <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #777; font-size: 12px;">
            <p>{footer_text}</p>
          </div>
        </div>
      </body>
    </html>
    """

    return html


def get_success_template(
    pipeline_name: str,
    step_name: str,
    run_name: str,
    stack_name: str,
    title: str = "ZenML Pipeline Success",
    status_message: str = "The step has completed successfully.",
    additional_content: Optional[List[Dict[str, Any]]] = None,
) -> str:
    """Generate HTML for a success notification email.

    Args:
        pipeline_name: Name of the pipeline
        step_name: Name of the step
        run_name: Name of the run
        stack_name: Name of the stack
        title: Custom title for the email. Defaults to "ZenML Pipeline Success"
        status_message: Custom status message. Defaults to "The step has completed successfully."
        additional_content: Additional content sections to include

    Returns:
        HTML string for the success email
    """
    table_rows = [
        {"label": "Pipeline", "value": pipeline_name},
        {"label": "Step", "value": step_name},
        {"label": "Run", "value": run_name},
        {"label": "Stack", "value": stack_name},
    ]

    content_sections = [
        {
            "title": "Status",
            "content": status_message,
            "bg_color": "#e8f5e9",
            "text_color": "#2e7d32",
        }
    ]

    # Add any additional content sections
    if additional_content:
        content_sections.extend(additional_content)

    return get_html_email_template(
        title=title,
        table_rows=table_rows,
        content_sections=content_sections,
    )


def get_failure_template(
    pipeline_name: str,
    step_name: str,
    run_name: str,
    stack_name: str,
    exception_type: str,
    exception_str: str,
    traceback: str,
    additional_content: Optional[List[Dict[str, Any]]] = None,
    title: str = "ZenML Pipeline Failure Alert",
) -> str:
    """Generate HTML for a failure notification email.

    Args:
        pipeline_name: Name of the pipeline
        step_name: Name of the step
        run_name: Name of the run
        stack_name: Name of the stack
        exception_type: Type of the exception
        exception_str: Exception message
        traceback: Exception traceback
        additional_content: Additional content sections to include
        title: Custom title for the email. Defaults to "ZenML Pipeline Failure Alert"

    Returns:
        HTML string for the failure email
    """
    table_rows = [
        {"label": "Pipeline", "value": pipeline_name},
        {"label": "Step", "value": step_name},
        {"label": "Run", "value": run_name},
        {"label": "Stack", "value": stack_name},
        {"label": "Exception Type", "value": exception_type},
    ]

    content_sections = [
        {
            "title": "Error Message",
            "content": exception_str,
            "bg_color": "#f3f3f3",
            "text_color": "#e53935",
        },
    ]

    # Add any additional content sections
    if additional_content:
        content_sections.extend(additional_content)

    # Add traceback section
    content_sections.append(
        {
            "title": "Traceback",
            "content": traceback,
            "bg_color": "#f8f8f8",
            "is_pre": True,
        }
    )

    return get_html_email_template(
        title=title,
        table_rows=table_rows,
        content_sections=content_sections,
    )
