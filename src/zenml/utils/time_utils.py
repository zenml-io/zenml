#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Time utils."""

from datetime import datetime, timedelta, timezone
from typing import Optional


def utc_now(tz: bool = False) -> datetime:
    """Get the current UTC time.

    Args:
        tz: Whether to return a timezone-aware datetime.

    Returns:
        The current UTC time.
    """
    if tz:
        return datetime.now(timezone.utc)
    else:
        return datetime.now(timezone.utc).replace(tzinfo=None)


def utc_now_tz() -> datetime:
    """Get the current timezone-aware UTC time.

    Returns:
        The current UTC time.
    """
    return utc_now(tz=True)


def seconds_to_human_readable(time_seconds: int) -> str:
    """Converts seconds to human-readable format.

    Args:
        time_seconds: Seconds to convert.

    Returns:
        Human readable string.
    """
    seconds = time_seconds % 60
    minutes = (time_seconds // 60) % 60
    hours = (time_seconds // 3600) % 24
    days = time_seconds // 86400
    tokens = []
    if days:
        tokens.append(f"{days}d")
    if hours:
        tokens.append(f"{hours}h")
    if minutes:
        tokens.append(f"{minutes}m")
    if seconds:
        tokens.append(f"{seconds}s")

    return "".join(tokens)


def expires_in(
    expires_at: datetime,
    expired_str: str,
    skew_tolerance: Optional[int] = None,
) -> str:
    """Returns a human-readable string of the time until an expiration.

    Args:
        expires_at: Expiration time.
        expired_str: String to return if the expiration is in the past.
        skew_tolerance: Seconds of skew tolerance to subtract from the
            expiration time. If the expiration is within the skew tolerance,
            the function will return the expired string.

    Returns:
        Human readable string.
    """
    now = utc_now_tz()
    expires_at = expires_at.replace(tzinfo=timezone.utc)
    if skew_tolerance:
        expires_at -= timedelta(seconds=skew_tolerance)
    if expires_at < now:
        return expired_str
    return seconds_to_human_readable(int((expires_at - now).total_seconds()))
