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
"""Document loading step for RLM analysis pipeline."""

import logging
from collections import Counter
from typing import Annotated, Any, Dict, List, Tuple

from zenml import step

logger = logging.getLogger(__name__)


def _build_summary(emails: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build a summary of the email corpus for the decomposition step.

    Args:
        emails: List of email dicts.

    Returns:
        Summary dict with stats and previews.
    """
    senders: Counter[str] = Counter()
    dates: List[str] = []
    subjects: List[str] = []
    total_chars = 0

    for e in emails:
        senders[e.get("from", "unknown")] += 1
        if e.get("date"):
            dates.append(e["date"])
        if e.get("subject"):
            subjects.append(e["subject"])
        total_chars += len(e.get("body", ""))

    sorted_dates = sorted(dates) if dates else []
    top_senders = senders.most_common(15)

    return {
        "total_emails": len(emails),
        "total_chars": total_chars,
        "date_range": {
            "earliest": sorted_dates[0] if sorted_dates else None,
            "latest": sorted_dates[-1] if sorted_dates else None,
        },
        "unique_senders": len(senders),
        "top_senders": [
            {"email": addr, "count": count} for addr, count in top_senders
        ],
        "sample_subjects": subjects[:20],
    }


@step
def load_documents(
    emails: List[Dict[str, Any]],
) -> Tuple[
    Annotated[List[Dict[str, Any]], "documents"],
    Annotated[Dict[str, Any], "doc_summary"],
]:
    """Validate email data and produce a corpus summary.

    The email data is loaded client-side (in the pipeline function) and
    passed here via ExternalArtifact so it works on both local and remote
    orchestrators. This step validates the data and builds a summary for
    the decomposition step.

    Args:
        emails: List of email dicts, each with from/to/date/subject/body.

    Returns:
        Tuple of (documents list, summary dict).
    """
    if not isinstance(emails, list):
        raise ValueError(
            f"Expected a list of email dicts, got {type(emails).__name__}"
        )

    logger.info(
        "Loaded %d emails (%d chars total)",
        len(emails),
        sum(len(e.get("body", "")) for e in emails),
    )

    summary = _build_summary(emails)
    return emails, summary
