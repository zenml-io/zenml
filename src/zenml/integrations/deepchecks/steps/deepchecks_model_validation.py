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
"""Implementation of the Deepchecks model validation validation step."""

from typing import Any, Dict, Optional, Sequence, cast

import pandas as pd
from deepchecks.core.suite import SuiteResult
from pydantic import Field
from sklearn.base import ClassifierMixin

from zenml.integrations.deepchecks.data_validators.deepchecks_data_validator import (
    DeepchecksDataValidator,
)
from zenml.integrations.deepchecks.validation_checks import (
    DeepchecksModelValidationCheck,
)
from zenml.steps.base_step import BaseStep
from zenml.steps.base_step_config import BaseStepConfig
from zenml.steps.utils import clone_step


class DeepchecksModelValidationCheckStepConfig(BaseStepConfig):
    """Config class for the Deepchecks model validation validator step.

    Attributes:
        check_list: Optional list of DeepchecksModelValidationCheck identifiers
            specifying the subset of Deepchecks model validation checks to be
            performed. If not supplied, the entire set of model validation checks
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

    check_list: Optional[Sequence[DeepchecksModelValidationCheck]] = None
    dataset_kwargs: Dict[str, Any] = Field(default_factory=dict)
    check_kwargs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    run_kwargs: Dict[str, Any] = Field(default_factory=dict)


class DeepchecksModelValidationCheckStep(BaseStep):
    """Deepchecks model validation step."""

    def entrypoint(  # type: ignore[override]
        self,
        dataset: pd.DataFrame,
        model: ClassifierMixin,
        config: DeepchecksModelValidationCheckStepConfig,
    ) -> SuiteResult:
        """Main entrypoint for the Deepchecks model validation step.

        Args:
            dataset: a Pandas DataFrame to use for the validation
            model: a scikit-learn model to validate
            config: the configuration for the step

        Returns:
            A Deepchecks suite result with the validation results.
        """
        data_validator = cast(
            DeepchecksDataValidator,
            DeepchecksDataValidator.get_active_data_validator(),
        )

        return data_validator.model_validation(
            dataset=dataset,
            model=model,
            check_list=cast(Optional[Sequence[str]], config.check_list),
            dataset_kwargs=config.dataset_kwargs,
            check_kwargs=config.check_kwargs,
            run_kwargs=config.run_kwargs,
        )


def deepchecks_model_validation_check_step(
    step_name: str,
    config: DeepchecksModelValidationCheckStepConfig,
) -> BaseStep:
    """Shortcut function to create a new instance of the DeepchecksModelValidationCheckStep step.

    The returned DeepchecksModelValidationCheckStep can be used in a pipeline to
    run model validation checks on an input pd.DataFrame dataset and an input
    scikit-learn ClassifierMixin model and return the results as a Deepchecks
    SuiteResult object.

    Args:
        step_name: The name of the step
        config: The configuration for the step

    Returns:
        a DeepchecksModelValidationCheckStep step instance
    """
    return clone_step(DeepchecksModelValidationCheckStep, step_name)(
        config=config
    )
