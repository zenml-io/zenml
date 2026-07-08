"""Kubernetes lifecycle helpers for a warm vLLM rollout server.

This module deliberately uses raw Kubernetes resources instead of ZenML's
model deployer. That is the point of this spike stage: ZenML records the
control steps and adapter artifacts, while Kubernetes owns the serving pod
that stays warm between RL iterations.
"""

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, List

DEFAULT_VLLM_PORT = 8000
DEFAULT_ADAPTER_ROOT = "/adapters"


def _load_kubernetes_config() -> None:
    """Load Kubernetes config from inside a pod, or from local kubeconfig."""
    from kubernetes import config

    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def _gpu_tolerations() -> List[Dict[str, str]]:
    """Return the taint toleration used by the RL spike GPU node pool."""
    return [
        {
            "key": "pool",
            "operator": "Equal",
            "value": "gpu",
            "effect": "NoSchedule",
        }
    ]


def _vllm_command(model_name: str, max_lora_rank: int) -> List[str]:
    """Build the vLLM OpenAI server command."""
    return [
        "vllm",
        "serve",
        model_name,
        "--host",
        "0.0.0.0",
        "--port",
        str(DEFAULT_VLLM_PORT),
        "--enable-lora",
        "--max-lora-rank",
        str(max_lora_rank),
        # Same constraint as VLLMGenerator: Qwen3-4B's 262k declared
        # context needs a 36GiB KV cache, which no single L4 has.
        "--max-model-len",
        "8192",
    ]


def _deployment_manifest(
    *,
    deployment_name: str,
    service_name: str,
    model_name: str,
    image: str,
    max_lora_rank: int,
    service_account_name: str,
) -> Any:
    """Create the Kubernetes Deployment object for the vLLM server."""
    from kubernetes import client

    labels = {"app": service_name, "component": "rl-spike-vllm"}
    return client.V1Deployment(
        metadata=client.V1ObjectMeta(name=deployment_name, labels=labels),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(match_labels={"app": service_name}),
            template=client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels=labels),
                spec=client.V1PodSpec(
                    service_account_name=service_account_name,
                    node_selector={"pool": "gpu"},
                    tolerations=_gpu_tolerations(),
                    containers=[
                        client.V1Container(
                            name="vllm",
                            image=image,
                            command=_vllm_command(model_name, max_lora_rank),
                            env=[
                                client.V1EnvVar(
                                    name="VLLM_ALLOW_RUNTIME_LORA_UPDATING",
                                    value="true",
                                ),
                            ],
                            ports=[
                                client.V1ContainerPort(
                                    container_port=DEFAULT_VLLM_PORT
                                )
                            ],
                            resources=client.V1ResourceRequirements(
                                requests={
                                    "cpu": "4",
                                    "memory": "16Gi",
                                    "nvidia.com/gpu": "1",
                                },
                                limits={
                                    "memory": "28Gi",
                                    "nvidia.com/gpu": "1",
                                },
                            ),
                        )
                    ],
                ),
            ),
        ),
    )


def _service_manifest(*, service_name: str) -> Any:
    """Create the ClusterIP Service object for the vLLM server."""
    from kubernetes import client

    return client.V1Service(
        metadata=client.V1ObjectMeta(
            name=service_name,
            labels={"app": service_name, "component": "rl-spike-vllm"},
        ),
        spec=client.V1ServiceSpec(
            type="ClusterIP",
            selector={"app": service_name},
            ports=[
                client.V1ServicePort(
                    name="http",
                    port=DEFAULT_VLLM_PORT,
                    target_port=DEFAULT_VLLM_PORT,
                )
            ],
        ),
    )


def _upsert_deployment(namespace: str, manifest: Any) -> None:
    """Create or replace the vLLM Deployment."""
    from kubernetes import client
    from kubernetes.client import ApiException

    apps = client.AppsV1Api()
    try:
        apps.read_namespaced_deployment(manifest.metadata.name, namespace)
    except ApiException as e:
        if e.status != 404:
            raise
        apps.create_namespaced_deployment(namespace=namespace, body=manifest)
    else:
        apps.patch_namespaced_deployment(
            name=manifest.metadata.name, namespace=namespace, body=manifest
        )


def _upsert_service(namespace: str, manifest: Any) -> None:
    """Create or patch the vLLM Service."""
    from kubernetes import client
    from kubernetes.client import ApiException

    core = client.CoreV1Api()
    try:
        core.read_namespaced_service(manifest.metadata.name, namespace)
    except ApiException as e:
        if e.status != 404:
            raise
        core.create_namespaced_service(namespace=namespace, body=manifest)
    else:
        core.patch_namespaced_service(
            name=manifest.metadata.name, namespace=namespace, body=manifest
        )


def _wait_for_deployment_rollout(
    *, namespace: str, deployment_name: str, timeout_seconds: int
) -> None:
    """Wait until the Deployment controller reports the new pod available."""
    from kubernetes import client

    apps = client.AppsV1Api()
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        deployment = apps.read_namespaced_deployment(deployment_name, namespace)
        spec_replicas = deployment.spec.replicas or 1
        status = deployment.status
        if (
            status.observed_generation == deployment.metadata.generation
            and (status.updated_replicas or 0) >= spec_replicas
            and (status.ready_replicas or 0) >= spec_replicas
            and (status.available_replicas or 0) >= spec_replicas
        ):
            return
        time.sleep(5)
    raise TimeoutError(
        f"Deployment {deployment_name!r} did not finish rolling out "
        f"within {timeout_seconds}s."
    )


def _wait_for_ready_pod(
    *, namespace: str, service_name: str, timeout_seconds: int
) -> str:
    """Wait for the vLLM pod to report Ready and return its pod name."""
    from kubernetes import client

    core = client.CoreV1Api()
    deadline = time.time() + timeout_seconds
    selector = f"app={service_name}"
    while time.time() < deadline:
        pods = core.list_namespaced_pod(namespace, label_selector=selector).items
        for pod in pods:
            conditions = pod.status.conditions or []
            ready = any(
                condition.type == "Ready" and condition.status == "True"
                for condition in conditions
            )
            if ready and pod.metadata.name:
                return pod.metadata.name
        time.sleep(5)
    raise TimeoutError(
        f"vLLM pod for service {service_name!r} did not become ready "
        f"within {timeout_seconds}s."
    )


def _wait_for_http_health(endpoint_url: str, timeout_seconds: int) -> None:
    """Wait until the vLLM OpenAI server accepts HTTP requests."""
    deadline = time.time() + timeout_seconds
    health_url = f"{endpoint_url.rstrip('/')}/health"
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=5) as response:
                if 200 <= response.status < 300:
                    return
        except (urllib.error.URLError, TimeoutError):
            pass
        time.sleep(5)
    raise TimeoutError(
        f"vLLM endpoint {endpoint_url!r} did not answer {health_url!r} "
        f"within {timeout_seconds}s."
    )


def ensure_vllm_deployment(
    *,
    model_name: str,
    image: str,
    namespace: str,
    deployment_name: str,
    service_name: str,
    max_lora_rank: int = 32,
    service_account_name: str = "zenml-service-account",
    timeout_seconds: int = 900,
) -> Dict[str, Any]:
    """Create or update the warm vLLM server and return its endpoint record.

    Args:
        model_name: Base policy model served by vLLM.
        image: Container image used for the vLLM server.
        namespace: Kubernetes namespace for the Deployment and Service.
        deployment_name: Name of the Kubernetes Deployment.
        service_name: Name of the ClusterIP Service.
        max_lora_rank: Maximum LoRA rank accepted by vLLM.
        service_account_name: Kubernetes service account for the raw vLLM pod.
        timeout_seconds: Readiness timeout.

    Returns:
        A JSON-serializable endpoint record for downstream ZenML steps.
    """
    _load_kubernetes_config()
    _upsert_deployment(
        namespace,
        _deployment_manifest(
            deployment_name=deployment_name,
            service_name=service_name,
            model_name=model_name,
            image=image,
            max_lora_rank=max_lora_rank,
            service_account_name=service_account_name,
        ),
    )
    _upsert_service(namespace, _service_manifest(service_name=service_name))
    _wait_for_deployment_rollout(
        namespace=namespace,
        deployment_name=deployment_name,
        timeout_seconds=timeout_seconds,
    )
    pod_name = _wait_for_ready_pod(
        namespace=namespace,
        service_name=service_name,
        timeout_seconds=timeout_seconds,
    )
    endpoint_url = (
        f"http://{service_name}.{namespace}.svc.cluster.local:"
        f"{DEFAULT_VLLM_PORT}"
    )
    _wait_for_http_health(endpoint_url, timeout_seconds=timeout_seconds)
    return {
        "url": endpoint_url,
        "namespace": namespace,
        "deployment_name": deployment_name,
        "service_name": service_name,
        "pod_name": pod_name,
        "model_name": model_name,
        "image": image,
        "service_account_name": service_account_name,
    }


def _exec_python_in_pod(
    *, namespace: str, pod_name: str, script: str, args: List[str]
) -> str:
    """Run a Python helper inside the vLLM pod and return combined output."""
    from kubernetes import client
    from kubernetes.stream import stream

    encoded = base64.b64encode(script.encode()).decode()
    command = [
        "python",
        "-c",
        (
            "import base64, sys; "
            "code = base64.b64decode(sys.argv[1]).decode(); "
            "sys.argv = sys.argv[1:]; "
            "exec(compile(code, '<adapter-loader>', 'exec'))"
        ),
        encoded,
        *args,
    ]
    return stream(
        client.CoreV1Api().connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=command,
        stderr=True,
        stdin=False,
        stdout=True,
        tty=False,
    )


def _adapter_loader_script() -> str:
    """Return the helper script that materializes one ZenML adapter artifact."""
    return r'''
import json
import os
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

from zenml.io import fileio


def _safe_members(tar, directory):
    directory = str(Path(directory).resolve())
    safe = []
    for member in tar.getmembers():
        if member.issym() or member.islnk():
            raise RuntimeError(f"Adapter archive may not contain links: {member.name}")
        target = str(Path(directory, member.name).resolve())
        if os.path.commonpath([directory, target]) != directory:
            raise RuntimeError(f"Unsafe tar member path: {member.name}")
        safe.append(member)
    return safe

archive_uri = sys.argv[1].rstrip("/") + "/data.tar.gz"
adapter_name = sys.argv[2]
adapter_root = Path(sys.argv[3])
target = adapter_root / adapter_name
staging = adapter_root / f".{adapter_name}.tmp"

adapter_root.mkdir(parents=True, exist_ok=True)
if staging.exists():
    shutil.rmtree(staging)
staging.mkdir(parents=True)

with tempfile.NamedTemporaryFile(suffix=".tar.gz", delete=False) as tmp:
    local_archive = tmp.name

fileio.copy(archive_uri, local_archive)
with tarfile.open(local_archive, "r:gz") as tar:
    tar.extractall(staging, members=_safe_members(tar, staging))
os.remove(local_archive)

if target.exists():
    shutil.rmtree(target)
staging.rename(target)
print(json.dumps({"ok": True, "adapter_path": str(target)}))
'''


def _post_json(url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """POST JSON and return the parsed response, if any."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read().decode()
    return json.loads(body) if body else {}


def delete_vllm_deployment(*, endpoint: Dict[str, Any]) -> None:
    """Delete the raw Kubernetes vLLM Deployment and Service."""
    from kubernetes import client
    from kubernetes.client import ApiException

    _load_kubernetes_config()
    namespace = endpoint["namespace"]
    apps = client.AppsV1Api()
    core = client.CoreV1Api()
    try:
        apps.delete_namespaced_deployment(
            name=endpoint["deployment_name"], namespace=namespace
        )
    except ApiException as e:
        if e.status != 404:
            raise
    try:
        core.delete_namespaced_service(
            name=endpoint["service_name"], namespace=namespace
        )
    except ApiException as e:
        if e.status != 404:
            raise


def load_lora_adapter(
    *,
    endpoint: Dict[str, Any],
    adapter_uri: str,
    adapter_name: str,
    adapter_root: str = DEFAULT_ADAPTER_ROOT,
) -> Dict[str, Any]:
    """Materialize a ZenML Path artifact in the vLLM pod and hot-load it.

    The PathMaterializer stores directory artifacts as `data.tar.gz` under
    the artifact URI. This helper copies that archive into the running vLLM
    pod, extracts it to `/adapters/<adapter_name>`, and calls vLLM's runtime
    LoRA endpoint with `load_inplace=true`.

    Args:
        endpoint: Endpoint record returned by `ensure_vllm_deployment`.
        adapter_uri: ZenML artifact URI for the LoRA adapter Path artifact.
        adapter_name: Versioned adapter name used in rollout requests.
        adapter_root: Directory inside the vLLM pod that stores adapters.

    Returns:
        A JSON-serializable record with the loaded adapter name and path.
    """
    _load_kubernetes_config()
    namespace = endpoint["namespace"]
    pod_name = _wait_for_ready_pod(
        namespace=namespace,
        service_name=endpoint["service_name"],
        timeout_seconds=120,
    )
    output = _exec_python_in_pod(
        namespace=namespace,
        pod_name=pod_name,
        script=_adapter_loader_script(),
        args=[adapter_uri, adapter_name, adapter_root],
    )
    result = None
    for line in reversed(output.strip().splitlines()):
        try:
            candidate = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(candidate, dict) and "ok" in candidate:
            result = candidate
            break
    if not result or not result.get("ok"):
        raise RuntimeError(
            "Adapter materialization inside the vLLM pod failed or did not "
            f"emit a success record. Output:\n{output}"
        )
    adapter_path = str(result["adapter_path"])
    _post_json(
        f"{endpoint['url'].rstrip('/')}/v1/load_lora_adapter",
        {
            "lora_name": adapter_name,
            "lora_path": adapter_path,
            "load_inplace": True,
        },
    )
    return {
        "adapter_name": adapter_name,
        "adapter_path": adapter_path,
        "adapter_uri": adapter_uri,
        "endpoint_url": endpoint["url"],
    }
