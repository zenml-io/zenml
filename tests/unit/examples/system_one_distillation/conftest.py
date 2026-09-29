"""Lightweight fixtures for the self-contained classifier example tests."""

from collections.abc import Iterator
from types import SimpleNamespace

import pytest


@pytest.fixture(scope="session", autouse=True)
def auto_environment() -> Iterator[tuple[SimpleNamespace, SimpleNamespace]]:
    """Avoid provisioning the repository integration-test environment."""
    yield SimpleNamespace(), SimpleNamespace()


@pytest.fixture(scope="module", autouse=True)
def check_module_requirements() -> None:
    """The example unit tests declare and install their own dependencies."""
