"""Tests for IntegrationRegistry.activate_integrations() best-effort behavior."""

import logging
from typing import List, Type

from zenml.integrations.registry import IntegrationRegistry
from zenml.stack.flavor import Flavor


class _FailingIntegration:
    """Mock integration whose activate() raises OSError."""

    NAME = "failing"
    REQUIREMENTS: List[str] = []

    @classmethod
    def check_installation(cls) -> bool:
        return True

    @classmethod
    def activate(cls) -> None:
        raise OSError("DLL load failed: fake library not found")

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        return []


class _SucceedingIntegration:
    """Mock integration that tracks whether activate() was called."""

    NAME = "succeeding"
    REQUIREMENTS: List[str] = []
    activated = False

    @classmethod
    def check_installation(cls) -> bool:
        return True

    @classmethod
    def activate(cls) -> None:
        cls.activated = True

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        return []


class _ImportErrorIntegration:
    """Mock integration whose activate() raises ImportError."""

    NAME = "import_failing"
    REQUIREMENTS: List[str] = []

    @classmethod
    def check_installation(cls) -> bool:
        return True

    @classmethod
    def activate(cls) -> None:
        raise ImportError("No module named 'nonexistent_lib'")

    @classmethod
    def flavors(cls) -> List[Type[Flavor]]:
        return []


def test_activate_integrations_continues_after_oserror(caplog):
    """A single integration raising OSError must not prevent others from activating."""
    _SucceedingIntegration.activated = False
    registry = IntegrationRegistry()
    registry._initialized = True
    registry._integrations = {
        _FailingIntegration.NAME: _FailingIntegration,
        _SucceedingIntegration.NAME: _SucceedingIntegration,
    }

    with caplog.at_level(logging.ERROR):
        registry.activate_integrations()

    assert _SucceedingIntegration.activated is True
    assert any(
        "Failed to activate integration `failing`" in record.message
        and record.levelno == logging.ERROR
        for record in caplog.records
    )


def test_activate_integrations_continues_after_import_error(caplog):
    """A single integration raising ImportError must not prevent others from activating."""
    _SucceedingIntegration.activated = False
    registry = IntegrationRegistry()
    registry._initialized = True
    registry._integrations = {
        _ImportErrorIntegration.NAME: _ImportErrorIntegration,
        _SucceedingIntegration.NAME: _SucceedingIntegration,
    }

    with caplog.at_level(logging.ERROR):
        registry.activate_integrations()

    assert _SucceedingIntegration.activated is True
    assert any(
        "Failed to activate integration `import_failing`" in record.message
        and record.levelno == logging.ERROR
        for record in caplog.records
    )


def test_activate_integrations_logs_continuation_message(caplog):
    """The error log must mention that activation-time registration was skipped."""
    registry = IntegrationRegistry()
    registry._initialized = True
    registry._integrations = {
        _FailingIntegration.NAME: _FailingIntegration,
    }

    with caplog.at_level(logging.ERROR):
        registry.activate_integrations()

    assert any(
        "Skipping activation-time registration" in record.message
        for record in caplog.records
    )
