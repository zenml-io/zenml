#!/usr/bin/env python3
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
"""Download the full Enron email dataset from Hugging Face.

Usage:
    pip install datasets
    python setup_data.py                  # First 1000 emails
    python setup_data.py --limit 5000     # First 5000 emails
    python setup_data.py --limit 0        # All ~517K emails (large!)
"""

import argparse
import email
import email.utils
import json
import sys
from pathlib import Path


def _normalize_date(raw_date: str) -> str:
    """Convert an RFC 2822 date header to ISO 8601 format.

    Args:
        raw_date: Raw date string from email header
            (e.g. "Mon, 14 Jun 1999 09:22:00 -0700").

    Returns:
        ISO 8601 date string, or the original string if parsing fails.
    """
    if not raw_date:
        return ""
    try:
        dt = email.utils.parsedate_to_datetime(raw_date)
        return dt.isoformat()
    except (ValueError, TypeError):
        return raw_date


def parse_raw_email(raw: str) -> dict:
    """Parse a raw RFC 2822 email string into a structured dict.

    Args:
        raw: Raw email text with headers and body.

    Returns:
        Dict with from, to, cc, date, subject, body fields.
    """
    msg = email.message_from_string(raw)
    return {
        "date": _normalize_date(msg.get("Date", "")),
        "from": msg.get("From", ""),
        "to": msg.get("To", ""),
        "cc": msg.get("Cc", ""),
        "subject": msg.get("Subject", ""),
        "body": msg.get_payload() or "",
        "x_from": msg.get("X-From", ""),
        "x_to": msg.get("X-To", ""),
        "x_folder": msg.get("X-Folder", ""),
        "x_origin": msg.get("X-Origin", ""),
    }


def main() -> None:
    """Download and convert Enron emails to JSON."""
    parser = argparse.ArgumentParser(
        description="Download Enron email dataset from Hugging Face"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1000,
        help="Max emails to download (0 for all, default 1000)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/emails.json",
        help="Output file path",
    )
    args = parser.parse_args()

    try:
        from datasets import load_dataset
    except ImportError:
        print("Error: 'datasets' package required. Install with:")
        print("  pip install datasets")
        sys.exit(1)

    print(f"Loading Enron email dataset from Hugging Face...")
    ds = load_dataset("corbt/enron-emails", streaming=True)

    emails = []
    count = 0
    limit = args.limit if args.limit > 0 else float("inf")

    for example in ds["train"]:
        if count >= limit:
            break

        # The dataset may have a 'message' column with raw email text,
        # or pre-parsed columns — handle both formats
        if "message" in example:
            parsed = parse_raw_email(example["message"])
        else:
            raw_date = example.get("date", example.get("Date", ""))
            parsed = {
                "date": _normalize_date(raw_date),
                "from": example.get("from", example.get("From", "")),
                "to": example.get("to", example.get("To", "")),
                "cc": example.get("cc", example.get("Cc", "")),
                "subject": example.get("subject", example.get("Subject", "")),
                "body": example.get("body", example.get("Body", "")),
            }

        parsed["id"] = f"enron_{count:06d}"
        emails.append(parsed)
        count += 1

        if count % 500 == 0:
            print(f"  Processed {count} emails...")

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w") as f:
        json.dump(emails, f, indent=2, default=str)

    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"Saved {len(emails)} emails to {output_path} ({size_mb:.1f} MB)")
    print(f"Run the pipeline with: python run.py --source {output_path}")


if __name__ == "__main__":
    main()
