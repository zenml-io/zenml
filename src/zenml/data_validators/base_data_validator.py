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

from typing import Any, ClassVar, Optional, Sequence

from zenml.enums import StackComponentType
from zenml.stack import StackComponent


class BaseDataValidator(StackComponent):
    """Base class for all ZenML data validators."""

    # Class configuration
    TYPE: ClassVar[StackComponentType] = StackComponentType.DATA_VALIDATOR
    FLAVOR: ClassVar[str]

    def data_profiling(
        self,
        dataset: Any,
        model: Optional[Any] = None,
        profile_list: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Analyze a dataset and generate a data profile.

        This method should be implemented by data validators that support
        analyzing a dataset and generating a data profile for it (e.g. schema,
        statistical summary, data distribution profile, validation rules etc.).
        The data profile can be visualized or validated with custom code. It may
        also be used to validate other datasets against it (see
        `data_profile_validation`).

        Some data profiling methods implemented by the data validator may
        require that a model be present during the profiling process to
        provide or dynamically generate additional information (e.g. label
        predictions, prediction probabilities, feature importance etc.) that is
        otherwise missing from the input dataset. Where that is the case, the
        method also takes in a model as argument.
        Alternatively, the missing information can be supplied using
        implementation specific keyword arguments, if so supported by the data
        validator.

        Data validators that support generating multiple categories of data
        profiles should also take in a `profile_list` argument that lists the
        subset of profiles to be generated. If not supplied, the default behavior
        is implementation specific (e.g. a single default data profile type may
        be generated and returned, or all available data profiles may be
        generated and returned as a single result).

        Args:
            dataset: Reference dataset to be profiled.
            model: Optional model to use to provide or dynamically generate
                additional information necessary for data profiling (e.g.
                labels, prediction probabilities, feature importance etc.).
            profile_list: Optional list identifying the categories of data
                profiles to be generated.
            **kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if data profiling is not supported by this
                data validator.
        """
        raise NotImplementedError(
            f"Data profiling is not supported by the {self.__class__} data "
            f"validator."
        )

    def data_profile_validation(
        self,
        dataset: Any,
        profile: Any,
        model: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        **kwargs: Any,
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

        Some data validation checks implemented by the data validator may
        require that a model be present during the validation process to
        provide or dynamically generate additional information (e.g. label
        predictions, prediction probabilities, feature importance etc.) that is
        otherwise missing from the input dataset. Where that is the case, the
        method also takes in a model as argument.
        Alternatively, the missing information can be supplied using
        implementation specific keyword arguments, if so supported by the data
        validator.

        Data validators that support running multiple categories of profile-based
        data validation checks should also take in a `check_list` argument that
        lists the subset of checks to be performed. If not supplied, the
        default behavior is implementation specific (e.g. a single default
        validation check may be performed, or all available validation checks
        may be performed and their results returned as a list of objects).

        Args:
            dataset: Target dataset to be validated.
            profile: Data profile (e.g. schema, statistical summary, data
                distribution profile) to be used to validate the target dataset.
            model: Optional model to use to provide or dynamically generate
                additional information necessary for data validation (e.g.
                labels, prediction probabilities, feature importance etc.).
            check_list: Optional list identifying the data validation checks to
                be performed.
            **kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if profile-based data validation is not
                supported by this data validator.
        """
        raise NotImplementedError(
            f"Profile-based data validation is not supported by the "
            f"{self.__class__} data validator."
        )

    def data_validation(
        self,
        dataset: Any,
        model: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Run data integrity checks on a dataset.

        This method should be implemented by data validators that support
        analyzing and identifying potential integrity problems with a dataset
        (e.g. missing values, conflicting labels, mixed data types etc.).

        Some data validation checks implemented by the data validator may
        require that a model be present during the validation process to
        provide or dynamically generate additional information (e.g. label
        predictions, prediction probabilities, feature importance etc.) that is
        otherwise missing from the input dataset. Where that is the case, the
        method also takes in a model as argument.
        Alternatively, the missing information can be supplied using
        implementation specific keyword arguments, if so supported by the data
        validator.

        Data validators that support running multiple categories of data
        integrity checks should also take in a `check_list` argument that
        lists the subset of checks to be performed. If not supplied, the
        default behavior is implementation specific (e.g. a single default
        validation check may be performed, or all available validation checks
        may be performed and their results returned as a list of objects).

        Args:
            dataset: Target dataset to be validated.
            model: Optional model to use to provide or dynamically generate
                additional information necessary for data validation (e.g.
                labels, prediction probabilities, feature importance etc.).
            check_list: Optional list identifying the data integrity checks to
                be performed.
            **kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if data integrity validation is not
                supported by this data validator.
        """
        raise NotImplementedError(
            f"Data validation not implemented for {self}."
        )

    def model_validation(
        self,
        dataset: Any,
        model: Any,
        check_list: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Run model validation checks.

        This method should be implemented by data validators that support
        running model validation checks (e.g. confusion matrix validation,
        performance reports, model error analyses, etc).

        Model validation checks require that a model be present during
        the validation process. Unlike `data_validation`, where the model
        is only required as an alternative of providing information otherwise
        not present in the input dataset or implementation specific keyword
        arguments (e.g. labels, prediction probabilities, feature importance),
        the model is a mandatory component of model validation.

        Data validators that support running multiple categories of model
        validation checks should also take in a `check_list` argument that
        lists the subset of checks to be performed. If not supplied, the
        default behavior is implementation specific (e.g. a single default
        validation check may be performed, or all available validation checks
        may be performed and their results returned as a list of objects).

        Args:
            dataset: Target dataset to be validated.
            model: Target model to be validated.
            check_list: Optional list identifying the model validation checks to
                be performed.
            **kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if model validation is not supported by this
                data validator.
        """
        raise NotImplementedError(
            f"Model validation not implemented for {self}."
        )

    def data_comparison(
        self,
        reference_dataset: Any,
        target_dataset: Any,
        model: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Validate a target dataset by comparing it to a reference dataset.

        This method should be implemented by data validators that support
        running dataset comparison checks (e.g. data drift checks).

        Some data comparison methods implemented by the data validator may
        require that a model be present during the comparison process to
        provide or dynamically generate additional information (e.g. label
        predictions, prediction probabilities, feature importance etc.) that is
        otherwise missing from the input datasets. Where that is the case, the
        method also takes in a model as argument.
        Alternatively, the missing information can be supplied using
        implementation specific keyword arguments, if so supported by the data
        validator.

        Data validators that support running multiple categories of data
        comparison checks should also take in a `check_list` argument that
        lists the subset of checks to be performed. If not supplied, the
        default behavior is implementation specific (e.g. a single default
        validation check may be performed, or all available validation checks
        may be performed and their results returned as a list of objects).

        Args:
            reference_dataset: Reference dataset (e.g. dataset used during model
                training).
            target_dataset: Dataset to be validated (e.g. dataset used during
                model validation or new data used in production).
            model: Optional model to use to provide or dynamically generate
                additional information necessary for data comparison (e.g.
                labels, prediction probabilities, feature importance etc.).
            check_list: Optional list identifying the data comparison checks to
                be performed.
            **kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if data comparison validation is not
                supported by this data validator.
        """
        raise NotImplementedError(
            f"Data comparison not implemented for {self}."
        )

    def model_comparison(
        self,
        reference_dataset: Any,
        target_dataset: Any,
        model: Any,
        check_list: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Validate a model using a target and a reference dataset.

        This method should be implemented by data validators that support
        identifying changes in a model performance by analyzing how it performs
        on a target dataset in comparison to how it performs on a reference
        dataset.

        Model comparison checks require that a model be present during
        the validation process. Unlike `data_comparison`, where the model
        is only required as an alternative of providing information otherwise
        not present in the input dataset or implementation specific keyword
        arguments (e.g. labels, prediction probabilities, feature importance),
        the model is a mandatory component of model comparison.

        Data validators that support running multiple categories of model
        comparison checks should also take in a `check_list` argument that
        lists the subset of checks to be performed. If not supplied, the
        default behavior is implementation specific (e.g. a single default
        validation check may be performed, or all available validation checks
        may be performed and their results returned as a list of objects).

        Args:
            reference_dataset: Reference dataset (e.g. dataset used during model
                training).
            target_dataset: Dataset to be validated (e.g. dataset used during
                model validation or new data used in production).
            model: Target model to be validated.
            check_list: Optional list identifying the model comparison checks to
                be performed.
            **kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if model comparison validation is not
                supported by this data validator.
        """
        raise NotImplementedError(
            f"Model comparison not implemented for {self}."
        )
