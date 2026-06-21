"""Tests for request management timeout semantics."""

import asyncio
import time
from dataclasses import dataclass
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi.responses import JSONResponse

from zenml.zen_server import utils as server_utils
from zenml.zen_server.request_management import RequestManager

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    """Run async request-manager tests on asyncio."""
    return "asyncio"


@dataclass
class _ServerConfig:
    """Minimal request manager configuration for unit tests."""

    request_deduplication: bool = True
    request_cache_timeout: int = 300
    request_timeout: float = 0.001
    api_transaction_cleanup_interval: float = 1.0


class _RequestContext:
    """Minimal request context used by RequestManager.execute."""

    def __init__(
        self,
        *,
        method: str = "POST",
        transaction_id: UUID | None = None,
        is_cacheable: bool = False,
    ) -> None:
        self.request = SimpleNamespace(
            method=method,
            url="http://test/api/request",
        )
        self.transaction_id = transaction_id
        self.is_cacheable = is_cacheable
        self.process_time = 0.0


class _ZenStore:
    """Minimal transaction store used by deduplicated request tests."""

    def __init__(self) -> None:
        self.finalized_transaction_id: UUID | None = None
        self.finalized_result: str | None = None

    def get_or_create_api_transaction(
        self, api_transaction: object
    ) -> tuple[SimpleNamespace, bool]:
        """Return a newly claimed transaction."""
        _ = api_transaction
        return SimpleNamespace(completed=False), True

    def get_api_transaction_result(self, _api_transaction_id: UUID) -> None:
        """Return no cached result."""
        return None

    def finalize_api_transaction(
        self, api_transaction_id: UUID, api_transaction_update: Any
    ) -> None:
        """Record the transaction finalization."""
        self.finalized_transaction_id = api_transaction_id
        self.finalized_result = api_transaction_update.get_result()

    def delete_api_transaction(self, _api_transaction_id: UUID) -> None:
        """No-op delete for failed transaction paths."""


def _configure_request_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(server_utils, "_server_config", _ServerConfig())
    monkeypatch.setattr(server_utils, "get_system_metrics", lambda: {})


async def test_non_deduplicated_requests_do_not_timeout(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Non-deduplicated requests keep connection and work lifetime aligned."""
    _configure_request_manager(monkeypatch)
    manager = RequestManager()
    manager.current_request = _RequestContext(is_cacheable=False)

    def slow_operation() -> str:
        time.sleep(0.01)
        return "done"

    result = await manager.execute(slow_operation, deduplicate=None)

    assert result == "done"


async def test_deduplicated_requests_can_timeout_and_continue(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Deduplicated requests may return backpressure while work continues."""
    _configure_request_manager(monkeypatch)
    zen_store = _ZenStore()
    monkeypatch.setattr(server_utils, "_zen_store", zen_store)

    manager = RequestManager()
    transaction_id = uuid4()
    manager.current_request = _RequestContext(
        transaction_id=transaction_id,
        is_cacheable=True,
    )

    def slow_operation() -> dict[str, bool]:
        time.sleep(0.02)
        return {"ok": True}

    result = await manager.execute(slow_operation, deduplicate=None)

    assert isinstance(result, JSONResponse)
    assert result.status_code == 429

    for _ in range(100):
        if transaction_id not in manager.transactions:
            break
        await asyncio.sleep(0.01)

    assert transaction_id not in manager.transactions
    assert zen_store.finalized_transaction_id == transaction_id
    assert zen_store.finalized_result is not None
