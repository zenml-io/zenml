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

from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

import pandas as pd
from deepchecks.core.checks import BaseCheck
from deepchecks.core.suite import SuiteResult
from deepchecks.tabular import Dataset as TabularData
from deepchecks.tabular import Suite as TabularSuite

from deepchecks.tabular import ModelComparisonSuite

# not part of deepchecks.tabular.checks
from deepchecks.tabular.suites import full_suite as full_tabular_suite
from deepchecks.vision import Suite as VisionSuite
from deepchecks.vision import VisionData
from deepchecks.vision.suites import full_suite as full_vision_suite
from sklearn.base import ClassifierMixin
from torch.nn import Module
from torch.utils.data.dataloader import DataLoader

from zenml import get_step_context
from zenml.data_validators import BaseDataValidator, BaseDataValidatorFlavor
from zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor import (
    DeepchecksDataValidatorFlavor,
)
from zenml.integrations.deepchecks.validation_checks import (
    DeepchecksDataDriftCheck,
    DeepchecksDataIntegrityCheck,
    DeepchecksModelDriftCheck,
    DeepchecksModelValidationCheck,
    DeepchecksValidationCheck,
)
from zenml.logger import get_logger
from zenml.utils.string_utils import random_str

logger = get_logger(__name__)


class DeepchecksDataValidator(BaseDataValidator):
    """Deepchecks data validator stack component."""

    NAME: ClassVar[str] = "Deepchecks"
    FLAVOR: ClassVar[Type[BaseDataValidatorFlavor]] = (
        DeepchecksDataValidatorFlavor
    )

    @staticmethod
    def _split_checks(
        check_list: Sequence[str],
    ) -> Tuple[Sequence[str], Sequence[str]]:
        """Split a list of check identifiers in two lists, one for tabular and one for computer vision checks.

        Args:
            check_list: A list of check identifiers.

        Returns:
            List of tabular check identifiers and list of computer vision
            check identifiers.
        """
        tabular_checks = list(
            filter(
                lambda check: DeepchecksValidationCheck.is_tabular_check(
                    check
                ),
                check_list,
            )
        )
        vision_checks = list(
            filter(
                lambda check: DeepchecksValidationCheck.is_vision_check(check),
                check_list,
            )
        )
        return tabular_checks, vision_checks

    @classmethod
    def _create_and_run_check_suite(
        cls,
        check_enum: Type[DeepchecksValidationCheck],
        reference_dataset: Union[pd.DataFrame, DataLoader[Any]],
        comparison_dataset: Optional[
            Union[pd.DataFrame, DataLoader[Any]]
        ] = None,
        models: Optional[List[Union[ClassifierMixin, Module]]] = None,
        check_list: Optional[Sequence[str]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
    ) -> SuiteResult:
        """Create and run a Deepchecks check suite corresponding to the input parameters.

        This method contains generic logic common to all Deepchecks data
        validator methods that validates the input arguments and uses them to
        generate and run a Deepchecks check suite.

        Args:
            check_enum: ZenML enum type grouping together Deepchecks checks with
                the same characteristics. This is used to generate a default
                list of checks, if a custom list isn't provided via the
                `check_list` argument.
            reference_dataset: Primary (reference) dataset argument used during
                validation.
            comparison_dataset: Optional secondary (comparison) dataset argument
                used during comparison checks.
            models: Optional model argument used during validation.
            check_list: Optional list of ZenML Deepchecks check identifiers
                specifying the list of Deepchecks checks to be performed.
            dataset_kwargs: Additional keyword arguments to be passed to the
                Deepchecks tabular.Dataset or vision.VisionData constructor.
            check_kwargs: Additional keyword arguments to be passed to the
                Deepchecks check object constructors. Arguments are grouped for
                each check and indexed using the full check class name or
                check enum value as dictionary keys.
            run_kwargs: Additional keyword arguments to be passed to the
                Deepchecks Suite `run` method.

        Returns:
            Deepchecks SuiteResult object with the Suite run results.

        Raises:
            TypeError: If the datasets, model and check list arguments combine
                data types and/or checks from different categories (tabular and
                computer vision).
        """
        # Detect what type of check to perform (tabular or computer vision) from
        # the dataset/model datatypes and the check list. At the same time,
        # validate the combination of data types used for dataset and model
        # arguments and the check list.
        is_tabular = False
        is_vision = False
        is_multi_model = False
        for dataset in [reference_dataset, comparison_dataset]:
            if dataset is None:
                continue
            if isinstance(dataset, pd.DataFrame):
                is_tabular = True
            elif isinstance(dataset, DataLoader):
                is_vision = True
            else:
                raise TypeError(
                    f"Unsupported dataset data type found: {type(dataset)}. "
                    f"Supported data types are {str(pd.DataFrame)} for tabular "
                    f"data and {str(DataLoader)} for computer vision data."
                )

        if models:
            # if there's more than one models, we should set the 
            # is_multi_model to True
            if len(models) > 1:
                is_multi_model = True
            # if the models are of different types, raise an error
            # only the same type of models can be used for comparison
            if len(set(type(model) for model in models)) > 1:
                raise TypeError(
                    f"Models used for comparison checks must be of the same type."
                )
            model = models[0]
            if isinstance(model, ClassifierMixin):
                is_tabular = True
            elif isinstance(model, Module):
                is_vision = True
            else:
                raise TypeError(
                    f"Unsupported model data type found: {type(model)}. "
                    f"Supported data types are {str(ClassifierMixin)} for "
                    f"tabular data and {str(Module)} for computer vision "
                    f"data."
                )

        if is_tabular and is_vision:
            raise TypeError(
                f"Tabular and computer vision data types used for datasets and "
                f"models cannot be mixed. They must all belong to the same "
                f"category. Supported data types for tabular data are "
                f"{str(pd.DataFrame)} for datasets and {str(ClassifierMixin)} "
                f"for models. Supported data types for computer vision data "
                f"are {str(pd.DataFrame)} for datasets and and {str(Module)} "
                f"for models."
            )

        if not check_list:
            # default to executing all the checks listed in the supplied
            # checks enum type if a custom check list is not supplied
            # don't include the TABULAR_PERFORMANCE_BIAS check enum value
            # as it requires a protected feature name to be set
            checks_to_exclude = [
                DeepchecksModelValidationCheck.TABULAR_PERFORMANCE_BIAS
            ]
            check_enum_values = [
                check.value
                for check in check_enum
                if check not in checks_to_exclude
            ]
            tabular_checks, vision_checks = cls._split_checks(
                check_enum_values
            )
            if is_tabular:
                check_list = tabular_checks
                vision_checks = []
            else:
                check_list = vision_checks
                tabular_checks = []
        else:
            tabular_checks, vision_checks = cls._split_checks(check_list)

        if tabular_checks and vision_checks:
            raise TypeError(
                f"The check list cannot mix tabular checks "
                f"({tabular_checks}) and computer vision checks ("
                f"{vision_checks})."
            )

        if is_tabular and vision_checks:
            raise TypeError(
                f"Tabular data types used for datasets and models can only "
                f"be used with tabular validation checks. The following "
                f"computer vision checks included in the check list are "
                f"not valid: {vision_checks}."
            )

        if is_vision and tabular_checks:
            raise TypeError(
                f"Computer vision data types used for datasets and models "
                f"can only be used with computer vision validation checks. "
                f"The following tabular checks included in the check list "
                f"are not valid: {tabular_checks}."
            )

        check_classes = map(
            lambda check: (
                check,
                check_enum.get_check_class(check),
            ),
            check_list,
        )

        # use the pipeline name and the step name to generate a unique suite
        # name
        try:
            # get pipeline name and step name
            step_context = get_step_context()
            pipeline_name = step_context.pipeline.name
            step_name = step_context.step_run.name
            suite_name = f"{pipeline_name}_{step_name}"
        except RuntimeError:
            # if not running inside a pipeline step, use random values
            suite_name = f"suite_{random_str(5)}"

        if is_tabular:
            dataset_class = TabularData
            suite_class = TabularSuite
            full_suite = full_tabular_suite()
        else:
            dataset_class = VisionData
            suite_class = VisionSuite
            full_suite = full_vision_suite()

        # if is_multi_model is True, we need to use the ModelComparisonSuite
        if is_multi_model:
            suite_class = ModelComparisonSuite

        train_dataset = dataset_class(reference_dataset, **dataset_kwargs)
        test_dataset = None
        if comparison_dataset is not None:
            test_dataset = dataset_class(comparison_dataset, **dataset_kwargs)
        suite = suite_class(name=suite_name)

        # Some Deepchecks checks require a minimum configuration such as
        # conditions to be configured (see https://docs.deepchecks.com/stable/user-guide/general/customizations/examples/plot_configure_check_conditions.html#sphx-glr-user-guide-general-customizations-examples-plot-configure-check-conditions-py)
        # for their execution to have meaning. For checks that don't have
        # custom configuration attributes explicitly specified in the
        # `check_kwargs` input parameter, we use the default check
        # instances extracted from the full suite shipped with Deepchecks.
        default_checks = {
            check.__class__: check for check in full_suite.checks.values()
        }
        for check_name, check_class in check_classes:
            extra_kwargs = check_kwargs.get(check_name, {})
            default_check = default_checks.get(check_class)
            check: BaseCheck
            if extra_kwargs or not default_check:
                check = check_class(**check_kwargs)
            else:
                check = default_check

            # extract the condition kwargs from the check kwargs
            for arg_name, condition_kwargs in extra_kwargs.items():
                if not arg_name.startswith("condition_") or not isinstance(
                    condition_kwargs, dict
                ):
                    continue
                condition_method = getattr(check, f"add_{arg_name}", None)
                if not condition_method or not callable(condition_method):
                    logger.warning(
                        f"Deepchecks check type {check.__class__} has no "
                        f"condition named {arg_name}. Ignoring the check "
                        f"argument."
                    )
                    continue
                condition_method(**condition_kwargs)

            # if the check is supported by the suite, add it
            if isinstance(check, suite.supported_checks()):
                suite.add(check)
            else:
                logger.warning(
                    f"Check {check_name} is not supported by the {suite_class} "
                    "suite. Ignoring the check."
                )

        if isinstance(suite, ModelComparisonSuite):
            return suite.run(
                models=models,
                train_datasets=train_dataset,
                test_datasets=test_dataset,
            )
        else:
            return suite.run(
                train_dataset=train_dataset,
                test_dataset=test_dataset,
                model=models[0] if models else None,
                **run_kwargs,
            )

    def data_validation(
        self,
        dataset: Union[pd.DataFrame, DataLoader[Any]],
        comparison_dataset: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
        **kwargs: Any,
    ) -> SuiteResult:
        """Run one or more Deepchecks data validation checks on a dataset.

        Call this method to analyze and identify potential integrity problems
        with a single dataset (e.g. missing values, conflicting labels, mixed
        data types etc.) and dataset comparison checks (e.g. data drift
        checks). Dataset comparison checks require that a second dataset be
        supplied via the `comparison_dataset` argument.

        The `check_list` argument may be used to specify a custom set of
        Deepchecks data integrity checks to perform, identified by
        `DeepchecksDataIntegrityCheck` and `DeepchecksDataDriftCheck` enum
        values. If omitted:

        * if the `comparison_dataset` is omitted, a suite with all available
        data integrity checks will be performed on the input data. See
        `DeepchecksDataIntegrityCheck` for a list of Deepchecks builtin
        checks that are compatible with this method.

        * if the `comparison_dataset` is supplied, a suite with all
        available data drift checks will be performed on the input
        data. See `DeepchecksDataDriftCheck` for a list of Deepchecks
        builtin checks that are compatible with this method.

        Args:
            dataset: Target dataset to be validated.
            comparison_dataset: Optional second dataset to be used for data
                comparison checks (e.g data drift checks).
            check_list: Optional list of ZenML Deepchecks check identifiers
                specifying the data validation checks to be performed.
                `DeepchecksDataIntegrityCheck` enum values should be used for
                single data validation checks and `DeepchecksDataDriftCheck`
                enum values for data comparison checks. If not supplied, the
                entire set of checks applicable to the input dataset(s)
                will be performed.
            dataset_kwargs: Additional keyword arguments to be passed to the
                Deepchecks `tabular.Dataset` or `vision.VisionData` constructor.
            check_kwargs: Additional keyword arguments to be passed to the
                Deepchecks check object constructors. Arguments are grouped for
                each check and indexed using the full check class name or
                check enum value as dictionary keys.
            run_kwargs: Additional keyword arguments to be passed to the
                Deepchecks Suite `run` method.
            kwargs: Additional keyword arguments (unused).

        Returns:
            A Deepchecks SuiteResult with the results of the validation.
        """
        check_enum: Type[DeepchecksValidationCheck]
        if comparison_dataset is None:
            check_enum = DeepchecksDataIntegrityCheck
        else:
            check_enum = DeepchecksDataDriftCheck

        return self._create_and_run_check_suite(
            check_enum=check_enum,
            reference_dataset=dataset,
            comparison_dataset=comparison_dataset,
            check_list=check_list,
            dataset_kwargs=dataset_kwargs,
            check_kwargs=check_kwargs,
            run_kwargs=run_kwargs,
        )

    def model_validation(
        self,
        dataset: Union[pd.DataFrame, DataLoader[Any]],
        model: Union[ClassifierMixin, Module],
        comparison_dataset: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
        **kwargs: Any,
    ) -> Any:
        """Run one or more Deepchecks model validation checks.

        Call this method to perform model validation checks (e.g. confusion
        matrix validation, performance reports, model error analyses, etc).
        A second dataset is required for model performance comparison tests
        (i.e. tests that identify changes in a model behavior by comparing how
        it performs on two different datasets).

        The `check_list` argument may be used to specify a custom set of
        Deepchecks model validation checks to perform, identified by
        `DeepchecksModelValidationCheck` and `DeepchecksModelDriftCheck` enum
        values. If omitted:

            * if the `comparison_dataset` is omitted, a suite with all available
            model validation checks will be performed on the input data. See
            `DeepchecksModelValidationCheck` for a list of Deepchecks builtin
            checks that are compatible with this method.

            * if the `comparison_dataset` is supplied, a suite with all
            available model comparison checks will be performed on the input
            data. See `DeepchecksModelValidationCheck` for a list of Deepchecks
            builtin checks that are compatible with this method.

        Args:
            dataset: Target dataset to be validated.
            model: Target model to be validated.
            comparison_dataset: Optional second dataset to be used for model
                comparison checks.
            check_list: Optional list of ZenML Deepchecks check identifiers
                specifying the model validation checks to be performed.
                `DeepchecksModelValidationCheck` enum values should be used for
                model validation checks and `DeepchecksModelDriftCheck` enum
                values for model comparison checks. If not supplied, the
                entire set of checks applicable to the input dataset(s)
                will be performed.
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
            A Deepchecks SuiteResult with the results of the validation.
        """
        check_enum: Type[DeepchecksValidationCheck]
        if comparison_dataset is None:
            check_enum = DeepchecksModelValidationCheck
        else:
            check_enum = DeepchecksModelDriftCheck

        return self._create_and_run_check_suite(
            check_enum=check_enum,
            reference_dataset=dataset,
            comparison_dataset=comparison_dataset,
            models=[model],
            check_list=check_list,
            dataset_kwargs=dataset_kwargs,
            check_kwargs=check_kwargs,
            run_kwargs=run_kwargs,
        )
