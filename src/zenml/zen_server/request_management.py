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
import base64
import json
from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, Callable, Dict, Optional
from uuid import UUID, uuid4

from fastapi import Request, Response
from fastapi.responses import JSONResponse

from zenml.constants import MEDIUMTEXT_MAX_LENGTH
from zenml.exceptions import EntityExistsError
from zenml.logger import get_logger
from zenml.models import ApiTransactionRequest, ApiTransactionUpdate
from zenml.utils.json_utils import pydantic_encoder
from zenml.utils.time_utils import utc_now

if TYPE_CHECKING:
    from zenml.zen_server.auth import AuthContext


logger = get_logger(__name__)


class RequestContext:
    """Context for a request."""

    def __init__(self, request: Request) -> None:
        """Initialize the request context.

        Args:
            request: The request.

        Raises:
            ValueError: If the idempotency key is not a valid UUID.
        """
        self.request = request
        self.request_id = request.headers.get("X-Request-ID", str(uuid4())[:8])
        self.transaction_id: Optional[UUID] = None
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

        self.auth_context: Optional["AuthContext"] = None

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

    @property
    def is_cacheable(self) -> bool:
        """Check if the request is cacheable.

        Returns:
            Whether the request is cacheable.
        """
        # Only cache requests that are authenticated and are part of a
        # transaction.
        return (
            self.auth_context is not None and self.transaction_id is not None
        )


class RequestRecord:
    """A record of an in-flight or cached request."""

    future: asyncio.Future[Any]
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
        self.completed = False

    def set_result(self, result: Any) -> None:
        """Set the result of the request.

        Args:
            result: The result of the request.
        """
        self.future.set_result(result)
        self.completed = True

    def set_exception(self, exception: Exception) -> None:
        """Set the exception of the request.

        Args:
            exception: The exception of the request.
        """
        self.future.set_exception(exception)
        self.completed = True


class RequestManager:
    """A manager for requests.

    This class is used to manage requests by caching the results of requests
    that have already been executed.
    """

    def __init__(
        self,
        transaction_ttl: int,
        request_timeout: float,
        deduplicate: bool = True,
    ) -> None:
        """Initialize the request manager.

        Args:
            transaction_ttl: The time to live for cached transactions. Comes
                into effect after a request is completed.
            request_timeout: The timeout for requests. If a request takes longer
                than this, a 429 error will be returned to the client to slow
                down the request rate.
            deduplicate: Whether to deduplicate requests.
        """
        self.deduplicate = deduplicate
        self.transactions: Dict[UUID, RequestRecord] = dict()
        self.lock = asyncio.Lock()
        self.transaction_ttl = transaction_ttl
        self.request_timeout = request_timeout

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
        """Start the request manager."""
        pass

    async def shutdown(self) -> None:
        """Shutdown the request manager."""
        pass

    async def async_run_and_cache_result(
        self,
        func: Callable[..., Any],
        deduplicate: bool,
        request_record: RequestRecord,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Run a request and cache the result.

        This method is called in the background to run a request and cache the
        result.

        Args:
            func: The function to execute.
            deduplicate: Whether to enable or disable request deduplication for
                this request.
            request_record: The request record to cache the result in.
            *args: The arguments to pass to the function.
            **kwargs: The keyword arguments to pass to the function.
        """
        from starlette.concurrency import run_in_threadpool

        from zenml.zen_server.utils import get_system_metrics_log_str

        request_context = request_record.request_context
        transaction_id = request_context.transaction_id

        logger.debug(
            f"[{request_context.log_request_id}] ENDPOINT STATS - "
            f"{request_context.log_request} "
            f"async {func.__name__} STARTED "
            f"{get_system_metrics_log_str(request_context.request)}"
        )

        def sync_run_and_cache_result(*args: Any, **kwargs: Any) -> Any:
            from zenml.zen_server.utils import zen_store

            # Copy the deduplicate flag to a local variable to avoid modifying
            # the argument in the outer scope.
            deduplicate_request = deduplicate

            logger.debug(
                f"[{request_context.log_request_id}] ENDPOINT STATS - "
                f"{request_context.log_request} "
                f"sync {func.__name__} STARTED "
                f"{get_system_metrics_log_str(request_context.request)}"
            )

            try:
                # Create or get the API transaction from the database
                if deduplicate_request:
                    assert transaction_id is not None
                    try:
                        api_transaction, transaction_created = (
                            zen_store().get_or_create_api_transaction(
                                api_transaction=ApiTransactionRequest(
                                    transaction_id=transaction_id,
                                    method=request_context.request.method,
                                    url=str(request_context.request.url),
                                )
                            )
                        )
                    except EntityExistsError:
                        logger.error(
                            f"[{request_context.log_request_id}] "
                            f"Transaction {transaction_id} already exists "
                            f"with method {request_context.request.method} and "
                            f"URL {str(request_context.request.url)}. Skipping "
                            "caching."
                        )
                        deduplicate_request = False

                    if deduplicate_request:
                        if api_transaction.completed:
                            logger.debug(
                                f"[{request_context.log_request_id}] "
                                "ENDPOINT STATS - "
                                f"{request_context.log_request} "
                                f"sync {func.__name__} CACHE HIT "
                                f"{get_system_metrics_log_str(request_context.request)}"
                            )

                            # The transaction already completed, we can return the
                            # result right away.
                            result = api_transaction.get_result()
                            if result is not None:
                                return Response(
                                    base64.b64decode(result),
                                    media_type="application/json",
                                )
                            else:
                                return

                        elif not transaction_created:
                            logger.debug(
                                f"[{request_context.log_request_id}] "
                                "ENDPOINT STATS - "
                                f"{request_context.log_request} "
                                f"sync {func.__name__} DELAYED "
                                f"{get_system_metrics_log_str(request_context.request)}"
                            )

                            # The transaction is being processed by another server
                            # instance. We need to wait for it to complete. Instead
                            # of blocking this worker thread, we return a 429 error
                            # to the client to force it to retry later.
                            return JSONResponse(
                                {
                                    "error": "Server too busy. Please try again later."
                                },
                                status_code=429,
                            )

                try:
                    result = func(*args, **kwargs)
                except Exception:
                    if deduplicate_request:
                        assert transaction_id is not None
                        # We don't cache exceptions. If the client retries, the
                        # request will be executed again and the exception, if
                        # persistent, will be raised again.
                        zen_store().delete_api_transaction(
                            api_transaction_id=transaction_id,
                        )
                    raise

                if deduplicate_request:
                    assert transaction_id is not None
                    cache_result = True
                    result_to_cache: Optional[bytes] = None
                    if result is not None:
                        try:
                            result_to_cache = base64.b64encode(
                                json.dumps(
                                    result, default=pydantic_encoder
                                ).encode("utf-8")
                            )
                        except Exception:
                            # If the result is not serializable, we don't cache it.
                            cache_result = False
                            logger.exception(
                                f"Failed to serialize result of {func.__name__} "
                                f"for transaction {transaction_id}. Skipping "
                                "caching."
                            )
                        else:
                            if len(result_to_cache) > MEDIUMTEXT_MAX_LENGTH:
                                # If the result is too large, we also don't cache it.
                                cache_result = False
                                result_to_cache = None
                                logger.error(
                                    f"Result of {func.__name__} "
                                    f"for transaction {transaction_id} is too "
                                    "large. Skipping caching."
                                )

                    if cache_result:
                        api_transaction_update = ApiTransactionUpdate(
                            cache_time=self.transaction_ttl,
                        )
                        if result_to_cache is not None:
                            api_transaction_update.set_result(
                                result_to_cache.decode("utf-8")
                            )
                        zen_store().finalize_api_transaction(
                            api_transaction_id=transaction_id,
                            api_transaction_update=api_transaction_update,
                        )
                    else:
                        # If the result is not cacheable, there is no point in
                        # keeping the transaction around.
                        zen_store().delete_api_transaction(
                            api_transaction_id=transaction_id,
                        )

                return result
            finally:
                logger.debug(
                    f"[{request_context.log_request_id}] ENDPOINT STATS - "
                    f"{request_context.log_request} "
                    f"sync {func.__name__} COMPLETED "
                    f"{get_system_metrics_log_str(request_context.request)}"
                )

        try:
            result = await run_in_threadpool(
                sync_run_and_cache_result, *args, **kwargs
            )
        except Exception as e:
            result = e

        if deduplicate:
            async with self.lock:
                if transaction_id in self.transactions:
                    del self.transactions[transaction_id]

        logger.debug(
            f"[{request_context.log_request_id}] ENDPOINT STATS - "
            f"{request_context.log_request} "
            f"async {func.__name__} COMPLETED "
            f"{get_system_metrics_log_str(request_context.request)}"
        )

        if isinstance(result, Exception):
            request_record.set_exception(result)
        else:
            request_record.set_result(result)

    async def execute(
        self,
        func: Callable[..., Any],
        deduplicate: Optional[bool],
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
            deduplicate: Whether to enable or disable request deduplication for
                this request. If not specified, by default, the deduplication
                is enabled for POST requests and disabled for other requests.
            *args: The arguments to pass to the function.
            **kwargs: The keyword arguments to pass to the function.

        Returns:
            The result of the request.
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

        transaction_id = request_context.transaction_id

        if deduplicate is None:
            # If not specified, by default, the deduplication is enabled for
            # POST requests and disabled for other requests.
            deduplicate = request_context.request.method == "POST"

        deduplicate = (
            deduplicate and self.deduplicate and request_context.is_cacheable
        )

        async with self.lock:
            if deduplicate and transaction_id in self.transactions:
                # The transaction is still being processed on the same
                # server instance. We just wait for it to complete.
                fut = self.transactions[transaction_id].future
                logger.debug(
                    f"[{request_context.log_request_id}] ENDPOINT STATS - "
                    f"{request_context.log_request} "
                    f"{func.__name__} RESUMED "
                    f"{get_system_metrics_log_str(request_context.request)}"
                )
            else:
                # Start execution in background, use the future to wait for it
                # to complete.
                fut = asyncio.get_event_loop().create_future()
                request_record = RequestRecord(
                    future=fut, request_context=request_context
                )
                if deduplicate:
                    assert transaction_id is not None
                    # Also record the transaction for deduplication.
                    self.transactions[transaction_id] = request_record
                asyncio.create_task(
                    self.async_run_and_cache_result(
                        func,
                        deduplicate,
                        request_record,
                        *args,
                        **kwargs,
                    )
                )

        # Wait for the request to complete; timeout if deduplication is enabled
        try:
            # We take into account the time that has already elapsed since the
            # request was received to avoid keeping the request for too long.
            timeout = max(
                0, self.request_timeout - request_context.process_time
            )
            result = await asyncio.wait_for(
                # We use asyncio.shield to prevent the request from being
                # cancelled when the timeout is reached.
                asyncio.shield(fut),
                timeout=timeout if deduplicate else None,
            )

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
