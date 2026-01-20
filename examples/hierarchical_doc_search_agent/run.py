#!/usr/bin/env python3
# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
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
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from pipelines import hierarchical_search_pipeline

parser = argparse.ArgumentParser()
parser.add_argument("--query", "-q", required=True, help="Search query")
parser.add_argument(
    "--max-agents", "-a", type=int, default=3, help="Max parallel agents"
)
parser.add_argument(
    "--max-depth", "-d", type=int, default=2, help="Max traversal depth"
)
args = parser.parse_args()

hierarchical_search_pipeline(
    query=args.query,
    max_agents=args.max_agents,
    max_depth=args.max_depth,
)
