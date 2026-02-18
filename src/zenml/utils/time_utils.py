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

import random
from datetime import datetime, timedelta, timezone
from typing import Iterator, Literal, Optional, Union


def utc_now(tz_aware: Union[bool, datetime] = False) -> datetime:
    """Get the current time in the UTC timezone.

    Args:
        tz_aware: Use this flag to control whether the returned datetime is
            timezone-aware or timezone-naive. If a datetime is provided, the
            returned datetime will be timezone-aware if and only if the input
            datetime is also timezone-aware.

    Returns:
        The current UTC time. If tz_aware is a datetime, the returned datetime
        will be timezone-aware only if the input datetime is also timezone-aware.
        If tz_aware is a boolean, the returned datetime will be timezone-aware
        if True, and timezone-naive if False.
    """
    now = datetime.now(timezone.utc)
    if (
        isinstance(tz_aware, bool)
        and tz_aware is False
        or isinstance(tz_aware, datetime)
        and tz_aware.tzinfo is None
    ):
        return now.replace(tzinfo=None)

    return now


def utc_now_tz_aware() -> datetime:
    """Get the current timezone-aware UTC time.

    Returns:
        The current UTC time.
    """
    return utc_now(tz_aware=True)


def to_local_tz(dt: datetime) -> datetime:
    """Convert a datetime to the local timezone.

    If the input datetime is timezone-naive, it will be assumed to be in the UTC
    timezone.

    Args:
        dt: datetime to convert.

    Returns:
        Datetime in the local timezone.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone()


def to_utc_timezone(dt: datetime) -> datetime:
    """Convert a datetime to the UTC timezone.

    If the input datetime is timezone-naive, it will be assumed to be in the UTC
    timezone.

    Args:
        dt: datetime to convert.

    Returns:
        Datetime in the UTC timezone.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
    now = utc_now(tz_aware=expires_at)
    if skew_tolerance:
        expires_at -= timedelta(seconds=skew_tolerance)
    if expires_at < now:
        return expired_str
    return seconds_to_human_readable(int((expires_at - now).total_seconds()))


def exponential_backoff_delays(
    attempts: Optional[int] = None,
    initial_delay: float = 1.0,
    max_delay: float = 30.0,
    factor: float = 2.0,
    jitter: Literal["none", "full", "equal"] = "full",
) -> Iterator[float]:
    """Yields exponential backoff delays for retry loops.

    Implements jitter algorithms described in:
    https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

    Example:
        for delay in exponential_backoff_delays(attempts=5):
            try:
                do_work()
                break
            except Exception:
                time.sleep(delay)

    Args:
        attempts: Number of delays to generate. If not provided, yields delays
            forever.
        initial_delay: Initial delay in seconds.
        max_delay: Maximum delay in seconds.
        factor: Multiplication factor applied per attempt.
        jitter: Jitter mode. If set to `"full"`, samples from
            `[0, computed_delay]`. If set to `"equal"`, samples from
            `[computed_delay / 2, computed_delay]`. If set to `"none"`, no
            jitter is applied.

    Yields:
        Delay values in seconds.
    """
    if attempts is not None and attempts < 0:
        raise ValueError("`attempts` must be greater than or equal to 0.")
    if initial_delay <= 0:
        raise ValueError("`initial_delay` must be greater than 0.")
    if max_delay <= 0:
        raise ValueError("`max_delay` must be greater than 0.")
    if factor < 1:
        raise ValueError("`factor` must be greater than or equal to 1.")

    if jitter not in {"none", "full", "equal"}:
        raise ValueError("`jitter` must be one of 'none', 'full', or 'equal'.")

    attempt = 0
    while attempts is None or attempt < attempts:
        delay = min(initial_delay * (factor**attempt), max_delay)
        if jitter == "full":
            delay = random.uniform(0, delay)
        elif jitter == "equal":
            half_delay = delay / 2
            delay = half_delay + random.uniform(0, half_delay)
        yield delay
        attempt += 1
