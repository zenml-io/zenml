#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Implementation of the Evidently data validator."""

import os
from typing import Any, ClassVar, Dict, List, Optional, Sequence, cast

import pandas as pd

from zenml.data_validators import BaseDataValidator
from zenml.logger import get_logger

logger = get_logger(__name__)


class EvidentlyDataValidator(BaseDataValidator):
    """Evidently data validator stack component."""

    # Class Configuration
    FLAVOR: ClassVar[str] = EVIDENTLY_DATA_VALIDATOR_FLAVOR


    def data_comparison(
        self,
        reference_dataset: pd.DataFrame,
        target_dataset: pd.DataFrame,
        model: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        column_mapping: Optional[ColumnMapping],
        **kwargs: Any,
    ) -> Any:
        """Run one or more data comparison (data drift) checks.

        Call this method to perform dataset comparison checks (e.g. data drift
        checks) by comparing a target dataset to a reference dataset.

        Some Deepchecks data comparison checks may require that a model be
        present during the validation process to provide or dynamically generate
        additional information (e.g. label predictions, prediction probabilities,
        feature importance etc.) that is otherwise missing from the input
        datasets. Where that is the case, the method also takes in a model as
        argument. Alternatively, the missing information can be supplied using
        custom `dataset_kwargs`, `check_kwargs` or `run_args` keyword
        arguments.

        The `check_list` argument may be used to specify a custom set of
        Deepchecks data comparison checks to perform, identified by
        `DeepchecksDataDriftCheck` enum values. If omitted, a suite with
        all available data comparison checks that don't require a model as
        input will be performed on the input datasets.
        See `DeepchecksDataDriftCheck` for a list of Deepchecks builtin
        checks that are compatible with this method.

        Args:
            reference_dataset: Reference dataset (e.g. dataset used during model
                training).
            target_dataset: Dataset to be validated (e.g. dataset used during
                model validation or new data used in production).
            model: Optional model to use to provide or dynamically generate
                additional information necessary for data comparison (e.g.
                labels, prediction probabilities, feature importance etc.).
            check_list: Optional list of ZenML Deepchecks check identifiers
                specifying the data comparison checks to be performed.
                `DeepchecksDataDriftCheck` enum values should be used as
                elements.
            dataset_kwargs: Additional keyword arguments to be passed to the
                Deepchecks tabular.Dataset or vision.VisionData constructor.
            check_kwargs: Additional keyword arguments to be passed to the
                Deepchecks check object constructors. Arguments are grouped for
                each check and indexed using the full check class name or
                check enum value as dictionary keys.
            run_kwargs: Additional keyword arguments to be passed to the
                Deepchecks Suite `run` method.
            kwargs: Additional keyword arguments (unused).

        Returns:
            A Datachecks SuiteResult with the results of the validation.
        """
        return self._create_and_run_check_suite(
            check_enum=DeepchecksDataDriftCheck,
            reference_dataset=reference_dataset,
            target_dataset=target_dataset,
            model=model,
            check_list=check_list,
            dataset_kwargs=dataset_kwargs,
            check_kwargs=check_kwargs,
            run_kwargs=run_kwargs,
        )