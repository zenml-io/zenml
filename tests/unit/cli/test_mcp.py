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
import importlib
import ssl
from types import SimpleNamespace
from typing import Any, List, Optional

import httpx
import pytest
from click.testing import CliRunner

pytest.importorskip("mcp")

from zenml.cli.cli import cli  # noqa: E402
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

    def get_or_generate_api_token(self) -> str:
        if self.failure is not None:
            raise self.failure
        if not self.tokens:
            raise CredentialsNotValid("No valid credentials found.")
        return self.tokens[0]

    def authenticate(self, force: bool = False) -> None:
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
    store = SimpleNamespace(session=session)
    assert isinstance(mcp_cli._verify(store), ssl.SSLContext)  # type: ignore[arg-type]
    assert seen == [{"cafile": str(tmp_path / "ca.pem")}]
    session.verify = False
    assert mcp_cli._verify(store) is False  # type: ignore[arg-type]


def test_an_unreachable_server_stops_the_command_with_a_short_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """No traceback and no server text when the store can't connect."""

    class Unreachable:
        @property
        def zen_store(self) -> Any:
            raise RuntimeError("Error connecting to URL: s3cr3t-echo")

    monkeypatch.setattr(mcp_cli, "Client", Unreachable)
    result = CliRunner().invoke(cli, ["mcp"])
    assert result.exit_code != 0
    assert "Couldn't reach the ZenML server (RuntimeError)" in result.output
    assert "s3cr3t-echo" not in result.output
    assert "Traceback" not in result.output
