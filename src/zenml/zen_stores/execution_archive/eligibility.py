#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
#  implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Workspace-policy eligibility for execution-history archiving."""

from datetime import datetime
from typing import Optional

from zenml.constants import (
    DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES,
)
from zenml.zen_stores.execution_archive.capture import ExecutionArchiveFamily


def execution_archive_blocker(
    family: ExecutionArchiveFamily, *, cutoff: datetime
) -> Optional[str]:
    """Return why an execution tree is not eligible under a policy.

    Args:
        family: Inspected execution-tree identity and safety evidence.
        cutoff: Latest completion and mutation time allowed by retention.

    Returns:
        A stable blocker category, or `None` when the tree is eligible.
    """
    if family.blockers:
        return family.blockers[0]
    if family.completed_at is None or family.completed_at > cutoff:
        return "execution tree completed within the retention period"
    if family.latest_mutation > cutoff:
        return "execution tree changed within the retention period"
    if (
        family.source_bytes
        > DEFAULT_ZENML_SERVER_EXECUTION_ARCHIVE_MAX_DECODED_BYTES
    ):
        return "execution tree exceeds the archive object size limit"
    return None
