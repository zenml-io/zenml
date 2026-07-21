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
"""Unit tests for the vLLM Kubernetes manifest builders."""

import json

from zenml.enums import KubernetesServiceType
from zenml.integrations.vllm.services.vllm_deployment import VLLMEngineArgs
from zenml.integrations.vllm.services.vllm_kubernetes_deployment import (
    build_vllm_deployment_manifest,
    build_vllm_service_manifest,
)

LABELS = {"managed-by": "zenml", "zenml-service-uuid": "abc"}


def _build_deployment(**overrides):
    """Build a Deployment manifest with sensible defaults.

    Args:
        overrides: Keyword arguments overriding the defaults.

    Returns:
        The Deployment manifest.
    """
    kwargs = dict(
        name="vllm-test",
        namespace="zenml-vllm",
        image="vllm/vllm-openai:v0.25.1",
        replicas=1,
        port=8000,
        engine_args=VLLMEngineArgs(model="facebook/opt-125m"),
        extra_serve_args=[],
        labels=LABELS,
        resources={},
        shm_size=None,
        env={},
        hf_secret_name=None,
        pod_settings=None,
    )
    kwargs.update(overrides)
    return build_vllm_deployment_manifest(**kwargs)


def _container(manifest):
    """Extract the vLLM container spec from a Deployment manifest.

    Args:
        manifest: A Deployment manifest.

    Returns:
        The container spec.
    """
    return manifest["spec"]["template"]["spec"]["containers"][0]


def test_container_args_from_engine_fields():
    """Engine fields translate to their corresponding CLI args."""
    engine_args = VLLMEngineArgs(
        model="facebook/opt-125m",
        tokenizer="facebook/opt-125m-tok",
        served_model_name=["opt", "opt-alias"],
        trust_remote_code=True,
        tokenizer_mode="slow",
        dtype="float16",
        revision="main",
    )
    manifest = _build_deployment(
        engine_args=engine_args, extra_serve_args=["--foo", "bar"]
    )
    args = _container(manifest)["args"]

    assert args == [
        "--model",
        "facebook/opt-125m",
        "--port",
        "8000",
        "--host",
        "0.0.0.0",
        "--tokenizer",
        "facebook/opt-125m-tok",
        "--served-model-name",
        "opt",
        "opt-alias",
        "--trust-remote-code",
        "--tokenizer-mode",
        "slow",
        "--dtype",
        "float16",
        "--revision",
        "main",
        "--foo",
        "bar",
    ]


def test_container_args_minimal_engine_fields():
    """Only the required model field and engine defaults produce args."""
    manifest = _build_deployment(
        engine_args=VLLMEngineArgs(model="facebook/opt-125m"), port=9000
    )
    args = _container(manifest)["args"]

    assert args == [
        "--model",
        "facebook/opt-125m",
        "--port",
        "9000",
        "--host",
        "0.0.0.0",
        "--tokenizer-mode",
        "auto",
        "--dtype",
        "auto",
    ]


def test_served_model_name_as_single_string():
    """A single served_model_name is passed as one CLI value."""
    engine_args = VLLMEngineArgs(
        model="facebook/opt-125m", served_model_name="opt"
    )
    manifest = _build_deployment(engine_args=engine_args)
    args = _container(manifest)["args"]

    assert args[args.index("--served-model-name") + 1] == "opt"


def test_probes_use_health_path_and_configured_port():
    """Readiness and liveness probes hit /health on the configured port."""
    manifest = _build_deployment(port=8888)
    container = _container(manifest)

    for probe_key in ("readinessProbe", "livenessProbe"):
        probe = container[probe_key]
        assert probe["httpGet"]["path"] == "/health"
        assert probe["httpGet"]["port"] == 8888


def test_readiness_and_liveness_probes_differ_in_thresholds():
    """The liveness probe tolerates a much longer startup than readiness."""
    manifest = _build_deployment()
    container = _container(manifest)

    assert container["readinessProbe"]["initialDelaySeconds"] == 10
    assert container["readinessProbe"]["failureThreshold"] == 60
    assert container["livenessProbe"]["initialDelaySeconds"] == 600
    assert container["livenessProbe"]["failureThreshold"] == 3


def test_gpu_limit_mirrored_into_requests():
    """A configured GPU limit is mirrored into requests."""
    manifest = _build_deployment(
        resources={"limits": {"nvidia.com/gpu": "1", "cpu": "2"}}
    )
    resources = _container(manifest)["resources"]

    assert resources["limits"] == {"nvidia.com/gpu": "1", "cpu": "2"}
    assert resources["requests"] == {"nvidia.com/gpu": "1"}


def test_existing_gpu_request_is_not_overwritten():
    """An explicit GPU request is left untouched, not replaced by the limit."""
    manifest = _build_deployment(
        resources={
            "limits": {"nvidia.com/gpu": "2"},
            "requests": {"nvidia.com/gpu": "1"},
        }
    )
    resources = _container(manifest)["resources"]

    assert resources["requests"]["nvidia.com/gpu"] == "1"


def test_no_gpu_limit_leaves_resources_unmirrored():
    """Resources without a GPU limit are passed through unchanged."""
    manifest = _build_deployment(resources={"limits": {"cpu": "2"}})
    resources = _container(manifest)["resources"]

    assert "requests" not in resources


def test_shm_volume_added_with_memory_medium_and_size_limit():
    """A configured shm_size adds a Memory-backed /dev/shm emptyDir volume."""
    manifest = _build_deployment(shm_size="4Gi")
    pod_spec = manifest["spec"]["template"]["spec"]

    assert pod_spec["volumes"] == [
        {"name": "shm", "emptyDir": {"medium": "Memory", "sizeLimit": "4Gi"}}
    ]
    assert _container(manifest)["volumeMounts"] == [
        {"name": "shm", "mountPath": "/dev/shm"}
    ]


def test_no_shm_volume_when_shm_size_unset():
    """No volume is added when shm_size is unset."""
    manifest = _build_deployment(shm_size=None)
    pod_spec = manifest["spec"]["template"]["spec"]

    assert pod_spec["volumes"] == []
    assert _container(manifest)["volumeMounts"] == []


def test_hf_token_secret_key_ref_added_when_secret_name_set():
    """An HF_TOKEN env var referencing the secret is added when configured."""
    manifest = _build_deployment(hf_secret_name="vllm-hf-abc")
    env = _container(manifest)["env"]
    hf_token_env = next(item for item in env if item["name"] == "HF_TOKEN")

    assert hf_token_env["valueFrom"]["secretKeyRef"] == {
        "name": "vllm-hf-abc",
        "key": "token",
    }


def test_hf_token_env_absent_when_secret_name_unset():
    """No HF_TOKEN env var is added when no secret name is passed."""
    manifest = _build_deployment(hf_secret_name=None)
    env = _container(manifest)["env"]

    assert not any(item["name"] == "HF_TOKEN" for item in env)


def test_custom_env_vars_included_alongside_hf_token():
    """Custom env vars and the HF_TOKEN secret ref coexist."""
    manifest = _build_deployment(
        env={"FOO": "BAR"}, hf_secret_name="vllm-hf-abc"
    )
    env = _container(manifest)["env"]

    assert {"name": "FOO", "value": "BAR"} in env
    assert any(item["name"] == "HF_TOKEN" for item in env)


def test_deployment_manifest_is_json_serializable():
    """The Deployment manifest can be JSON-serialized as-is."""
    manifest = _build_deployment(
        resources={"limits": {"nvidia.com/gpu": "1"}},
        shm_size="2Gi",
        env={"FOO": "BAR"},
        hf_secret_name="vllm-hf-abc",
    )

    json.dumps(manifest)


def test_service_manifest_selector_matches_deployment_pod_labels():
    """The Service selector matches the Deployment's pod template labels."""
    deployment_manifest = _build_deployment()
    service_manifest = build_vllm_service_manifest(
        name="vllm-test",
        namespace="zenml-vllm",
        port=8000,
        service_type=KubernetesServiceType.CLUSTER_IP,
        selector_labels=LABELS,
        labels=LABELS,
    )

    pod_labels = deployment_manifest["spec"]["template"]["metadata"]["labels"]
    assert service_manifest["spec"]["selector"] == pod_labels


def test_service_manifest_exposes_configured_port_and_type():
    """The Service exposes the configured port and Service type."""
    service_manifest = build_vllm_service_manifest(
        name="vllm-test",
        namespace="zenml-vllm",
        port=8000,
        service_type=KubernetesServiceType.LOAD_BALANCER,
        selector_labels=LABELS,
        labels=LABELS,
    )

    assert service_manifest["spec"]["type"] == "LoadBalancer"
    assert service_manifest["spec"]["ports"] == [
        {"port": 8000, "targetPort": 8000}
    ]


def test_service_manifest_is_json_serializable():
    """The Service manifest can be JSON-serialized as-is."""
    service_manifest = build_vllm_service_manifest(
        name="vllm-test",
        namespace="zenml-vllm",
        port=8000,
        service_type=KubernetesServiceType.CLUSTER_IP,
        selector_labels=LABELS,
        labels=LABELS,
    )

    json.dumps(service_manifest)
