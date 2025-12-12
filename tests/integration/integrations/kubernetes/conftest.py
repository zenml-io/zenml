"""Lightweight fixtures for Kubernetes integration-style unit tests."""

from types import SimpleNamespace
from typing import Iterator, Tuple

import pytest

pytest_plugins = ["tests.unit.deployers.server.conftest"]


@pytest.fixture(scope="session", autouse=True)
def auto_environment() -> Iterator[Tuple[SimpleNamespace, SimpleNamespace]]:
    """Override heavy env fixture to avoid provisioning in these tests."""
    yield SimpleNamespace(), SimpleNamespace()
