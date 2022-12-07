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
"""Implementation of the Deepchecks model drift validation step."""

from typing import Any, Dict, Optional, Sequence, cast

import pandas as pd
from deepchecks.core.suite import SuiteResult
from pydantic import Field
from sklearn.base import ClassifierMixin

from zenml.integrations.deepchecks.data_validators.deepchecks_data_validator import (
    DeepchecksDataValidator,
)
from zenml.integrations.deepchecks.validation_checks import (
    DeepchecksModelDriftCheck,
)
from zenml.steps import BaseParameters, BaseStep


class DeepchecksModelDriftCheckStepParameters(BaseParameters):
    """Parameters class for the Deepchecks model drift validator step.

    Attributes:
        check_list: Optional list of DeepchecksModelDriftCheck identifiers
            specifying the subset of Deepchecks model drift checks to be
            performed. If not supplied, the entire set of model drift checks
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

    check_list: Optional[Sequence[DeepchecksModelDriftCheck]] = None
    dataset_kwargs: Dict[str, Any] = Field(default_factory=dict)
    check_kwargs: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    run_kwargs: Dict[str, Any] = Field(default_factory=dict)


class DeepchecksModelDriftCheckStep(BaseStep):
    """Deepchecks model drift step."""

    def entrypoint(
        self,
        reference_dataset: pd.DataFrame,
        target_dataset: pd.DataFrame,
        model: ClassifierMixin,
        params: DeepchecksModelDriftCheckStepParameters,
    ) -> SuiteResult:
        """Main entrypoint for the Deepchecks model drift step.

        Args:
            reference_dataset: Reference dataset for the model drift check.
            target_dataset: Target dataset to be used for the model drift check.
            model: a scikit-learn model to validate
            params: the parameters for the step

        Returns:
            A Deepchecks suite result with the validation results.
        """
        data_validator = cast(
            DeepchecksDataValidator,
            DeepchecksDataValidator.get_active_data_validator(),
        )

        return data_validator.model_validation(
            dataset=reference_dataset,
            comparison_dataset=target_dataset,
            model=model,
            check_list=cast(Optional[Sequence[str]], params.check_list),
            dataset_kwargs=params.dataset_kwargs,
            check_kwargs=params.check_kwargs,
            run_kwargs=params.run_kwargs,
        )


def deepchecks_model_drift_check_step(
    step_name: str,
    params: DeepchecksModelDriftCheckStepParameters,
) -> BaseStep:
    """Shortcut function to create a new instance of the DeepchecksModelDriftCheckStep step.

    The returned DeepchecksModelDriftCheckStep can be used in a pipeline to
    run model drift checks on two input pd.DataFrame datasets and an input
    scikit-learn ClassifierMixin model and return the results as a Deepchecks
    SuiteResult object.

    Args:
        step_name: The name of the step
        params: The parameters for the step

    Returns:
        a DeepchecksModelDriftCheckStep step instance
    """
    return DeepchecksModelDriftCheckStep(name=step_name, params=params)
