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
"""Asyncio utilities."""

import asyncio
import contextvars
import functools
import inspect
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Coroutine, TypeVar

T = TypeVar("T")


def is_async_callable(fn: Any) -> bool:
    """Check whether a callable is a coroutine function.

    Args:
        fn: The callable to check.

    Returns:
        Whether the callable is a coroutine function.
    """
    while isinstance(fn, functools.partial):
        fn = fn.func

    if inspect.iscoroutinefunction(fn):
        return True

    unwrapped = inspect.unwrap(fn) if callable(fn) else fn
    return inspect.iscoroutinefunction(unwrapped)


def run_coroutine_isolated(coro: Coroutine[Any, Any, T]) -> T:
    """Run a coroutine to completion on its own event loop.

    Uses the current thread when it has no running loop, otherwise runs on a
    fresh thread so an already-running loop is never reused or blocked.

    Args:
        coro: The coroutine to run.

    Returns:
        The result of the coroutine.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)

    ctx = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(ctx.run, asyncio.run, coro).result()
