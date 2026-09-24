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
"""Tests for reading pipeline runs, their DAG, and their snapshots."""

from datetime import datetime
from types import SimpleNamespace
from typing import Optional
from unittest.mock import Mock
from uuid import UUID, uuid4

import pytest
from sqlmodel import SQLModel

from zenml.client import Client
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.models import (
    PipelineRunFilter,
    PipelineSnapshotFilter,
    ProjectFilter,
    StackFilter,
)
from zenml.zen_stores import schemas as s
from zenml.zen_stores.sql_zen_store import SqlZenStore

WHEN = datetime(2026, 1, 1)


def insert(store: SqlZenStore, *records: SQLModel) -> None:
    """Insert rows directly, in foreign-key order."""
    rows: dict = {}
    for record in records:
        rows.setdefault(record.__tablename__, []).append(record.model_dump())
    with store.engine.begin() as connection:
        for table in SQLModel.metadata.sorted_tables:
            for values in rows.get(table.name, []):
                connection.execute(table.insert().values(**values))


def two_step_run(store: SqlZenStore, kind: str) -> SimpleNamespace:
    """Insert a finished producer/consumer run.

    Args:
        store: Store to insert into.
        kind: Where step definitions live: `static` on the snapshot,
            `dynamic` on each step run, or `legacy` inline on the step rows
            of a run that has no snapshot.

    Returns:
        The run and step IDs.
    """
    project = store.list_projects(ProjectFilter()).items[0].id
    shared = dict(project_id=project, created=WHEN, updated=WHEN)
    pipeline = s.PipelineSchema(name=str(uuid4()), run_count=1, **shared)
    snapshot = s.PipelineSnapshotSchema(
        pipeline_id=pipeline.id,
        pipeline_configuration='{"name":"example"}',
        client_environment="{}",
        step_count=2,
        run_name_template="example",
        is_dynamic=kind == "dynamic",
        **shared,
    )
    legacy = kind == "legacy"
    run = s.PipelineRunSchema(
        name=str(uuid4()),
        pipeline_id=pipeline.id,
        snapshot_id=None if legacy else snapshot.id,
        pipeline_configuration=snapshot.pipeline_configuration
        if legacy
        else None,
        client_environment="{}" if legacy else None,
        status="completed",
        in_progress=False,
        index=1,
        enable_heartbeat=False,
        start_time=WHEN,
        end_time=WHEN,
        **shared,
    )
    records = [pipeline, snapshot, run]
    # The consumer's row sorts before the producer's, so the DAG has to order
    # steps by their dependencies rather than by how the rows load.
    consumer_id, producer_id = sorted([uuid4(), uuid4()])
    for index, (name, step_id) in enumerate(
        (("producer", producer_id), ("consumer", consumer_id))
    ):
        definition = Step(
            spec=StepSpec(
                source=Source(
                    module="tests", attribute=name, type=SourceType.INTERNAL
                ),
                upstream_steps=["producer"] if index else [],
            ),
            config=StepConfiguration(name=name),
        )
        records.append(
            s.StepRunSchema(
                id=step_id,
                name=name,
                pipeline_run_id=run.id,
                snapshot_id=None if legacy else snapshot.id,
                step_configuration=definition.model_dump_json()
                if legacy
                else None,
                status="completed",
                version=1,
                is_retriable=False,
                start_time=WHEN,
                end_time=WHEN,
                **shared,
            )
        )
        if not legacy:
            records.append(
                s.StepConfigurationSchema(
                    name=name,
                    index=index,
                    snapshot_id=snapshot.id if kind == "static" else None,
                    step_run_id=step_id if kind == "dynamic" else None,
                    config=definition.model_dump_json(),
                    created=WHEN,
                    updated=WHEN,
                )
            )
    records.append(
        s.StepRunParentsSchema(parent_id=producer_id, child_id=consumer_id)
    )
    insert(store, *records)
    return SimpleNamespace(
        run=run.id, producer=producer_id, consumer=consumer_id
    )


@pytest.mark.parametrize("kind", ["static", "dynamic", "legacy"])
def test_run_dag_links_the_producer_to_its_consumer(
    clean_client: Client, kind: str
) -> None:
    """Each way of storing step definitions yields the same two-step graph."""
    store = clean_client.zen_store
    ids = two_step_run(store, kind)

    dag = store.get_pipeline_run_dag(ids.run)

    steps = {node.name: node for node in dag.nodes if node.type == "step"}
    assert set(steps) == {"producer", "consumer"}
    assert steps["producer"].id == ids.producer
    assert any(
        edge.source == steps["producer"].node_id
        and edge.target == steps["consumer"].node_id
        for edge in dag.edges
    )


def test_a_page_of_run_summaries_parses_no_configuration(
    clean_client: Client, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Only hydrated runs pay for decoding their pipeline configuration."""
    store = clean_client.zen_store
    ids = two_step_run(store, "static")
    parsed = Mock(wraps=s.PipelineRunSchema.get_pipeline_configuration)
    monkeypatch.setattr(
        s.PipelineRunSchema,
        "get_pipeline_configuration",
        lambda run: parsed(run),
    )

    summaries = store.list_runs(PipelineRunFilter(id=ids.run), hydrate=False)
    parsed.assert_not_called()
    hydrated = store.list_runs(PipelineRunFilter(id=ids.run), hydrate=True)

    assert [run.id for run in summaries.items] == [ids.run]
    assert hydrated.items[0].config.name == "example"
    parsed.assert_called()


def test_runnable_and_templatable_filters_follow_the_build(
    clean_client: Client,
) -> None:
    """A snapshot is runnable only with a server-side build on a stack."""
    store = clean_client.zen_store
    project = store.list_projects(ProjectFilter()).items[0].id
    stack = store.list_stacks(StackFilter()).items[0].id
    shared = dict(project_id=project, created=WHEN, updated=WHEN)

    def build(
        is_local: bool, stack_id: Optional[UUID]
    ) -> s.PipelineBuildSchema:
        return s.PipelineBuildSchema(
            stack_id=stack_id,
            images="{}",
            is_local=is_local,
            contains_code=True,
            **shared,
        )

    builds = {
        "server": build(is_local=False, stack_id=stack),
        "local": build(is_local=True, stack_id=stack),
        "stackless": build(is_local=False, stack_id=None),
    }
    pipeline = s.PipelineSchema(name=str(uuid4()), run_count=0, **shared)
    records: list = [pipeline, *builds.values()]
    snapshots, runs = {}, {}
    for name in ("server", "local", "stackless", "unbuilt"):
        snapshots[name] = s.PipelineSnapshotSchema(
            pipeline_id=pipeline.id,
            build_id=builds[name].id if name in builds else None,
            pipeline_configuration='{"name":"example"}',
            client_environment="{}",
            step_count=0,
            run_name_template="example",
            **shared,
        )
        runs[name] = s.PipelineRunSchema(
            name=str(uuid4()),
            snapshot_id=snapshots[name].id,
            status="completed",
            in_progress=False,
            index=1,
            enable_heartbeat=False,
            **shared,
        )
    runs["no snapshot"] = s.PipelineRunSchema(
        name=str(uuid4()),
        pipeline_configuration='{"name":"example"}',
        status="completed",
        in_progress=False,
        index=1,
        enable_heartbeat=False,
        **shared,
    )
    insert(store, *records, *snapshots.values(), *runs.values())

    runnable = store.list_snapshots(PipelineSnapshotFilter(runnable=True))
    templatable = store.list_runs(PipelineRunFilter(templatable=True))
    not_templatable = store.list_runs(PipelineRunFilter(templatable=False))

    assert {item.id for item in runnable.items} == {snapshots["server"].id}
    assert {run.id for run in templatable.items} == {runs["server"].id}
    assert {run.id for run in not_templatable.items} == {
        run.id for name, run in runs.items() if name != "server"
    }
