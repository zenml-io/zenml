"""Lightweight fixtures for CI helper unit tests."""

from types import SimpleNamespace
from typing import Iterator, Tuple

import pytest


@pytest.fixture(scope="session", autouse=True)
def auto_environment() -> Iterator[Tuple[SimpleNamespace, SimpleNamespace]]:
    """Override the global ZenML test environment for pure helper tests."""
    yield SimpleNamespace(), SimpleNamespace()
