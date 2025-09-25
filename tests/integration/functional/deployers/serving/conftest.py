#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Test-specific fixtures for serving integration tests."""

from types import SimpleNamespace
from typing import Generator, Tuple

import pytest


@pytest.fixture(scope="session", autouse=True)
def auto_environment() -> Generator[
    Tuple[SimpleNamespace, SimpleNamespace], None, None
]:
    """Override the global auto_environment fixture with a lightweight stub.

    Yields:
        The active environment and a client connected with it.
    """
    yield SimpleNamespace(), SimpleNamespace()
