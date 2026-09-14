# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Regression coverage for shared execution-retention source policies."""

import json
from itertools import product
from uuid import UUID, uuid4

import pytest
from sqlalchemy import event
from sqlmodel import Session

from zenml.models import PipelineRunFilter, StackFilter
from zenml.zen_stores.schemas import (
    PipelineBuildSchema,
    PipelineRunSchema,
    PipelineSnapshotSchema,
    StepRunSchema,
)


@pytest.mark.parametrize("kind", ["static", "dynamic", "legacy"])
def test_shared_configuration_resolution_preserves_reader_contracts(
    retention_store, run_factory, kind
) -> None:
    """Shared decoding preserves substitutions, hooks, legacy, and replay rules."""
    ids = run_factory(retention_store, kind=kind)
    pipeline = {
        "name": "example",
        "substitutions": {"team": "cleanup"},
        "environment": {"SHARED": "yes"},
        "secrets": ["shared_secret"],
        "step_input_overrides": {"consumer": {"shadowed": str(UUID(int=123))}},
        "success_hook_source": {
            "module": "tests",
            "attribute": "hook",
            "type": "internal",
        },
    }
    with Session(retention_store.engine) as session:
        snapshot = session.get(PipelineSnapshotSchema, ids.snapshot)
        run = session.get(PipelineRunSchema, ids.run)
        assert snapshot is not None and run is not None
        snapshot.pipeline_configuration = json.dumps(pipeline)
        session.add(snapshot)
        if kind == "legacy":
            run.pipeline_configuration = json.dumps(pipeline)
            session.add(run)

        for step_id in (ids.producer, ids.consumer):
            step = session.get(StepRunSchema, step_id)
            assert step is not None
            if kind == "legacy":
                configuration = json.loads(step.step_configuration)
                configuration["config"]["parameters"] = {
                    "shadowed": "original",
                    "kept": "value",
                }
                step.step_configuration = json.dumps(configuration)
                session.add(step)
            else:
                owner = step.dynamic_config or step.static_config
                assert owner is not None
                configuration = json.loads(owner.config)
                configuration.pop("config", None)
                configuration["step_config_overrides"]["parameters"] = {
                    "shadowed": "original",
                    "kept": "value",
                }
                owner.config = json.dumps(configuration)
                session.add(owner)
        session.commit()

    with Session(retention_store.engine) as session:
        run = session.get(PipelineRunSchema, ids.run)
        producer = session.get(StepRunSchema, ids.producer)
        consumer = session.get(StepRunSchema, ids.consumer)
        assert (
            run is not None and producer is not None and consumer is not None
        )

        pipeline_configuration = run.get_pipeline_configuration()
        producer_configuration = producer.get_step_configuration()
        consumer_configuration = consumer.get_step_configuration()

        assert pipeline_configuration.substitutions == {
            "team": "cleanup",
            "date": "2025_09_23",
            "time": "00_00_00_000000",
        }
        if kind == "legacy":
            assert producer_configuration.config.environment == {}
            assert producer_configuration.config.substitutions == {}
            assert consumer_configuration.config.parameters == {
                "shadowed": "original",
                "kept": "value",
            }
        else:
            assert producer_configuration.config.environment == {
                "SHARED": "yes"
            }
            assert producer_configuration.config.parameters == {
                "shadowed": "original",
                "kept": "value",
            }
            assert consumer_configuration.config.parameters == {
                "kept": "value"
            }
            assert (
                producer_configuration.config.success_hook_source is None
            ) is (kind == "dynamic")

        if kind == "static":
            run_step = run.get_step_configuration("consumer")
            assert run_step.config.parameters == {
                "shadowed": "original",
                "kept": "value",
            }


def test_templatable_filter_preserves_nullable_and_archive_cases(
    retention_store, run_factory
) -> None:
    """Shared positive policy keeps the existing negative SQL truth table."""
    labels = {}
    project_id = None
    stack_id = retention_store.list_stacks(StackFilter()).items[0].id
    for run_archived, snapshot_state, build_state in product(
        (False, True),
        ("missing", "hot", "cold"),
        (
            "missing",
            "local_stack",
            "local_no_stack",
            "remote_stack",
            "remote_no_stack",
        ),
    ):
        ids = run_factory(retention_store)
        project_id = ids.project
        labels[ids.run] = (
            f"run_archived={run_archived};snapshot={snapshot_state};"
            f"build={build_state}"
        )
        with Session(retention_store.engine) as session:
            run = session.get(PipelineRunSchema, ids.run)
            snapshot = session.get(PipelineSnapshotSchema, ids.snapshot)
            assert run is not None and snapshot is not None
            if run_archived:
                run.archive_bundle_id = uuid4()
            if snapshot_state == "missing":
                run.snapshot_id = None
            elif snapshot_state == "cold":
                snapshot.archive_bundle_id = uuid4()
            if build_state != "missing":
                build = PipelineBuildSchema(
                    project_id=ids.project,
                    stack_id=stack_id
                    if build_state in {"local_stack", "remote_stack"}
                    else None,
                    images="{}",
                    is_local=build_state.startswith("local"),
                    contains_code=True,
                )
                session.add(build)
                session.flush()
                snapshot.build_id = build.id
            session.add_all([run, snapshot])
            session.commit()

    assert project_id is not None
    templatable = retention_store.list_runs(
        PipelineRunFilter(project=project_id, templatable=True, size=1000)
    )
    not_templatable = retention_store.list_runs(
        PipelineRunFilter(project=project_id, templatable=False, size=1000)
    )
    templatable_labels = {labels[run.id] for run in templatable.items}
    not_templatable_labels = {labels[run.id] for run in not_templatable.items}

    expected_templatable = {
        "run_archived=False;snapshot=hot;build=remote_stack"
    }
    assert templatable_labels == expected_templatable
    assert (
        not_templatable_labels == set(labels.values()) - expected_templatable
    )


def test_step_owner_uses_one_header_only_query(
    retention_store, run_factory
) -> None:
    """Owner authorization excludes run payloads without lazy-load queries."""
    ids = run_factory(retention_store)
    statements = []

    def observe(conn, cursor, statement, parameters, context, many):
        statements.append(statement)

    event.listen(retention_store.engine, "before_cursor_execute", observe)
    try:
        owner = retention_store.get_step_run_owner(ids.consumer)
    finally:
        event.remove(retention_store.engine, "before_cursor_execute", observe)

    assert owner.id == ids.run and owner.project_id == ids.project
    assert owner.metadata is None and owner.resources is None
    assert len(statements) == 1
    statement = statements[0]
    projection = statement.split("FROM", 1)[0]
    assert statement.lower().count(" join ") == 1
    assert all(
        column not in projection
        for column in (
            "pipeline_run.orchestrator_environment",
            "pipeline_run.exception_info",
            "pipeline_run.pipeline_configuration",
            "pipeline_run.client_environment",
        )
    )
