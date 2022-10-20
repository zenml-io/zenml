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
import platform
import subprocess
import sys

import click
import pytest
from click.testing import CliRunner

from zenml.cli.base import clean
from zenml.cli.pipeline import export_pipeline_runs, import_pipeline_runs
from zenml.client import Client
from zenml.enums import ExecutionStatus
from zenml.post_execution.pipeline import get_pipeline

PIPELINE_NAME = "some_pipe"
STEP_NAME = "some_step"
MATERIALIZER_NAME = "SomeMaterializer"
CUSTOM_OBJ_NAME = "SomeObj"


def test_pipeline_run_single_file(clean_client, files_dir: str) -> None:
    """Test that zenml pipeline run works as expected when the pipeline, its
    steps and materializers are all in the same file."""
    clean_sys_modules = sys.modules

    os.chdir(files_dir)
    clean_client.activate_root()
    Client.initialize(root=files_dir)

    assert os.path.isfile(os.path.join(files_dir, "run.py"))
    assert os.path.isfile(os.path.join(files_dir, "config.yaml"))

    # Run Pipeline using subprocess as runner.invoke seems to have issues with
    #  pytest https://github.com/pallets/click/issues/824,
    #  https://github.com/pytest-dev/pytest/issues/3344
    subprocess.check_call(
        ["zenml", "pipeline", "run", "run.py", "-c", "config.yaml"],
        cwd=files_dir,
        shell=click._compat.WIN,
        env=os.environ.copy(),
    )

    # Assert that the pipeline ran successfully
    historic_pipeline = get_pipeline(pipeline_name=PIPELINE_NAME)

    assert len(historic_pipeline.runs) == 1

    assert historic_pipeline.runs[-1].status == ExecutionStatus.COMPLETED

    # Clean up sys modules that were imported in the course of this test
    for mod in sys.modules:
        if mod not in clean_sys_modules:
            del sys.modules[mod]


def test_pipeline_run_multifile(clean_client, files_dir: str) -> None:
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
    clean_sys_modules = sys.modules

    os.chdir(files_dir)
    clean_client.activate_root()
    Client.initialize(root=files_dir)

    assert os.path.isfile(os.path.join(files_dir, "pipeline_file/pipeline.py"))
    assert os.path.isfile(os.path.join(files_dir, "config.yaml"))

    # Run Pipeline using subprocess as runner.invoke seems to have issues with
    #  pytest https://github.com/pallets/click/issues/824,
    #  https://github.com/pytest-dev/pytest/issues/3344
    subprocess.check_output(
        [
            "zenml",
            "pipeline",
            "run",
            "pipeline_file/pipeline.py",
            "-c",
            "config.yaml",
        ],
        cwd=files_dir,
        shell=click._compat.WIN,
        env=os.environ.copy(),
    )

    # Assert that pipeline completed successfully
    historic_pipeline = get_pipeline(pipeline_name=PIPELINE_NAME)

    assert len(historic_pipeline.runs) == 1

    assert historic_pipeline.runs[-1].status == ExecutionStatus.COMPLETED

    # Clean up sys modules that were imported in the course of this test
    for mod in sys.modules:
        if mod not in clean_sys_modules:
            del sys.modules[mod]


# TODO: Fix this test for windows once we have public run delete methods
@pytest.mark.skipif(
    platform.system() == "Windows",
    reason="ZenML clean not supported on Windows.",
)
def test_pipeline_export_delete_import(
    clean_client,
    sample_pipeline_run_model,
    sample_step_model,
    sample_artifact_model,
) -> None:
    """Tests exporting, deleting and importing a pipeline run."""
    sample_pipeline_run_model.project = clean_client.active_project.id
    sample_pipeline_run_model.user = clean_client.active_user.id
    sample_step_model.pipeline_run_id = sample_pipeline_run_model.id
    sample_artifact_model.parent_step_id = sample_step_model.id
    sample_artifact_model.producer_step_id = sample_step_model.id
    clean_client.zen_store.create_run(sample_pipeline_run_model)
    clean_client.zen_store.create_run_step(sample_step_model)
    clean_client.zen_store.create_artifact(sample_artifact_model)
    assert len(clean_client.zen_store.list_runs()) > 0
    assert len(clean_client.zen_store.list_run_steps()) > 0
    assert len(clean_client.zen_store.list_artifacts()) > 0

    # Export pipeline run
    runner = CliRunner()
    file_name = "aria_runs_fast.yaml"
    result = runner.invoke(export_pipeline_runs, [file_name])
    assert result.exit_code == 0
    assert os.path.exists(file_name)

    # Delete everything
    runner.invoke(clean, ["--yes"])
    assert len(clean_client.zen_store.list_runs()) == 0
    assert len(clean_client.zen_store.list_run_steps()) == 0
    assert len(clean_client.zen_store.list_artifacts()) == 0

    # Import pipeline run
    result = runner.invoke(import_pipeline_runs, [file_name])
    assert result.exit_code == 0
    assert len(clean_client.zen_store.list_runs()) > 0
    assert len(clean_client.zen_store.list_run_steps()) > 0
    assert len(clean_client.zen_store.list_artifacts()) > 0
