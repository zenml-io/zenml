"""Bounded Kubernetes inference with explicit ownership and GPU teardown."""

from __future__ import annotations

import json
import os
import re
import shutil
import socket
import subprocess
import time
import urllib.request
import uuid
from pathlib import Path
from typing import Any, cast


class KubernetesInference:
    """Create an isolated serving job and verify its worker is terminated."""

    def __init__(
        self,
        config: dict[str, Any],
        model: dict[str, str],
        run_id: str,
        evidence_directory: Path,
    ) -> None:
        """Configure a session without contacting cloud services.

        Args:
            config: Explicit cloud, Kubernetes, image, and timeout settings.
            model: Hugging Face model name and immutable revision.
            run_id: Label identifying the evaluation run.
            evidence_directory: Directory for operational evidence.

        Raises:
            ValueError: The serving image is not pinned by digest.
            RuntimeError: A required executable is unavailable.
        """
        self.server_kind = config.get("server_kind", "vllm")
        if self.server_kind not in {"vllm", "skyrl"}:
            raise ValueError("server_kind must be vllm or skyrl")
        image_key = (
            "training_image" if self.server_kind == "skyrl" else "vllm_image"
        )
        self.image = config[image_key]
        if not re.search(r"@sha256:[0-9a-f]{64}$", self.image):
            raise ValueError(
                f"{image_key} must use an immutable sha256 digest"
            )
        self.config, self.model = dict(config), dict(model)
        self.directory = evidence_directory
        self.token = uuid.uuid4().hex
        self.name = "endless-" + self.token[:20]
        self.identity = {
            "run_id": run_id,
            "job_name": self.name,
            "ownership_token": self.token,
            "model": self.model,
            "server_kind": self.server_kind,
            "image": self.image,
            image_key: self.image,
        }
        self.cleanup_report: dict[str, Any] = {"complete": False, "errors": []}
        self.base_url = ""
        self.uid: str | None = None
        self.attempted = False
        self._serving_deadline: float | None = None
        self.instance_id: str | None = None
        self.forward: subprocess.Popen[str] | None = None
        self.forward_log: Any = None
        self.env = {
            **os.environ,
            "AWS_PROFILE": config["aws_profile"],
            "AWS_DEFAULT_REGION": config["aws_region"],
            "AWS_REGION": config["aws_region"],
        }
        self.aws = shutil.which("aws")
        self.kubectl = shutil.which("kubectl")
        if not self.aws or not self.kubectl:
            raise RuntimeError("aws and kubectl must be available on PATH")

    @property
    def serving_seconds_remaining(self) -> float:
        """Return the conservative remaining job lifetime, including startup.

        Returns:
            Seconds before the serving deadline, or zero before creation.
            Reserve an additional margin before starting another episode.
        """
        if self._serving_deadline is None:
            return 0.0
        return max(0.0, self._serving_deadline - time.monotonic())

    def _call(self, args: list[str], timeout: float = 60) -> str:
        result = subprocess.run(
            args, env=self.env, capture_output=True, text=True, timeout=timeout
        )
        if result.returncode:
            raise RuntimeError(f"{args[0]} failed: {result.stderr[:2000]}")
        return result.stdout

    def _kube(self, *args: str) -> str:
        return self._call(
            [
                str(self.kubectl),
                "--context",
                self.config["kube_context"],
                *args,
            ]
        )

    def _aws(self, *args: str) -> dict[str, Any]:
        return cast(
            dict[str, Any],
            json.loads(
                self._call(
                    [
                        str(self.aws),
                        "--profile",
                        self.config["aws_profile"],
                        "--region",
                        self.config["aws_region"],
                        *args,
                        "--output",
                        "json",
                    ]
                )
            ),
        )

    def _group(self) -> dict[str, Any]:
        groups = self._aws(
            "autoscaling",
            "describe-auto-scaling-groups",
            "--auto-scaling-group-names",
            self.config["gpu_asg"],
        )["AutoScalingGroups"]
        if len(groups) != 1:
            raise RuntimeError(
                "Expected exactly one dedicated GPU autoscaling group"
            )
        return cast(dict[str, Any], groups[0])

    def _job(self) -> dict[str, Any] | None:
        raw = self._kube(
            "get",
            "job",
            self.name,
            "-n",
            self.config["namespace"],
            "--ignore-not-found=true",
            "-o",
            "json",
        )
        return json.loads(raw) if raw.strip() else None

    def _owned(self, job: dict[str, Any]) -> None:
        metadata = job["metadata"]
        if metadata.get("labels", {}).get("endless-owner") != self.token:
            raise RuntimeError(
                "Job ownership token mismatch; refusing deletion"
            )
        if self.uid and metadata["uid"] != self.uid:
            raise RuntimeError("Job UID changed; refusing deletion")
        self.uid = metadata["uid"]

    def _manifest(self) -> dict[str, Any]:
        labels = {
            "endless-owner": self.token,
            "endless-run": re.sub(
                r"[^a-zA-Z0-9_.-]", "-", self.identity["run_id"]
            )[:63].strip("-_.")
            or "run",
        }
        manifest: dict[str, Any] = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "name": self.name,
                "namespace": self.config["namespace"],
                "labels": labels,
            },
            "spec": {
                "backoffLimit": 0,
                "activeDeadlineSeconds": self.config.get(
                    "serving_deadline", 2700
                ),
                "template": {
                    "metadata": {"labels": labels},
                    "spec": {
                        "restartPolicy": "Never",
                        "automountServiceAccountToken": False,
                        "nodeSelector": self.config.get(
                            "node_selector", {"pool": "gpu"}
                        ),
                        "tolerations": self.config.get(
                            "tolerations",
                            [
                                {
                                    "key": "pool",
                                    "operator": "Equal",
                                    "value": "gpu",
                                    "effect": "NoSchedule",
                                }
                            ],
                        ),
                        "volumes": [
                            {
                                "name": "shm",
                                "emptyDir": {
                                    "medium": "Memory",
                                    "sizeLimit": "2Gi",
                                },
                            }
                        ],
                        "containers": [
                            {
                                "name": "vllm",
                                "image": self.image,
                                "volumeMounts": [
                                    {"name": "shm", "mountPath": "/dev/shm"}
                                ],
                                "args": [
                                    "--model",
                                    self.model["name"],
                                    "--revision",
                                    self.model["revision"],
                                    "--host",
                                    "127.0.0.1",
                                    "--port",
                                    "8000",
                                    "--dtype",
                                    "bfloat16",
                                    "--max-model-len",
                                    "16384",
                                    "--max-num-seqs",
                                    "1",
                                    "--gpu-memory-utilization",
                                    "0.8",
                                    "--enforce-eager",
                                    "--disable-log-requests",
                                    "--generation-config",
                                    "vllm",
                                ],
                                "resources": {
                                    "requests": {
                                        "nvidia.com/gpu": "1",
                                        "cpu": "2",
                                        "memory": "8Gi",
                                    },
                                    "limits": {
                                        "nvidia.com/gpu": "1",
                                        "cpu": "6",
                                        "memory": "24Gi",
                                    },
                                },
                                "readinessProbe": {
                                    "exec": {
                                        "command": [
                                            "python3",
                                            "-c",
                                            "import urllib.request; "
                                            "urllib.request.urlopen("
                                            "'http://127.0.0.1:8000/health', "
                                            "timeout=2)",
                                        ]
                                    },
                                    "periodSeconds": 5,
                                    "timeoutSeconds": 3,
                                },
                            }
                        ],
                    },
                },
            },
        }

        if self.server_kind == "skyrl":
            container = manifest["spec"]["template"]["spec"]["containers"][0]
            container["name"] = "skyrl"
            del container["args"]
            container["env"] = [
                {"name": "SKYRL_MODEL_NAME", "value": self.model["name"]},
                {"name": "SKYRL_DUMP_INFRA_LOG_TO_STDOUT", "value": "1"},
                {
                    "name": "RAY_DEFAULT_OBJECT_STORE_MAX_MEMORY_BYTES",
                    "value": "1073741824",
                },
                {
                    "name": "SKYRL_MODEL_REVISION",
                    "value": self.model["revision"],
                },
            ]
            container["readinessProbe"]["exec"]["command"] = [
                "python",
                "-c",
                "import urllib.request; "
                "urllib.request.urlopen("
                "'http://127.0.0.1:8000/api/v1/healthz', timeout=2)",
            ]
        return manifest

    def __enter__(self) -> KubernetesInference:
        """Start serving and return the session, cleaning up failed starts.

        Returns:
            This session with a verified local inference URL.

        Raises:
            RuntimeError: Ownership, startup, or cleanup verification fails.
            BaseException: Startup interruption, reraised after cleanup.
        """
        self.directory.mkdir(parents=True, exist_ok=True)
        initial = self._group()
        if (
            initial["MinSize"] != 0
            or initial["DesiredCapacity"] != 0
            or initial["Instances"]
        ):
            raise RuntimeError(
                "GPU group must start empty with minimum and desired zero"
            )
        if self._job():
            raise RuntimeError("Job already exists; refusing to reuse it")
        path = self.directory / "job.json"
        path.write_text(json.dumps(self._manifest(), indent=2))
        try:
            self._serving_deadline = time.monotonic() + self.config.get(
                "serving_deadline", 2700
            )
            self.attempted = True
            created = json.loads(
                self._kube("create", "-f", str(path), "-o", "json")
            )
            self._owned(created)
            self._wait_ready()
            self._forward()
            return self
        except BaseException as exc:
            try:
                self._cleanup()
            except Exception as cleanup_error:
                raise RuntimeError(
                    f"Startup failed: {exc}; cleanup failed: {cleanup_error}"
                ) from exc
            raise

    def _pods(self) -> list[dict[str, Any]]:
        return cast(
            list[dict[str, Any]],
            json.loads(
                self._kube(
                    "get",
                    "pods",
                    "-n",
                    self.config["namespace"],
                    "-l",
                    "endless-owner=" + self.token,
                    "-o",
                    "json",
                )
            )["items"],
        )

    def _wait_ready(self) -> None:
        deadline = time.monotonic() + self.config.get("startup_timeout", 900)
        while time.monotonic() < deadline:
            for pod in self._pods():
                node = pod["spec"].get("nodeName")
                if node:
                    info = json.loads(
                        self._kube("get", "node", node, "-o", "json")
                    )
                    self.instance_id = info["spec"]["providerID"].rsplit(
                        "/", 1
                    )[-1]
                if pod["status"].get("phase") in {"Failed", "Succeeded"}:
                    raise RuntimeError("Serving pod ended before readiness")
                if any(
                    c["type"] == "Ready" and c["status"] == "True"
                    for c in pod["status"].get("conditions", [])
                ):
                    self.identity.update(
                        {"job_uid": self.uid, "instance_id": self.instance_id}
                    )
                    return
            time.sleep(5)
        raise RuntimeError("Serving startup deadline exceeded")

    @staticmethod
    def _port() -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _forward(self) -> None:
        port = self._port()
        self.forward_log = (self.directory / "port-forward.log").open("w")
        self.forward = subprocess.Popen(
            [
                str(self.kubectl),
                "--context",
                self.config["kube_context"],
                "port-forward",
                "-n",
                self.config["namespace"],
                "job/" + self.name,
                f"{port}:8000",
                "--address=127.0.0.1",
            ],
            env=self.env,
            stdout=self.forward_log,
            stderr=subprocess.STDOUT,
            text=True,
        )
        origin = f"http://127.0.0.1:{port}"
        self.base_url = (
            origin if self.server_kind == "skyrl" else origin + "/v1"
        )
        for _ in range(20):
            if self.forward.poll() is not None:
                raise RuntimeError("Port forwarding exited")
            try:
                self._verify_server()
                return
            except OSError:
                time.sleep(1)
        raise RuntimeError("Port forwarding never became ready")

    def _verify_server(self) -> None:
        if self.server_kind == "skyrl":
            with urllib.request.urlopen(
                self.base_url + "/api/v1/healthz", timeout=2
            ):
                pass
            identity = json.loads(
                self._kube(
                    "exec",
                    "-n",
                    self.config["namespace"],
                    "job/" + self.name,
                    "--",
                    "cat",
                    "/checkpoints/server-identity.json",
                )
            )
            if (
                identity.get("model_name") != self.model["name"]
                or identity.get("model_revision") != self.model["revision"]
            ):
                raise RuntimeError("Training server model identity mismatch")
            self.identity["training_server"] = identity
            (self.directory / "server-identity.json").write_text(
                json.dumps(identity, indent=2)
            )
        else:
            with urllib.request.urlopen(
                self.base_url + "/models", timeout=2
            ) as response:
                models = json.load(response)
            if not any(m["id"] == self.model["name"] for m in models["data"]):
                raise RuntimeError("Served model identity mismatch")

    def _delete_job(self) -> None:
        job = self._job()
        if job is None:
            return
        self._owned(job)
        # UID preconditions protect replacements created after this read.
        options = self.directory / "delete-options.json"
        options.write_text(
            json.dumps(
                {
                    "apiVersion": "v1",
                    "kind": "DeleteOptions",
                    "propagationPolicy": "Foreground",
                    "preconditions": {"uid": self.uid},
                }
            )
        )
        url = (
            f"/apis/batch/v1/namespaces/{self.config['namespace']}"
            f"/jobs/{self.name}"
        )
        self._kube("delete", "--raw", url, "-f", str(options))
        deadline = time.monotonic() + 60
        while time.monotonic() < deadline:
            if self._job() is None and not self._pods():
                self.cleanup_report["job_deleted"] = True
                return
            time.sleep(2)
        raise RuntimeError("Serving job or pods remain after deletion")

    @staticmethod
    def _stop(process: subprocess.Popen[str]) -> None:
        process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)

    def _empty_node(self, instance_id: str) -> None:
        nodes = json.loads(self._kube("get", "nodes", "-o", "json"))["items"]
        node = next(
            (
                n
                for n in nodes
                if n["spec"].get("providerID", "").endswith("/" + instance_id)
            ),
            None,
        )
        if node is None:
            return
        name = node["metadata"]["name"]
        for cordoned in (False, True):
            pods = json.loads(
                self._kube(
                    "get",
                    "pods",
                    "-A",
                    "--field-selector",
                    "spec.nodeName=" + name,
                    "-o",
                    "json",
                )
            )["items"]
            if any(
                not any(
                    r.get("kind") == "DaemonSet"
                    for r in p["metadata"].get("ownerReferences", [])
                )
                for p in pods
            ):
                raise RuntimeError(
                    "GPU worker has other workloads; refusing termination"
                )
            if not cordoned:
                self._kube("cordon", name)

    def _gpu_cleanup(self) -> None:
        state = self._group()
        instances = state["Instances"]
        if len(instances) > 1:
            raise RuntimeError(
                "Multiple GPU instances; association is ambiguous"
            )
        if instances:
            candidate = instances[0]["InstanceId"]
            if self.instance_id and candidate != self.instance_id:
                raise RuntimeError("GPU instance differs from serving worker")
            self.instance_id = candidate
            self._empty_node(candidate)
            if not instances[0]["LifecycleState"].startswith("Terminating"):
                flag = (
                    "--should-decrement-desired-capacity"
                    if state["DesiredCapacity"] > 0
                    else "--no-should-decrement-desired-capacity"
                )
                self._aws(
                    "autoscaling",
                    "terminate-instance-in-auto-scaling-group",
                    "--instance-id",
                    candidate,
                    flag,
                )
        deadline = time.monotonic() + self.config.get("cleanup_timeout", 240)
        forced = False
        while True:
            state = self._group()
            ec2_states: dict[str, str] = {}
            if self.instance_id:
                reservations = self._aws(
                    "ec2",
                    "describe-instances",
                    "--instance-ids",
                    self.instance_id,
                )["Reservations"]
                ec2_states = {
                    i["InstanceId"]: i["State"]["Name"]
                    for r in reservations
                    for i in r["Instances"]
                }
            self.cleanup_report.update(
                {
                    "gpu_desired": state["DesiredCapacity"],
                    "gpu_instances": state["Instances"],
                    "ec2_states": ec2_states,
                }
            )
            if (
                state["DesiredCapacity"] == 0
                and not state["Instances"]
                and (
                    not self.instance_id
                    or ec2_states.get(self.instance_id) == "terminated"
                )
            ):
                return
            if time.monotonic() >= deadline:
                if (
                    self.config.get("force_termination", False)
                    and not forced
                    and self.instance_id
                ):
                    self._empty_node(self.instance_id)
                    self.cleanup_report["force_termination_used"] = True
                    self._aws(
                        "ec2",
                        "terminate-instances",
                        "--instance-ids",
                        self.instance_id,
                        "--force",
                        "--skip-os-shutdown",
                    )
                    forced = True
                    deadline = time.monotonic() + self.config.get(
                        "cleanup_timeout", 240
                    )
                else:
                    raise RuntimeError(
                        "GPU teardown did not reach verified zero capacity"
                    )
            time.sleep(5)

    def _capture_training_logs(self) -> None:
        """Retain bounded Ray and SkyRL log tails before removing the owned job.

        Raises:
            RuntimeError: Ownership or remote diagnostic collection fails.
        """  # noqa: DOC502
        job = self._job()
        if job is None:
            return
        self._owned(job)
        script = r"""
import json, os
from pathlib import Path
roots = [Path('/tmp/skyrl-logs'), Path('/tmp/ray/session_latest/logs')]
critical = {'raylet.out', 'raylet.err', 'gcs_server.out', 'gcs_server.err'}
candidates = []
for name in ('memory.events', 'memory.current', 'memory.peak', 'memory.max'):
    path = Path('/sys/fs/cgroup') / name
    if path.is_file():
        candidates.append((-2, 0, path))
for root in roots:
    if not root.exists():
        continue
    root = root.resolve()
    for directory, _, names in os.walk(root, followlinks=False):
        for name in names:
            path = Path(directory) / name
            if path.suffix not in {'.err', '.out', '.log'} or path.is_symlink():
                continue
            try:
                if not path.resolve().is_relative_to(root) or not path.is_file():
                    continue
                priority = -1 if name in critical else 0 if 'engine' in name.lower() else 1 if 'worker' in name.lower() else 2
                candidates.append((priority, -path.stat().st_mtime, path))
            except OSError:
                continue
remaining = 1024 * 1024
logs = {}
for priority, _, path in sorted(candidates)[:20]:
    if remaining <= 0:
        break
    try:
        limit = min(4096 if priority == -2 else 65536, remaining)
        with path.open('rb') as source:
            source.seek(max(0, path.stat().st_size - limit))
            data = source.read(limit)
        remaining -= len(data)
        logs[str(path)] = data.decode('utf-8', errors='replace')
    except OSError as exc:
        logs[str(path)] = 'Unable to read log: ' + type(exc).__name__
print(json.dumps({'log_tails': logs, 'max_files': 20, 'max_bytes': 1048576}))
"""
        output = self._call(
            [
                str(self.kubectl),
                "--context",
                self.config["kube_context"],
                "exec",
                "-n",
                self.config["namespace"],
                "job/" + self.name,
                "--",
                "python3",
                "-c",
                script,
            ],
            timeout=20,
        )
        (self.directory / "training-worker-logs.json").write_text(output)

    def _cleanup(self) -> None:
        errors = self.cleanup_report["errors"]
        try:
            if self.forward:
                self._stop(self.forward)
        except Exception as exc:
            errors.append(f"Port forwarding: {exc}")
        finally:
            if self.forward_log:
                try:
                    self.forward_log.close()
                except Exception as exc:
                    errors.append(f"Closing port-forward log: {exc}")
        if self.attempted:
            try:
                log = self._kube(
                    "logs",
                    "-n",
                    self.config["namespace"],
                    "job/" + self.name,
                    "--tail=500",
                )
                (self.directory / "server.log").write_text(log)
            except Exception as exc:
                self.cleanup_report["diagnostic_error"] = str(exc)
            if self.server_kind == "skyrl":
                try:
                    self._capture_training_logs()
                except Exception as exc:
                    self.cleanup_report["training_diagnostic_error"] = str(exc)
            try:
                self._delete_job()
                self._gpu_cleanup()
            except Exception as exc:
                errors.append(str(exc))
        self.cleanup_report["complete"] = not errors
        try:
            (self.directory / "cleanup.json").write_text(
                json.dumps(self.cleanup_report, indent=2)
            )
        except OSError as exc:
            errors.append(f"Writing cleanup evidence: {exc}")
            self.cleanup_report["complete"] = False
        if errors:
            raise RuntimeError("; ".join(errors))

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        """Stop serving and verify teardown, raising if cleanup is incomplete.

        Args:
            exc_type: Exception type from the context body, if any.
            exc: Exception from the context body, if any.
            traceback: Context body's traceback, if any.

        Raises:
            RuntimeError: Cleanup could not be verified.
        """  # noqa: DOC502
        self._cleanup()
