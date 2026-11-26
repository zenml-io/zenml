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
"""`zenml mcp`: its stored login, its TLS settings and its start-up."""

import asyncio
import gc
import importlib
import ssl
import sys
import threading
from types import SimpleNamespace
from typing import Any, List, Optional, Tuple

import anyio
import httpx
import pytest
import requests
from click.testing import CliRunner

pytest.importorskip("mcp")

from zenml.cli.cli import cli  # noqa: E402
from zenml.constants import ENV_ZENML_ACTIVE_PROJECT_ID  # noqa: E402
from zenml.enums import AuthScheme  # noqa: E402
from zenml.exceptions import (  # noqa: E402
    AuthorizationException,
    CredentialsNotValid,
)
from zenml_mcp.client import (  # noqa: E402
    ZenMLAuthError,
    ZenMLRestClient,
    ZenMLUnavailable,
)

# `zenml.cli` exports the command under the module's name.
mcp_cli = importlib.import_module("zenml.cli.mcp")


class _Store:
    """The REST store calls the stored login makes, with a fake server."""

    url = "https://zenml.example"

    def __init__(
        self,
        tokens: Optional[List[str]] = None,
        scheme: AuthScheme = AuthScheme.OAUTH2_PASSWORD_BEARER,
        failure: Optional[Exception] = None,
    ) -> None:
        self.tokens = list(tokens or [])
        self.server_info = SimpleNamespace(auth_scheme=scheme)
        self.failure = failure
        self.forced = 0
        self.signed_in = 0

    def get_or_generate_api_token(self) -> str:
        if self.failure is not None:
            raise self.failure
        if not self.tokens:
            raise CredentialsNotValid("No valid credentials found.")
        return self.tokens[0]

    def authenticate(self, force: bool = False) -> None:
        self.signed_in += 1
        if force:
            self.forced += 1
            self.tokens.pop(0)


def _get(store: _Store, answer: Any, requests: int = 1) -> List[Any]:
    """Send `requests` reads at once through the stored login.

    Args:
        store: The fake store.
        answer: Answers each request.
        requests: How many reads to send together.

    Returns:
        Each read's answer, or the exception it raised.
    """

    async def run() -> List[Any]:
        transport = httpx.MockTransport(answer)
        async with httpx.AsyncClient(transport=transport) as http:
            client = ZenMLRestClient(
                store.url,
                mcp_cli._login(store),  # type: ignore[arg-type]
                http=http,
                cache_key="k",
            )
            reads = [
                client.get("/info", what="Reading") for _ in range(requests)
            ]
            return await asyncio.gather(*reads, return_exceptions=True)

    return asyncio.run(run())


def test_requests_rejected_together_sign_in_once() -> None:
    """Four reads that all meet an expired token renew it once."""
    store = _Store(tokens=["old", "new"])

    def answer(request: httpx.Request) -> httpx.Response:
        if request.headers["Authorization"] == "Bearer old":
            return httpx.Response(401, json={"detail": "expired"})
        return httpx.Response(200, json={"ok": True})

    assert _get(store, answer, requests=4) == [{"ok": True}] * 4
    assert store.forced == 1


def test_a_server_without_authentication_gets_unsigned_requests() -> None:
    """With no stored login, a local server without auth is still read."""
    store = _Store(scheme=AuthScheme.NO_AUTH)
    sent: List[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={"ok": True})

    assert _get(store, answer, requests=3) == [{"ok": True}] * 3
    assert all("Authorization" not in request.headers for request in sent)


def test_a_missing_login_fails_before_anything_is_sent() -> None:
    """An authenticated server without a stored login asks for one."""
    sent: List[httpx.Request] = []

    def answer(request: httpx.Request) -> httpx.Response:
        sent.append(request)
        return httpx.Response(200, json={})

    (error,) = _get(_Store(), answer)
    assert isinstance(error, ZenMLAuthError)
    assert "zenml login https://zenml.example" in error.message
    assert sent == []


@pytest.mark.parametrize(
    ("failure", "kind"),
    [
        (AuthorizationException("Pro session expired"), ZenMLAuthError),
        (
            RuntimeError("500 HTTP Error received from server: s3cr3t-echo"),
            ZenMLUnavailable,
        ),
    ],
)
def test_a_failed_sign_in_is_typed_and_keeps_the_servers_text_out(
    failure: Exception, kind: type
) -> None:
    """Any sign-in failure is a refusal or an outage, without the server's text.

    Args:
        failure: What the store raises.
        kind: The error the tool call gets.
    """
    (error,) = _get(
        _Store(failure=failure), lambda _: httpx.Response(200, json={})
    )
    assert isinstance(error, kind)
    assert "s3cr3t-echo" not in error.message


def test_tls_trusts_the_ca_bundle_requests_would_use(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    """`REQUESTS_CA_BUNDLE` reaches the MCP server's client too."""
    seen: List[Any] = []
    monkeypatch.setattr(
        ssl,
        "create_default_context",
        lambda **kwargs: seen.append(kwargs) or ssl.SSLContext(),
    )
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", str(tmp_path / "ca.pem"))
    session = SimpleNamespace(verify=True)
    store = SimpleNamespace(session=session, url="https://zenml.example")
    assert isinstance(mcp_cli._verify(store), ssl.SSLContext)  # type: ignore[arg-type]
    assert seen == [{"cafile": str(tmp_path / "ca.pem")}]
    session.verify = False
    assert mcp_cli._verify(store) is False  # type: ignore[arg-type]


def _start(
    monkeypatch: pytest.MonkeyPatch, failures: List[Exception]
) -> Tuple[Any, int]:
    """Run `zenml mcp` with a store whose first reads fail as given.

    Args:
        monkeypatch: Replaces the client and the retry's wait.
        failures: What each attempt to build the store raises, in order.

    Returns:
        The command's result and how many times the store was built.
    """
    attempts = []

    class Failing:
        @property
        def zen_store(self) -> Any:
            attempts.append(1)
            raise failures[len(attempts) - 1]

    monkeypatch.setattr(mcp_cli, "Client", Failing)
    monkeypatch.setattr("zenml_mcp.server.START_RETRY_DELAY_S", 0.0)
    return CliRunner().invoke(cli, ["mcp"]), len(attempts)


def _wrapped(cause: Exception) -> RuntimeError:
    """The store's error for a failed first read, as it raises it.

    Args:
        cause: What the read raised.

    Returns:
        The store's error, caused by `cause`.
    """
    try:
        raise RuntimeError("Error connecting to URL: s3cr3t-echo") from cause
    except RuntimeError as error:
        return error


def test_a_stalled_first_read_is_retried_once_then_reported_briefly(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """zenml-io/mcp-zenml#96, then a short error without the server's text."""
    stall = _wrapped(requests.exceptions.ReadTimeout("body stalled"))
    result, attempts = _start(monkeypatch, [stall, stall])
    assert attempts == 2
    assert result.exit_code != 0
    assert "Couldn't reach the ZenML server (RuntimeError)" in result.output
    assert "s3cr3t-echo" not in result.output
    assert "Traceback" not in result.output


def test_an_answered_failure_is_not_retried(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A server that answered with an error isn't stalled: no retry."""
    answered = _wrapped(requests.HTTPError("500 Server Error"))
    result, attempts = _start(monkeypatch, [answered])
    assert attempts == 1
    assert "Connecting to the ZenML server failed" in result.output
    assert "s3cr3t-echo" not in result.output


def test_a_cancelled_renewal_keeps_one_sign_in_at_a_time() -> None:
    """The lock stays held until the sign-in thread ends, cancelled or not."""
    release = threading.Event()
    running: List[int] = []
    peak: List[int] = []

    class Slow(_Store):
        def authenticate(self, force: bool = False) -> None:
            running.append(1)
            peak.append(len(running))
            release.wait(5)
            super().authenticate(force)
            running.pop()

    store = Slow(tokens=["old", "new", "newer"])

    async def run() -> None:
        auth = mcp_cli._login(store)  # type: ignore[arg-type]
        first = asyncio.ensure_future(auth.renew("old"))
        await asyncio.sleep(0.05)
        first.cancel()
        second = asyncio.ensure_future(auth.renew("old"))
        await asyncio.sleep(0.05)
        release.set()
        with pytest.raises(asyncio.CancelledError):
            await first
        await second

    asyncio.run(run())
    assert max(peak) == 1


def test_requests_rejected_together_share_a_failed_renewal() -> None:
    """One failed sign-in answers every request that waited on it."""
    store = _Store(tokens=["old"])

    def answer(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"detail": "expired"})

    errors = _get(store, answer, requests=4)
    assert all(isinstance(error, ZenMLAuthError) for error in errors)
    # One renewal: a re-read of the stored login, then a forced sign-in.
    assert store.signed_in == 2


def test_a_failed_renewal_is_tried_again_by_a_later_call() -> None:
    """A renewal that failed once doesn't fail every later call with it."""

    class Flaky(_Store):
        def authenticate(self, force: bool = False) -> None:
            if self.signed_in == 0:
                self.signed_in += 1
                raise requests.ConnectionError("down for a moment")
            super().authenticate(force)

    store = Flaky(tokens=["old", "new"])

    def answer(request: httpx.Request) -> httpx.Response:
        if request.headers["Authorization"] == "Bearer old":
            return httpx.Response(401, json={"detail": "expired"})
        return httpx.Response(200, json={"ok": True})

    async def run() -> List[Any]:
        transport = httpx.MockTransport(answer)
        async with httpx.AsyncClient(transport=transport) as http:
            client = ZenMLRestClient(
                store.url,
                mcp_cli._login(store),  # type: ignore[arg-type]
                http=http,
                cache_key="k",
            )
            reads: List[Any] = []
            for _ in range(2):
                try:
                    reads.append(await client.get("/info", what="Reading"))
                except ZenMLUnavailable as error:
                    reads.append(error)
            return reads

    first, second = asyncio.run(run())
    assert isinstance(first, ZenMLUnavailable)
    assert second == {"ok": True}


def test_a_renewal_is_shared_across_a_rejection_of_another_token() -> None:
    """Requests rejected with one token share its renewal, a failure too.

    A rejection of an older token in between doesn't split it: the second
    request rejected with B waits on B's renewal instead of signing in again.
    """
    release = threading.Event()
    forced: List[str] = []

    class Overlapping(_Store):
        active = "B"

        def get_or_generate_api_token(self) -> str:
            return self.active

        def authenticate(self, force: bool = False) -> None:
            if not force:
                return
            forced.append(self.active)
            if len(forced) == 1:
                release.wait(5)
                raise requests.ConnectionError("down for a moment")
            self.active = "C"

    async def run() -> List[Any]:
        auth = mcp_cli._login(Overlapping())  # type: ignore[arg-type]
        first = asyncio.ensure_future(auth.renew("B"))
        await asyncio.sleep(0)
        older = asyncio.ensure_future(auth.renew("A"))
        await asyncio.sleep(0)
        second = asyncio.ensure_future(auth.renew("B"))
        await asyncio.sleep(0)
        release.set()
        return await asyncio.gather(
            first, older, second, return_exceptions=True
        )

    first, _, second = asyncio.run(run())
    assert isinstance(first, ZenMLUnavailable)
    assert isinstance(second, ZenMLUnavailable)
    assert forced == ["B"]


def test_a_renewal_no_request_waits_for_fails_without_a_report() -> None:
    """A renewal whose requests were all cancelled leaves no unread error."""
    release = threading.Event()
    reports: List[str] = []

    class Failing(_Store):
        def authenticate(self, force: bool = False) -> None:
            if force:
                release.wait(5)
                raise requests.ConnectionError("down for a moment")

    async def run() -> None:
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(
            lambda _, context: reports.append(context["message"])
        )
        auth = mcp_cli._login(Failing(tokens=["old"]))  # type: ignore[arg-type]
        waiter = asyncio.ensure_future(auth.renew("old"))
        await asyncio.sleep(0)
        (renewal,) = [
            task
            for task in asyncio.all_tasks()
            if task.get_coro().__qualname__.endswith("._renewed")
        ]
        waiter.cancel()
        with pytest.raises(asyncio.CancelledError):
            await waiter
        release.set()
        await asyncio.wait({renewal})
        del renewal, waiter
        gc.collect()

    asyncio.run(run())
    assert reports == []


def test_a_token_refused_after_renewal_is_not_sent_again() -> None:
    """The next call renews instead of resending the refused token."""
    store = _Store(tokens=["old", "new", "newer"])
    sent: List[str] = []

    def answer(request: httpx.Request) -> httpx.Response:
        token = request.headers["Authorization"].removeprefix("Bearer ")
        sent.append(token)
        if token == "newer":
            return httpx.Response(200, json={"ok": True})
        return httpx.Response(401, json={"detail": "refused"})

    async def run() -> List[Any]:
        transport = httpx.MockTransport(answer)
        async with httpx.AsyncClient(transport=transport) as http:
            client = ZenMLRestClient(
                store.url,
                mcp_cli._login(store),  # type: ignore[arg-type]
                http=http,
                cache_key="k",
            )
            reads = []
            for _ in range(2):
                try:
                    reads.append(await client.get("/info", what="Reading"))
                except ZenMLAuthError as error:
                    reads.append(error)
            return reads

    first, second = asyncio.run(run())
    assert isinstance(first, ZenMLAuthError) and second == {"ok": True}
    assert sent == ["old", "new", "newer"]


def test_a_missing_mcp_sdk_shows_the_install_hint(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Without the extra, the command says how to install it."""
    monkeypatch.setitem(sys.modules, "zenml_mcp.server", None)
    result = CliRunner().invoke(cli, ["mcp"])
    assert result.exit_code != 0
    assert "pip install 'zenml[mcp]'" in result.output
    assert "Traceback" not in result.output


def test_a_ca_bundle_variable_is_ignored_for_an_http_server(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Requests ignores it there, so a stale one must not stop the command."""
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/nonexistent/ca.pem")
    store = SimpleNamespace(
        session=SimpleNamespace(verify=True), url="http://127.0.0.1:8237"
    )
    assert mcp_cli._verify(store) is True  # type: ignore[arg-type]


def test_an_expired_login_shows_on_the_next_token_read() -> None:
    """The stored login is asked each time, so a diagnosis sees expiry."""
    store = _Store(tokens=["t1"])

    async def read_twice() -> Any:
        auth = mcp_cli._login(store)  # type: ignore[arg-type]
        assert await auth.token() == "t1"
        store.tokens.clear()
        with pytest.raises(ZenMLAuthError):
            await auth.token()

    asyncio.run(read_twice())


def test_a_refused_connection_is_not_retried_again(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The store already retried connecting; only a stall gets one more."""
    refused = _wrapped(requests.ConnectionError("connection refused"))
    result, attempts = _start(monkeypatch, [refused])
    assert attempts == 1
    assert "Couldn't reach the ZenML server (RuntimeError)" in result.output


def test_a_renewal_cancelled_by_its_task_group_waits_without_spinning(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """anyio repeats a cancellation; the wait for the sign-in holds it off."""
    release = threading.Event()

    class Slow(_Store):
        def authenticate(self, force: bool = False) -> None:
            release.wait(5)
            super().authenticate(force)

    waits: List[int] = []
    wait = asyncio.wait

    async def counted(*args: Any, **kwargs: Any) -> Any:
        waits.append(1)
        return await wait(*args, **kwargs)

    monkeypatch.setattr(asyncio, "wait", counted)
    store = Slow(tokens=["old", "new"])

    async def run() -> None:
        auth = mcp_cli._login(store)  # type: ignore[arg-type]
        threading.Timer(0.3, release.set).start()
        with anyio.move_on_after(0.05):
            await auth.renew("old")

    asyncio.run(run())
    assert release.is_set()
    assert len(waits) <= 2


def _served(
    monkeypatch: pytest.MonkeyPatch,
    *arguments: str,
    active: Optional[str] = None,
    variable: Optional[str] = None,
) -> Any:
    """The `ZenMLCall` that `zenml mcp` serves with, without stdio or a server.

    Args:
        monkeypatch: Replaces the client, the store, the start-up check and
            the server.
        *arguments: The command's options.
        active: The project `zenml project set` chose, if any.
        variable: The `ZENML_ACTIVE_PROJECT_ID` set, if any; a lookup of it
            fails as a server error does.

    Returns:
        The call the server was built with.
    """
    built: List[Any] = []

    class Configured:
        @property
        def active_project(self) -> Any:
            if variable is not None:
                raise RuntimeError("500 Server Error: upstream unavailable")
            if active is None:
                raise RuntimeError("No active project is configured.")
            return SimpleNamespace(id=active)

    class Served:
        async def run_stdio_async(self) -> None:
            return None

    async def checked(client: Any) -> Any:
        return {}

    def build(call: Any) -> Served:
        built.append(call)
        return Served()

    store = SimpleNamespace(
        url="http://127.0.0.1:8237", session=SimpleNamespace(verify=True)
    )
    monkeypatch.setattr(mcp_cli, "Client", Configured)
    if variable is None:
        monkeypatch.delenv(ENV_ZENML_ACTIVE_PROJECT_ID, raising=False)
    else:
        monkeypatch.setenv(ENV_ZENML_ACTIVE_PROJECT_ID, variable)
    monkeypatch.setattr(mcp_cli, "_connected_store", lambda delay: store)
    monkeypatch.setattr("zenml_mcp.server.check_server", checked)
    monkeypatch.setattr("zenml_mcp.server.build_server", build)
    result = CliRunner().invoke(cli, ["mcp", *arguments])
    assert result.exit_code == 0, result.output
    return built[0]


def test_read_only_reaches_the_call_the_server_runs_with(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`--read-only` makes every tool call read-only, not only the listing."""
    assert _served(monkeypatch, "--read-only").read_only is True
    assert _served(monkeypatch).read_only is False


def test_the_active_project_scopes_the_calls_that_name_none(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`zenml project set` picks the project, else the server's default."""
    chosen = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    assert _served(monkeypatch, active=chosen).client.project == chosen
    assert _served(monkeypatch).client.project is None


def test_a_project_set_in_the_environment_is_used_without_a_lookup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A lookup that fails can't switch the server to another project.

    The project is passed as set; a call that uses a project ZenML can't
    find then fails with a typed error.
    """
    chosen = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    assert _served(monkeypatch, variable=chosen).client.project == chosen
