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
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Pure eligibility rules of execution archiving."""

from datetime import datetime, timedelta
from typing import List

from pydantic import BaseModel, ConfigDict

from zenml.utils.time_utils import to_utc_timezone
from zenml.zen_stores.execution_archive.capture import ExecutionArchiveFamily


def to_utc_naive(value: datetime) -> datetime:
    """Normalize a timestamp for comparison with SQL DATETIME values.

    Args:
        value: A naive or timezone-aware timestamp.

    Returns:
        The same instant as a naive UTC timestamp.
    """
    return to_utc_timezone(value).replace(tzinfo=None)


class ExecutionArchiveEligibility(BaseModel):
    """Whether a family may be archived, and why not."""

    eligible_at: datetime
    blockers: List[str]

    model_config = ConfigDict(frozen=True)

    @property
    def eligible(self) -> bool:
        """Whether every gate passed.

        Returns:
            Whether the family may be archived now.
        """
        return not self.blockers


def evaluate_eligibility(
    family: ExecutionArchiveFamily,
    *,
    now: datetime,
    older_than: timedelta,
    max_stored_bytes: int,
) -> ExecutionArchiveEligibility:
    """Evaluate every archive gate for one family.

    Args:
        family: The family, as inspected in SQL.
        now: The current time.
        older_than: How long a family must have been unchanged.
        max_stored_bytes: The largest payload that may be archived.

    Returns:
        When the family becomes eligible and what currently blocks it.
    """
    now = to_utc_naive(now)
    eligible_at = to_utc_naive(family.latest_mutation) + older_than
    blockers = []
    if not family.completed:
        blockers.append("the execution family is not fully completed")
    if family.operational_snapshot_ids:
        blockers.append("a snapshot is named or operationally referenced")
    blockers.extend(family.active_blockers)
    if family.stored_bytes > max_stored_bytes:
        blockers.append(
            f"the payload ({family.stored_bytes} stored bytes) is too large "
            "to archive"
        )
    if eligible_at > now:
        blockers.append("the family changed more recently than the cutoff")
    return ExecutionArchiveEligibility(
        eligible_at=eligible_at, blockers=blockers
    )
