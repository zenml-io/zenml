#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""mcp-zenml's `report_feedback` (#113), as `zenml_report_feedback`.

It sends nothing: it drafts a GitHub issue on zenml-io/zenml as a link that
opens it pre-filled, for the user to read and submit.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import Any
from urllib.parse import quote, urlencode

from mcp.types import ToolAnnotations

from zenml_mcp.call import ZenMLCall
from zenml_mcp.client import ZenMLBadRequest
from zenml_mcp.registry import Tools

FEEDBACK_ISSUE_URL = "https://github.com/zenml-io/zenml/issues/new"
# Browsers and GitHub reject much longer links; 8,000 characters is a safe limit.
_MAX_ISSUE_URL_LENGTH = 8000
_MAX_FEEDBACK_TITLE_LENGTH = 200
_TRUNCATION_NOTE = (
    "\n\n_(Cut short to fit in a link. Paste the rest of the report here.)_"
)


def _zenml_version() -> str:
    # The installed distribution's metadata: importing `zenml` would load it.
    try:
        return version("zenml")
    except PackageNotFoundError:
        return "unknown"


def _issue_body(
    what_happened: str, proposed_fix: str, tool_name: str | None
) -> str:
    context = [f"- ZenML MCP: zenml {_zenml_version()}"]
    if tool_name:
        context.insert(0, f"- Tool: `{tool_name}`")
    return "\n".join(
        [
            "## What happened",
            what_happened,
            "",
            "## Proposed fix",
            proposed_fix,
            "",
            "## Context",
            *context,
            "",
            "_Drafted by an AI agent with the `zenml_report_feedback` tool._",
        ]
    )


def _issue_url(title: str, body: str) -> str:
    query = urlencode({"title": title, "body": body}, quote_via=quote)
    return f"{FEEDBACK_ISSUE_URL}?{query}"


def _prefilled_issue_url(title: str, body: str) -> tuple[str, bool]:
    """A new-issue link, its body cut as little as needed to fit.

    Args:
        title: The issue's title.
        body: The issue's body.

    Returns:
        The link, and whether the body was cut.
    """
    url = _issue_url(title, body)
    if len(url) <= _MAX_ISSUE_URL_LENGTH:
        return url, False
    # The longest body prefix whose link, with the note, fits. Each character
    # encodes to at least one, so more than the limit never fits.
    low, high = 0, min(len(body), _MAX_ISSUE_URL_LENGTH)
    while low < high:
        middle = (low + high + 1) // 2
        candidate = _issue_url(title, body[:middle] + _TRUNCATION_NOTE)
        if len(candidate) <= _MAX_ISSUE_URL_LENGTH:
            low = middle
        else:
            high = middle - 1
    return _issue_url(title, body[:low] + _TRUNCATION_NOTE), True


def register(tools: Tools) -> None:
    """Register the feedback tool.

    Args:
        tools: Where it is registered.
    """

    @tools.tool(
        annotations=ToolAnnotations(
            read_only_hint=True,
            destructive_hint=False,
            idempotent_hint=True,
            open_world_hint=False,
        ),
        needs_server=False,
    )
    async def zenml_report_feedback(  # noqa: D417
        call: ZenMLCall,
        title: str,
        what_happened: str,
        proposed_fix: str,
        tool_name: str | None = None,
    ) -> dict[str, Any]:
        """Draft a GitHub issue about this MCP server for the user to review and submit.

        Use this when a tool in this server got in your way: an error message that
        did not explain the problem, a confusing or wrong schema or description, a
        filter or resource type you needed that is missing, or results that were
        wrong or hard to use. Do not use it for problems in the user's own
        pipelines or ZenML server; this reports problems with the MCP server.

        Nothing is sent. The tool returns a link that opens a pre-filled issue on
        github.com/zenml-io/zenml. Show the link to the user and tell them to
        read the text before they submit it, because the issue will be public.

        Write the report for a maintainer who has never seen this conversation.
        Leave out anything private: API keys, passwords, server URLs, and the names
        of the user's pipelines, stacks, models or projects. Describe them
        generically instead (for example "a pipeline with 40 steps").

        Args:
            title: A one-line summary of the problem, under 100 characters.
            what_happened: What you called, with which arguments, what you expected,
                and what you got instead. Quote the error message if there was one.
            proposed_fix: The change you suggest to the server, as specifically as
                you can (which tool, parameter or description to change, and how).
            tool_name: The tool the feedback is about, if it is about one tool.
        """  # noqa: DOC101, DOC103, DOC201, DOC501, DOC503
        title = " ".join(title.split())[:_MAX_FEEDBACK_TITLE_LENGTH]
        what_happened, proposed_fix = (
            what_happened.strip(),
            proposed_fix.strip(),
        )
        if not (title and what_happened and proposed_fix):
            raise ZenMLBadRequest(
                "title, what_happened and proposed_fix must not be empty."
            )
        body = _issue_body(what_happened, proposed_fix, tool_name)
        url, truncated = _prefilled_issue_url(title, body)
        note = (
            "Nothing has been sent. Show the user this link and ask them to "
            "read the issue before submitting it, because it will be public."
        )
        result: dict[str, Any] = {"issue_url": url, "truncated": truncated}
        if truncated:
            note += (
                " The report was too long to fit in a link, so the issue text "
                "is cut short. Give the user the full body below to paste in."
            )
            result["body"] = body
        return {**result, "note": note}
