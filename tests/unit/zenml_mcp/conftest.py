#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Every test starts with none of the package's process-wide caches.

The tools cache server facts per server URL and per caller, and remember
which servers lack the log entries route. The fake servers of these tests
share URLs, so a test must not read what another test left behind.
"""

import pytest

pytest.importorskip("mcp")

from zenml_mcp import common, steps  # noqa: E402
from zenml_mcp.cache import SingleFlightCache  # noqa: E402


@pytest.fixture(autouse=True)
def fresh_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """Give each test empty caches.

    Args:
        monkeypatch: Restores the caches after the test.
    """
    for cache in ("_server_info", "_default_project", "_project_names"):
        monkeypatch.setattr(common, cache, SingleFlightCache())
    monkeypatch.setattr(steps, "_servers_without_log_entries", {})
