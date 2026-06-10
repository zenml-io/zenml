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
"""Tests for path-based security decisions in the ZenML server middleware."""

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from zenml.zen_server.middleware import RestrictFileUploadsMiddleware

MULTIPART_HEADERS = {"content-type": "multipart/form-data; boundary=x"}


def _build_upload_app() -> Starlette:
    """Build a minimal app guarded by the upload-restriction middleware.

    Returns:
        A Starlette app that only allows multipart uploads on ``/allowed``.
    """

    async def upload(_request: Request) -> PlainTextResponse:
        return PlainTextResponse("reached upload handler")

    app = Starlette(
        routes=[
            Route("/allowed", upload, methods=["POST"]),
            Route("/blocked", upload, methods=["POST"]),
        ]
    )
    app.add_middleware(
        RestrictFileUploadsMiddleware, allowed_paths={"/allowed"}
    )
    return app


def test_upload_allowed_on_allowlisted_path():
    """Multipart uploads are permitted on an allowlisted path."""
    client = TestClient(_build_upload_app())

    response = client.post("/allowed", headers=MULTIPART_HEADERS)

    assert response.status_code == 200


def test_upload_blocked_on_non_allowlisted_path():
    """Multipart uploads are rejected on a path outside the allowlist."""
    client = TestClient(_build_upload_app())

    response = client.post("/blocked", headers=MULTIPART_HEADERS)

    assert response.status_code == 403


def test_upload_block_survives_host_header_poisoning():
    """Regression test for CVE-2026-48710 / GHSA-86qp-5c8j-p5mr.

    A malformed ``Host`` header makes Starlette reconstruct ``request.url.path``
    so that it differs from the path the router actually dispatched to. Here the
    header is crafted so ``request.url.path`` reconstructs to the allowlisted
    ``/allowed`` while routing still serves ``/blocked``. The upload restriction
    must hold, because it now keys off the raw ASGI scope path rather than the
    poisonable reconstructed URL.
    """
    client = TestClient(_build_upload_app())

    response = client.post(
        "/blocked",
        headers={**MULTIPART_HEADERS, "host": "evil.example.com/allowed?x="},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == (
        "File uploads are not allowed on this endpoint."
    )
