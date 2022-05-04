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
from pathlib import Path
import os
import shutil
import subprocess
from unittest import skip

from pytest import fixture
from click.testing import CliRunner

from zenml.cli.pipeline import pipeline
from zenml.enums import ExecutionStatus
from zenml.repository import Repository
from zenml.utils import yaml_utils

PIPELINE_NAME = "some_pipe"
STEP_NAME = "some_step"
MATERIALIZER_NAME = "SomeMaterializer"
CUSTOM_OBJ_NAME = "SomeObj"


@fixture
def files_dir(request, tmp_path: Path) -> Path:
    """Fixture that will search for a folder with the same name as the test
    file and move it into the temp path of the test.

    |dir
    |--test_functionality
    |--|--test_specific_method
    |--test_functionality.py#test_specific_method

    In this case if the `test_specific_method()` function inside the
    `test_functionality.py` has this fixture, the
    `test_functionality/test_specific_method` file is copied into the tmp_path.
    The path is passed into the test_specific_method(datadir: str) as string.

    TO use this, ensure the filename (minus '.py') corresponds to the outer
    directory name. And the inner directory corresponds to the test methods
    name.

    Returns:
        tmp_path at which to find the files.
    """
    filename = Path(request.module.__file__)
    test_dir = filename.with_suffix('')

    test_name = request.function.__name__

    tmp_path = tmp_path / test_name

    if os.path.isdir(test_dir):
        test_function_dir = test_dir / test_name
        if os.path.isdir(test_function_dir):
            shutil.copytree(test_function_dir, tmp_path)

    return tmp_path


def test_pipeline_run_single_file(clean_repo: Repository,
                                  files_dir: str) -> None:
    """Test that zenml pipeline run works as expected when the pipeline, its
    steps and materializers are all in the same file."""
    runner = CliRunner()

    os.chdir(files_dir)
    clean_repo.activate_root()
    # Run Pipeline
    runner.invoke(pipeline, ["run", "run.py", "-c", "config.yaml"])

    # Assert that the pipeline ran successfully
    historic_pipeline = Repository().get_pipeline(pipeline_name=PIPELINE_NAME)

    assert len(historic_pipeline.runs) == 1

    assert historic_pipeline.runs[-1].status == ExecutionStatus.COMPLETED


def test_pipeline_run_multifile(clean_repo: Repository,
                                  files_dir: str) -> None:
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
    """ ""
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
