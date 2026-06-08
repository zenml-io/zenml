#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
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
"""Unit tests for async utils."""

import asyncio
import contextvars
import functools
import threading
from typing import Optional

import pytest

from zenml.utils.async_utils import (
    is_async_callable,
    run_coroutine_blocking,
)


async def _async_fn() -> int:
    return 1


def _sync_fn() -> int:
    return 1


def test_is_async_callable_true_for_async_def() -> None:
    """An `async def` function is detected as async."""
    assert is_async_callable(_async_fn) is True


def test_is_async_callable_false_for_sync_def_and_lambda() -> None:
    """A plain function and a lambda are not detected as async."""
    assert is_async_callable(_sync_fn) is False
    assert is_async_callable(lambda: 1) is False


def test_is_async_callable_true_for_partial_wrapping_async() -> None:
    """A partial wrapping an `async def` is detected as async."""
    partial = functools.partial(_async_fn)
    assert is_async_callable(partial) is True


def test_is_async_callable_false_for_partial_wrapping_sync() -> None:
    """A partial wrapping a sync function is not detected as async."""
    partial = functools.partial(_sync_fn)
    assert is_async_callable(partial) is False


def test_run_coroutine_blocking_no_loop_returns_value() -> None:
    """Running without a loop returns the coroutine result."""

    async def coro() -> int:
        return 42

    assert run_coroutine_blocking(coro()) == 42


def test_run_coroutine_blocking_no_loop_propagates_exception() -> None:
    """Running without a loop propagates an exception from the coroutine."""

    async def coro() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        run_coroutine_blocking(coro())


def test_run_coroutine_blocking_dispatches_to_loop_with_context() -> None:
    """Dispatching onto a running loop preserves context and switches thread."""
    test_var: contextvars.ContextVar[str] = contextvars.ContextVar(
        "_test_var", default="default"
    )

    loop = asyncio.new_event_loop()
    loop_thread_id: Optional[int] = None
    ready = threading.Event()

    def _run_loop() -> None:
        nonlocal loop_thread_id
        loop_thread_id = threading.get_ident()
        asyncio.set_event_loop(loop)
        loop.call_soon(ready.set)
        loop.run_forever()

    thread = threading.Thread(target=_run_loop)
    thread.start()
    try:
        ready.wait()
        assert loop.is_running()

        main_thread_id = threading.get_ident()
        test_var.set("propagated")

        async def read_var() -> tuple[str, int]:
            return test_var.get(), threading.get_ident()

        value, executed_thread_id = run_coroutine_blocking(
            read_var(), loop=loop
        )

        assert value == "propagated"
        assert executed_thread_id == loop_thread_id
        assert executed_thread_id != main_thread_id
    finally:
        loop.call_soon_threadsafe(loop.stop)
        thread.join()
        loop.close()


def test_run_coroutine_blocking_raises_on_same_thread_loop() -> None:
    """Dispatching onto the loop running on the current thread raises."""

    async def inner() -> int:
        return 1

    async def main() -> None:
        loop = asyncio.get_running_loop()
        coro = inner()
        try:
            with pytest.raises(RuntimeError):
                run_coroutine_blocking(coro, loop=loop)
        finally:
            coro.close()

    asyncio.run(main())
