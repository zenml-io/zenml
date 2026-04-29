"""Unit tests for functional integration test configuration."""

from __future__ import annotations

from collections.abc import Generator
from types import SimpleNamespace

import pytest

from tests.integration.functional import conftest as functional_conftest


class _FakeRequest:
    """Minimal request object for driving the autouse fixture directly."""

    def __init__(
        self,
        *,
        marker: object | None = None,
        fixturenames: list[str] | None = None,
    ) -> None:
        self.fixturenames = fixturenames or []
        self.fixture_requests: list[str] = []
        self.node = SimpleNamespace(
            get_closest_marker=lambda marker_name: (
                marker
                if marker_name
                == functional_conftest.NO_ISOLATED_PROJECT_MARKER
                else None
            )
        )

    def getfixturevalue(self, fixture_name: str) -> object:
        """Record requested fixtures without invoking pytest internals."""
        self.fixture_requests.append(fixture_name)
        return object()


def _run_auto_isolated_project_fixture(request: _FakeRequest) -> None:
    fixture = functional_conftest.auto_isolated_project.__wrapped__
    generator: Generator[None, None, None] = fixture(request)
    next(generator)
    with pytest.raises(StopIteration):
        next(generator)


def test_auto_isolated_project_uses_isolated_project_when_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The Modal env flag activates per-test project isolation."""
    monkeypatch.setenv(functional_conftest.AUTO_ISOLATE_ENV_VAR, "1")
    request = _FakeRequest()

    _run_auto_isolated_project_fixture(request)

    assert request.fixture_requests == ["isolated_project"]


def test_auto_isolated_project_skips_when_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without the Modal env flag, local functional tests keep current behavior."""
    monkeypatch.delenv(functional_conftest.AUTO_ISOLATE_ENV_VAR, raising=False)
    request = _FakeRequest()

    _run_auto_isolated_project_fixture(request)

    assert request.fixture_requests == []


def test_auto_isolated_project_honors_marker_opt_out(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The marker allows tests that need shared state to opt out."""
    monkeypatch.setenv(functional_conftest.AUTO_ISOLATE_ENV_VAR, "true")
    request = _FakeRequest(marker=object())

    _run_auto_isolated_project_fixture(request)

    assert request.fixture_requests == []


def test_auto_isolated_project_skips_explicit_project_fixtures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Tests that already request project isolation are not double-isolated."""
    monkeypatch.setenv(functional_conftest.AUTO_ISOLATE_ENV_VAR, "true")
    request = _FakeRequest(fixturenames=["clean_project"])

    _run_auto_isolated_project_fixture(request)

    assert request.fixture_requests == []
