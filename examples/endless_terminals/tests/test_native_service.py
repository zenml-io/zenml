"""Native GPU lifecycle guarantees without creating Kubernetes resources."""

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from kubernetes.client.rest import ApiException
from native_service import (
    NativeServiceConfig,
    NativeTrainingService,
    build_proxy_config,
)
from pydantic import ValidationError


@pytest.fixture
def session(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> NativeTrainingService:
    """Build a service with isolated fake API clients.

    Args:
        tmp_path: Temporary evidence parent directory.
        monkeypatch: Scoped patch helper for stack selection.

    Returns:
        Configured service with mocked Kubernetes APIs.
    """
    sandbox = SimpleNamespace(
        config=SimpleNamespace(kubernetes_namespace="tasks", incluster=True)
    )
    monkeypatch.setattr(
        NativeTrainingService, "_select_sandbox", lambda self: sandbox
    )
    result = NativeTrainingService(
        NativeServiceConfig(
            training_image="registry/trainer@sha256:" + "a" * 64,
            proxy_image="registry/proxy@sha256:" + "b" * 64,
            cleanup_timeout=1,
        ),
        {"name": "test/model", "revision": "c" * 40},
        "test-run",
        tmp_path / "service",
    )
    result.namespace = "tasks"
    result._controller_owner = {
        "apiVersion": "v1",
        "kind": "Pod",
        "name": "controller",
        "uid": "controller-uid",
    }
    result._core = Mock()
    result._batch = Mock()
    result._client = Mock()
    result._core.list_namespaced_pod.return_value = SimpleNamespace(items=[])
    return result


def resource(
    session: NativeTrainingService, uid: str, token: str | None = None
) -> SimpleNamespace:
    """Create an API object carrying ownership metadata.

    Args:
        session: Service supplying default ownership labels.
        uid: Resource UID returned by Kubernetes.
        token: Alternate token for collision tests.

    Returns:
        Minimal Kubernetes-style object.
    """
    return SimpleNamespace(
        metadata=SimpleNamespace(
            name=session.name,
            uid=uid,
            labels={"endless-owner": token or session.token},
        ),
        status=SimpleNamespace(conditions=[]),
    )


def test_constructor_does_not_create_output(
    session: NativeTrainingService,
) -> None:
    """Training can create its output directory after constructing the session.

    Args:
        session: Isolated service.
    """
    assert not session.directory.exists()
    assert session.service_host == f"{session.name}.tasks.svc.cluster.local"
    assert session.base_url == f"http://{session.service_host}:8001"
    assert session.serving_seconds_remaining == 0
    assert session.cleanup_report["complete"] is False


@pytest.mark.parametrize(
    "field,value",
    [
        ("proxy_image", "proxy:latest"),
        ("training_image", "trainer:latest"),
        ("startup_timeout", 1801),
        ("serving_deadline", 5401),
        ("cleanup_timeout", 301),
        ("cleanup_timeout", 0),
        ("api_key", "caller-supplied"),
        ("inference_gpu_memory_utilization", 0),
        ("inference_gpu_memory_utilization", 0.96),
    ],
)
def test_rejects_unpinned_or_unbounded_configuration(
    field: str, value: object
) -> None:
    """Images must be immutable and callers cannot bypass authentication.

    Args:
        field: Invalid configuration field.
        value: Value that violates the configuration contract.
    """
    config: dict[str, object] = {
        "training_image": "trainer@sha256:" + "a" * 64,
        "proxy_image": "proxy@sha256:" + "b" * 64,
    }
    config[field] = value
    with pytest.raises(ValidationError):
        NativeServiceConfig.model_validate(config)


def test_proxy_authenticates_all_routes_with_case_sensitive_key(
    session: NativeTrainingService,
) -> None:
    """Auth covers health and download routes and keys do not enter upstream logs.

    Args:
        session: Isolated service with random credential.
    """
    config = build_proxy_config(session.api_key)
    assert f"~^{session.api_key}$ 1;" in config
    assert "if ($authenticated = 0) { return 401; }" in config
    assert config.index("return 401") < config.index("location /")
    assert "access_log off;" in config
    assert "proxy_set_header Host $http_host;" in config
    assert 'proxy_set_header X-API-Key "";' in config
    assert "proxy_pass http://127.0.0.1:8000;" in config
    with pytest.raises(ValueError):
        build_proxy_config("untrusted-key; nginx injection")


def test_manifest_is_owned_authenticated_and_gpu_bounded(
    session: NativeTrainingService,
) -> None:
    """Tasks cannot mount the proxy secret or inherit the controller token.

    Args:
        session: Isolated service.
    """
    job, secret, service = session._manifests()
    spec = job["spec"]["template"]["spec"]
    assert job["metadata"]["ownerReferences"] == [session._controller_owner]
    assert job["spec"]["backoffLimit"] == 0
    assert (
        job["spec"]["activeDeadlineSeconds"] == session.config.serving_deadline
    )
    assert spec["automountServiceAccountToken"] is False
    assert spec["restartPolicy"] == "Never"
    assert not spec["hostNetwork"] and not spec["hostPID"]
    main, proxy = spec["containers"]
    assert main["resources"]["limits"] == {
        "memory": "28Gi",
        "nvidia.com/gpu": "1",
    }
    assert main["resources"]["requests"]["memory"] == "26Gi"
    assert main["securityContext"]["runAsUser"] == 1000
    assert proxy["securityContext"]["readOnlyRootFilesystem"] is True
    assert proxy["securityContext"]["runAsUser"] == 101
    volumes = {volume["name"]: volume for volume in spec["volumes"]}
    assert volumes["shm"]["emptyDir"]["sizeLimit"] == "8Gi"
    assert {item["key"] for item in volumes["source"]["secret"]["items"]} == {
        "entrypoint.py",
        "backend_config.json",
        "diagnostics.py",
    }
    assert volumes["proxy-config"]["secret"]["items"] == [
        {"key": "nginx.conf", "path": "nginx.conf"}
    ]
    assert service["spec"]["type"] == "ClusterIP"
    assert service["spec"]["ports"] == [
        {"name": "authenticated-api", "port": 8001, "targetPort": 8001}
    ]
    assert session.api_key in secret["stringData"]["nginx.conf"]
    assert session.api_key not in json.dumps(job)
    assert session.api_key not in json.dumps(session.identity)
    assert not session.directory.exists()


@pytest.mark.parametrize("utilization", [0.35, 0.5])
def test_inference_memory_setting_is_mounted_and_hashed(
    session: NativeTrainingService, utilization: float
) -> None:
    """The server receives and verifies the run's inference memory budget.

    Args:
        session: Isolated service.
        utilization: Fraction of GPU memory reserved for inference.
    """
    values = session.config.model_dump()
    values["inference_gpu_memory_utilization"] = utilization
    session.config = NativeServiceConfig.model_validate(values)
    _, secret, _ = session._manifests()
    content = secret["stringData"]["backend_config.json"]
    backend = json.loads(content)
    assert (
        backend["generator.inference_engine.gpu_memory_utilization"]
        == utilization
    )
    assert session._backend_config == backend
    assert (
        session.identity["source_sha256"]["backend_config.json"]
        == hashlib.sha256(content.encode()).hexdigest()
    )


def test_ambiguous_create_is_reconciled_and_deleted_by_uid(
    session: NativeTrainingService,
) -> None:
    """Lost create responses cannot leave an owned GPU Job behind.

    Args:
        session: Isolated service with fake API methods.
    """
    session._operation_deadline = float("inf")
    session._batch.create_namespaced_job.side_effect = TimeoutError(
        "response lost"
    )
    with pytest.raises(TimeoutError):
        session._create("job", {})
    assert session._attempted == {"job"}
    session._batch.read_namespaced_job.side_effect = [
        resource(session, "job-uid"),
        ApiException(status=404),
    ]
    session._cleanup()
    assert session.cleanup_report["complete"] is True
    kwargs = session._batch.delete_namespaced_job.call_args.kwargs
    assert kwargs["body"]["preconditions"] == {"uid": "job-uid"}
    assert kwargs["body"]["propagationPolicy"] == "Foreground"
    assert 0 < kwargs["_request_timeout"] <= 15


def test_collision_is_never_deleted(session: NativeTrainingService) -> None:
    """A same-name resource belonging to another run is preserved.

    Args:
        session: Isolated service.
    """
    session._attempted = {"job"}
    session._batch.read_namespaced_job.return_value = resource(
        session, "foreign", "foreign-token"
    )
    session._cleanup()
    session._batch.delete_namespaced_job.assert_not_called()
    assert session.cleanup_report["complete"] is False
    assert "ownership token mismatch" in str(session.cleanup_report["errors"])


def test_uid_replacement_is_never_deleted(
    session: NativeTrainingService,
) -> None:
    """Even matching labels do not authorize deleting a replacement object.

    Args:
        session: Isolated service.
    """
    session._attempted = {"job"}
    session._uids["job"] = "original"
    session._batch.read_namespaced_job.return_value = resource(
        session, "replacement"
    )
    session._cleanup()
    session._batch.delete_namespaced_job.assert_not_called()
    assert session.cleanup_report["complete"] is False


def test_delete_failures_do_not_skip_other_resources(
    session: NativeTrainingService,
) -> None:
    """Service, Job, and Secret cleanup proceeds independently.

    Args:
        session: Isolated service.
    """
    session._attempted = {"service", "job", "secret"}
    for kind, api in (
        ("service", session._core),
        ("job", session._batch),
        ("secret", session._core),
    ):
        getattr(api, f"read_namespaced_{kind}").side_effect = [
            resource(session, kind + "-uid"),
            ApiException(status=404),
        ]
    session._core.delete_namespaced_service.side_effect = RuntimeError(
        "transport error"
    )
    session._cleanup()
    session._batch.delete_namespaced_job.assert_called_once()
    session._core.delete_namespaced_secret.assert_called_once()
    assert session.cleanup_report["complete"] is False


def test_startup_failure_captures_before_cleanup(
    session: NativeTrainingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failed readiness preserves diagnostic evidence and still removes resources.

    Args:
        session: Isolated service.
        monkeypatch: Scoped helper for replacing service methods.
    """
    order: list[str] = []
    monkeypatch.setattr(session, "_connect", Mock())
    monkeypatch.setattr(
        session,
        "_manifests",
        Mock(return_value=({}, {"metadata": {}}, {"metadata": {}})),
    )

    def create(kind: str, body: dict[str, object]) -> None:
        session._attempted.add(kind)
        session._uids[kind] = kind + "-uid"

    monkeypatch.setattr(session, "_create", Mock(side_effect=create))
    monkeypatch.setattr(
        session,
        "_wait_ready",
        Mock(side_effect=RuntimeError("main terminated")),
    )
    monkeypatch.setattr(
        session, "_capture", Mock(side_effect=lambda: order.append("capture"))
    )
    monkeypatch.setattr(
        session, "_cleanup", Mock(side_effect=lambda: order.append("cleanup"))
    )
    with pytest.raises(RuntimeError, match="main terminated"):
        session.__enter__()
    assert order == ["capture", "cleanup"]
    assert (session.directory / "native-service-cleanup.json").exists()


def test_diagnostic_failure_and_secrets_do_not_escape_evidence(
    session: NativeTrainingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Diagnostic errors remain separate and cannot leak the credential.

    Args:
        session: Isolated service with fake sensitive errors.
        monkeypatch: Scoped helper for replacing service methods.
    """
    session.directory.mkdir()
    session._attempted = {"job"}
    monkeypatch.setattr(
        session, "_capture", Mock(side_effect=RuntimeError(session.api_key))
    )
    session._batch.read_namespaced_job.side_effect = [
        resource(session, "uid"),
        ApiException(status=404),
    ]
    session._finish()
    assert session.cleanup_report["complete"] is True
    assert session.cleanup_report["diagnostic_errors"]
    assert session.cleanup_report["errors"] == []
    session._write("logs.txt", session.api_key)
    for path in session.directory.iterdir():
        assert session.api_key not in path.read_text()
    assert session.api_key not in json.dumps(session.cleanup_report)


def test_deadline_includes_startup_and_blocks_late_calls(
    session: NativeTrainingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Startup consumes the serving budget and no late API call is dispatched.

    Args:
        session: Isolated service.
        monkeypatch: Scoped clock patch helper.
    """
    session._serving_deadline = 200
    session._operation_deadline = 150
    monkeypatch.setattr("native_service.time.monotonic", lambda: 120)
    assert session.serving_seconds_remaining == 80
    operation = Mock()
    session._call(operation)
    assert operation.call_args.kwargs["_request_timeout"] == 15
    monkeypatch.setattr("native_service.time.monotonic", lambda: 201)
    assert session.serving_seconds_remaining == 0
    with pytest.raises(TimeoutError):
        session._call(operation)
    operation.assert_called_once()


def test_terminated_main_fails_even_while_proxy_runs(
    session: NativeTrainingService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A living sidecar cannot hide the training process exiting.

    Args:
        session: Isolated service.
        monkeypatch: Scoped helper for replacing service methods.
    """
    session._operation_deadline = float("inf")
    monkeypatch.setattr(
        session, "_read", Mock(return_value=resource(session, "uid"))
    )
    pod = resource(session, "pod-uid")
    pod.status.container_statuses = [
        SimpleNamespace(
            name="main",
            state=SimpleNamespace(terminated=SimpleNamespace(exit_code=1)),
        ),
        SimpleNamespace(
            name="auth-proxy", state=SimpleNamespace(terminated=None)
        ),
    ]
    monkeypatch.setattr(session, "_pods", Mock(return_value=[pod]))
    with pytest.raises(RuntimeError, match="main terminated"):
        session._wait_ready()


@pytest.mark.parametrize(
    "changed", ["model_revision", "backend_config", "source_sha256"]
)
def test_identity_mismatch_is_rejected(
    session: NativeTrainingService,
    changed: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Health alone never validates different weights, settings, or source.

    Args:
        session: Isolated service.
        changed: Identity field corrupted by the fake server.
        monkeypatch: Scoped helper for replacing service methods.
    """
    identity = {
        "model_name": session.model["name"],
        "model_revision": session.model["revision"],
        "backend_config": {},
        "source_sha256": {},
    }
    identity[changed] = "wrong"
    monkeypatch.setattr(
        session, "_exec", Mock(return_value=json.dumps(identity))
    )
    with pytest.raises(RuntimeError, match="mismatch"):
        session._verify_server()
