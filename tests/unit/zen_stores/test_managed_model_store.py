"""Exercise persistence, retries and fencing against a disposable database."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import Column, MetaData, Table, Uuid, create_engine, event

from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.managed_models.state import ManagedModelCheckpoint
from zenml.models.managed_model import (
    ManagedModelMutation,
    ManagedModelServiceRequest,
)
from zenml.zen_stores.managed_model_store import ManagedModelStore
from zenml.zen_stores.schemas.managed_model_schemas import (
    ManagedModelOperationSchema,
    ManagedModelServiceSchema,
)


@pytest.fixture
def serving_store(tmp_path):
    """Use real constraints with minimal parent identity tables."""
    engine = create_engine(f"sqlite:///{tmp_path / 'serving.db'}")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, record):
        connection.execute("PRAGMA foreign_keys=ON")

    metadata = MetaData()
    project = Table("project", metadata, Column("id", Uuid, primary_key=True))
    component = Table(
        "stack_component", metadata, Column("id", Uuid, primary_key=True)
    )
    ManagedModelServiceSchema.__table__.to_metadata(metadata)
    ManagedModelOperationSchema.__table__.to_metadata(metadata)
    metadata.create_all(engine)
    project_id, component_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(project.insert().values(id=project_id))
        connection.execute(component.insert().values(id=component_id))
    artifact = {"artifact_version_id": uuid4()}
    request = ManagedModelServiceRequest(
        project_id=project_id,
        model_deployer_id=component_id,
        name="support",
        serving_profile="chat-v1",
        package={
            "kind": "transformers",
            "model": artifact,
            "tokenizer": artifact,
        },
    )
    yield ManagedModelStore(engine), request
    engine.dispose()


def test_concurrent_create_and_restart_recover_one_intent(serving_store):
    """Duplicate accepted requests survive process replacement without new rows."""
    store, request = serving_store
    with ThreadPoolExecutor(max_workers=2) as executor:
        services = list(
            executor.map(lambda _: store.create(request, "same-key"), range(2))
        )
    assert services[0].id == services[1].id
    restarted = ManagedModelStore(store.engine)
    assert restarted.create(request, "same-key").id == services[0].id
    assert restarted.list(request.project_id).total == 1
    assert restarted.list(uuid4()).total == 0
    with pytest.raises(EntityExistsError):
        restarted.create(
            request.model_copy(update={"name": "different"}), "same-key"
        )


def test_expired_lease_recovers_checkpoint_and_fences_old_worker(
    serving_store, monkeypatch
):
    """A recovered attempt retains evidence and rejects a late old callback."""
    store, request = serving_store
    store.create(request, "create")
    first = store.claim(lease_seconds=1)
    assert first is not None
    store.checkpoint(first, ManagedModelCheckpoint(phase="submission_started"))
    monkeypatch.setattr(
        "zenml.zen_stores.managed_model_store.utc_now",
        lambda: first.expires_at + timedelta(seconds=1),
    )
    second = store.claim()
    assert second is not None
    assert second.operation_id == first.operation_id
    assert second.lease_id != first.lease_id
    assert second.checkpoint.phase == "submission_started"
    with pytest.raises(IllegalOperationError):
        store.checkpoint(first, ManagedModelCheckpoint(phase="submitted"))


def test_update_preserves_active_revision_and_rejects_conflicts(serving_store):
    """Candidate acceptance keeps the serving revision and serializes mutations."""
    store, request = serving_store
    service = store.create(request, "create")
    with pytest.raises(EntityExistsError):
        store.mutate(
            service.id,
            ManagedModelMutation(action="delete", expected_generation=1),
            "early-delete",
        )
    lease = store.claim()
    assert lease is not None
    service = lease.service
    service.state = "ready"
    service.active_revision_id = lease.target_revision_id
    service.operation.status = "succeeded"
    store.finish(lease, service, {})
    old_revision = service.active_revision_id
    update = ManagedModelMutation(
        action="update",
        expected_generation=1,
        revision={"package": request.package, "serving_profile": "chat-v2"},
    )
    updated = store.mutate(service.id, update, "update")
    assert updated.active_revision_id == old_revision
    assert updated.state == "ready"
    assert len(updated.revisions) == 2
    assert (
        store.mutate(service.id, update, "update").operation.id
        == updated.operation.id
    )
    with pytest.raises(EntityExistsError):
        store.mutate(
            service.id,
            ManagedModelMutation(action="pause", expected_generation=1),
            "stale",
        )


def test_permission_filter_applies_before_count_and_pagination(serving_store):
    """Restricted callers cannot infer hidden service counts or page offsets."""
    store, request = serving_store
    hidden = store.create(request, "hidden")
    visible = store.create(request, "visible")
    page = store.list(request.project_id, limit=1, allowed_ids={visible.id})
    assert page.total == 1
    assert [item.id for item in page.items] == [visible.id]
    assert hidden.id != visible.id
    assert store.list(request.project_id, allowed_ids=set()).total == 0


def test_concurrent_identical_mutations_return_one_operation(serving_store):
    """Concurrent retries recover the winning intent instead of reporting conflict."""
    store, request = serving_store
    service = store.create(request, "create")
    lease = store.claim()
    service = lease.service
    service.active_revision_id = lease.target_revision_id
    service.state = "ready"
    service.operation.status = "succeeded"
    store.finish(lease, service, {})
    mutation = ManagedModelMutation(action="pause", expected_generation=1)
    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(
            executor.map(
                lambda _: store.mutate(service.id, mutation, "pause"), range(2)
            )
        )
    assert outcomes[0].operation.id == outcomes[1].operation.id
    assert outcomes[0].generation == outcomes[1].generation == 2
