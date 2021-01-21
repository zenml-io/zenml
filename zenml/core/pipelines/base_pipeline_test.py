#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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
import os
import zenml
from zenml.core.pipelines.base_pipeline import BasePipeline
from zenml.core.repo.repo import Repository
from zenml.utils.enums import PipelineStatusTypes


ZENML_ROOT = os.path.dirname(zenml.__path__[0])


def test_executed():
    name = "my_pipeline"
    p = BasePipeline(name=name)
    assert not p.is_executed_in_metadata_store


def test_naming():
    name = "my_pipeline"
    p = BasePipeline(name=name)
    file_name = p.file_name
    pipeline_name = p.pipeline_name

    assert p.get_type_from_file_name(file_name) == p.PIPELINE_TYPE
    assert p.get_name_from_pipeline_name(pipeline_name) == name
    assert p.get_type_from_pipeline_name(pipeline_name) == p.PIPELINE_TYPE


def test_get_unknown_pipeline_status():
    name = "my_pipeline"
    p = BasePipeline(name=name)

    # passing this test means that if the pipeline is not in the metadata
    # store, it is (semantically) not started yet
    assert p.get_status() == PipelineStatusTypes.NotStarted.name
