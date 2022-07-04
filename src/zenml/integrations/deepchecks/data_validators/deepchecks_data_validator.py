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
"""Implementation of the Deepchecks data validator."""

from deepchecks.core.suite import SuiteResult
from deepchecks.core.check_result import CheckResult

from deepchecks.tabular import Dataset
from deepchecks.tabular.suites import full_suite
from sklearn.base import ClassifierMixin

from typing import Any, ClassVar, Dict

import pandas as pd

from zenml.data_validators import BaseDataValidator
from zenml.integrations.deepchecks import (
    DEEPCHECKS_DATA_VALIDATOR_FLAVOR,
)
from zenml.repository import Repository


class DeepchecksDataValidator(BaseDataValidator):
    """Deepchecks data validator stack component."""

    # Class Configuration
    FLAVOR: ClassVar[str] = DEEPCHECKS_DATA_VALIDATOR_FLAVOR

    @classmethod
    def get_active_data_validator(cls) -> "DeepchecksDataValidator":
        """Get the Deepchecks data validator registered in the active stack.

        Returns:
            The Deepchecks data validator registered in the active stack.

        TypeError: if a Deepchecks data validator is not part of the
            active stack.
        """
        repo = Repository(skip_repository_check=True)  # type: ignore[call-arg]
        data_validator = repo.active_stack.data_validator
        if data_validator and isinstance(data_validator, cls):
            return data_validator

        raise TypeError(
            f"The active stack needs to have a Deepchecks data "
            f"validator component registered to be able to run data validation "
            f"actions with Deepchecks. You can create a new stack with "
            f"a Deepchecks data validator component or update your "
            f"active stack to add this component, e.g.:\n\n"
            f"  `zenml data-validator register deepchecks "
            f"--flavor={cls.FLAVOR} ...`\n"
            f"  `zenml stack register stack-name -dv deepchecks ...`\n"
            f"  or:\n"
            f"  `zenml stack update -dv deepchecks`\n\n"
        )

    def data_model_comparison(
        self,
        reference_dataset: pd.DataFrame,
        target_dataset: pd.DataFrame,
        model: ClassifierMixin,
        dataset_args: Dict[str, Any] = {},
        suite_run_args: Dict[str, Any] = {},
    ) -> SuiteResult:
        """Validate data using deepchecks"""
        ds_train = Dataset(reference_dataset, **dataset_args)
        ds_test = Dataset(target_dataset, **dataset_args)
        suite = full_suite()
        return suite.run(
            train_dataset=ds_train,
            test_dataset=ds_test,
            model=model,
            **suite_run_args,
        )
