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
"""mcp-zenml's `diagnose_zenml_setup`, ported as `zenml_diagnose_zenml_setup`.

It is ported from mcp-zenml `3de0643` in its own shape. Upstream checks its own process: environment variables, its Python and ZenML,
then the server's reachability and a fresh login with its API key. Here the
same reachability probes go to the call's server, and the sign-in is the
caller's own, through the client's `ZenMLAuth`, so a model calling this in a
loop sends no login its host would not send anyway. The keys about upstream's
own process are left out, and so are the issues only they raise.
"""

from __future__ import annotations

import ssl
from typing import Any
from urllib.parse import urlsplit

import httpx

from zenml_mcp.call import ZenMLCall
from zenml_mcp.client import ZenMLAuthError, ZenMLRestError, ZenMLUnavailable
from zenml_mcp.common import read_tool
from zenml_mcp.registry import Tools

# Upstream's probe timeouts: (connect, read).
_PROBE_TIMEOUT = httpx.Timeout(2.5, connect=1.0)
# Upstream's issues for a failed sign-in, by its `failure_kind`.
_SIGN_IN_ISSUES = {
    "rejected": (
        "authentication_failed",
        "ZenML authentication failed. Check ZENML_STORE_API_KEY.",
    ),
    "server_error": (
        "authentication_server_error",
        "The ZenML authentication endpoint returned a server error.",
    ),
    "unreachable": (
        "authentication_unreachable",
        "Could not validate ZenML credentials because the authentication "
        "endpoint was unavailable.",
    ),
}


def _untrusted(error: BaseException) -> bool:
    """Whether a probe failed on the server's certificate.

    Upstream's `requests` raises `SSLError`; httpx raises a `ConnectError`
    caused by ssl's error.

    Args:
        error: The error the probe raised.

    Returns:
        True when an ssl error is in its chain of causes.
    """
    seen: BaseException | None = error
    while seen is not None:
        if isinstance(seen, ssl.SSLError):
            return True
        seen = seen.__cause__ or seen.__context__
    return False


def _redacted(url: str) -> str:
    """Upstream's `_redact_url`: scheme and host only.

    Args:
        url: The probed URL.

    Returns:
        Its scheme and host, its host alone, or `<invalid-url>`.
    """
    try:
        parts = urlsplit(url)
        if parts.scheme and parts.hostname:
            return f"{parts.scheme}://{parts.hostname}"
        return parts.hostname or "<invalid-url>"
    except ValueError:
        return "<invalid-url>"


def register(tools: Tools) -> None:
    """Register the setup diagnosis tool.

    Args:
        tools: The registry the tool is added to.
    """

    @read_tool(tools, None)
    async def zenml_diagnose_zenml_setup(call: ZenMLCall) -> dict[str, Any]:
        """Diagnose your access to a ZenML workspace (connectivity, sign-in,
        server version).

        Returns structured diagnostics: whether this server reaches the
        workspace, which ZenML version it runs, and whether your sign-in there
        works.
        """  # noqa: D205, DOC101, DOC103, DOC201
        client = call.client
        checks: dict[str, Any] = {}
        connectivity: dict[str, Any] = {"attempted": True}
        untrusted = False
        for path in ("/api/v1/info", "/health"):
            url = f"{client.server_url}{path}"
            try:
                response = await client.http.get(url, timeout=_PROBE_TIMEOUT)
            except httpx.HTTPError as error:
                untrusted = _untrusted(error)
                connectivity.update(
                    {"ok": False, "last_error_type": type(error).__name__}
                )
                continue
            connectivity.update(
                {
                    "url": _redacted(url),
                    "status_code": response.status_code,
                    "ok": response.status_code in (200, 204),
                }
            )
            if response.status_code == 200 and path == "/api/v1/info":
                try:
                    info = response.json()
                except ValueError:
                    info = None
                if isinstance(info, dict) and "version" in info:
                    checks["zenml_server_version"] = info["version"]
            break
        checks["connectivity"] = connectivity

        authentication: dict[str, Any] = {"attempted": True}
        try:
            await client.auth.token()
            authentication["ok"] = True
        except ZenMLAuthError:
            authentication.update({"ok": False, "failure_kind": "rejected"})
        except ZenMLUnavailable:
            authentication.update({"ok": False, "failure_kind": "unreachable"})
        except ZenMLRestError:
            authentication.update(
                {"ok": False, "failure_kind": "server_error"}
            )
        checks["authentication"] = authentication

        issues: list[dict[str, Any]] = []
        failure = authentication.get("failure_kind")
        if failure in _SIGN_IN_ISSUES:
            code, message = _SIGN_IN_ISSUES[failure]
            issues.append(
                {"severity": "error", "code": code, "message": message}
            )
        if connectivity.get("ok") is False:
            issues.append(
                {
                    "severity": "warning",
                    "code": "unreachable",
                    "message": "Could not reach ZenML server.",
                }
            )
        if untrusted:
            issues.append(
                {
                    "severity": "error",
                    "code": "tls_verification_failed",
                    "message": (
                        "The ZenML server's TLS certificate could not be verified. "
                        "For a private CA, set ZENML_STORE_VERIFY_SSL to the path of "
                        "its CA bundle."
                    ),
                }
            )
        ok = not any(issue["severity"] == "error" for issue in issues)
        return {"ok": ok, "issues": issues, "checks": checks}
