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
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, Generator, List, Optional, Tuple

import pytest

from zenml.cli import EXAMPLES_RUN_SCRIPT, SHELL_EXECUTABLE, LocalExample
from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.models.pipeline_run_models import PipelineRunResponseModel
from zenml.utils.pagination_utils import depaginate

DEFAULT_PIPELINE_RUN_START_TIMEOUT = 30
DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT = 300


def copy_example_files(example_dir: str, dst_dir: str) -> None:
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


def example_runner(examples_dir: Path) -> List[str]:
    """Get the executable that runs examples.

    By default, returns the path to an executable .sh file in the
    repository, but can also prefix that with the path to a shell
    / interpreter when the file is not executable on its own. The
    latter option is needed for Windows compatibility.
    """
    return (
        [os.environ[SHELL_EXECUTABLE]]
        if SHELL_EXECUTABLE in os.environ
        else []
    ) + [str(examples_dir / EXAMPLES_RUN_SCRIPT)]


@contextmanager
def run_example(
    request: pytest.FixtureRequest,
    name: str,
    example_args: Optional[List[str]] = None,
    pipelines: Optional[Dict[str, Tuple[int, int]]] = None,
    timeout_limit: int = DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT,
    # pipeline_name: Optional[str] = None,
    # run_count: Optional[int] = None,
    # step_count: Optional[int] = None,
) -> Generator[
    Tuple[LocalExample, Dict[str, List[PipelineRunResponseModel]]], None, None
]:
    """Runs the given example and validates it ran correctly.

    Args:
        request: The pytest request object.
        name: The name (=directory name) of the example.
        example_args: Additional arguments to pass to the example
        pipelines: Validate that the pipelines were executed during the example
            run. Maps pipeline names to a Tuple (run_count, step_count) that
            specifies the expected number of runs (and their steps) to validate.
        timeout_limit: The maximum time to wait for the pipeline run to finish.

    Yields:
        The example and the pipeline runs that were executed and validated.
    """
    from zenml.client import Client

    # Root directory of all checked out examples
    examples_directory = Path(__file__).parents[3] / "examples"

    dst_dir = Path(os.getcwd())

    # Copy all example files into the repository directory
    copy_example_files(str(examples_directory / name), str(dst_dir))

    client = Client()
    existing_pipeline_ids = {
        pipeline.id
        for pipeline in depaginate(list_method=client.list_pipelines)
    }
    existing_build_ids = {
        build.id for build in depaginate(list_method=client.list_builds)
    }

    now = datetime.utcnow()

    # Run the example
    example = LocalExample(name=name, path=dst_dir, skip_manual_check=True)
    example_args = example_args or []
    example.run_example_directly(*example_args)

    pipelines = pipelines or {}
    runs: Dict[str, List[PipelineRunResponseModel]] = {}
    for pipeline_name, (run_count, step_count) in pipelines.items():
        runs[pipeline_name] = wait_and_validate_pipeline_run(
            pipeline_name=pipeline_name,
            run_count=run_count,
            step_count=step_count,
            older_than=now,
            finish_timeout=timeout_limit,
        )

    yield example, runs

    # Cleanup registered pipelines so they don't cause trouble in future
    # example runs
    for pipeline in depaginate(list_method=client.list_pipelines):
        if (
            pipeline.id not in existing_pipeline_ids
            and pipeline_name in pipelines
        ):
            client.delete_pipeline(pipeline.id)

    cleanup_docker = request.config.getoption("cleanup_docker", False)

    if cleanup_docker:
        # Clean up more expensive resources like docker containers, volumes and
        # images, if any were created.
        image_names = set()
        for build in depaginate(list_method=client.list_builds):
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


def wait_and_validate_pipeline_run(
    pipeline_name: str,
    run_count: Optional[int] = None,
    step_count: Optional[int] = None,
    older_than: Optional[datetime] = None,
    start_timeout: int = DEFAULT_PIPELINE_RUN_START_TIMEOUT,
    finish_timeout: int = DEFAULT_PIPELINE_RUN_FINISH_TIMEOUT,
    poll_period: int = 10,
) -> List[PipelineRunResponseModel]:
    """A basic example validation function.

    This function makes sure that a pipeline is registered and optionally waits
    until a number of pipeline runs have executed by checking the run status as
    well as making sure all steps were executed.

    Args:
        pipeline_name: The name of the pipeline to verify.
        run_count: The amount of pipeline runs to verify.
        step_count: The amount of steps inside the pipeline.
        older_than: Only look at runs older than this datetime. If not supplied
            all runs will be checked.
        start_timeout: The timeout in seconds to wait for a single pipeline run
            to be recorded. Set to 0 or a negative number to disable.
        finish_timeout: The timeout in seconds to wait for a single pipeline run
            to finish.
        poll_period: The period in seconds to wait between polling the pipeline
            run status.

    Returns:
        A list of pipeline runs that were validated.

    Raises:
        AssertionError: If the validation failed.
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

    runs: List[PipelineRunResponseModel] = []

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

            runs = [r for r in runs if r.status != ExecutionStatus.RUNNING]

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
