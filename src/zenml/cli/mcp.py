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
"""Run the ZenML MCP server for the ZenML server you're logged in to."""

import asyncio
import logging
import os
import ssl
import sys
from typing import TYPE_CHECKING, Optional, Union

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.enums import AuthScheme
from zenml.exceptions import AuthorizationException, CredentialsNotValid
from zenml.logger import ZenMLConsoleHandler
from zenml.zen_stores.rest_zen_store import RestZenStore

if TYPE_CHECKING:
    from zenml_mcp.client import ZenMLAuth


@cli.command(
    "mcp",
    help="""Run the ZenML MCP server over stdio.

The server acts as you on the ZenML server you're logged in to, with the
login `zenml login` stored. Add it to an MCP client (Claude Desktop, Claude
Code, Cursor) as the command `zenml mcp`. It needs `pip install
'zenml[mcp]'`.
""",
)
@click.option(
    "--read-only",
    is_flag=True,
    help="Offer only the tools that change nothing.",
)
def mcp(read_only: bool) -> None:
    """Run the ZenML MCP server over stdio.

    Args:
        read_only: Offer only the tools that change nothing.
    """
    try:
        from zenml_mcp.client import ZenMLRestError
    except ImportError:
        cli_utils.error(
            "The ZenML MCP server needs the MCP extra: "
            "pip install 'zenml[mcp]'"
        )
    # stdout carries the MCP protocol, so ZenML's logs go to stderr.
    for handler in logging.getLogger().handlers:
        if isinstance(handler, ZenMLConsoleHandler):
            handler.setStream(sys.stderr)
    try:
        store = Client().zen_store
    except AuthorizationException:
        cli_utils.error(
            "Your ZenML login has expired. Run `zenml login` and start the "
            "MCP server again."
        )
    except Exception as error:
        # The store already retried. Its message can quote the server's
        # answer, so only the error's type is shown.
        cli_utils.error(
            f"Couldn't reach the ZenML server ({type(error).__name__}). "
            "Check that it is running, then start the MCP server again."
        )
    if not isinstance(store, RestZenStore):
        cli_utils.error(
            "The ZenML MCP server reads a ZenML server. Log in to one "
            "first: zenml login <server URL>"
        )
    try:
        asyncio.run(_serve(store, read_only))
    except ZenMLRestError as error:
        cli_utils.error(error.message)


def _verify(store: RestZenStore) -> Union[bool, ssl.SSLContext]:
    """The TLS check the REST store's requests make, for httpx.

    Requests also trusts a CA bundle named by `REQUESTS_CA_BUNDLE` or
    `CURL_CA_BUNDLE` when no other is configured; httpx reads neither.

    Args:
        store: The REST store.

    Returns:
        False, or a context that trusts the CA bundle requests would use.
    """
    verify = store.session.verify
    if verify is True:
        verify = (
            os.environ.get("REQUESTS_CA_BUNDLE")
            or os.environ.get("CURL_CA_BUNDLE")
            or True
        )
    if isinstance(verify, str):
        if os.path.isdir(verify):
            return ssl.create_default_context(capath=verify)
        return ssl.create_default_context(cafile=verify)
    return bool(verify)


async def _serve(store: RestZenStore, read_only: bool) -> None:
    """Serve over stdio until the client disconnects.

    Args:
        store: The REST store, with the stored login.
        read_only: Offer only the tools that change nothing.
    """
    import httpx

    from zenml_mcp.call import ZenMLCall
    from zenml_mcp.client import ZenMLRestClient
    from zenml_mcp.server import build_server, check_server

    async with httpx.AsyncClient(
        verify=_verify(store), timeout=httpx.Timeout(30.0, connect=10.0)
    ) as http:
        client = ZenMLRestClient(
            store.url, _login(store), http=http, cache_key=store.url
        )
        await check_server(client)
        # The CLI points `sys.stdout` at stderr to keep logs out of piped
        # output. The MCP SDK serves the protocol from the real stdout and,
        # while it serves, points file descriptor 1 at stderr, so stray
        # output still misses the protocol.
        sys.stdout = sys.__stdout__
        await build_server(
            ZenMLCall(client, read_only=read_only)
        ).run_stdio_async()


def _sign_in(
    store: RestZenStore, rejected: Optional[str], renew: bool
) -> Optional[str]:
    """A token from the stored login, as the REST store gets one.

    Args:
        store: The REST store.
        rejected: The token ZenML refused, when renewing.
        renew: Whether ZenML refused the last token.

    Returns:
        A token, or None for a server without authentication when there is
        no stored login.

    Raises:
        ZenMLAuthError: When there is no valid login.
        ZenMLUnavailable: When signing in fails otherwise.
    """
    from zenml_mcp.client import ZenMLAuthError, ZenMLUnavailable

    try:
        if not renew:
            return store.get_or_generate_api_token()
        # A newer login, from `zenml login` in another terminal, is used
        # before the stored one is dropped and signed in again.
        store.authenticate()
        token = store.get_or_generate_api_token()
        if token == rejected:
            store.authenticate(force=True)
            token = store.get_or_generate_api_token()
        return token
    except AuthorizationException as error:
        no_auth = store.server_info.auth_scheme == AuthScheme.NO_AUTH
        if isinstance(error, CredentialsNotValid) and not renew and no_auth:
            return None
        raise ZenMLAuthError(
            f"Your ZenML login is missing or has expired. Run `zenml login "
            f"{store.url}` and start the MCP server again."
        ) from None
    except Exception as error:
        # The store's message can quote the server's answer, so only the
        # error's type is passed on.
        raise ZenMLUnavailable(
            f"Signing in to ZenML failed ({type(error).__name__}). "
            "Try again shortly."
        ) from None


def _login(store: RestZenStore) -> "ZenMLAuth":
    """The stored login, as the MCP client's auth.

    Args:
        store: The REST store.

    Returns:
        An auth that signs in and renews as the REST store does.
    """
    from zenml_mcp.client import ZenMLAuth

    class StoredLogin(ZenMLAuth):
        """One sign-in at a time: requests rejected together renew once."""

        def __init__(self) -> None:
            super().__init__()
            self._lock = asyncio.Lock()
            self._current: Optional[str] = None
            self._known = False

        async def token(self) -> Optional[str]:
            async with self._lock:
                if not self._known:
                    self._current = await asyncio.to_thread(
                        _sign_in, store, None, False
                    )
                    self._known = True
                return self._current

        async def renew(self, rejected: Optional[str]) -> str:
            async with self._lock:
                current = self._current
                if self._known and current is not None and current != rejected:
                    # Another request renewed it while this one waited.
                    return current
                self._known = False
                token = await asyncio.to_thread(
                    _sign_in, store, rejected, True
                )
                if token is None:
                    raise RuntimeError("A renewed sign-in gave no token.")
                self._current, self._known = token, True
                return token

    return StoredLogin()
