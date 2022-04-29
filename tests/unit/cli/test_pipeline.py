#  Copyright (c) ZenML GmbH 2020. All Rights Reserved.
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

from click.testing import CliRunner

from zenml.cli.pipeline import pipeline
from zenml.enums import ExecutionStatus
from zenml.repository import Repository
from zenml.utils import yaml_utils

PIPELINE_NAME = "some_pipe"
STEP_NAME = "some_step"
MATERIALIZER_NAME = "SomeMaterializer"
CUSTOM_OBJ_NAME = "SomeObj"

object_definition = f"""
class {CUSTOM_OBJ_NAME}:
    def __init__(self, name: str):
        self.name = name
"""

materializer_definition = f"""
import os
from typing import Type

from zenml.artifacts import DataArtifact
from zenml.io import fileio
from zenml.materializers.base_materializer import BaseMaterializer


class {MATERIALIZER_NAME}(BaseMaterializer):
    ASSOCIATED_TYPES = ({CUSTOM_OBJ_NAME},)
    ASSOCIATED_ARTIFACT_TYPES = (DataArtifact,)

    def handle_input(self, data_type: Type[{CUSTOM_OBJ_NAME}]
                    ) -> {CUSTOM_OBJ_NAME}:
        super().handle_input(data_type)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'),
                         'r') as f:
            name = f.read()
        return {CUSTOM_OBJ_NAME}(name=name)

    def handle_return(self, my_obj: {CUSTOM_OBJ_NAME}) -> None:
        super().handle_return(my_obj)
        with fileio.open(os.path.join(self.artifact.uri, 'data.txt'),
                         'w') as f:
            f.write(my_obj.name)
"""

step_definition = f"""
from zenml.steps import step, Output, BaseStepConfig


class StepConfig(BaseStepConfig):
    some_option: int = 4

@step
def {STEP_NAME}(config: StepConfig) -> Output(output_1={CUSTOM_OBJ_NAME},
                                              output_2=int):
    return {CUSTOM_OBJ_NAME}("Custom-Object"), config.some_option
"""

define_sys_path_definition = """
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
"""

pipeline_definition = f"""
from zenml.pipelines import pipeline

@pipeline(enable_cache=False)
def {PIPELINE_NAME}(
        step_1,
):
    step_1()
"""


def test_pipeline_run_single_file(clean_repo, mocker, tmp_path) -> None:
    """Test that zenml pipeline run works as expected when the pipeline, its
    steps and materializers are all in the same file."""
    runner = CliRunner()

    os.chdir(str(tmp_path))
    Repository.initialize()
    clean_repo.activate_root()

    # Create run.py file with steps, custom object, custom materializer and
    #  pipeline definition
    main_python_file = clean_repo.root / "run.py"
    main_python_file.write_text(
        "\n".join(
            [
                object_definition,
                materializer_definition,
                step_definition,
                pipeline_definition,
            ]
        )
    )

    # Create run config
    run_config = {
        "name": PIPELINE_NAME,
        "steps": {
            "step_1": {
                "source": {"name": STEP_NAME},
                "parameters": {"some_option": 3},
                "materializers": {"output_1": {"name": MATERIALIZER_NAME}},
            }
        },
    }
    config_path = str(clean_repo.root / "config.yaml")
    yaml_utils.write_yaml(config_path, run_config)

    # Run Pipeline
    runner.invoke(pipeline, ["run", "run.py", "-c", "config.yaml"])

    # Assert that the pipeline ran successfully
    historic_pipeline = Repository().get_pipeline(pipeline_name=PIPELINE_NAME)

    assert len(historic_pipeline.runs) == 1

    assert historic_pipeline.runs[-1].status == ExecutionStatus.COMPLETED


def test_pipeline_run_multifile(clean_repo, tmp_path) -> None:
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

    STEP_FILE = "step_file"
    MATERIALIZER_FILE = "materializer_file"
    CUSTOM_OBJ_FILE = "custom_obj_file"

    runner = CliRunner()

    os.chdir(str(tmp_path))
    Repository.initialize()
    clean_repo.activate_root()

    # Write pipeline definition, add file to sys path to make sure the other
    #  modules will be able to import from one another
    new_pipeline_definition = (
        define_sys_path_definition + "\n" + pipeline_definition
    )
    main_python_file = clean_repo.root / "run.py"
    main_python_file.write_text(new_pipeline_definition)

    # Write custom object file
    custom_obj_file = (
        clean_repo.root / CUSTOM_OBJ_FILE / f"{CUSTOM_OBJ_FILE}.py"
    )
    custom_obj_file.parent.mkdir()
    custom_obj_file.write_text(object_definition)

    # Make sure the custom materializer imports the custom object
    import_obj_path = os.path.splitext(
        os.path.relpath(custom_obj_file, tmp_path.parent)
    )[0].replace("/", ".")
    new_materializer_definition = (
        f"from {import_obj_path} "
        f"import {CUSTOM_OBJ_NAME} \n" + materializer_definition
    )

    # Write custom materializer file
    materializer_file = (
        clean_repo.root / MATERIALIZER_FILE / f"{MATERIALIZER_FILE}.py"
    )
    materializer_file.parent.mkdir()
    materializer_file.write_text(new_materializer_definition)

    # Make sure the step imports the custom object
    import_obj_path = os.path.splitext(
        os.path.relpath(custom_obj_file, tmp_path.parent)
    )[0].replace("/", ".")
    new_step_definition = (
        f"from {import_obj_path} "
        f"import {CUSTOM_OBJ_NAME} \n" + step_definition
    )
    # Write step file
    step_file = clean_repo.root / STEP_FILE / f"{STEP_FILE}.py"
    step_file.parent.mkdir()
    step_file.write_text(new_step_definition)

    # Write run configuration
    run_config = {
        "name": PIPELINE_NAME,
        "steps": {
            "step_1": {
                "source": {
                    "name": STEP_NAME,
                    "file": os.path.relpath(step_file, clean_repo.root),
                },
                "parameters": {"some_option": 3},
                "materializers": {
                    "output_1": {
                        "name": MATERIALIZER_NAME,
                        "file": os.path.relpath(
                            materializer_file, clean_repo.root
                        ),
                    }
                },
            }
        },
    }
    config_path = str(clean_repo.root / "config.yaml")
    yaml_utils.write_yaml(config_path, run_config)

    # Run Pipeline
    runner.invoke(pipeline, ["run", "run.py", "-c", "config.yaml"])

    # Assert that pipeline completed successfully
    historic_pipeline = Repository().get_pipeline(pipeline_name=PIPELINE_NAME)

    assert len(historic_pipeline.runs) == 1

    assert historic_pipeline.runs[-1].status == ExecutionStatus.COMPLETED

