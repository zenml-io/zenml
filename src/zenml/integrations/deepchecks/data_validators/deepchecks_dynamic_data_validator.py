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
"""Implementation of the dynamic Deepchecks data validator."""

from typing import Any, ClassVar, Dict, Optional, Sequence, Type

from deepchecks.core.suite import SuiteResult

# not part of deepchecks.tabular.checks
from zenml.data_validators.base_data_validator import BaseDataValidatorFlavor
from zenml.integrations.deepchecks.data_validators.base_deepchecks_data_validator import (
    BaseDeepchecksDataValidator,
)
from zenml.integrations.deepchecks.data_validators.deepchecks_tabular_data_validator import (
    DeepchecksTabularDataValidator,
)
from zenml.integrations.deepchecks.data_validators.deepchecks_vision_data_validator import (
    DeepchecksVisionDataValidator,
)
from zenml.integrations.deepchecks.enums import DeepchecksModuleName
from zenml.integrations.deepchecks.flavors.deepchecks_data_validator_flavor import (
    DeepchecksDataValidatorFlavor,
)
from zenml.logger import get_logger

logger = get_logger(__name__)


class DeepchecksDynamicDataValidator(DeepchecksVisionDataValidator):
    """Dynamic data validator that can handle both tabular and vision data.

    This class overrides the `data_validation` and `model_validation` methods
    to dynamically resolve the correct Deepchecks module to use based on the
    input data. It then assumes the behaviour of the data validator that can
    handle that Deepchecks module.

    This is needed for backwards compatibility with the old
    `DeepchecksDataValidator` from ZenML < 0.33.0 that could handle both tabular
    and vision data.
    """

    NAME: ClassVar[str] = "Deepchecks Dynamic (Deprecated)"
    FLAVOR: ClassVar[
        Type[BaseDataValidatorFlavor]
    ] = DeepchecksDataValidatorFlavor

    def data_validation(
        self,
        dataset: Any,
        comparison_dataset: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
        **kwargs: Any,
    ) -> SuiteResult:
        """Run one or more Deepchecks data validation checks on a dataset.

        This method is overridden to change behaviour based on the input types.

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
        deepchecks_module = self._resolve_deepchecks_module(
            reference_dataset=dataset,
            comparison_dataset=comparison_dataset,
            model=None,
        )
        self._face_off(deepchecks_module)
        return super().data_validation(
            dataset=dataset,
            comparison_dataset=comparison_dataset,
            check_list=check_list,
            dataset_kwargs=dataset_kwargs,
            check_kwargs=check_kwargs,
            run_kwargs=run_kwargs,
            **kwargs,
        )

    def model_validation(
        self,
        dataset: Any,
        model: Any,
        comparison_dataset: Optional[Any] = None,
        check_list: Optional[Sequence[str]] = None,
        dataset_kwargs: Dict[str, Any] = {},
        check_kwargs: Dict[str, Dict[str, Any]] = {},
        run_kwargs: Dict[str, Any] = {},
        **kwargs: Any,
    ) -> Any:
        """Run one or more Deepchecks model validation checks.

        This method is overridden to change behaviour based on the input types.

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
        deepchecks_module = self._resolve_deepchecks_module(
            reference_dataset=dataset,
            comparison_dataset=comparison_dataset,
            model=model,
        )
        self._face_off(deepchecks_module)
        return super().model_validation(
            dataset=dataset,
            model=model,
            comparison_dataset=comparison_dataset,
            check_list=check_list,
            dataset_kwargs=dataset_kwargs,
            check_kwargs=check_kwargs,
            run_kwargs=run_kwargs,
            **kwargs,
        )

    def _resolve_deepchecks_module(
        self, reference_dataset: Any, comparison_dataset: Any, model: Any
    ) -> DeepchecksModuleName:
        """Resolve the deepchecks module that can handle the input data.

        Detects what type of check to perform (tabular or computer vision) from
        the dataset/model datatypes. At the same time, validate the combination
        of data types used for dataset and model arguments.

        Returns:
            The deepchecks module to use for the check.

        Raises:
            TypeError: If the combination of dataset types and model types is
            not supported.
        """
        is_tabular = False
        is_vision = False

        tabular_data_types = (
            DeepchecksTabularDataValidator.supported_dataset_types
        )
        vision_data_types = (
            DeepchecksVisionDataValidator.supported_dataset_types
        )
        tabular_model_types = (
            DeepchecksTabularDataValidator.supported_model_types
        )
        vision_model_types = (
            DeepchecksVisionDataValidator.supported_model_types
        )

        for dataset in [reference_dataset, comparison_dataset]:
            if dataset is None:
                continue
            if isinstance(dataset, tabular_data_types):
                is_tabular = True
            elif isinstance(dataset, vision_data_types):
                is_vision = True
            else:
                raise TypeError(
                    f"Unsupported dataset data type found: {type(dataset)}. "
                    f"Supported data types are {tabular_data_types} for "
                    f"tabular data and {vision_data_types} for computer vision "
                    f"data."
                )

        if model:
            if isinstance(model, tabular_model_types):
                is_tabular = True
            elif isinstance(model, vision_model_types):
                is_vision = True
            else:
                raise TypeError(
                    f"Unsupported model data type found: {type(model)}. "
                    f"Supported data types are {tabular_model_types} for "
                    f"tabular data and {vision_model_types} for computer "
                    f"vision data."
                )

        if is_tabular and not is_vision:
            return DeepchecksModuleName.TABULAR
        elif is_vision and not is_tabular:
            return DeepchecksModuleName.VISION
        else:
            raise TypeError(
                f"Tabular and computer vision data types used for datasets and "
                f"models cannot be mixed. They must all belong to the same "
                f"category. Supported data types for tabular data are "
                f"{tabular_data_types} for datasets and {tabular_model_types} "
                f"for models. Supported data types for computer vision data "
                f"are {vision_data_types} for datasets and "
                f"{vision_model_types} for models."
            )

    def _face_off(self, deepchecks_module: DeepchecksModuleName) -> None:
        """Assume the identity of another data validator class.

        This method is used to dynamically change the behaviour of this class
        to be able to handle multiple deepchecks modules.

        Args:
            deepchecks_module: The deepchecks module which this data validator
                needs to handle.
        """
        validator_class: Type["BaseDeepchecksDataValidator"]
        if deepchecks_module == DeepchecksModuleName.TABULAR:
            validator_class = DeepchecksTabularDataValidator
        else:
            validator_class = DeepchecksVisionDataValidator

        for attr in [
            "deepchecks_module",
            "supported_dataset_types",
            "supported_model_types",
            "dataset_class",
            "suite_class",
            "full_suite",
            "data_validation_check_enum",
            "data_drift_check_enum",
            "model_validation_check_enum",
            "model_drift_check_enum",
        ]:
            setattr(self, attr, getattr(validator_class, attr))
