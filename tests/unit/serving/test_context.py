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
"""Tests for serving context management."""

import asyncio
import concurrent.futures
import threading
from typing import Optional

import pytest

from zenml.serving.context import (
    ServingStepContext,
    get_serving_job_context,
    get_serving_step_context,
    is_serving_context,
    serving_job_context,
    serving_step_context,
)


def test_serving_step_context_basic():
    """Test basic serving step context functionality."""
    context = ServingStepContext("test_step", job_id="test_job")

    assert context.step_name == "test_step"
    assert context.job_id == "test_job"

    # Test metadata
    context.add_output_metadata({"test": "value"})
    assert context._metadata == {"test": "value"}

    # Test artifact URI
    uri = context.get_output_artifact_uri("output")
    assert uri == "serving://test_job/test_step/output"


def test_serving_step_context_manager():
    """Test serving step context manager."""
    # Initially no context
    assert get_serving_step_context() is None
    assert not is_serving_context()

    # Within context
    with serving_step_context("test_step") as context:
        assert get_serving_step_context() is not None
        assert is_serving_context()
        assert context.step_name == "test_step"

    # After context
    assert get_serving_step_context() is None
    assert not is_serving_context()


def test_serving_job_context():
    """Test serving job context functionality."""
    params = {"param1": "value1"}

    with serving_job_context("test_job", params) as job_context:
        assert job_context.job_id == "test_job"
        assert job_context.parameters == params

        # Test step context creation
        step_context = job_context.get_step_context("step1")
        assert step_context.step_name == "step1"
        assert step_context.job_id == "test_job"

        # Same step context is returned
        step_context2 = job_context.get_step_context("step1")
        assert step_context is step_context2


def test_concurrent_step_contexts():
    """Test that step contexts are isolated between threads."""
    results = {}
    context_values = {}

    def worker(thread_id: int, step_name: str):
        """Worker function that sets and reads context."""
        with serving_step_context(step_name) as context:
            # Store the context
            context_values[thread_id] = context

            # Add some metadata
            context.add_output_metadata({"thread_id": thread_id})

            # Sleep to allow other threads to run
            threading.Event().wait(0.1)

            # Verify our context is still correct
            current_context = get_serving_step_context()
            assert current_context is not None
            assert current_context.step_name == step_name
            assert current_context._metadata.get("thread_id") == thread_id

            results[thread_id] = True

    # Run multiple threads concurrently
    threads = []
    for i in range(10):
        thread = threading.Thread(target=worker, args=(i, f"step_{i}"))
        threads.append(thread)
        thread.start()

    # Wait for all threads to complete
    for thread in threads:
        thread.join()

    # Verify all threads succeeded
    assert len(results) == 10
    assert all(results.values())

    # Verify contexts were isolated
    assert len(context_values) == 10
    for thread_id, context in context_values.items():
        assert context.step_name == f"step_{thread_id}"
        assert context._metadata.get("thread_id") == thread_id


@pytest.mark.asyncio
async def test_async_step_contexts():
    """Test that step contexts work with async/await."""
    results = {}

    async def async_worker(task_id: int, step_name: str):
        """Async worker function."""
        with serving_step_context(step_name) as context:
            context.add_output_metadata({"task_id": task_id})

            # Yield control to other tasks
            await asyncio.sleep(0.1)

            # Verify context is still correct
            current_context = get_serving_step_context()
            assert current_context is not None
            assert current_context.step_name == step_name
            assert current_context._metadata.get("task_id") == task_id

            results[task_id] = True

    # Run multiple async tasks concurrently
    tasks = [async_worker(i, f"async_step_{i}") for i in range(5)]

    await asyncio.gather(*tasks)

    # Verify all tasks succeeded
    assert len(results) == 5
    assert all(results.values())


def test_thread_pool_executor_contexts():
    """Test contexts with ThreadPoolExecutor."""

    def worker_with_context(step_name: str) -> Optional[str]:
        """Worker that uses serving context."""
        with serving_step_context(step_name) as context:
            context.add_output_metadata({"executed": True})
            current = get_serving_step_context()
            return current.step_name if current else None

    # Execute with thread pool
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        futures = [
            executor.submit(worker_with_context, f"pool_step_{i}")
            for i in range(5)
        ]

        results = [future.result() for future in futures]

    # Verify results
    expected = [f"pool_step_{i}" for i in range(5)]
    assert sorted(results) == sorted(expected)


def test_nested_contexts():
    """Test nested serving contexts."""
    with serving_job_context("job1", {"param": "value1"}) as job1:
        assert get_serving_job_context() == job1

        with serving_step_context("step1") as step1:
            assert get_serving_step_context() == step1
            assert step1.step_name == "step1"

            with serving_step_context("step2") as step2:
                assert get_serving_step_context() == step2
                assert step2.step_name == "step2"

            # Back to step1 context
            assert get_serving_step_context() == step1

        # Back to job context only
        assert get_serving_job_context() == job1
        assert get_serving_step_context() is None


def test_context_isolation_between_jobs():
    """Test that job contexts don't interfere with each other."""

    def job_worker(job_id: str, params: dict) -> str:
        """Worker that uses job context."""
        with serving_job_context(job_id, params):
            job_context = get_serving_job_context()
            assert job_context is not None
            assert job_context.job_id == job_id
            assert job_context.parameters == params
            return job_id

    # Run multiple jobs concurrently
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
        jobs = [
            ("job1", {"param": "value1"}),
            ("job2", {"param": "value2"}),
            ("job3", {"param": "value3"}),
        ]

        futures = [
            executor.submit(job_worker, job_id, params)
            for job_id, params in jobs
        ]

        results = [future.result() for future in futures]

    # All jobs should have completed successfully
    assert sorted(results) == ["job1", "job2", "job3"]
