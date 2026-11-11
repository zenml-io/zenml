"""Exercise persistence, retries and fencing against a disposable database."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import (
    Column,
    MetaData,
    Table,
    Uuid,
    create_engine,
    delete,
    event,
)
from sqlalchemy.exc import IntegrityError

from zenml.exceptions import EntityExistsError, IllegalOperationError
from zenml.managed_models.provider import ManagedModelProviderResource
from zenml.managed_models.state import (
    ManagedModelCheckpoint,
    ManagedModelDependency,
)
from zenml.models.managed_model import (
    ManagedModelMutation,
    ManagedModelServiceRequest,
)
from zenml.zen_stores.managed_inference_keys_store import (
    ManagedInferenceKeysStore,
)
from zenml.zen_stores.managed_model_store import ManagedModelStore
from zenml.zen_stores.schemas.managed_model_schemas import (
    ManagedModelDependencySchema,
    ManagedModelOperationSchema,
    ManagedModelServiceSchema,
    ManagedModelWorkspaceSchema,
)
from zenml.zen_stores.schemas.secret_schemas import SecretSchema


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
    Table("artifact_version", metadata, Column("id", Uuid, primary_key=True))
    Table("service_connector", metadata, Column("id", Uuid, primary_key=True))
    ManagedModelDependencySchema.__table__.to_metadata(metadata)
    ManagedModelWorkspaceSchema.__table__.to_metadata(metadata)
    user = Table("user", metadata, Column("id", Uuid, primary_key=True))
    SecretSchema.__table__.to_metadata(metadata)
    metadata.create_all(engine)
    project_id, component_id = uuid4(), uuid4()
    with engine.begin() as connection:
        connection.execute(project.insert().values(id=project_id))
        connection.execute(user.insert().values(id=project_id))
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
    yield ManagedModelStore(engine, retry_base_seconds=0), request
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
            ManagedModelMutation(action="pause", expected_generation=1),
            "early-pause",
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


def test_worker_assignment_is_invalid_after_completion(serving_store):
    """A valid token cannot keep accessing dependencies after its claim ends."""
    store, request = serving_store
    store.create(request, "worker-assignment")
    lease = store.claim()
    assert lease is not None
    assert (
        store.get_claim(lease.operation_id, lease.lease_id).service.id
        == lease.service.id
    )
    with pytest.raises(IllegalOperationError):
        store.get_claim(lease.operation_id, uuid4())
    lease.service.operation.status = "failed"
    store.finish(lease, lease.service, {})
    with pytest.raises(IllegalOperationError):
        store.get_claim(lease.operation_id, lease.lease_id)


def test_inference_selects_active_revision_and_denies_pause_immediately(
    serving_store,
):
    """Admission and target come from one record, independently of provider readiness."""
    store, request = serving_store
    service = store.create(request, "inference-create")
    lease = store.claim()
    service = lease.service
    service.state = "ready"
    service.active_revision_id = lease.target_revision_id
    service.serving_generation = 1
    service.operation.status = "succeeded"
    resource = ManagedModelProviderResource(
        model_id="model", deployment_id="revision", environment="production"
    )
    keys, values = _credential_store(store)
    reference = keys.rotate(service.id, request.project_id)
    key = values[reference.id]["api_key"]
    store.finish(lease, service, {str(lease.target_revision_id): resource})
    target = store.get_inference_target(service.id, key)
    assert (
        target.revision_id == lease.target_revision_id
        and target.resource == resource
    )
    store.mutate(
        service.id,
        ManagedModelMutation(action="pause", expected_generation=1),
        "inference-pause",
    )
    with pytest.raises(IllegalOperationError, match="admission is closed"):
        store.get_inference_target(service.id, key)


def test_retained_dependencies_block_deletion_until_cleanup(serving_store):
    """Real foreign keys protect dependencies and release them after owned cleanup."""
    store, request = serving_store
    source = ManagedModelDependency(
        artifact_version_id=request.package.model.artifact_version_id,
        artifact_store_id=request.model_deployer_id,
        connector_id=uuid4(),
        uri="s3://customer/model/revision/",
    )
    metadata = MetaData()
    metadata.reflect(store.engine)
    with store.engine.begin() as connection:
        connection.execute(
            metadata.tables["artifact_version"]
            .insert()
            .values(id=source.artifact_version_id.hex)
        )
        connection.execute(
            metadata.tables["service_connector"]
            .insert()
            .values(id=source.connector_id.hex)
        )
    service = store.create(request, "retained", [source])
    for table, identity in [
        ("artifact_version", source.artifact_version_id),
        ("service_connector", source.connector_id),
        ("stack_component", source.artifact_store_id),
    ]:
        with pytest.raises(IntegrityError), store.engine.begin() as connection:
            connection.execute(
                delete(metadata.tables[table]).where(
                    metadata.tables[table].c.id == identity
                )
            )
    lease = store.claim()
    assert lease.sources == [source]
    with pytest.raises(IllegalOperationError):
        store.purge(service.id)
    lease.service.operation.status = "failed"
    store.finish(lease, lease.service, {})
    store.mutate(
        service.id,
        ManagedModelMutation(action="delete", expected_generation=1),
        "cleanup-retained",
    )
    lease = store.claim()
    lease.service.state = "deleted"
    lease.service.operation.status = "succeeded"
    store.finish(lease, lease.service, {})
    with store.engine.begin() as connection:
        connection.execute(
            delete(metadata.tables["artifact_version"]).where(
                metadata.tables["artifact_version"].c.id
                == source.artifact_version_id
            )
        )
        connection.execute(
            delete(metadata.tables["service_connector"]).where(
                metadata.tables["service_connector"].c.id
                == source.connector_id
            )
        )
    store.purge(service.id)
    with pytest.raises(KeyError):
        store.get(service.id)


def test_delete_fences_worker_and_waits_before_recovering_submission(
    serving_store, monkeypatch
):
    """Cancellation retains evidence and cannot race the old bounded worker."""
    store, request = serving_store
    service = store.create(request, "cancel-create")
    old = store.claim()
    store.checkpoint(old, ManagedModelCheckpoint(phase="submitting"))
    deletion = store.mutate(
        service.id,
        ManagedModelMutation(action="delete", expected_generation=1),
        "cancel-delete",
    )
    assert deletion.desired_state == "deleted"
    with pytest.raises(IllegalOperationError):
        store.get_claim(old.operation_id, old.lease_id)
    assert store.claim() is None
    monkeypatch.setattr(
        "zenml.zen_stores.managed_model_store.utc_now",
        lambda: old.expires_at + timedelta(seconds=1),
    )
    cleanup = store.claim()
    assert cleanup.service.operation.action == "delete"
    assert cleanup.checkpoint.phase == "submitting"
    assert cleanup.target_revision_id == old.target_revision_id


def test_drain_closes_admission_before_cleanup_can_be_reported(serving_store):
    """A ready teardown response cannot race a newly accepted deployment."""
    store, request = serving_store
    service = store.create(request, "drain-create")
    store.begin_drain()
    with pytest.raises(IllegalOperationError, match="draining"):
        store.create(
            request.model_copy(update={"name": "late"}), "late-create"
        )
    assert not store.cleanup_ready()
    with pytest.raises(IllegalOperationError):
        store.reopen_admission()
    lease = store.claim()
    assert (
        lease.service.id == service.id
        and lease.service.operation.action == "delete"
    )
    lease.service.state = "deleted"
    lease.service.operation.status = "succeeded"
    store.finish(lease, lease.service, {})
    assert store.cleanup_ready()
    store.reopen_admission()
    assert not store.cleanup_ready()
    store.create(request.model_copy(update={"name": "reopened"}), "reopened")


def test_retry_preserves_unknown_submission_instead_of_resubmitting(
    serving_store,
):
    """Explicit retries observe the original phase instead of allocating blindly."""
    store, request = serving_store
    service = store.create(request, "unknown-create")
    lease = store.claim()
    store.checkpoint(lease, ManagedModelCheckpoint(phase="submitting"))
    lease.service.operation.status = "uncertain"
    store.finish(lease, lease.service, {})
    store.mutate(
        service.id,
        ManagedModelMutation(action="retry", expected_generation=1),
        "retry-unknown",
    )
    retry = store.claim()
    assert retry.checkpoint.phase == "submitting"
    assert retry.service.operation.action == "create"
    assert retry.target_revision_id == lease.target_revision_id


def test_absence_confirmation_requires_exact_uncertain_submission(
    serving_store,
):
    """Only an explicit investigated generation can clear the no-resubmit fence."""
    store, request = serving_store
    service = store.create(request, "manual-recovery")
    lease = store.claim()
    with pytest.raises(IllegalOperationError):
        store.confirm_submission_absent(
            service.id, 1, "Fixture evidence of absence"
        )
    store.checkpoint(lease, ManagedModelCheckpoint(phase="submitting"))
    lease.service.operation.status = "uncertain"
    store.finish(lease, lease.service, {})
    with pytest.raises(IllegalOperationError):
        store.confirm_submission_absent(
            service.id, 2, "Fixture evidence of absence"
        )
    store.confirm_submission_absent(
        service.id, 1, "Fixture evidence of absence"
    )
    resumed = store.claim()
    assert resumed.checkpoint.phase == "verified-absent"
    assert resumed.checkpoint.error == "Fixture evidence of absence"
    assert "Fixture evidence" not in store.get(service.id).model_dump_json()


def test_inference_keys_are_private_scoped_rotatable_and_revocable(
    serving_store,
):
    """Keys grant inference for one service and are recoverable only from secrets."""
    import hashlib

    from sqlmodel import Session

    store, request = serving_store
    service = store.create(request, "key-test")
    other = store.create(
        request.model_copy(update={"name": "other"}), "other-key-test"
    )
    with pytest.raises(PermissionError):
        store.get_inference_target(service.id, "zenml-access-token")
    keys, values = _credential_store(store)
    reference = keys.rotate(service.id, request.project_id)
    key = values[reference.id]["api_key"]
    with Session(store.engine) as session:
        row = session.get(ManagedModelServiceSchema, service.id)
        assert (
            row.inference_key_hash == hashlib.sha256(key.encode()).hexdigest()
        )
        assert key not in row.document
        assert "inference_key" not in row.to_model().model_dump_json()
    with pytest.raises(PermissionError):
        store.get_inference_target(other.id, key)
    # A correct key passes authentication but cannot invoke an unready service.
    with pytest.raises(IllegalOperationError, match="admission is closed"):
        store.get_inference_target(service.id, key)
    reference = keys.rotate(service.id, request.project_id)
    replacement = values[reference.id]["api_key"]
    assert replacement != key
    with pytest.raises(PermissionError):
        store.get_inference_target(service.id, key)
    with pytest.raises(IllegalOperationError, match="admission is closed"):
        store.get_inference_target(service.id, replacement)
    keys.revoke(service.id)
    with pytest.raises(PermissionError):
        store.get_inference_target(service.id, replacement)
    store.mutate(
        service.id,
        ManagedModelMutation(action="delete", expected_generation=1),
        "delete-key-test",
    )
    with pytest.raises(IllegalOperationError, match="deleted service"):
        keys.rotate(service.id, request.project_id)


def _credential_store(store):
    values = {}
    backend = SimpleNamespace(
        engine=store.engine,
        _set_secret_values=lambda identity, data: values.update(
            {identity: data}
        ),
        _delete_secret_values=lambda identity: values.pop(identity, None),
    )
    return ManagedInferenceKeysStore(backend), values


def test_initial_secret_replay_failure_and_revocation(serving_store):
    """A failed write is recoverable and creation retries never resurrect revoked keys."""
    store, request = serving_store
    service = store.create(request, "initial-key", wait_for_inference_key=True)
    assert store.claim() is None
    keys, values = _credential_store(store)
    original_write = keys.store._set_secret_values
    keys.store._set_secret_values = lambda *args: (_ for _ in ()).throw(
        OSError("storage unavailable")
    )
    with pytest.raises(RuntimeError, match="Unable to store"):
        keys.ensure(service.id, request.project_id)
    assert store.get(service.id).inference_secret is None
    assert store.claim() is None
    keys.store._set_secret_values = original_write
    keys.ensure(service.id, request.project_id)
    reference = store.get(service.id).inference_secret
    assert reference is not None
    assert values[reference.id]["api_key"].startswith("zmm_")
    keys.ensure(service.id, request.project_id)
    assert store.get(service.id).inference_secret == reference
    assert len(values) == 1
    assert store.claim() is not None
    keys.revoke(service.id)
    keys.ensure(service.id, request.project_id)
    assert store.get(service.id).inference_secret is None


def test_failed_rotation_preserves_key_and_late_write_cannot_undo_revocation(
    serving_store,
):
    """External storage completion never overrides newer credential intent."""
    store, request = serving_store
    service = store.create(request, "rotation")
    keys, values = _credential_store(store)
    active = keys.rotate(service.id, request.project_id)
    original_write = keys.store._set_secret_values

    def fail(identity, data):
        original_write(identity, data)
        raise OSError("response lost after storage")

    keys.store._set_secret_values = fail
    with pytest.raises(RuntimeError, match="Unable to store"):
        keys.rotate(service.id, request.project_id)
    assert store.get(service.id).inference_secret == active
    with pytest.raises(IllegalOperationError, match="admission is closed"):
        store.get_inference_target(service.id, values[active.id]["api_key"])

    def revoke_during_write(identity, data):
        keys.revoke(service.id)
        original_write(identity, data)

    keys.store._set_secret_values = revoke_during_write
    with pytest.raises(IllegalOperationError, match="credentials changed"):
        keys.rotate(service.id, request.project_id)
    assert store.get(service.id).inference_secret is None
    for data in values.values():
        with pytest.raises(PermissionError):
            store.get_inference_target(service.id, data["api_key"])


def test_secret_cleanup_includes_failed_attempts_and_can_retry(serving_store):
    """Cleanup uses owned IDs, keeps its journal on failure, and removes secret metadata."""
    from sqlmodel import Session, select

    store, request = serving_store
    service = store.create(request, "cleanup")
    keys, values = _credential_store(store)
    keys.rotate(service.id, request.project_id)
    keys.rotate(service.id, request.project_id)
    with pytest.raises(IllegalOperationError):
        keys.cleanup(service.id)
    store.mutate(
        service.id,
        ManagedModelMutation(action="delete", expected_generation=1),
        "delete",
    )
    lease = store.claim()
    lease.service.state = "deleted"
    lease.service.operation.status = "succeeded"
    store.finish(lease, lease.service, {})
    original_delete = keys.store._delete_secret_values
    keys.store._delete_secret_values = lambda identity: (_ for _ in ()).throw(
        OSError("unavailable")
    )
    with pytest.raises(OSError):
        keys.cleanup(service.id)
    keys.store._delete_secret_values = original_delete
    keys.cleanup(service.id)
    keys.cleanup(service.id)
    assert not values
    with Session(store.engine) as session:
        assert not session.exec(select(SecretSchema)).all()


def test_newer_rotation_wins_and_late_deleted_key_is_cleaned(serving_store):
    """Late writes cannot replace newer keys or leak a credential after deletion."""
    store, request = serving_store
    service = store.create(request, "concurrent-keys")
    keys, values = _credential_store(store)
    original_write = keys.store._set_secret_values
    winner = []

    def concurrent_rotation(identity, data):
        keys.store._set_secret_values = original_write
        winner.append(keys.rotate(service.id, request.project_id))
        original_write(identity, data)

    keys.store._set_secret_values = concurrent_rotation
    with pytest.raises(IllegalOperationError, match="credentials changed"):
        keys.rotate(service.id, request.project_id)
    assert store.get(service.id).inference_secret == winner[0]
    assert set(values) == {winner[0].id}

    def deletion_during_write(identity, data):
        store.mutate(
            service.id,
            ManagedModelMutation(action="delete", expected_generation=1),
            "delete-race",
        )
        keys.cleanup(service.id)
        original_write(identity, data)

    keys.store._set_secret_values = deletion_during_write
    with pytest.raises(IllegalOperationError, match="credentials changed"):
        keys.rotate(service.id, request.project_id)
    assert not values
    assert store.get(service.id).inference_secret is None
