"""Check workspace isolation and trusted grading order without Kubernetes calls."""

import hashlib
import io
import tarfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from kubernetes.client.rest import ApiException
from runtime.sandbox_env import SandboxEnvironment
from runtime.sandbox_workspace import SandboxRuntimeConfig, SandboxWorkspace

from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.integrations.kubernetes.sandboxes.kubernetes_sandbox import (
    KubernetesSandbox,
)


def workspace() -> SandboxWorkspace:
    """Build a workspace using fake Kubernetes API boundaries.

    Returns:
        Workspace with no allocated resources.
    """
    sandbox = Mock(
        spec=KubernetesSandbox,
        config=SimpleNamespace(
            sandbox_environment={},
            kubernetes_namespace="tasks",
            pod_settings=KubernetesPodSettings(
                node_selectors={"pool": "workloads"},
                tolerations=[
                    {
                        "key": "pool",
                        "value": "workloads",
                        "effect": "NoSchedule",
                        "operator": "Equal",
                    }
                ],
            ),
        ),
        core_api=Mock(),
    )
    return SandboxWorkspace(
        sandbox, SandboxRuntimeConfig(helper_image="helper@sha256:" + "a" * 64)
    )


def test_settings_isolate_network_and_preserve_cpu_placement() -> None:
    """Only the trusted init container receives permission to disable interfaces."""
    settings = workspace().settings("task@sha256:" + "b" * 64, "/home/user")
    pod = settings.pod_settings
    assert pod is not None
    assert pod.node_selectors["pool"] == "workloads"
    assert pod.volume_mounts[0]["subPath"] == "home"
    assert settings.automount_service_account_token is False
    assert (
        "NET_ADMIN"
        not in pod.container_security_context["capabilities"]["add"]
    )
    assert pod.additional_pod_spec_args["host_network"] is False
    init = pod.additional_pod_spec_args["init_containers"][0]
    assert init["securityContext"]["capabilities"]["add"] == ["NET_ADMIN"]
    assert 'ip link set dev "$name" down' in init["command"][-1]
    assert workspace().settings("image", None).pod_settings.volumes == []  # type: ignore[union-attr]


def test_snapshot_reads_only_after_agent_termination(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A clean read-only helper starts only after the agent deletion completes.

    Args:
        monkeypatch: Scoped environment method replacements.
    """
    env = object.__new__(SandboxEnvironment)
    env.final = None
    env.agent = Mock(id="agent")
    env.shell = Mock()
    env.workspace = Mock()
    env.stopped = False
    reader = Mock(id="reader")
    events = []
    env.workspace.destroy_session.side_effect = lambda session: events.append(
        "delete-" + session.id
    )

    def create_reader(*args: object, **kwargs: object) -> Mock:
        events.append("reader")
        return reader

    new_session = Mock(side_effect=create_reader)
    monkeypatch.setattr(env, "_new", new_session)
    monkeypatch.setattr(env, "_archive", Mock(return_value=b"archive"))
    assert env.home_snapshot() == b"archive"
    assert events == ["delete-agent", "reader", "delete-reader"]
    new_session.assert_called_once_with("/workspace", readonly=True)
    assert env.stopped


def test_protected_hash_uses_trusted_archive_bytes() -> None:
    """Source hashing does not invoke potentially modified binaries in the agent."""
    archive = io.BytesIO()
    with tarfile.open(fileobj=archive, mode="w") as tar:
        member = tarfile.TarInfo("logs/input.log")
        member.size = 4
        tar.addfile(member, io.BytesIO(b"data"))
    env = object.__new__(SandboxEnvironment)
    env.stopped = False
    env.initial = archive.getvalue()
    assert (
        env.source_hash("/home/user/logs/input.log")
        == hashlib.sha256(b"data").hexdigest()
    )
    with pytest.raises(ValueError):
        env.source_hash("/home/user/../etc/passwd")


def test_timeout_cleanup_requires_pod_disappearance() -> None:
    """Send a UID-preconditioned deletion and wait for a real NotFound response."""
    item = workspace()
    session = Mock(id="agent")
    item.sessions[session.id] = (session, "pod", "uid")
    item.sandbox.core_api.read_namespaced_pod.side_effect = [
        SimpleNamespace(metadata=SimpleNamespace(uid="uid")),
        ApiException(status=404),
    ]
    item.destroy_session(session)
    assert (
        item.sandbox.core_api.delete_namespaced_pod.call_args.kwargs[
            "body"
        ].preconditions.uid
        == "uid"
    )
    assert not item.sessions
    session.close.assert_called_once()


def test_failed_start_orphan_is_removed_by_unique_workspace_label() -> None:
    """Recover a created pod whose SDK session failed before returning its handle."""
    item = workspace()
    item.sandbox.core_api.list_namespaced_pod.return_value = SimpleNamespace(
        items=[
            SimpleNamespace(
                metadata=SimpleNamespace(name="orphan", uid="orphan-uid")
            )
        ]
    )
    item.sandbox.core_api.read_namespaced_pod.side_effect = ApiException(
        status=404
    )
    item.close()
    assert (
        item.sandbox.core_api.delete_namespaced_pod.call_args.kwargs[
            "body"
        ].preconditions.uid
        == "orphan-uid"
    )
    assert item.provenance["cleanup_complete"] is True


def test_unsafe_archive_never_starts_verifier(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject symlink transfers before provisioning a trusted verifier.

    Args:
        tmp_path: Temporary test-file directory.
        monkeypatch: Scoped session constructor replacement.
    """
    data = io.BytesIO()
    with tarfile.open(fileobj=data, mode="w") as tar:
        member = tarfile.TarInfo("bad")
        member.type = tarfile.SYMTYPE
        member.linkname = "/etc/passwd"
        tar.addfile(member)
    env = object.__new__(SandboxEnvironment)
    new_session = Mock()
    monkeypatch.setattr(env, "_new", new_session)
    with pytest.raises(ValueError, match="Unsafe"):
        env.verify_snapshot(data.getvalue(), tmp_path / "test.py")
    new_session.assert_not_called()


@pytest.mark.parametrize(
    "mutation",
    [
        "secret_volume",
        "env_from",
        "secret_env",
        "literal_env",
        "wrong_mount",
        "init_mount",
    ],
)
def test_admission_credentials_are_rejected(
    mutation: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reject injected credentials and mounts before exposing a sandbox session.

    Args:
        mutation: Admission mutation applied to an otherwise valid pod.
        monkeypatch: Scoped sandbox session constructor replacement.
    """
    from kubernetes import client as k8s

    item = workspace()
    session = Mock(id="agent")
    monkeypatch.setattr(
        item.sandbox, "create_session", Mock(return_value=session)
    )
    container = k8s.V1Container(
        name="main",
        image="task",
        env=[],
        security_context=k8s.V1SecurityContext(
            privileged=False,
            allow_privilege_escalation=False,
            capabilities=k8s.V1Capabilities(drop=["ALL"], add=["CHOWN"]),
        ),
        volume_mounts=[
            k8s.V1VolumeMount(
                name="workspace", mount_path="/home/user", sub_path="home"
            )
        ],
    )
    initializer = k8s.V1Container(
        name="disable-network", image=item.config.helper_image
    )
    pod = k8s.V1Pod(
        metadata=k8s.V1ObjectMeta(name="pod", uid="uid"),
        spec=k8s.V1PodSpec(
            containers=[container],
            init_containers=[initializer],
            automount_service_account_token=False,
            volumes=[
                k8s.V1Volume(
                    name="workspace",
                    persistent_volume_claim=k8s.V1PersistentVolumeClaimVolumeSource(
                        claim_name=item.name
                    ),
                )
            ],
        ),
        status=k8s.V1PodStatus(),
    )
    if mutation == "secret_volume":
        pod.spec.volumes.append(
            k8s.V1Volume(
                name="credential",
                secret=k8s.V1SecretVolumeSource(secret_name="secret"),
            )
        )
    elif mutation == "env_from":
        container.env_from = [
            k8s.V1EnvFromSource(
                secret_ref=k8s.V1SecretEnvSource(name="secret")
            )
        ]
    elif mutation == "secret_env":
        container.env = [
            k8s.V1EnvVar(
                name="KEY",
                value_from=k8s.V1EnvVarSource(
                    secret_key_ref=k8s.V1SecretKeySelector(
                        name="secret", key="key"
                    )
                ),
            )
        ]
    elif mutation == "literal_env":
        container.env = [k8s.V1EnvVar(name="KEY", value="credential")]
    elif mutation == "wrong_mount":
        container.volume_mounts[0].mount_path = "/etc"
    else:
        initializer.volume_mounts = container.volume_mounts
    item.sandbox.core_api.list_namespaced_pod.return_value = SimpleNamespace(
        items=[pod]
    )
    with pytest.raises(RuntimeError, match="Admission"):
        item.create_session("task", "/home/user")
    assert session.id in item.sessions


def test_cleanup_timeout_does_not_force_delete(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Keep the session tracked when graceful termination cannot be confirmed.

    Args:
        monkeypatch: Test-local clock replacement.
    """
    item = workspace()
    session = Mock(id="agent")
    item.sessions[session.id] = (session, "pod", "uid")
    item.sandbox.core_api.read_namespaced_pod.return_value = SimpleNamespace(
        metadata=SimpleNamespace(uid="uid")
    )
    ticks = iter([0, 121])
    monkeypatch.setattr(
        "runtime.sandbox_workspace.time.monotonic", lambda: next(ticks)
    )
    with pytest.raises(TimeoutError, match="termination"):
        item.destroy_session(session)
    deletion = item.sandbox.core_api.delete_namespaced_pod
    deletion.assert_called_once()
    assert deletion.call_args.kwargs["body"].grace_period_seconds == 5
    assert session.id in item.sessions
    session.close.assert_not_called()
