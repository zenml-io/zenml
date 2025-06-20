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
"""Functionality for OpenAI standard hooks."""

import traceback
from typing import Optional

from openai import OpenAI

from zenml import get_step_context
from zenml.client import Client
from zenml.hooks import get_failure_template
from zenml.logger import get_logger
from zenml.utils.markdown_utils import (
    FULL_MARKDOWN_OPTIONS,
    MarkdownOutputFormat,
    format_markdown,
)

logger = get_logger(__name__)


def openai_alerter_failure_hook_helper(
    exception: BaseException,
    model_name: str,
) -> None:
    """Standard failure hook that sends a message to an Alerter.

    Your OpenAI API key must be stored in the secret store under the name
    "openai" and with the key "api_key".

    Args:
        exception: The exception that was raised.
        model_name: The OpenAI model to use for the chatbot.

    This implementation uses the OpenAI v1 SDK with automatic retries and backoff.
    """
    client = Client()
    context = get_step_context()

    # get the api_key from the secret store
    try:
        openai_secret = client.get_secret(
            "openai", allow_partial_name_match=False
        )
        openai_api_key: Optional[str] = openai_secret.secret_values.get(
            "api_key"
        )
    except (KeyError, NotImplementedError):
        openai_api_key = None

    alerter = client.active_stack.alerter
    if alerter and openai_api_key:
        # Check if we're using SMTP Email alerter and conditionally import if needed
        is_smtp_email_alerter = False
        smtp_params = None
        smtp_payload = None

        try:
            from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
                SMTPEmailAlerter,
                SMTPEmailAlerterParameters,
                SMTPEmailAlerterPayload,
            )

            is_smtp_email_alerter = isinstance(alerter, SMTPEmailAlerter)
            if is_smtp_email_alerter:
                # Make these available for later use
                smtp_params = SMTPEmailAlerterParameters
                smtp_payload = SMTPEmailAlerterPayload
        except ImportError:
            pass

        # Get standard Python traceback instead of Rich traceback for better email compatibility
        tb_lines = traceback.format_exception(
            type(exception), exception, exception.__traceback__
        )
        plain_traceback = "".join(tb_lines).strip()

        # Initialize OpenAI client with timeout and retry settings
        openai_client = OpenAI(
            api_key=openai_api_key,
            max_retries=3,  # Will retry 3 times with exponential backoff
            timeout=60.0,  # 60 second timeout
        )

        # Create chat completion using the new client pattern
        response = openai_client.chat.completions.create(
            model=model_name,
            messages=[
                {
                    "role": "user",
                    "content": f"This is an error message (following an exception of type '{type(exception)}') "
                    f"I encountered while executing a ZenML step. Please suggest ways I might fix the problem. "
                    f"Feel free to give code snippets as examples: {exception} -- {plain_traceback}. "
                    f"For formatting, please use bullet points (•) instead of numbered lists for better display. "
                    f"Thank you!",
                }
            ],
        )

        suggestion = response.choices[0].message.content

        # Format the alert message
        message = "\n".join(
            [
                "*Failure Hook Notification! Step failed!*",
                "",
                f"Run name: `{context.pipeline_run.name}`",
                f"Step name: `{context.step_run.name}`",
                f"Parameters: `{context.step_run.config.parameters}`",
                f"Exception: `({type(exception)}) {exception}`",
                "",
                f"*OpenAI ChatGPT's suggestion (model = `{model_name}`) on how to fix it:*\n{suggestion}",
            ]
        )

        # If using SMTP Email alerter, use specialized formatting for better email display
        if is_smtp_email_alerter and smtp_params and smtp_payload:
            # Create a plain text message for email body
            plain_message = f"""OpenAI Failure Hook Notification - Step failed!

Step: {context.step_run.name}
Pipeline: {context.pipeline.name}
Run: {context.pipeline_run.name}
Stack: {client.active_stack.name}
Parameters: {context.step_run.config.parameters}
Exception: ({type(exception).__name__}) {exception}

OpenAI ChatGPT's suggestion (model = {model_name}) on how to fix it:
{suggestion}

{plain_traceback}
"""
            # Use the shared template for consistency, but add an OpenAI-specific section
            additional_content = [
                {
                    "title": f"OpenAI ChatGPT's suggestion (model = {model_name})",
                    "content": format_markdown(
                        suggestion,
                        output_format=MarkdownOutputFormat.HTML,
                        options=FULL_MARKDOWN_OPTIONS,
                    )
                    if suggestion
                    else "No suggestion available.",
                    "bg_color": "#f0f7ff",
                    "is_pre": False,
                }
            ]

            html_body = get_failure_template(
                pipeline_name=context.pipeline.name,
                step_name=context.step_run.name,
                run_name=context.pipeline_run.name,
                stack_name=client.active_stack.name,
                exception_type=type(exception).__name__,
                exception_str=str(exception),
                traceback=plain_traceback,
                additional_content=additional_content,
                title="ZenML OpenAI Pipeline Failure Alert",
            )

            # Create a payload with relevant pipeline information
            payload = smtp_payload(
                pipeline_name=context.pipeline.name,
                step_name=context.step_run.name,
                stack_name=client.active_stack.name,
            )

            # Clean up Markdown formatting in subject
            clean_pipeline_name = context.pipeline.name.replace(
                "*", ""
            ).replace("`", "")
            clean_step_name = context.step_run.name.replace("*", "").replace(
                "`", ""
            )

            # Create parameters with HTML enabled and a clear subject
            params = smtp_params(
                subject=f"ZenML OpenAI Failure: {clean_pipeline_name} - {clean_step_name}",
                include_html=True,
                payload=payload,
                html_body=html_body,
            )

            # Post the alert with our email-optimized parameters
            alerter.post(plain_message, params=params)
        else:
            # For non-email alerters, use the standard formatting
            alerter.post(message)
    elif not openai_api_key:
        logger.warning(
            "Specified OpenAI failure hook but no OpenAI API key found. Skipping..."
        )
    else:
        logger.warning(
            "Specified OpenAI failure hook but no alerter configured in the stack. Skipping..."
        )


def openai_chatgpt_alerter_failure_hook(
    exception: BaseException,
) -> None:
    """Alerter hook that uses the OpenAI ChatGPT model.

    Args:
        exception: The exception that was raised.
    """
    openai_alerter_failure_hook_helper(exception, "gpt-4o")


def openai_gpt4_alerter_failure_hook(
    exception: BaseException,
) -> None:
    """Alerter hook that uses the OpenAI GPT-4 model.

    Args:
        exception: The exception that was raised.
    """
    openai_alerter_failure_hook_helper(exception, "gpt-4")
