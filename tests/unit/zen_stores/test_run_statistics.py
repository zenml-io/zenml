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
"""Unit tests for the run statistics aggregation in SqlZenStore."""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterator, Optional
from uuid import UUID, uuid4

import pytest

from zenml.enums import (
    ExecutionStatus,
    MetadataResourceTypes,
    TaggableResourceTypes,
)
from zenml.metadata.metadata_types import MetadataTypeEnum
from zenml.models import (
    MetadataGrouping,
    MetadataMetric,
    PipelineRunFilter,
    ProjectFilter,
    RunStatisticsRequest,
    SimpleGrouping,
    SimpleMetric,
    StackFilter,
    TimeGrouping,
    UserFilter,
)
from zenml.zen_stores.schemas import (
    ArtifactSchema,
    ArtifactVersionSchema,
    PipelineRunSchema,
    PipelineSchema,
    PipelineSnapshotSchema,
    RunMetadataResourceSchema,
    RunMetadataSchema,
    StepRunOutputArtifactSchema,
    StepRunSchema,
    TagResourceSchema,
    TagSchema,
    TriggerSchema,
)
from zenml.zen_stores.schemas.trigger_assoc import TriggerExecutionSchema
from zenml.zen_stores.sql_zen_store import (
    Session,
    SqlZenStore,
    SqlZenStoreConfiguration,
)


@pytest.fixture
def sql_store(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> Iterator[SqlZenStore]:
    """Create a fresh SQLite-backed SqlZenStore for tests."""
    db_dir = tmp_path / "zenml-cfg"
    db_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("ZENML_CONFIG_PATH", str(db_dir))
    db_path = db_dir / "test.db"
    config = SqlZenStoreConfiguration(url=f"sqlite:///{db_path}")
    store = SqlZenStore(config=config, skip_default_registrations=False)
    yield store


def _project_id(store: SqlZenStore) -> UUID:
    return (
        store.list_projects(project_filter_model=ProjectFilter()).items[0].id
    )


def _default_user_id(store: SqlZenStore) -> UUID:
    return store.list_users(user_filter_model=UserFilter()).items[0].id


def _create_run(
    sql_store: SqlZenStore,
    *,
    project_id: UUID,
    name: str,
    status: ExecutionStatus = ExecutionStatus.COMPLETED,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    pipeline_id: Optional[UUID] = None,
    snapshot_id: Optional[UUID] = None,
    user_id: Optional[UUID] = None,
    index: int = 1,
) -> UUID:
    run = PipelineRunSchema(
        id=uuid4(),
        project_id=project_id,
        name=name,
        orchestrator_run_id=None,
        start_time=start_time,
        end_time=end_time,
        status=status.value,
        index=index,
        in_progress=False,
        enable_heartbeat=False,
        pipeline_id=pipeline_id,
        snapshot_id=snapshot_id,
        user_id=user_id,
    )
    with Session(sql_store.engine, expire_on_commit=False) as session:
        session.add(run)
        session.commit()
    return run.id


def _create_run_metadata(
    sql_store: SqlZenStore,
    *,
    project_id: UUID,
    run_id: UUID,
    key: str,
    value: object,
    type_: MetadataTypeEnum,
) -> None:
    rm = RunMetadataSchema(
        project_id=project_id,
        key=key,
        value=json.dumps(value),
        type=type_.value,
    )
    with Session(sql_store.engine) as session:
        session.add(rm)
        session.flush()
        session.add(
            RunMetadataResourceSchema(
                resource_id=run_id,
                resource_type=MetadataResourceTypes.PIPELINE_RUN.value,
                run_metadata_id=rm.id,
            )
        )
        session.commit()


def _create_pipeline(sql_store: SqlZenStore, project_id: UUID) -> UUID:
    pipeline = PipelineSchema(
        id=uuid4(),
        project_id=project_id,
        name=f"pipeline-{uuid4().hex[:8]}",
        run_count=0,
    )
    with Session(sql_store.engine, expire_on_commit=False) as session:
        session.add(pipeline)
        session.commit()
    return pipeline.id


def _create_snapshot(
    sql_store: SqlZenStore,
    project_id: UUID,
    pipeline_id: UUID,
    source_snapshot_id: Optional[UUID] = None,
    stack_id: Optional[UUID] = None,
) -> UUID:
    snapshot = PipelineSnapshotSchema(
        id=uuid4(),
        project_id=project_id,
        pipeline_id=pipeline_id,
        pipeline_configuration="{}",
        client_environment="{}",
        run_name_template="t",
        client_version="0.0.0",
        server_version="0.0.0",
        source_snapshot_id=source_snapshot_id,
        stack_id=stack_id,
        step_count=0,
    )
    with Session(sql_store.engine, expire_on_commit=False) as session:
        session.add(snapshot)
        session.commit()
    return snapshot.id


def _create_trigger(sql_store: SqlZenStore, project_id: UUID) -> UUID:
    trigger = TriggerSchema(
        id=uuid4(),
        project_id=project_id,
        name=f"trigger-{uuid4().hex[:8]}",
        active=True,
        is_archived=False,
        type="webhook",
        flavor="test",
        configuration="{}",
        concurrency="SKIP",
    )
    with Session(sql_store.engine, expire_on_commit=False) as session:
        session.add(trigger)
        session.commit()
    return trigger.id


def _create_tag(sql_store: SqlZenStore, project_id: UUID, name: str) -> UUID:
    tag = TagSchema(
        id=uuid4(),
        name=name,
        color="gray",
    )
    with Session(sql_store.engine, expire_on_commit=False) as session:
        session.add(tag)
        session.commit()
    return tag.id


def test_run_count_grouped_by_status(sql_store: SqlZenStore) -> None:
    """Returns one row per status with the right run counts."""
    project_id = _project_id(sql_store)
    _create_run(
        sql_store,
        project_id=project_id,
        name="r1",
        status=ExecutionStatus.COMPLETED,
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="r2",
        status=ExecutionStatus.COMPLETED,
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="r3",
        status=ExecutionStatus.FAILED,
    )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[SimpleGrouping(type="status", name="status")],
    )
    response = sql_store.get_run_statistics(request)

    by_status = {g.group_keys["status"]: g for g in response.groups}
    assert by_status["completed"].run_count == 2
    assert by_status["failed"].run_count == 1
    # ordering: run_count descending
    assert response.groups[0].run_count >= response.groups[-1].run_count


def test_avg_duration_grouped_by_pipeline(sql_store: SqlZenStore) -> None:
    """Aggregates run duration over the runs joined by pipeline_id."""
    project_id = _project_id(sql_store)
    pid_a = _create_pipeline(sql_store, project_id)
    pid_b = _create_pipeline(sql_store, project_id)
    base = datetime(2026, 1, 1, 12, 0, 0)

    _create_run(
        sql_store,
        project_id=project_id,
        name="a1",
        pipeline_id=pid_a,
        start_time=base,
        end_time=base + timedelta(seconds=10),
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="a2",
        pipeline_id=pid_a,
        start_time=base,
        end_time=base + timedelta(seconds=20),
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="b1",
        pipeline_id=pid_b,
        start_time=base,
        end_time=base + timedelta(seconds=30),
    )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[SimpleGrouping(type="pipeline", name="pipeline")],
        metrics=[
            SimpleMetric(name="avg_dur", source="duration", aggregation="avg")
        ],
    )
    response = sql_store.get_run_statistics(request)

    by_pipeline = {g.group_keys["pipeline"]: g for g in response.groups}
    assert by_pipeline[str(pid_a)].run_count == 2
    assert by_pipeline[str(pid_a)].metrics["avg_dur"] == pytest.approx(15.0)
    assert by_pipeline[str(pid_b)].metrics["avg_dur"] == pytest.approx(30.0)


def test_metadata_aggregation_filters_non_numeric(
    sql_store: SqlZenStore,
) -> None:
    """Average over a metadata key ignores non-numeric stored values."""
    project_id = _project_id(sql_store)
    run_ids = [
        _create_run(sql_store, project_id=project_id, name=f"r{i}")
        for i in range(4)
    ]

    _create_run_metadata(
        sql_store,
        project_id=project_id,
        run_id=run_ids[0],
        key="accuracy",
        value=0.5,
        type_=MetadataTypeEnum.FLOAT,
    )
    _create_run_metadata(
        sql_store,
        project_id=project_id,
        run_id=run_ids[1],
        key="accuracy",
        value=0.9,
        type_=MetadataTypeEnum.FLOAT,
    )
    _create_run_metadata(
        sql_store,
        project_id=project_id,
        run_id=run_ids[2],
        key="accuracy",
        value=2,
        type_=MetadataTypeEnum.INT,
    )
    # Non-numeric entry must be ignored.
    _create_run_metadata(
        sql_store,
        project_id=project_id,
        run_id=run_ids[3],
        key="accuracy",
        value="not-a-number",
        type_=MetadataTypeEnum.STRING,
    )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        metrics=[
            MetadataMetric(
                name="avg_acc",
                source="metadata",
                aggregation="avg",
                metadata_key="accuracy",
            )
        ],
    )
    response = sql_store.get_run_statistics(request)

    assert len(response.groups) == 1
    assert response.groups[0].run_count == 4
    # (0.5 + 0.9 + 2.0) / 3 == 1.13333...
    assert response.groups[0].metrics["avg_acc"] == pytest.approx(
        (0.5 + 0.9 + 2.0) / 3
    )


def test_metadata_grouping_decodes_json_values(
    sql_store: SqlZenStore,
) -> None:
    """Grouping by metadata key produces decoded string keys plus null bucket."""
    project_id = _project_id(sql_store)
    run_ids = [
        _create_run(sql_store, project_id=project_id, name=f"r{i}")
        for i in range(3)
    ]

    _create_run_metadata(
        sql_store,
        project_id=project_id,
        run_id=run_ids[0],
        key="env",
        value="prod",
        type_=MetadataTypeEnum.STRING,
    )
    _create_run_metadata(
        sql_store,
        project_id=project_id,
        run_id=run_ids[1],
        key="env",
        value="prod",
        type_=MetadataTypeEnum.STRING,
    )
    # run_ids[2] has no `env` metadata -> null bucket

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[
            MetadataGrouping(type="metadata", name="env", metadata_key="env")
        ],
    )
    response = sql_store.get_run_statistics(request)

    by_env = {g.group_keys["env"]: g.run_count for g in response.groups}
    assert by_env["prod"] == 2
    assert by_env[None] == 1


def test_metadata_grouping_does_not_double_count_other_keys(
    sql_store: SqlZenStore,
) -> None:
    """Other metadata keys on the same run must not inflate the null bucket.

    Regression test: a run that has both an ``env`` entry and an ``accuracy``
    entry must end up only in its real ``env`` bucket, not in both the real
    bucket and the null bucket.
    """
    project_id = _project_id(sql_store)
    run_ids = [
        _create_run(sql_store, project_id=project_id, name=f"r{i}")
        for i in range(3)
    ]

    # Each "with-env" run also carries an unrelated `accuracy` entry.
    for run_id, env in ((run_ids[0], "prod"), (run_ids[1], "staging")):
        _create_run_metadata(
            sql_store,
            project_id=project_id,
            run_id=run_id,
            key="env",
            value=env,
            type_=MetadataTypeEnum.STRING,
        )
        _create_run_metadata(
            sql_store,
            project_id=project_id,
            run_id=run_id,
            key="accuracy",
            value=0.5,
            type_=MetadataTypeEnum.FLOAT,
        )
    # run_ids[2] has no metadata at all -> belongs in the null bucket

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[
            MetadataGrouping(type="metadata", name="env", metadata_key="env")
        ],
    )
    response = sql_store.get_run_statistics(request)

    by_env = {g.group_keys["env"]: g.run_count for g in response.groups}
    # The two with-env runs must NOT also appear in the null bucket.
    assert by_env == {"prod": 1, "staging": 1, None: 1}
    # And the totals must match the actual number of runs in the project.
    assert sum(g.run_count for g in response.groups) == 3


def test_step_count_collapses_retries(sql_store: SqlZenStore) -> None:
    """COUNT(DISTINCT step_run.name) collapses retries into one step."""
    project_id = _project_id(sql_store)
    run_id = _create_run(sql_store, project_id=project_id, name="r-retry")

    now = datetime(2026, 1, 1, 0, 0, 0)
    with Session(sql_store.engine) as session:
        # Same step name, two versions = retry attempt
        session.add(
            StepRunSchema(
                id=uuid4(),
                project_id=project_id,
                pipeline_run_id=run_id,
                name="train",
                version=1,
                status=ExecutionStatus.FAILED.value,
                is_retriable=True,
                start_time=now,
                end_time=now,
            )
        )
        session.add(
            StepRunSchema(
                id=uuid4(),
                project_id=project_id,
                pipeline_run_id=run_id,
                name="train",
                version=2,
                status=ExecutionStatus.COMPLETED.value,
                is_retriable=False,
                start_time=now,
                end_time=now,
            )
        )
        session.add(
            StepRunSchema(
                id=uuid4(),
                project_id=project_id,
                pipeline_run_id=run_id,
                name="eval",
                version=1,
                status=ExecutionStatus.COMPLETED.value,
                is_retriable=False,
                start_time=now,
                end_time=now,
            )
        )
        session.commit()

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        metrics=[
            SimpleMetric(
                name="avg_steps", source="step_count", aggregation="avg"
            )
        ],
    )
    response = sql_store.get_run_statistics(request)

    assert len(response.groups) == 1
    assert response.groups[0].metrics["avg_steps"] == pytest.approx(2.0)


def test_cached_step_count(sql_store: SqlZenStore) -> None:
    """Counts step runs with status='cached', zero for runs with no hits."""
    project_id = _project_id(sql_store)
    run_a_id = _create_run(sql_store, project_id=project_id, name="r-cache-a")
    run_b_id = _create_run(sql_store, project_id=project_id, name="r-cache-b")

    now = datetime(2026, 1, 1, 0, 0, 0)
    with Session(sql_store.engine) as session:
        # Run A: 2 cached steps + 1 completed step.
        session.add_all(
            [
                StepRunSchema(
                    id=uuid4(),
                    project_id=project_id,
                    pipeline_run_id=run_a_id,
                    name="load",
                    version=1,
                    status=ExecutionStatus.CACHED.value,
                    is_retriable=False,
                    start_time=now,
                    end_time=now,
                ),
                StepRunSchema(
                    id=uuid4(),
                    project_id=project_id,
                    pipeline_run_id=run_a_id,
                    name="featurize",
                    version=1,
                    status=ExecutionStatus.CACHED.value,
                    is_retriable=False,
                    start_time=now,
                    end_time=now,
                ),
                StepRunSchema(
                    id=uuid4(),
                    project_id=project_id,
                    pipeline_run_id=run_a_id,
                    name="train",
                    version=1,
                    status=ExecutionStatus.COMPLETED.value,
                    is_retriable=False,
                    start_time=now,
                    end_time=now,
                ),
            ]
        )
        # Run B: no cached steps.
        session.add(
            StepRunSchema(
                id=uuid4(),
                project_id=project_id,
                pipeline_run_id=run_b_id,
                name="train",
                version=1,
                status=ExecutionStatus.COMPLETED.value,
                is_retriable=False,
                start_time=now,
                end_time=now,
            )
        )
        session.commit()

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        metrics=[
            SimpleMetric(
                name="total_cached",
                source="cached_step_count",
                aggregation="sum",
            ),
            SimpleMetric(
                name="max_cached",
                source="cached_step_count",
                aggregation="max",
            ),
        ],
    )
    response = sql_store.get_run_statistics(request)

    assert len(response.groups) == 1
    assert response.groups[0].metrics["total_cached"] == pytest.approx(2.0)
    assert response.groups[0].metrics["max_cached"] == pytest.approx(2.0)


def test_output_artifact_count_dedups_shared_versions(
    sql_store: SqlZenStore,
) -> None:
    """COUNT(DISTINCT artifact_id) counts each version once per run."""
    project_id = _project_id(sql_store)
    run_a_id = _create_run(sql_store, project_id=project_id, name="r-a")
    run_b_id = _create_run(sql_store, project_id=project_id, name="r-b")

    now = datetime(2026, 1, 1, 0, 0, 0)
    with Session(sql_store.engine) as session:
        artifact = ArtifactSchema(
            id=uuid4(),
            project_id=project_id,
            name=f"art-{uuid4().hex[:8]}",
            has_custom_name=False,
        )
        session.add(artifact)
        session.flush()

        # Run A: two step runs that both reference the same artifact version
        # plus a second step run with its own artifact version. Distinct count
        # should collapse the shared one to 1 + 1 = 2.
        shared_version = ArtifactVersionSchema(
            id=uuid4(),
            project_id=project_id,
            artifact_id=artifact.id,
            version="1",
            type="DataArtifact",
            uri="s3://x/1",
            materializer="m",
            data_type="d",
            save_type="step_output",
        )
        unique_version = ArtifactVersionSchema(
            id=uuid4(),
            project_id=project_id,
            artifact_id=artifact.id,
            version="2",
            type="DataArtifact",
            uri="s3://x/2",
            materializer="m",
            data_type="d",
            save_type="step_output",
        )
        run_b_version = ArtifactVersionSchema(
            id=uuid4(),
            project_id=project_id,
            artifact_id=artifact.id,
            version="3",
            type="DataArtifact",
            uri="s3://x/3",
            materializer="m",
            data_type="d",
            save_type="step_output",
        )
        session.add_all([shared_version, unique_version, run_b_version])
        session.flush()

        step_a1 = StepRunSchema(
            id=uuid4(),
            project_id=project_id,
            pipeline_run_id=run_a_id,
            name="train",
            version=1,
            status=ExecutionStatus.COMPLETED.value,
            is_retriable=False,
            start_time=now,
            end_time=now,
        )
        step_a2 = StepRunSchema(
            id=uuid4(),
            project_id=project_id,
            pipeline_run_id=run_a_id,
            name="eval",
            version=1,
            status=ExecutionStatus.COMPLETED.value,
            is_retriable=False,
            start_time=now,
            end_time=now,
        )
        step_b1 = StepRunSchema(
            id=uuid4(),
            project_id=project_id,
            pipeline_run_id=run_b_id,
            name="train",
            version=1,
            status=ExecutionStatus.COMPLETED.value,
            is_retriable=False,
            start_time=now,
            end_time=now,
        )
        session.add_all([step_a1, step_a2, step_b1])
        session.flush()

        session.add_all(
            [
                StepRunOutputArtifactSchema(
                    step_id=step_a1.id,
                    artifact_id=shared_version.id,
                    name="out",
                ),
                StepRunOutputArtifactSchema(
                    step_id=step_a2.id,
                    artifact_id=shared_version.id,
                    name="out",
                ),
                StepRunOutputArtifactSchema(
                    step_id=step_a2.id,
                    artifact_id=unique_version.id,
                    name="extra",
                ),
                StepRunOutputArtifactSchema(
                    step_id=step_b1.id,
                    artifact_id=run_b_version.id,
                    name="out",
                ),
            ]
        )
        session.commit()

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        metrics=[
            SimpleMetric(
                name="total_outputs",
                source="output_artifact_count",
                aggregation="sum",
            ),
            SimpleMetric(
                name="avg_outputs",
                source="output_artifact_count",
                aggregation="avg",
            ),
        ],
    )
    response = sql_store.get_run_statistics(request)

    assert len(response.groups) == 1
    # Run A contributes 2 (shared version dedup'd) + Run B contributes 1 = 3.
    assert response.groups[0].metrics["total_outputs"] == pytest.approx(3.0)
    assert response.groups[0].metrics["avg_outputs"] == pytest.approx(1.5)


def test_multi_dimensional_grouping(sql_store: SqlZenStore) -> None:
    """Status x time bucket produces one row per combination."""
    project_id = _project_id(sql_store)
    day_one = datetime(2026, 1, 1, 12, 0, 0)
    day_two = datetime(2026, 1, 2, 12, 0, 0)

    _create_run(
        sql_store,
        project_id=project_id,
        name="d1-c",
        status=ExecutionStatus.COMPLETED,
        start_time=day_one,
        end_time=day_one + timedelta(seconds=1),
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="d1-f",
        status=ExecutionStatus.FAILED,
        start_time=day_one,
        end_time=day_one + timedelta(seconds=1),
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="d2-c1",
        status=ExecutionStatus.COMPLETED,
        start_time=day_two,
        end_time=day_two + timedelta(seconds=1),
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="d2-c2",
        status=ExecutionStatus.COMPLETED,
        start_time=day_two,
        end_time=day_two + timedelta(seconds=1),
    )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[
            TimeGrouping(type="time", name="day", granularity="day"),
            SimpleGrouping(type="status", name="status"),
        ],
    )
    response = sql_store.get_run_statistics(request)

    combos = {
        (g.group_keys["day"], g.group_keys["status"]): g.run_count
        for g in response.groups
    }
    assert combos[("2026-01-01", "completed")] == 1
    assert combos[("2026-01-01", "failed")] == 1
    assert combos[("2026-01-02", "completed")] == 2
    # time bucket ordering ascending
    days = [str(g.group_keys["day"]) for g in response.groups]
    assert days == sorted(days)


def test_duration_metric_unaffected_by_metadata_fan_out(
    sql_store: SqlZenStore,
) -> None:
    """Per-run scalars are not inflated by multi-row metadata metrics.

    R1 has duration 10s and two `score` metadata rows (5, 15); R2 has
    duration 20s and one `score`=30. SUM(duration) must be 30 (not 40)
    and AVG(duration) must be 15 (not the fan-out-inflated 13.33).
    The metadata metric uses the latest value per run (R1=15, R2=30),
    matching `RunMetadataInterface.fetch_metadata` semantics.
    """
    project_id = _project_id(sql_store)
    base = datetime(2026, 1, 1, 12, 0, 0)
    r1_id = _create_run(
        sql_store,
        project_id=project_id,
        name="r1",
        start_time=base,
        end_time=base + timedelta(seconds=10),
    )
    r2_id = _create_run(
        sql_store,
        project_id=project_id,
        name="r2",
        start_time=base,
        end_time=base + timedelta(seconds=20),
    )

    for value in (5, 15):
        _create_run_metadata(
            sql_store,
            project_id=project_id,
            run_id=r1_id,
            key="score",
            value=value,
            type_=MetadataTypeEnum.INT,
        )
    _create_run_metadata(
        sql_store,
        project_id=project_id,
        run_id=r2_id,
        key="score",
        value=30,
        type_=MetadataTypeEnum.INT,
    )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        metrics=[
            SimpleMetric(name="sum_dur", source="duration", aggregation="sum"),
            SimpleMetric(name="avg_dur", source="duration", aggregation="avg"),
            MetadataMetric(
                name="sum_score",
                source="metadata",
                aggregation="sum",
                metadata_key="score",
            ),
        ],
    )
    response = sql_store.get_run_statistics(request)

    assert len(response.groups) == 1
    group = response.groups[0]
    assert group.run_count == 2
    assert group.metrics["sum_dur"] == pytest.approx(30.0)
    assert group.metrics["avg_dur"] == pytest.approx(15.0)
    # Latest-per-run for score: R1=15, R2=30 → SUM = 45.
    assert group.metrics["sum_score"] == pytest.approx(45.0)


def test_week_granularity_buckets_by_monday(sql_store: SqlZenStore) -> None:
    """WEEK granularity labels each run with the Monday of its week."""
    project_id = _project_id(sql_store)
    # 2025-12-29 is the Monday of the week that contains 2025-12-31 and
    # 2026-01-01, so all three runs must land in the 2025-12-29 bucket.
    monday = datetime(2025, 12, 29, 10, 0, 0)
    wednesday = datetime(2025, 12, 31, 10, 0, 0)
    thursday = datetime(2026, 1, 1, 10, 0, 0)
    # 2026-01-05 is the next Monday, in a separate bucket.
    next_monday = datetime(2026, 1, 5, 10, 0, 0)

    for i, ts in enumerate([monday, wednesday, thursday, next_monday]):
        _create_run(
            sql_store,
            project_id=project_id,
            name=f"r-{i}",
            start_time=ts,
            end_time=ts + timedelta(seconds=1),
        )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[
            TimeGrouping(type="time", name="week", granularity="week"),
        ],
    )
    response = sql_store.get_run_statistics(request)

    by_week = {g.group_keys["week"]: g.run_count for g in response.groups}
    assert by_week == {"2025-12-29": 3, "2026-01-05": 1}
    weeks = [str(g.group_keys["week"]) for g in response.groups]
    assert weeks == sorted(weeks)


def test_grouping_by_snapshot_and_user(sql_store: SqlZenStore) -> None:
    """Snapshot and user grouping return UUID strings."""
    project_id = _project_id(sql_store)
    user_a = _default_user_id(sql_store)
    pipeline_id = _create_pipeline(sql_store, project_id)
    snap = _create_snapshot(sql_store, project_id, pipeline_id)
    _create_run(
        sql_store,
        project_id=project_id,
        name="r1",
        snapshot_id=snap,
        user_id=user_a,
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="r2",
        snapshot_id=snap,
        user_id=user_a,
    )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[
            SimpleGrouping(type="snapshot", name="snap"),
            SimpleGrouping(type="user", name="user"),
        ],
    )
    response = sql_store.get_run_statistics(request)

    assert len(response.groups) == 1
    group = response.groups[0]
    assert group.group_keys["snap"] == str(snap)
    assert group.group_keys["user"] == str(user_a)
    assert group.run_count == 2


def test_grouping_by_source_snapshot(sql_store: SqlZenStore) -> None:
    """Source snapshot grouping joins through pipeline_snapshot."""
    project_id = _project_id(sql_store)
    pipeline_id = _create_pipeline(sql_store, project_id)
    # source_snapshot_id has no FK; can be any UUID.
    source_snap = uuid4()
    snapshot_id = _create_snapshot(
        sql_store, project_id, pipeline_id, source_snap
    )

    _create_run(
        sql_store,
        project_id=project_id,
        name="r1",
        snapshot_id=snapshot_id,
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="r2",
        snapshot_id=snapshot_id,
    )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[
            SimpleGrouping(type="source_snapshot", name="src"),
        ],
    )
    response = sql_store.get_run_statistics(request)

    by_src = {g.group_keys["src"]: g.run_count for g in response.groups}
    assert by_src[str(source_snap)] == 2


def test_grouping_by_stack(sql_store: SqlZenStore) -> None:
    """Stack grouping joins through pipeline_snapshot.stack_id."""
    project_id = _project_id(sql_store)

    stack_id = (
        sql_store.list_stacks(stack_filter_model=StackFilter()).items[0].id
    )
    pipeline_id = _create_pipeline(sql_store, project_id)
    snapshot_id = _create_snapshot(
        sql_store, project_id, pipeline_id, stack_id=stack_id
    )

    for i in range(3):
        _create_run(
            sql_store,
            project_id=project_id,
            name=f"r{i}",
            snapshot_id=snapshot_id,
        )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[SimpleGrouping(type="stack", name="stack")],
    )
    response = sql_store.get_run_statistics(request)

    by_stack = {g.group_keys["stack"]: g.run_count for g in response.groups}
    assert by_stack[str(stack_id)] == 3


def test_grouping_by_trigger(sql_store: SqlZenStore) -> None:
    """Trigger grouping joins through trigger_execution to TriggerSchema.id."""
    project_id = _project_id(sql_store)
    trigger_id = _create_trigger(sql_store, project_id)

    triggered_ids = [
        _create_run(sql_store, project_id=project_id, name=f"t{i}")
        for i in range(2)
    ]
    _create_run(sql_store, project_id=project_id, name="manual")

    with Session(sql_store.engine) as session:
        for run_id in triggered_ids:
            session.add(
                TriggerExecutionSchema(
                    trigger_id=trigger_id, pipeline_run_id=run_id
                )
            )
        session.commit()

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[SimpleGrouping(type="trigger", name="trigger")],
    )
    response = sql_store.get_run_statistics(request)

    by_trigger = {
        g.group_keys["trigger"]: g.run_count for g in response.groups
    }
    assert by_trigger[str(trigger_id)] == 2
    assert by_trigger[None] == 1


def test_grouping_by_tag_multi_bucket(sql_store: SqlZenStore) -> None:
    """A run with N tags contributes to N tag buckets.

    Sum across tag buckets can therefore exceed the number of runs.
    Untagged runs land in the null bucket.
    """
    project_id = _project_id(sql_store)
    run_ids = [
        _create_run(sql_store, project_id=project_id, name=f"r{i}")
        for i in range(3)
    ]

    tag_prod = _create_tag(sql_store, project_id, "prod")
    tag_v1 = _create_tag(sql_store, project_id, "v1")

    with Session(sql_store.engine) as session:
        # run_ids[0] tagged ["prod", "v1"], run_ids[1] tagged ["prod"],
        # run_ids[2] none.
        for tag_id in (tag_prod, tag_v1):
            session.add(
                TagResourceSchema(
                    tag_id=tag_id,
                    resource_id=run_ids[0],
                    resource_type=TaggableResourceTypes.PIPELINE_RUN.value,
                )
            )
        session.add(
            TagResourceSchema(
                tag_id=tag_prod,
                resource_id=run_ids[1],
                resource_type=TaggableResourceTypes.PIPELINE_RUN.value,
            )
        )
        session.commit()

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[SimpleGrouping(type="tag", name="tag")],
    )
    response = sql_store.get_run_statistics(request)

    by_tag = {g.group_keys["tag"]: g.run_count for g in response.groups}
    assert by_tag == {"prod": 2, "v1": 1, None: 1}
    # Sum exceeds total runs (3) because runs[0] is in two buckets.
    assert sum(by_tag.values()) == 4


def test_max_groups_truncation(sql_store: SqlZenStore) -> None:
    """When more groups exist than max_groups, the response is truncated."""
    project_id = _project_id(sql_store)
    pipeline_ids = [_create_pipeline(sql_store, project_id) for _ in range(5)]
    for i in range(5):
        _create_run(
            sql_store,
            project_id=project_id,
            name=f"r{i}",
            status=ExecutionStatus.COMPLETED,
            pipeline_id=pipeline_ids[i],
        )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[SimpleGrouping(type="pipeline", name="pipeline")],
        max_groups=3,
    )
    response = sql_store.get_run_statistics(request)

    assert response.truncated is True
    assert len(response.groups) == 3


def test_time_grouping_truncation_keeps_latest_buckets(
    sql_store: SqlZenStore,
) -> None:
    """Truncation drops the oldest buckets and keeps the latest ones."""
    project_id = _project_id(sql_store)
    base = datetime(2026, 1, 1, 12, 0, 0)
    for i in range(5):
        _create_run(
            sql_store,
            project_id=project_id,
            name=f"r{i}",
            start_time=base + timedelta(days=i),
            end_time=base + timedelta(days=i, seconds=1),
        )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[
            TimeGrouping(type="time", name="day", granularity="day"),
        ],
        max_groups=3,
    )
    response = sql_store.get_run_statistics(request)

    assert response.truncated is True
    assert [g.group_keys["day"] for g in response.groups] == [
        "2026-01-03",
        "2026-01-04",
        "2026-01-05",
    ]


def test_empty_groupings_produce_single_row(sql_store: SqlZenStore) -> None:
    """No groupings returns one row with the global run_count."""
    project_id = _project_id(sql_store)
    for i in range(3):
        _create_run(sql_store, project_id=project_id, name=f"r{i}")

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
    )
    response = sql_store.get_run_statistics(request)

    assert len(response.groups) == 1
    assert response.groups[0].run_count == 3
    assert response.groups[0].group_keys == {}
    assert response.groups[0].metrics == {}


def test_metadata_key_used_for_both_grouping_and_metric(
    sql_store: SqlZenStore,
) -> None:
    """Same metadata key serves a group bucket and an aggregate together.

    Two runs share env=prod, one has env=staging. The same `env` key drives
    the grouping (bucket label) and the numeric metric (avg score per
    bucket, since `env` is non-numeric the metric must be null). A second
    metric over a different metadata key proves numeric aggregation still
    works alongside.
    """
    project_id = _project_id(sql_store)
    run_ids = [
        _create_run(sql_store, project_id=project_id, name=f"r{i}")
        for i in range(3)
    ]

    for run_id, env in (
        (run_ids[0], "prod"),
        (run_ids[1], "prod"),
        (run_ids[2], "staging"),
    ):
        _create_run_metadata(
            sql_store,
            project_id=project_id,
            run_id=run_id,
            key="env",
            value=env,
            type_=MetadataTypeEnum.STRING,
        )
    for run_id, score in (
        (run_ids[0], 10),
        (run_ids[1], 20),
        (run_ids[2], 30),
    ):
        _create_run_metadata(
            sql_store,
            project_id=project_id,
            run_id=run_id,
            key="score",
            value=score,
            type_=MetadataTypeEnum.INT,
        )

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id),
        groupings=[
            MetadataGrouping(type="metadata", name="env", metadata_key="env"),
        ],
        metrics=[
            # `env` is non-numeric, so the metric must be null in every
            # bucket; this verifies the per-run latest projection drives
            # both columns without collision.
            MetadataMetric(
                name="avg_env_numeric",
                source="metadata",
                aggregation="avg",
                metadata_key="env",
            ),
            MetadataMetric(
                name="avg_score",
                source="metadata",
                aggregation="avg",
                metadata_key="score",
            ),
        ],
    )
    response = sql_store.get_run_statistics(request)

    by_env = {g.group_keys["env"]: g for g in response.groups}
    assert by_env["prod"].run_count == 2
    assert by_env["prod"].metrics["avg_env_numeric"] is None
    assert by_env["prod"].metrics["avg_score"] == pytest.approx(15.0)
    assert by_env["staging"].run_count == 1
    assert by_env["staging"].metrics["avg_env_numeric"] is None
    assert by_env["staging"].metrics["avg_score"] == pytest.approx(30.0)


def test_tag_filter_does_not_inflate_metrics(sql_store: SqlZenStore) -> None:
    """PipelineRunFilter(tags=[...]) must not fan out per-run aggregates.

    A run with N tags is joined N times by `TaggableFilter.apply_filter`.
    Without deduplication that multiplies SUM/AVG/step_count/etc. The
    expected sum is 10 + 20 = 30; an inflated query would return 40
    (the multi-tagged run counted twice).
    """
    project_id = _project_id(sql_store)
    base = datetime(2026, 1, 1, 12, 0, 0)
    r_multi = _create_run(
        sql_store,
        project_id=project_id,
        name="r-multi",
        start_time=base,
        end_time=base + timedelta(seconds=10),
    )
    r_single = _create_run(
        sql_store,
        project_id=project_id,
        name="r-single",
        start_time=base,
        end_time=base + timedelta(seconds=20),
    )
    _create_run(
        sql_store,
        project_id=project_id,
        name="r-other",
        start_time=base,
        end_time=base + timedelta(seconds=100),
    )

    tag_prod = _create_tag(sql_store, project_id, "prod")
    tag_v1 = _create_tag(sql_store, project_id, "v1")

    now = datetime(2026, 1, 1, 0, 0, 0)
    with Session(sql_store.engine) as session:
        for tag_id in (tag_prod, tag_v1):
            session.add(
                TagResourceSchema(
                    tag_id=tag_id,
                    resource_id=r_multi,
                    resource_type=TaggableResourceTypes.PIPELINE_RUN.value,
                )
            )
        session.add(
            TagResourceSchema(
                tag_id=tag_prod,
                resource_id=r_single,
                resource_type=TaggableResourceTypes.PIPELINE_RUN.value,
            )
        )
        # One step per "prod" run to confirm step_count is also not inflated.
        for run_id in (r_multi, r_single):
            session.add(
                StepRunSchema(
                    id=uuid4(),
                    project_id=project_id,
                    pipeline_run_id=run_id,
                    name="train",
                    version=1,
                    status=ExecutionStatus.COMPLETED.value,
                    is_retriable=False,
                    start_time=now,
                    end_time=now,
                )
            )
        session.commit()

    request = RunStatisticsRequest(
        filter=PipelineRunFilter(project=project_id, tags=["prod"]),
        metrics=[
            SimpleMetric(name="sum_dur", source="duration", aggregation="sum"),
            SimpleMetric(name="avg_dur", source="duration", aggregation="avg"),
            SimpleMetric(
                name="sum_steps", source="step_count", aggregation="sum"
            ),
        ],
    )
    response = sql_store.get_run_statistics(request)

    assert len(response.groups) == 1
    group = response.groups[0]
    assert group.run_count == 2
    assert group.metrics["sum_dur"] == pytest.approx(30.0)
    assert group.metrics["avg_dur"] == pytest.approx(15.0)
    assert group.metrics["sum_steps"] == pytest.approx(2.0)
