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
"""Functionality for SMTP Email alerter hooks."""

import io
import sys
from typing import Optional

from rich.console import Console

from zenml import get_step_context
from zenml.client import Client
from zenml.logger import get_logger

# Import these classes in the function body to avoid circular imports
# SMTPEmailAlerter, SMTPEmailAlerterParameters, SMTPEmailAlerterPayload

logger = get_logger(__name__)


def smtp_email_alerter_failure_hook(exception: BaseException) -> None:
    """Email-specific failure hook that executes after step fails.

    This hook is optimized for SMTP Email alerters, providing proper
    email formatting with HTML support. It organizes the error information
    in a structured way that displays well in email clients.

    Args:
        exception: Original exception that lead to step failing.
    """
    # Import here to avoid circular imports
    from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
        SMTPEmailAlerter,
        SMTPEmailAlerterParameters,
        SMTPEmailAlerterPayload,
    )
    
    context = get_step_context()
    alerter = Client().active_stack.alerter
    
    if not alerter:
        logger.warning(
            "Specified SMTP email failure hook but no alerter configured in the stack. Skipping.."
        )
        return
        
    if not isinstance(alerter, SMTPEmailAlerter):
        logger.warning(
            "Specified SMTP email failure hook but alerter is not an SMTP Email alerter. "
            "Using alerter.post() directly which may result in formatting issues."
        )
        # Fall back to standard message format
        output_captured = io.StringIO()
        original_stdout = sys.stdout
        sys.stdout = output_captured
        console = Console()
        console.print_exception(show_locals=False)

        sys.stdout = original_stdout
        rich_traceback = output_captured.getvalue()

        message = "*Failure Hook Notification! Step failed!*" + "\n\n"
        message += f"Pipeline name: `{context.pipeline.name}`" + "\n"
        message += f"Run name: `{context.pipeline_run.name}`" + "\n"
        message += f"Step name: `{context.step_run.name}`" + "\n"
        message += f"Parameters: `{context.step_run.config.parameters}`" + "\n"
        message += (
            f"Exception: `({type(exception)}) {rich_traceback}`" + "\n\n"
        )
        alerter.post(message)
        return

    # Capture rich traceback
    output_captured = io.StringIO()
    original_stdout = sys.stdout
    sys.stdout = output_captured
    console = Console()
    console.print_exception(show_locals=False)

    sys.stdout = original_stdout
    rich_traceback = output_captured.getvalue()
    
    # Clean up the traceback to remove any leading/trailing whitespace
    # and handle any special cases that might appear in the rich traceback
    rich_traceback = rich_traceback.strip()

    # Create a clean exception string without the traceback
    exception_str = str(exception)
    
    # Prepare plain text message for email body - this is for the plain text part
    message = f"""Pipeline Failure Alert

Step: {context.step_run.name}
Pipeline: {context.pipeline.name}
Run: {context.pipeline_run.name}
Stack: {Client().active_stack.name}

Error: {exception_str}

{rich_traceback}
"""

    # For HTML email, we need to create a custom HTML body to properly format the traceback
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 20px; border-radius: 5px;">
          <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://zenml-strapi-media.s3.eu-central-1.amazonaws.com/03_Zen_ML_Logo_Square_White_efefc24ae7.png" alt="ZenML Logo" width="100" style="background-color: #361776; padding: 10px; border-radius: 10px;">
          </div>
          <h2 style="color: #361776; margin-bottom: 20px;">ZenML Pipeline Failure Alert</h2>
          <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd; width: 30%;"><strong>Pipeline:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{context.pipeline.name}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Step:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{context.step_run.name}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Run:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{context.pipeline_run.name}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Stack:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{Client().active_stack.name}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Exception Type:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{type(exception).__name__}</td>
            </tr>
          </table>
          <div style="background-color: #f3f3f3; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <p style="margin: 0;"><strong>Error Message:</strong></p>
            <p style="margin-top: 10px; color: #e53935;">{exception_str}</p>
          </div>
          <div style="background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; overflow-x: auto;">
            <pre style="margin: 0; font-family: monospace; white-space: pre-wrap; font-size: 12px; padding: 10px; background-color: #f0f0f0; border-radius: 3px;">{rich_traceback}</pre>
          </div>
          <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #777; font-size: 12px;">
            <p>This is an automated message from ZenML. Please do not reply to this email.</p>
          </div>
        </div>
      </body>
    </html>
    """

    # Create a payload with relevant pipeline information
    payload = SMTPEmailAlerterPayload(
        pipeline_name=context.pipeline.name,
        step_name=context.step_run.name,
        stack_name=Client().active_stack.name,
    )

    # Create parameters with HTML enabled and a clear subject
    params = SMTPEmailAlerterParameters(
        subject=f"ZenML Pipeline Failure: {context.pipeline.name} - {context.step_run.name}",
        include_html=True,
        payload=payload,
        html_body=html_body,  # Use our custom HTML template instead of the default
    )

    # Post the alert with our email-optimized parameters
    alerter.post(message, params=params)


def smtp_email_alerter_success_hook() -> None:
    """Email-specific success hook that executes after step completes successfully.

    This hook is optimized for SMTP Email alerters, providing proper
    email formatting with HTML support. It organizes the success information
    in a structured way that displays well in email clients.
    """
    # Import here to avoid circular imports
    from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
        SMTPEmailAlerter,
        SMTPEmailAlerterParameters,
        SMTPEmailAlerterPayload,
    )
    
    context = get_step_context()
    alerter = Client().active_stack.alerter
    
    if not alerter:
        logger.warning(
            "Specified SMTP email success hook but no alerter configured in the stack. Skipping.."
        )
        return
        
    if not isinstance(alerter, SMTPEmailAlerter):
        logger.warning(
            "Specified SMTP email success hook but alerter is not an SMTP Email alerter. "
            "Using alerter.post() directly which may result in formatting issues."
        )
        # Fall back to standard message format
        message = (
            "*Success Hook Notification! Step completed successfully*" + "\n\n"
        )
        message += f"Pipeline name: `{context.pipeline.name}`" + "\n"
        message += f"Run name: `{context.pipeline_run.name}`" + "\n"
        message += f"Step name: `{context.step_run.name}`" + "\n"
        message += f"Parameters: `{context.step_run.config.parameters}`" + "\n"
        alerter.post(message)
        return

    # Prepare plain text message for email body
    message = f"""Pipeline Success Notification

Step: {context.step_run.name}
Pipeline: {context.pipeline.name}
Run: {context.pipeline_run.name}
Stack: {Client().active_stack.name}

The step has completed successfully.
"""

    # For HTML email, we need to create a custom HTML body with proper formatting
    html_body = f"""
    <html>
      <body style="font-family: Arial, sans-serif; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 20px; border-radius: 5px;">
          <div style="text-align: center; margin-bottom: 20px;">
            <img src="https://zenml-strapi-media.s3.eu-central-1.amazonaws.com/03_Zen_ML_Logo_Square_White_efefc24ae7.png" alt="ZenML Logo" width="100" style="background-color: #361776; padding: 10px; border-radius: 10px;">
          </div>
          <h2 style="color: #361776; margin-bottom: 20px;">ZenML Pipeline Success</h2>
          <table style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd; width: 30%;"><strong>Pipeline:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{context.pipeline.name}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Step:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{context.step_run.name}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Run:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{context.pipeline_run.name}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Stack:</strong></td>
              <td style="padding: 10px; border-bottom: 1px solid #ddd;">{Client().active_stack.name}</td>
            </tr>
          </table>
          <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
            <p style="margin: 0; color: #2e7d32;"><strong>Status:</strong></p>
            <p style="margin-top: 10px; color: #2e7d32;">The step has completed successfully.</p>
          </div>
          <div style="text-align: center; margin-top: 20px; padding-top: 20px; border-top: 1px solid #ddd; color: #777; font-size: 12px;">
            <p>This is an automated message from ZenML. Please do not reply to this email.</p>
          </div>
        </div>
      </body>
    </html>
    """

    # Create a payload with relevant pipeline information
    payload = SMTPEmailAlerterPayload(
        pipeline_name=context.pipeline.name,
        step_name=context.step_run.name,
        stack_name=Client().active_stack.name,
    )

    # Create parameters with HTML enabled and a clear subject
    params = SMTPEmailAlerterParameters(
        subject=f"ZenML Pipeline Success: {context.pipeline.name} - {context.step_run.name}",
        include_html=True,
        payload=payload,
        html_body=html_body,  # Use our custom HTML template instead of the default
    )

    # Post the alert with our email-optimized parameters
    alerter.post(message, params=params)