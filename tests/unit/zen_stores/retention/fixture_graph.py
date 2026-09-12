# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Two-step execution with payloads and retained dependency/artifact links."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlmodel import SQLModel

from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ExecutionStatus
from zenml.models import StepRunRequest
from zenml.zen_stores import schemas as s


def dynamic_step(ids, name: str, now: datetime) -> StepRunRequest:
    """Build a completed step with a distinct definition."""
    return StepRunRequest(
        project=ids.project,
        name=name,
        pipeline_run_id=ids.run,
        start_time=now,
        end_time=now,
        status=ExecutionStatus.COMPLETED,
        dynamic_config=Step(
            spec=StepSpec(
                source=Source(module="tests", type=SourceType.INTERNAL),
                upstream_steps=[],
            ),
            config=StepConfiguration(name=name),
        ),
    )


def graph_rows(project_id: UUID, when: datetime, kind: str) -> dict:
    """Build independent SQL inputs for static, dynamic, and legacy variants."""
    shared = dict(project_id=project_id, created=when, updated=when)
    pipeline = s.PipelineSchema(name=str(uuid4()), run_count=1, **shared)
    snapshot = s.PipelineSnapshotSchema(
        pipeline_id=pipeline.id,
        pipeline_configuration='{"name":"example"}',
        client_environment='{"python":"test"}',
        source_code="def pipeline(): pass",
        description="Preserve Unicode: é😀",
        step_count=2,
        run_name_template="example",
        is_dynamic=kind == "dynamic",
        **shared,
    )
    run = s.PipelineRunSchema(
        name=str(uuid4()),
        pipeline_id=pipeline.id,
        snapshot_id=None if kind == "legacy" else snapshot.id,
        pipeline_configuration=snapshot.pipeline_configuration
        if kind == "legacy"
        else None,
        client_environment=snapshot.client_environment
        if kind == "legacy"
        else None,
        status="completed",
        in_progress=False,
        index=1,
        enable_heartbeat=False,
        start_time=when,
        end_time=when,
        orchestrator_environment='{"test":"environment"}',
        exception_info='{"traceback":"run failure"}',
        **shared,
    )
    records = [pipeline, snapshot, run]
    specs = []
    # Reverse primary-key order to exercise DAG ordering through dependencies.
    step_ids = sorted([uuid4(), uuid4()], reverse=True)
    for index, name in enumerate(("producer", "consumer")):
        definition = Step(
            spec=StepSpec(
                source=Source(
                    module="tests", attribute=name, type=SourceType.INTERNAL
                ),
                upstream_steps=["producer"] if index else [],
                inputs={
                    "item": {"step_name": "producer", "output_name": "out"}
                }
                if index
                else {},
            ),
            config=StepConfiguration(name=name, step_type="llm_call"),
        )
        specs.append(definition.spec)
        records.append(
            s.StepRunSchema(
                id=step_ids[index],
                name=name,
                cache_key=str(step_ids[index]),
                pipeline_run_id=run.id,
                snapshot_id=None if kind == "legacy" else snapshot.id,
                step_configuration=definition.model_dump_json()
                if kind == "legacy"
                else None,
                status="completed",
                version=1,
                is_retriable=False,
                start_time=when,
                end_time=when,
                source_code=f"def {name}(): pass",
                exception_info='{"traceback":"step failure"}',
                **shared,
            )
        )
        if kind != "legacy":
            records.append(
                s.StepConfigurationSchema(
                    name=name,
                    index=index,
                    snapshot_id=snapshot.id if kind == "static" else None,
                    step_run_id=step_ids[index] if kind == "dynamic" else None,
                    config=definition.model_dump_json(),
                    created=when,
                    updated=when,
                )
            )
    snapshot.pipeline_spec = PipelineSpec(steps=specs).model_dump_json()
    artifact = s.ArtifactSchema(
        name=str(uuid4()), has_custom_name=False, **shared
    )
    version = s.ArtifactVersionSchema(
        artifact_id=artifact.id,
        version="1",
        version_number=1,
        uri="test://output",
        type="DataArtifact",
        save_type="step_output",
        data_type=Source(
            module="builtins", attribute="int", type=SourceType.UNKNOWN
        ).model_dump_json(),
        materializer=Source(
            module="zenml.materializers",
            attribute="BuiltInMaterializer",
            type=SourceType.UNKNOWN,
        ).model_dump_json(),
        **shared,
    )
    records.extend(
        [
            artifact,
            version,
            s.StepRunParentsSchema(
                parent_id=step_ids[0], child_id=step_ids[1]
            ),
            s.StepRunOutputArtifactSchema(
                step_id=step_ids[0], artifact_id=version.id, name="out"
            ),
            s.StepRunInputArtifactSchema(
                step_id=step_ids[1],
                artifact_id=version.id,
                name="item",
                input_index=0,
                type="step_output",
            ),
        ]
    )
    rows = {}
    for record in records:
        rows.setdefault(record.__tablename__, []).append(record.model_dump())
    return rows


def insert_rows(store, rows: dict) -> None:
    """Insert fixture rows in foreign-key order."""
    with store.engine.begin() as connection:
        for table in SQLModel.metadata.sorted_tables:
            for values in rows.get(table.name, []):
                connection.execute(table.insert().values(**values))


def read_tables(store) -> dict:
    """Snapshot payloads and links independently of archive serialization."""
    names = (
        "pipeline_run",
        "step_run",
        "pipeline_snapshot",
        "step_configuration",
        "artifact",
        "artifact_version",
        "step_run_parents",
        "step_run_input_artifact",
        "step_run_output_artifact",
    )
    with store.engine.connect() as connection:
        return {
            name: [
                dict(row)
                for row in connection.execute(
                    select(table).order_by(*table.primary_key.columns)
                ).mappings()
            ]
            for name in names
            for table in [SQLModel.metadata.tables[name]]
        }
