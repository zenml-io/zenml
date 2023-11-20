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

from great_expectations.core import ExpectationSuite

from tests.unit.test_general import _test_materializer
from zenml.integrations.great_expectations.data_validators.ge_data_validator import (
    GreatExpectationsDataValidator,
)
from zenml.integrations.great_expectations.materializers.ge_materializer import (
    GreatExpectationsMaterializer,
)


def test_great_expectations_materializer(clean_workspace, mocker):
    """Tests whether the steps work for the Great Expectations materializer."""

    class MockContext:
        """Mock class for the GE DataContext."""

        @staticmethod
        def get_docs_sites_urls(identifier):
            """Mock method to get all docs sites (visualizations)."""
            return []

    # The GE materializer needs to access the GE data validator of the active
    # stack in order to find where the data docs (visualizations) were saved.
    # This is not possible in a unit test, so we mock the data context. This
    # means, however, that we do not test whether the visualizations are
    # actually accessible.
    mocker.patch.object(
        GreatExpectationsDataValidator,
        "get_data_context",
        return_value=MockContext(),
    )

    expectation_suite = _test_materializer(
        step_output=ExpectationSuite("arias_suite"),
        materializer_class=GreatExpectationsMaterializer,
        expected_metadata_size=2,
    )

    assert expectation_suite.expectation_suite_name == "arias_suite"
    assert len(expectation_suite.expectations) == 0
