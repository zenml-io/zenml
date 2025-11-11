#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
from datetime import datetime, timedelta
from uuid import uuid4

from zenml.enums import StackComponentType
from zenml.orchestrators import (
    LocalDockerOrchestratorConfig,
    LocalDockerOrchestratorFlavor,
)


def test_local_docker_orchestrator_flavor_attributes():
    """Tests that the basic attributes of the local docker orchestrator flavor
    are set correctly."""

    flavor = LocalDockerOrchestratorFlavor()
    assert flavor.type == StackComponentType.ORCHESTRATOR
    assert flavor.name == "local_docker"


def test_local_docker_orchestrator_is_schedulable():
    """Tests that the local docker orchestrator is marked as schedulable."""

    config = LocalDockerOrchestratorConfig()
    assert config.is_schedulable is True


def test_local_docker_orchestrator_scheduler_initialization():
    """Tests that the scheduler is properly initialized."""
    from zenml.orchestrators.local_docker.local_docker_scheduler import (
        LocalDockerOrchestratorScheduler,
    )

    orchestrator_id = uuid4()
    scheduler = LocalDockerOrchestratorScheduler()
    scheduler.start(orchestrator_id)

    assert scheduler._scheduler is not None
    assert scheduler._scheduler.running is True

    scheduler.stop()
    assert scheduler._scheduler.running is False


def test_scheduler_add_cron_schedule():
    """Tests adding a schedule with a cron expression."""
    from zenml.models import (
        ScheduleResponse,
        ScheduleResponseBody,
        ScheduleResponseMetadata,
        ScheduleResponseResources,
    )
    from zenml.orchestrators.local_docker.local_docker_scheduler import (
        LocalDockerOrchestratorScheduler,
    )

    orchestrator_id = uuid4()
    scheduler = LocalDockerOrchestratorScheduler()
    scheduler.start(orchestrator_id)

    # Create a mock schedule with a cron expression
    schedule_id = uuid4()
    schedule = ScheduleResponse(
        id=schedule_id,
        name="test_cron_schedule",
        body=ScheduleResponseBody(
            active=True,
            cron_expression="0 0 * * *",  # Daily at midnight
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        ),
        metadata=ScheduleResponseMetadata(
            pipeline_id=uuid4(),
            orchestrator_id=orchestrator_id,
        ),
        resources=ScheduleResponseResources(),
    )

    scheduler.add_schedule(schedule)

    # Verify the job was added
    jobs = scheduler.list_jobs()
    assert str(schedule_id) in jobs
    assert jobs[str(schedule_id)]["name"] == "test_cron_schedule"

    scheduler.stop()


def test_scheduler_add_interval_schedule():
    """Tests adding a schedule with an interval."""
    from zenml.models import (
        ScheduleResponse,
        ScheduleResponseBody,
        ScheduleResponseMetadata,
        ScheduleResponseResources,
    )
    from zenml.orchestrators.local_docker.local_docker_scheduler import (
        LocalDockerOrchestratorScheduler,
    )

    orchestrator_id = uuid4()
    scheduler = LocalDockerOrchestratorScheduler()
    scheduler.start(orchestrator_id)

    # Create a mock schedule with an interval
    schedule_id = uuid4()
    schedule = ScheduleResponse(
        id=schedule_id,
        name="test_interval_schedule",
        body=ScheduleResponseBody(
            active=True,
            start_time=datetime.utcnow(),
            interval_second=timedelta(hours=1),
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        ),
        metadata=ScheduleResponseMetadata(
            pipeline_id=uuid4(),
            orchestrator_id=orchestrator_id,
        ),
        resources=ScheduleResponseResources(),
    )

    scheduler.add_schedule(schedule)

    # Verify the job was added
    jobs = scheduler.list_jobs()
    assert str(schedule_id) in jobs

    scheduler.stop()


def test_scheduler_update_schedule():
    """Tests updating an existing schedule."""
    from zenml.models import (
        ScheduleResponse,
        ScheduleResponseBody,
        ScheduleResponseMetadata,
        ScheduleResponseResources,
    )
    from zenml.orchestrators.local_docker.local_docker_scheduler import (
        LocalDockerOrchestratorScheduler,
    )

    orchestrator_id = uuid4()
    scheduler = LocalDockerOrchestratorScheduler()
    scheduler.start(orchestrator_id)

    # Create and add a schedule
    schedule_id = uuid4()
    schedule = ScheduleResponse(
        id=schedule_id,
        name="test_schedule",
        body=ScheduleResponseBody(
            active=True,
            cron_expression="0 0 * * *",
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        ),
        metadata=ScheduleResponseMetadata(
            pipeline_id=uuid4(),
            orchestrator_id=orchestrator_id,
        ),
        resources=ScheduleResponseResources(),
    )

    scheduler.add_schedule(schedule)

    # Update the schedule to be inactive
    updated_schedule = ScheduleResponse(
        id=schedule_id,
        name="test_schedule",
        body=ScheduleResponseBody(
            active=False,
            cron_expression="0 0 * * *",
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        ),
        metadata=ScheduleResponseMetadata(
            pipeline_id=uuid4(),
            orchestrator_id=orchestrator_id,
        ),
        resources=ScheduleResponseResources(),
    )

    scheduler.update_schedule(updated_schedule)

    # Verify the job was removed
    jobs = scheduler.list_jobs()
    assert str(schedule_id) not in jobs

    scheduler.stop()


def test_scheduler_delete_schedule():
    """Tests deleting a schedule."""
    from zenml.models import (
        ScheduleResponse,
        ScheduleResponseBody,
        ScheduleResponseMetadata,
        ScheduleResponseResources,
    )
    from zenml.orchestrators.local_docker.local_docker_scheduler import (
        LocalDockerOrchestratorScheduler,
    )

    orchestrator_id = uuid4()
    scheduler = LocalDockerOrchestratorScheduler()
    scheduler.start(orchestrator_id)

    # Create and add a schedule
    schedule_id = uuid4()
    schedule = ScheduleResponse(
        id=schedule_id,
        name="test_schedule",
        body=ScheduleResponseBody(
            active=True,
            cron_expression="0 0 * * *",
            created=datetime.utcnow(),
            updated=datetime.utcnow(),
        ),
        metadata=ScheduleResponseMetadata(
            pipeline_id=uuid4(),
            orchestrator_id=orchestrator_id,
        ),
        resources=ScheduleResponseResources(),
    )

    scheduler.add_schedule(schedule)

    # Delete the schedule
    scheduler.delete_schedule(schedule_id)

    # Verify the job was removed
    jobs = scheduler.list_jobs()
    assert str(schedule_id) not in jobs

    scheduler.stop()


def test_scheduler_singleton():
    """Tests that the scheduler is a singleton."""
    from zenml.orchestrators.local_docker.local_docker_scheduler import (
        LocalDockerOrchestratorScheduler,
    )

    scheduler1 = LocalDockerOrchestratorScheduler()
    scheduler2 = LocalDockerOrchestratorScheduler()

    assert scheduler1 is scheduler2
