# Copyright (c) ZenML GmbH 2026. All Rights Reserved.
"""Regression coverage for shared execution-retention source policies."""

import json
from uuid import UUID

import pytest
from sqlmodel import Session

from zenml.zen_stores.schemas import (
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
