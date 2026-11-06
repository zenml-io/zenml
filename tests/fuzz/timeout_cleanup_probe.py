#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""Probe that lets runner tests verify SIGTERM unwinds pytest cleanup."""

import os
import time
from pathlib import Path


def test_timeout_runs_cleanup() -> None:
    """Record cleanup after the runner interrupts this deliberately slow test."""
    marker = Path(os.environ["ZENML_FUZZ_TIMEOUT_CLEANUP_MARKER"])
    try:
        time.sleep(60)
    finally:
        marker.write_text("cleaned\n")
