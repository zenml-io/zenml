from datetime import datetime

import pytest
from tests.integration.functional.utils import sample_name

from zenml import (
    PipelineRequest,
    PipelineRunRequest,
    PipelineSnapshotRequest,
    StepRunRequest,
    StepRunUpdate,
)
from zenml.client import Client
from zenml.config.global_config import GlobalConfiguration
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ExecutionStatus, StoreType


def test_heartbeat_rest_functionality():
    if GlobalConfiguration().zen_store.config.type != StoreType.REST:
        pytest.skip("Heartbeat testing requires REST")

    client = Client()

    pipeline_model = client.zen_store.create_pipeline(
        PipelineRequest(
            name=sample_name("pipeline"),
            project=client.active_project.id,
        )
    )

    step_name = sample_name("foo")
    snapshot = client.zen_store.create_snapshot(
        PipelineSnapshotRequest(
            project=client.active_project.id,
            run_name_template=sample_name("foo"),
            pipeline_configuration=PipelineConfiguration(
                name=sample_name("foo")
            ),
            stack=client.active_stack.id,
            pipeline=pipeline_model.id,
            client_version="0.1.0",
            server_version="0.1.0",
            step_configurations={
                step_name: Step(
                    spec=StepSpec(
                        source=Source(
                            module="acme.foo",
                            type=SourceType.INTERNAL,
                        ),
                        upstream_steps=[],
                    ),
                    config=StepConfiguration(name=step_name),
                )
            },
        )
    )
    pr, _ = client.zen_store.get_or_create_run(
        PipelineRunRequest(
            project=client.active_project.id,
            name=sample_name("foo"),
            snapshot=snapshot.id,
            status=ExecutionStatus.RUNNING,
            enable_heartbeat=True,
        )
    )
    step_run = client.zen_store.create_run_step(
        StepRunRequest(
            project=client.active_project.id,
            name=step_name,
            status=ExecutionStatus.RUNNING,
            pipeline_run_id=pr.id,
            start_time=datetime.now(),
        )
    )

    assert step_run.latest_heartbeat is None

    assert (
        client.zen_store.get_run_step(step_run_id=step_run.id).latest_heartbeat
        is None
    )

    hb_response = client.zen_store.update_step_heartbeat(
        step_run_id=step_run.id
    )

    assert hb_response.status == ExecutionStatus.RUNNING
    assert hb_response.latest_heartbeat is not None
    assert hb_response.pipeline_run_status == ExecutionStatus.RUNNING

    assert (
        client.zen_store.get_run_step(step_run_id=step_run.id).latest_heartbeat
        == hb_response.latest_heartbeat
    )

    client.zen_store.update_run_step(
        step_run_id=step_run.id,
        step_run_update=StepRunUpdate(status=ExecutionStatus.COMPLETED),
    )

    with pytest.raises(ValueError):
        client.zen_store.update_step_heartbeat(step_run_id=step_run.id)
