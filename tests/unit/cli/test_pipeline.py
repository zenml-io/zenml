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
import os
import subprocess

from click.testing import CliRunner

from zenml.cli.pipeline import pipeline
from zenml.enums import ExecutionStatus
from zenml.repository import Repository

PIPELINE_NAME = "some_pipe"
STEP_NAME = "some_step"
MATERIALIZER_NAME = "SomeMaterializer"
CUSTOM_OBJ_NAME = "SomeObj"


def test_pipeline_run_single_file(
    clean_repo: Repository, files_dir: str
) -> None:
    """Test that zenml pipeline run works as expected when the pipeline, its
    steps and materializers are all in the same file."""
    os.chdir(files_dir)
    clean_repo.activate_root()

    # Run Pipeline using subprocess as runner.invoke seems to have issues with
    #  pytest https://github.com/pallets/click/issues/824,
    #  https://github.com/pytest-dev/pytest/issues/3344
    subprocess.check_call(
        ["zenml", "pipeline", "run", "run.py", "-c", "config.yaml"]
    )

    # Assert that the pipeline ran successfully
    historic_pipeline = Repository().get_pipeline(pipeline_name=PIPELINE_NAME)

    assert len(historic_pipeline.runs) == 1

    assert historic_pipeline.runs[-1].status == ExecutionStatus.COMPLETED


def test_pipeline_run_multifile(clean_repo: Repository, files_dir: str) -> None:
    """Test that zenml pipeline run works as expected when the pipeline, its
    steps and materializers are all in the different files.

    This test creates a project with the following structure.
    |custom_obj_file
    |   |--custom_obj_file.py
    |materializer_file
    |   |--materializer_file.py
    |step_file
    |   |--step_file.py
    |config.yaml
    |run.py
    """
    os.chdir(files_dir)
    clean_repo.activate_root()

    # Run Pipeline using subprocess as runner.invoke seems to have issues with
    #  pytest https://github.com/pallets/click/issues/824,
    #  https://github.com/pytest-dev/pytest/issues/3344
    subprocess.check_call(
        ["zenml", "pipeline", "run", "run.py", "-c", "config.yaml"]
    )

    # Assert that pipeline completed successfully
    historic_pipeline = Repository().get_pipeline(pipeline_name=PIPELINE_NAME)

    assert len(historic_pipeline.runs) == 1

    assert historic_pipeline.runs[-1].status == ExecutionStatus.COMPLETED
