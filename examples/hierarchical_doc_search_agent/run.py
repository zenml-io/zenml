#!/usr/bin/env python3
"""Hierarchical Document Search Agent."""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from pipelines import hierarchical_search_pipeline

parser = argparse.ArgumentParser()
parser.add_argument("--query", "-q", required=True, help="Search query")
parser.add_argument("--max-agents", "-a", type=int, default=3, help="Max parallel agents")
parser.add_argument("--max-depth", "-d", type=int, default=2, help="Max traversal depth")
args = parser.parse_args()

hierarchical_search_pipeline(
    query=args.query,
    max_agents=args.max_agents,
    max_depth=args.max_depth,
)
