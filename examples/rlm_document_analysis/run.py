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
"""RLM Document Analysis — CLI entry point."""

import argparse
from typing import Optional, Sequence

from pipelines.rlm_pipeline import rlm_analysis_pipeline


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Run the RLM document analysis pipeline.

    Args:
        argv: Command-line arguments. If None, uses sys.argv.
    """
    parser = argparse.ArgumentParser(
        description="Analyze an email corpus using the RLM pattern"
    )
    parser.add_argument(
        "--query",
        "-q",
        default="What financial irregularities or concerns are discussed?",
        help="Research question to investigate",
    )
    parser.add_argument(
        "--source",
        "-s",
        default="data/sample_emails.json",
        help="Path to email data JSON file",
    )
    parser.add_argument(
        "--max-chunks",
        "-c",
        type=int,
        default=4,
        help="Max parallel chunks (1-10, controls DAG width)",
    )
    parser.add_argument(
        "--max-iterations",
        "-i",
        type=int,
        default=6,
        help="Max LLM calls per chunk (2-12, controls analysis depth)",
    )
    args = parser.parse_args(argv)

    rlm_analysis_pipeline(
        source_path=args.source,
        query=args.query,
        max_chunks=args.max_chunks,
        max_iterations=args.max_iterations,
    )


if __name__ == "__main__":
    main()
