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
from typing import List, Match, Optional

from openai import OpenAI

from zenml import get_step_context
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)


def _format_markdown_for_html(markdown_text: str) -> str:
    """Formats markdown text for HTML display.

    Args:
        markdown_text: The markdown text to format.

    Returns:
        HTML formatted string.
    """
    import html
    import re

    # First escape HTML characters to prevent injection
    # We'll unescape code blocks later
    safe_text = html.escape(markdown_text)

    # Different code block patterns to handle:
    # 1. Multi-line code blocks with language annotation: ```python\ncode\n```
    # 2. Multi-line code blocks without language: ```\ncode\n```
    # 3. Single-line code blocks: ```code```

    # Handle multi-line code blocks with or without language annotation
    def process_code_blocks(text: str) -> str:
        # This pattern matches:
        # - Opening ``` optionally followed by a language identifier
        # - Content (possibly multi-line)
        # - Closing ```
        pattern = r"```([\w\+\#\-\.]+)?\s*\n?([\s\S]*?)\n?\s*```"

        def replacer(match: Match[str]) -> str:
            # Get the code and unescape HTML entities since we escaped everything earlier
            code = html.unescape(match.group(2))
            return f'<pre style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; font-family: monospace; overflow-x: auto; margin: 10px 0;"><code>{code}</code></pre>'

        return re.sub(pattern, replacer, text)

    # Process code blocks first
    result = process_code_blocks(safe_text)

    # Process inline code with backticks - but avoid processing code that's already in HTML tags
    def process_inline_code(text: str) -> str:
        # Split by HTML tags
        parts = re.split(
            r"(<pre.*?</pre>|<code.*?</code>)", text, flags=re.DOTALL
        )
        result_parts: List[str] = []

        for i, part in enumerate(parts):
            # Skip processing parts that are HTML tags (odd-indexed parts after the split)
            if i % 2 == 1:
                result_parts.append(part)
            else:
                # Process inline code in text parts
                processed = re.sub(
                    r"`([^`]+)`",
                    r'<code style="background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: monospace;">\1</code>',
                    part,
                )
                result_parts.append(processed)

        return "".join(result_parts)

    result = process_inline_code(result)

    # Process bold with double asterisks
    result = re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", result)

    # Process italics with single asterisks (but not ones we've already processed as bold)
    # Use a more reliable approach than look-behind/look-ahead
    def process_single_asterisks(text: str) -> str:
        # This pattern catches single asterisks but not double
        pattern = r"\*([^*\n]+)\*"

        def replacer(match: Match[str]) -> str:
            # Check if it's surrounded by other asterisks (part of bold)
            full_match = match.group(0)
            if "**" in full_match:
                return full_match
            return f"<em>{match.group(1)}</em>"

        return re.sub(pattern, replacer, text)

    result = process_single_asterisks(result)

    # Process italics with underscores
    result = re.sub(r"_([^_\n]+)_", r"<em>\1</em>", result)

    # Convert markdown headers
    result = re.sub(r"^# (.+)$", r"<h1>\1</h1>", result, flags=re.MULTILINE)
    result = re.sub(r"^## (.+)$", r"<h2>\1</h2>", result, flags=re.MULTILINE)
    result = re.sub(r"^### (.+)$", r"<h3>\1</h3>", result, flags=re.MULTILINE)

    # Handle numbered lists - convert them to bullet lists for consistency
    # This is simpler and avoids issues with auto-numbering in email clients
    numbered_list_pattern = r"^(\d+)\.\s+(.+)$"

    def replace_numbered_list(text: str) -> str:
        lines = text.split("\n")
        result_lines: List[str] = []

        for line in lines:
            match = re.match(numbered_list_pattern, line)
            if match:
                # Convert to a bullet point instead of keeping the number
                result_lines.append(f"• {match.group(2)}")
            else:
                result_lines.append(line)

        return "\n".join(result_lines)

    result = replace_numbered_list(result)

    # Handle bullet points - including the bullet symbol we added for numbered lists
    bullet_list_pattern = r"^[\*\-\+•]\s+(.+)$"

    def replace_bullet_list(text: str) -> str:
        lines = text.split("\n")
        in_list = False
        result_lines: List[str] = []

        for line in lines:
            match = re.match(bullet_list_pattern, line)
            if match:
                if not in_list:
                    result_lines.append("<ul>")
                    in_list = True
                result_lines.append(f"<li>{match.group(1)}</li>")
            else:
                if in_list:
                    result_lines.append("</ul>")
                    in_list = False
                result_lines.append(line)

        if in_list:
            result_lines.append("</ul>")

        return "\n".join(result_lines)

    result = replace_bullet_list(result)

    # Handle paragraphs and line breaks properly
    paragraphs = re.split(r"\n\s*\n", result)
    processed_paragraphs: List[str] = []

    for p in paragraphs:
        if not p.strip():
            continue

        # Skip wrapping with <p> if the content already has block-level HTML
        if re.match(r"^\s*<(pre|h[1-6]|ul|ol|table|blockquote)", p.strip()):
            processed_paragraphs.append(p.strip())
        else:
            # Replace single newlines with <br> within paragraphs
            processed_p = re.sub(r"\n", "<br>", p.strip())
            processed_paragraphs.append(f"<p>{processed_p}</p>")

    result = "\n".join(processed_paragraphs)

    return result


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
        # Check if we're using SMTP Email alerter and import related classes if needed
        is_smtp_email_alerter = False
        try:
            from zenml.integrations.smtp_email.alerters.smtp_email_alerter import (
                SMTPEmailAlerter,
                SMTPEmailAlerterParameters,
                SMTPEmailAlerterPayload,
            )

            is_smtp_email_alerter = isinstance(alerter, SMTPEmailAlerter)
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
        if is_smtp_email_alerter:
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
            # For HTML email, create a custom HTML body with proper formatting
            html_body = f"""
            <html>
              <body style="font-family: Arial, sans-serif; padding: 20px;">
                <div style="max-width: 600px; margin: 0 auto; background-color: #f9f9f9; padding: 20px; border-radius: 5px;">
                  <div style="text-align: center; margin-bottom: 20px;">
                    <img src="https://zenml-strapi-media.s3.eu-central-1.amazonaws.com/03_Zen_ML_Logo_Square_White_efefc24ae7.png" alt="ZenML Logo" width="100" style="background-color: #361776; padding: 10px; border-radius: 10px;">
                  </div>
                  <h2 style="color: #361776; margin-bottom: 20px;">ZenML OpenAI Pipeline Failure Alert</h2>
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
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;">{client.active_stack.name}</td>
                    </tr>
                    <tr>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Parameters:</strong></td>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;"><code>{context.step_run.config.parameters}</code></td>
                    </tr>
                    <tr>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;"><strong>Exception Type:</strong></td>
                      <td style="padding: 10px; border-bottom: 1px solid #ddd;">{type(exception).__name__}</td>
                    </tr>
                  </table>
                  <div style="background-color: #f3f3f3; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <p style="margin: 0;"><strong>Error Message:</strong></p>
                    <p style="margin-top: 10px; color: #e53935;">{exception}</p>
                  </div>
                  <div style="background-color: #f0f7ff; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                    <p style="margin: 0;"><strong>OpenAI ChatGPT's suggestion (model = {model_name}):</strong></p>
                    <div style="margin-top: 10px;">
                    {_format_markdown_for_html(suggestion) if suggestion else "No suggestion available."}
                    </div>
                  </div>
                  <div style="background-color: #f8f8f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; overflow-x: auto;">
                    <p style="margin: 0;"><strong>Traceback:</strong></p>
                    <pre style="margin: 0; font-family: monospace; white-space: pre-wrap; font-size: 12px; padding: 10px; background-color: #f0f0f0; border-radius: 3px;">{plain_traceback}</pre>
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
            params = SMTPEmailAlerterParameters(
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
