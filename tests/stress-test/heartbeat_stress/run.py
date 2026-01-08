import time
from datetime import datetime
from uuid import UUID

from tests.integration.functional.utils import sample_name
from tqdm import tqdm

from zenml import (
    PipelineRequest,
    PipelineRunRequest,
    PipelineSnapshotRequest,
    ProjectFilter,
    StackFilter,
    StepRunRequest,
    UserFilter,
)
from zenml.client import Client
from zenml.config.pipeline_configurations import PipelineConfiguration
from zenml.config.pipeline_spec import PipelineSpec
from zenml.config.source import Source, SourceType
from zenml.config.step_configurations import Step, StepConfiguration, StepSpec
from zenml.enums import ExecutionStatus
from zenml.steps import StepHeartbeatWorker
from zenml.zen_stores.sql_zen_store import (
    SqlZenStore,
    SqlZenStoreConfiguration,
)


class StatTrackingWorker(StepHeartbeatWorker):
    def __init__(self, step_id: UUID):
        super().__init__(step_id)

        self.executions = []

    def _heartbeat(self):
        try:
            st = time.time()

            super()._heartbeat()

            end = time.time()

            print(f"PING WITH WORKER {self.name} lasted {round(end - st, 2)}")

            self.executions.append({"time": time.time() - st})

        except Exception as e:
            print(e)


def populate_database(num_running_steps: int = 10):
    store = SqlZenStore(
        config=SqlZenStoreConfiguration(
            url="mysql://root:password@localhost:3306/zenml"
        ),
        skip_migrations=True,
    )

    print(store.list_projects(project_filter_model=ProjectFilter()))
    print(store.list_users(user_filter_model=UserFilter()))

    store._default_user = store.list_users(user_filter_model=UserFilter())[0]

    default_project = store.get_project("default")
    default_stack = store.list_stacks(
        stack_filter_model=StackFilter(name="default")
    )[0]

    pipeline = store.create_pipeline(
        pipeline=PipelineRequest(
            project=default_project.id,
            name=sample_name("stress-heartbeat-pipeline"),
            tags=["stress", "heartbeat"],
        )
    )

    snapshot = store.create_snapshot(
        PipelineSnapshotRequest(
            project=default_project.id,
            run_name_template=sample_name("stress-heartbeat-pipeline"),
            pipeline_configuration=PipelineConfiguration(
                name=sample_name("foo"),
                enable_heartbeat=True,
            ),
            stack=default_stack.id,
            pipeline=pipeline.id,
            client_version="0.1.0",
            server_version="0.1.0",
            pipeline_spec=PipelineSpec(
                steps=[
                    StepSpec(
                        source=Source(
                            module="acme.foo",
                            type=SourceType.INTERNAL,
                        ),
                        upstream_steps=["hb_step_0"] if index != 0 else [],
                        enable_heartbeat=True,
                        invocation_id=f"hb_step_{index}",
                    )
                    for index in range(num_running_steps)
                ]
            ),
            step_configurations={
                f"hb_step_{index}": Step(
                    spec=StepSpec(
                        source=Source(
                            module="acme.foo",
                            type=SourceType.INTERNAL,
                        ),
                        upstream_steps=["hb_step_0"] if index != 0 else [],
                        enable_heartbeat=True,
                        invocation_id=f"hb_step_{index}",
                    ),
                    config=StepConfiguration(
                        name=f"hb_step_{index}", heartbeat_healthy_threshold=10
                    ),
                    step_config_overrides=StepConfiguration(
                        name=f"hb_step_{index}"
                    ),
                )
                for index in range(num_running_steps)
            },
            is_dynamic=False,
        )
    )

    pr, _ = store.get_or_create_run(
        PipelineRunRequest(
            project=default_project.id,
            name=sample_name("stress-heartbeat-pipeline"),
            snapshot=snapshot.id,
            status=ExecutionStatus.RUNNING,
        )
    )

    for index in range(num_running_steps):
        store.create_run_step(
            StepRunRequest(
                project=default_project.id,
                name=f"hb_step_{index}",
                status=ExecutionStatus.RUNNING,
                pipeline_run_id=pr.id,
                start_time=datetime.now(),
            )
        )

    return pipeline.id, snapshot.id, pr.id


def check_heartbeat_worker_stats(pipeline_run_id: UUID):
    client = Client()

    print(client.zen_store.url)

    workers = []

    for step in tqdm(
        client.list_run_steps(pipeline_run_id=pipeline_run_id, size=2000)
    ):
        worker = StatTrackingWorker(step_id=step.id)
        workers.append(worker)
        worker.start()

    time.sleep(600)

    for worker in workers:
        worker.stop()


def run():
    pid, sid, rid = populate_database(num_running_steps=100)

    check_heartbeat_worker_stats(pipeline_run_id=rid)

    # calculate_token_validity_stats(pipeline_run_id=rid)


if __name__ == "__main__":
    run()
