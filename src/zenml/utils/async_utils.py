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
"""Helpers for running async user code from synchronous code."""

import asyncio
import contextvars
import functools
import inspect
from concurrent.futures import Future
from typing import Any, Coroutine, Optional, TypeVar

T = TypeVar("T")


def is_async_callable(fn: Any) -> bool:
    """Check whether a callable is a coroutine function.

    Unwraps `functools.partial` and `functools.wraps`-style wrappers.

    Args:
        fn: The callable to check.

    Returns:
        Whether calling `fn` returns a coroutine.
    """
    while isinstance(fn, functools.partial):
        fn = fn.func

    if inspect.iscoroutinefunction(fn):
        return True

    unwrapped = inspect.unwrap(fn) if callable(fn) else fn
    return inspect.iscoroutinefunction(unwrapped)


def run_coroutine_blocking(
    coro: "Coroutine[Any, Any, T]",
    loop: Optional[asyncio.AbstractEventLoop] = None,
) -> T:
    """Run a coroutine to completion from synchronous code.

    If `loop` is given and running, the coroutine is dispatched onto it under
    the caller's `contextvars` context and this call blocks until it finishes.
    Otherwise the coroutine runs on a new event loop on the current thread.

    Args:
        coro: The coroutine to run.
        loop: The shared event loop to dispatch onto, if any.

    Raises:
        RuntimeError: If `loop` is the event loop already running on the
            current thread.

    Returns:
        The coroutine result.
    """
    if loop is not None and loop.is_running():
        try:
            running_loop: Optional[asyncio.AbstractEventLoop] = (
                asyncio.get_running_loop()
            )
        except RuntimeError:
            running_loop = None

        if running_loop is loop:
            raise RuntimeError(
                "Cannot run a coroutine to completion from within the event "
                "loop it should run on."
            )

        context = contextvars.copy_context()
        return run_coroutine_threadsafe_in_context(
            coro=coro, loop=loop, context=context
        ).result()

    return asyncio.run(coro)


def run_coroutine_threadsafe_in_context(
    coro: "Coroutine[Any, Any, T]",
    loop: asyncio.AbstractEventLoop,
    context: contextvars.Context,
) -> "Future[T]":
    """Schedule a coroutine on another loop under a captured context.

    The coroutine task is created from within `context.run(...)` so the task
    copies and runs under the captured context.

    Args:
        coro: The coroutine to run.
        loop: The target event loop.
        context: The context to run the coroutine under.

    Returns:
        A future resolved with the coroutine result.
    """
    result_future: "Future[T]" = Future()

    def _schedule() -> None:
        try:
            task = context.run(loop.create_task, coro)
        except BaseException as exc:
            result_future.set_exception(exc)
            return

        def _chain(completed: "asyncio.Task[T]") -> None:
            if completed.cancelled():
                result_future.set_exception(asyncio.CancelledError())
            elif (exc := completed.exception()) is not None:
                result_future.set_exception(exc)
            else:
                result_future.set_result(completed.result())

        task.add_done_callback(_chain)

    loop.call_soon_threadsafe(_schedule)
    return result_future
