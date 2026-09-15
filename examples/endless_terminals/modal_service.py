"""Bound one authenticated Modal GPU sandbox to a native training run."""

from __future__ import annotations

import hashlib
import json
import math
import secrets
import time
import urllib.error
import urllib.request
from pathlib import Path
from types import TracebackType
from typing import Any, Literal
from urllib.parse import urlsplit

from checkpoint_download import NoRedirect
from pydantic import BaseModel, ConfigDict, Field

# The backend stays on loopback. Only this authenticated port gets a tunnel.
PROXY_SOURCE = r"""
import hmac
import http.client
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

KEY = os.environ.pop("ENDLESS_API_KEY")
HOP = {"connection", "transfer-encoding", "keep-alive", "proxy-authenticate", "proxy-authorization", "te", "trailer", "upgrade"}

class Handler(BaseHTTPRequestHandler):
    def log_message(self, *_args):
        pass

    def forward(self):
        self.connection.settimeout(600)
        if not hmac.compare_digest(self.headers.get("X-API-Key", ""), KEY):
            self.send_error(401)
            return
        if self.headers.get("Transfer-Encoding"):
            self.send_error(400)
            return
        try:
            size = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self.send_error(400)
            return
        if not 0 <= size <= 64 * 1024 * 1024:
            self.send_error(413)
            return
        if not self.path.startswith("/") or self.path.startswith("//"):
            self.send_error(400)
            return
        headers = {k: v for k, v in self.headers.items() if k.lower() not in HOP | {"x-api-key", "x-forwarded-proto", "x-forwarded-host"}}
        headers["X-Forwarded-Proto"] = "https"
        connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=600)
        started = False
        try:
            connection.request(self.command, self.path, self.rfile.read(size), headers)
            response = connection.getresponse()
            self.send_response(response.status)
            for key, value in response.getheaders():
                if key.lower() not in HOP:
                    self.send_header(key, value)
            self.send_header("Connection", "close")
            self.end_headers()
            started = True
            if self.command != "HEAD":
                while chunk := response.read(1024 * 1024):
                    self.wfile.write(chunk)
        except (OSError, http.client.HTTPException):
            if not started:
                self.send_error(502)
        finally:
            connection.close()
            self.close_connection = True

    do_GET = do_POST = do_PUT = do_PATCH = do_DELETE = do_OPTIONS = do_HEAD = forward

ThreadingHTTPServer(("0.0.0.0", 8001), Handler).serve_forever()
"""


class ModalServiceConfig(BaseModel):
    """Pin the workspace and resources for the bounded 7B pilot."""

    model_config = ConfigDict(extra="forbid", frozen=True)
    backend: Literal["modal"] = "modal"
    training_image: str = Field(pattern=r"^[^\s@]+@sha256:[0-9a-f]{64}$")
    imported_image_id: str | None = Field(
        default=None,
        pattern=r"^im-[A-Za-z0-9]+$",
        description="Previously verified Modal import of training_image. This "
        "is an explicit operational pairing; the adapter does not infer or "
        "verify the registry digest associated with an existing Modal image.",
    )
    workspace: str = Field(default="zenml-io", pattern=r"^\S+$")
    modal_environment: str = Field(default="dev", pattern=r"^\S+$")
    gpu: Literal["H200"] = "H200"
    memory_mib: int = Field(default=262144, ge=262144, le=262144)
    cpu: int = Field(default=8, ge=8, le=16)
    startup_timeout: int = Field(default=1800, gt=0, le=1800)
    serving_deadline: int = Field(default=5400, gt=0, le=5400)
    cleanup_timeout: int = Field(default=180, gt=0, le=300)
    inference_gpu_memory_utilization: float = Field(default=0.5, gt=0, le=0.95)


class ModalTrainingService:
    """Start, verify, diagnose, and terminate one authenticated GPU service."""

    def __init__(
        self,
        config: ModalServiceConfig,
        model: dict[str, str],
        run_id: str,
        directory: Path,
    ) -> None:
        """Prepare a service without allocating remote resources.

        Args:
            config: Pinned resource and placement settings.
            model: Immutable model name and revision.
            run_id: Owning ZenML run ID.
            directory: Local lifecycle evidence directory.

        Raises:
            ValueError: Model identity is not immutable.
        """
        import re

        if not model.get("name") or not re.fullmatch(
            r"[0-9a-f]{40}", model.get("revision", "")
        ):
            raise ValueError(
                "An immutable model name and revision are required"
            )
        self.config, self.model, self.directory = (
            config,
            dict(model),
            directory,
        )
        self.api_key = "tml-native-" + secrets.token_hex(32)
        self.name = "endless-training-" + secrets.token_hex(8)
        self.base_url = self.service_host = ""
        self.identity: dict[str, Any] = {
            "server_kind": "skyrl",
            "backend": "modal_sandbox",
            "run_id": run_id,
            "training_image": config.training_image,
            "resources": {
                "gpu": config.gpu,
                "memory_mib": config.memory_mib,
                "cpu": config.cpu,
            },
        }
        self.cleanup_report: dict[str, Any] = {
            "complete": False,
            "errors": [],
            "diagnostic_errors": [],
        }
        self._sandbox: Any = None
        self._backend_process: Any = None
        self._allocation_attempted = False
        self._deadline = 0.0
        self._startup_deadline = 0.0
        self._entered = False
        self._closed = False
        self._backend_config: dict[str, Any] = {}
        self._source_hashes: dict[str, str] = {}

    @property
    def serving_seconds_remaining(self) -> float:
        """Return the remaining GPU lifetime including startup."""
        return max(0.0, self._deadline - time.monotonic())

    def __enter__(self) -> ModalTrainingService:
        """Create and authenticate the service, cleaning up failed startup.

        Returns:
            This ready service.

        Raises:
            RuntimeError: This service instance has already been entered.
            BaseException: Placement, allocation, startup, or verification fails.
        """
        if self._entered:
            raise RuntimeError("Training service sessions cannot be reused")
        self._entered = True
        self.directory.mkdir(parents=True, exist_ok=True)
        self._deadline = time.monotonic() + self.config.serving_deadline
        self._startup_deadline = min(
            self._deadline, time.monotonic() + self.config.startup_timeout
        )
        try:
            self._start()
            self._wait_ready()
            self._write("native-service-identity.json", self.identity)
            return self
        except BaseException:
            self._finish()
            raise

    def _start(self) -> None:
        import modal

        from zenml.client import Client
        from zenml.integrations.modal import sandbox_utils
        from zenml.integrations.modal.sandboxes.modal_sandbox import (
            ModalSandbox,
        )

        stack = Client().active_stack
        component = stack.sandbox
        if not isinstance(component, ModalSandbox):
            raise TypeError("Select a Modal sandbox in the active stack")
        if component.config.modal_environment != self.config.modal_environment:
            raise ValueError(
                f"Active sandbox must select Modal environment {self.config.modal_environment}"
            )
        if not component.config.token_id or not component.config.token_secret:
            raise ValueError("Modal sandbox requires explicit credentials")
        client = sandbox_utils.create_modal_client_from_credentials(
            token_id=component.config.token_id,
            token_secret=component.config.token_secret,
        )
        workspace = modal.Workspace.from_context(client=client).hydrate()
        if workspace.name != self.config.workspace:
            raise ValueError(
                f"Authenticated Modal workspace must be {self.config.workspace}"
            )
        modal.Environment.from_name(
            self.config.modal_environment,
            create_if_missing=False,
            client=client,
        ).hydrate()
        self.identity.update(
            workspace=workspace.name,
            modal_environment=self.config.modal_environment,
        )
        app = modal.App.lookup(
            component.config.app_name,
            create_if_missing=True,
            environment_name=self.config.modal_environment,
            client=client,
        )
        if self.config.imported_image_id:
            image = modal.Image.from_id(
                self.config.imported_image_id, client=client
            )
            self.identity["image_selection"] = "explicit_operational_pairing"
        else:
            registry = stack.container_registry
            credentials = (
                registry.credentials
                if registry
                and registry.is_valid_image_name_for_registry(
                    self.config.training_image
                )
                else None
            )
            image = sandbox_utils.get_modal_image_from_registry(
                self.config.training_image, registry_credentials=credentials
            )
            self.identity["image_selection"] = "registry_import"
        imported_image = image
        # Sandbox command arguments otherwise append to the Docker entrypoint,
        # which would start the baked server before current sources are uploaded.
        image = image.entrypoint([])
        self._allocation_attempted = True
        self._sandbox = modal.Sandbox.create(
            "sleep",
            "infinity",
            app=app,
            image=image,
            gpu=self.config.gpu,
            cpu=self.config.cpu,
            memory=self.config.memory_mib,
            timeout=max(1, math.floor(self.serving_seconds_remaining)),
            encrypted_ports=[8001],
            env={
                "SKYRL_MODEL_NAME": self.model["name"],
                "SKYRL_MODEL_REVISION": self.model["revision"],
                "SKYRL_DUMP_INFRA_LOG_TO_STDOUT": "1",
                "RAY_DEFAULT_OBJECT_STORE_MAX_MEMORY_BYTES": "1073741824",
            },
            client=client,
            environment_name=self.config.modal_environment,
            name=self.name,
        )
        self.identity["sandbox_id"] = self._sandbox.object_id
        self.identity["imported_modal_image_id"] = imported_image.object_id
        self.identity["modal_image_id"] = image.object_id
        self._write("native-service-identity.json", self.identity)
        self._exec(
            [
                "mkdir",
                "-p",
                "/tmp/terminal-training",
                "/models",
                "/checkpoints",
            ]
        )
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
            name: hashlib.sha256(value.encode()).hexdigest()
            for name, value in files.items()
        }
        self.identity["source_sha256"] = self._source_hashes
        files["proxy.py"] = PROXY_SOURCE
        for name, value in files.items():
            self._sandbox.filesystem.write_text(
                value, "/tmp/terminal-training/" + name
            )
        self.identity["proxy_sha256"] = hashlib.sha256(
            PROXY_SOURCE.encode()
        ).hexdigest()
        self._write(
            "training-capacity.json",
            self._exec(
                [
                    "python",
                    "/tmp/terminal-training/diagnostics.py",
                    "--collect",
                ]
            ),
        )
        self._sandbox.exec(
            "bash",
            "-c",
            "exec python /tmp/terminal-training/proxy.py > /checkpoints/proxy.log 2>&1",
            secrets=[
                modal.Secret.from_dict({"ENDLESS_API_KEY": self.api_key})
            ],
        )
        self._backend_process = self._sandbox.exec(
            "bash",
            "-c",
            "exec python /tmp/terminal-training/entrypoint.py > /checkpoints/training.log 2>&1",
            workdir="/opt/skyrl",
        )
        self.base_url = self._sandbox.tunnels(timeout=60)[8001].url.rstrip("/")
        self.service_host = urlsplit(self.base_url).hostname or ""
        self.identity["service_url"] = self.base_url
        self._write("native-service-identity.json", self.identity)
        from training_client import validate_training_url

        validate_training_url(self.base_url, self.service_host)

    def _exec(
        self, command: list[str], limit: int = 2097152, timeout: int = 60
    ) -> str:
        process = self._sandbox.exec(*command, timeout=timeout)
        # Output is bounded at its trusted producer; do not collect Ray's full logs.
        stdout, stderr = process.stdout.read(), process.stderr.read()
        process.wait()
        if process.returncode:
            raise RuntimeError(
                f"Training diagnostic command failed: {stderr[:2000]}"
            )
        if len(stdout.encode()) > limit:
            raise RuntimeError("Remote evidence exceeded its bound")
        return str(stdout)

    def _wait_ready(self) -> None:
        deadline = self._startup_deadline
        opener = urllib.request.build_opener(NoRedirect())
        while time.monotonic() < deadline:
            if self._sandbox.poll() is not None:
                raise RuntimeError(
                    "Modal training sandbox exited during startup"
                )
            self._check_backend_running()
            try:
                request = urllib.request.Request(
                    self.base_url + "/api/v1/healthz",
                    headers={"X-API-Key": self.api_key},
                )
                with opener.open(
                    request,
                    timeout=min(10, max(1, deadline - time.monotonic())),
                ) as response:
                    if response.status == 200:
                        break
            except (urllib.error.URLError, TimeoutError):
                pass
            time.sleep(2)
        else:
            raise TimeoutError("Modal training service did not become ready")
        try:
            opener.open(self.base_url + "/api/v1/healthz", timeout=10)
        except urllib.error.HTTPError as error:
            if error.code != 401:
                raise RuntimeError(
                    "Training proxy did not reject missing credentials"
                ) from error
        else:
            raise RuntimeError(
                "Training proxy accepted an unauthenticated request"
            )
        identity = json.loads(
            self._exec(
                ["cat", "/checkpoints/server-identity.json"], limit=65536
            )
        )
        if (
            identity.get("model_name") != self.model["name"]
            or identity.get("model_revision") != self.model["revision"]
            or identity.get("backend_config") != self._backend_config
            or identity.get("source_sha256") != self._source_hashes
        ):
            raise RuntimeError(
                "Training server model, configuration, or source identity mismatch"
            )
        self.identity["training_server"] = identity
        self._check_backend_running()

    def _check_backend_running(self) -> None:
        if self._backend_process is None:
            raise RuntimeError(
                "The owned training backend has not been launched"
            )
        code = self._backend_process.poll()
        if code is not None:
            raise RuntimeError(
                f"The owned training backend exited during startup (exit {code})"
            )

    def _write(self, name: str, value: Any) -> None:
        text = (
            value
            if isinstance(value, str)
            else json.dumps(value, indent=2, default=str)
        )
        (self.directory / name).write_text(
            text.replace(self.api_key, "[REDACTED]")[:2097152] + "\n"
        )

    def _finish(self) -> None:
        if self._closed:
            return
        try:
            if self._sandbox is not None:
                for name, command in (
                    (
                        "training-main.log",
                        ["tail", "-c", "65536", "/checkpoints/training.log"],
                    ),
                    (
                        "training-proxy.log",
                        ["tail", "-c", "8192", "/checkpoints/proxy.log"],
                    ),
                    (
                        "training-worker-logs.json",
                        [
                            "python",
                            "/tmp/terminal-training/diagnostics.py",
                            "--collect",
                        ],
                    ),
                ):
                    try:
                        self._write(name, self._exec(command, timeout=30))
                    except Exception as error:
                        self.cleanup_report["diagnostic_errors"].append(
                            type(error).__name__
                        )
        finally:
            try:
                if self._sandbox is not None:
                    self._sandbox.terminate()
                    deadline = time.monotonic() + self.config.cleanup_timeout
                    while self._sandbox.poll() is None:
                        if time.monotonic() >= deadline:
                            raise TimeoutError(
                                "Modal GPU sandbox termination was not confirmed"
                            )
                        time.sleep(1)
                if self._sandbox is None and self._allocation_attempted:
                    raise RuntimeError(
                        "Modal allocation outcome is unknown; cleanup cannot be confirmed "
                        f"for sandbox {self.name} in {self.config.workspace}/{self.config.modal_environment}"
                    )
                self.cleanup_report["complete"] = True
                self._closed = True
            except Exception as error:
                self.cleanup_report["errors"].append(
                    str(error).replace(self.api_key, "[REDACTED]")[:2000]
                )
            self._write("native-service-cleanup.json", self.cleanup_report)

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """Collect evidence and confirm termination after success or failure.

        Args:
            exc_type: Original exception class.
            exc: Original exception instance.
            traceback: Original traceback.

        Raises:
            RuntimeError: Cleanup remains incomplete after successful training.
        """
        self._finish()
        if not self.cleanup_report["complete"] and exc is None:
            raise RuntimeError(
                "Modal training cleanup incomplete; inspect cleanup report"
            )
