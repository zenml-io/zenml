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

import os
from typing import Any

from zenml.constants import ENV_ZENML_DEBUG
from zenml.materializers.base_materializer import BaseMaterializer
from zenml.pipelines import pipeline
from zenml.steps import step


def test_handle_int_env_var():
    """Checks that the ZENML_DEBUG is set in the tests."""
    assert os.environ[ENV_ZENML_DEBUG] == "true"


def _test_materializer(
    step_output: Any, materializer: BaseMaterializer
) -> None:
    """Helper function to simplify materializer testing.

    Args:
        step_output: The output artifact we want to materialize.
        materializer: The materializer object.
    """
    step_output_type = type(step_output)

    @step
    def read_step() -> step_output_type:
        return step_output

    @pipeline
    def test_pipeline(read_step) -> None:
        read_step()

    test_pipeline(
        read_step=read_step().with_return_materializers(materializer)
    ).run()
