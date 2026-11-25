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
import asyncio
import functools

import pytest

from zenml.utils.async_utils import is_async_callable, run_coroutine_isolated


def _sync_fn() -> int:
    return 1


async def _async_fn() -> int:
    return 1


def test_is_async_callable_with_plain_function():
    """Tests that a plain function is not detected as async."""
    assert is_async_callable(_sync_fn) is False


def test_is_async_callable_with_coroutine_function():
    """Tests that a coroutine function is detected as async."""
    assert is_async_callable(_async_fn) is True


def test_is_async_callable_with_partial_of_plain_function():
    """Tests that a partial of a plain function is not detected as async."""
    assert is_async_callable(functools.partial(_sync_fn)) is False


def test_is_async_callable_with_partial_of_coroutine_function():
    """Tests that a partial of a coroutine function is detected as async."""
    assert is_async_callable(functools.partial(_async_fn)) is True


def test_is_async_callable_with_wrapped_plain_function():
    """Tests that a wrapper around a plain function is not detected as async."""

    @functools.wraps(_sync_fn)
    def wrapper():
        return _sync_fn()

    assert is_async_callable(wrapper) is False


def test_is_async_callable_with_wrapped_coroutine_function():
    """Tests that a wrapper around a coroutine function is detected as async."""

    @functools.wraps(_async_fn)
    def wrapper():
        return _async_fn()

    assert is_async_callable(wrapper) is True


def test_run_coroutine_isolated_returns_value():
    """Tests that the coroutine result is returned."""

    async def coro():
        return 42

    assert run_coroutine_isolated(coro()) == 42


def test_run_coroutine_isolated_propagates_exception():
    """Tests that an exception raised inside the coroutine propagates."""

    async def coro():
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        run_coroutine_isolated(coro())


def test_run_coroutine_isolated_returns_value_from_running_loop():
    """Tests that the result is returned when called from a running loop."""

    async def coro():
        return 42

    async def driver():
        return run_coroutine_isolated(coro())

    assert asyncio.run(driver()) == 42


def test_run_coroutine_isolated_propagates_exception_from_running_loop():
    """Tests that an exception propagates when called from a running loop."""

    async def coro():
        raise ValueError("boom")

    async def driver():
        return run_coroutine_isolated(coro())

    with pytest.raises(ValueError, match="boom"):
        asyncio.run(driver())
