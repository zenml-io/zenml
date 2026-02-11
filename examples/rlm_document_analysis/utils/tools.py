# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2026. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Programmatic search tools for RLM-style document analysis.

These functions operate on lists of email dicts and are called
by the process_chunk step based on LLM-generated search plans.
They replace the arbitrary code execution of a full REPL with
safe, typed, observable operations.
"""

import re
from datetime import datetime
from typing import Any, Dict, List


def grep_emails(
    emails: List[Dict[str, Any]], pattern: str
) -> List[Dict[str, Any]]:
    """Search for a regex pattern in email body and subject.

    Args:
        emails: List of email dicts.
        pattern: Regex pattern to search for.

    Returns:
        Emails where body or subject matches the pattern.
    """
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error:
        # Treat invalid regex as a literal string search
        compiled = re.compile(re.escape(pattern), re.IGNORECASE)
    return [
        e
        for e in emails
        if compiled.search(e.get("body", ""))
        or compiled.search(e.get("subject", ""))
    ]


def filter_by_sender(
    emails: List[Dict[str, Any]], sender: str
) -> List[Dict[str, Any]]:
    """Filter emails by sender (case-insensitive substring match).

    Args:
        emails: List of email dicts.
        sender: Sender name or email substring to match.

    Returns:
        Emails whose 'from' field contains the sender string.
    """
    sender_lower = sender.lower()
    return [e for e in emails if sender_lower in e.get("from", "").lower()]


def filter_by_recipient(
    emails: List[Dict[str, Any]], recipient: str
) -> List[Dict[str, Any]]:
    """Filter emails where recipient appears in To or Cc fields.

    Args:
        emails: List of email dicts.
        recipient: Recipient name or email substring to match.

    Returns:
        Emails where the recipient appears in to or cc.
    """
    r_lower = recipient.lower()
    results = []
    for e in emails:
        to_field = e.get("to", "")
        cc_field = e.get("cc", "")
        to_str = to_field if isinstance(to_field, str) else ",".join(to_field)
        cc_str = cc_field if isinstance(cc_field, str) else ",".join(cc_field)
        if r_lower in to_str.lower() or r_lower in cc_str.lower():
            results.append(e)
    return results


def filter_by_date(
    emails: List[Dict[str, Any]], start: str, end: str
) -> List[Dict[str, Any]]:
    """Filter emails by ISO-format date range (inclusive).

    Args:
        emails: List of email dicts.
        start: Start date in ISO format (e.g. '2001-01-01').
        end: End date in ISO format (e.g. '2001-12-31').

    Returns:
        Emails whose date falls within [start, end].
    """
    try:
        start_dt = datetime.fromisoformat(start)
        end_dt = datetime.fromisoformat(end)
    except ValueError:
        return emails

    results = []
    for e in emails:
        try:
            email_dt = datetime.fromisoformat(e.get("date", ""))
            if start_dt <= email_dt <= end_dt:
                results.append(e)
        except (ValueError, TypeError):
            continue
    return results


def count_matches(emails: List[Dict[str, Any]], pattern: str) -> int:
    """Count total regex matches across all email bodies.

    Args:
        emails: List of email dicts.
        pattern: Regex pattern to count.

    Returns:
        Total number of matches across all emails.
    """
    try:
        compiled = re.compile(pattern, re.IGNORECASE)
    except re.error:
        compiled = re.compile(re.escape(pattern), re.IGNORECASE)
    return sum(len(compiled.findall(e.get("body", ""))) for e in emails)


def preview_chunk(emails: List[Dict[str, Any]], n: int = 5) -> str:
    """Create a text summary of a chunk of emails.

    Args:
        emails: List of email dicts.
        n: Number of emails to preview.

    Returns:
        Human-readable summary string.
    """
    if not emails:
        return "Empty chunk (0 emails)."

    senders = set(e.get("from", "unknown") for e in emails)
    dates = sorted(e.get("date", "") for e in emails if e.get("date"))

    lines = [
        f"Chunk contains {len(emails)} emails",
        f"Date range: {dates[0] if dates else 'N/A'} to "
        f"{dates[-1] if dates else 'N/A'}",
        f"Unique senders: {len(senders)}",
        f"Top senders: {', '.join(list(senders)[:8])}",
        "",
        f"Sample of first {min(n, len(emails))} emails:",
    ]

    for e in emails[:n]:
        lines.append(
            f"  [{e.get('date', 'N/A')}] "
            f"{e.get('from', '?')} -> {e.get('to', '?')}"
        )
        lines.append(f"  Subject: {e.get('subject', '(no subject)')}")
        body = e.get("body", "")
        lines.append(f"  Body: {body[:150]}...")
        lines.append("")

    return "\n".join(lines)


def format_email(email: Dict[str, Any], max_body: int = 500) -> str:
    """Format a single email for display to the LLM.

    Args:
        email: Email dict.
        max_body: Max characters of body to include.

    Returns:
        Formatted email string.
    """
    to_field = email.get("to", "")
    if isinstance(to_field, list):
        to_field = ", ".join(to_field)

    body = email.get("body", "")
    if len(body) > max_body:
        body = body[:max_body] + "..."

    return (
        f"From: {email.get('from', 'N/A')}\n"
        f"To: {to_field}\n"
        f"Date: {email.get('date', 'N/A')}\n"
        f"Subject: {email.get('subject', 'N/A')}\n"
        f"Body: {body}"
    )


TOOL_DESCRIPTIONS = {
    "grep": "grep_emails(pattern) - Search email bodies/subjects by regex",
    "sender": "filter_by_sender(sender) - Filter by sender name/email",
    "recipient": "filter_by_recipient(recipient) - Filter by recipient",
    "date": "filter_by_date(start, end) - Filter by ISO date range",
    "count": "count_matches(pattern) - Count regex matches across emails",
}
