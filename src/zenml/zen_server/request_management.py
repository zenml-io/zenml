#  Copyright (c) ZenML GmbH 2025. All Rights Reserved.
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
"""Request management utilities."""

import asyncio
import logging
import threading
import time
from contextvars import ContextVar
from typing import Any, Callable, Dict, Optional
from uuid import UUID, uuid4

from fastapi import Request
from fastapi.responses import JSONResponse

from zenml.logger import get_logger
from zenml.utils.time_utils import utc_now
from zenml.zen_server.auth import AuthContext

logger = get_logger(__name__)


MAX_ALLOWED_REQUEST_RETRY_AGE_SECONDS = 600  # 10 minutes


class RequestContext:
    """Context for a request."""

    def __init__(self, request: Request) -> None:
        """Initialize the request context.

        Args:
            request: The request.
        """
        self.request = request
        self.request_id = request.headers.get("X-Request-ID", str(uuid4())[:8])
        transaction_id = request.headers.get("Idempotency-Key")
        if transaction_id:
            try:
                self.transaction_id = UUID(transaction_id)
            except ValueError:
                raise ValueError(
                    f"Invalid UUID idempotency key: {transaction_id}. "
                    "Please use a valid UUID."
                )

        # Use a random trace ID to identify the request internally in the logs.
        self.trace_id = str(uuid4())[:4]

        self.source = request.headers.get("User-Agent") or ""
        self.received_at = utc_now()

        self.auth_context: Optional[AuthContext] = None

    @property
    def process_time(self) -> float:
        """Get the process time in seconds of the request.

        Returns:
            The request ID.
        """
        return (utc_now() - self.received_at).total_seconds()

    @property
    def log_request_id(self) -> str:
        """Get the full request ID for logging.

        Returns:
            The request ID.
        """
        source_type = self.source.split("/")[0]
        return f"{self.request_id}/{source_type}/{self.trace_id}"

    @property
    def log_request(self) -> str:
        """Get the request details for logging.

        Returns:
            The request details for logging.
        """
        client_ip = (
            self.request.client.host if self.request.client else "unknown"
        )
        url_path = self.request.url.path
        method = self.request.method
        return f"{method} {url_path} from {client_ip}"

    @property
    def log_duration(self) -> str:
        """Get the duration of the request.

        Returns:
            The duration of the request.
        """
        current_time = utc_now()
        duration = (current_time - self.received_at).total_seconds() * 1000
        return f"{duration:.2f}ms"

    def is_retry(self, request_context: "RequestContext") -> bool:
        """Check if the request context is a retry of the this request context.

        Args:
            request_context: The request context to check.
        """
        # The similarities between the two requests must be very strictly
        # verified to avoid replay attacks:
        #
        # 1. They must have the same idempotency transaction ID.
        if request_context.transaction_id != self.transaction_id:
            return False

        # 2. They must have the same URL and method
        if (
            request_context.request.url != self.request.url
            or request_context.request.method != self.request.method
        ):
            return False

        # 3. If the original request was authenticated, the new request must
        # also be authenticated with the same account.
        if self.auth_context is not None and (
            request_context.auth_context is None
            or (
                request_context.auth_context.user.id
                != self.auth_context.user.id
            )
        ):
            return False

        return True


class RequestRecord:
    """A record of an in-flight or cached request."""

    future: Optional[asyncio.Future[Any]] = None
    result_timestamp: Optional[float] = None
    result: Any = None
    request_context: RequestContext

    def __init__(
        self, future: asyncio.Future[Any], request_context: RequestContext
    ) -> None:
        """Initialize the request record.

        Args:
            future: The future of the request.
            request_context: The request context.
        """
        self.future = future
        self.request_context = request_context

    def set_result(self, result: Any) -> None:
        """Set the result of the request.

        Args:
            result: The result of the request.
        """
        if self.future:
            self.future.set_result(result)
            self.future = None
        self.result = result
        self.result_timestamp = time.time()

    def set_exception(self, exception: Exception) -> None:
        """Set the exception of the request.

        Args:
            exception: The exception of the request.
        """
        if self.future:
            self.future.set_exception(exception)
            self.future = None
        self.result = exception
        self.result_timestamp = time.time()

    def fetch_result(self) -> Any:
        """Fetch the result of the request.

        Returns:
            The result of the request.

        Raises:
            Exception: The exception of the request, if one is stored instead
                of a result.
        """
        try:
            if isinstance(self.result, Exception):
                raise self.result
            return self.result
        finally:
            # Reset the result timestamp every time it is fetched
            self.result_timestamp = time.time()


class RequestManager:
    """A manager for requests.

    This class is used to manage requests by caching the results of requests
    that have already been executed. It also handles cleanup of expired
    requests and limits the number of completed requests.
    """

    def __init__(
        self,
        result_ttl: float = 60.0,
        max_completed_requests: int = 100,
        timeout: float = 20.0,
    ) -> None:
        """Initialize the request manager.

        Args:
            result_ttl: The time to live for cached results. Comes into effect
                after a request is completed and is reset every time the result
                is fetched.
            max_completed_requests: The maximum number of completed requests to
                keep. This is used to limit the memory usage of the
                manager.
            timeout: The timeout for requests. If a request takes longer than
                this, a 429 error will be returned to the client to slow down
                the request rate.
        """
        self.requests: Dict[UUID, RequestRecord] = dict()
        self.lock = asyncio.Lock()
        self.result_ttl = result_ttl
        self.max_completed_requests = max_completed_requests
        self.timeout = timeout
        self.cleanup_task: Optional[asyncio.Task[None]] = None
        self.shutdown_event = asyncio.Event()

        self.request_contexts: ContextVar[Optional[RequestContext]] = (
            ContextVar("request_contexts", default=None)
        )

    @property
    def current_request(self) -> RequestContext:
        """Get the current request context.

        Returns:
            The current request context.

        Raises:
            RuntimeError: If no request context is set.
        """
        request_context = self.request_contexts.get()
        if request_context is None:
            raise RuntimeError("No request context set")
        return request_context

    @current_request.setter
    def current_request(self, request_context: RequestContext) -> None:
        """Set the current request context.

        Args:
            request_context: The request context.
        """
        self.request_contexts.set(request_context)

    async def startup(self) -> None:
        """Start the request manager.

        This method starts a background task that periodically cleans up
        expired requests and limits the number of completed requests.
        """
        self.cleanup_task = asyncio.create_task(self._periodic_cleanup())

    async def shutdown(self) -> None:
        """Shutdown the request manager.

        This method stops the background task that periodically cleans up
        expired requests and limits the number of completed requests.
        """
        self.shutdown_event.set()
        if self.cleanup_task:
            await self.cleanup_task

    async def _periodic_cleanup(self) -> None:
        """Periodic cleanup task.

        Periodically clean up expired requests and limit the number of
        completed requests.
        """
        while not self.shutdown_event.is_set():
            await self._cleanup()
            await asyncio.sleep(5)

    async def _cleanup(self) -> None:
        """Clean up expired requests and limit the number of completed requests.

        This method is called periodically by the background task as well as
        opportunistically when a request is completed to clean up expired
        requests and limit the number of completed requests.
        """
        async with self.lock:
            now = time.time()

            completed_requests = [
                (request_id, record.result_timestamp)
                for request_id, record in self.requests.items()
                if record.result_timestamp is not None
            ]

            # Remove expired completed requests
            for i in reversed(range(len(completed_requests))):
                request_id, result_timestamp = completed_requests[i]
                if now - result_timestamp > self.result_ttl:
                    del self.requests[request_id]
                    del completed_requests[i]

            # If we have more completed requests than allowed, remove oldest ones
            if len(completed_requests) > self.max_completed_requests:
                # Sort by timestamp, oldest first
                completed_requests.sort(key=lambda x: x[1])
                for request_id, _ in completed_requests[
                    : self.max_completed_requests
                ]:
                    del self.requests[request_id]

    async def _verify_duplicate_request_forgery(
        self, request_context: RequestContext
    ) -> bool:
        """Verify if the request is a forgery of a previously executed request.

        A forgery is a request that has the same transaction ID as a previously
        executed request, but has different request parameters.

        Args:
            request_context: The request context to verify.

        Returns:
            True if the request is a forgery of a previously executed request,
            False otherwise.
        """
        if request_context.transaction_id not in self.requests:
            # This is not a forgery, it's a new request
            return False

        # A previous request with the same transaction ID exists.
        previous_request = self.requests[request_context.transaction_id]

        if not previous_request.request_context.is_retry(request_context):
            # This is a forgery: it's a new request with the same transaction
            # ID but it does not qualify as a retry according to the request
            # parameters.
            return True

        # This is a retry of a previously executed request.
        return False

    async def run_and_cache_result(
        self,
        func: Callable[..., Any],
        cache_enabled: bool,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Run a request and cache the result.

        This method is called in the background to run a request and cache the
        result.

        Args:
            func: The function to execute.
            cache_enabled: Whether to cache the result when done.
            *args: The arguments to pass to the function.
            **kwargs: The keyword arguments to pass to the function.
        """
        from starlette.concurrency import run_in_threadpool

        from zenml.zen_server.utils import get_system_metrics_log_str

        request_context = self.current_request

        logger.debug(
            f"[{request_context.log_request_id}] ENDPOINT STATS - "
            f"{request_context.log_request} "
            f"async {func.__name__} STARTED "
            f"{get_system_metrics_log_str(request_context.request)}"
        )

        def run_func_with_logs(*args: Any, **kwargs: Any) -> Any:
            logger.debug(
                f"[{request_context.log_request_id}] ENDPOINT STATS - "
                f"{request_context.log_request} "
                f"sync {func.__name__} STARTED "
                f"{get_system_metrics_log_str(request_context.request)}"
            )

            try:
                return func(*args, **kwargs)
            finally:
                logger.debug(
                    f"[{request_context.log_request_id}] ENDPOINT STATS - "
                    f"{request_context.log_request} "
                    f"sync {func.__name__} COMPLETED "
                    f"{get_system_metrics_log_str(request_context.request)}"
                )

        try:
            result = await run_in_threadpool(
                run_func_with_logs, *args, **kwargs
            )
        except Exception as e:
            result = e

        logger.debug(
            f"[{request_context.log_request_id}] ENDPOINT STATS - "
            f"{request_context.log_request} "
            f"async {func.__name__} COMPLETED "
            f"{get_system_metrics_log_str(request_context.request)}"
        )

        if cache_enabled:
            async with self.lock:
                if request_context.transaction_id in self.requests:
                    if isinstance(result, Exception):
                        self.requests[
                            request_context.transaction_id
                        ].set_exception(result)
                    else:
                        self.requests[
                            request_context.transaction_id
                        ].set_result(result)

        await self._cleanup()

    async def execute(
        self,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute a request with in-memory de-duplication.

        Call this method to execute a request with in-memory de-duplication.
        If the request (identified by the request_id) has previously been
        executed and the result is still cached, the result will be returned
        immediately. If the request is in-flight, the method will wait for it
        to complete. If the request is not in-flight, the method will start
        execution in the background and cache the result.

        Args:
            func: The function to execute.
            *args: The arguments to pass to the function.
            **kwargs: The keyword arguments to pass to the function.

        Returns:
            The result of the request.

        Raises:
            Exception: The cached exception of the request, if one is cached
                instead of a result.
        """
        from zenml.zen_server.utils import get_system_metrics_log_str

        request_context = self.current_request
        assert request_context is not None

        logger.debug(
            f"[{request_context.log_request_id}] ENDPOINT STATS - "
            f"{request_context.log_request} "
            f"{func.__name__} STARTED "
            f"{get_system_metrics_log_str(request_context.request)}"
        )

        # Clean up expired requests
        await self._cleanup()

        async with self.lock:
            # Check for a cached result first
            transaction_id = request_context.transaction_id
            cache_result = True
            if await self._verify_duplicate_request_forgery(request_context):
                # It was detected that this request might be a forgery of a
                # previously executed request. This might happen if the
                # request has different request headers but the same request
                # ID, for example if the request is processed by a proxy,
                # so we still want to process it, but we log a warning and
                # bypass the request deduplication.
                logger.warning(
                    f"[{request_context.log_request_id}] "
                    f"FORGERY DETECTED: "
                    f"{request_context.log_request}. "
                )
                # Mark the request as not being cached/deduplicated
                cache_result = False

            if cache_result and transaction_id in self.requests:
                cached_request = self.requests[transaction_id]
                if cached_request.future is None:
                    logger.debug(
                        f"[{request_context.log_request_id}] ENDPOINT STATS - "
                        f"{request_context.log_request} "
                        f"{func.__name__} CACHE HIT "
                        f"{get_system_metrics_log_str(request_context.request)}"
                    )
                    # Request has already been executed, result is available
                    return cached_request.fetch_result()
                else:
                    logger.debug(
                        f"[{request_context.log_request_id}] ENDPOINT STATS - "
                        f"{request_context.log_request} "
                        f"{func.__name__} RESUMED "
                        f"{get_system_metrics_log_str(request_context.request)}"
                    )
                    # Request is still in-flight, wait for it to complete
                    fut = cached_request.future
            else:
                # Start execution in background, store the future
                fut = asyncio.get_event_loop().create_future()
                if cache_result:
                    self.requests[transaction_id] = RequestRecord(
                        future=fut, request_context=request_context
                    )
                asyncio.create_task(
                    self.run_and_cache_result(
                        func,
                        cache_result,
                        *args,
                        **kwargs,
                    )
                )

        # Wait for the request to complete, with timeout
        try:
            # We take into account the time that has already elapsed since the
            # request was received to avoid keeping the request for too long.
            timeout = max(0, self.timeout - request_context.process_time)
            result = await asyncio.wait_for(
                # We use asyncio.shield to prevent the request from being
                # cancelled when the timeout is reached.
                asyncio.shield(fut),
                timeout=timeout,
            )
            async with self.lock:
                # We successfully completed the request, so the result cache is
                # no longer needed.
                if transaction_id in self.requests:
                    del self.requests[transaction_id]

            logger.debug(
                f"[{request_context.log_request_id}] ENDPOINT STATS - "
                f"{request_context.log_request} "
                f"{func.__name__} COMPLETED "
                f"{get_system_metrics_log_str(request_context.request)}"
            )
            return result
        except asyncio.TimeoutError:
            logger.debug(
                f"[{request_context.log_request_id}] ENDPOINT STATS - "
                f"{request_context.log_request} "
                f"{func.__name__} TIMEOUT "
                f"{get_system_metrics_log_str(request_context.request)}"
            )
            return JSONResponse(
                {"error": "Server too busy. Please try again later."},
                status_code=429,
            )
