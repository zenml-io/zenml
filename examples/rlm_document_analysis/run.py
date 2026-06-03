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
"""RLM Document Analysis — CLI entry point.

Reads the email data file client-side and uploads it to the artifact store
via save_artifact() before launching the pipeline. This ensures the data is
available to all steps regardless of orchestrator (local or Kubernetes).
"""

import argparse
import json
from pathlib import Path
from typing import Optional, Sequence

from pipelines.rlm_pipeline import BUNDLED_SAMPLE, rlm_analysis_pipeline

from zenml import save_artifact


def _resolve_source(source_path: str) -> Path:
    """Find the data file, trying the path as-is and relative to this script."""
    candidates = [Path(source_path), Path(__file__).parent / source_path]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"Data file not found at: {[str(c) for c in candidates]}. "
        f"Run setup_data.py to download the dataset, or use the bundled "
        f"sample at {BUNDLED_SAMPLE}."
    )


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
        default=BUNDLED_SAMPLE,
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

    # Read and upload data client-side so it's in the artifact store
    # before the pipeline runs. This is critical for remote orchestrators
    # (Kubernetes, etc.) where the pipeline function executes in a pod
    # that doesn't have access to local files.
    data_path = _resolve_source(args.source)
    with open(data_path, encoding="utf-8") as f:
        emails = json.load(f)

    artifact_version = save_artifact(
        data=emails,
        name="rlm_email_corpus",
        has_custom_name=True,
    )

    rlm_analysis_pipeline(
        emails_artifact_id=str(artifact_version.id),
        query=args.query,
        max_chunks=args.max_chunks,
        max_iterations=args.max_iterations,
    )


if __name__ == "__main__":
    main()
