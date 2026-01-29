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
"""Hierarchical Document Search Agent."""

import argparse
from typing import Optional, Sequence

from pipelines.hierarchical_search_pipeline import hierarchical_search_pipeline


def main(argv: Optional[Sequence[str]] = None) -> None:
    """Run the hierarchical search pipeline.

    Args:
        argv: Command-line arguments. If None, uses sys.argv.
    """
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument(
        "--max-agents", "-a", type=int, default=3, help="Max parallel agents"
    )
    parser.add_argument(
        "--max-depth", "-d", type=int, default=2, help="Max traversal depth"
    )
    args = parser.parse_args(argv)

    hierarchical_search_pipeline(
        query=args.query,
        max_agents=args.max_agents,
        max_depth=args.max_depth,
    )


if __name__ == "__main__":
    main()
