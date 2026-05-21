"""Lightweight fixtures for Kubernetes integration unit tests."""

from types import SimpleNamespace
from typing import Iterator, Tuple

import pytest


@pytest.fixture(scope="session")
def auto_environment() -> Iterator[Tuple[SimpleNamespace, SimpleNamespace]]:
    """Override the global environment fixture for pure Kubernetes unit tests."""
    yield SimpleNamespace(), SimpleNamespace()
