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
"""Unit tests for async pipeline validation."""

import pytest

from zenml import pipeline


def test_async_bare_pipeline_decorator_raises() -> None:
    """Tests that a bare `@pipeline` rejects an async entrypoint."""
    with pytest.raises(RuntimeError, match="dynamic=True"):

        @pipeline
        async def p() -> None: ...


def test_async_non_dynamic_pipeline_decorator_raises() -> None:
    """Tests that `@pipeline(dynamic=False)` rejects an async entrypoint."""
    with pytest.raises(RuntimeError, match="dynamic=True"):

        @pipeline(dynamic=False)
        async def p() -> None: ...


def test_async_dynamic_pipeline_decorator_succeeds() -> None:
    """Tests that `@pipeline(dynamic=True)` accepts an async entrypoint."""

    @pipeline(dynamic=True)
    async def p() -> None: ...

    assert p


def test_sync_bare_pipeline_decorator_succeeds() -> None:
    """Tests that a bare `@pipeline` accepts a sync entrypoint."""

    @pipeline
    def p() -> None: ...

    assert p


def test_sync_dynamic_pipeline_decorator_succeeds() -> None:
    """Tests that `@pipeline(dynamic=True)` accepts a sync entrypoint."""

    @pipeline(dynamic=True)
    def p() -> None: ...

    assert p
