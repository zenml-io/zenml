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
"""Unit tests for the vLLM Kubernetes deployment service."""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from kubernetes import client as k8s_client

from zenml.enums import KubernetesServiceType, ServiceState
from zenml.integrations.vllm.flavors.vllm_kubernetes_model_deployer_flavor import (
    DEFAULT_VLLM_IMAGE,
)
from zenml.integrations.vllm.model_deployers.vllm_kubernetes_model_deployer import (
    KubernetesVLLMModelDeployer,
)
from zenml.integrations.vllm.services.vllm_kubernetes_deployment import (
    VLLMKubernetesDeploymentService,
    VLLMKubernetesServiceConfig,
)


def _build_service(**config_overrides):
    """Build a service with a minimal Kubernetes config.

    Args:
        config_overrides: Keyword arguments overriding the config defaults.

    Returns:
        The service.
    """
    config_kwargs = dict(
        name="vllm-test",
        model="facebook/opt-125m",
        namespace="zenml-vllm",
        port=8000,
    )
    config_kwargs.update(config_overrides)
    return VLLMKubernetesDeploymentService(
        uuid=uuid4(), config=VLLMKubernetesServiceConfig(**config_kwargs)
    )


def _mock_deployer(deployment=None):
    """Build a deployer mock whose applier returns the given Deployment.

    Args:
        deployment: Deployment resource returned by `get_resource`.

    Returns:
        The deployer mock.
    """
    deployer = MagicMock()
    deployer.k8s_applier.get_resource.return_value = deployment
    return deployer


def test_check_status_inactive_when_deployment_missing():
    """A missing Deployment maps to INACTIVE."""
    service = _build_service()
    deployer = _mock_deployer(deployment=None)

    with patch.object(
        KubernetesVLLMModelDeployer,
        "get_active_model_deployer",
        return_value=deployer,
    ):
        state, message = service.check_status()

    assert state == ServiceState.INACTIVE
    assert message == ""


def test_check_status_active_when_available_replicas_meet_desired():
    """Available replicas meeting the desired count maps to ACTIVE."""
    service = _build_service()
    deployment = {
        "spec": {"replicas": 2},
        "status": {"availableReplicas": 2, "conditions": []},
    }
    deployer = _mock_deployer(deployment=deployment)

    with (
        patch.object(
            KubernetesVLLMModelDeployer,
            "get_active_model_deployer",
            return_value=deployer,
        ),
        patch.object(service, "_list_pods", return_value=[]),
        patch.object(service, "_get_pod_failure_message", return_value=None),
    ):
        state, _ = service.check_status()

    assert state == ServiceState.ACTIVE


def test_check_status_error_on_progress_deadline_exceeded():
    """A stuck rollout maps to ERROR with the condition's message."""
    service = _build_service()
    deployment = {
        "spec": {"replicas": 2},
        "status": {
            "availableReplicas": 0,
            "conditions": [
                {
                    "type": "Progressing",
                    "reason": "ProgressDeadlineExceeded",
                    "message": "deployment exceeded its progress deadline",
                }
            ],
        },
    }
    deployer = _mock_deployer(deployment=deployment)

    with patch.object(
        KubernetesVLLMModelDeployer,
        "get_active_model_deployer",
        return_value=deployer,
    ):
        state, message = service.check_status()

    assert state == ServiceState.ERROR
    assert message == "deployment exceeded its progress deadline"


def test_check_status_pending_startup_when_replicas_not_yet_available():
    """Fewer available replicas than desired maps to PENDING_STARTUP."""
    service = _build_service()
    deployment = {
        "spec": {"replicas": 2},
        "status": {"availableReplicas": 1, "conditions": []},
    }
    deployer = _mock_deployer(deployment=deployment)

    with (
        patch.object(
            KubernetesVLLMModelDeployer,
            "get_active_model_deployer",
            return_value=deployer,
        ),
        patch.object(service, "_list_pods", return_value=[]),
        patch.object(service, "_get_pod_failure_message", return_value=None),
        patch.object(service, "_get_pod_pending_message", return_value=None),
    ):
        state, _ = service.check_status()

    assert state == ServiceState.PENDING_STARTUP


def test_check_status_error_on_crash_loop_backoff():
    """A crash-looping pod maps to ERROR with the failure details."""
    service = _build_service()
    deployment = {
        "spec": {"replicas": 1},
        "status": {"availableReplicas": 0, "conditions": []},
    }
    deployer = _mock_deployer(deployment=deployment)

    with (
        patch.object(
            KubernetesVLLMModelDeployer,
            "get_active_model_deployer",
            return_value=deployer,
        ),
        patch.object(service, "_list_pods", return_value=[]),
        patch.object(
            service,
            "_get_pod_failure_message",
            return_value="container waiting reason: CrashLoopBackOff",
        ),
    ):
        state, message = service.check_status()

    assert state == ServiceState.ERROR
    assert message == "container waiting reason: CrashLoopBackOff"


def test_check_status_pending_startup_on_unschedulable_pod():
    """An unschedulable pod maps to PENDING_STARTUP, not ERROR.

    An unschedulable pod is indistinguishable at observation time from the
    cluster autoscaler being about to add a node that fits it. The
    unschedulable detail is still surfaced in the status message.
    """
    service = _build_service()
    deployment = {
        "spec": {"replicas": 1},
        "status": {"availableReplicas": 0, "conditions": []},
    }
    deployer = _mock_deployer(deployment=deployment)
    pending_message = (
        "pod `vllm-test-0`: pod condition: PodScheduled, Unschedulable, "
        "message=0/3 nodes are available: 3 Insufficient nvidia.com/gpu"
    )

    with (
        patch.object(
            KubernetesVLLMModelDeployer,
            "get_active_model_deployer",
            return_value=deployer,
        ),
        patch.object(service, "_list_pods", return_value=[]),
        patch.object(service, "_get_pod_failure_message", return_value=None),
        patch.object(
            service,
            "_get_pod_pending_message",
            return_value=pending_message,
        ),
    ):
        state, message = service.check_status()

    assert state == ServiceState.PENDING_STARTUP
    assert message == pending_message


def test_list_pods_uses_label_selector_and_namespace():
    """Pods are listed with the service's namespace and label selector."""
    service = _build_service()
    core_api = MagicMock()
    core_api.list_namespaced_pod.return_value = k8s_client.V1PodList(items=[])

    service._list_pods(core_api)

    core_api.list_namespaced_pod.assert_called_once_with(
        namespace="zenml-vllm",
        label_selector=f"managed-by=zenml,zenml-service-uuid={service.uuid}",
    )


def test_get_pod_failure_message_detects_crash_loop_backoff():
    """A crash-looping container is surfaced as a failure message."""
    service = _build_service()
    pod = k8s_client.V1Pod(
        spec=k8s_client.V1PodSpec(
            containers=[k8s_client.V1Container(name="vllm", image="img")]
        ),
        status=k8s_client.V1PodStatus(
            container_statuses=[
                k8s_client.V1ContainerStatus(
                    name="vllm",
                    image="img",
                    image_id="",
                    ready=False,
                    restart_count=1,
                    state=k8s_client.V1ContainerState(
                        waiting=k8s_client.V1ContainerStateWaiting(
                            reason="CrashLoopBackOff",
                        )
                    ),
                )
            ]
        ),
    )

    message = service._get_pod_failure_message([pod])

    assert message is not None
    assert "CrashLoopBackOff" in message


def test_get_pod_failure_message_none_when_no_pods_failing():
    """No failure message is returned when no pod is crash-looping."""
    service = _build_service()
    pod = k8s_client.V1Pod(
        spec=k8s_client.V1PodSpec(
            containers=[k8s_client.V1Container(name="vllm", image="img")]
        ),
        status=k8s_client.V1PodStatus(container_statuses=[]),
    )

    assert service._get_pod_failure_message([pod]) is None


def test_get_pod_pending_message_detects_unschedulable_condition():
    """An unschedulable pod condition is surfaced as a pending message."""
    service = _build_service()
    pod = k8s_client.V1Pod(
        status=k8s_client.V1PodStatus(
            conditions=[
                k8s_client.V1PodCondition(
                    type="PodScheduled",
                    status="False",
                    reason="Unschedulable",
                    message="0/3 nodes are available",
                )
            ]
        ),
    )

    message = service._get_pod_pending_message([pod])

    assert message is not None
    assert "Unschedulable" in message


def test_get_pod_pending_message_none_when_no_pods_pending():
    """No pending message is returned when no pod has a pending condition."""
    service = _build_service()

    assert service._get_pod_pending_message([]) is None


def test_deployment_and_service_names_are_deterministic_and_sanitized():
    """Resource names are derived from the service UUID and sanitized."""
    service_uuid = uuid4()
    service = _build_service()
    service.uuid = service_uuid

    assert service.deployment_name == f"vllm-{service_uuid}"
    assert service.service_name == f"vllm-{service_uuid}"
    assert service.hf_secret_name == f"vllm-hf-{service_uuid}"


def test_namespace_falls_back_to_deployer_namespace_when_unset():
    """Reading namespace without a configured value falls back to the deployer's namespace."""
    service = VLLMKubernetesDeploymentService(
        uuid=uuid4(),
        config=VLLMKubernetesServiceConfig(
            name="vllm-test", model="facebook/opt-125m", port=8000
        ),
    )
    deployer = MagicMock()
    deployer.config.kubernetes_namespace = "deployer-namespace"

    with patch.object(
        KubernetesVLLMModelDeployer,
        "get_active_model_deployer",
        return_value=deployer,
    ):
        assert service.namespace == "deployer-namespace"


def test_namespace_uses_configured_value_when_set():
    """Reading namespace with a configured value returns it as-is."""
    service = _build_service()

    assert service.namespace == "zenml-vllm"


def test_service_type_falls_back_to_deployer_service_type_when_unset():
    """Reading service_type without a configured value falls back to the deployer's default_service_type."""
    service = _build_service()
    deployer = MagicMock()
    deployer.config.default_service_type = KubernetesServiceType.NODE_PORT

    with patch.object(
        KubernetesVLLMModelDeployer,
        "get_active_model_deployer",
        return_value=deployer,
    ):
        assert service.service_type == KubernetesServiceType.NODE_PORT


def test_service_type_falls_back_to_cluster_ip_when_no_deployer_resolvable():
    """Reading service_type without a configured value or resolvable deployer falls back to CLUSTER_IP."""
    service = _build_service()

    with patch.object(
        KubernetesVLLMModelDeployer,
        "get_active_model_deployer",
        side_effect=TypeError("no active model deployer"),
    ):
        assert service.service_type == KubernetesServiceType.CLUSTER_IP


def test_service_type_uses_configured_value_when_set():
    """Reading service_type with a configured value returns it as-is."""
    service = _build_service(service_type=KubernetesServiceType.LOAD_BALANCER)

    assert service.service_type == KubernetesServiceType.LOAD_BALANCER


def test_image_falls_back_to_deployer_default_image_when_unset():
    """Reading image without a configured value falls back to the deployer's default_image."""
    service = _build_service()
    deployer = MagicMock()
    deployer.config.default_image = "vllm/deployer-image:latest"

    with patch.object(
        KubernetesVLLMModelDeployer,
        "get_active_model_deployer",
        return_value=deployer,
    ):
        assert service.image == "vllm/deployer-image:latest"


def test_image_falls_back_to_default_constant_when_no_deployer_resolvable():
    """Reading image without a configured value or resolvable deployer falls back to DEFAULT_VLLM_IMAGE."""
    service = _build_service()

    with patch.object(
        KubernetesVLLMModelDeployer,
        "get_active_model_deployer",
        side_effect=TypeError("no active model deployer"),
    ):
        assert service.image == DEFAULT_VLLM_IMAGE


def test_image_uses_configured_value_when_set():
    """Reading image with a configured value returns it as-is."""
    service = _build_service(image="vllm/custom-image:latest")

    assert service.image == "vllm/custom-image:latest"


def test_service_url_resolves_base_url_when_running():
    """The base URL is resolved when the service is running."""
    service = _build_service()

    with (
        patch.object(
            VLLMKubernetesDeploymentService,
            "check_status",
            return_value=(ServiceState.ACTIVE, ""),
        ),
        patch.object(
            service,
            "_resolve_service_url",
            return_value="http://1.2.3.4:8000",
        ),
    ):
        assert service.service_url == "http://1.2.3.4:8000"


def test_service_url_none_when_service_not_running():
    """No base URL is resolved while the Deployment is not active."""
    service = _build_service()

    with patch.object(
        VLLMKubernetesDeploymentService,
        "check_status",
        return_value=(ServiceState.INACTIVE, ""),
    ):
        assert service.service_url is None


def test_prediction_url_composes_base_url_with_prediction_path():
    """The prediction URL appends the OpenAI-compatible path to the base URL."""
    service = _build_service()

    with (
        patch.object(
            VLLMKubernetesDeploymentService,
            "check_status",
            return_value=(ServiceState.ACTIVE, ""),
        ),
        patch.object(
            service,
            "_resolve_service_url",
            return_value="http://1.2.3.4:8000",
        ),
    ):
        assert service.prediction_url == "http://1.2.3.4:8000/v1"


def test_healthcheck_url_composes_base_url_with_health_path():
    """The healthcheck URL appends the health path to the base URL."""
    service = _build_service()

    with (
        patch.object(
            VLLMKubernetesDeploymentService,
            "check_status",
            return_value=(ServiceState.ACTIVE, ""),
        ),
        patch.object(
            service,
            "_resolve_service_url",
            return_value="http://1.2.3.4:8000",
        ),
    ):
        assert service.healthcheck_url == "http://1.2.3.4:8000/health"


def test_prediction_url_none_when_service_not_running():
    """No prediction URL is exposed while the Deployment is not active."""
    service = _build_service()

    with patch.object(
        VLLMKubernetesDeploymentService,
        "check_status",
        return_value=(ServiceState.INACTIVE, ""),
    ):
        assert service.prediction_url is None


def test_prediction_url_none_when_service_url_not_resolvable():
    """No prediction URL is exposed when the Service has no resolvable address."""
    service = _build_service()

    with (
        patch.object(
            VLLMKubernetesDeploymentService,
            "check_status",
            return_value=(ServiceState.ACTIVE, ""),
        ),
        patch.object(service, "_resolve_service_url", return_value=None),
    ):
        assert service.prediction_url is None


def test_resolve_service_url_none_when_service_resource_missing():
    """No base URL is resolved when the Service resource does not exist."""
    service = _build_service()
    deployer = _mock_deployer(deployment=None)

    with patch.object(
        KubernetesVLLMModelDeployer,
        "get_active_model_deployer",
        return_value=deployer,
    ):
        assert service._resolve_service_url() is None


def test_resolve_service_url_delegates_to_build_service_url():
    """The base URL is built via kube_utils.build_service_url."""
    service = _build_service()
    deployer = _mock_deployer(deployment={"spec": {"type": "ClusterIP"}})

    with (
        patch.object(
            KubernetesVLLMModelDeployer,
            "get_active_model_deployer",
            return_value=deployer,
        ),
        patch(
            "zenml.integrations.vllm.services.vllm_kubernetes_deployment."
            "kube_utils.build_service_url",
            return_value="http://10.0.0.1:8000",
        ) as build_service_url_mock,
    ):
        assert service._resolve_service_url() == "http://10.0.0.1:8000"

    build_service_url_mock.assert_called_once()
