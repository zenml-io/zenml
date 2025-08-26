#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Tests for serving concurrency management."""

import asyncio
import time

import pytest

from zenml.serving.concurrency import (
    ServingConcurrencyConfig,
    ServingExecutionManager,
    TooManyRequestsError,
)


@pytest.fixture
def test_config():
    """Create test concurrency configuration."""
    # Override environment variables for testing
    import os

    original_env = {}
    test_env = {
        "ZENML_SERVING_MAX_CONCURRENCY": "2",
        "ZENML_SERVING_MAX_QUEUE_SIZE": "3",
        "ZENML_SERVING_EXECUTOR": "thread",
        "ZENML_SERVING_REQUEST_TIMEOUT": "5",
    }

    # Save original values and set test values
    for key, value in test_env.items():
        original_env[key] = os.environ.get(key)
        os.environ[key] = value

    config = ServingConcurrencyConfig()

    # Restore original values
    for key, original_value in original_env.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value

    return config


@pytest.fixture
def execution_manager(test_config):
    """Create test execution manager."""
    manager = ServingExecutionManager(test_config)
    yield manager
    # Cleanup
    asyncio.create_task(manager.shutdown())


def slow_function(duration: float = 1.0) -> str:
    """A slow synchronous function for testing."""
    time.sleep(duration)
    return f"completed after {duration}s"


async def slow_async_function(duration: float = 1.0) -> str:
    """A slow asynchronous function for testing."""
    await asyncio.sleep(duration)
    return f"async completed after {duration}s"


def failing_function() -> str:
    """A function that always fails."""
    raise ValueError("Test error")


@pytest.mark.asyncio
async def test_basic_execution(execution_manager):
    """Test basic function execution."""
    result = await execution_manager.execute_with_limits(slow_function, 0.1)
    assert result == "completed after 0.1s"


@pytest.mark.asyncio
async def test_async_function_execution(execution_manager):
    """Test async function execution."""
    result = await execution_manager.execute_with_limits(
        slow_async_function, 0.1
    )
    assert result == "async completed after 0.1s"


@pytest.mark.asyncio
async def test_concurrency_limits(execution_manager):
    """Test that concurrency limits are enforced."""
    # Start two long-running tasks (should fill capacity)
    task1 = asyncio.create_task(
        execution_manager.execute_with_limits(slow_function, 2.0)
    )
    task2 = asyncio.create_task(
        execution_manager.execute_with_limits(slow_function, 2.0)
    )

    # Let them start
    await asyncio.sleep(0.1)

    # Stats should show active executions
    stats = execution_manager.get_stats()
    assert stats["active_executions"] == 2
    assert stats["total_executions"] == 2

    # Wait for completion
    results = await asyncio.gather(task1, task2)
    assert len(results) == 2

    # Final stats
    final_stats = execution_manager.get_stats()
    assert final_stats["active_executions"] == 0


@pytest.mark.asyncio
async def test_queue_overflow(execution_manager):
    """Test that queue overflow triggers TooManyRequestsError."""
    # Fill up both capacity and queue
    # Config: max_concurrency=2, max_queue_size=3
    tasks = []

    # Start 2 tasks (fill capacity)
    for i in range(2):
        task = asyncio.create_task(
            execution_manager.execute_with_limits(slow_function, 1.0)
        )
        tasks.append(task)

    # Wait a bit for tasks to start
    await asyncio.sleep(0.1)

    # Add 3 more tasks (fill queue)
    for i in range(3):
        task = asyncio.create_task(
            execution_manager.execute_with_limits(slow_function, 0.1)
        )
        tasks.append(task)

    # Wait for queue to fill
    await asyncio.sleep(0.1)

    # This should trigger TooManyRequestsError
    with pytest.raises(TooManyRequestsError):
        await execution_manager.execute_with_limits(slow_function, 0.1)

    # Wait for all tasks to complete
    await asyncio.gather(*tasks)


@pytest.mark.asyncio
async def test_timeout_handling(execution_manager):
    """Test timeout handling."""
    with pytest.raises(TimeoutError):
        await execution_manager.execute_with_limits(
            slow_function, 2.0, timeout=0.5
        )


@pytest.mark.asyncio
async def test_error_propagation(execution_manager):
    """Test that errors are properly propagated."""
    with pytest.raises(ValueError, match="Test error"):
        await execution_manager.execute_with_limits(failing_function)


@pytest.mark.asyncio
async def test_stats_accuracy(execution_manager):
    """Test that statistics are accurate."""
    initial_stats = execution_manager.get_stats()
    assert initial_stats["total_executions"] == 0
    assert initial_stats["active_executions"] == 0

    # Execute some successful tasks
    await execution_manager.execute_with_limits(slow_function, 0.1)
    await execution_manager.execute_with_limits(slow_function, 0.1)

    # Execute a failing task
    try:
        await execution_manager.execute_with_limits(failing_function)
    except ValueError:
        pass

    final_stats = execution_manager.get_stats()
    assert final_stats["total_executions"] == 3
    assert final_stats["active_executions"] == 0


@pytest.mark.asyncio
async def test_overload_detection(execution_manager):
    """Test overload detection."""
    # Initially not overloaded
    assert not execution_manager.is_overloaded()

    # Fill up capacity and queue
    tasks = []

    # Start long-running tasks to fill capacity and queue
    for i in range(5):  # 2 capacity + 3 queue
        task = asyncio.create_task(
            execution_manager.execute_with_limits(slow_function, 1.0)
        )
        tasks.append(task)

    # Wait for queue to fill
    await asyncio.sleep(0.2)

    # Should now be overloaded
    assert execution_manager.is_overloaded()

    # Wait for tasks to complete
    await asyncio.gather(*tasks)

    # Should no longer be overloaded
    await asyncio.sleep(0.1)  # Let cleanup happen
    assert not execution_manager.is_overloaded()


@pytest.mark.asyncio
async def test_concurrent_mixed_workload(execution_manager):
    """Test mixed workload with different execution times."""
    # Create a mix of fast and slow tasks
    fast_tasks = [
        execution_manager.execute_with_limits(slow_function, 0.1)
        for _ in range(3)
    ]

    slow_tasks = [
        execution_manager.execute_with_limits(slow_function, 0.5)
        for _ in range(2)
    ]

    # Execute all concurrently
    all_tasks = fast_tasks + slow_tasks
    results = await asyncio.gather(*all_tasks)

    # All should complete
    assert len(results) == 5

    # Check that fast tasks completed with expected duration
    fast_results = results[:3]
    for result in fast_results:
        assert "0.1s" in result

    # Check that slow tasks completed with expected duration
    slow_results = results[3:]
    for result in slow_results:
        assert "0.5s" in result


def test_config_from_environment():
    """Test configuration loading from environment variables."""
    import os

    # Test with custom environment
    test_env = {
        "ZENML_SERVING_MAX_CONCURRENCY": "10",
        "ZENML_SERVING_MAX_QUEUE_SIZE": "50",
        "ZENML_SERVING_EXECUTOR": "process",
        "ZENML_SERVING_REQUEST_TIMEOUT": "600",
        "ZENML_SERVING_STREAM_BUFFER": "200",
    }

    original_env = {}
    try:
        # Set test environment
        for key, value in test_env.items():
            original_env[key] = os.environ.get(key)
            os.environ[key] = value

        config = ServingConcurrencyConfig()

        assert config.max_concurrency == 10
        assert config.max_queue_size == 50
        assert config.executor_type.value == "process"
        assert config.request_timeout == 600
        assert config.stream_buffer_size == 200

    finally:
        # Restore original environment
        for key, original_value in original_env.items():
            if original_value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = original_value
