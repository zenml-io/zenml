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
from contextlib import ExitStack as does_not_raise

from great_expectations.core import ExpectationSuite

from zenml.integrations.great_expectations.materializers.ge_materializer import (
    GreatExpectationsMaterializer,
)
from zenml.pipelines import pipeline
from zenml.steps import step


def test_great_expectations_materializer(clean_repo):
    """Tests whether the steps work for the Great Expectations materializer."""

    @step
    def read_suite() -> ExpectationSuite:
        """Reads and materializes a Sklearn model."""
        return ExpectationSuite("arias_suite")

    @pipeline
    def test_pipeline(read_suite) -> None:
        """Tests the Great Expectations materializer."""
        read_suite()

    with does_not_raise():
        test_pipeline(
            read_suite=read_suite().with_return_materializers(
                GreatExpectationsMaterializer
            )
        ).run()

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    expectation_suite = last_run.steps[-1].output.read()
    assert isinstance(expectation_suite, ExpectationSuite)
    assert expectation_suite.expectation_suite_name == "arias_suite"
    assert len(expectation_suite.expectations) == 0
