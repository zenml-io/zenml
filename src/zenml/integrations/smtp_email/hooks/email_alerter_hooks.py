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

import traceback

from zenml import get_step_context
from zenml.client import Client
from zenml.hooks import get_failure_template, get_success_template
from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
    SMTPEmailAlerter,
    SMTPEmailAlerterParameters,
    SMTPEmailAlerterPayload,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


def smtp_email_alerter_failure_hook(exception: BaseException) -> None:
    """Email-specific failure hook that executes after step fails.

    This hook is optimized for SMTP Email alerters, providing proper
    email formatting with HTML support. It organizes the error information
    in a structured way that displays well in email clients.

    Args:
        exception: Original exception that lead to step failing.
    """
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
        tb_lines = traceback.format_exception(
            type(exception), exception, exception.__traceback__
        )
        plain_traceback = "".join(tb_lines).strip()

        message = "*Failure Hook Notification! Step failed!*" + "\n\n"
        message += f"Pipeline name: `{context.pipeline.name}`" + "\n"
        message += f"Run name: `{context.pipeline_run.name}`" + "\n"
        message += f"Step name: `{context.step_run.name}`" + "\n"
        message += f"Parameters: `{context.step_run.config.parameters}`" + "\n"
        message += (
            f"Exception: `({type(exception).__name__}) {str(exception)}`"
            + "\n\n"
        )
        message += f"{plain_traceback}"
        alerter.post(message)
        return

    # Get a standard Python traceback instead of a Rich one
    tb_lines = traceback.format_exception(
        type(exception), exception, exception.__traceback__
    )
    plain_traceback = "".join(tb_lines)

    # Clean up the traceback to remove any leading/trailing whitespace
    plain_traceback = plain_traceback.strip()

    # Create a clean exception string without the traceback
    exception_str = str(exception)

    # Prepare plain text message for email body - this is for the plain text part
    message = f"""Pipeline Failure Alert

Step: {context.step_run.name}
Pipeline: {context.pipeline.name}
Run: {context.pipeline_run.name}
Stack: {Client().active_stack.name}

Error: {exception_str}

{plain_traceback}
"""

    # Use the shared template for consistent styling
    html_body = get_failure_template(
        pipeline_name=context.pipeline.name,
        step_name=context.step_run.name,
        run_name=context.pipeline_run.name,
        stack_name=Client().active_stack.name,
        exception_type=type(exception).__name__,
        exception_str=exception_str,
        traceback=plain_traceback,
    )

    # Create a payload with relevant pipeline information
    payload = SMTPEmailAlerterPayload(
        pipeline_name=context.pipeline.name,
        step_name=context.step_run.name,
        stack_name=Client().active_stack.name,
    )

    # Create parameters with HTML enabled and a clear subject
    # Remove any potential Markdown formatting (*bold*, `code`, etc.) from the subject
    # as email subjects can't render formatting
    clean_pipeline_name = context.pipeline.name.replace("*", "").replace(
        "`", ""
    )
    clean_step_name = context.step_run.name.replace("*", "").replace("`", "")

    params = SMTPEmailAlerterParameters(
        subject=f"ZenML Pipeline Failure: {clean_pipeline_name} - {clean_step_name}",
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

    # Use the shared template for consistent styling
    html_body = get_success_template(
        pipeline_name=context.pipeline.name,
        step_name=context.step_run.name,
        run_name=context.pipeline_run.name,
        stack_name=Client().active_stack.name,
    )

    # Create a payload with relevant pipeline information
    payload = SMTPEmailAlerterPayload(
        pipeline_name=context.pipeline.name,
        step_name=context.step_run.name,
        stack_name=Client().active_stack.name,
    )

    # Create parameters with HTML enabled and a clear subject
    # Remove any potential Markdown formatting (*bold*, `code`, etc.) from the subject
    # as email subjects can't render formatting
    clean_pipeline_name = context.pipeline.name.replace("*", "").replace(
        "`", ""
    )
    clean_step_name = context.step_run.name.replace("*", "").replace("`", "")

    params = SMTPEmailAlerterParameters(
        subject=f"ZenML Pipeline Success: {clean_pipeline_name} - {clean_step_name}",
        include_html=True,
        payload=payload,
        html_body=html_body,  # Use our custom HTML template instead of the default
    )

    # Post the alert with our email-optimized parameters
    alerter.post(message, params=params)
