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
"""Public history-reader scenarios on retained execution identities."""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, Literal
from uuid import UUID, uuid4

import pytest
from sqlmodel import select

from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source
from zenml.config.step_configurations import (
    InputSpec,
    Step,
    StepConfiguration,
    StepSpec,
)
from zenml.enums import (
    ArchiveBundleStatus,
    ExecutionStatus,
    StepRunInputArtifactType,
    StepType,
)
from zenml.models import (
    HookInvocationFilter,
    PipelineRunFilter,
    PipelineRunRequest,
    PipelineSnapshotFilter,
    ProjectFilter,
    RunWaitConditionFilter,
    StepRunFilter,
    StepRunRequest,
)
from zenml.orchestrators.cache_utils import get_cached_step_run
from zenml.utils.time_utils import utc_now
from zenml.zen_stores.schemas import (
    ArchiveBundleSchema,
    ArtifactSchema,
    ArtifactVersionSchema,
    HookInvocationSchema,
    PipelineRunSchema,
    PipelineSchema,
    PipelineSnapshotSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    RunWaitConditionSchema,
    StepConfigurationSchema,
    StepRunInputArtifactSchema,
    StepRunOutputArtifactSchema,
    StepRunParentsSchema,
    StepRunSchema,
)
from zenml.zen_stores.sql_zen_store import (
    Session,
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@dataclass(frozen=True)
class ExecutionTree:
    """IDs for a producer, consumer, and their retained artifact links."""

    project: UUID
    run: UUID
    snapshot: UUID
    producer: UUID
    consumer: UUID
    input_artifact: UUID
    output_artifact: UUID


@pytest.fixture
def sql_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SqlZenStore]:
    """Create a SQLite store without redirecting the editable install.

    Args:
        tmp_path: Isolated test directory.
        monkeypatch: Environment isolation fixture.

    Yields:
        A fresh migrated store.
    """
    directory = tmp_path / "config"
    directory.mkdir()
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(directory))
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(url=f"sqlite:///{directory / 'db'}"),
        skip_default_registrations=False,
    )
    yield store
    store.engine.dispose()


def create_tree(
    store: SqlZenStore,
    layout: Literal["static", "dynamic", "legacy"] = "static",
) -> ExecutionTree:
    """Create valid hot definitions and a realized two-step graph.

    Args:
        store: Isolated SQL store.
        layout: Definition ownership to exercise.

    Returns:
        The execution and artifact identifiers.
    """
    project = store.list_projects(ProjectFilter()).items[0].id
    configuration = PipelineConfiguration(
        name="retention", substitutions={"project_label": "retained"}
    )
    producer_config = StepConfiguration(
        name="producer", step_type=StepType.TOOL_CALL
    )
    consumer_config = StepConfiguration(
        name="consumer",
        step_type=StepType.LLM_CALL,
        substitutions={"step_label": "kept"},
    )
    producer = Step(
        spec=StepSpec(
            source="tests.producer",
            upstream_steps=[],
            invocation_id="producer",
        ),
        config=producer_config,
        step_config_overrides=producer_config,
    )
    consumer = Step(
        spec=StepSpec(
            source="tests.consumer",
            upstream_steps=["producer"],
            invocation_id="consumer",
            inputs={
                "item": InputSpec(step_name="producer", output_name="out")
            },
        ),
        config=consumer_config,
        step_config_overrides=consumer_config,
    )
    now = utc_now()
    pipeline = PipelineSchema(
        project_id=project, name=f"pipeline-{uuid4()}", run_count=1
    )
    snapshot = PipelineSnapshotSchema(
        project_id=project,
        pipeline_id=pipeline.id,
        pipeline_configuration=configuration.model_dump_json(),
        pipeline_spec=PipelineSpec(
            steps=[producer.spec, consumer.spec]
        ).model_dump_json(),
        client_environment='{"python": "3.11"}',
        run_name_template="history",
        client_version="0.96.3",
        server_version="0.96.3",
        step_count=2,
        is_dynamic=layout == "dynamic",
    )
    run = PipelineRunSchema(
        project_id=project,
        pipeline_id=pipeline.id,
        snapshot_id=None if layout == "legacy" else snapshot.id,
        name=f"run-{uuid4()}",
        index=1,
        status=ExecutionStatus.COMPLETED.value,
        in_progress=False,
        enable_heartbeat=False,
        start_time=now,
        end_time=now,
        orchestrator_environment='{"orchestrator": "local"}',
        pipeline_configuration=configuration.model_dump_json()
        if layout == "legacy"
        else None,
        client_environment='{"python": "3.11"}'
        if layout == "legacy"
        else None,
    )
    steps = [
        StepRunSchema(
            project_id=project,
            pipeline_run_id=run.id,
            snapshot_id=None if layout == "legacy" else snapshot.id,
            name=definition.config.name,
            status=ExecutionStatus.COMPLETED.value,
            version=1,
            is_retriable=False,
            start_time=now,
            end_time=now,
            source_code=f"def {definition.config.name}(): return 7",
            docstring=f"Documentation for {definition.config.name}.",
            code_hash="code-hash",
            cache_key=f"cache-{run.id}-{definition.config.name}",
            step_configuration=definition.model_dump_json()
            if layout == "legacy"
            else None,
        )
        for definition in (producer, consumer)
    ]
    artifact = ArtifactSchema(
        project_id=project, name=f"artifact-{uuid4()}", has_custom_name=False
    )
    versions = [
        ArtifactVersionSchema(
            project_id=project,
            artifact_id=artifact.id,
            version=str(index),
            version_number=index,
            type="DataArtifact",
            uri=f"s3://retained/{index}",
            save_type="step_output",
            materializer=Source.from_import_path(
                "zenml.materializers.BuiltInMaterializer"
            ).model_dump_json(),
            data_type=Source.from_import_path(
                "builtins.int"
            ).model_dump_json(),
        )
        for index in (1, 2)
    ]
    with Session(store.engine) as session:
        session.add_all([pipeline, snapshot, run, artifact, *steps, *versions])
        session.flush()
        if layout != "legacy":
            session.add_all(
                [
                    StepConfigurationSchema(
                        index=index,
                        name=definition.config.name,
                        config=definition.model_dump_json(),
                        snapshot_id=snapshot.id
                        if layout == "static"
                        else None,
                        step_run_id=step.id if layout == "dynamic" else None,
                    )
                    for index, (step, definition) in enumerate(
                        zip(steps, (producer, consumer))
                    )
                ]
            )
        metadata = RunMetadataSchema(
            project_id=project,
            key="score",
            value="7",
            type="int",
            publisher_step_id=steps[1].id,
        )
        session.add(metadata)
        session.flush()
        session.add_all(
            [
                StepRunParentsSchema(
                    parent_id=steps[0].id, child_id=steps[1].id
                ),
                StepRunOutputArtifactSchema(
                    step_id=steps[0].id, artifact_id=versions[0].id, name="out"
                ),
                StepRunInputArtifactSchema(
                    step_id=steps[1].id,
                    artifact_id=versions[0].id,
                    name="item",
                    type=StepRunInputArtifactType.STEP_OUTPUT.value,
                    input_index=0,
                    chunk_index=1,
                    chunk_size=2,
                ),
                StepRunOutputArtifactSchema(
                    step_id=steps[1].id,
                    artifact_id=versions[1].id,
                    name="result",
                ),
                RunMetadataResourceSchema(
                    resource_id=steps[1].id,
                    resource_type="step_run",
                    run_metadata_id=metadata.id,
                ),
                RunMetadataResourceSchema(
                    resource_id=run.id,
                    resource_type="pipeline_run",
                    run_metadata_id=metadata.id,
                ),
            ]
        )
        result = ExecutionTree(
            project,
            run.id,
            snapshot.id,
            steps[0].id,
            steps[1].id,
            versions[0].id,
            versions[1].id,
        )
        session.commit()
    return result


def archive_tree(
    store: SqlZenStore,
    tree: ExecutionTree,
    marker: Literal["both", "timestamp", "bundle"] = "both",
) -> UUID:
    """Set synthetic archived rows after capturing their real projections.

    This is reader coverage, not compactor acceptance: no object is exported.

    Args:
        store: Isolated SQL store.
        tree: Execution to mark.
        marker: Also test incomplete marker pairs fail closed before decoding.

    Returns:
        The synthetic catalog identifier.
    """
    with Session(store.engine) as session:
        bundle = ArchiveBundleSchema(
            project_id=tree.project,
            root_run_id=tree.run,
            uri="s3://archive/reader-fixture",
            size_bytes=1,
            row_counts="{}",
            manifest_hash="sha256:reader-fixture",
            format_version=1,
            schema_revision="7a1c3d9e2b4f",
            status=ArchiveBundleStatus.COMPLETE.value,
        )
        session.add(bundle)
        rows: list[
            StepRunSchema | PipelineRunSchema | PipelineSnapshotSchema
        ] = []
        for step_id in (tree.producer, tree.consumer):
            step = session.get(StepRunSchema, step_id)
            assert step is not None
            config = step.get_step_configuration().config
            step.step_type = (
                config.step_type.value if config.step_type else None
            )
            step.substitutions = json.dumps(config.substitutions)
            step.step_configuration = "{}"
            step.exception_info = "{}"
            rows.append(step)
        snapshot = session.get(PipelineSnapshotSchema, tree.snapshot)
        run = session.get(PipelineRunSchema, tree.run)
        assert snapshot is not None and run is not None
        snapshot.pipeline_configuration = "{}"
        snapshot.client_environment = "{}"
        snapshot.pipeline_spec = "{}"
        snapshot.source_code = None
        snapshot.description = None
        run.pipeline_configuration = "{}"
        run.client_environment = "{}"
        run.orchestrator_environment = "{}"
        run.exception_info = "{}"
        rows.extend([snapshot, run])
        for row in rows:
            row.archived_at = utc_now() if marker != "bundle" else None
            row.archive_bundle_id = (
                bundle.id if marker != "timestamp" else None
            )
        for config_row in session.exec(select(StepConfigurationSchema)).all():
            if (
                config_row.snapshot_id == tree.snapshot
                or config_row.step_run_id in (tree.producer, tree.consumer)
            ):
                config_row.config = "{}"
        bundle_id = bundle.id
        session.commit()
    return bundle_id


@pytest.mark.parametrize("hydrate", [False, True])
def test_archived_step_lists_preserve_real_body_and_resources(
    sql_store: SqlZenStore, hydrate: bool
) -> None:
    """Hydrated and unhydrated lists survive cleared detail.

    Args:
        sql_store: Isolated SQL store.
        hydrate: Whether metadata is requested.
    """
    tree = create_tree(sql_store)
    before = sql_store.get_run_step(tree.consumer)
    bundle = archive_tree(sql_store, tree)
    page = sql_store.list_run_steps(
        StepRunFilter(pipeline_run_id=tree.run), hydrate=hydrate
    )
    assert page.total == 2
    result = next(step for step in page.items if step.id == tree.consumer)
    assert result.body is not None
    assert result.type == before.type == StepType.LLM_CALL
    assert result.substitutions == before.substitutions
    assert result.archive_bundle_id == bundle
    assert result.inputs["item"][0].id == tree.input_artifact
    assert result.outputs["result"][0].id == tree.output_artifact
    if hydrate:
        assert result.metadata is not None
        assert result.metadata.config is None and result.metadata.spec is None
        assert result.metadata.exception_info is None
        assert result.source_code == before.source_code
        assert result.docstring == before.docstring
        assert result.cache_key == before.cache_key
        assert result.original_step_run_id is None
    else:
        assert result.metadata is None


@pytest.mark.parametrize("layout", ["static", "dynamic", "legacy"])
@pytest.mark.parametrize("marker", ["both", "timestamp", "bundle"])
def test_archived_details_do_not_decode_any_configuration(
    sql_store: SqlZenStore,
    layout: Literal["static", "dynamic", "legacy"],
    marker: Literal["both", "timestamp", "bundle"],
) -> None:
    """Either marker protects current and legacy cleared JSON paths.

    Args:
        sql_store: Isolated SQL store.
        layout: Definition ownership to exercise.
        marker: Stored marker shape.
    """
    tree = create_tree(sql_store, layout)
    archive_tree(sql_store, tree, marker)
    run = sql_store.get_run(tree.run)
    step = sql_store.get_run_step(tree.consumer)
    snapshot = sql_store.get_snapshot(tree.snapshot)
    assert run.metadata is not None and run.metadata.config is None
    assert run.metadata.client_environment is None
    assert run.metadata.orchestrator_environment is None
    assert run.metadata.exception_info is None
    assert run.run_metadata == {"score": 7}
    assert step.metadata is not None and step.metadata.config is None
    assert step.metadata.spec is None and step.source_code is not None
    assert snapshot.metadata is not None
    assert snapshot.metadata.pipeline_configuration is None
    assert snapshot.metadata.pipeline_spec is None
    assert snapshot.metadata.step_configurations is None
    assert snapshot.metadata.config_template is None
    assert snapshot.metadata.config_schema is None
    assert snapshot.runnable is False and snapshot.deployable is False


@pytest.mark.parametrize("layout", ["static", "dynamic", "legacy"])
def test_archived_dag_uses_real_steps_parents_and_artifacts(
    sql_store: SqlZenStore,
    layout: Literal["static", "dynamic", "legacy"],
) -> None:
    """The realized DAG remains readable without static or dynamic text.

    Args:
        sql_store: Isolated SQL store.
        layout: Ownership of the now-archived configurations.
    """
    tree = create_tree(sql_store, layout)
    archive_tree(sql_store, tree)
    dag = sql_store.get_pipeline_run_dag(
        tree.run, include_step_metadata=["score"]
    )
    steps = {node.name: node for node in dag.nodes if node.type == "step"}
    assert set(steps) == {"producer", "consumer"}
    assert steps["consumer"].id == tree.consumer
    assert steps["consumer"].metadata["type"] == StepType.LLM_CALL.value
    assert steps["consumer"].metadata["run_metadata"] == {"score": 7}
    edges = {(edge.source, edge.target) for edge in dag.edges}
    assert (steps["producer"].node_id, steps["consumer"].node_id) in edges
    input_nodes = [
        node for node in dag.nodes if node.id == tree.input_artifact
    ]
    assert len(input_nodes) == 1
    assert (steps["producer"].node_id, input_nodes[0].node_id) in edges
    assert (input_nodes[0].node_id, steps["consumer"].node_id) in edges


def test_missing_archived_projection_is_not_fabricated(
    sql_store: SqlZenStore,
) -> None:
    """Missing projected values remain unknown rather than invented defaults.

    Args:
        sql_store: Isolated SQL store.
    """
    tree = create_tree(sql_store)
    archive_tree(sql_store, tree)
    with Session(sql_store.engine) as session:
        step = session.get(StepRunSchema, tree.consumer)
        assert step is not None
        step.step_type = None
        step.substitutions = None
        session.commit()
    response = sql_store.get_run_step(tree.consumer, hydrate=False)
    assert response.type is None
    assert response.body is not None and response.body.substitutions is None
    with pytest.raises(ValueError, match="(?i)restore"):
        _ = response.substitutions


@pytest.mark.parametrize(
    "alternate_status", [ExecutionStatus.COMPLETED, ExecutionStatus.RETRIED]
)
def test_archived_dag_disambiguates_parents_and_omits_retried_steps(
    sql_store: SqlZenStore,
    alternate_status: ExecutionStatus,
) -> None:
    """Shared output IDs do not invent an edge to one arbitrary producer.

    Args:
        sql_store: Isolated SQL store.
        alternate_status: Whether the second producer remains part of the DAG.
    """
    tree = create_tree(sql_store)
    bundle = archive_tree(sql_store, tree)
    with Session(sql_store.engine) as session:
        alternate = StepRunSchema(
            project_id=tree.project,
            pipeline_run_id=tree.run,
            snapshot_id=tree.snapshot,
            name="alternate",
            version=1,
            status=alternate_status.value,
            is_retriable=False,
            archived_at=utc_now(),
            archive_bundle_id=bundle,
            step_configuration="{}",
            substitutions="{}",
        )
        session.add(alternate)
        session.flush()
        session.add_all(
            [
                StepRunParentsSchema(
                    parent_id=alternate.id, child_id=tree.consumer
                ),
                StepRunOutputArtifactSchema(
                    step_id=alternate.id,
                    artifact_id=tree.input_artifact,
                    name="other_alias",
                ),
            ]
        )
        session.commit()
    dag = sql_store.get_pipeline_run_dag(tree.run)
    steps = {node.name: node for node in dag.nodes if node.type == "step"}
    inputs = [
        edge
        for edge in dag.edges
        if edge.target == steps["consumer"].node_id
        and edge.metadata.get("input_name") == "item"
    ]
    assert len(inputs) == 1
    nodes = [node for node in dag.nodes if node.id == tree.input_artifact]
    edges = {(edge.source, edge.target) for edge in dag.edges}
    if alternate_status == ExecutionStatus.RETRIED:
        assert "alternate" not in steps
        assert len(nodes) == 1
        assert (steps["producer"].node_id, inputs[0].source) in edges
    else:
        assert len(nodes) == 3
        assert (steps["producer"].node_id, inputs[0].source) not in edges
        assert (steps["alternate"].node_id, inputs[0].source) not in edges
        assert (steps["alternate"].node_id, steps["consumer"].node_id) in edges
        assert (steps["producer"].node_id, steps["consumer"].node_id) in edges


def test_archived_dag_keeps_wait_child_and_trigger_context(
    sql_store: SqlZenStore,
) -> None:
    """Retained context survives while the archived wait question disappears.

    Args:
        sql_store: Isolated SQL store.
    """
    tree = create_tree(sql_store)
    child = create_tree(sql_store)
    triggered = create_tree(sql_store)
    with Session(sql_store.engine) as session:
        child_run = session.get(PipelineRunSchema, child.run)
        triggered_run = session.get(PipelineRunSchema, triggered.run)
        assert child_run is not None and triggered_run is not None
        child_run.parent_run_id = tree.run
        child_run.root_run_id = tree.run
        triggered_run.triggered_by = tree.consumer
        triggered_run.triggered_by_type = "step_run"
        wait = RunWaitConditionSchema(
            run_id=tree.run,
            project_id=tree.project,
            name="approval",
            type="external_input",
            status="resolved",
            resolution="continue",
            question="Historical question",
            resolved_at=utc_now(),
        )
        session.add(wait)
        session.flush()
        wait_id = wait.id
        session.commit()
    before = sql_store.get_pipeline_run_dag(tree.run)
    before_nodes = {
        node.id: node for node in before.nodes if node.id is not None
    }
    assert before_nodes[wait_id].metadata["question"] == "Historical question"
    archive_tree(sql_store, tree)
    after = sql_store.get_pipeline_run_dag(tree.run)
    after_nodes = {
        node.id: node for node in after.nodes if node.id is not None
    }
    for run_id in (child.run, triggered.run):
        assert (
            after_nodes[run_id].model_dump()
            == before_nodes[run_id].model_dump()
        )
    expected_wait = before_nodes[wait_id].metadata.copy()
    expected_wait.pop("question")
    assert after_nodes[wait_id].metadata == expected_wait
    assert (
        after_nodes[tree.consumer].node_id,
        after_nodes[triggered.run].node_id,
    ) in {(edge.source, edge.target) for edge in after.edges}


def test_related_snapshot_marker_protects_unmarked_run_and_steps(
    sql_store: SqlZenStore,
) -> None:
    """Related archived configurations are never parsed through a hot marker.

    Args:
        sql_store: Isolated SQL store.
    """
    tree = create_tree(sql_store)
    archive_tree(sql_store, tree)
    with Session(sql_store.engine) as session:
        run = session.get(PipelineRunSchema, tree.run)
        assert run is not None
        run.archived_at = None
        run.archive_bundle_id = None
        for step_id in (tree.producer, tree.consumer):
            step = session.get(StepRunSchema, step_id)
            assert step is not None
            step.archived_at = None
            step.archive_bundle_id = None
        session.commit()
    run_response = sql_store.get_run(tree.run)
    step_response = sql_store.get_run_step(tree.consumer)
    assert (
        run_response.metadata is not None
        and run_response.metadata.config is None
    )
    assert (
        step_response.metadata is not None
        and step_response.metadata.config is None
    )
    assert step_response.type == StepType.LLM_CALL
    assert {
        node.id for node in sql_store.get_pipeline_run_dag(tree.run).nodes
    } >= {
        tree.producer,
        tree.consumer,
    }


@pytest.mark.parametrize("marker", ["timestamp", "bundle"])
def test_wait_and_hook_readers_omit_only_archived_detail(
    sql_store: SqlZenStore,
    marker: Literal["timestamp", "bundle"],
) -> None:
    """Public child-resource reads guard malformed archived JSON.

    Args:
        sql_store: Isolated SQL store.
        marker: Either owning-run marker must protect the detail.
    """
    tree = create_tree(sql_store)
    now = utc_now()
    with Session(sql_store.engine) as session:
        wait = RunWaitConditionSchema(
            run_id=tree.run,
            project_id=tree.project,
            name="approval",
            type="external_input",
            status="resolved",
            resolution="continue",
            question="Historical question",
            data_schema_json='{"type":"integer"}',
            result_json="7",
            resolved_at=now,
            last_polled_at=now,
            poller_instance_id="old-poller",
            poller_lease_expires_at=now,
        )
        hook = HookInvocationSchema(
            project_id=tree.project,
            pipeline_run_id=tree.run,
            step_run_id=tree.consumer,
            hook_type="custom",
            name="retained-hook",
            status=ExecutionStatus.COMPLETED.value,
            start_time=now,
            end_time=now,
            source="tests.retained_hook",
            exception_info='{"traceback":"history"}',
        )
        session.add_all([wait, hook])
        session.flush()
        wait_id, hook_id = wait.id, hook.id
        session.commit()
    hot_wait = sql_store.get_run_wait_condition(wait_id)
    hot_hook = sql_store.get_hook_invocation(hook_id)
    assert hot_wait.question == "Historical question"
    assert hot_wait.data_schema == {"type": "integer"} and hot_wait.result == 7
    assert hot_wait.poller_instance_id == "old-poller"
    assert hot_hook.exception_info is not None
    assert hot_hook.exception_info.traceback == "history"
    archive_tree(sql_store, tree, marker)
    with Session(sql_store.engine) as session:
        wait_row = session.get(RunWaitConditionSchema, wait_id)
        hook_row = session.get(HookInvocationSchema, hook_id)
        assert wait_row is not None and hook_row is not None
        wait_row.data_schema_json = "{unrestored"
        wait_row.result_json = "{unrestored"
        hook_row.exception_info = "{unrestored"
        session.commit()
    waits = [
        sql_store.get_run_wait_condition(wait_id),
        *sql_store.list_run_wait_conditions(
            RunWaitConditionFilter(pipeline_run=tree.run), hydrate=True
        ).items,
    ]
    hooks = [
        sql_store.get_hook_invocation(hook_id),
        *sql_store.list_hook_invocations(
            HookInvocationFilter(pipeline_run_id=tree.run), hydrate=True
        ).items,
    ]
    assert len(waits) == len(hooks) == 2
    for response in waits:
        assert (
            response.id == wait_id
            and response.resolution == hot_wait.resolution
        )
        assert (
            response.status == hot_wait.status and response.resolved_at == now
        )
        assert response.question is None and response.data_schema is None
        assert response.result is None and response.poller_instance_id is None
        assert (
            response.last_polled_at is None
            and response.poller_lease_expires_at is None
        )
    for invocation in hooks:
        assert (
            invocation.id == hook_id and invocation.status == hot_hook.status
        )
        assert invocation.source == hot_hook.source == "tests.retained_hook"
        assert invocation.exception_info is None


def test_new_run_from_archived_snapshot_requires_restore(
    sql_store: SqlZenStore,
) -> None:
    """Execution refuses archived snapshots before parsing poisoned text.

    Args:
        sql_store: Isolated SQL store.
    """
    tree = create_tree(sql_store)
    archive_tree(sql_store, tree)
    with pytest.raises(ValueError, match="zenml pipeline runs restore"):
        sql_store.get_or_create_run(
            PipelineRunRequest(
                project=tree.project,
                snapshot=tree.snapshot,
                name="refused",
                status=ExecutionStatus.INITIALIZING,
            )
        )
    assert sql_store.list_runs(PipelineRunFilter(name="refused")).total == 0


@pytest.mark.parametrize("archived", [False, True])
@pytest.mark.parametrize(
    "status", [ExecutionStatus.CACHED, ExecutionStatus.SKIPPED]
)
def test_cached_and_skipped_creation_copy_hot_and_archived_history(
    sql_store: SqlZenStore,
    monkeypatch: pytest.MonkeyPatch,
    archived: bool,
    status: ExecutionStatus,
) -> None:
    """The cached/skipped copy contract retains inputs, outputs and metadata.

    This covers store-level copying, not the public pipeline replay operation,
    which requires restored execution configuration.

    Args:
        sql_store: Isolated SQL store.
        monkeypatch: Bind the real Client API to the isolated SQL store.
        archived: Whether the selected original has archived detail.
        status: Cache or replay creation status.
    """
    original = create_tree(sql_store)
    before = sql_store.get_run_step(original.consumer)
    destination = create_tree(sql_store, "dynamic")
    if archived:
        archive_tree(sql_store, original)
    project = sql_store.get_project(original.project)
    monkeypatch.setattr(Client, "zen_store", property(lambda self: sql_store))
    monkeypatch.setattr(
        Client, "active_project", property(lambda self: project)
    )
    assert before.cache_key is not None
    selected = get_cached_step_run(before.cache_key)
    assert selected is not None and selected.id == original.consumer
    assert selected.source_code == before.source_code
    assert selected.docstring == before.docstring
    reused_config = StepConfiguration(name="reused")
    result = sql_store.create_run_step(
        StepRunRequest(
            project=original.project,
            name="reused",
            pipeline_run_id=destination.run,
            original_step_run_id=selected.id,
            status=status,
            start_time=utc_now(),
            end_time=utc_now(),
            source_code=selected.source_code,
            docstring=selected.docstring,
            code_hash=selected.code_hash,
            cache_key=selected.cache_key,
            cache_expires_at=selected.cache_expires_at,
            inputs={
                "item": [artifact.id for artifact in selected.inputs["item"]]
            },
            outputs={
                "result": [
                    artifact.id for artifact in selected.outputs["result"]
                ]
            },
            dynamic_config=Step(
                spec=StepSpec(
                    source="tests.reused",
                    upstream_steps=[],
                    invocation_id="reused",
                ),
                config=reused_config,
                step_config_overrides=reused_config,
            ),
        )
    )
    assert result.status == status
    assert result.original_step_run_id == original.consumer
    assert (
        result.source_code == before.source_code
        and result.docstring == before.docstring
    )
    assert result.outputs["result"][0].id == original.output_artifact
    assert result.inputs["item"][0].id == original.input_artifact
    assert result.inputs["item"][0].chunk_index == 1
    assert result.inputs["item"][0].chunk_size == 2
    assert result.run_metadata == {"score": 7}


def test_mixed_history_lists_keep_hot_detail_and_archived_metadata(
    sql_store: SqlZenStore,
) -> None:
    """Lists include both histories and only real retained metadata.

    Args:
        sql_store: Isolated SQL store.
    """
    hot = create_tree(sql_store)
    cold = create_tree(sql_store)
    archive_tree(sql_store, cold)
    runs = {
        run.id: run
        for run in sql_store.list_runs(PipelineRunFilter(), hydrate=True).items
    }
    hot_metadata = runs[hot.run].metadata
    cold_metadata = runs[cold.run].metadata
    assert hot_metadata is not None and hot_metadata.config is not None
    assert cold_metadata is not None and cold_metadata.config is None
    assert runs[cold.run].run_metadata == {"score": 7}
    snapshots = sql_store.list_snapshots(
        PipelineSnapshotFilter(), hydrate=True
    )
    assert {snapshot.id for snapshot in snapshots.items} == {
        hot.snapshot,
        cold.snapshot,
    }
