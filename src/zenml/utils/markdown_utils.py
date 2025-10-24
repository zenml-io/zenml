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
"""Unified markdown parsing and formatting utilities for ZenML alerters."""

import html
import re
from dataclasses import dataclass
from enum import Enum
from typing import List, Match, Optional


class MarkdownOutputFormat(Enum):
    """Output formats for markdown conversion."""

    HTML = "html"
    SLACK = "slack"
    DISCORD = "discord"
    PLAIN = "plain"


@dataclass
class MarkdownOptions:
    """Configuration options for markdown processing."""

    # Basic formatting
    inline_code: bool = True
    bold: bool = True
    italic: bool = True

    # Advanced formatting
    code_blocks: bool = False
    headers: bool = False
    lists: bool = False
    paragraphs: bool = False

    # Special features
    traceback_detection: bool = False
    html_escaping: bool = True

    # Styling (for HTML output)
    code_style: str = "background-color: #f5f5f5; padding: 2px 4px; border-radius: 3px; font-family: monospace;"
    pre_style: str = "font-family: monospace; white-space: pre-wrap; font-size: 12px; background-color: #f8f8f8; padding: 10px; border-radius: 3px;"
    traceback_style: str = "font-family: monospace; white-space: pre-wrap; font-size: 12px; background-color: #f8f8f8; padding: 10px; border-radius: 3px;"


# Preset configurations
EMAIL_MARKDOWN_OPTIONS = MarkdownOptions(
    inline_code=True,
    bold=True,
    italic=True,
    code_blocks=True,
    traceback_detection=True,
    paragraphs=True,
    html_escaping=True,
)

FULL_MARKDOWN_OPTIONS = MarkdownOptions(
    inline_code=True,
    bold=True,
    italic=True,
    code_blocks=True,
    headers=True,
    lists=True,
    paragraphs=True,
    html_escaping=True,
)

BASIC_MARKDOWN_OPTIONS = MarkdownOptions(
    inline_code=True,
    bold=True,
    italic=True,
    html_escaping=True,
)


def escape_html_safely(text: str) -> str:
    """Escapes HTML characters to prevent injection.

    Args:
        text: The text to escape.

    Returns:
        HTML-escaped string.
    """
    return html.escape(text)


def format_code_blocks(text: str, style: Optional[str] = None) -> str:
    """Formats markdown code blocks (```) to HTML.

    Args:
        text: The text containing code blocks.
        style: Optional CSS style for the pre block.

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
        style_attr = f' style="{style}"' if style else ""
        return f"<pre{style_attr}><code>{code}</code></pre>"

    return re.sub(pattern, replacer, text)


def format_inline_code(
    text: str,
    style: Optional[str] = None,
    output_format: MarkdownOutputFormat = MarkdownOutputFormat.HTML,
) -> str:
    """Formats inline code (`) to the specified output format.

    Args:
        text: The text containing inline code.
        style: Optional CSS style for HTML output.
        output_format: The target output format.

    Returns:
        Text with inline code converted to the specified format.
    """
    if output_format == MarkdownOutputFormat.HTML:
        # Split by HTML tags to avoid processing already converted content
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
                style_attr = f' style="{style}"' if style else ""
                processed = re.sub(
                    r"`([^`]+)`",
                    rf"<code{style_attr}>\1</code>",
                    part,
                )
                result_parts.append(processed)

        return "".join(result_parts)
    elif output_format == MarkdownOutputFormat.SLACK:
        # Slack uses backticks for inline code
        return text  # Keep as-is for Slack
    elif output_format == MarkdownOutputFormat.DISCORD:
        # Discord uses backticks for inline code
        return text  # Keep as-is for Discord
    else:
        # Plain text - remove formatting
        return re.sub(r"`([^`]+)`", r"\1", text)


def format_bold(
    text: str, output_format: MarkdownOutputFormat = MarkdownOutputFormat.HTML
) -> str:
    """Formats bold text to the specified output format.

    Args:
        text: The text containing bold markdown.
        output_format: The target output format.

    Returns:
        Text with bold markdown converted to the specified format.
    """
    if output_format == MarkdownOutputFormat.HTML:
        return re.sub(r"\*\*([^*\n]+)\*\*", r"<strong>\1</strong>", text)
    elif output_format == MarkdownOutputFormat.SLACK:
        # Slack uses *text* for bold
        return re.sub(r"\*\*([^*\n]+)\*\*", r"*\1*", text)
    elif output_format == MarkdownOutputFormat.DISCORD:
        # Discord uses **text** for bold
        return text  # Keep as-is for Discord
    else:
        # Plain text - remove formatting
        return re.sub(r"\*\*([^*\n]+)\*\*", r"\1", text)


def format_italic(
    text: str, output_format: MarkdownOutputFormat = MarkdownOutputFormat.HTML
) -> str:
    """Formats italic text to the specified output format.

    Args:
        text: The text containing italic markdown.
        output_format: The target output format.

    Returns:
        Text with italic markdown converted to the specified format.
    """
    if output_format == MarkdownOutputFormat.HTML:
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
    elif output_format == MarkdownOutputFormat.SLACK:
        # Slack uses _text_ for italic
        text = re.sub(r"\*([^*\n]+)\*", r"_\1_", text)
        return text  # Keep underscores as-is
    elif output_format == MarkdownOutputFormat.DISCORD:
        # Discord uses *text* for italic
        text = re.sub(r"_([^_\n]+)_", r"*\1*", text)
        return text
    else:
        # Plain text - remove formatting
        text = re.sub(r"\*([^*\n]+)\*", r"\1", text)
        text = re.sub(r"_([^_\n]+)_", r"\1", text)
        return text


def format_headers(text: str) -> str:
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


def format_numbered_lists(text: str) -> str:
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


def format_bullet_lists(text: str) -> str:
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


def format_paragraphs(text: str) -> str:
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


def detect_and_format_tracebacks(
    text: str, style: Optional[str] = None
) -> str:
    """Detects Python tracebacks and formats them with special styling.

    Args:
        text: The text that may contain tracebacks.
        style: Optional CSS style for the pre block.

    Returns:
        Text with tracebacks formatted in pre blocks.
    """
    if "Traceback" not in text and "File " not in text:
        return text

    formatted_parts: List[str] = []
    in_traceback = False
    lines = text.split("\n")

    for line in lines:
        if "Traceback" in line or in_traceback or "File " in line:
            in_traceback = True
            if not formatted_parts or not formatted_parts[-1].startswith(
                "<pre"
            ):
                style_attr = f' style="{style}"' if style else ""
                formatted_parts.append(f"<pre{style_attr}>")
            formatted_parts[-1] += line + "\n"
        else:
            if formatted_parts and formatted_parts[-1].startswith("<pre"):
                formatted_parts[-1] += "</pre>"
                in_traceback = False
            formatted_parts.append(line + "<br>")

    # Close the last pre tag if needed
    if formatted_parts and formatted_parts[-1].startswith("<pre"):
        formatted_parts[-1] += "</pre>"

    return "".join(formatted_parts)


def format_markdown(
    text: str,
    output_format: MarkdownOutputFormat = MarkdownOutputFormat.HTML,
    options: Optional[MarkdownOptions] = None,
) -> str:
    """Convert markdown text to specified output format.

    Args:
        text: The markdown text to format.
        output_format: The target output format.
        options: Configuration options for formatting.

    Returns:
        Formatted text in the specified output format.
    """
    if not text:
        return ""

    if options is None:
        options = BASIC_MARKDOWN_OPTIONS

    result = text

    # First escape HTML characters to prevent injection (if enabled)
    if options.html_escaping and output_format == MarkdownOutputFormat.HTML:
        result = escape_html_safely(result)

    # Apply transformations in the correct order for HTML output
    if output_format == MarkdownOutputFormat.HTML:
        # 1. Process traceback detection first (if enabled)
        if options.traceback_detection:
            result = detect_and_format_tracebacks(
                result, options.traceback_style
            )

        # 2. Process code blocks (to prevent other formatting inside code)
        if options.code_blocks:
            result = format_code_blocks(result, options.pre_style)

        # 3. Process inline code (avoiding already processed HTML tags)
        if options.inline_code:
            result = format_inline_code(
                result, options.code_style, output_format
            )

        # 4. Process bold formatting
        if options.bold:
            result = format_bold(result, output_format)

        # 5. Process italic formatting
        if options.italic:
            result = format_italic(result, output_format)

        # 6. Process headers
        if options.headers:
            result = format_headers(result)

        # 7. Process numbered lists (converts to bullets)
        if options.lists:
            result = format_numbered_lists(result)

        # 8. Process bullet lists
        if options.lists:
            result = format_bullet_lists(result)

        # 9. Process paragraphs and line breaks
        if options.paragraphs:
            result = format_paragraphs(result)

    else:
        # For non-HTML formats, apply simpler transformations
        if options.bold:
            result = format_bold(result, output_format)

        if options.italic:
            result = format_italic(result, output_format)

        if options.inline_code:
            result = format_inline_code(result, None, output_format)

        # Convert numbered lists to bullets for consistency
        if options.lists:
            result = format_numbered_lists(result)

    return result
