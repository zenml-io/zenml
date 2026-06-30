"""Tests for Kubernetes resource request allocation helpers."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from zenml.enums import (
    ResourceRequestReclaimTolerance,
    ResourceRequestStatus,
)
from zenml.integrations.kubernetes import kube_utils
from zenml.integrations.kubernetes.flavors import (
    KubernetesStepOperatorSettings,
)
from zenml.integrations.kubernetes.pod_settings import KubernetesPodSettings
from zenml.models import (
    ResourcePoolAllocation,
    ResourcePoolCapacityComponentSettings,
    ResourceRequestDemand,
    ResourceRequestResponse,
    ResourceRequestResponseBody,
    ResourceRequestResponseMetadata,
    ResourceRequestResponseResources,
    ResourceRequestServiceConnectorSettings,
)


def _allocation(
    *,
    request_id: UUID,
    demand_index: int,
    quantity: int,
    unit: str | None = None,
    component_id: UUID | None = None,
    component_settings: (
        list[ResourcePoolCapacityComponentSettings] | None
    ) = None,
) -> ResourcePoolAllocation:
    return ResourcePoolAllocation(
        id=uuid4(),
        request_id=request_id,
        demand_index=demand_index,
        pool_id=uuid4(),
        pool_name="pool",
        resource_id=uuid4(),
        resource="resource",
        class_name="default",
        quantity=quantity,
        unit=unit,
        policy_id=uuid4(),
        priority=0,
        component_id=component_id or uuid4(),
        component_settings=component_settings or [],
        preemption_state="active",
    )


def _resource_request(
    *,
    demands: list[ResourceRequestDemand],
    allocations: list[ResourcePoolAllocation],
    component_settings: dict[str, object] | None = None,
    service_connector_settings: (
        ResourceRequestServiceConnectorSettings | None
    ) = None,
) -> ResourceRequestResponse:
    request_id = allocations[0].request_id if allocations else uuid4()
    return ResourceRequestResponse(
        id=request_id,
        name=str(request_id),
        body=ResourceRequestResponseBody(
            status=ResourceRequestStatus.ALLOCATED,
            user=uuid4(),
            created=datetime.now(tz=timezone.utc),
            updated=datetime.now(tz=timezone.utc),
            version=1,
            demands=demands,
            reclaim_tolerance=ResourceRequestReclaimTolerance.NONE,
        ),
        metadata=ResourceRequestResponseMetadata(),
        resources=ResourceRequestResponseResources(
            component_settings=component_settings or {},
            service_connector_settings=service_connector_settings,
            allocations=allocations,
        ),
    )


def test_unitless_cpu_allocation_threshold() -> None:
    """Unitless CPU allocations above 50 are interpreted as milliCPU."""
    request_id = uuid4()
    demands = [
        ResourceRequestDemand(kind="cpu", quantity=50),
        ResourceRequestDemand(kind="cpu", quantity=51),
    ]

    full_cpu_request = _resource_request(
        demands=demands,
        allocations=[
            _allocation(
                request_id=request_id,
                demand_index=0,
                quantity=50,
            )
        ],
    )
    millicpu_request = _resource_request(
        demands=demands,
        allocations=[
            _allocation(
                request_id=request_id,
                demand_index=1,
                quantity=51,
            )
        ],
    )

    full_cpu_settings = (
        kube_utils.apply_resource_request_allocations_to_pod_settings(
            full_cpu_request
        )
    )
    millicpu_settings = (
        kube_utils.apply_resource_request_allocations_to_pod_settings(
            millicpu_request
        )
    )

    assert full_cpu_settings.resources["requests"]["cpu"] == "50"
    assert full_cpu_settings.resources["limits"]["cpu"] == "50"
    assert millicpu_settings.resources["requests"]["cpu"] == "51m"
    assert millicpu_settings.resources["limits"]["cpu"] == "51m"


def test_cpu_memory_and_gpu_allocations_override_requests_and_limits() -> None:
    """Basic allocations overwrite matching pod requests and limits."""
    request_id = uuid4()
    request = _resource_request(
        demands=[
            ResourceRequestDemand(kind="cpu", quantity=2, unit="CPU"),
            ResourceRequestDemand(kind="memory", quantity=1, unit="GiB"),
            ResourceRequestDemand(kind="gpu", quantity=1),
        ],
        allocations=[
            _allocation(
                request_id=request_id,
                demand_index=0,
                quantity=2,
                unit="CPU",
            ),
            _allocation(
                request_id=request_id,
                demand_index=1,
                quantity=1,
                unit="GiB",
            ),
            _allocation(
                request_id=request_id,
                demand_index=2,
                quantity=1,
            ),
        ],
    )
    pod_settings = KubernetesPodSettings(
        resources={
            "requests": {
                "cpu": "1",
                "example.com/custom": "keep-request",
            },
            "limits": {
                "memory": "1Gi",
                "example.com/custom": "keep-limit",
            },
        }
    )

    result = kube_utils.apply_resource_request_allocations_to_pod_settings(
        request,
        pod_settings=pod_settings,
    )

    assert result.resources["requests"]["cpu"] == "2"
    assert result.resources["limits"]["cpu"] == "2"
    assert result.resources["requests"]["memory"] == "1024Mi"
    assert result.resources["limits"]["memory"] == "1024Mi"
    assert result.resources["requests"]["nvidia.com/gpu"] == "1"
    assert result.resources["limits"]["nvidia.com/gpu"] == "1"
    assert result.resources["requests"]["example.com/custom"] == "keep-request"
    assert result.resources["limits"]["example.com/custom"] == "keep-limit"


def test_multiple_allocations_for_same_kind_are_summed() -> None:
    """Multiple allocations for one resource kind are summed."""
    request_id = uuid4()
    request = _resource_request(
        demands=[
            ResourceRequestDemand(kind="cpu", quantity=250, unit="mCPU"),
            ResourceRequestDemand(kind="gpu", quantity=1),
        ],
        allocations=[
            _allocation(
                request_id=request_id,
                demand_index=0,
                quantity=250,
                unit="mCPU",
            ),
            _allocation(
                request_id=request_id,
                demand_index=0,
                quantity=250,
                unit="mCPU",
            ),
            _allocation(
                request_id=request_id,
                demand_index=1,
                quantity=1,
            ),
            _allocation(
                request_id=request_id,
                demand_index=1,
                quantity=2,
            ),
        ],
    )

    result = kube_utils.apply_resource_request_allocations_to_pod_settings(
        request
    )

    assert result.resources["requests"]["cpu"] == "500m"
    assert result.resources["limits"]["cpu"] == "500m"
    assert result.resources["requests"]["nvidia.com/gpu"] == "3"
    assert result.resources["limits"]["nvidia.com/gpu"] == "3"


def test_matching_component_settings_override_existing_settings() -> None:
    """Resource request component settings override base settings."""
    component_id = uuid4()
    request_id = uuid4()
    request = _resource_request(
        demands=[ResourceRequestDemand(kind="gpu", quantity=1)],
        component_settings={
            "pod_settings": {
                "node_selectors": {
                    "accelerator": "h200",
                },
                "resources": {
                    "requests": {
                        "nvidia.com/gpu": "{{ quantity }}",
                    },
                },
            },
        },
        allocations=[
            _allocation(
                request_id=request_id,
                demand_index=0,
                quantity=1,
                component_id=component_id,
            )
        ],
    )
    settings = KubernetesStepOperatorSettings(
        pod_settings=KubernetesPodSettings(
            node_selectors={"accelerator": "old"},
        )
    )

    result = kube_utils.apply_resource_request_component_settings(
        settings=settings,
        allocated_resource_request=request,
        settings_class=KubernetesStepOperatorSettings,
    )

    assert result.pod_settings is not None
    assert result.pod_settings.node_selectors == {"accelerator": "h200"}
    assert (
        result.pod_settings.resources["requests"]["nvidia.com/gpu"]
        == "{{ quantity }}"
    )


def test_service_connector_settings_do_not_override_component_settings() -> (
    None
):
    """Service connector settings do not affect component settings."""
    component_id = uuid4()
    request_id = uuid4()
    request = _resource_request(
        demands=[ResourceRequestDemand(kind="gpu", quantity=1)],
        service_connector_settings=ResourceRequestServiceConnectorSettings(
            connector_id=uuid4(),
            resource_type="kubernetes-cluster",
            resource_id="cluster",
        ),
        allocations=[
            _allocation(
                request_id=request_id,
                demand_index=0,
                quantity=1,
                component_id=component_id,
            ),
        ],
    )
    settings = KubernetesStepOperatorSettings(
        pod_settings=KubernetesPodSettings(
            node_selectors={"accelerator": "old"},
        )
    )

    result = kube_utils.apply_resource_request_component_settings(
        settings=settings,
        allocated_resource_request=request,
        settings_class=KubernetesStepOperatorSettings,
    )

    assert result.pod_settings is not None
    assert result.pod_settings.node_selectors == {"accelerator": "old"}
