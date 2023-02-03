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
"""Implementation of the Deepchecks data drift validation step."""

from typing import Any, Dict, Optional, Sequence, cast

import pandas as pd
from deepchecks.core.suite import SuiteResult
from pydantic import Field

from zenml.integrations.deepchecks.data_validators.deepchecks_data_validator import (
    DeepchecksDataValidator,
)
from zenml.integrations.deepchecks.validation_checks import (
    DeepchecksDataDriftCheck,
)
from zenml.steps import BaseParameters
from zenml.steps.base_step import BaseStep


class DeepchecksDataDriftCheckStepParameters(BaseParameters):
    """Parameter class for the Deepchecks data drift validator step.

    Attributes:
        check_list: Optional list of DeepchecksDataDriftCheck identifiers
            specifying the subset of Deepchecks data drift checks to be
            performed. If not supplied, the entire set of data drift checks will
            be performed.
        dataset_kwargs: Additional keyword arguments to be passed to the
            Deepchecks `tabular.Dataset` or `vision.VisionData` constructor.
        check_kwargs: Additional keyword arguments to be passed to the
            Deepchecks check object constructors. Arguments are grouped for
            each check and indexed using the full check class name or
            check enum value as dictionary keys.
        run_kwargs: Additional keyword arguments to be passed to the
            Deepchecks Suite `run` method.
    """

    check_list: Optional[Sequence[DeepchecksDataDriftCheck]] = None
    dataset_kwargs: Dict[str, Any] = Field(default_factory=dict)
    check_kwargs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    run_kwargs: Dict[str, Any] = Field(default_factory=dict)


class DeepchecksDataDriftCheckStep(BaseStep):
    """Deepchecks data drift validator step."""

    def entrypoint(
        self,
        reference_dataset: pd.DataFrame,
        target_dataset: pd.DataFrame,
        params: DeepchecksDataDriftCheckStepParameters,
    ) -> SuiteResult:
        """Main entrypoint for the Deepchecks data drift validator step.

        Args:
            reference_dataset: Reference dataset for the data drift check.
            target_dataset: Target dataset to be used for the data drift check.
            params: The parameters for the step

        Returns:
            A Deepchecks suite result with the validation results.
        """
        data_validator = cast(
            DeepchecksDataValidator,
            DeepchecksDataValidator.get_active_data_validator(),
        )

        return data_validator.data_validation(
            dataset=reference_dataset,
            comparison_dataset=target_dataset,
            check_list=cast(Optional[Sequence[str]], params.check_list),
            dataset_kwargs=params.dataset_kwargs,
            check_kwargs=params.check_kwargs,
            run_kwargs=params.run_kwargs,
        )


def deepchecks_data_drift_check_step(
    step_name: str,
    params: DeepchecksDataDriftCheckStepParameters,
) -> BaseStep:
    """Shortcut function to create a new instance of the DeepchecksDataDriftCheckStep step.

    The returned DeepchecksDataDriftCheckStep can be used in a pipeline to
    run data drift checks on two input pd.DataFrame and return the results
    as a Deepchecks SuiteResult object.

    Args:
        step_name: The name of the step
        params: The parameters for the step

    Returns:
        a DeepchecksDataDriftCheckStep step instance
    """
    return DeepchecksDataDriftCheckStep(name=step_name, params=params)
