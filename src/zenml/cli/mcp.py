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
import ssl
import sys
from typing import TYPE_CHECKING, Optional, Union

import click

from zenml.cli import utils as cli_utils
from zenml.cli.cli import cli
from zenml.client import Client
from zenml.exceptions import CredentialsNotValid
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
        import zenml_mcp.server  # noqa: F401
    except ImportError:
        cli_utils.exception(
            ImportError(
                "The ZenML MCP server needs the MCP extra: "
                "pip install 'zenml[mcp]'"
            )
        )
    # stdout carries the MCP protocol, so ZenML's logs go to stderr.
    for handler in logging.getLogger().handlers:
        if isinstance(handler, ZenMLConsoleHandler):
            handler.setStream(sys.stderr)
    store = Client().zen_store
    if not isinstance(store, RestZenStore):
        cli_utils.exception(
            RuntimeError(
                "The ZenML MCP server reads a ZenML server. Log in to one "
                "first: zenml login <server URL>"
            )
        )
    from zenml_mcp.client import ZenMLRestError

    try:
        asyncio.run(_serve(store, read_only))
    except ZenMLRestError as error:
        cli_utils.error(error.message)


def _verify(store: RestZenStore) -> Union[bool, ssl.SSLContext]:
    """The TLS check the REST store makes, for httpx.

    Args:
        store: The REST store.

    Returns:
        False, True, or a context that trusts the configured CA bundle.
    """
    verify = store.session.verify
    if isinstance(verify, str):
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
        # output; the MCP protocol needs the real stdout back.
        sys.stdout = sys.__stdout__
        await build_server(
            ZenMLCall(client, read_only=read_only), read_only=read_only
        ).run_stdio_async()


def _login(store: RestZenStore) -> "ZenMLAuth":
    """The stored login, as the MCP client's auth.

    Args:
        store: The REST store.

    Returns:
        An auth that signs in and renews as the REST store does.
    """
    import requests

    from zenml_mcp.client import (
        ZenMLAuth,
        ZenMLAuthError,
        ZenMLUnavailable,
    )

    def signed_in(force: bool) -> Optional[str]:
        # The store signs in, refreshes and caches tokens as `zenml` does.
        try:
            if force:
                store.authenticate(force=True)
            return store.get_or_generate_api_token()
        except CredentialsNotValid:
            if not force:
                # No stored login: a server without authentication, such
                # as a local one, takes requests unsigned, and any other
                # answers them with a 401 that signs in.
                return None
            raise ZenMLAuthError(
                f"Your ZenML login has expired. Run `zenml login {store.url}` "
                "and start the MCP server again."
            ) from None
        except (requests.ConnectionError, requests.Timeout) as error:
            raise ZenMLUnavailable(
                f"Signing in to ZenML failed ({type(error).__name__}). "
                "Try again shortly."
            ) from None

    class StoredLogin(ZenMLAuth):
        async def token(self) -> Optional[str]:
            return await asyncio.to_thread(signed_in, False)

        async def renew(self, rejected: Optional[str]) -> str:
            token = await asyncio.to_thread(signed_in, True)
            if token is None:
                raise ZenMLAuthError(
                    f"Log in to ZenML first: zenml login {store.url}"
                )
            return token

    return StoredLogin()
