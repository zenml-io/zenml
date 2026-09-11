# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Independent typed graphs and explicit version 1 fixture regeneration."""

import argparse
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlmodel import Session, SQLModel

from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import (
    InputSpec,
    Step,
    StepConfiguration,
    StepSpec,
)
from zenml.enums import (
    ExecutionStatus,
    StepRunInputArtifactType,
    StepType,
)
from zenml.models import ProjectFilter, RetentionSettings, StepRunRequest
from zenml.utils.json_utils import pydantic_encoder
from zenml.zen_stores import schemas
from zenml.zen_stores.retention.format import (
    ArchiveDocument,
    ConfigurationRecord,
    RunRecord,
    SnapshotRecord,
    StepRecord,
    canonical_json,
    encode,
)
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
)

FROZEN_NOW = datetime(2026, 1, 1)
GOLDEN_NOW = datetime(2026, 1, 1, 12)
GOLDEN_BUNDLE_ID = UUID(int=14)
DETAIL_TABLES = (
    "pipeline_run",
    "step_run",
    "pipeline_snapshot",
    "step_configuration",
)


def graph_rows(
    project_id: UUID, when: datetime, fixed: bool = False
) -> dict[str, list[dict[str, Any]]]:
    """Build independent typed rows, with fixed identities only for golden output.

    Args:
        project_id: Owning project.
        when: Execution and row timestamps.
        fixed: Use reproducible synthetic identities.

    Returns:
        Rows grouped by table, before configuration ownership is adjusted.
    """
    ids = {
        index: UUID(int=index) if fixed else uuid4() for index in range(2, 14)
    }
    # Exercise consumer-first primary-key order independently of insertion order.
    if not fixed:
        ids[5], ids[6] = sorted((ids[5], ids[6]), reverse=True)
    source: dict[str, list[dict[str, Any]]] = {}
    common = dict(
        project_id=project_id,
        pipeline_id=ids[2],
        snapshot_id=ids[3],
        pipeline_run_id=ids[4],
        created=when,
        updated=when,
        start_time=when,
        end_time=when,
        status=ExecutionStatus.COMPLETED,
    )

    def add(
        schema: type[SQLModel], identity: int | None = None, **values: Any
    ) -> None:
        """Append one schema-backed row with shared graph defaults.

        Args:
            schema: Typed SQL row schema.
            identity: Stable synthetic identity number, if the table has one.
            **values: Explicit graph edges and payloads.
        """
        fields = {
            key: value
            for key, value in common.items()
            if key in schema.model_fields
        }
        if identity is not None:
            fields["id"] = ids[identity]
        row = schema(**{**fields, **values})
        values = {name: None for name in row.__table__.columns.keys()}
        values.update(row.model_dump())
        source.setdefault(str(row.__tablename__), []).append(values)

    definitions = []
    for index, name in enumerate(("producer", "consumer")):
        config = StepConfiguration(
            name=name,
            step_type=StepType.TOOL_CALL if index == 0 else StepType.LLM_CALL,
        )
        spec = StepSpec(
            source=f"synthetic.{name}",
            invocation_id=name,
            upstream_steps=["producer"] if index else [],
            inputs={"item": InputSpec(step_name="producer", output_name="out")}
            if index
            else {},
        )
        definitions.append(
            Step(spec=spec, config=config, step_config_overrides=config)
        )
        add(
            schemas.StepRunSchema,
            5 + index,
            name=name,
            version=1,
            is_retriable=False,
            source_code=f"def {name}(): return 7",
            step_type=config.step_type,
            substitutions=json.dumps(
                {
                    "date": when.strftime("%Y_%m_%d"),
                    "time": when.strftime("%H_%M_%S_%f"),
                }
            ),
        )
        add(
            schemas.StepConfigurationSchema,
            10 + index,
            index=index,
            name=name,
            config=definitions[-1].model_dump_json(),
        )
        add(
            schemas.ArtifactVersionSchema,
            8 + index,
            artifact_id=ids[7],
            version=str(index + 1),
            version_number=index + 1,
            type="DataArtifact",
            uri=f"synthetic://golden/{index}",
            save_type="step_output",
            materializer=Source.from_import_path(
                "zenml.materializers.BuiltInMaterializer"
            ).model_dump_json(),
            data_type=Source.from_import_path(
                "builtins.int"
            ).model_dump_json(),
        )
        add(
            schemas.StepRunOutputArtifactSchema,
            step_id=ids[5 + index],
            artifact_id=ids[8 + index],
            name="out",
        )
    add(schemas.PipelineSchema, 2, name=str(ids[2]), run_count=1)
    add(
        schemas.PipelineSnapshotSchema,
        3,
        run_name_template="golden",
        step_count=2,
        is_dynamic=False,
        pipeline_configuration=PipelineConfiguration(
            name="golden"
        ).model_dump_json(),
        pipeline_spec=PipelineSpec(
            steps=[step.spec for step in definitions]
        ).model_dump_json(),
        client_environment='{"python":"synthetic"}',
        source_code="def pipeline(): pass",
    )
    add(
        schemas.PipelineRunSchema,
        4,
        name=str(ids[4]),
        index=1,
        in_progress=False,
        enable_heartbeat=False,
        orchestrator_environment='{"fixture":"v1"}',
        exception_info='{"traceback":"synthetic"}',
    )
    add(schemas.ArtifactSchema, 7, name=str(ids[7]), has_custom_name=False)
    add(
        schemas.HookInvocationSchema,
        12,
        hook_type="run_success",
        exception_info='{"message":"synthetic","traceback":"golden"}',
    )
    add(
        schemas.RunWaitConditionSchema,
        13,
        run_id=ids[4],
        name="golden-wait",
        type="external_input",
        status="resolved",
        resolution="continue",
        question="Preserve Unicode: é😀?",
        result_json='{"answer":true}',
    )
    add(schemas.StepRunParentsSchema, parent_id=ids[5], child_id=ids[6])
    add(
        schemas.StepRunInputArtifactSchema,
        step_id=ids[6],
        artifact_id=ids[8],
        name="item",
        type=StepRunInputArtifactType.STEP_OUTPUT,
        input_index=0,
    )
    return source


def dynamic_step(ids: Any, name: str, now: datetime) -> StepRunRequest:
    """Build a finished dynamic step for an existing run.

    Args:
        ids: Run identities.
        name: Step name.
        now: Step timestamps.

    Returns:
        The step request.
    """
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


def insert_rows(
    store: SqlZenStore, rows: dict[str, list[dict[str, Any]]]
) -> None:
    """Insert independent graph rows in foreign-key order.

    Args:
        store: Destination metadata store.
        rows: Typed SQL values grouped by table.
    """
    with store.engine.begin() as connection:
        for table in SQLModel.metadata.sorted_tables:
            for values in rows.get(table.name, []):
                connection.execute(table.insert().values(**values))


def seed_run(
    store: SqlZenStore,
    now: datetime,
    parent: UUID | None = None,
    age: int = 100,
    bundle_id: UUID | None = None,
) -> dict[str, UUID]:
    """Persist the shared typed graph for policy and endpoint checks.

    Args:
        store: Isolated destination store.
        now: Policy evaluation time.
        parent: Optional root run for a nested execution.
        age: Execution age in days.
        bundle_id: Archive marker applied to execution identities.

    Returns:
        Graph identities used by policy and endpoint assertions.
    """
    project = store.list_projects(ProjectFilter()).items[0].id
    source = graph_rows(project, now - timedelta(days=age))
    source["pipeline_run"][0].update(
        parent_run_id=parent,
        root_run_id=parent,
        archive_bundle_id=bundle_id,
    )
    source["pipeline_snapshot"][0]["archive_bundle_id"] = bundle_id
    for step in source["step_run"]:
        step["archive_bundle_id"] = bundle_id
    insert_rows(store, source)
    return {
        "project": project,
        "pipeline": source["pipeline"][0]["id"],
        "snapshot": source["pipeline_snapshot"][0]["id"],
        "run": source["pipeline_run"][0]["id"],
        "step": source["step_run"][0]["id"],
        "consumer": source["step_run"][1]["id"],
    }


def read_tables(store: SqlZenStore) -> dict[str, list[dict[str, Any]]]:
    """Read stable hot SQL expectations without duplicating the cold state.

    Args:
        store: Seeded metadata store before archival.

    Returns:
        Detail rows ordered by primary key.
    """
    result = {}
    with Session(store.engine) as session:
        for name in DETAIL_TABLES:
            table = SQLModel.metadata.tables[name]
            result[name] = [
                dict(row)
                for row in session.execute(
                    select(table).order_by(*table.primary_key.columns)
                ).mappings()
            ]
    return result


def golden_document(
    source: dict[str, list[dict[str, Any]]],
) -> ArchiveDocument:
    """Build the archive document of the golden run from its SQL rows.

    Args:
        source: Golden graph rows with snapshot-owned configurations.

    Returns:
        The document an archive pass would capture for the run.
    """

    def fields(model: type, row: dict[str, Any]) -> dict[str, Any]:
        return {name: row[name] for name in model.model_fields}

    run = source["pipeline_run"][0]
    return ArchiveDocument(
        project_id=run["project_id"],
        run_id=run["id"],
        run=RunRecord.model_validate(fields(RunRecord, run)),
        steps=[
            StepRecord.model_validate(
                {
                    **fields(StepRecord, row),
                    "substitutions": json.loads(row["substitutions"]),
                }
            )
            for row in sorted(source["step_run"], key=lambda row: row["id"])
        ],
        snapshots=[
            SnapshotRecord.model_validate(fields(SnapshotRecord, row))
            for row in source["pipeline_snapshot"]
        ],
        configurations=[
            ConfigurationRecord.model_validate(
                fields(ConfigurationRecord, row)
            )
            for row in sorted(
                source["step_configuration"], key=lambda row: row["id"]
            )
        ],
    )


def generate(destination: Path) -> None:
    """Write the golden object, bundle row, and SQL rows for version 1.

    Args:
        destination: Output directory, which need not already exist.
    """
    when = GOLDEN_NOW - timedelta(days=100)
    project = schemas.ProjectSchema(
        id=UUID(int=1),
        name="golden",
        display_name="Golden",
        description="Synthetic version 1 compatibility fixture",
        created=when,
        updated=when,
        retention_settings=RetentionSettings(
            archive_after_days=90
        ).model_dump_json(),
    )
    source = graph_rows(project.id, when, fixed=True)
    source["project"] = [project.model_dump()]
    encoded = encode(golden_document(source))
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "v1-document.json.gz").write_bytes(encoded.data)
    (destination / "v1-bundle.json").write_bytes(
        canonical_json(
            {
                "bundle_id": str(GOLDEN_BUNDLE_ID),
                "content_hash": encoded.content_hash,
                "created": GOLDEN_NOW.isoformat(),
                "project_id": str(project.id),
                "run_id": str(source["pipeline_run"][0]["id"]),
                "size_bytes": len(encoded.data),
            }
        )
        + b"\n"
    )
    (destination / "v1-sql.json").write_text(
        json.dumps(
            {"before": source},
            default=pydantic_encoder,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir", type=Path, default=Path(__file__).parent / "fixtures"
    )
    generate(parser.parse_args().output_dir)
