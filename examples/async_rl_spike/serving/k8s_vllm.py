"""Kubernetes lifecycle helpers for per-version warm vLLM servers.

Remote serving gives every published version its own raw Kubernetes vLLM
Deployment and Service (no ZenML model deployer, on purpose). The trainer
creates one when it publishes a version and deletes it when the version
ages out of the staleness window. Generators reach the server over HTTP.
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
    """Load in-cluster config, or fall back to local kubeconfig."""
    from kubernetes import config

    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()


def _gpu_tolerations() -> List[Dict[str, str]]:
    """Return the taint toleration for the GPU node pool."""
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
        # Qwen3-4B's 262k declared context needs a 36GiB KV cache, which no
        # single L4 has. Our prompts plus completions fit in 8k.
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
    """Build the Kubernetes Deployment object for the vLLM server."""
    from kubernetes import client

    labels = {"app": service_name, "component": "async-rl-spike-vllm"}
    return client.V1Deployment(
        metadata=client.V1ObjectMeta(name=deployment_name, labels=labels),
        spec=client.V1DeploymentSpec(
            replicas=1,
            selector=client.V1LabelSelector(
                match_labels={"app": service_name}
            ),
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
    """Build the ClusterIP Service object for the vLLM server."""
    from kubernetes import client

    return client.V1Service(
        metadata=client.V1ObjectMeta(
            name=service_name,
            labels={"app": service_name, "component": "async-rl-spike-vllm"},
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
    """Wait until the Deployment controller reports the pod available.

    Args:
        namespace: Kubernetes namespace.
        deployment_name: Deployment to watch.
        timeout_seconds: Readiness timeout.

    Raises:
        TimeoutError: If the rollout does not finish in time.
    """
    from kubernetes import client

    apps = client.AppsV1Api()
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        deployment = apps.read_namespaced_deployment(
            deployment_name, namespace
        )
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
    """Wait for the vLLM pod to report Ready and return its name.

    Args:
        namespace: Kubernetes namespace.
        service_name: Service whose selector matches the pod.
        timeout_seconds: Readiness timeout.

    Raises:
        TimeoutError: If no pod becomes ready in time.

    Returns:
        The ready pod's name.
    """
    from kubernetes import client

    core = client.CoreV1Api()
    deadline = time.time() + timeout_seconds
    selector = f"app={service_name}"
    while time.time() < deadline:
        pods = core.list_namespaced_pod(
            namespace, label_selector=selector
        ).items
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
    """Wait until the vLLM server answers its health endpoint.

    Args:
        endpoint_url: Base URL of the vLLM server.
        timeout_seconds: Readiness timeout.

    Raises:
        TimeoutError: If the server does not answer in time.
    """
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
    """Create or update one version's vLLM server and return its endpoint.

    Args:
        model_name: Base policy model served by vLLM.
        image: Container image for the vLLM server.
        namespace: Kubernetes namespace.
        deployment_name: Deployment name for this version.
        service_name: ClusterIP Service name for this version.
        max_lora_rank: Maximum LoRA rank accepted by vLLM.
        service_account_name: Kubernetes service account for the pod.
        timeout_seconds: Readiness timeout.

    Returns:
        Endpoint record for the version's server.
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


def _stream_dir_into_pod(
    *,
    namespace: str,
    pod_name: str,
    local_dir: str,
    target_dir: str,
) -> None:
    """Stream a local directory into a pod over the exec websocket.

    The raw vLLM pod has no ZenML session and its node role has no artifact
    store access, so it cannot pull the adapter. The step already has the
    adapter materialized locally, so the bytes go over the exec channel as
    a base64-encoded tar.gz decoded by `sh` in the pod.

    Args:
        namespace: Kubernetes namespace of the pod.
        pod_name: Target pod.
        local_dir: Local directory to copy.
        target_dir: Absolute directory inside the pod to extract into.
    """
    import io
    import tarfile

    from kubernetes import client
    from kubernetes.stream import stream

    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        tar.add(local_dir, arcname=".")
    payload = base64.b64encode(buffer.getvalue()).decode()

    command = [
        "sh",
        "-c",
        f"mkdir -p {target_dir} && base64 -d | tar xzf - -C {target_dir}",
    ]
    ws = stream(
        client.CoreV1Api().connect_get_namespaced_pod_exec,
        pod_name,
        namespace,
        command=command,
        stderr=True,
        stdin=True,
        stdout=True,
        tty=False,
        _preload_content=False,
    )
    chunk_size = 1 << 16
    for i in range(0, len(payload), chunk_size):
        ws.write_stdin(payload[i : i + chunk_size])
    # Closing the websocket is the only way to signal EOF to the in-pod
    # pipeline. Success is verified with a follow-up exec.
    ws.close()


def _exec_in_pod(*, namespace: str, pod_name: str, command: List[str]) -> str:
    """Run a command in a pod and return its combined output."""
    from kubernetes import client
    from kubernetes.stream import stream

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
    if not body:
        return {}
    try:
        result = json.loads(body)
    except json.JSONDecodeError:
        # vLLM's runtime LoRA endpoints answer 200 with a plain-text body
        # ("Success: ..."), not JSON.
        return {"raw": body}
    return result if isinstance(result, dict) else {"raw": body}


def delete_vllm_deployment(*, endpoint: Dict[str, Any]) -> None:
    """Delete a version's Kubernetes vLLM Deployment and Service.

    Args:
        endpoint: Endpoint record from `ensure_vllm_deployment`.
    """
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
    adapter_dir: str,
    adapter_name: str,
    adapter_root: str = DEFAULT_ADAPTER_ROOT,
) -> Dict[str, Any]:
    """Push a local LoRA adapter into a version's vLLM pod and hot-load it.

    Args:
        endpoint: Endpoint record from `ensure_vllm_deployment`.
        adapter_dir: Local directory with the materialized adapter files.
        adapter_name: LoRA name used in rollout requests.
        adapter_root: Directory inside the pod that stores adapters.

    Raises:
        RuntimeError: If the adapter files do not appear in the pod.

    Returns:
        Record with the loaded adapter name and in-pod path.
    """
    _load_kubernetes_config()
    namespace = endpoint["namespace"]
    pod_name = _wait_for_ready_pod(
        namespace=namespace,
        service_name=endpoint["service_name"],
        timeout_seconds=120,
    )
    adapter_path = f"{adapter_root.rstrip('/')}/{adapter_name}"
    _stream_dir_into_pod(
        namespace=namespace,
        pod_name=pod_name,
        local_dir=adapter_dir,
        target_dir=adapter_path,
    )
    check = _exec_in_pod(
        namespace=namespace,
        pod_name=pod_name,
        command=[
            "sh",
            "-c",
            f"test -s {adapter_path}/adapter_config.json && echo TRANSFER_OK",
        ],
    )
    if "TRANSFER_OK" not in check:
        raise RuntimeError(
            "Adapter transfer into the vLLM pod failed: "
            f"{adapter_path}/adapter_config.json missing or empty. "
            f"Check output: {check!r}"
        )
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
        "endpoint_url": endpoint["url"],
    }
