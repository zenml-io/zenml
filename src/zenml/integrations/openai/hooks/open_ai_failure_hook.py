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

import html
import re
import traceback
from typing import List, Match, Optional

from openai import OpenAI

from zenml import get_step_context
from zenml.client import Client
from zenml.hooks import get_failure_template
from zenml.logger import get_logger

logger = get_logger(__name__)


def _escape_html_safely(text: str) -> str:
    """Escapes HTML characters to prevent injection.

    Args:
        text: The text to escape.

    Returns:
        HTML-escaped string.
    """
    return html.escape(text)


def _format_code_blocks(text: str) -> str:
    """Formats markdown code blocks (```) to HTML.

    Args:
        text: The text containing code blocks.

    Returns:
        Text with code blocks converted to HTML.
    """
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


def _format_inline_code(text: str) -> str:
    """Formats inline code (`) to HTML, avoiding already processed HTML tags.

    Args:
        text: The text containing inline code.

    Returns:
        Text with inline code converted to HTML.
    """
    # Split by HTML tags
    parts = re.split(r"(<pre.*?</pre>|<code.*?</code>)", text, flags=re.DOTALL)
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


def _format_bold(text: str) -> str:
    """Formats bold text (**text**) to HTML.

    Args:
        text: The text containing bold markdown.

    Returns:
        Text with bold markdown converted to HTML.
    """
    return re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", text)


def _format_italics(text: str) -> str:
    """Formats italic text (*text* and _text_) to HTML.

    Args:
        text: The text containing italic markdown.

    Returns:
        Text with italic markdown converted to HTML.
    """

    # Process single asterisks (but not ones that are part of bold)
    def process_single_asterisks(text: str) -> str:
        pattern = r"\*([^*\n]+)\*"

        def replacer(match: Match[str]) -> str:
            # Check if it's surrounded by other asterisks (part of bold)
            full_match = match.group(0)
            if "**" in full_match:
                return full_match
            return f"<em>{match.group(1)}</em>"

        return re.sub(pattern, replacer, text)

    text = process_single_asterisks(text)
    # Process underscores
    text = re.sub(r"_([^_\n]+)_", r"<em>\1</em>", text)
    return text


def _format_headers(text: str) -> str:
    """Formats markdown headers (# ## ###) to HTML.

    Args:
        text: The text containing markdown headers.

    Returns:
        Text with headers converted to HTML.
    """
    text = re.sub(r"^# (.+)$", r"<h1>\1</h1>", text, flags=re.MULTILINE)
    text = re.sub(r"^## (.+)$", r"<h2>\1</h2>", text, flags=re.MULTILINE)
    text = re.sub(r"^### (.+)$", r"<h3>\1</h3>", text, flags=re.MULTILINE)
    return text


def _format_numbered_lists(text: str) -> str:
    """Converts numbered lists to bullet points for consistency.

    Args:
        text: The text containing numbered lists.

    Returns:
        Text with numbered lists converted to bullet points.
    """
    numbered_list_pattern = r"^(\d+)\.\s+(.+)$"
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


def _format_bullet_lists(text: str) -> str:
    """Formats bullet lists to HTML unordered lists.

    Args:
        text: The text containing bullet lists.

    Returns:
        Text with bullet lists converted to HTML.
    """
    bullet_list_pattern = r"^[\*\-\+•]\s+(.+)$"
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


def _format_paragraphs(text: str) -> str:
    """Formats paragraphs and handles line breaks.

    Args:
        text: The text to format into paragraphs.

    Returns:
        Text with proper paragraph formatting.
    """
    paragraphs = re.split(r"\n\s*\n", text)
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

    return "\n".join(processed_paragraphs)


def _format_markdown_for_html(markdown_text: str) -> str:
    """Formats markdown text for HTML display.

    Args:
        markdown_text: The markdown text to format.

    Returns:
        HTML formatted string.
    """
    # First escape HTML characters to prevent injection
    # We'll unescape code blocks later
    safe_text = _escape_html_safely(markdown_text)

    # Apply transformations in the correct order
    result = safe_text

    # 1. Process code blocks first (to prevent other formatting inside code)
    result = _format_code_blocks(result)

    # 2. Process inline code (avoiding already processed HTML tags)
    result = _format_inline_code(result)

    # 3. Process bold formatting
    result = _format_bold(result)

    # 4. Process italic formatting
    result = _format_italics(result)

    # 5. Process headers
    result = _format_headers(result)

    # 6. Process numbered lists (converts to bullets)
    result = _format_numbered_lists(result)

    # 7. Process bullet lists
    result = _format_bullet_lists(result)

    # 8. Process paragraphs and line breaks
    result = _format_paragraphs(result)

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
                    "content": _format_markdown_for_html(suggestion)
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
