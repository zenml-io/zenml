#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
import logging
import os
import shutil
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Generator, List, Optional, Set, Tuple

import pytest

from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.models import PipelineRunResponse
from zenml.utils.pagination_utils import depaginate

if TYPE_CHECKING:
    from uuid import UUID

    from zenml.models import PipelineBuildResponse, PipelineResponse


DEFAULT_PIPELINE_RUN_START_TIMEOUT = 30
DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT = 300


class IntegrationTestExample:
    """Encapsulates an integration test example, providing methods to run it.

    Attributes:
        name: The name of the example.
        path: The file system path to the example's directory.
        run_dot_py_file: The full path to the `run.py` script of the example.
    """

    def __init__(self, path: Path, name: str) -> None:
        """Initializes an IntegrationTestExample instance.

        Args:
            path: The file system path to the example's directory.
            name: The name of the example.

        Raises:
            RuntimeError: If a `run.py` file is not found in the example's
                directory.
        """
        self.name = name
        self.path = path

        # Make sure the example has a `run.py` file
        self.run_dot_py_file = os.path.join(self.path, "run.py")
        if not os.path.exists(self.run_dot_py_file):
            raise RuntimeError(
                f"No `run.py` file found in example {self.name}. "
                f"{self.run_dot_py_file} does not exist."
            )

    def __call__(self, *args: str) -> None:
        """Runs the example's `run.py` script.

        This method executes the `run.py` script associated with the example,
        passing any provided arguments to it. The script is run in the
        context of the example's directory.

        Args:
            *args: A variable number of string arguments to pass to the
                `run.py` script.

        Raises:
            RuntimeError: If the execution of the `run.py` script fails.
        """
        subprocess.check_call(
            [sys.executable, self.run_dot_py_file, *args],
            cwd=str(self.path),
            env=os.environ.copy(),
        )


def copy_example_files(example_dir: str, dst_dir: str) -> None:
    """Copies files from an example directory to a destination directory.

    This function iterates over all items in the `example_dir`. If an item
    is a directory, it's recursively copied. If it's a file, it's copied
    directly. The '.zen' directory (ZenML repository) is explicitly skipped
    to avoid conflicts or unintended behavior.

    Args:
        example_dir: The source directory from which to copy files.
        dst_dir: The destination directory to which files will be copied.
    """
    for item in os.listdir(example_dir):
        if item == ".zen":
            # don't copy any existing ZenML repository
            continue

        s = os.path.join(example_dir, item)
        d = os.path.join(dst_dir, item)
        if os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)


@contextmanager
def run_example(
    request: pytest.FixtureRequest,
    name: str,
    example_args: Optional[List[str]] = None,
    pipelines: Optional[Dict[str, Tuple[int, int]]] = None,
    timeout_limit: int = DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT,
    is_public_example: bool = False,
) -> Generator[Dict[str, List[PipelineRunResponse]], None, None]:
    """Context manager to run a ZenML example and validate its execution.

    This function prepares the environment for running an example by copying its
    files to the current working directory. It then executes the example's
    `run.py` script. After execution, it can validate pipeline runs and
    perform cleanup operations like deleting created pipelines and Docker
    resources.

    Args:
        request: The pytest FixtureRequest object, used to access test
            configuration and context.
        name: The name of the example (corresponds to its directory name).
        example_args: A list of additional string arguments to pass to the
            example's `run.py` script.
        pipelines: A dictionary mapping pipeline names to a tuple of
            (expected_run_count, expected_step_count). This is used to
            validate the number of runs and steps for specified pipelines
            after the example has executed.
        timeout_limit: The maximum time in seconds to wait for pipeline runs
            to finish during validation.
        is_public_example: A boolean indicating whether the example is a public
            example (located in `examples/`) or an integration test-specific
            example (located in `tests/integration/examples/`).

    Yields:
        Dict[str, List[PipelineRunResponse]]: A dictionary mapping pipeline
            names to a list of their corresponding pipeline run responses that
            were executed and validated.
    """
    # Copy all example files into the repository directory
    if is_public_example:  # examples/<name>
        examples_directory = str(Path(__file__).parents[3] / "examples" / name)
    else:  # tests/integration/examples/<name>
        examples_directory = str(Path(__file__).parents[0] / name)
    dst_dir = Path(os.getcwd())
    copy_example_files(examples_directory, str(dst_dir))

    # Get the existing pipelines and builds
    existing_pipeline_ids = {pipe.id for pipe in get_pipelines()}
    existing_build_ids = {build.id for build in get_builds()}
    now = datetime.utcnow()

    # Run the example
    example = IntegrationTestExample(name=name, path=dst_dir)
    example_args = example_args or []
    example(*example_args)

    # Validate the pipelines
    runs = wait_and_validate_pipeline_runs(
        pipelines=pipelines,
        older_than=now,
        timeout_limit=timeout_limit,
    )

    yield runs

    pipeline_names = list(pipelines.keys()) if pipelines else []
    cleanup_pipelines(existing_pipeline_ids, pipeline_names)

    if request.config.getoption("cleanup_docker", False):
        cleanup_docker_files(existing_build_ids)


def get_pipelines() -> List["PipelineResponse"]:
    """Fetches all pipelines from the ZenML server.

    Returns:
        A list of PipelineResponse objects representing the pipelines.
    """
    from zenml.client import Client

    client = Client()
    return depaginate(list_method=client.list_pipelines)


def get_builds() -> List["PipelineBuildResponse"]:
    """Fetches all pipeline builds from the ZenML server.

    Returns:
        A list of PipelineBuildResponse objects representing the builds.
    """
    from zenml.client import Client

    client = Client()
    return depaginate(list_method=client.list_builds)


def wait_and_validate_pipeline_runs(
    pipelines: Optional[Dict[str, Tuple[int, int]]] = None,
    older_than: Optional[datetime] = None,
    timeout_limit: int = DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT,
) -> Dict[str, List[PipelineRunResponse]]:
    """Waits for specified pipeline runs to complete and validates them.

    This function iterates through a dictionary of pipelines, waiting for each
    to meet its expected run and step counts within a given timeout.

    Args:
        pipelines: A dictionary where keys are pipeline names and values are
            tuples of (expected_run_count, expected_step_count).
        older_than: If provided, only pipeline runs created after this
            datetime will be considered.
        timeout_limit: The maximum time in seconds to wait for all specified
            pipeline runs to finish.

    Returns:
        A dictionary mapping pipeline names to a list of their validated
        PipelineRunResponse objects.
    """
    pipelines = pipelines or {}
    runs: Dict[str, List[PipelineRunResponse]] = {}
    for pipeline_name, (run_count, step_count) in pipelines.items():
        runs[pipeline_name] = wait_and_validate_pipeline_run(
            pipeline_name=pipeline_name,
            run_count=run_count,
            step_count=step_count,
            older_than=older_than,
            finish_timeout=timeout_limit,
        )
    return runs


def wait_and_validate_pipeline_run(
    pipeline_name: str,
    run_count: Optional[int] = None,
    step_count: Optional[int] = None,
    older_than: Optional[datetime] = None,
    start_timeout: int = DEFAULT_PIPELINE_RUN_START_TIMEOUT,
    finish_timeout: int = DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT,
    poll_period: int = 10,
) -> List[PipelineRunResponse]:
    """Waits for and validates a specific pipeline's runs.

    This function ensures that a named pipeline is registered in ZenML. It then
    polls for a specified number of runs of this pipeline to be recorded and to
    reach a finished status (e.g., COMPLETED). It also checks if the runs
    have the expected number of steps.

    Args:
        pipeline_name: The name of the pipeline to verify.
        run_count: The expected number of pipeline runs to find and validate.
            If None or 0, the function returns an empty list.
        step_count: The expected number of steps in each validated pipeline run.
            If None, this check is skipped.
        older_than: If provided, only pipeline runs created at or after this
            datetime will be considered. This helps filter out older,
            irrelevant runs.
        start_timeout: The maximum time in seconds to wait for the expected
            number of pipeline runs to be recorded (i.e., appear in the system).
            If 0 or negative, this check is skipped.
        finish_timeout: The maximum time in seconds to wait for each recorded
            pipeline run to reach a finished status.
        poll_period: The interval in seconds at which to poll for pipeline run
            status updates.

    Returns:
        A list of PipelineRunResponse objects for the validated pipeline runs.
        The list will contain up to `run_count` runs.

    Raises:
        AssertionError: If the pipeline is not found, if the expected number
            of runs are not recorded within `start_timeout`, if runs do not
            finish within `finish_timeout`, if a run's status is not
            COMPLETED, or if a run does not have `step_count` steps (if provided).
    """
    # Not all orchestrators support synchronous execution, and some may not
    # even be configured to do that. In other cases, we may have to wait for
    # scheduled pipeline runs. So we need to poll for `run_count` pipeline
    # runs older than the supplied timestamp to be recorded and finish before
    # we can validate them.

    pipeline = Client().get_pipeline(pipeline_name)
    assert pipeline

    if not run_count:
        return []

    runs: List[PipelineRunResponse]] = []

    # Wait for all pipeline runs to be recorded and complete. We assume the
    # runs will be executed in sequence, so we wait for an increasing number
    # of runs to be recorded and complete.
    for run_no in range(1, run_count + 1):
        logging.info(f"Waiting for {run_no} pipeline runs to complete...")

        # Wait for the current number of runs (run_no) to be recorded for
        # a maximum of `start_timeout` seconds
        wait_start = start_timeout
        while True:
            logging.debug(
                f"Waiting for {run_no} pipeline runs to be recorded..."
            )

            runs = pipeline.runs[:run_no]

            if older_than is not None:
                runs = [r for r in runs if r.created >= older_than]

            if len(runs) >= run_no:
                # We have at least `run_no` runs recorded
                break
            if wait_start <= 0:
                raise AssertionError(
                    f"Timed out waiting for {run_no} pipeline runs to be "
                    f"recorded"
                )
            wait_start -= poll_period
            time.sleep(poll_period)

        # After they are recorded, wait for the current number of runs (run_no)
        # to complete or fail for a maximum of `finish_timeout` seconds
        wait_finish = finish_timeout
        while True:
            logging.debug(f"Waiting for {run_no} pipeline runs to complete...")

            runs = pipeline.runs[:run_no]

            if older_than is not None:
                runs = [r for r in runs if r.created >= older_than]

            runs = [r for r in runs if r.status.is_finished]

            if len(runs) >= run_no:
                # We have at least `run_no` runs completed or failed
                break
            if wait_finish <= 0:
                raise AssertionError(
                    f"Timed out waiting for {run_no} pipeline runs to be "
                    f"completed or failed"
                )
            wait_finish -= poll_period
            time.sleep(poll_period)

    assert len(runs) >= run_count

    for run in runs[:run_count]:
        assert run.status == ExecutionStatus.COMPLETED
        if step_count:
            assert len(run.steps) == step_count

    return runs[:run_count]


def cleanup_pipelines(
    existing_pipeline_ids: Set["UUID"],
    pipeline_names: List[str],
) -> None:
    """Removes pipelines created during a test run.

    This function identifies pipelines that were created during the current
    test session (i.e., their IDs are not in `existing_pipeline_ids`) and
    whose names are in `pipeline_names`. These pipelines are then deleted
    from the ZenML server to ensure a clean state for subsequent tests.

    Args:
        existing_pipeline_ids: A set of pipeline IDs that existed before the
            current test session started.
        pipeline_names: A list of names of pipelines that were potentially
            created by the current test.
    """
    client = Client()
    pipelines = get_pipelines()
    for pipeline in pipelines:
        if (
            pipeline.id not in existing_pipeline_ids
            and pipeline.name in pipeline_names
        ):
            client.delete_pipeline(pipeline.id)


def cleanup_docker_files(existing_build_ids: Set["UUID"]) -> None:
    """Cleans up Docker resources created during a test run.

    This function identifies Docker images associated with pipeline builds
    that were created during the current test session. It then attempts to
    prune unused Docker containers and volumes, and remove the identified
    Docker images to free up system resources.

    Args:
        existing_build_ids: A set of pipeline build IDs that existed before the
            current test session started. This is used to identify builds
            created by the current test.
    """
    builds = get_builds()

    image_names = set()
    for build in builds:
        if build.id in existing_build_ids:
            continue

        image_names.update(item.image for item in build.images.values())

    try:
        from docker.client import DockerClient
        from docker.errors import ImageNotFound

        # Try to ping Docker, to see if it's installed and running
        docker_client = DockerClient.from_env()
        docker_client.ping()
    except Exception:
        # Docker is not installed or running
        pass
    else:
        docker_client.containers.prune()
        docker_client.volumes.prune()
        for image_name in image_names:
            try:
                logging.debug(f"Removing Docker image {image_name}")
                image = docker_client.images.get(image_name)
                docker_client.images.remove(image.id, force=True)
            except ImageNotFound:
                pass

        docker_client.images.prune()
