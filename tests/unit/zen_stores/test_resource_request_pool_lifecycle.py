from copy import deepcopy
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import pytest

from zenml.config.step_configurations import Step
from zenml.enums import ExecutionStatus, ResourceRequestStatus
from zenml.models import (
    ComponentRequest,
    PipelineRequest,
    ResourcePoolRequest,
    ResourcePoolSubjectPolicyRequest,
    ResourcePoolUpdate,
    ResourceRequestRequest,
)
from zenml.enums import StackComponentType
from zenml.zen_stores.sql_zen_store import SqlZenStore


def _create_step_run_in_db(
    clean_client,
    sample_pipeline_snapshot_request_model,
    sample_pipeline_run_request_model,
    sample_step_request_model,
    *,
    step_name: str = "sample_step",
) -> Tuple[UUID, UUID]:
    """Create a pipeline run and one step run in the DB."""
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
    """Create an orchestrator component and return its ID."""
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
    """Create a resource pool with policies."""
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
    """Create a resource request."""
    return clean_client.zen_store.create_resource_request(
        ResourceRequestRequest(
            component_id=component_id,
            step_run_id=step_run_id,
            requested_resources=requested_resources,
            preemptable=preemptable,
        )
    )


def _get_request(clean_client, request_id: UUID):
    return clean_client.zen_store.get_resource_request(request_id, hydrate=False)


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

    assert _get_request(clean_client, req_1.id).status == ResourceRequestStatus.ALLOCATED
    assert _get_request(clean_client, req_2.id).status == ResourceRequestStatus.PENDING
    assert _get_request(clean_client, req_3.id).status == ResourceRequestStatus.ALLOCATED

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
    low_priority_component = _create_orchestrator_component(clean_client, "low")
    high_priority_component = _create_orchestrator_component(clean_client, "high")

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

    assert _get_request(clean_client, victim.id).status == ResourceRequestStatus.ALLOCATED
    assert _get_request(clean_client, head.id).status == ResourceRequestStatus.PENDING
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
    low_priority_component = _create_orchestrator_component(clean_client, "low")
    high_priority_component = _create_orchestrator_component(clean_client, "high")

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
    assert _get_request(clean_client, victim.id).status == ResourceRequestStatus.PREEMPTING


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
    assert _get_request(clean_client, orphan_candidate.id).status == ResourceRequestStatus.ALLOCATED

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
    assert orphan.status_reason == "Cancelled because owning step run no longer exists."
    assert _get_request(clean_client, next_request.id).status == ResourceRequestStatus.ALLOCATED
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
    assert _get_request(clean_client, pending.id).status == ResourceRequestStatus.PENDING

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


# def test_detaching_policy_rejects_enqueued_requests(
#     clean_client,
#     sample_pipeline_snapshot_request_model,
#     sample_pipeline_run_request_model,
#     sample_step_request_model,
# ):
#     component_id = clean_client.active_stack.orchestrator.id
#     pool = _create_pool(
#         clean_client,
#         capacity={"gpu": 1},
#         policies=[
#             ResourcePoolSubjectPolicyRequest(
#                 component_id=component_id,
#                 priority=1,
#                 reserved={"gpu": 1},
#                 limit={"gpu": 1},
#             )
#         ],
#     )

#     _, step_1 = _create_step_run_in_db(
#         clean_client,
#         sample_pipeline_snapshot_request_model,
#         sample_pipeline_run_request_model,
#         sample_step_request_model,
#     )
#     _, step_2 = _create_step_run_in_db(
#         clean_client,
#         sample_pipeline_snapshot_request_model,
#         sample_pipeline_run_request_model,
#         sample_step_request_model,
#     )

#     allocated = _create_resource_request(
#         clean_client,
#         component_id=component_id,
#         step_run_id=step_1,
#         requested_resources={"gpu": 1},
#     )
#     queued = _create_resource_request(
#         clean_client,
#         component_id=component_id,
#         step_run_id=step_2,
#         requested_resources={"gpu": 1},
#     )
#     assert _get_request(clean_client, queued.id).status == ResourceRequestStatus.PENDING

#     clean_client.zen_store.update_resource_pool(
#         pool.id,
#         ResourcePoolUpdate(detach_policies=[component_id]),
#     )

#     assert _get_request(clean_client, allocated.id).status == ResourceRequestStatus.ALLOCATED
#     assert _get_request(clean_client, queued.id).status == ResourceRequestStatus.REJECTED


# def test_updating_pool_capacity_handles_allocated_and_queued_requests(
#     clean_client,
#     sample_pipeline_snapshot_request_model,
#     sample_pipeline_run_request_model,
#     sample_step_request_model,
# ):
#     component_id = clean_client.active_stack.orchestrator.id
#     pool = _create_pool(
#         clean_client,
#         capacity={"gpu": 2},
#         policies=[
#             ResourcePoolSubjectPolicyRequest(
#                 component_id=component_id,
#                 priority=1,
#                 reserved={"gpu": 0},
#                 limit={"gpu": 2},
#             )
#         ],
#     )

#     _, step_1 = _create_step_run_in_db(
#         clean_client,
#         sample_pipeline_snapshot_request_model,
#         sample_pipeline_run_request_model,
#         sample_step_request_model,
#     )
#     _, step_2 = _create_step_run_in_db(
#         clean_client,
#         sample_pipeline_snapshot_request_model,
#         sample_pipeline_run_request_model,
#         sample_step_request_model,
#     )
#     _, step_3 = _create_step_run_in_db(
#         clean_client,
#         sample_pipeline_snapshot_request_model,
#         sample_pipeline_run_request_model,
#         sample_step_request_model,
#     )
#     _, step_4 = _create_step_run_in_db(
#         clean_client,
#         sample_pipeline_snapshot_request_model,
#         sample_pipeline_run_request_model,
#         sample_step_request_model,
#     )

#     allocated = _create_resource_request(
#         clean_client,
#         component_id=component_id,
#         step_run_id=step_1,
#         requested_resources={"gpu": 2},
#     )
#     pending_too_large = _create_resource_request(
#         clean_client,
#         component_id=component_id,
#         step_run_id=step_2,
#         requested_resources={"gpu": 2},
#     )
#     assert _get_request(clean_client, pending_too_large.id).status == ResourceRequestStatus.PENDING

#     clean_client.zen_store.update_resource_pool(
#         pool.id, ResourcePoolUpdate(capacity={"gpu": 1})
#     )

#     assert _get_request(clean_client, allocated.id).status == ResourceRequestStatus.ALLOCATED
#     assert _get_request(clean_client, pending_too_large.id).status == ResourceRequestStatus.REJECTED

#     one_gpu_allocated = _create_resource_request(
#         clean_client,
#         component_id=component_id,
#         step_run_id=step_3,
#         requested_resources={"gpu": 1},
#     )
#     one_gpu_pending = _create_resource_request(
#         clean_client,
#         component_id=component_id,
#         step_run_id=step_4,
#         requested_resources={"gpu": 1},
#     )
#     assert _get_request(clean_client, one_gpu_allocated.id).status == ResourceRequestStatus.ALLOCATED
#     assert _get_request(clean_client, one_gpu_pending.id).status == ResourceRequestStatus.PENDING

#     clean_client.zen_store.update_resource_pool(
#         pool.id, ResourcePoolUpdate(capacity={"gpu": 2})
#     )

#     assert _get_request(clean_client, one_gpu_pending.id).status == ResourceRequestStatus.ALLOCATED

