"""Tests for SQL secret re-encryption command contracts."""

from collections.abc import Generator
from importlib import import_module
from types import SimpleNamespace
from typing import Any

import pytest
from click.testing import CliRunner

from zenml.cli.secret import reencrypt_sql_secrets
from zenml.constants import SECRETS_OPERATIONS, SECRETS_REENCRYPT_SQL
from zenml.zen_stores.rest_zen_store import RestZenStore

secret_cli_module = import_module("zenml.cli.secret")


@pytest.fixture(scope="module", autouse=True)
def auto_environment() -> Generator[
    tuple[SimpleNamespace, SimpleNamespace], None, None
]:
    """Use a lightweight test environment for re-encryption contract tests."""
    yield SimpleNamespace(), SimpleNamespace()


def test_rest_store_reencrypt_sql_secrets_calls_operation_endpoint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """REST store sends re-encryption requests to the secret operation route."""
    store = RestZenStore.model_construct()
    captured: dict[str, Any] = {}

    def fake_put(
        self: RestZenStore,
        path: str,
        *,
        params: dict[str, Any],
    ) -> dict[str, int]:
        captured["path"] = path
        captured["params"] = params
        return {
            "scanned": 4,
            "reencrypted": 2,
            "skipped": 1,
            "failed": 1,
        }

    monkeypatch.setattr(RestZenStore, "put", fake_put)

    stats = store.reencrypt_sql_secrets(limit=4, ignore_errors=True)

    assert captured == {
        "path": f"{SECRETS_OPERATIONS}{SECRETS_REENCRYPT_SQL}",
        "params": {"ignore_errors": True, "limit": 4},
    }
    assert stats == {
        "scanned": 4,
        "reencrypted": 2,
        "skipped": 1,
        "failed": 1,
    }


def test_cli_reencrypt_sql_secrets_prints_non_secret_counters(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """CLI command reports only migration counters."""

    class FakeClient:
        def reencrypt_sql_secrets(
            self,
            *,
            limit: int | None,
            ignore_errors: bool,
        ) -> dict[str, int]:
            assert limit == 5
            assert ignore_errors is True
            return {
                "scanned": 5,
                "reencrypted": 3,
                "skipped": 2,
                "failed": 0,
            }

    monkeypatch.setattr(secret_cli_module, "Client", FakeClient)

    result = CliRunner().invoke(
        reencrypt_sql_secrets,
        ["--limit", "5", "--ignore-errors"],
    )

    assert result.exit_code == 0
    assert "scanned=5" in result.output
    assert "reencrypted=3" in result.output
    assert "skipped=2" in result.output
    assert "failed=0" in result.output
