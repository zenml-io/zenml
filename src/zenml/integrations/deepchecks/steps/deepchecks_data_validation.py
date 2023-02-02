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
"""Implementation of the Deepchecks data integrity validation step."""

from typing import Any, Dict, Optional, Sequence, cast

import pandas as pd
from deepchecks.core.suite import SuiteResult
from pydantic import Field

from zenml.integrations.deepchecks.data_validators.base_deepchecks_data_validator import (
    BaseDeepchecksDataValidator,
)
from zenml.integrations.deepchecks.validation_checks.base_validation_checks import (
    DeepchecksDataValidationCheck,
)
from zenml.logger import get_logger
from zenml.steps import BaseParameters
from zenml.steps.base_step import BaseStep

logger = get_logger(__name__)


class DeepchecksDataValidationCheckStepParameters(BaseParameters):
    """Parameters class for the Deepchecks data integrity validator step.

    Attributes:
        check_list: Optional list of `DeepchecksDataValidationCheck` identifiers
            specifying the subset of Deepchecks data integrity checks to be
            performed. If not supplied, the entire set of data integrity checks
            will be performed.
        dataset_kwargs: Additional keyword arguments to be passed to the
            Deepchecks `tabular.Dataset` or `vision.VisionData` constructor.
        check_kwargs: Additional keyword arguments to be passed to the
            Deepchecks check object constructors. Arguments are grouped for
            each check and indexed using the full check class name or
            check enum value as dictionary keys.
        run_kwargs: Additional keyword arguments to be passed to the
            Deepchecks Suite `run` method.
    """

    check_list: Optional[Sequence[DeepchecksDataValidationCheck]] = None
    dataset_kwargs: Dict[str, Any] = Field(default_factory=dict)
    check_kwargs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    run_kwargs: Dict[str, Any] = Field(default_factory=dict)


class DeepchecksDataValidationCheckStep(BaseStep):
    """Deepchecks data validation step."""

    def entrypoint(
        self,
        dataset: pd.DataFrame,
        params: DeepchecksDataValidationCheckStepParameters,
    ) -> SuiteResult:
        """Main entrypoint for the Deepchecks data validation step.

        Args:
            dataset: a Pandas DataFrame to validate
            params: The parameters for the step

        Returns:
            A Deepchecks suite result with the validation results.
        """
        data_validator = cast(
            BaseDeepchecksDataValidator,
            BaseDeepchecksDataValidator.get_active_data_validator(),
        )

        return data_validator.data_validation(
            dataset=dataset,
            check_list=cast(Optional[Sequence[str]], params.check_list),
            dataset_kwargs=params.dataset_kwargs,
            check_kwargs=params.check_kwargs,
            run_kwargs=params.run_kwargs,
        )


def deepchecks_data_validation_check_step(
    step_name: str,
    params: DeepchecksDataValidationCheckStepParameters,
) -> BaseStep:
    """Shortcut function to create a new data validation step.

    The returned `DeepchecksDataValidationCheckStep` can be used in a pipeline
    to run data validation checks on an input `pd.DataFrame` and return the
    results as a Deepchecks `SuiteResult` object.

    Args:
        step_name: The name of the step
        params: The parameters for the step

    Returns:
        a `DeepchecksDataValidationCheckStep` step instance
    """
    return DeepchecksDataValidationCheckStep(name=step_name, params=params)


# ------ DEPRECATED ------


class DeepchecksDataIntegrityCheckStepParameters(
    DeepchecksDataValidationCheckStepParameters
):
    """Deprecated data validation parameters."""


class DeepchecksDataIntegrityCheckStep(DeepchecksDataValidationCheckStep):
    """Deprecated data validation step."""

    def entrypoint(
        self,
        dataset: pd.DataFrame,
        params: DeepchecksDataValidationCheckStepParameters,
    ) -> SuiteResult:
        """We override this entrypoint so we can log a deprecation warning.

        Args:
            dataset: a Pandas DataFrame to validate
            params: The parameters for the step

        Returns:
            A Deepchecks suite result with the validation results.
        """
        logger.warning(
            "The `DeepchecksDataIntegrityCheckStep` class is deprecated and "
            "will be removed in a future release. Please use the "
            "`DeepchecksDataValidationCheckStep` class instead."
        )
        super().entrypoint(dataset=dataset, params=params)


def deepchecks_data_integrity_check_step(
    step_name: str,
    params: DeepchecksDataValidationCheckStepParameters,
) -> BaseStep:
    """Deprecated method to generate a data validation step.

    Args:
        step_name: The name of the step
        params: The parameters for the step

    Returns:
        a `DeepchecksDataValidationCheckStep` step instance
    """
    logger.warning(
        "The `deepchecks_data_integrity_check_step` function is deprecated and "
        "will be removed in a future release. Please use the "
        "`deepchecks_data_validation_check_step` function instead."
    )
    return deepchecks_data_validation_check_step(
        step_name=step_name, params=params
    )
