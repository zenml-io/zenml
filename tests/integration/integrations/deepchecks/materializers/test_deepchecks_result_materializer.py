#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Unit tests for Deepchecks result materializer."""

from contextlib import ExitStack as does_not_raise

import pandas as pd
import pytest
from deepchecks.core.check_result import CheckResult
from deepchecks.core.suite import SuiteResult
from deepchecks.tabular import Context, Dataset, TrainTestCheck

from tests.unit.test_general import _test_materializer
from zenml.integrations.deepchecks.materializers.deepchecks_results_materializer import (
    DeepchecksResultMaterializer,
)


class DatasetSizeComparison(TrainTestCheck):
    """Check which compares the sizes of train and test datasets."""

    def run_logic(self, context: Context) -> CheckResult:
        ## Check logic
        train_size = context.train.n_samples
        test_size = context.test.n_samples

        ## Return value as check result
        return_value = {"train_size": train_size, "test_size": test_size}
        return CheckResult(return_value)


@pytest.fixture
def check_result():
    """Fixture to get a check result."""
    train_dataset = Dataset(
        pd.DataFrame(data={"x": [1, 2, 3, 4, 5, 6, 7, 8, 9]}), label=None
    )
    test_dataset = Dataset(pd.DataFrame(data={"x": [1, 2, 3]}), label=None)
    return DatasetSizeComparison().run(train_dataset, test_dataset)


def test_deepchecks_dataset_materializer_with_check_result(
    clean_client, check_result
):
    """Test the Deepchecks dataset materializer for a single check result."""
    with does_not_raise():
        _test_materializer(
            step_output=check_result,
            materializer_class=DeepchecksResultMaterializer,
            assert_visualization_exists=True,
        )


def test_deepchecks_dataset_materializer_with_suite_result(
    clean_client, check_result
):
    """Test the Deepchecks dataset materializer for a suite result."""
    suite = SuiteResult(name="aria_wears_suites", results=[check_result])
    with does_not_raise():
        _test_materializer(
            step_output=suite,
            materializer_class=DeepchecksResultMaterializer,
            assert_visualization_exists=True,
        )
