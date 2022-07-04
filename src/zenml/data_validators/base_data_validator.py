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
"""Base class for all ZenML data validators."""

from abc import ABC, abstractmethod
from typing import Any, ClassVar, List, Optional, Tuple, Type

from pydantic import BaseModel

from zenml.enums import StackComponentType
from zenml.stack import StackComponent
from zenml.utils.enum_utils import StrEnum


class BaseDataValidator(StackComponent):
    """Base class for all ZenML data validators."""

    # Class configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.DATA_VALIDATOR
    FLAVOR: ClassVar[str]

    def data_profiling(self, dataset: Any, **kwargs: Any) -> Any:
        """Analyze a dataset and generate a data profile.

        This method should be implemented by data validators that support
        analyzing a dataset and generating a data profile for it (e.g. schema,
        statistical summary, data distribution profile, validation rules etc.).
        The data profile can be visualized or validated with custom code. It may
        also be used to validate other datasets against it (see
        `data_profile_validation`).

        Args:
            dataset: Reference dataset to be profiled.
            kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if data profiling is not supported by this
                data validator.

        Returns:
            Data profile generated from the input dataset.
        """
        raise NotImplementedError(
            f"Data profiling is not supported by the {self.__class__} data "
            f"validator."
        )

    def data_profile_validation(
        self, dataset: Any, profile: Any, **kwargs: Any
    ) -> Any:
        """Validate a dataset against a data profile.

        This method should be implemented by data validators that support
        validating a dataset against an existing data profile (e.g. schema,
        statistical summary, data distribution profile, pre-compiled data
        validation rules etc.).

        This method is usually paired with a data profiling feature (see
        `data_profiling` for details) that is capable of generating a data
        profile for a given dataset. This allows data validation to be performed
        in two steps: first, a baseline profile is generated on a reference
        dataset (e.g. a training dataset), then the profile is used to validate
        a second dataset against the reference dataset. This is useful because
        it doesn't require the reference dataset to be present and loaded during
        the validation. Data validators that do not support this two stage
        separation may implement the `data_comparison` method instead, which
        accepts both the reference and the target datasets as input arguments.

        Args:
            dataset: Target dataset to be validated.
            profile: Data profile (e.g. schema, statistical summary, data
                distribution profile) to be used to validate the target dataset.
            kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if profile-based data validation is not
                supported by this data validator.

        Returns:
            Dataset validation results.
        """
        raise NotImplementedError(
            f"Profile-based data validation is not supported by the "
            f"{self.__class__} data validator."
        )

    def data_validation(
        self, dataset: Any, model: Optional[Any] = None, **kwargs: Any
    ) -> Any:
        """Run data integrity checks on a dataset.

        This method should be implemented by data validators that support
        analyzing and identifying potential integrity problems with a dataset
        (e.g. missing values, conflicting labels, mixed data types etc.).

        Some data validation checks require data labels to be part of the
        dataset. If labels are not included, the method also takes in a model as
        argument that will be used to compute predictions on the fly.

        Args:
            dataset: Target dataset to be validated.
            model: Optional model to use to compute predictions from the
                dataset. Only required for data validations that require labels
                to be part of the datasets and if the labels are missing.
            kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if data integrity validation is not
                supported by this data validator.

        Returns:
            Dataset integrity validation results.
        """
        raise NotImplementedError(
            f"Data validation not implemented for {self}."
        )

    def data_comparison(
        self,
        reference_dataset: Any,
        target_dataset: Any,
        model: Optional[Any] = None,
        **kwargs: Any,
    ) -> Any:
        """Validate a target dataset by comparing it to a reference dataset.

        This method should be implemented by data validators that support
        running dataset comparison checks (i.e. data drift detection).

        Some data comparison checks require data labels to be part of both
        datasets (e.g. prediction drift). If labels are not included, the method
        also takes in a model as argument that will be used to compute
        predictions on the fly.

        Args:
            reference_dataset: Reference dataset (e.g. dataset used during model
                training).
            target_dataset: Dataset to be validated (e.g. dataset used during
                model validation or new data used in production).
            model: Optional model to use to compute predictions from the
                datasets. Only required for data comparison validations that
                require labels to be part of the datasets and if the labels are
                missing.
            kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if data comparison validation is not
                supported by this data validator.

        Returns:
            Dataset comparison validation results.
        """
        raise NotImplementedError(
            f"Data comparison not implemented for {self}."
        )

    def model_validation(self, model: Any, **kwargs: Any) -> Any:
        raise NotImplementedError(
            f"Model validation not implemented for {self}."
        )

    def model_comparison(
        self,
        reference_dataset: List[Any],
        target_dataset: List[Any],
        models: List[Any],
    ) -> Any:
        raise NotImplementedError(
            f"Model comparison not implemented for {self}."
        )
