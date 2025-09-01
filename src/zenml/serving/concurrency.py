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
"""Concurrency management for ZenML pipeline serving."""

import asyncio
import os
import time
from collections import deque
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from enum import Enum
from typing import Any, Callable, Dict, Optional, TypeVar, Union, cast

import anyio
from anyio import CapacityLimiter

from zenml.logger import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


class ExecutorType(str, Enum):
    """Supported executor types for serving workloads."""

    THREAD = "thread"
    PROCESS = "process"


class ServingConcurrencyConfig:
    """Configuration for serving concurrency management."""

    def __init__(self) -> None:
        """Initialize concurrency configuration from environment variables."""
        # Maximum concurrent executions (default: 5 per CPU core)
        cpu_count = os.cpu_count() or 4
        self.max_concurrency = int(
            os.getenv("ZENML_SERVING_MAX_CONCURRENCY", cpu_count * 5)
        )

        # Maximum queue size for pending executions
        self.max_queue_size = int(
            os.getenv("ZENML_SERVING_MAX_QUEUE_SIZE", "100")
        )

        # Executor type (thread or process)
        executor_type_str = os.getenv(
            "ZENML_SERVING_EXECUTOR", "thread"
        ).lower()
        self.executor_type = ExecutorType(executor_type_str)

        # Request timeout in seconds
        self.request_timeout = int(
            os.getenv("ZENML_SERVING_REQUEST_TIMEOUT", "300")
        )

        # Stream buffer size for events
        self.stream_buffer_size = int(
            os.getenv("ZENML_SERVING_STREAM_BUFFER", "100")
        )

        logger.info(
            f"Serving concurrency config: max_concurrency={self.max_concurrency}, "
            f"max_queue_size={self.max_queue_size}, executor_type={self.executor_type}, "
            f"request_timeout={self.request_timeout}s"
        )


class ServingExecutionManager:
    """Manages concurrent pipeline execution with backpressure and limits."""

    def __init__(self, config: Optional[ServingConcurrencyConfig] = None):
        """Initialize the execution manager.

        Args:
            config: Concurrency configuration, creates default if None
        """
        self.config = config or ServingConcurrencyConfig()

        # Capacity limiter for controlling concurrency
        self._capacity_limiter = CapacityLimiter(self.config.max_concurrency)

        # Executor for running sync functions
        if self.config.executor_type == ExecutorType.PROCESS:
            self._executor: Union[
                ProcessPoolExecutor, ThreadPoolExecutor
            ] = ProcessPoolExecutor(max_workers=self.config.max_concurrency)
        else:
            self._executor = ThreadPoolExecutor(
                max_workers=self.config.max_concurrency
            )

        # Track executions and queue with explicit counters for accurate backpressure
        self._active_executions = 0
        self._total_executions = 0
        self._successful_executions = 0
        self._failed_executions = 0
        self._timeout_executions = 0
        self._canceled_executions = 0
        self._queue_full_rejections = 0
        self._queued_executions = 0  # Explicit queue size tracking
        self._stats_lock = asyncio.Lock()  # Thread-safe stats updates

        # Track execution times for percentiles
        self._execution_times: "deque[float]" = deque(
            maxlen=1000
        )  # Keep last 1000 execution times

        logger.info(
            f"ServingExecutionManager initialized with {self.config.executor_type} executor"
        )

    async def execute_with_limits(
        self,
        func: Callable[..., T],
        *args: Any,
        timeout: Optional[float] = None,
        **kwargs: Any,
    ) -> T:
        """Execute a function with concurrency limits and timeout.

        This method ensures that:
        1. No more than max_concurrency executions run simultaneously
        2. Requests timeout if they take too long
        3. Backpressure is applied when queue is full

        Args:
            func: Function to execute
            *args: Positional arguments for func
            timeout: Optional timeout override
            **kwargs: Keyword arguments for func

        Returns:
            Result of func execution

        Raises:
            TooManyRequestsError: If queue is at capacity
            TimeoutError: If execution exceeds timeout
            Exception: Any exception from func execution
        """
        # Check if we're at queue capacity using explicit tracking
        async with self._stats_lock:
            current_queue_size = self._queued_executions
            if current_queue_size >= self.config.max_queue_size:
                self._queue_full_rejections += 1
                raise TooManyRequestsError(
                    f"Service overloaded: {current_queue_size} "
                    f"requests queued (max: {self.config.max_queue_size}). "
                    "Please retry later."
                )

            # Reserve spot in queue
            self._queued_executions += 1
            self._total_executions += 1

        timeout = timeout or self.config.request_timeout
        start_time = time.time()

        try:
            # Execute with capacity limiter and timeout
            async with self._capacity_limiter:
                # Update counters when we start actual execution
                async with self._stats_lock:
                    self._queued_executions -= 1  # No longer queued
                    self._active_executions += 1  # Now active

                if asyncio.iscoroutinefunction(func):
                    # Async function - run directly with timeout
                    result = await asyncio.wait_for(
                        func(*args, **kwargs), timeout=timeout
                    )
                else:
                    # Sync function - run in appropriate executor with timeout and capacity limiter
                    if self.config.executor_type == ExecutorType.PROCESS:
                        # Use process executor for CPU-intensive tasks
                        loop = asyncio.get_running_loop()
                        result = await asyncio.wait_for(
                            loop.run_in_executor(
                                self._executor, lambda: func(*args, **kwargs)
                            ),
                            timeout=timeout,
                        )
                    else:
                        # Use thread executor via anyio for I/O-bound tasks
                        # Note: Don't pass limiter since we're already under "async with self._capacity_limiter"
                        result = await asyncio.wait_for(
                            anyio.to_thread.run_sync(func, *args, **kwargs),
                            timeout=timeout,
                        )

            # Track successful execution
            execution_time = time.time() - start_time
            async with self._stats_lock:
                self._successful_executions += 1
                self._execution_times.append(execution_time)

            return cast(T, result)

        except asyncio.TimeoutError:
            execution_time = time.time() - start_time
            async with self._stats_lock:
                self._timeout_executions += 1
                self._execution_times.append(execution_time)
            logger.warning(f"Execution timed out after {timeout}s")
            raise TimeoutError(f"Request timed out after {timeout}s")

        except asyncio.CancelledError:
            execution_time = time.time() - start_time
            async with self._stats_lock:
                self._canceled_executions += 1
                self._execution_times.append(execution_time)
            logger.warning("Execution was cancelled")
            raise

        except Exception as e:
            execution_time = time.time() - start_time
            async with self._stats_lock:
                self._failed_executions += 1
                self._execution_times.append(execution_time)
            logger.error(f"Execution failed: {str(e)}")
            raise

        finally:
            # Clean up counters
            async with self._stats_lock:
                if self._active_executions > 0:
                    self._active_executions -= 1
                if self._queued_executions > 0:
                    self._queued_executions -= 1

    def get_stats(self) -> Dict[str, Any]:
        """Get current execution statistics.

        Returns:
            Dictionary with execution statistics including percentiles
        """
        # Calculate execution time percentiles
        exec_times = (
            list(self._execution_times) if self._execution_times else [0]
        )
        if len(exec_times) > 0:
            exec_times.sort()
            p50 = exec_times[int(len(exec_times) * 0.5)]
            p95 = exec_times[int(len(exec_times) * 0.95)]
            p99 = exec_times[int(len(exec_times) * 0.99)]
            avg = sum(exec_times) / len(exec_times)
        else:
            p50 = p95 = p99 = avg = 0.0

        # Use explicit counters instead of CapacityLimiter.statistics()
        # which may not be public API
        return {
            # Core execution metrics
            "active_executions": self._active_executions,
            "total_executions": self._total_executions,
            "successful_executions": self._successful_executions,
            "failed_executions": self._failed_executions,
            "timeout_executions": self._timeout_executions,
            "canceled_executions": self._canceled_executions,
            # Queue and capacity metrics
            "queue_length": self._queued_executions,
            "queue_full_rejections": self._queue_full_rejections,
            "max_concurrency": self.config.max_concurrency,
            "max_queue_size": self.config.max_queue_size,
            # Execution time percentiles (in seconds)
            "execution_time_p50": round(p50, 3),
            "execution_time_p95": round(p95, 3),
            "execution_time_p99": round(p99, 3),
            "execution_time_avg": round(avg, 3),
            "execution_time_samples": len(exec_times),
            # Configuration
            "executor_type": self.config.executor_type.value,
        }

    def is_overloaded(self) -> bool:
        """Check if the service is currently overloaded.

        Returns:
            True if service is overloaded and should reject new requests
        """
        # Use explicit queue tracking instead of capacity limiter statistics
        return self._queued_executions >= self.config.max_queue_size

    async def shutdown(self) -> None:
        """Shutdown the execution manager and cleanup resources."""
        logger.info("Shutting down ServingExecutionManager...")

        # Shutdown executor
        if hasattr(self._executor, "shutdown"):
            if self.config.executor_type == ExecutorType.PROCESS:
                self._executor.shutdown(wait=True)
            else:
                self._executor.shutdown(wait=False)

        logger.info("ServingExecutionManager shutdown complete")


class TooManyRequestsError(Exception):
    """Exception raised when service is overloaded and cannot accept more requests."""

    pass
