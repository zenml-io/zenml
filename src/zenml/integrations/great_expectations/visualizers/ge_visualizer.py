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

"""Great Expectations visualizers for expectation suites and validation results."""

from typing import Any, cast

import great_expectations as ge  # type: ignore[import]
from great_expectations.checkpoint.types.checkpoint_result import (  # type: ignore[import]
    CheckpointResult,
)
from great_expectations.core import ExpectationSuite  # type: ignore[import]
from great_expectations.data_context.types.resource_identifiers import (  # type: ignore[import]
    ExpectationSuiteIdentifier,
)

from zenml.enums import ArtifactType
from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
from zenml.logger import get_logger
from zenml.post_execution import StepView
from zenml.visualizers import BaseVisualizer

logger = get_logger(__name__)


class GreatExpectationsVisualizer(BaseVisualizer):
    """The implementation of a Great Expectations Visualizer."""

    def visualize(self, object: StepView, *args: Any, **kwargs: Any) -> None:
        """Method to visualize a Great Expectations resource.

        Args:
            object: StepView fetched from run.get_step().
            *args: Additional arguments.
            **kwargs: Additional keyword arguments.
        """
        for artifact_view in object.outputs.values():
            # filter out anything but Great Expectations data analysis artifacts
            if (
                artifact_view.type == ArtifactType.DATA_ANALYSIS
                and artifact_view.data_type.startswith("great_expectations.")
            ):
                artifact = artifact_view.read()
                if isinstance(artifact, CheckpointResult):
                    result = cast(CheckpointResult, artifact)
                    identifier = next(iter(result.run_results.keys()))
                else:
                    suite = cast(ExpectationSuite, artifact)
                    identifier = ExpectationSuiteIdentifier(
                        suite.expectation_suite_name
                    )

                context = GreatExpectationsDataValidator.get_data_context()
                context.open_data_docs(identifier)
