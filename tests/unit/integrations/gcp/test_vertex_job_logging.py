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
"""Tests that Vertex job logs and errors don't expose the ZenML API token."""

import enum
import logging
import sys
from contextlib import nullcontext
from datetime import datetime
from types import ModuleType, SimpleNamespace
from typing import Any, ContextManager, Dict, Iterator
from unittest import mock
from uuid import uuid4

import pytest

from zenml.config.resource_settings import ResourceSettings
from zenml.enums import StackComponentType
from zenml.integrations.gcp.flavors.vertex_step_operator_flavor import (
    VertexStepOperatorConfig,
    VertexStepOperatorSettings,
)

API_TOKEN = "fake-zenml-api-token-0123456789"
ENVIRONMENT = {
    "ZENML_STORE_URL": "https://zenml.example.com",
    "ZENML_STORE_API_TOKEN": API_TOKEN,
}
JOB_NAME = "projects/my-project/locations/europe-west4/customJobs/1"


def _google_cloud_stubs() -> Dict[str, ModuleType]:
    """Build the parts of `google.cloud` that the Vertex modules import.

    Returns:
        Stub modules keyed by their import path.
    """

    class JobState(enum.IntEnum):
        JOB_STATE_QUEUED = 1
        JOB_STATE_PENDING = 2
        JOB_STATE_RUNNING = 3
        JOB_STATE_SUCCEEDED = 4
        JOB_STATE_FAILED = 5
        JOB_STATE_CANCELLING = 6
        JOB_STATE_CANCELLED = 7

    class ServerError(Exception):
        pass

    aiplatform = ModuleType("google.cloud.aiplatform")
    aiplatform.gapic = SimpleNamespace(  # type: ignore[attr-defined]
        AcceleratorType=enum.Enum("AcceleratorType", ["NVIDIA_TESLA_T4"]),
        JobServiceClient=type("JobServiceClient", (), {}),
    )
    job_state = ModuleType("google.cloud.aiplatform_v1.types.job_state")
    job_state.JobState = JobState  # type: ignore[attr-defined]
    exceptions = ModuleType("google.api_core.exceptions")
    exceptions.ServerError = ServerError  # type: ignore[attr-defined]

    return {
        "google.cloud": ModuleType("google.cloud"),
        "google.cloud.aiplatform": aiplatform,
        "google.cloud.aiplatform_v1": ModuleType("google.cloud.aiplatform_v1"),
        "google.cloud.aiplatform_v1.types": ModuleType(
            "google.cloud.aiplatform_v1.types"
        ),
        "google.cloud.aiplatform_v1.types.job_state": job_state,
        "google.api_core": ModuleType("google.api_core"),
        "google.api_core.exceptions": exceptions,
    }


@pytest.fixture
def vertex_modules() -> Iterator[SimpleNamespace]:
    """Import the Vertex modules, stubbing `google.cloud` if it's missing.

    Yields:
        The Vertex step operator, constants and utils modules.
    """
    google_cloud: ContextManager[Any]
    try:
        import google.cloud.aiplatform  # noqa: F401

        google_cloud = nullcontext()
    except ImportError:
        # `patch.dict` also unloads the ZenML modules imported against the
        # stubs, so later tests can't pick them up.
        google_cloud = mock.patch.dict(sys.modules, _google_cloud_stubs())

    with google_cloud:
        from zenml.integrations.gcp import constants, utils
        from zenml.integrations.gcp.step_operators import (
            vertex_step_operator,
        )

        yield SimpleNamespace(
            constants=constants,
            utils=utils,
            vertex_step_operator=vertex_step_operator,
        )


def test_vertex_step_operator_submit_does_not_log_environment_values(
    vertex_modules: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The debug logs of a submission don't contain environment values.

    Args:
        vertex_modules: The imported Vertex modules.
        caplog: The log capture fixture.
    """
    vertex_step_operator = vertex_modules.vertex_step_operator
    operator_class = vertex_step_operator.VertexStepOperator
    step_operator = operator_class(
        name="vertex",
        id=uuid4(),
        config=VertexStepOperatorConfig(region="europe-west4"),
        flavor="gcp",
        type=StackComponentType.STEP_OPERATOR,
        user=uuid4(),
        created=datetime.now(),
        updated=datetime.now(),
    )
    client = mock.MagicMock()
    # The returned job's repr includes the spec it was created from.
    client.create_custom_job.side_effect = lambda parent, custom_job: (
        SimpleNamespace(name=JOB_NAME, job_spec=custom_job)
    )
    info = mock.MagicMock()
    info.config.resource_settings = ResourceSettings()
    info.get_image.return_value = "gcr.io/my-project/zenml:latest"

    with (
        mock.patch.object(
            operator_class, "get_job_service_client", return_value=client
        ),
        mock.patch.object(
            operator_class,
            "get_settings",
            return_value=VertexStepOperatorSettings(),
        ),
        mock.patch.object(
            operator_class,
            "gcp_project_id",
            new_callable=mock.PropertyMock,
            return_value="my-project",
        ),
        mock.patch.object(vertex_step_operator, "publish_step_run_metadata"),
        caplog.at_level(logging.DEBUG, logger=vertex_step_operator.__name__),
    ):
        step_operator.submit(
            info=info,
            entrypoint_command=["python", "-m", "zenml.entrypoints"],
            environment=ENVIRONMENT,
        )

    assert API_TOKEN not in caplog.text
    assert "ZENML_STORE_API_TOKEN" in caplog.text

    submitted_job = client.create_custom_job.call_args.kwargs["custom_job"]
    container_spec = submitted_job["job_spec"]["worker_pool_specs"][0][
        "container_spec"
    ]
    assert {
        "name": "ZENML_STORE_API_TOKEN",
        "value": API_TOKEN,
    } in container_spec["env"]


def test_monitor_job_failure_does_not_expose_environment_values(
    vertex_modules: SimpleNamespace,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """A failed job's error log and exception don't contain env values.

    Args:
        vertex_modules: The imported Vertex modules.
        caplog: The log capture fixture.
    """
    utils = vertex_modules.utils
    failed_job = SimpleNamespace(
        name=JOB_NAME,
        job_spec={"env": ENVIRONMENT},
        state=vertex_modules.constants.VERTEX_JOB_STATES_FAILED[0],
        error=SimpleNamespace(
            message="The replica workerpool0-0 exited with status 1."
        ),
    )
    client = mock.MagicMock()
    client.get_custom_job.return_value = failed_job

    with (
        mock.patch.object(utils.time, "sleep"),
        caplog.at_level(logging.DEBUG, logger=utils.__name__),
        pytest.raises(RuntimeError) as exc_info,
    ):
        utils.monitor_job(job_id=JOB_NAME, get_client=lambda: client)

    assert API_TOKEN not in caplog.text
    assert "exited with status 1" in caplog.text

    error_message = str(exc_info.value)
    assert API_TOKEN not in error_message
    assert "exited with status 1" in error_message
    assert "JOB_STATE_FAILED" in error_message
