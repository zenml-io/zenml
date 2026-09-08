"""Own one temporary Kubernetes volume and its public ZenML sandbox sessions."""

from __future__ import annotations

import queue
import re
import threading
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, TypeVar, cast

from kubernetes.client import V1DeleteOptions, V1Preconditions
from kubernetes.client.rest import ApiException

from zenml.integrations.kubernetes.flavors.kubernetes_sandbox_flavor import (
    KubernetesSandboxSettings,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.integrations.kubernetes.sandboxes.kubernetes_sandbox import (
    KubernetesSandbox,
)
from zenml.sandboxes.session import SandboxSession

_T = TypeVar("_T")


@dataclass(frozen=True)
class SandboxRuntimeConfig:
    """Bound bootstrap and cleanup for an example-owned temporary workspace."""

    helper_image: str
    storage_class: str = "gp2"
    startup_timeout: int = 600
    cleanup_timeout: int = 120
    api_timeout: int = 15
    controller_pod_name: str | None = None
    modal_agent_image: str | None = None
    modal_workspace: str = "zenml-io"
    modal_environment: str = "dev"


def bounded_call(action: Callable[[], _T], timeout: float) -> _T:
    """Wait for public sandbox APIs without relying on private stream controls.

    Args:
        action: Operation to invoke on a daemon thread.
        timeout: Maximum controller waiting time.

    Returns:
        Operation result.

    Raises:
        TimeoutError: The controller deadline expires.
        BaseException: The operation fails.
    """  # noqa: DOC503 - The original exception is raised through `value`.
    result: queue.Queue[tuple[bool, Any]] = queue.Queue(maxsize=1)

    def invoke() -> None:
        try:
            result.put((True, action()))
        except BaseException as exc:
            result.put((False, exc))

    threading.Thread(target=invoke, daemon=True).start()
    try:
        success, value = result.get(timeout=timeout)
    except queue.Empty:
        raise TimeoutError("Sandbox API operation exceeded deadline") from None
    if not success:
        raise value
    return cast(_T, value)


class SandboxWorkspace:
    """Create sessions using only public sandbox APIs and own Kubernetes objects."""

    def __init__(
        self, sandbox: KubernetesSandbox, config: SandboxRuntimeConfig
    ) -> None:
        """Configure a unique workspace without creating cluster resources.

        Args:
            sandbox: Selected Kubernetes sandbox component.
            config: Workspace settings.

        Raises:
            ValueError: The helper image or timeout settings are invalid.
        """
        if not re.fullmatch(
            r"[^\s]+@sha256:[0-9a-f]{64}", config.helper_image
        ):
            raise ValueError(
                "Helper image must use an immutable registry digest"
            )
        if (
            min(
                config.startup_timeout,
                config.cleanup_timeout,
                config.api_timeout,
            )
            <= 0
        ):
            raise ValueError("Workspace timeouts must be positive")
        if sandbox.config.sandbox_environment:
            raise ValueError(
                "Task sandbox configuration must not inject environment values"
            )
        self.sandbox = sandbox
        self.config = config
        self.namespace = sandbox.config.kubernetes_namespace
        self.token = uuid.uuid4().hex
        self.name = "endless-workspace-" + self.token[:16]
        self.pvc_uid: str | None = None
        self.volume_attempted = False
        self.sessions: dict[str, tuple[SandboxSession, str, str]] = {}
        self.owner_references: list[dict[str, Any]] = []
        self.provenance: dict[str, Any] = {
            "backend": "kubernetes_sandbox",
            "namespace": self.namespace,
            "workspace_name": self.name,
            "pods": [],
            "cleanup_complete": False,
        }

    def create_volume(self) -> None:
        """Create a dedicated volume, optionally owned by the controller pod."""
        if self.config.controller_pod_name:
            owner = self.sandbox.core_api.read_namespaced_pod(
                self.config.controller_pod_name,
                self.namespace,
                _request_timeout=self.config.api_timeout,
            )
            self.owner_references = [
                {
                    "apiVersion": "v1",
                    "kind": "Pod",
                    "name": owner.metadata.name,
                    "uid": owner.metadata.uid,
                    "blockOwnerDeletion": False,
                }
            ]
        body = {
            "apiVersion": "v1",
            "kind": "PersistentVolumeClaim",
            "metadata": {
                "name": self.name,
                "labels": {"endless-workspace": self.token},
                "ownerReferences": self.owner_references,
            },
            "spec": {
                "accessModes": ["ReadWriteOnce"],
                "storageClassName": self.config.storage_class,
                "resources": {"requests": {"storage": "1Gi"}},
            },
        }
        self.volume_attempted = True
        claim = (
            self.sandbox.core_api.create_namespaced_persistent_volume_claim(
                self.namespace,
                body,
                _request_timeout=self.config.api_timeout,
            )
        )
        self.pvc_uid = claim.metadata.uid
        self.provenance["pvc_uid"] = self.pvc_uid

    def settings(
        self, image: str, mount: str | None, readonly: bool = False
    ) -> KubernetesSandboxSettings:
        """Build isolated pod settings while retaining CPU placement choices.

        Args:
            image: Immutable task image.
            mount: PVC mount location, or None for a clean verifier.
            readonly: Whether the PVC must be read-only.

        Returns:
            Explicit sandbox settings with isolated networking and no credentials.
        """
        base = self.sandbox.config.pod_settings or KubernetesPodSettings()
        isolation = (
            "set -eu; for path in /sys/class/net/*; do name=${path##*/}; "
            '[ "$name" = lo ] || ip link set dev "$name" down; done; '
            "ip -j link show"
        )
        volumes = (
            [
                {
                    "name": "workspace",
                    "persistentVolumeClaim": {"claimName": self.name},
                }
            ]
            if mount
            else []
        )
        mounts = (
            [{"name": "workspace", "mountPath": mount, "readOnly": readonly}]
            if mount
            else []
        )
        if mount == "/home/user":
            mounts[0]["subPath"] = "home"
        pod = KubernetesPodSettings(
            node_selectors={
                **base.node_selectors,
                "kubernetes.io/os": "linux",
                "kubernetes.io/arch": "amd64",
            },
            affinity=base.affinity,
            tolerations=base.tolerations,
            image_pull_secrets=base.image_pull_secrets,
            resources={
                "requests": {"cpu": "1", "memory": "1Gi"},
                "limits": {"cpu": "1", "memory": "1Gi"},
            },
            labels={"endless-workspace": self.token},
            volumes=volumes,
            volume_mounts=mounts,
            container_security_context={
                "runAsUser": 0,
                "privileged": False,
                "allowPrivilegeEscalation": False,
                "capabilities": {
                    "drop": ["ALL"],
                    "add": ["DAC_OVERRIDE", "FOWNER", "CHOWN"],
                },
            },
            additional_pod_spec_args={
                "host_network": False,
                "host_pid": False,
                "host_ipc": False,
                "share_process_namespace": False,
                "enable_service_links": False,
                "active_deadline_seconds": 1800,
                "termination_grace_period_seconds": 5,
                "security_context": {
                    "seccompProfile": {"type": "RuntimeDefault"}
                },
                "init_containers": [
                    {
                        "name": "disable-network",
                        "image": self.config.helper_image,
                        "command": ["/bin/sh", "-c", isolation],
                        "securityContext": {
                            "runAsUser": 0,
                            "privileged": False,
                            "allowPrivilegeEscalation": False,
                            "capabilities": {
                                "drop": ["ALL"],
                                "add": ["NET_ADMIN"],
                            },
                        },
                    }
                ],
            },
        )
        return KubernetesSandboxSettings(
            image=image,
            pod_settings=pod,
            automount_service_account_token=False,
            privileged=False,
            sandbox_environment={},
            pod_startup_timeout=self.config.startup_timeout,
            api_request_timeout=self.config.api_timeout,
            max_api_retries=0,
        )

    def create_session(
        self, image: str, mount: str | None, readonly: bool = False
    ) -> SandboxSession:
        """Create a public sandbox and record its exact pod UID before use.

        Args:
            image: Task image digest.
            mount: Optional workspace mount location.
            readonly: Read-only volume flag.

        Returns:
            Running session.

        Raises:
            RuntimeError: Pod identity or admission-mutated security is unexpected.
        """
        session = self.sandbox.create_session(
            settings=self.settings(image, mount, readonly)
        )
        pods = self.sandbox.core_api.list_namespaced_pod(
            self.namespace,
            label_selector=f"zenml-sandbox-id={session.id},endless-workspace={self.token}",
            _request_timeout=self.config.api_timeout,
        ).items
        if len(pods) != 1:
            raise RuntimeError("Expected one uniquely labeled sandbox pod")
        pod = pods[0]
        self.sessions[session.id] = (
            session,
            pod.metadata.name,
            pod.metadata.uid,
        )
        self.provenance["pods"].append(
            {
                "session_id": session.id,
                "pod_name": pod.metadata.name,
                "pod_uid": pod.metadata.uid,
                "node": pod.spec.node_name,
                "image": image,
                "phase": "agent"
                if mount == "/home/user"
                else "reader"
                if readonly
                else "seed"
                if mount
                else "verifier",
                "image_ids": [
                    status.image_id
                    for status in (pod.status.container_statuses or [])
                ],
            }
        )
        spec = pod.spec
        if (
            spec.host_network
            or spec.host_pid
            or spec.host_ipc
            or spec.share_process_namespace
            or spec.automount_service_account_token
            or spec.termination_grace_period_seconds == 0
            or spec.ephemeral_containers
            or len(spec.containers) != 1
            or len(spec.init_containers or []) != 1
        ):
            raise RuntimeError("Admission changed sandbox isolation settings")
        main = spec.containers[0]
        initializer = spec.init_containers[0]
        if (
            main.image != image
            or initializer.image != self.config.helper_image
        ):
            raise RuntimeError("Admission changed sandbox images")
        for container in [main, initializer]:
            if container.env_from or any(
                entry.value_from is not None
                or entry.name != "ZENML_ENABLE_REPO_INIT_WARNINGS"
                or entry.value != "False"
                for entry in (container.env or [])
            ):
                raise RuntimeError(
                    "Admission injected sandbox environment values"
                )
            if container.volume_devices:
                raise RuntimeError("Admission injected sandbox volume devices")
        if initializer.volume_mounts:
            raise RuntimeError("Admission injected initializer volume mounts")
        volumes = spec.volumes or []
        mounts = main.volume_mounts or []
        if mount is None:
            if volumes or mounts:
                raise RuntimeError(
                    "Clean verifier received unexpected volumes"
                )
        else:
            if len(volumes) != 1 or len(mounts) != 1:
                raise RuntimeError(
                    "Admission changed sandbox workspace volumes"
                )
            volume, actual_mount = volumes[0], mounts[0]
            if (
                volume.name != "workspace"
                or volume.persistent_volume_claim is None
                or volume.persistent_volume_claim.claim_name != self.name
                or volume.persistent_volume_claim.read_only
                or any(
                    value is not None
                    for key, value in volume.to_dict().items()
                    if key not in {"name", "persistent_volume_claim"}
                )
                or actual_mount.name != "workspace"
                or actual_mount.mount_path != mount
                or bool(actual_mount.read_only) != readonly
                or actual_mount.sub_path
                != ("home" if mount == "/home/user" else None)
                or actual_mount.sub_path_expr
                or actual_mount.mount_propagation not in {None, "None"}
            ):
                raise RuntimeError("Admission changed sandbox workspace mount")
        security = spec.containers[0].security_context
        if (
            security.privileged
            or security.allow_privilege_escalation
            or set(security.capabilities.add or [])
            - {"DAC_OVERRIDE", "FOWNER", "CHOWN"}
            or "ALL" not in (security.capabilities.drop or [])
        ):
            raise RuntimeError("Sandbox container capabilities are unsafe")
        if self.owner_references:
            self.sandbox.core_api.patch_namespaced_pod(
                pod.metadata.name,
                self.namespace,
                {
                    "metadata": {
                        "uid": pod.metadata.uid,
                        "ownerReferences": self.owner_references,
                    }
                },
                _request_timeout=self.config.api_timeout,
            )
        return session

    def destroy_session(self, session: SandboxSession) -> None:
        """Delete the recorded pod and confirm its original UID is gone.

        Args:
            session: Owned session to terminate.

        Raises:
            TimeoutError: The pod remains after the cleanup deadline.
            RuntimeError: Pod ownership changed.
            ApiException: A Kubernetes read or delete request fails.
        """
        if session.id not in self.sessions:
            return
        _, name, uid = self.sessions[session.id]
        api = self.sandbox.core_api
        try:
            pod = api.read_namespaced_pod(
                name, self.namespace, _request_timeout=self.config.api_timeout
            )
            if pod.metadata.uid != uid:
                raise RuntimeError("Sandbox pod identity changed")
            api.delete_namespaced_pod(
                name,
                self.namespace,
                body=V1DeleteOptions(
                    grace_period_seconds=5,
                    preconditions=V1Preconditions(uid=uid),
                ),
                _request_timeout=self.config.api_timeout,
            )
        except ApiException as exc:
            if exc.status != 404:
                raise
        deadline = time.monotonic() + self.config.cleanup_timeout
        while time.monotonic() < deadline:
            try:
                pod = api.read_namespaced_pod(
                    name,
                    self.namespace,
                    _request_timeout=self.config.api_timeout,
                )
                if pod.metadata.uid != uid:
                    raise RuntimeError(
                        "Replacement pod detected during cleanup"
                    )
            except ApiException as exc:
                if exc.status == 404:
                    session.close()
                    del self.sessions[session.id]
                    self.provenance.setdefault("deleted_pod_uids", []).append(
                        uid
                    )
                    return
                raise
            time.sleep(0.25)
        raise TimeoutError("Sandbox pod termination was not confirmed")

    def close(self) -> None:
        """Remove owned sessions and the volume without hiding incomplete cleanup.

        Raises:
            RuntimeError: A session or volume could not be removed.
        """  # noqa: DOC503 - API errors and timeouts are caught and aggregated.
        errors = []
        api = self.sandbox.core_api
        try:
            pods = api.list_namespaced_pod(
                self.namespace,
                label_selector=f"endless-workspace={self.token}",
                _request_timeout=self.config.api_timeout,
            ).items
            tracked = {uid for _, _, uid in self.sessions.values()}
            for pod in pods:
                if pod.metadata.uid in tracked:
                    continue
                name, uid = pod.metadata.name, pod.metadata.uid
                api.delete_namespaced_pod(
                    name,
                    self.namespace,
                    body=V1DeleteOptions(
                        grace_period_seconds=5,
                        preconditions=V1Preconditions(uid=uid),
                    ),
                    _request_timeout=self.config.api_timeout,
                )
                deadline = time.monotonic() + self.config.cleanup_timeout
                while time.monotonic() < deadline:
                    try:
                        existing = api.read_namespaced_pod(
                            name,
                            self.namespace,
                            _request_timeout=self.config.api_timeout,
                        )
                        if existing.metadata.uid != uid:
                            raise RuntimeError("Orphan pod identity changed")
                    except ApiException as exc:
                        if exc.status == 404:
                            self.provenance.setdefault(
                                "deleted_pod_uids", []
                            ).append(uid)
                            break
                        raise
                    time.sleep(0.25)
                else:
                    raise TimeoutError("Failed-start sandbox pod remains")
            if self.volume_attempted and self.pvc_uid is None:
                try:
                    claim = api.read_namespaced_persistent_volume_claim(
                        self.name,
                        self.namespace,
                        _request_timeout=self.config.api_timeout,
                    )
                    if (claim.metadata.labels or {}).get(
                        "endless-workspace"
                    ) != self.token:
                        raise RuntimeError(
                            "Workspace volume ownership differs"
                        )
                    self.pvc_uid = claim.metadata.uid
                except ApiException as exc:
                    if exc.status != 404:
                        raise
        except Exception as exc:
            errors.append(str(exc))
        for session, _, _ in list(self.sessions.values()):
            try:
                self.destroy_session(session)
            except Exception as exc:
                errors.append(str(exc))
        if not errors and self.pvc_uid:
            try:
                self.sandbox.core_api.delete_namespaced_persistent_volume_claim(
                    self.name,
                    self.namespace,
                    body=V1DeleteOptions(
                        preconditions=V1Preconditions(uid=self.pvc_uid)
                    ),
                    _request_timeout=self.config.api_timeout,
                )
                deadline = time.monotonic() + self.config.cleanup_timeout
                while time.monotonic() < deadline:
                    try:
                        self.sandbox.core_api.read_namespaced_persistent_volume_claim(
                            self.name,
                            self.namespace,
                            _request_timeout=self.config.api_timeout,
                        )
                    except ApiException as exc:
                        if exc.status == 404:
                            self.pvc_uid = None
                            break
                        raise
                    time.sleep(0.25)
                if self.pvc_uid:
                    raise TimeoutError(
                        "Workspace PVC deletion was not confirmed"
                    )
            except ApiException as exc:
                if exc.status == 404:
                    self.pvc_uid = None
                else:
                    errors.append(str(exc))
            except Exception as exc:
                errors.append(str(exc))
        self.provenance["cleanup_complete"] = not errors
        self.provenance["cleanup_errors"] = errors
        if errors:
            raise RuntimeError(
                "Workspace cleanup failed: " + "; ".join(errors)
            )
