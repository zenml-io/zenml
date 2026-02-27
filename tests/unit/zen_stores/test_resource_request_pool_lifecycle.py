from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Tuple
from uuid import UUID, uuid4

import pytest
from sqlmodel import Session, select

from zenml.config.step_configurations import Step
from zenml.enums import (
    ExecutionStatus,
    ResourceRequestStatus,
    StackComponentType,
)
from zenml.exceptions import IllegalOperationError
from zenml.models import (
    PipelineRequest,
    ResourcePoolRequest,
    ResourcePoolSubjectPolicyRequest,
    ResourcePoolUpdate,
    ResourceRequestRequest,
)
from zenml.zen_stores.schemas.resource_pool_schemas import (
    ResourcePoolQueueSchema,
    ResourcePoolResourceSchema,
    ResourceRequestSchema,
)
from zenml.zen_stores.sql_zen_store import SqlZenStore


def _create_step_run_in_db(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
    *,
    step_name: str = "sample_step",
) -> Tuple[UUID, UUID]:
    """Create a pipeline run and one step run in the DB.

    Args:
        clean_client: Test client fixture.
        sample_pipeline_snapshot_request_model: Snapshot request fixture.
        sample_pipeline_run_request_model: Pipeline run request fixture.
        sample_step_request_model: Step run request fixture.
        step_name: Name of the created step.

    Returns:
        A tuple of `(pipeline_run_id, step_run_id)`.
    """
    store = clean_client.zen_store
    pipeline = store.create_pipeline(
        PipelineRequest(
            name=f"test-pipeline-{uuid4()}",
            project=clean_client.active_project.id,
        )
    )

    snapshot_request = deepcopy(sample_pipeline_snapshot_request_model)
    snapshot_request.project = clean_client.active_project.id
    snapshot_request.stack = clean_client.active_stack.id
    snapshot_request.pipeline = pipeline.id
    snapshot_request.step_configurations = {
        step_name: Step.model_validate(
            {
                "spec": {
                    "source": "module.step_class",
                    "upstream_steps": [],
                    "inputs": {},
                },
                "config": {"name": step_name},
            }
        )
    }
    snapshot = store.create_snapshot(snapshot_request)

    run_request = deepcopy(sample_pipeline_run_request_model)
    run_request.project = clean_client.active_project.id
    run_request.snapshot = snapshot.id
    run_request.name = f"test-run-{uuid4()}"
    run_request.status = ExecutionStatus.RUNNING
    run, created = store.get_or_create_run(run_request)
    assert created

    step_request = deepcopy(sample_step_request_model)
    step_request.project = clean_client.active_project.id
    step_request.pipeline_run_id = run.id
    step_request.name = step_name
    step_request.status = ExecutionStatus.RUNNING
    step_request.start_time = datetime.utcnow()
    step = store.create_run_step(step_request)
    return run.id, step.id


def _create_orchestrator_component(clean_client, name: str) -> UUID:
    """Create an orchestrator component and return its ID.

    Args:
        clean_client: Test client fixture.
        name: Prefix for the component name.

    Returns:
        The created component ID.
    """
    component = clean_client.create_stack_component(
        name=f"{name}-{uuid4()}",
        flavor="local",
        component_type=StackComponentType.ORCHESTRATOR,
        configuration={},
    )
    return component.id


def _create_pool(
    clean_client,
    *,
    capacity: Dict[str, int],
    policies: List[ResourcePoolSubjectPolicyRequest],
):
    """Create a resource pool with policies.

    Args:
        clean_client: Test client fixture.
        capacity: Pool capacity per resource key.
        policies: Policies to attach to the pool.

    Returns:
        The created pool model.
    """
    return clean_client.zen_store.create_resource_pool(
        ResourcePoolRequest(
            name=f"pool-{uuid4()}",
            capacity=capacity,
            policies=policies,
        )
    )


def _create_resource_request(
    clean_client,
    *,
    component_id: UUID,
    step_run_id: UUID,
    requested_resources: Dict[str, int],
    preemptable: bool = True,
):
    """Create a resource request.

    Args:
        clean_client: Test client fixture.
        component_id: Component requesting resources.
        step_run_id: Step run owning the request.
        requested_resources: Requested resources per key.
        preemptable: Whether the request is preemptable.

    Returns:
        The created resource request model.
    """
    return clean_client.zen_store.create_resource_request(
        ResourceRequestRequest(
            component_id=component_id,
            step_run_id=step_run_id,
            requested_resources=requested_resources,
            preemptable=preemptable,
        )
    )


def _get_request(clean_client, request_id: UUID):
    return clean_client.zen_store.get_resource_request(
        request_id, hydrate=False
    )


def _get_pool(clean_client, pool_id: UUID):
    return clean_client.zen_store.get_resource_pool(pool_id, hydrate=True)


def test_request_rejected_if_exceeds_pool_total_capacity(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            )
        ],
    )

    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 2},
    )
    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.REJECTED
    )


def test_request_rejected_if_exceeds_policy_limit(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 2},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            )
        ],
    )

    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 2},
    )
    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.REJECTED
    )


def test_non_preemptable_request_rejected_if_exceeds_reserved_share(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 2},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 2},
            )
        ],
    )

    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 2},
        preemptable=False,
    )
    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.REJECTED
    )


def test_request_allocated_when_equal_pool_total_capacity(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 2},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 2},
                limit={"gpu": 2},
            )
        ],
    )

    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 2},
    )
    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.ALLOCATED
    )


def test_request_allocated_when_equal_policy_limit(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 3},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 2},
            )
        ],
    )

    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 2},
    )
    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.ALLOCATED
    )


def test_non_preemptable_request_allocated_when_equal_reserved_share(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 3},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 2},
                limit={"gpu": 3},
            )
        ],
    )

    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 2},
        preemptable=False,
    )
    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.ALLOCATED
    )


def test_missing_unbounded_pool_key_allows_allocation(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            )
        ],
    )

    _, cpu_step = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    cpu_request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=cpu_step,
        requested_resources={"cpu": 100},
    )

    assert (
        _get_request(clean_client, cpu_request.id).status
        == ResourceRequestStatus.ALLOCATED
    )


def test_missing_bounded_pool_key_rejects_request(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            )
        ],
    )

    _, disk_step = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    disk_request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=disk_step,
        requested_resources={"disk": 1},
    )

    assert (
        _get_request(clean_client, disk_request.id).status
        == ResourceRequestStatus.REJECTED
    )


def test_missing_policy_key_inherits_bounded_pool_capacity(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 2},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={},
                limit={},
            )
        ],
    )

    _, step_fit = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_too_large = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    fit_request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_fit,
        requested_resources={"gpu": 2},
    )
    too_large_request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_too_large,
        requested_resources={"gpu": 3},
    )

    assert (
        _get_request(clean_client, fit_request.id).status
        == ResourceRequestStatus.ALLOCATED
    )
    assert (
        _get_request(clean_client, too_large_request.id).status
        == ResourceRequestStatus.REJECTED
    )


def test_explicit_policy_limit_zero_overrides_pool_capacity(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 2},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={},
                limit={"gpu": 0},
            )
        ],
    )

    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 1},
    )

    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.REJECTED
    )


def test_policy_without_key_can_use_new_pool_key_after_capacity_update(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={},
                limit={},
            )
        ],
    )

    _, step_before = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    before_update = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_before,
        requested_resources={"disk": 1},
    )
    assert (
        _get_request(clean_client, before_update.id).status
        == ResourceRequestStatus.REJECTED
    )

    clean_client.zen_store.update_resource_pool(
        pool.id, ResourcePoolUpdate(capacity={"gpu": 1, "disk": 2})
    )

    _, step_after = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    after_update = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_after,
        requested_resources={"disk": 2},
    )
    assert (
        _get_request(clean_client, after_update.id).status
        == ResourceRequestStatus.ALLOCATED
    )


def test_allocation_respects_non_preemptable_reserved_share(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _, step_1 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_2 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_3 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    pool = _create_pool(
        clean_client,
        capacity={"gpu": 2},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 2},
            )
        ],
    )

    req_1 = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_1,
        requested_resources={"gpu": 1},
        preemptable=False,
    )
    req_2 = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_2,
        requested_resources={"gpu": 1},
        preemptable=False,
    )
    req_3 = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_3,
        requested_resources={"gpu": 1},
        preemptable=True,
    )

    assert (
        _get_request(clean_client, req_1.id).status
        == ResourceRequestStatus.ALLOCATED
    )
    assert (
        _get_request(clean_client, req_2.id).status
        == ResourceRequestStatus.PENDING
    )
    assert (
        _get_request(clean_client, req_3.id).status
        == ResourceRequestStatus.ALLOCATED
    )

    hydrated_pool = _get_pool(clean_client, pool.id)
    active_ids = {item.request.id for item in hydrated_pool.active_requests}
    queued_ids = {item.request.id for item in hydrated_pool.queued_requests}
    assert req_1.id in active_ids
    assert req_3.id in active_ids
    assert req_2.id in queued_ids


def test_preemption_skips_non_preemptable_victims(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
    monkeypatch,
):
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    low_priority_component = _create_orchestrator_component(
        clean_client, "low"
    )
    high_priority_component = _create_orchestrator_component(
        clean_client, "high"
    )

    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=low_priority_component,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            ),
            ResourcePoolSubjectPolicyRequest(
                component_id=high_priority_component,
                priority=2,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            ),
        ],
    )

    _, low_step = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, high_step = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    victim = _create_resource_request(
        clean_client,
        component_id=low_priority_component,
        step_run_id=low_step,
        requested_resources={"gpu": 1},
        preemptable=False,
    )

    evictions: List[UUID] = []

    def _mock_trigger(self, session, request_id):
        evictions.append(request_id)

    monkeypatch.setattr(
        SqlZenStore, "_trigger_resource_request_eviction", _mock_trigger
    )

    head = _create_resource_request(
        clean_client,
        component_id=high_priority_component,
        step_run_id=high_step,
        requested_resources={"gpu": 1},
        preemptable=True,
    )

    assert (
        _get_request(clean_client, victim.id).status
        == ResourceRequestStatus.ALLOCATED
    )
    assert (
        _get_request(clean_client, head.id).status
        == ResourceRequestStatus.PENDING
    )
    assert evictions == []
    assert _get_pool(clean_client, pool.id).queued_requests


def test_preemption_triggers_for_preemptable_victims(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
    monkeypatch,
):
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    low_priority_component = _create_orchestrator_component(
        clean_client, "low"
    )
    high_priority_component = _create_orchestrator_component(
        clean_client, "high"
    )

    _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=low_priority_component,
                priority=1,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            ),
            ResourcePoolSubjectPolicyRequest(
                component_id=high_priority_component,
                priority=2,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            ),
        ],
    )

    _, low_step = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, high_step = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    victim = _create_resource_request(
        clean_client,
        component_id=low_priority_component,
        step_run_id=low_step,
        requested_resources={"gpu": 1},
        preemptable=True,
    )

    evictions: List[UUID] = []

    def _mock_trigger(self, session, request_id):
        evictions.append(request_id)

    monkeypatch.setattr(
        SqlZenStore, "_trigger_resource_request_eviction", _mock_trigger
    )

    _create_resource_request(
        clean_client,
        component_id=high_priority_component,
        step_run_id=high_step,
        requested_resources={"gpu": 1},
        preemptable=True,
    )

    assert evictions == [victim.id]
    assert (
        _get_request(clean_client, victim.id).status
        == ResourceRequestStatus.PREEMPTING
    )


def test_orphaned_requests_are_cancelled_before_allocation(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            )
        ],
    )

    run_1, step_1 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    orphan_candidate = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_1,
        requested_resources={"gpu": 1},
        preemptable=True,
    )
    assert (
        _get_request(clean_client, orphan_candidate.id).status
        == ResourceRequestStatus.ALLOCATED
    )

    clean_client.zen_store.delete_run(run_1)

    _, step_2 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    next_request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_2,
        requested_resources={"gpu": 1},
        preemptable=True,
    )

    orphan = _get_request(clean_client, orphan_candidate.id)
    assert orphan.status == ResourceRequestStatus.CANCELLED
    assert (
        orphan.status_reason
        == "Cancelled because owning step run no longer exists."
    )
    assert (
        _get_request(clean_client, next_request.id).status
        == ResourceRequestStatus.ALLOCATED
    )
    assert _get_pool(clean_client, pool.id).active_requests


def test_attaching_policy_allocates_pending_requests_from_other_pool(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool_a = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            )
        ],
    )
    pool_b = _create_pool(clean_client, capacity={"gpu": 1}, policies=[])

    _, step_1 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_2 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_1,
        requested_resources={"gpu": 1},
    )
    pending = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_2,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, pending.id).status
        == ResourceRequestStatus.PENDING
    )

    clean_client.zen_store.update_resource_pool(
        pool_b.id,
        ResourcePoolUpdate(
            attach_policies=[
                ResourcePoolSubjectPolicyRequest(
                    component_id=component_id,
                    priority=5,
                    reserved={"gpu": 1},
                    limit={"gpu": 1},
                )
            ]
        ),
    )

    pending_after = _get_request(clean_client, pending.id)
    assert pending_after.status == ResourceRequestStatus.ALLOCATED
    assert pending_after.running_in_pool is not None
    assert pending_after.running_in_pool.id == pool_b.id
    assert _get_pool(clean_client, pool_a.id).queued_requests == []


def test_detaching_policy_blocked_if_component_has_active_requests(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            )
        ],
    )

    _, step_1 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_2 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    allocated = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_1,
        requested_resources={"gpu": 1},
    )
    queued = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_2,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, queued.id).status
        == ResourceRequestStatus.PENDING
    )

    with pytest.raises(IllegalOperationError):
        clean_client.zen_store.update_resource_pool(
            pool.id,
            ResourcePoolUpdate(detach_policies=[component_id]),
        )

    assert (
        _get_request(clean_client, allocated.id).status
        == ResourceRequestStatus.ALLOCATED
    )
    assert (
        _get_request(clean_client, queued.id).status
        == ResourceRequestStatus.PENDING
    )


def test_decreasing_pool_capacity_keeps_allocated_and_rebuilds_queue(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 2},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 0},
                limit={"gpu": 2},
            )
        ],
    )

    _, step_1 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_2 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_3 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    allocated = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_1,
        requested_resources={"gpu": 2},
    )
    pending_too_large = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_2,
        requested_resources={"gpu": 2},
    )
    pending_small = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_3,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, pending_too_large.id).status
        == ResourceRequestStatus.PENDING
    )
    assert (
        _get_request(clean_client, pending_small.id).status
        == ResourceRequestStatus.PENDING
    )

    clean_client.zen_store.update_resource_pool(
        pool.id, ResourcePoolUpdate(capacity={"gpu": 1})
    )

    assert (
        _get_request(clean_client, allocated.id).status
        == ResourceRequestStatus.ALLOCATED
    )
    assert (
        _get_request(clean_client, pending_too_large.id).status
        == ResourceRequestStatus.REJECTED
    )
    assert (
        _get_request(clean_client, pending_small.id).status
        == ResourceRequestStatus.PENDING
    )


def test_deleting_pool_blocked_if_pool_has_active_requests(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            )
        ],
    )

    _, step_1 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_2 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_1,
        requested_resources={"gpu": 1},
    )
    _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_2,
        requested_resources={"gpu": 1},
    )

    with pytest.raises(IllegalOperationError):
        clean_client.zen_store.delete_resource_pool(pool.id)

    assert _get_pool(clean_client, pool.id).id == pool.id


def test_orphan_cleanup_cancels_allocated_and_queued_requests(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            )
        ],
    )

    run_1, step_1 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    run_2, step_2 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_3 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    allocated = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_1,
        requested_resources={"gpu": 1},
    )
    queued = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_2,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, allocated.id).status
        == ResourceRequestStatus.ALLOCATED
    )
    assert (
        _get_request(clean_client, queued.id).status
        == ResourceRequestStatus.PENDING
    )

    clean_client.zen_store.delete_run(run_1)
    clean_client.zen_store.delete_run(run_2)

    next_request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_3,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, allocated.id).status
        == ResourceRequestStatus.CANCELLED
    )
    assert (
        _get_request(clean_client, queued.id).status
        == ResourceRequestStatus.CANCELLED
    )
    assert (
        _get_request(clean_client, next_request.id).status
        == ResourceRequestStatus.ALLOCATED
    )


def test_preemption_candidates_filtered_by_requested_resource_keys(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
    monkeypatch,
):
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    low_priority_component = _create_orchestrator_component(
        clean_client, "low-filter"
    )
    high_priority_component = _create_orchestrator_component(
        clean_client, "high-filter"
    )

    _create_pool(
        clean_client,
        capacity={"gpu": 1, "cpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=low_priority_component,
                priority=1,
                reserved={"gpu": 0, "cpu": 0},
                limit={"gpu": 1, "cpu": 1},
            ),
            ResourcePoolSubjectPolicyRequest(
                component_id=high_priority_component,
                priority=2,
                reserved={"gpu": 0, "cpu": 0},
                limit={"gpu": 1, "cpu": 1},
            ),
        ],
    )

    _, low_step_gpu = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, low_step_cpu = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, high_step = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    gpu_victim = _create_resource_request(
        clean_client,
        component_id=low_priority_component,
        step_run_id=low_step_gpu,
        requested_resources={"gpu": 1},
        preemptable=True,
    )
    cpu_victim = _create_resource_request(
        clean_client,
        component_id=low_priority_component,
        step_run_id=low_step_cpu,
        requested_resources={"cpu": 1},
        preemptable=True,
    )
    assert (
        _get_request(clean_client, gpu_victim.id).status
        == ResourceRequestStatus.ALLOCATED
    )
    assert (
        _get_request(clean_client, cpu_victim.id).status
        == ResourceRequestStatus.ALLOCATED
    )

    evictions: List[UUID] = []

    def _mock_trigger(self, session, request_id):
        evictions.append(request_id)

    monkeypatch.setattr(
        SqlZenStore, "_trigger_resource_request_eviction", _mock_trigger
    )

    _create_resource_request(
        clean_client,
        component_id=high_priority_component,
        step_run_id=high_step,
        requested_resources={"gpu": 1},
        preemptable=True,
    )

    assert evictions == [gpu_victim.id]


def test_capacity_rebuild_keeps_boundary_multikey_requests_eligible(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1, "cpu": 4},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 0, "cpu": 0},
                limit={"gpu": 1, "cpu": 4},
            )
        ],
    )

    _, step_alloc = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_boundary = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_too_large = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_alloc,
        requested_resources={"gpu": 1, "cpu": 1},
    )
    boundary = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_boundary,
        requested_resources={"gpu": 1, "cpu": 3},
    )
    too_large = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_too_large,
        requested_resources={"gpu": 1, "cpu": 4},
    )
    assert (
        _get_request(clean_client, boundary.id).status
        == ResourceRequestStatus.PENDING
    )
    assert (
        _get_request(clean_client, too_large.id).status
        == ResourceRequestStatus.PENDING
    )

    clean_client.zen_store.update_resource_pool(
        pool.id, ResourcePoolUpdate(capacity={"gpu": 1, "cpu": 3})
    )

    assert (
        _get_request(clean_client, boundary.id).status
        == ResourceRequestStatus.PENDING
    )
    assert (
        _get_request(clean_client, too_large.id).status
        == ResourceRequestStatus.REJECTED
    )


def test_capacity_rebuild_keeps_pending_non_preemptable_if_still_eligible(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 2},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 2},
            )
        ],
    )

    _, step_alloc = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_non_preemptable = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_preemptable = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_alloc,
        requested_resources={"gpu": 2},
        preemptable=True,
    )
    pending_non_preemptable = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_non_preemptable,
        requested_resources={"gpu": 1},
        preemptable=False,
    )
    pending_preemptable = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_preemptable,
        requested_resources={"gpu": 1},
        preemptable=True,
    )

    clean_client.zen_store.update_resource_pool(
        pool.id, ResourcePoolUpdate(capacity={"gpu": 1})
    )

    assert (
        _get_request(clean_client, pending_non_preemptable.id).status
        == ResourceRequestStatus.PENDING
    )
    assert (
        _get_request(clean_client, pending_preemptable.id).status
        == ResourceRequestStatus.PENDING
    )


def test_detach_and_delete_pool_succeed_after_requests_are_drained(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            )
        ],
    )

    run_1, step_1 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_1,
        requested_resources={"gpu": 1},
    )
    clean_client.zen_store.delete_run(run_1)

    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    with Session(store.engine) as session:
        store._allocate_queued_requests_for_pool(
            session=session, pool_id=pool.id
        )
        session.commit()

    clean_client.zen_store.update_resource_pool(
        pool.id, ResourcePoolUpdate(detach_policies=[component_id])
    )
    clean_client.zen_store.delete_resource_pool(pool.id)

    with pytest.raises(KeyError):
        clean_client.zen_store.get_resource_pool(pool.id)


def test_explicit_bounded_capacity_for_unbounded_key_is_enforced(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"cpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={},
                limit={},
            )
        ],
    )

    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"cpu": 2},
    )

    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.REJECTED
    )


def test_detach_policy_not_blocked_by_other_component_activity(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_a = _create_orchestrator_component(
        clean_client, "detach-scope-a"
    )
    component_b = _create_orchestrator_component(
        clean_client, "detach-scope-b"
    )
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_a,
                priority=1,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            ),
            ResourcePoolSubjectPolicyRequest(
                component_id=component_b,
                priority=2,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            ),
        ],
    )

    _, step_b = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    active_b = _create_resource_request(
        clean_client,
        component_id=component_b,
        step_run_id=step_b,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, active_b.id).status
        == ResourceRequestStatus.ALLOCATED
    )

    clean_client.zen_store.update_resource_pool(
        pool.id, ResourcePoolUpdate(detach_policies=[component_a])
    )


def test_detach_policy_blocked_when_component_has_only_queued_requests(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_a = _create_orchestrator_component(
        clean_client, "detach-queued-a"
    )
    component_b = _create_orchestrator_component(
        clean_client, "detach-queued-b"
    )
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_a,
                priority=1,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            ),
            ResourcePoolSubjectPolicyRequest(
                component_id=component_b,
                priority=2,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            ),
        ],
    )

    _, step_b = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    _, step_a = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )

    _create_resource_request(
        clean_client,
        component_id=component_b,
        step_run_id=step_b,
        requested_resources={"gpu": 1},
    )
    queued_a = _create_resource_request(
        clean_client,
        component_id=component_a,
        step_run_id=step_a,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, queued_a.id).status
        == ResourceRequestStatus.PENDING
    )

    with pytest.raises(IllegalOperationError) as error:
        clean_client.zen_store.update_resource_pool(
            pool.id, ResourcePoolUpdate(detach_policies=[component_a])
        )

    assert "queued=1" in str(error.value)
    assert "allocated=0" in str(error.value)


def test_delete_pool_blocked_when_only_allocated_requests_exist(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            )
        ],
    )

    _, step_1 = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_1,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.ALLOCATED
    )

    with pytest.raises(IllegalOperationError) as error:
        clean_client.zen_store.delete_resource_pool(pool.id)

    assert "queued=0" in str(error.value)
    assert "allocated=1" in str(error.value)


def test_reconciliation_cancels_orphaned_allocations_without_new_requests(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    component_id = clean_client.active_stack.orchestrator.id
    _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 1},
                limit={"gpu": 1},
            )
        ],
    )

    run_id, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.ALLOCATED
    )

    clean_client.zen_store.delete_run(run_id)
    store.reconcile_resource_pools()

    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.CANCELLED
    )


def test_reconciliation_repairs_occupied_resource_counters(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            )
        ],
    )

    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 1},
    )
    assert (
        _get_request(clean_client, request.id).status
        == ResourceRequestStatus.ALLOCATED
    )

    with Session(store.engine) as session:
        pool_resource = session.exec(
            select(ResourcePoolResourceSchema)
            .where(ResourcePoolResourceSchema.pool_id == pool.id)
            .where(ResourcePoolResourceSchema.key == "gpu")
        ).one()
        pool_resource.occupied = 0
        session.add(pool_resource)
        session.commit()

    store.reconcile_resource_pools()

    with Session(store.engine) as session:
        pool_resource = session.exec(
            select(ResourcePoolResourceSchema)
            .where(ResourcePoolResourceSchema.pool_id == pool.id)
            .where(ResourcePoolResourceSchema.key == "gpu")
        ).one()
        assert pool_resource.occupied == 1


def test_reconciliation_cleans_stale_queue_entries(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
):
    store = clean_client.zen_store
    assert isinstance(store, SqlZenStore)
    component_id = clean_client.active_stack.orchestrator.id
    pool = _create_pool(
        clean_client,
        capacity={"gpu": 1},
        policies=[
            ResourcePoolSubjectPolicyRequest(
                component_id=component_id,
                priority=1,
                reserved={"gpu": 0},
                limit={"gpu": 1},
            )
        ],
    )
    _, step_id = _create_step_run_in_db(
        clean_client,
        sample_pipeline_snapshot_request_model,
        sample_pipeline_run_request_model,
        sample_step_request_model,
    )
    request = _create_resource_request(
        clean_client,
        component_id=component_id,
        step_run_id=step_id,
        requested_resources={"gpu": 1},
    )
    request_model = _get_request(clean_client, request.id)
    assert request_model.status == ResourceRequestStatus.ALLOCATED

    with Session(store.engine) as session:
        session.add(
            ResourcePoolQueueSchema(
                pool_id=pool.id,
                request_id=request.id,
                priority=1,
                request_created=request_model.created,
            )
        )
        session.commit()

    with Session(store.engine) as session:
        stale_queue_entries_before = len(
            session.exec(
                select(ResourcePoolQueueSchema.id)
                .join(
                    ResourceRequestSchema,
                    ResourceRequestSchema.id
                    == ResourcePoolQueueSchema.request_id,
                )
                .where(ResourcePoolQueueSchema.pool_id == pool.id)
                .where(
                    ResourceRequestSchema.status
                    != ResourceRequestStatus.PENDING.value
                )
            ).all()
        )
        assert stale_queue_entries_before == 1

    store.reconcile_resource_pools()

    with Session(store.engine) as session:
        stale_queue_entries_after = len(
            session.exec(
                select(ResourcePoolQueueSchema.id)
                .join(
                    ResourceRequestSchema,
                    ResourceRequestSchema.id
                    == ResourcePoolQueueSchema.request_id,
                )
                .where(ResourcePoolQueueSchema.pool_id == pool.id)
                .where(
                    ResourceRequestSchema.status
                    != ResourceRequestStatus.PENDING.value
                )
            ).all()
        )
        assert stale_queue_entries_after == 0
