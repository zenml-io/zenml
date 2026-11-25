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
"""Tests for ZenML server rate limiting."""

from starlette.requests import Request

from zenml.zen_server.rate_limit import RequestLimiter


def _request(
    headers: list[tuple[bytes, bytes]],
    client: str = "10.0.0.10",
) -> Request:
    """Create a minimal Starlette request for rate limiter tests."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": "/",
            "headers": headers,
            "client": (client, 1234),
        }
    )


def test_get_ipaddr_ignores_raw_x_forwarded_for_header() -> None:
    """The limiter uses the ASGI client host, not raw forwarded headers."""
    limiter = RequestLimiter(day_limit=10)

    request = _request([(b"x-forwarded-for", b"203.0.113.5, 10.0.0.1")])

    assert limiter._get_ipaddr(request) == "10.0.0.10"


def test_get_ipaddr_falls_back_to_client_host() -> None:
    """The limiter falls back to the direct client host."""
    limiter = RequestLimiter(day_limit=10)

    request = _request(headers=[], client="10.0.0.10")

    assert limiter._get_ipaddr(request) == "10.0.0.10"
