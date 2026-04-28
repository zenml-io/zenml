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
"""Shared helpers for Modal-hosted test deployments.

The two Modal deployment classes (MySQL and MariaDB variants) share
everything except the upstream database image tag. This module owns the
pieces that would otherwise drift between them: credentials validation,
Modal image construction, server-ready polling, and filesystem locations.
"""

import logging
import os
import time
from pathlib import Path
from typing import TYPE_CHECKING, Dict

import requests

if TYPE_CHECKING:
    import modal  # type: ignore[import-not-found]

HARNESS_DEPLOYMENT_DIR = Path(__file__).parent
REPO_ROOT = HARNESS_DEPLOYMENT_DIR.parents[2]
ENTRYPOINT_SCRIPT_PATH = HARNESS_DEPLOYMENT_DIR / "_modal_server_entrypoint.sh"

# Exposed HTTPS port on the sandbox. ZenML's FastAPI app listens here
# inside the container; Modal tunnels it out via `encrypted_ports`.
ZENML_SERVER_PORT = 8080

# Upper bound for waiting on the Modal image build + sandbox boot + DB
# init + server first response. First build from scratch on a cold Modal
# cache can take several minutes; subsequent builds on a warm cache are
# ~30s.
DEFAULT_SERVER_READY_TIMEOUT_SECS = 600

# Files under the repo that would bloat the Modal image build context and
# don't belong inside the server sandbox. Mirrors `.dockerignore` intent
# without needing to parse it.
_IMAGE_IGNORE_PATTERNS = (
    ".git",
    ".venv",
    "venv",
    "node_modules",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".offload-image-cache",
    "test-results",
    "tests/harness/runtime",
    "docs/book",
    "examples",
)


def check_modal_credentials() -> None:
    """Verify that Modal API credentials are available.

    Modal auth falls back to ``~/.modal.toml`` if these env vars are
    missing, but in CI we exclusively use env-based auth and we want a
    fast, clear failure if the secrets weren't wired in.

    Raises:
        RuntimeError: If ``MODAL_TOKEN_ID`` or ``MODAL_TOKEN_SECRET`` is
            missing.
    """
    missing = [
        name
        for name in ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET")
        if not os.environ.get(name)
    ]
    if missing:
        raise RuntimeError(
            "Missing Modal credentials: "
            + ", ".join(missing)
            + ". Set these environment variables (or add them as GitHub "
            "Actions secrets) before using the Modal test deployments."
        )


def build_server_image(
    db_image: str,
    python_version: str,
    db_env: Dict[str, str],
) -> "modal.Image":
    """Build a Modal image layering the ZenML server atop a DB base image.

    The base image is taken from a public registry (for example
    ``mysql:8.0`` or ``mariadb:10.6``) and then extended with Python, the
    current repo's source tree, a ``zenml[server]`` install, environment
    variables that configure the DB + server, and the shared entrypoint
    script that sequences ``mysqld`` → wait-for-ready → ``uvicorn``.

    Args:
        db_image: Upstream DB container image tag.
        python_version: Python version to install on top of the base.
        db_env: DB-specific environment variables (credentials, database
            name, store URL) that the entrypoint script consumes.

    Returns:
        A fully-configured ``modal.Image``.
    """
    import modal

    base = modal.Image.from_registry(db_image, add_python=python_version)

    env: Dict[str, str] = {
        "ZENML_ANALYTICS_OPT_IN": "false",
        "ZENML_DEBUG": "true",
        "ZENML_SERVER_DEPLOYMENT_TYPE": "docker",
        "ZENML_SERVER_AUTO_ACTIVATE": "True",
        "ZENML_SERVER_AUTO_CREATE_DEFAULT_USER": "True",
        "ZENML_SERVER_PORT": str(ZENML_SERVER_PORT),
        **db_env,
    }

    return (
        base.add_local_dir(
            str(REPO_ROOT),
            "/src/zenml",
            copy=True,
            ignore=list(_IMAGE_IGNORE_PATTERNS),
        )
        .add_local_file(
            str(ENTRYPOINT_SCRIPT_PATH),
            "/usr/local/bin/zenml-modal-entrypoint.sh",
            copy=True,
        )
        .run_commands(
            "chmod +x /usr/local/bin/zenml-modal-entrypoint.sh",
            "pip install --no-cache-dir -e '/src/zenml[server]'",
        )
        .env(env)
    )


def wait_for_server(
    url: str,
    timeout_secs: int = DEFAULT_SERVER_READY_TIMEOUT_SECS,
) -> None:
    """Poll the ZenML server URL until it returns a healthy response.

    The ZenML FastAPI app exposes ``/health`` early in its startup; that's
    the cheapest signal that the whole stack (DB + server) is ready.

    Args:
        url: Base URL of the Modal tunnel (``https://…modal.host``).
        timeout_secs: Maximum time to wait.

    Raises:
        RuntimeError: If the server does not become healthy in time.
    """
    deadline = time.monotonic() + timeout_secs
    health_url = url.rstrip("/") + "/health"
    last_error: str = ""

    while time.monotonic() < deadline:
        try:
            response = requests.get(health_url, timeout=5)
            if response.ok:
                logging.info("Modal-hosted ZenML server is healthy.")
                return
            last_error = (
                f"HTTP {response.status_code} from {health_url}: "
                f"{response.text[:200]}"
            )
        except requests.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"

        time.sleep(3)

    raise RuntimeError(
        "Modal-hosted ZenML server did not become healthy "
        f"within {timeout_secs}s. Last error: {last_error or 'no response'}"
    )
