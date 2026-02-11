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

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Annotated, Any, Dict, List, Tuple

from zenml import step

logger = logging.getLogger(__name__)


def _find_data_file(source_path: str) -> Path:
    """Resolve the data file path, trying multiple locations.

    Args:
        source_path: User-provided path to data file.

    Returns:
        Resolved Path object.

    Raises:
        FileNotFoundError: If no valid path is found.
    """
    candidates = [
        Path(source_path),
        Path(__file__).parent.parent / source_path,
        Path("/app") / source_path,
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Data file not found. Tried: {[str(c) for c in candidates]}. "
        f"Run setup_data.py to download the dataset, or use the bundled "
        f"sample at data/sample_emails.json."
    )


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
    source_path: str,
) -> Tuple[
    Annotated[List[Dict[str, Any]], "documents"],
    Annotated[Dict[str, Any], "doc_summary"],
]:
    """Load email documents from a JSON file and produce a corpus summary.

    The summary is used by the decomposition step to decide how to
    partition the corpus. The full document list is passed to each
    process_chunk step.

    Args:
        source_path: Path to the JSON data file.

    Returns:
        Tuple of (documents list, summary dict).
    """
    data_path = _find_data_file(source_path)
    logger.info("Loading documents from %s", data_path)

    with open(data_path) as f:
        emails = json.load(f)

    if not isinstance(emails, list):
        raise ValueError(
            f"Expected a JSON array of email objects, got {type(emails).__name__}"
        )

    logger.info(
        "Loaded %d emails (%d chars total)",
        len(emails),
        sum(len(e.get("body", "")) for e in emails),
    )

    summary = _build_summary(emails)
    return emails, summary
