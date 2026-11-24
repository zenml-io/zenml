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
"""The ZenML REST client: one caller, one ZenML server, built per tool call.

Signing in and renewing the session belong to the host's `ZenMLAuth`, and the
connections to the host's `httpx.AsyncClient`, so this module only sends
requests:

* A read that gets a 401 renews the session once and resends.
* A write carries an `Idempotency-Key` and is never resent once it may have
  applied. A 401 means the server rejected it first, so that one case renews
  and resends with the same key. A timeout or a dropped connection raises
  `ZenMLOutcomeUnknown` so the caller checks the state instead of repeating it.

A failure is labeled from ZenML's HTTP status, once, in `_raise_for_status`:
its kind names what happened and the message's last sentence the next step.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import AsyncGenerator
from typing import Any

import httpx

API_PREFIX = "/api/v1"


class ZenMLRestError(Exception):
    """A ZenML REST call failed.

    `kind` is a stable, model-facing category and `status` ZenML's HTTP
    status, when ZenML answered. A tool call that raises one answers
    `{"error": {"kind", "message"}}`.
    """

    kind = "error"

    def __init__(self, message: str, *, status: int | None = None) -> None:
        """Record the message and, when ZenML answered, its HTTP status.

        Args:
            message: What failed and, in its last sentence, the next step.
            status: ZenML's HTTP status, or None when ZenML didn't answer.
        """
        super().__init__(message)
        self.message = message
        self.status = status


class ZenMLAuthError(ZenMLRestError):
    """The caller's ZenML session was refused, even after a fresh login.

    A host's `ZenMLAuth` raises it when it can't sign in or renew.
    """

    kind = "unauthenticated"


class ZenMLPermissionDenied(ZenMLRestError):
    """ZenML refused the caller access to what the call asked for."""

    kind = "permission_denied"


class ZenMLNotFound(ZenMLRestError):
    """ZenML has no such entity, or the server has no such route."""

    kind = "not_found"

    def __init__(
        self,
        message: str,
        *,
        route_missing: bool = False,
        status: int | None = None,
    ) -> None:
        """Record the message and whether the route itself is missing.

        Args:
            message: What was not found and the next step.
            route_missing: True when the server has no such route at all.
            status: ZenML's HTTP status, or None when ZenML didn't answer.
        """
        super().__init__(message, status=status)
        # True when the server has no such route at all (an older ZenML
        # version), as opposed to ZenML reporting a missing entity.
        self.route_missing = route_missing


class ZenMLUnsupported(ZenMLRestError):
    """The connected ZenML server or plan does not offer this operation."""

    kind = "unsupported"


class ZenMLRateLimited(ZenMLRestError):
    """ZenML refused the call because the caller sent too many requests."""

    kind = "rate_limited"


class ZenMLBadRequest(ZenMLRestError):
    """ZenML, or this package before sending, refused the call's arguments."""

    kind = "invalid_request"


class ZenMLAlreadyExists(ZenMLRestError):
    """ZenML already has an entity with that name."""

    kind = "already_exists"


# Upstream's error when the SDK can't parse ZenML's answer to a write, though the
# write may have been applied.
UNREADABLE = "Invalid input. Please check the supplied values."


class ZenMLUnavailable(ZenMLRestError):
    """The ZenML server could not be reached or answered with a server error.

    A host's `ZenMLAuth` raises it when the sign-in can't be reached.
    """

    kind = "unavailable"


class ZenMLOutcomeUnknown(ZenMLRestError):
    """A write was sent but its response was lost; it may or may not have applied."""

    kind = "outcome_unknown"


_CREDENTIAL_PREFIX = re.compile(
    r"(?i)(bearer\s+|basic\s+|zenkey_|zenprokey_|kitkey_)[^\s,;\]\}\"']+"
)
_URL_LOGIN = re.compile(r"://[^/\s@]+@")
_SIGN_IN_CODE = re.compile(r"(?i)((?:[?&#]|&amp;)code=)[^\s&#\"'<>,;)\]\}]+")
_CREDENTIAL_FIELD = re.compile(
    r"(?i)([\w.-]*(?:password|passwd|pwd|secret|token|credential|cookie"
    r"|api[_-]?key|access[_-]?key|private[_-]?key)[\w.-]*[\"']?\s*[:=]\s*)"
    r"(?:\"(?:\\.|[^\"\\])*\"?|'(?:\\.|[^'\\])*'?|[^\s,;&\]\}]+)"
)


def mask_credentials(text: str) -> str:
    """Mask what looks like a credential in a server's message.

    Mask first and shorten after: a cut secret would not match.

    Args:
        text: The message, before it reaches a tool result.

    Returns:
        The message with each credential replaced by `***`.
    """
    text = _CREDENTIAL_PREFIX.sub(lambda match: f"{match.group(1)}***", text)
    text = _URL_LOGIN.sub("://***@", text)
    text = _CREDENTIAL_FIELD.sub(lambda match: f"{match.group(1)}***", text)
    return _SIGN_IN_CODE.sub(lambda match: f"{match.group(1)}***", text)


class ZenMLAuth(httpx.Auth):
    """Signs a client's requests in as one caller.

    It sends the caller's token and, on a 401, renews it once and resends the
    same request. A 401 means ZenML applied nothing, so the resend is safe for
    writes too and keeps the request's body and `Idempotency-Key`. A host
    implements `token` and `renew`, and raises `ZenMLAuthError` when the
    caller's sign-in is refused and `ZenMLUnavailable` when it can't be
    reached. A `token` of None sends the requests unsigned, for a server
    that runs without authentication, such as a local one; a 401 then signs
    in.

    One instance serves all of a call's requests, several of them at once,
    so several can be rejected together: `renew` must sign in once for them
    and give the others the new token.
    """

    def __init__(self) -> None:
        """Start with no token: the first request asks for one."""
        self._token: str | None = None
        self._has_token = False
        # The last token ZenML refused even after a renewal: never sent again.
        self._refused: str | None = None

    async def token(self) -> str | None:
        """The caller's current token.

        Returns:
            A token ZenML accepts as a bearer token, or None to send the
            request unsigned.

        Raises:
            NotImplementedError: Unless the host implements it.
        """
        raise NotImplementedError

    async def renew(self, rejected: str | None) -> str:
        """A new token, after ZenML refused `rejected`.

        Args:
            rejected: The token ZenML refused, or None for an unsigned
                request.

        Returns:
            A new token.

        Raises:
            NotImplementedError: Unless the host implements it.
        """
        raise NotImplementedError

    async def async_auth_flow(
        self, request: httpx.Request
    ) -> AsyncGenerator[httpx.Request, httpx.Response]:
        """Send `request` with the token, and once more with a renewed one.

        Args:
            request: The request to sign.

        Yields:
            The signed request, and once more after a 401.
        """  # noqa: DOC201, DOC403
        if not self._has_token:
            token = await self.token()
            if token is not None and token == self._refused:
                token = await self.renew(token)
            self._token, self._has_token = token, True
        token = self._token
        if token is not None:
            request.headers["Authorization"] = f"Bearer {token}"
        response = yield request
        if response.status_code != 401:
            return
        # Free the connection first: the renewal may use the same pool.
        await response.aread()
        # A failed renewal leaves no token, so the next request asks again.
        # A late refusal of an older token leaves a newer one in place.
        if self._token == token:
            self._has_token = False
        renewed = await self.renew(token)
        if renewed == self._refused:
            # Another request's renewal gave a token ZenML already refused.
            renewed = await self.renew(renewed)
        if not self._has_token or self._token == token:
            self._token, self._has_token = renewed, True
        request.headers["Authorization"] = f"Bearer {renewed}"
        response = yield request
        if response.status_code == 401:
            # Refused again: the next request renews instead of resending it.
            self._refused = renewed
            if self._token == renewed:
                self._has_token = False


class BearerToken(ZenMLAuth):
    """A token that never changes, such as a ZenML API key's session."""

    def __init__(self, token: str) -> None:
        """Sign every request in with `token`.

        Args:
            token: The bearer token.
        """
        super().__init__()
        self._fixed = token

    async def token(self) -> str:
        """The fixed token.

        Returns:
            The token.
        """
        return self._fixed

    async def renew(self, rejected: str | None) -> str:
        """Refuse: a fixed token can't be renewed.

        Args:
            rejected: The token ZenML refused.

        Raises:
            ZenMLAuthError: Always.
        """  # noqa: DOC201
        raise ZenMLAuthError(
            "ZenML refused this server's token. Sign in to ZenML again."
        )


def _error_detail(response: httpx.Response) -> str:
    """Pull ZenML's error message out of a response without echoing bodies.

    The message goes into a tool result, so credentials are masked first.
    ZenML answers `{"detail": ["ExceptionType", "message"]}`; request-body
    validation errors are a bare `["ExceptionType", "message"]` list; FastAPI
    validation errors are `{"detail": [{"msg": ..., "loc": ...}]}`.

    Args:
        response: ZenML's error response.

    Returns:
        The masked message, at most 500 characters, or the HTTP reason when
        the body has none.
    """
    try:
        body = response.json()
    except ValueError:
        return response.reason_phrase or f"HTTP {response.status_code}"
    detail = body.get("detail") if isinstance(body, dict) else body
    if isinstance(detail, list) and detail:
        parts = [
            str(item.get("msg") or "") if isinstance(item, dict) else str(item)
            for item in detail
        ]
        return mask_credentials(": ".join(p for p in parts if p))[:500]
    if isinstance(detail, str):
        return mask_credentials(detail)[:500]
    return response.reason_phrase or f"HTTP {response.status_code}"


_TRY_AGAIN = "Try again shortly."


def _sentence(text: str) -> str:
    text = text.strip()
    return text if text.endswith((".", "!", "?")) else f"{text}."


def _raise_for_status(response: httpx.Response, what: str) -> None:
    status = response.status_code
    if status < 400:
        return
    detail = _error_detail(response)
    reason = _sentence(f"{what} failed: {detail}")
    if status == 401:
        raise ZenMLAuthError(
            f"{reason} Sign in to this server again.", status=status
        )
    if status == 402:
        raise ZenMLUnsupported(
            f"{what} failed: this ZenML plan doesn't include it.",
            status=status,
        )
    if status == 403:
        raise ZenMLPermissionDenied(
            f"{reason} If this is about access, ask a workspace admin for it; "
            "signing in again won't help.",
            status=status,
        )
    if status == 404:
        route_missing = detail == "Not Found"
        raise ZenMLNotFound(
            f"{reason} This workspace's ZenML version doesn't support it."
            if route_missing
            else f"{reason} Check the name or id, for example with a list tool.",
            route_missing=route_missing,
            status=status,
        )
    if status in {405, 501}:
        raise ZenMLUnsupported(
            f"{reason} This workspace's ZenML version doesn't support it.",
            status=status,
        )
    if status == 409:
        raise ZenMLAlreadyExists(
            f"{reason} Choose another name, or update the existing one.",
            status=status,
        )
    if status == 429:
        raise ZenMLRateLimited(
            f"{reason} Wait a minute and try again.", status=status
        )
    if status < 500 and status != 408:
        raise ZenMLBadRequest(
            f"{reason} Fix the arguments and try again.", status=status
        )
    if detail in ("", response.reason_phrase or f"HTTP {status}"):
        raise ZenMLUnavailable(f"{reason} {_TRY_AGAIN}", status=status)
    raise ZenMLUnavailable(
        f"{reason} If ZenML's reason doesn't say what to change, try again shortly.",
        status=status,
    )


def page_of(answer: Any) -> dict[str, Any]:
    """A ZenML page, read so that a server newer or older than this one still reads.

    Fields it doesn't know are ignored, and a missing count is taken from the
    items. Without a list of items there is nothing to read.

    Args:
        answer: ZenML's answer to a list request.

    Returns:
        The page's `items`, `total`, `index` and `total_pages`.

    Raises:
        ZenMLUnavailable: If the answer has no list of items.
    """
    items = answer.get("items") if isinstance(answer, dict) else None
    if not isinstance(items, list):
        raise ZenMLUnavailable(
            "The workspace answered a list request in a shape this server can't read."
        )

    def number(key: str, default: int) -> int:
        value = answer.get(key)
        return value if isinstance(value, int) else default

    return {
        "items": items,
        "total": number("total", len(items)),
        "index": number("index", 1),
        "total_pages": number("total_pages", 1),
    }


class ZenMLRestClient:
    """Calls one ZenML server as one caller.

    Build one per tool call. `cache_key` names the caller and the server
    together, so that what this package caches per user (the default
    project, project names) is never read by another caller: a host that
    serves several users must give each its own. `http` is shared and owns
    the connections; it must not keep cookies, since one client's session
    would then reach another caller.
    """

    def __init__(
        self,
        server_url: str,
        auth: ZenMLAuth,
        *,
        http: httpx.AsyncClient,
        cache_key: str,
    ) -> None:
        """Call `server_url` as the caller `auth` signs in.

        Args:
            server_url: The ZenML server's URL, without `/api/v1`.
            auth: Signs each request in as the caller.
            http: The client that sends the requests.
            cache_key: Names the caller and the server, for per-user caches.
        """
        self.server_url = server_url.rstrip("/")
        self.auth = auth
        self.http = http
        self.cache_key = cache_key

    def url(self, path: str) -> str:
        """The URL of an API path.

        Args:
            path: The path under `/api/v1`.

        Returns:
            The full URL.
        """
        return f"{self.server_url}{API_PREFIX}{path}"

    async def _send(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | None,
        json: Any,
        what: str,
        idempotency_key: str | None = None,
    ) -> httpx.Response:
        headers = {"Source-Context": "api"}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        try:
            response = await self.http.request(
                method,
                self.url(path),
                params={k: v for k, v in params.items() if v is not None}
                if params
                else None,
                json=json,
                headers=headers,
                auth=self.auth,
            )
        except httpx.TimeoutException as error:
            # A connection that timed out never carried the request.
            if method != "GET" and not isinstance(error, httpx.ConnectTimeout):
                raise ZenMLOutcomeUnknown(
                    f"{what}: the request was sent but ZenML did not answer in "
                    "time. It may or may not have been applied; check its "
                    "current state before trying again."
                ) from error
            raise ZenMLUnavailable(
                f"{what}: ZenML did not answer in time. {_TRY_AGAIN}"
            ) from error
        except httpx.HTTPError as error:
            if method != "GET" and not isinstance(error, httpx.ConnectError):
                raise ZenMLOutcomeUnknown(
                    f"{what}: the connection failed after the request was "
                    "sent. Check the current state before trying again."
                ) from error
            raise ZenMLUnavailable(
                f"{what}: could not reach the ZenML server "
                f"({type(error).__name__}). {_TRY_AGAIN}"
            ) from error
        _raise_for_status(response, what)
        return response

    async def get(
        self, path: str, *, params: dict[str, Any] | None = None, what: str
    ) -> Any:
        """GET a path, resent once after a 401 by the client's auth.

        Args:
            path: The path under `/api/v1`.
            params: Query parameters; ones that are None are left out.
            what: What the call does, to start an error's message.

        Returns:
            ZenML's answer, parsed from JSON.
        """
        response = await self._send(
            "GET", path, params=params, json=None, what=what
        )
        return response.json()

    async def page(
        self, path: str, *, params: dict[str, Any] | None = None, what: str
    ) -> dict[str, Any]:
        """A list answer, read with `page_of`.

        Args:
            path: The path under `/api/v1`.
            params: Query parameters; ones that are None are left out.
            what: What the call does, to start an error's message.

        Returns:
            The page, as `page_of` reads it.
        """
        return page_of(await self.get(path, params=params, what=what))

    async def write(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        what: str,
    ) -> Any:
        """POST/PUT/PATCH/DELETE, never repeated once it may have applied.

        Args:
            method: The HTTP method.
            path: The path under `/api/v1`.
            json: The request body.
            params: Query parameters; ones that are None are left out.
            what: What the call does, to start an error's message.

        Returns:
            ZenML's answer parsed from JSON, its text when it isn't JSON, or
            None when it is empty.
        """
        # ZenML de-duplicates writes that carry the same UUID Idempotency-Key.
        response = await self._send(
            method,
            path,
            params=params,
            json=json,
            what=what,
            idempotency_key=str(uuid.uuid4()),
        )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError:
            return response.text
