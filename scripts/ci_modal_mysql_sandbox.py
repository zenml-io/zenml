#!/usr/bin/env python3
"""Manage the per-run Modal MySQL CI sandbox."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import os
import secrets
import shlex
import string
import textwrap
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

GITHUB_OUTPUT = os.environ.get("GITHUB_OUTPUT")
DEFAULT_USERNAME = "default"
SERVER_PORT = 8080
START_TIMEOUT_SECONDS = 600
SANDBOX_TIMEOUT_SECONDS = 3600


def _is_sensitive_output_name(name: str) -> bool:
    """Return whether an output name likely carries sensitive data."""
    lowered = name.lower()
    return any(
        token in lowered for token in ("password", "token", "secret", "key")
    )


def _write_output(name: str, value: str) -> None:
    """Write a GitHub Actions output."""
    if not GITHUB_OUTPUT:
        safe_value = (
            "***REDACTED***" if _is_sensitive_output_name(name) else value
        )
        print(f"{name}={safe_value}")
        return
    with Path(GITHUB_OUTPUT).open("a", encoding="utf-8") as output_file:
        output_file.write(f"{name}={value}\n")


def _get_required_env(name: str) -> str:
    """Read a required environment variable."""
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Environment variable {name} is required")
    return value


def _generate_password() -> str:
    """Generate a URL-safe password for internal sandbox services."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(32))


def _password_context() -> str:
    """Return the stable per-run context used to derive the server password."""
    return ":".join(
        [
            _get_required_env("GITHUB_REPOSITORY"),
            os.environ.get("ZENML_CI_CHECKOUT_REF")
            or _get_required_env("GITHUB_SHA"),
            os.environ.get("GITHUB_RUN_ID", "local"),
        ]
    )


def derive_server_password() -> str:
    """Derive the per-run server password without storing it as job output."""
    seed = _get_required_env("MODAL_TOKEN_SECRET").encode("utf-8")
    digest = hmac.new(
        seed, _password_context().encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")[:32]


def _build_server_command(repository: str, checkout_ref: str) -> str:
    """Build the command that runs inside the Modal sandbox."""
    quoted_repository = shlex.quote(repository)
    quoted_checkout_ref = shlex.quote(checkout_ref)
    return textwrap.dedent(
        f"""
        set -euo pipefail

        mkdir -p /workspace
        service mariadb start || service mysql start
        for _ in $(seq 1 60); do
          mysqladmin ping --silent && break
          sleep 1
        done

        mysql -uroot <<SQL
        CREATE DATABASE IF NOT EXISTS zenml;
        CREATE USER IF NOT EXISTS 'zenml'@'%'
          IDENTIFIED BY '${{ZENML_DB_PASSWORD}}';
        CREATE USER IF NOT EXISTS 'zenml'@'localhost'
          IDENTIFIED BY '${{ZENML_DB_PASSWORD}}';
        GRANT ALL PRIVILEGES ON zenml.* TO 'zenml'@'%';
        GRANT ALL PRIVILEGES ON zenml.* TO 'zenml'@'localhost';
        FLUSH PRIVILEGES;
        SQL

        git clone --depth 1 https://github.com/{quoted_repository}.git /workspace/zenml
        cd /workspace/zenml
        git fetch --depth 1 origin {quoted_checkout_ref}
        git checkout FETCH_HEAD

        uv venv /workspace/venv
        . /workspace/venv/bin/activate
        uv pip install -e '.[server]'

        export ZENML_ANALYTICS_OPT_IN=false
        export ZENML_DEBUG=true
        export ZENML_STORE_URL=mysql://zenml:${{ZENML_DB_PASSWORD}}@127.0.0.1/zenml
        export ZENML_SERVER_DEPLOYMENT_TYPE=docker
        export ZENML_SERVER_AUTO_ACTIVATE=True
        export ZENML_SERVER_AUTO_CREATE_DEFAULT_USER=True
        export ZENML_DEFAULT_USER_NAME={DEFAULT_USERNAME}
        export ZENML_DEFAULT_USER_PASSWORD=${{ZENML_DEFAULT_USER_PASSWORD}}
        export AUTO_OPEN_DASHBOARD=false

        uvicorn zenml.zen_server.zen_server_api:app \
          --no-server-header \
          --proxy-headers \
          --forwarded-allow-ips '*' \
          --host 0.0.0.0 \
          --port {SERVER_PORT}
        """
    ).strip()


def _get_modal() -> Any:
    """Import Modal with an actionable error message."""
    try:
        import modal
    except ImportError as exc:
        raise RuntimeError(
            "The 'modal' package is required. Install it with "
            "`python -m pip install --upgrade 'modal>=1.0.0'`."
        ) from exc
    return modal


def _modal_app() -> Any:
    """Return the Modal app used by CI sandboxes."""
    modal = _get_modal()
    return modal.App.lookup("zenml-ci-mysql-sandbox", create_if_missing=True)


def _modal_image() -> Any:
    """Return the Modal image used by CI sandboxes."""
    modal = _get_modal()
    return (
        modal.Image.debian_slim(python_version="3.13")
        .apt_install(
            "default-mysql-server",
            "default-libmysqlclient-dev",
            "build-essential",
            "pkg-config",
            "git",
            "curl",
        )
        .pip_install("uv")
    )


def _create_modal_sandbox(command: str, environment: dict[str, str]) -> Any:
    """Create a Modal sandbox running the ZenML server command."""
    modal = _get_modal()
    image = _modal_image()
    app = _modal_app()

    try:
        return modal.Sandbox.create(
            "bash",
            "-lc",
            command,
            app=app,
            image=image,
            env=environment,
            encrypted_ports=[SERVER_PORT],
            timeout=SANDBOX_TIMEOUT_SECONDS,
        )
    except TypeError as exc:
        raise RuntimeError(
            "This Modal SDK does not support the Sandbox.create arguments used "
            "by the CI sandbox. Please use a Modal version that supports "
            "encrypted_ports on sandboxes."
        ) from exc


def _get_tunnel_url(sandbox: Any) -> str:
    """Wait for Modal to expose the ZenML server tunnel."""
    deadline = time.time() + START_TIMEOUT_SECONDS
    while time.time() < deadline:
        return_code = sandbox.poll()
        if return_code is not None:
            raise RuntimeError(
                f"Modal sandbox exited before becoming ready: {return_code}"
            )

        tunnels = sandbox.tunnels()
        tunnel = tunnels.get(SERVER_PORT) if tunnels else None
        url = getattr(tunnel, "url", None) if tunnel else None
        if url:
            return str(url).rstrip("/")
        time.sleep(5)

    raise RuntimeError("Timed out waiting for Modal sandbox tunnel")


def _wait_until_ready(server_url: str) -> None:
    """Wait until the ZenML server responds to readiness checks."""
    deadline = time.time() + START_TIMEOUT_SECONDS
    ready_url = f"{server_url}/ready"
    last_error: Exception | None = None

    while time.time() < deadline:
        try:
            with urllib.request.urlopen(ready_url, timeout=10) as response:
                if response.status == 200:
                    return
        except (
            ConnectionError,
            OSError,
            urllib.error.URLError,
            TimeoutError,
        ) as exc:
            last_error = exc
        time.sleep(5)

    raise RuntimeError(
        f"Timed out waiting for ZenML server readiness at {ready_url}: "
        f"{last_error}"
    )


def start() -> None:
    """Start the per-run Modal sandbox and emit connection details."""
    if os.environ.get("ZENML_CI_MODAL_DISABLED") == "true":
        _write_output("server_url", "")
        _write_output("server_username", "")
        _write_output("sandbox_id", "")
        return

    repository = _get_required_env("GITHUB_REPOSITORY")
    checkout_ref = os.environ.get(
        "ZENML_CI_CHECKOUT_REF"
    ) or _get_required_env("GITHUB_SHA")
    password = derive_server_password()
    db_password = _generate_password()
    sandbox = _create_modal_sandbox(
        _build_server_command(repository, checkout_ref),
        environment={
            "ZENML_DEFAULT_USER_PASSWORD": password,
            "ZENML_DB_PASSWORD": db_password,
        },
    )
    try:
        server_url = _get_tunnel_url(sandbox)
        _wait_until_ready(server_url)
    except (
        ConnectionError,
        OSError,
        RuntimeError,
        TimeoutError,
        urllib.error.URLError,
    ):
        sandbox.terminate()
        raise

    _write_output("server_url", server_url)
    _write_output("server_username", DEFAULT_USERNAME)
    _write_output("sandbox_id", sandbox.object_id)


def stop(sandbox_id: str) -> None:
    """Stop the per-run Modal sandbox."""
    if not sandbox_id:
        return

    modal = _get_modal()
    sandbox = modal.Sandbox.from_id(sandbox_id)
    sandbox.terminate()


def warm_image() -> None:
    """Build and warm the Modal image used by CI sandboxes."""
    _modal_image().build(app=_modal_app())


def main() -> None:
    """Run the CLI."""
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("start")
    subparsers.add_parser("warm-image")
    stop_parser = subparsers.add_parser("stop")
    stop_parser.add_argument("--sandbox-id", required=True)
    args = parser.parse_args()

    if args.command == "start":
        start()
    elif args.command == "warm-image":
        warm_image()
    elif args.command == "stop":
        stop(args.sandbox_id)


if __name__ == "__main__":
    main()
