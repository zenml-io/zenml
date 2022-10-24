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

from typing import Any, ClassVar, Optional, Sequence, Type, cast

from zenml.client import Client
from zenml.enums import StackComponentType
from zenml.stack import Flavor, StackComponent
from zenml.stack.stack_component import StackComponentConfig


class BaseDataValidatorConfig(StackComponentConfig):
    """Base config for all data validators."""


class BaseDataValidator(StackComponent):
    """Base class for all ZenML data validators."""

    NAME: ClassVar[str]
    FLAVOR: ClassVar[Type["BaseDataValidatorFlavor"]]

    @property
    def config(self) -> BaseDataValidatorConfig:
        """Returns the config of this data validator.

        Returns:
            The config of this data validator.
        """
        return cast(BaseDataValidatorConfig, self._config)

    @classmethod
    def get_active_data_validator(cls) -> "BaseDataValidator":
        """Get the data validator registered in the active stack.

        Returns:
            The data validator registered in the active stack.

        Raises:
            TypeError: if a data validator is not part of the
                active stack.
        """
        flavor: BaseDataValidatorFlavor = cls.FLAVOR()
        client = Client()
        data_validator = client.active_stack.data_validator
        if not data_validator or not isinstance(data_validator, cls):
            raise TypeError(
                f"The active stack needs to have a {cls.NAME} data "
                f"validator component registered to be able to run data validation "
                f"actions with {cls.NAME}. You can create a new stack with "
                f"a {cls.NAME} data validator component or update your "
                f"active stack to add this component, e.g.:\n\n"
                f"  `zenml data-validator register {flavor.name} "
                f"--flavor={flavor.name} ...`\n"
                f"  `zenml stack register <STACK-NAME> -dv {flavor.name} ...`\n"
                f"  or:\n"
                f"  `zenml stack update -dv {flavor.name}`\n\n"
            )

        return data_validator

    def data_profiling(
        self,
        dataset: Any,
        comparison_dataset: Optional[Any] = None,
        profile_list: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Analyze one or more datasets and generate a data profile.

        This method should be implemented by data validators that support
        analyzing a dataset and generating a data profile (e.g. schema,
        statistical summary, data distribution profile, validation
        rules, data drift reports etc.).
        The method should return a data profile object.

        This method also accepts an optional second dataset argument to
        accommodate different categories of data profiling, e.g.:

        * profiles generated from a single dataset: schema inference, validation
        rules inference, statistical profiles, data integrity reports
        * differential profiles that need a second dataset for comparison:
        differential statistical profiles, data drift reports

        Data validators that support generating multiple categories of data
        profiles should also take in a `profile_list` argument that lists the
        subset of profiles to be generated. If not supplied, the behavior is
        implementation specific, but it is recommended to provide a good default
        (e.g. a single default data profile type may be generated and returned,
        or all available data profiles may be generated and returned as a single
        result).

        Args:
            dataset: Target dataset to be profiled.
            comparison_dataset: Optional second dataset to be used for data
                comparison profiles (e.g data drift reports).
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

    def data_validation(
        self,
        dataset: Any,
        comparison_dataset: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Run data validation checks on a dataset.

        This method should be implemented by data validators that support
        running data quality checks an input dataset (e.g. data integrity
        checks, data drift checks).

        This method also accepts an optional second dataset argument to
        accommodate different categories of data validation tests, e.g.:

        * single dataset checks: data integrity checks (e.g. missing
        values, conflicting labels, mixed data types etc.)
        * checks that compare two datasets: data drift checks (e.g. new labels,
        feature drift, label drift etc.)

        Data validators that support running multiple categories of data
        integrity checks should also take in a `check_list` argument that
        lists the subset of checks to be performed. If not supplied, the
        behavior is implementation specific, but it is recommended to provide a
        good default (e.g. a single default validation check may be performed,
        or all available validation checks may be performed and their results
        returned as a list of objects).

        Args:
            dataset: Target dataset to be validated.
            comparison_dataset: Optional second dataset to be used for data
                comparison checks (e.g data drift checks).
            check_list: Optional list identifying the data checks to
                be performed.
            **kwargs: Implementation specific keyword arguments.

        Raises:
            NotImplementedError: if data validation is not
                supported by this data validator.
        """
        raise NotImplementedError(
            f"Data validation not implemented for {self}."
        )

    def model_validation(
        self,
        dataset: Any,
        model: Any,
        comparison_dataset: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        **kwargs: Any,
    ) -> Any:
        """Run model validation checks.

        This method should be implemented by data validators that support
        running model validation checks (e.g. confusion matrix validation,
        performance reports, model error analyses, etc).

        Unlike `data_validation`, model validation checks require that a model
        be present as an active component during the validation process.

        This method also accepts an optional second dataset argument to
        accommodate different categories of data validation tests, e.g.:

        * single dataset tests: confusion matrix validation,
        performance reports, model error analyses, etc
        * model comparison tests: tests that identify changes in a model
        behavior by comparing how it performs on two different datasets.

        Data validators that support running multiple categories of model
        validation checks should also take in a `check_list` argument that
        lists the subset of checks to be performed. If not supplied, the
        behavior is implementation specific, but it is recommended to provide a
        good default (e.g. a single default validation check may be performed,
        or all available validation checks may be performed and their results
        returned as a list of objects).

        Args:
            dataset: Target dataset to be validated.
            model: Target model to be validated.
            comparison_dataset: Optional second dataset to be used for model
                comparison checks (e.g model performance comparison checks).
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


class BaseDataValidatorFlavor(Flavor):
    """Base class for data validator flavors."""

    @property
    def type(self) -> StackComponentType:
        """The type of the component.

        Returns:
            The type of the component.
        """
        return StackComponentType.DATA_VALIDATOR

    @property
    def config_class(self) -> Type[BaseDataValidatorConfig]:
        """Config class for data validator.

        Returns:
            Config class for data validator.
        """
        return BaseDataValidatorConfig

    @property
    def implementation_class(self) -> Type[BaseDataValidator]:
        """Implementation for data validator.

        Returns:
            Implementation for data validator.
        """
        return BaseDataValidator
