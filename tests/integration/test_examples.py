#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
import pytest
import shutil
from pathlib import Path

from zenml.cli import LocalExample, EXAMPLES_RUN_SCRIPT

QUICKSTART = 'quickstart'
NOT_SO_QUICKSTART = 'not_so_quickstart'
CACHING = 'caching'


@pytest.fixture(scope='session')
def examples_dir(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp('tmp')
    examples_path = tmp_path / "zenml_examples"
    source_path = Path('examples')
    shutil.copytree(source_path, examples_path)
    yield examples_path
    shutil.rmtree(str(examples_path))


def test_run_quickstart(examples_dir: Path):
    """"""
    local_example = LocalExample(examples_dir / QUICKSTART,
                                 name=QUICKSTART)

    bash_script_location = examples_dir / EXAMPLES_RUN_SCRIPT
    local_example.run_example(
        bash_file=str(bash_script_location), force=True
    )

    # assert (local_example.path.joinpath(
    #             '.zen/local_store/trainer/output/2/model'
    #         ).is_file())


def test_run_not_so_quickstart(examples_dir: Path):
    """"""
    local_example = LocalExample(examples_dir / NOT_SO_QUICKSTART,
                                 name=NOT_SO_QUICKSTART)

    bash_script_location = examples_dir / EXAMPLES_RUN_SCRIPT
    local_example.run_example(
        bash_file=str(bash_script_location), force=True
    )

    # assert (local_example.path.joinpath(
    #     '.zen/local_store/tf_trainer/output/3/saved_model.pb'
    # ).is_file())
    # assert (local_example.path.joinpath(
    #     '.zen/local_store/torch_trainer/output/7/entire_model.pt'
    # ).is_file())
    # assert (local_example.path.joinpath(
    #     '.zen/local_store/sklearn_trainer/output/11/model'
    # ).is_file())


# def test_run_caching(examples_dir: Path):
#     """"""
#     examples_dir = Path('home/apenner/delete')
#
#     local_example = LocalExample(examples_dir / CACHING,
#                                  name=CACHING)
#
#     bash_script_location = examples_dir / CACHING
#     local_example.run_example(
#         bash_file=str(bash_script_location), force=True
#     )
#     a = 0
#     assert (local_example.path.joinpath(
#         '.zen/local_store/tf_trainer/output/3/saved_model.pb'
#     ).is_file())
#     assert (local_example.path.joinpath(
#         '.zen/local_store/tf_trainer/output/7/saved_model.pb'
#     ).is_file())

