"""Verify Modal service authentication, endpoint trust, and failure cleanup."""

import http.client
import json
import threading
from email.message import Message
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
from modal_service import (
    PROXY_SOURCE,
    ModalServiceConfig,
    ModalTrainingService,
)
from training_client import validate_training_url


def service(tmp_path: Path) -> ModalTrainingService:
    """Construct an offline service for lifecycle tests.

    Args:
        tmp_path: Temporary lifecycle evidence directory.

    Returns:
        An unstarted Modal training service.
    """
    return ModalTrainingService(
        ModalServiceConfig(training_image="registry/train@sha256:" + "a" * 64),
        {"name": "Qwen/model", "revision": "b" * 40},
        "run",
        tmp_path,
    )


@pytest.mark.parametrize(
    "url", ["https://sb-test.modal.host", "https://sb-test.modal.host:443"]
)
def test_owned_modal_https_origin(url: str) -> None:
    """Accept only HTTPS to the exact tunnel supplied by the service.

    Args:
        url: Owned HTTPS tunnel origin.
    """
    validate_training_url(url, "sb-test.modal.host")


@pytest.mark.parametrize(
    "url",
    [
        "http://sb-test.modal.host",
        "https://other.modal.host",
        "https://sb-test.modal.host:8001",
        "https://sb-test.modal.host.evil.example",
        "https://sb-test.modal.host/path",
        "https://key@sb-test.modal.host",
        "https://sb-test.modal.host?key=secret",
    ],
)
def test_reject_changed_modal_origin(url: str) -> None:
    """Prevent credentials from being sent to a substituted endpoint.

    Args:
        url: Invalid or substituted tunnel origin.
    """
    with pytest.raises(ValueError):
        validate_training_url(url, "sb-test.modal.host")


def test_failed_start_terminates_and_records_cleanup(tmp_path: Path) -> None:
    """A failure after allocation still terminates the owned GPU sandbox.

    Args:
        tmp_path: Temporary lifecycle evidence directory.
    """
    instance = service(tmp_path)
    sandbox = MagicMock()
    sandbox.poll.return_value = 0

    def fail() -> None:
        instance._sandbox = sandbox
        raise RuntimeError("startup failed")

    with (
        patch.object(instance, "_start", side_effect=fail),
        patch.object(instance, "_exec", return_value="diagnostics"),
    ):
        with pytest.raises(RuntimeError, match="startup failed"):
            with instance:
                pass
    sandbox.terminate.assert_called_once()
    assert json.loads((tmp_path / "native-service-cleanup.json").read_text())[
        "complete"
    ]


def test_failed_termination_is_not_success(tmp_path: Path) -> None:
    """Termination errors remain visible and retryable.

    Args:
        tmp_path: Temporary lifecycle evidence directory.
    """
    instance = service(tmp_path)
    instance._sandbox = MagicMock()
    instance._sandbox.terminate.side_effect = RuntimeError("cannot terminate")
    with patch.object(instance, "_exec", return_value="diagnostics"):
        with pytest.raises(RuntimeError, match="cleanup incomplete"):
            instance.__exit__(None, None, None)
    assert not instance.cleanup_report["complete"]
    assert not instance._closed


def test_evidence_redacts_api_key(tmp_path: Path) -> None:
    """Neither diagnostics nor serialized structures expose the service key.

    Args:
        tmp_path: Temporary lifecycle evidence directory.
    """
    instance = service(tmp_path)
    instance._write("evidence.json", {"error": instance.api_key})
    assert instance.api_key not in (tmp_path / "evidence.json").read_text()


def test_proxy_authenticates_and_streams_without_forwarding_key() -> None:
    """Exercise the actual proxy against a local HTTP backend."""
    observed = []

    class Backend(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            observed.append(dict(self.headers))
            payload = b"checkpoint" * 200000
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def log_message(self, *_args: object) -> None:
            pass

    backend = ThreadingHTTPServer(("127.0.0.1", 0), Backend)
    backend_thread = threading.Thread(
        target=backend.serve_forever, daemon=True
    )
    backend_thread.start()
    namespace: dict[str, Any] = {}
    code = PROXY_SOURCE.replace(
        "8000, timeout=600", f"{backend.server_port}, timeout=600"
    ).replace(
        'ThreadingHTTPServer(("0.0.0.0", 8001), Handler).serve_forever()', ""
    )
    with patch.dict("os.environ", {"ENDLESS_API_KEY": "test-key"}):
        exec(compile(code, "proxy.py", "exec"), namespace)
    proxy = ThreadingHTTPServer(("127.0.0.1", 0), namespace["Handler"])
    proxy_thread = threading.Thread(target=proxy.serve_forever, daemon=True)
    proxy_thread.start()
    try:
        connection = http.client.HTTPConnection("127.0.0.1", proxy.server_port)
        connection.request("GET", "/archive")
        denied = connection.getresponse()
        assert denied.status == 401
        denied.read()
        assert observed == []
        connection.close()
        connection = http.client.HTTPConnection("127.0.0.1", proxy.server_port)
        connection.request(
            "GET",
            "/archive",
            headers={"X-API-Key": "test-key", "Host": "owned.modal.host"},
        )
        response = connection.getresponse()
        assert response.status == 200
        assert response.read() == b"checkpoint" * 200000
        assert "X-API-Key" not in observed[0]
        assert observed[0]["Host"] == "owned.modal.host"
        assert observed[0]["X-Forwarded-Proto"] == "https"
        connection.close()
    finally:
        proxy.shutdown()
        backend.shutdown()
        proxy.server_close()
        backend.server_close()
        proxy_thread.join()
        backend_thread.join()


def test_ready_server_identity_must_match(tmp_path: Path) -> None:
    """HTTP health is insufficient when the service loaded another revision.

    Args:
        tmp_path: Temporary lifecycle evidence directory.
    """
    import time
    import urllib.error

    instance = service(tmp_path)
    instance._sandbox = MagicMock()
    instance._sandbox.poll.return_value = None
    instance._backend_process = MagicMock()
    instance._backend_process.poll.return_value = None
    instance._startup_deadline = time.monotonic() + 10
    instance.base_url = "https://owned.modal.host"
    response = MagicMock()
    response.__enter__.return_value.status = 200
    opener = MagicMock()
    opener.open.side_effect = [
        response,
        urllib.error.HTTPError(
            instance.base_url, 401, "Unauthorized", Message(), None
        ),
    ]
    with (
        patch("urllib.request.build_opener", return_value=opener),
        patch.object(
            instance, "_exec", return_value=json.dumps({"model_name": "wrong"})
        ),
    ):
        with pytest.raises(RuntimeError, match="identity mismatch"):
            instance._wait_ready()


def test_uncertain_allocation_does_not_claim_cleanup(tmp_path: Path) -> None:
    """A lost allocation response must not be reported as confirmed cleanup.

    Args:
        tmp_path: Temporary lifecycle evidence directory.
    """
    instance = service(tmp_path)

    def fail_after_request() -> None:
        instance._allocation_attempted = True
        raise TimeoutError("allocation response lost")

    with patch.object(instance, "_start", side_effect=fail_after_request):
        with pytest.raises(TimeoutError, match="response lost"):
            with instance:
                pass
    report = json.loads((tmp_path / "native-service-cleanup.json").read_text())
    assert not report["complete"]
    assert instance.name in report["errors"][0]


@pytest.mark.parametrize("imported_image_id", [None, "im-VerifiedImport123"])
@pytest.mark.parametrize(
    "identity", [("zenml-io", "dev"), ("external-team", "research")]
)
def test_start_uploads_current_sources_through_filesystem(
    tmp_path: Path,
    imported_image_id: str | None,
    identity: tuple[str, str],
) -> None:
    """Upload exact source contents without calling the removed file API.

    Args:
        tmp_path: Temporary lifecycle evidence directory.
        imported_image_id: Explicit previously verified image ID, if reused.
        identity: Expected workspace and environment.
    """
    import hashlib
    import time

    from zenml.integrations.modal.sandboxes.modal_sandbox import ModalSandbox

    instance = service(tmp_path)
    instance.config = instance.config.model_copy(
        update={
            "imported_image_id": imported_image_id,
            "workspace": identity[0],
            "modal_environment": identity[1],
        }
    )
    instance._deadline = time.monotonic() + 5400
    component = MagicMock(spec=ModalSandbox)
    component.config.modal_environment = identity[1]
    component.config.app_name = "test-app"
    stack = MagicMock()
    stack.sandbox = component
    sandbox = MagicMock()
    sandbox.object_id = "sb-test"
    sandbox.tunnels.return_value = {
        8001: MagicMock(url="https://random.w.modal.host")
    }
    workspace = MagicMock()
    workspace.hydrate.return_value.name = identity[0]
    with (
        patch("zenml.client.Client") as client,
        patch("modal.Workspace.from_context", return_value=workspace),
        patch("modal.Environment.from_name"),
        patch("modal.App.lookup"),
        patch("modal.Sandbox.create", return_value=sandbox) as sandbox_create,
        patch("modal.Secret.from_dict"),
        patch("modal.Image.from_id") as image_lookup,
        patch.object(
            type(stack),
            "container_registry",
            new_callable=PropertyMock,
            create=True,
            return_value=None,
        ) as registry_access,
        patch(
            "zenml.integrations.modal.sandbox_utils.create_modal_client_from_credentials"
        ) as modal_client,
        patch(
            "zenml.integrations.modal.sandbox_utils.get_modal_image_from_registry"
        ) as registry_import,
        patch.object(instance, "_exec", return_value="{}"),
    ):
        client.return_value.active_stack = stack
        image_lookup.return_value.object_id = "im-VerifiedImport123"
        registry_import.return_value.object_id = "im-NewImport123"
        selected_image = (
            image_lookup.return_value
            if imported_image_id
            else registry_import.return_value
        )
        selected_image.entrypoint.return_value.object_id = (
            "im-EntrypointCleared123"
        )
        instance._start()
        assert instance.identity["workspace"] == identity[0]
        assert (
            sandbox_create.call_args.kwargs["environment_name"] == identity[1]
        )
        selected_image.entrypoint.assert_called_once_with([])
        assert (
            sandbox_create.call_args.kwargs["image"]
            is selected_image.entrypoint.return_value
        )
        assert instance._backend_process is sandbox.exec.return_value
        assert "entrypoint.py" in sandbox.exec.call_args.args[2]
        assert instance.identity["modal_image_id"] == "im-EntrypointCleared123"
        if imported_image_id:
            image_lookup.assert_called_once_with(
                imported_image_id, client=modal_client.return_value
            )
            registry_access.assert_not_called()
            registry_import.assert_not_called()
            assert (
                instance.identity["imported_modal_image_id"]
                == imported_image_id
            )
            assert (
                instance.identity["image_selection"]
                == "explicit_operational_pairing"
            )
        else:
            image_lookup.assert_not_called()
            registry_import.assert_called_once()
            assert (
                instance.identity["imported_modal_image_id"]
                == "im-NewImport123"
            )
    assert (
        json.loads((tmp_path / "native-service-identity.json").read_text())[
            "service_url"
        ]
        == "https://random.w.modal.host"
    )
    sandbox.open.assert_not_called()
    uploaded = {
        call.args[1]: call.args[0]
        for call in sandbox.filesystem.write_text.call_args_list
    }
    assert set(uploaded) == {
        "/tmp/terminal-training/entrypoint.py",
        "/tmp/terminal-training/backend_config.json",
        "/tmp/terminal-training/diagnostics.py",
        "/tmp/terminal-training/proxy.py",
    }
    assert uploaded["/tmp/terminal-training/proxy.py"] == PROXY_SOURCE
    configuration = json.loads(
        uploaded["/tmp/terminal-training/backend_config.json"]
    )
    assert (
        configuration["generator.inference_engine.gpu_memory_utilization"]
        == 0.5
    )
    source = Path(__file__).parent.parent / "training_server"
    for name in ("entrypoint.py", "diagnostics.py"):
        assert (
            uploaded["/tmp/terminal-training/" + name]
            == (source / name).read_text()
        )
    for name, expected_hash in instance.identity["source_sha256"].items():
        assert (
            hashlib.sha256(
                uploaded["/tmp/terminal-training/" + name].encode()
            ).hexdigest()
            == expected_hash
        )


@pytest.mark.parametrize(
    "host",
    [
        "random.w.modal.host",
        "wtqcahqwhd4tu0.r5.modal.host",
        "random.region.relay.modal.host",
    ],
)
def test_owned_multilabel_tunnel_origin(host: str) -> None:
    """Accept the complete SDK hostname across Modal relay DNS layouts.

    Args:
        host: Valid multi-label Modal tunnel hostname.
    """
    validate_training_url("https://" + host, host)
    validate_training_url("https://" + host + ":443", host)


@pytest.mark.parametrize(
    "url, trusted_host",
    [
        ("https://other.w.modal.host", "random.w.modal.host"),
        ("http://random.w.modal.host", "random.w.modal.host"),
        ("https://random.w.modal.host:8001", "random.w.modal.host"),
        ("https://key@random.w.modal.host", "random.w.modal.host"),
        (
            "https://random.w.modal.host.evil.test",
            "random.w.modal.host.evil.test",
        ),
        ("https://random.w.notmodal.host", "random.w.notmodal.host"),
        ("https://random..modal.host", "random..modal.host"),
        ("https://random.-w.modal.host", "random.-w.modal.host"),
        ("https://random.w-.modal.host", "random.w-.modal.host"),
        ("https://random.w_.modal.host", "random.w_.modal.host"),
        ("https://" + "a" * 64 + ".w.modal.host", "a" * 64 + ".w.modal.host"),
    ],
)
def test_reject_untrusted_or_malformed_multilabel_origin(
    url: str, trusted_host: str
) -> None:
    """Reject host substitution, non-TLS routes and invalid DNS labels.

    Args:
        url: Candidate training endpoint.
        trusted_host: Host supplied by the service.
    """
    with pytest.raises(ValueError):
        validate_training_url(url, trusted_host)


@pytest.mark.parametrize("exit_code", [0, 1, 137])
def test_ready_rejects_exited_owned_backend(
    tmp_path: Path, exit_code: int
) -> None:
    """Never accept another process's healthy endpoint after our backend exits.

    Args:
        tmp_path: Temporary lifecycle evidence directory.
        exit_code: Exit status returned by the exact launched backend process.
    """
    import time

    instance = service(tmp_path)
    instance._sandbox = MagicMock()
    instance._sandbox.poll.return_value = None
    instance._backend_process = MagicMock()
    instance._backend_process.poll.return_value = exit_code
    instance._startup_deadline = time.monotonic() + 10
    with patch("urllib.request.build_opener") as opener:
        with pytest.raises(
            RuntimeError, match="owned training backend exited"
        ):
            instance._wait_ready()
    opener.return_value.open.assert_not_called()


def test_ready_rechecks_backend_after_identity(tmp_path: Path) -> None:
    """A backend exit during health verification invalidates otherwise valid identity.

    Args:
        tmp_path: Temporary lifecycle evidence directory.
    """
    import time
    import urllib.error

    instance = service(tmp_path)
    instance._sandbox = MagicMock()
    instance._sandbox.poll.return_value = None
    instance._backend_process = MagicMock()
    instance._backend_process.poll.side_effect = [None, 1]
    instance._startup_deadline = time.monotonic() + 10
    instance.base_url = "https://owned.w.modal.host"
    identity = {
        "model_name": instance.model["name"],
        "model_revision": instance.model["revision"],
        "backend_config": instance._backend_config,
        "source_sha256": instance._source_hashes,
    }
    response = MagicMock()
    response.__enter__.return_value.status = 200
    opener = MagicMock()
    opener.open.side_effect = [
        response,
        urllib.error.HTTPError(
            instance.base_url, 401, "Unauthorized", Message(), None
        ),
    ]
    with (
        patch("urllib.request.build_opener", return_value=opener),
        patch.object(instance, "_exec", return_value=json.dumps(identity)),
    ):
        with pytest.raises(
            RuntimeError, match="owned training backend exited"
        ):
            instance._wait_ready()
    assert instance._backend_process.poll.call_count == 2


@pytest.mark.parametrize(
    "mismatch", ["workspace", "environment", "credentials"]
)
def test_service_identity_mismatch_prevents_allocation(
    tmp_path: Path, mismatch: str
) -> None:
    """Reject configured identity mismatches before allocating the GPU or app.

    Args:
        tmp_path: Temporary lifecycle evidence directory.
        mismatch: Identity check to fail.
    """
    from zenml.integrations.modal.sandboxes.modal_sandbox import ModalSandbox

    instance = service(tmp_path)
    instance.config = instance.config.model_copy(
        update={"workspace": "external-team", "modal_environment": "research"}
    )
    component = MagicMock(spec=ModalSandbox)
    component.config.modal_environment = (
        "other" if mismatch == "environment" else "research"
    )
    component.config.token_id = (
        None if mismatch == "credentials" else "test-id"
    )
    component.config.token_secret = "test-secret"
    with (
        patch("zenml.client.Client") as client,
        patch("modal.Workspace.from_context") as workspace,
        patch("modal.App.lookup") as app,
        patch("modal.Sandbox.create") as allocate,
        patch(
            "zenml.integrations.modal.sandbox_utils.create_modal_client_from_credentials"
        ),
    ):
        client.return_value.active_stack.sandbox = component
        workspace.return_value.hydrate.return_value.name = "wrong-team"
        with pytest.raises(ValueError):
            instance._start()
        app.assert_not_called()
        allocate.assert_not_called()
