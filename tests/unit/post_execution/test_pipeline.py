#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

from contextlib import ExitStack as does_not_raise

import pytest

from zenml.pipelines import pipeline
from zenml.post_execution.pipeline import get_pipeline


def test_get_pipeline():
    """Tests that getting post-execution pipelines forwards calls to the metadata store of the (active) stack."""
    # register a stack with a mysql metadata store

    @pipeline
    def some_pipeline():
        pass

    input_args = [
        {"pipeline": "some_pipeline"},  # calling by name
        {"pipeline": some_pipeline},  # calling by pipeline class
        {"pipeline": some_pipeline()},  # calling by pipeline instance
        {"pipeline_name": "some_pipeline"},
    ]  # calling with deprecated kwarg

    for input_arg in input_args:
        with does_not_raise():
            get_pipeline(**input_arg)


def test_get_pipeline_raises_exception():
    """Tests that get_pipeline raises a runtime error."""
    # register a stack with a mysql metadata store

    class NonPipeline:
        pass

    input_args = [
        {"pipeline": NonPipeline},  # calling with wrong class
        {"pipeline": NonPipeline()},  # calling with wrong class instance
        {"useless_arg": "some_pipeline"},  # calling with wrong kwarg
        {"pipeline_name": 1234},
    ]  # calling kwarg with wrong data type

    for input_arg in input_args:
        with pytest.raises(RuntimeError):
            get_pipeline(**input_arg)
