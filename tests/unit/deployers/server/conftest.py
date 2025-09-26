"""Test-specific fixtures for deployment unit tests."""

from types import SimpleNamespace
from typing import Iterator, Tuple

import pytest


@pytest.fixture(scope="session", autouse=True)
def auto_environment() -> Iterator[Tuple[SimpleNamespace, SimpleNamespace]]:
    """Override the global auto_environment fixture with a lightweight stub.

    Yields:
        The active environment and a connected client stub.
    """
    yield SimpleNamespace(), SimpleNamespace()
