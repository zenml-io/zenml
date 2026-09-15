"""Bounded, authenticated GPU training service in the active native sandbox."""

from __future__ import annotations

import hashlib
import json
import os
import re
import secrets
import time
import urllib.error
import urllib.request
from functools import partial
from pathlib import Path
from types import TracebackType
from typing import TYPE_CHECKING, Any, Callable, cast

from pydantic import BaseModel, ConfigDict, Field

if TYPE_CHECKING:
    from zenml.integrations.kubernetes.sandboxes.kubernetes_sandbox import (
        KubernetesSandbox,
    )


class NativeServiceConfig(BaseModel):
    """Immutable images and finite resource limits for one GPU service."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    training_image: str = Field(pattern=r"^[^\s]+@sha256:[0-9a-f]{64}$")
    proxy_image: str = Field(pattern=r"^[^\s]+@sha256:[0-9a-f]{64}$")
    startup_timeout: int = Field(default=1500, gt=0, le=1800)
    serving_deadline: int = Field(default=3600, gt=0, le=5400)
    cleanup_timeout: int = Field(default=180, gt=0, le=300)
    node_selector: dict[str, str] = Field(
        default_factory=lambda: {"pool": "gpu"}
    )
    tolerations: list[dict[str, str]] = Field(
        default_factory=lambda: [
            {
                "key": "pool",
                "operator": "Equal",
                "value": "gpu",
                "effect": "NoSchedule",
            }
        ]
    )
    cpu_request: str = "4"
    memory_request: str = "26Gi"
    memory_limit: str = "28Gi"
    inference_gpu_memory_utilization: float = Field(
        default=0.35, gt=0, le=0.95
    )


def build_proxy_config(api_key: str) -> str:
    """Build nginx configuration authenticating every route.

    Args:
        api_key: Random native service credential, never written as evidence.

    Returns:
        Configuration suitable for nginx-unprivileged with read-only rootfs.

    Raises:
        ValueError: The credential is not a generated native service key.
    """
    if not re.fullmatch(r"tml-native-[0-9a-f]{64}", api_key):
        raise ValueError("Expected a generated native service key")
    return f"""worker_processes 1;
error_log /dev/stderr warn;
pid /tmp/nginx.pid;
events {{ worker_connections 1024; }}
http {{
    access_log off;
    client_body_temp_path /tmp/client_temp;
    proxy_temp_path /tmp/proxy_temp;
    fastcgi_temp_path /tmp/fastcgi_temp;
    uwsgi_temp_path /tmp/uwsgi_temp;
    scgi_temp_path /tmp/scgi_temp;
    map $http_x_api_key $authenticated {{
        default 0;
        ~^{api_key}$ 1;
    }}
    server {{
        listen 8001;
        if ($authenticated = 0) {{ return 401; }}
        client_max_body_size 64m;
        location / {{
            proxy_pass http://127.0.0.1:8000;
            proxy_set_header Host $http_host;
            proxy_set_header X-API-Key "";
            proxy_buffering off;
            proxy_read_timeout 600s;
        }}
    }}
}}
"""


class _NoHealthRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        req: urllib.request.Request,
        fp: Any,
        code: int,
        msg: str,
        headers: Any,
        newurl: str,
    ) -> None:
        return None


class NativeTrainingService:
    """Create one GPU Job and capture evidence before UID-guarded cleanup."""

    def __init__(
        self,
        config: NativeServiceConfig,
        model: dict[str, str],
        run_id: str,
        directory: Path,
    ) -> None:
        """Prepare a service without contacting Kubernetes.

        Args:
            config: Validated service settings.
            model: Exact Hugging Face model name and immutable revision.
            run_id: Training run identifier for evidence.
            directory: Directory for sanitized lifecycle evidence.

        Raises:
            ValueError: The model lacks an immutable revision or name.
        """
        if not model.get("name") or not re.fullmatch(
            r"[0-9a-f]{40}", model.get("revision", "")
        ):
            raise ValueError(
                "Model name and immutable 40-character revision are required"
            )
        self.config = config
        self.model = dict(model)
        self.directory = directory
        self.token = secrets.token_hex(16)
        self.name = "endless-training-" + self.token[:16]
        self.api_key = "tml-native-" + secrets.token_hex(32)
        self._sandbox = self._select_sandbox()
        self.namespace = self._sandbox.config.kubernetes_namespace
        self.service_host = f"{self.name}.{self.namespace}.svc.cluster.local"
        self.base_url = f"http://{self.service_host}:8001"
        self.identity: dict[str, Any] = {
            "server_kind": "skyrl",
            "backend": "kubernetes_sandbox",
            "run_id": run_id,
            "job_name": self.name,
            "training_image": config.training_image,
            "proxy_image": config.proxy_image,
        }
        self.cleanup_report: dict[str, Any] = {
            "complete": False,
            "errors": [],
            "diagnostic_errors": [],
        }
        self._attempted: set[str] = set()
        self._uids: dict[str, str] = {}
        self._serving_deadline = 0.0
        self._operation_deadline = 0.0
        self._pod_name: str | None = None
        self._closed = False
        self._entered = False
        self._backend_config: dict[str, Any] = {}
        self._source_hashes: dict[str, str] = {}
        self._client: Any = None

    @property
    def serving_seconds_remaining(self) -> float:
        """Remaining total Job lifetime, including startup time."""
        return max(0.0, self._serving_deadline - time.monotonic())

    def __enter__(self) -> NativeTrainingService:
        """Start the service and verify its exact model and source identity.

        Returns:
            This authenticated service session.

        Raises:
            RuntimeError: Startup, identity verification, or ownership fails.
            BaseException: Startup fails or is interrupted; cleanup runs first.
        """
        if self._entered:
            raise RuntimeError("Native service sessions cannot be reused")
        self._entered = True
        self.directory.mkdir(parents=True, exist_ok=True)
        self._serving_deadline = (
            time.monotonic() + self.config.serving_deadline
        )
        self._operation_deadline = min(
            self._serving_deadline,
            time.monotonic() + self.config.startup_timeout,
        )
        try:
            self._connect()
            job, secret, service = self._manifests()
            self._create("job", job)
            owner = self._owner_reference("Job", self.name, self._uids["job"])
            for kind, body in (("secret", secret), ("service", service)):
                body["metadata"]["ownerReferences"] = [owner]
                self._create(kind, body)
            self._wait_ready()
            self._write("native-service-identity.json", self.identity)
            return self
        except BaseException:
            self._finish()
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Capture diagnostics and delete owned resources.

        Args:
            exc_type: Exception type raised by the training operation.
            exc: Original training exception, if any.
            traceback: Original exception traceback.

        Raises:
            RuntimeError: Cleanup is incomplete after an otherwise successful run.
        """
        self._finish()
        if not self.cleanup_report["complete"] and exc is None:
            raise RuntimeError(
                "Native service cleanup incomplete; inspect cleanup report"
            )

    @staticmethod
    def _select_sandbox() -> KubernetesSandbox:
        from zenml.client import Client
        from zenml.integrations.kubernetes.sandboxes.kubernetes_sandbox import (
            KubernetesSandbox,
        )

        sandbox = Client().active_stack.sandbox
        if (
            not isinstance(sandbox, KubernetesSandbox)
            or not sandbox.config.incluster
        ):
            raise RuntimeError(
                "Native training requires an in-cluster KubernetesSandbox"
            )
        return sandbox

    def _connect(self) -> None:
        from kubernetes import client as k8s

        controller = os.environ.get("HOSTNAME")
        if not controller or not os.environ.get("KUBERNETES_SERVICE_HOST"):
            raise RuntimeError(
                "Native training must run inside its Kubernetes controller pod"
            )
        self._client = self._sandbox.build_kube_client()
        self._client.configuration.retries = 0
        self._core = k8s.CoreV1Api(self._client)
        self._batch = k8s.BatchV1Api(self._client)
        pod = self._call(
            self._core.read_namespaced_pod, controller, self.namespace
        )
        if pod.metadata.name != controller or not pod.metadata.uid:
            raise RuntimeError("Controller pod identity is missing")
        self._controller_owner = self._owner_reference(
            "Pod", controller, pod.metadata.uid
        )
        self.identity.update(
            namespace=self.namespace,
            controller_pod=controller,
            controller_uid=pod.metadata.uid,
            service_host=self.service_host,
        )

    @staticmethod
    def _owner_reference(kind: str, name: str, uid: str) -> dict[str, Any]:
        return {
            "apiVersion": "batch/v1" if kind == "Job" else "v1",
            "kind": kind,
            "name": name,
            "uid": uid,
            "blockOwnerDeletion": False,
        }

    def _call(
        self, function: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        remaining = self._operation_deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError("Native service operation deadline exceeded")
        return function(*args, **kwargs, _request_timeout=min(15.0, remaining))

    def _manifests(
        self,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        source = Path(__file__).with_name("training_server")
        files = {
            name: (source / name).read_text()
            for name in (
                "entrypoint.py",
                "backend_config.json",
                "diagnostics.py",
            )
        }
        self._backend_config = json.loads(files["backend_config.json"])
        self._backend_config[
            "generator.inference_engine.gpu_memory_utilization"
        ] = self.config.inference_gpu_memory_utilization
        files["backend_config.json"] = (
            json.dumps(self._backend_config, indent=2) + "\n"
        )
        self._source_hashes = {
            name: hashlib.sha256(content.encode()).hexdigest()
            for name, content in files.items()
        }
        self.identity["source_sha256"] = self._source_hashes
        metadata = {"name": self.name, "labels": {"endless-owner": self.token}}
        source_items = [{"key": name, "path": name} for name in files]
        security = {
            "runAsNonRoot": True,
            "runAsUser": 1000,
            "allowPrivilegeEscalation": False,
            "capabilities": {"drop": ["ALL"]},
        }
        main = {
            "name": "main",
            "image": self.config.training_image,
            "command": ["python", "/opt/terminal-training/entrypoint.py"],
            "securityContext": security,
            "env": [
                {"name": key, "value": value}
                for key, value in {
                    "SKYRL_MODEL_NAME": self.model["name"],
                    "SKYRL_MODEL_REVISION": self.model["revision"],
                    "SKYRL_DUMP_INFRA_LOG_TO_STDOUT": "1",
                    "RAY_DEFAULT_OBJECT_STORE_MAX_MEMORY_BYTES": "1073741824",
                }.items()
            ],
            "resources": {
                "requests": {
                    "cpu": self.config.cpu_request,
                    "memory": self.config.memory_request,
                    "nvidia.com/gpu": "1",
                },
                "limits": {
                    "memory": self.config.memory_limit,
                    "nvidia.com/gpu": "1",
                },
            },
            "volumeMounts": [
                {
                    "name": "source",
                    "mountPath": "/opt/terminal-training",
                    "readOnly": True,
                },
                {"name": "models", "mountPath": "/models"},
                {"name": "checkpoints", "mountPath": "/checkpoints"},
                {"name": "shm", "mountPath": "/dev/shm"},
            ],
        }
        proxy = {
            "name": "auth-proxy",
            "image": self.config.proxy_image,
            "command": [
                "nginx",
                "-c",
                "/etc/nginx/nginx.conf",
                "-g",
                "daemon off;",
            ],
            "securityContext": {
                **security,
                "runAsUser": 101,
                "readOnlyRootFilesystem": True,
            },
            "resources": {
                "requests": {"cpu": "50m", "memory": "32Mi"},
                "limits": {"cpu": "500m", "memory": "128Mi"},
            },
            "ports": [{"containerPort": 8001}],
            "volumeMounts": [
                {
                    "name": "proxy-config",
                    "mountPath": "/etc/nginx",
                    "readOnly": True,
                },
                {"name": "proxy-tmp", "mountPath": "/tmp"},
            ],
        }
        job = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                **metadata,
                "ownerReferences": [self._controller_owner],
            },
            "spec": {
                "backoffLimit": 0,
                "activeDeadlineSeconds": self.config.serving_deadline,
                "ttlSecondsAfterFinished": 180,
                "template": {
                    "metadata": {"labels": metadata["labels"]},
                    "spec": {
                        "restartPolicy": "Never",
                        "automountServiceAccountToken": False,
                        "hostNetwork": False,
                        "hostPID": False,
                        "hostIPC": False,
                        "securityContext": {
                            "fsGroup": 1000,
                            "seccompProfile": {"type": "RuntimeDefault"},
                        },
                        "nodeSelector": self.config.node_selector,
                        "tolerations": self.config.tolerations,
                        "containers": [main, proxy],
                        "volumes": [
                            {
                                "name": "source",
                                "secret": {
                                    "secretName": self.name,
                                    "items": source_items,
                                },
                            },
                            {
                                "name": "proxy-config",
                                "secret": {
                                    "secretName": self.name,
                                    "items": [
                                        {
                                            "key": "nginx.conf",
                                            "path": "nginx.conf",
                                        }
                                    ],
                                },
                            },
                            {"name": "models", "emptyDir": {}},
                            {"name": "checkpoints", "emptyDir": {}},
                            {
                                "name": "shm",
                                "emptyDir": {
                                    "medium": "Memory",
                                    "sizeLimit": "8Gi",
                                },
                            },
                            {
                                "name": "proxy-tmp",
                                "emptyDir": {"sizeLimit": "128Mi"},
                            },
                        ],
                    },
                },
            },
        }
        secret = {
            "apiVersion": "v1",
            "kind": "Secret",
            "metadata": dict(metadata),
            "immutable": True,
            "type": "Opaque",
            "stringData": {
                **files,
                "nginx.conf": build_proxy_config(self.api_key),
            },
        }
        service = {
            "apiVersion": "v1",
            "kind": "Service",
            "metadata": dict(metadata),
            "spec": {
                "type": "ClusterIP",
                "selector": metadata["labels"],
                "ports": [
                    {
                        "name": "authenticated-api",
                        "port": 8001,
                        "targetPort": 8001,
                    }
                ],
            },
        }
        return job, secret, service

    def _resource_api(self, kind: str, operation: str) -> Callable[..., Any]:
        # Kubernetes generated methods have no common resource protocol.
        return cast(
            Callable[..., Any],
            getattr(
                self._batch if kind == "job" else self._core,
                f"{operation}_namespaced_{kind}",
            ),
        )

    def _read(self, kind: str) -> Any:
        from kubernetes.client.rest import ApiException

        try:
            obj = self._call(
                self._resource_api(kind, "read"), self.name, self.namespace
            )
        except ApiException as error:
            if error.status == 404:
                return None
            raise
        if not obj.metadata.uid or obj.metadata.name != self.name:
            raise RuntimeError(f"Refusing {kind}: resource identity missing")
        if (obj.metadata.labels or {}).get("endless-owner") != self.token:
            raise RuntimeError(f"Refusing {kind}: ownership token mismatch")
        if kind in self._uids and obj.metadata.uid != self._uids[kind]:
            raise RuntimeError(f"Refusing {kind}: UID changed")
        self._uids[kind] = obj.metadata.uid
        return obj

    def _create(self, kind: str, body: dict[str, Any]) -> None:
        self._attempted.add(kind)
        # Register the name before sending: a transport failure may mean the
        # object exists. Cleanup reconciles it using the unguessable owner token.
        obj = self._call(
            self._resource_api(kind, "create"), self.namespace, body
        )
        if (
            not obj.metadata.uid
            or obj.metadata.labels.get("endless-owner") != self.token
        ):
            raise RuntimeError(f"Created {kind} has an invalid identity")
        self._uids[kind] = obj.metadata.uid
        self.identity[f"{kind}_uid"] = obj.metadata.uid

    def _pods(self) -> list[Any]:
        pods = self._call(
            self._core.list_namespaced_pod,
            self.namespace,
            label_selector=f"endless-owner={self.token}",
        ).items
        for pod in pods:
            if pod.metadata.labels.get(
                "endless-owner"
            ) != self.token or not any(
                owner.kind == "Job"
                and owner.name == self.name
                and owner.uid == self._uids.get("job")
                for owner in (pod.metadata.owner_references or [])
            ):
                raise RuntimeError("Refusing pod: Job ownership mismatch")
        return cast(list[Any], pods)

    def _wait_ready(self) -> None:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}), _NoHealthRedirect()
        )
        while time.monotonic() < self._operation_deadline:
            job = self._read("job")
            if job is None:
                raise RuntimeError("Training Job disappeared during startup")
            if any(
                condition.type == "Failed" and condition.status == "True"
                for condition in (job.status.conditions or [])
            ):
                raise RuntimeError("Training Job failed during startup")
            pods = self._pods()
            if len(pods) > 1:
                raise RuntimeError(
                    "Training Job unexpectedly created multiple pods"
                )
            if pods:
                pod = pods[0]
                self._pod_name = pod.metadata.name
                self.identity.update(
                    pod_name=pod.metadata.name, pod_uid=pod.metadata.uid
                )
                for container in pod.status.container_statuses or []:
                    if container.state.terminated:
                        raise RuntimeError(
                            f"Training container {container.name} terminated before readiness"
                        )
                request = urllib.request.Request(
                    self.base_url + "/api/v1/healthz",
                    headers={"X-API-Key": self.api_key},
                )
                try:
                    with opener.open(
                        request,
                        timeout=min(
                            5,
                            max(
                                0.1,
                                self._operation_deadline - time.monotonic(),
                            ),
                        ),
                    ) as response:
                        healthy = response.status == 200
                except (OSError, urllib.error.URLError):
                    healthy = False
                if healthy:
                    self._verify_server()
                    return
            time.sleep(
                min(2.0, max(0.0, self._operation_deadline - time.monotonic()))
            )
        raise TimeoutError("Native training service startup deadline exceeded")

    def _exec(self, command: list[str], max_bytes: int = 1048576) -> str:
        from kubernetes import client as k8s
        from kubernetes.stream import stream

        if not self._pod_name:
            raise RuntimeError(
                "No owned training pod available for diagnostics"
            )
        deadline = min(self._operation_deadline, time.monotonic() + 15)
        # stream changes ApiClient's transport; never reuse the REST client.
        with self._sandbox.build_kube_client() as api_client:
            api_client.configuration.retries = 0
            api = k8s.CoreV1Api(api_client)
            socket = self._call(
                stream,
                api.connect_get_namespaced_pod_exec,
                self._pod_name,
                self.namespace,
                container="main",
                command=command,
                stdout=True,
                stderr=True,
                stdin=False,
                tty=False,
                _preload_content=False,
            )
            output = ""
            try:
                while socket.is_open() and time.monotonic() < deadline:
                    socket.update(
                        timeout=min(1, max(0.01, deadline - time.monotonic()))
                    )
                    output += cast(str, socket.read_stdout())
                    if len(output.encode()) > max_bytes:
                        raise RuntimeError(
                            "Remote output exceeded evidence bound"
                        )
                output += cast(str, socket.read_stdout())
                if socket.is_open():
                    raise TimeoutError("Training pod exec deadline exceeded")
                if socket.returncode != 0:
                    raise RuntimeError("Training pod exec failed")
                if len(output.encode()) > max_bytes:
                    raise RuntimeError("Remote output exceeded evidence bound")
                return output
            finally:
                socket.close()

    def _verify_server(self) -> None:
        identity = json.loads(
            self._exec(
                ["cat", "/checkpoints/server-identity.json"], max_bytes=65536
            )
        )
        if (
            identity.get("model_name") != self.model["name"]
            or identity.get("model_revision") != self.model["revision"]
        ):
            raise RuntimeError("Training server model identity mismatch")
        if identity.get("backend_config") != self._backend_config:
            raise RuntimeError(
                "Training server backend configuration mismatch"
            )
        if identity.get("source_sha256") != self._source_hashes:
            raise RuntimeError("Training server source identity mismatch")
        self.identity["training_server"] = identity

    def _write(self, name: str, value: Any) -> None:
        data = (
            value
            if isinstance(value, str)
            else json.dumps(value, indent=2, default=str)
        )
        data = data.replace(self.api_key, "[REDACTED]")
        (self.directory / name).write_text(data[:2097152] + "\n")

    def _diagnostic(self, name: str, collect: Callable[[], Any]) -> None:
        try:
            self._write(name, collect())
        except Exception as error:
            self.cleanup_report["diagnostic_errors"].append(
                f"{name}: {type(error).__name__}: {error}".replace(
                    self.api_key, "[REDACTED]"
                )
            )

    def _capture(self) -> None:
        self._operation_deadline = time.monotonic() + 60
        pods = self._pods()
        for pod in pods[:1]:
            self._pod_name = pod.metadata.name
            self._write(
                "training-pod-status.json",
                {
                    "name": pod.metadata.name,
                    "uid": pod.metadata.uid,
                    "node": pod.spec.node_name,
                    "phase": pod.status.phase,
                    "reason": pod.status.reason,
                    "message": pod.status.message,
                    "containers": [
                        {
                            "name": status.name,
                            "ready": status.ready,
                            "restart_count": status.restart_count,
                            "state": status.state.to_dict(),
                        }
                        for status in (pod.status.container_statuses or [])
                    ],
                },
            )
            for container in ("main", "auth-proxy"):
                self._diagnostic(
                    f"training-{container}.log",
                    partial(
                        self._call,
                        self._core.read_namespaced_pod_log,
                        pod.metadata.name,
                        self.namespace,
                        container=container,
                        tail_lines=400,
                        limit_bytes=65536,
                    ),
                )
            self._diagnostic(
                "training-worker-logs.json",
                lambda: json.loads(
                    self._exec(
                        [
                            "python",
                            "/opt/terminal-training/diagnostics.py",
                            "--collect",
                        ],
                        max_bytes=2097152,
                    )
                ),
            )
            self._diagnostic(
                "training-pod-events.json",
                lambda: [
                    {
                        "reason": event.reason,
                        "message": event.message,
                        "type": event.type,
                        "count": event.count,
                    }
                    for event in self._call(
                        self._core.list_namespaced_event,
                        self.namespace,
                        field_selector=f"involvedObject.uid={pod.metadata.uid}",
                        limit=100,
                    ).items
                ],
            )

    def _cleanup(self) -> None:
        from kubernetes.client.rest import ApiException

        self._operation_deadline = (
            time.monotonic() + self.config.cleanup_timeout
        )
        pending = set(self._attempted)
        for kind in ("service", "job", "secret"):
            if kind not in pending:
                continue
            try:
                obj = self._read(kind)
                if obj is None:
                    pending.remove(kind)
                    continue
                self._call(
                    self._resource_api(kind, "delete"),
                    self.name,
                    self.namespace,
                    body={
                        "apiVersion": "v1",
                        "kind": "DeleteOptions",
                        "propagationPolicy": "Foreground",
                        "preconditions": {"uid": obj.metadata.uid},
                    },
                )
            except ApiException as error:
                if error.status != 404:
                    self.cleanup_report["errors"].append(
                        f"delete {kind}: {error}"
                    )
            except Exception as error:
                self.cleanup_report["errors"].append(f"delete {kind}: {error}")
        while time.monotonic() < self._operation_deadline:
            for kind in list(pending):
                try:
                    if self._read(kind) is None:
                        pending.remove(kind)
                except Exception as error:
                    self.cleanup_report["errors"].append(
                        f"verify {kind}: {error}"
                    )
                    pending.remove(kind)
            try:
                pods = self._pods() if "job" in self._attempted else []
            except Exception as error:
                self.cleanup_report["errors"].append(f"verify pods: {error}")
                break
            if not pending and not pods:
                self.cleanup_report["complete"] = not self.cleanup_report[
                    "errors"
                ]
                return
            time.sleep(
                min(1.0, max(0.0, self._operation_deadline - time.monotonic()))
            )
        self.cleanup_report["errors"].append(
            "Cleanup deadline reached or ownership verification failed"
        )

    def _finish(self) -> None:
        if self._closed:
            return
        self._closed = True
        if self._attempted:
            try:
                self._capture()
            except Exception as error:
                self.cleanup_report["diagnostic_errors"].append(
                    f"capture: {error}"
                )
            try:
                self._cleanup()
            except Exception as error:
                self.cleanup_report["errors"].append(f"cleanup: {error}")
        else:
            self.cleanup_report["complete"] = True
        self.cleanup_report = json.loads(
            json.dumps(self.cleanup_report, default=str).replace(
                self.api_key, "[REDACTED]"
            )
        )
        self._write("native-service-cleanup.json", self.cleanup_report)
        if self._client is not None:
            self._client.close()
