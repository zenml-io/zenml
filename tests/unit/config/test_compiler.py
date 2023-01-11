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

from zenml.config.compiler import Compiler
from zenml.steps import step
from zenml.steps.base_step import BaseStep


def _compile_step(step: BaseStep):
    # Call the step here to finalize the configuration
    step()

    compiler = Compiler()
    return compiler._compile_step(
        step=step,
        pipeline_settings={},
        pipeline_extra={},
        stack=None,
    )


def test_compiler_sets_step_docstring():
    """Test that the compiler writes the step docstring into the step config."""

    @step
    def step_without_docstring() -> None:
        pass

    assert _compile_step(step_without_docstring()).config.docstring is None

    @step
    def step_with_empty_docstring() -> None:
        """"""

    assert _compile_step(step_with_empty_docstring()).config.docstring == ""

    @step
    def step_with_docstring() -> None:
        """docstring."""

    assert _compile_step(step_with_docstring()).config.docstring == "docstring."
