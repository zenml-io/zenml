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
"""Rate limiting for the ZenML Server."""

import inspect
import time
from collections import defaultdict
from contextlib import contextmanager
from functools import wraps
from typing import (
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Optional,
    TypeVar,
    cast,
)

from starlette.requests import Request

from zenml.logger import get_logger
from zenml.zen_server.utils import server_config

logger = get_logger(__name__)
F = TypeVar("F", bound=Callable[..., Any])


class RequestLimiter:
    """Simple in-memory rate limiter."""

    def __init__(
        self,
        day_limit: Optional[int] = None,
        minute_limit: Optional[int] = None,
    ):
        """Initializes the limiter.

        Args:
            day_limit: The number of requests allowed per day.
            minute_limit: The number of requests allowed per minute.

        Raises:
            ValueError: If both day_limit and minute_limit are None.
        """
        self.limiting_enabled = server_config().rate_limit_enabled
        if not self.limiting_enabled:
            return
        if day_limit is None and minute_limit is None:
            raise ValueError("Pass either day or minuter limits, or both.")
        self.day_limit = day_limit
        self.minute_limit = minute_limit
        self.limiter: Dict[str, List[float]] = defaultdict(list)

    def hit_limiter(self, request: Request) -> None:
        """Increase the number of hits in the limiter.

        Args:
            request: Request object.

        Raises:
            HTTPException: If the request limit is exceeded.
        """
        if not self.limiting_enabled:
            return
        from fastapi import HTTPException

        requester = self._get_ipaddr(request)
        now = time.time()
        minute_ago = now - 60
        day_ago = now - 60 * 60 * 24
        self.limiter[requester].append(now)

        from bisect import bisect_left

        # remove failures older than a day
        older_index = bisect_left(self.limiter[requester], day_ago)
        self.limiter[requester] = self.limiter[requester][older_index:]

        if self.day_limit and len(self.limiter[requester]) > self.day_limit:
            raise HTTPException(
                status_code=429, detail="Daily request limit exceeded."
            )
        minute_requests = len(
            [
                limiter_hit
                for limiter_hit in self.limiter[requester][::-1]
                if limiter_hit >= minute_ago
            ]
        )
        if self.minute_limit and minute_requests > self.minute_limit:
            raise HTTPException(
                status_code=429, detail="Minute request limit exceeded."
            )

    def reset_limiter(self, request: Request) -> None:
        """Resets the limiter on successful request.

        Args:
            request: Request object.
        """
        if self.limiting_enabled:
            requester = self._get_ipaddr(request)
            if requester in self.limiter:
                del self.limiter[requester]

    def _get_ipaddr(self, request: Request) -> str:
        """Returns the IP address for the current request.

        Based on the X-Forwarded-For headers or client information.

        Args:
            request: The request object.

        Returns:
            The ip address for the current request (or 127.0.0.1 if none found).
        """
        if "X_FORWARDED_FOR" in request.headers:
            return request.headers["X_FORWARDED_FOR"]
        else:
            if not request.client or not request.client.host:
                return "127.0.0.1"

            return request.client.host

    @contextmanager
    def limit_failed_requests(
        self, request: Request
    ) -> Generator[None, Any, Any]:
        """Limits the number of failed requests.

        Args:
            request: Request object.

        Yields:
            None
        """
        self.hit_limiter(request)

        yield

        # if request was successful - reset limiter
        self.reset_limiter(request)


def rate_limit_requests(
    day_limit: Optional[int] = None,
    minute_limit: Optional[int] = None,
) -> Callable[..., Any]:
    """Decorator to handle exceptions in the API.

    Args:
        day_limit: Number of requests allowed per day.
        minute_limit: Number of requests allowed per minute.

    Returns:
        Decorated function.
    """
    limiter = RequestLimiter(day_limit=day_limit, minute_limit=minute_limit)

    def decorator(func: F) -> F:
        request_arg, request_kwarg = None, None
        parameters = inspect.signature(func).parameters
        for arg_num, arg_name in enumerate(parameters):
            if parameters[arg_name].annotation == Request:
                request_arg = arg_num
                request_kwarg = arg_name
                break
        if request_arg is None or request_kwarg is None:
            raise ValueError(
                "Rate limiting APIs must have argument of `Request` type."
            )

        @wraps(func)
        def decorated(
            *args: Any,
            **kwargs: Any,
        ) -> Any:
            if request_kwarg in kwargs:
                request = kwargs[request_kwarg]
            else:
                request = args[request_arg]
            with limiter.limit_failed_requests(request):
                return func(*args, **kwargs)

        return cast(F, decorated)

    return decorator
