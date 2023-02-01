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
"""Definition of the Deepchecks validation check type base classes."""

from typing import Type

from deepchecks.core.checks import BaseCheck

from zenml.integrations.deepchecks.enums import (
    DeepchecksCheckType,
    DeepchecksModuleName,
)
from zenml.logger import get_logger
from zenml.utils.enum_utils import StrEnum
from zenml.utils.source_utils import import_class_by_path

logger = get_logger(__name__)


class BaseDeepchecksValidationCheck(StrEnum):
    """Base class for all Deepchecks categories of validation checks.

    This base class defines some conventions used for all enum values used to
    identify the various validation checks that can be performed with
    Deepchecks:

      * enum values represent fully formed class paths pointing to Deepchecks
      BaseCheck subclasses
      * all tabular data checks are located under the
      `deepchecks.tabular.checks` module sub-tree
      * all computer vision data checks are located under the
      `deepchecks.vision.checks` module sub-tree
    """

    @classmethod
    def get_deepchecks_module(cls) -> DeepchecksModuleName:
        """Return the Deepchecks module that contains the checks in this class.

        E.g., `tabular` if the checks are part of `deepchecks.tabular`.

        Currently, only `tabular` and `vision` are supported.

        Returns:
            The Deepchecks module that contains the checks in this class.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError(
            "Subclasses of `BaseDeepchecksValidationCheck` must implement "
            "the `get_deepchecks_module` method."
        )

    @classmethod
    def get_check_type(cls) -> DeepchecksCheckType:
        """Return the type of the check.

        This information is required to determine which checks to perform by
        default when a user runs a Deepchecks step without explicitly specifying
        which checks to use.

        Currently, the following check types are supported:
            - `data_validation`: A data validation check.
            - `data_drift`: A data drift check.
            - `model_validation`: A model validation check.
            - `model_drift`: A model drift check.

        Returns:
            The type of the check.

        Raises:
            NotImplementedError: If the method is not implemented by a subclass.
        """
        raise NotImplementedError(
            "Subclasses of `BaseDeepchecksValidationCheck` must implement "
            "the `get_check_type` method."
        )

    @classmethod
    def validate_check_name(cls, check_name: str) -> None:
        """Validate a Deepchecks check identifier.

        Args:
            check_name: Identifies a builtin Deepchecks check. The identifier
                must be formatted as `deepchecks.{tabular|vision}.checks.<...>.<class-name>`.

        Raises:
            ValueError: If the check identifier does not follow the convention
                used by ZenML to identify Deepchecks builtin checks.
        """
        base_module_path = f"deepchecks.{cls.get_deepchecks_module()}.checks."
        if not check_name.startswith(base_module_path):
            raise ValueError(
                f"The supplied Deepcheck check identifier does not follow the "
                f"convention used by ZenML: `{check_name}`. The identifier"
                f"must be formatted as `{base_module_path}...` and must be "
                f"resolvable to a valid Deepchecks BaseCheck subclass."
            )

    @classmethod
    def get_check_class(cls, check_name: str) -> Type[BaseCheck]:
        """Get the Deepchecks check class associated with an enum value or a custom check name.

        Args:
            check_name: Identifies a builtin Deepchecks check. The identifier
                must be formatted as `deepchecks.{tabular|vision}.checks.<class-name>`
                and must be resolvable to a valid Deepchecks BaseCheck class.

        Returns:
            The Deepchecks check class associated with this enum value.

        Raises:
            ValueError: If the check name could not be converted to a valid
                Deepchecks check class. This can happen for example if the enum
                values fall out of sync with the Deepchecks code base or if a
                custom check name is supplied that cannot be resolved to a valid
                Deepchecks BaseCheck class.
        """
        cls.validate_check_name(check_name)

        try:
            check_class = import_class_by_path(check_name)
        except AttributeError:
            raise ValueError(
                f"Could not map the `{check_name}` check identifier to a valid "
                f"Deepchecks check class."
            )

        if not issubclass(check_class, BaseCheck):
            raise ValueError(
                f"The `{check_name}` check identifier is mapped to an invalid "
                f"data type. Expected a {str(BaseCheck)} subclass, but instead "
                f"got: {str(check_class)}."
            )

        if check_name not in cls.values():
            logger.warning(
                f"You are using a custom Deepchecks check identifier that is "
                f"not listed in the `{str(cls)}` enum type. This could lead "
                f"to unexpected behavior."
            )

        return check_class

    @property
    def check_class(self) -> Type[BaseCheck]:
        """Convert the enum value to a valid Deepchecks check class.

        Returns:
            The Deepchecks check class associated with the enum value.
        """
        return self.get_check_class(self.value)


class DeepchecksDataValidationCheck(BaseDeepchecksValidationCheck):
    """Mixin class for all Deepchecks data validation checks.

    These are checks that require a single dataset as input.
    """

    @classmethod
    def get_check_type(cls) -> DeepchecksCheckType:
        """Return the type of the check.

        Returns:
            The type of the check.
        """
        return DeepchecksCheckType.DATA_VALIDATION


class DeepchecksDataDriftCheck(BaseDeepchecksValidationCheck):
    """Mixin class for all Deepchecks data drift checks.

    These are checks that require two datasets as input.
    """

    @classmethod
    def get_check_type(cls) -> DeepchecksCheckType:
        """Return the type of the check.

        Returns:
            The type of the check.
        """
        return DeepchecksCheckType.DATA_DRIFT


class DeepchecksModelValidationCheck(BaseDeepchecksValidationCheck):
    """Mixin class for all Deepchecks model validation checks.

    These are checks that require a dataset and a mandatory model as input.
    """

    @classmethod
    def get_check_type(cls) -> DeepchecksCheckType:
        """Return the type of the check.

        Returns:
            The type of the check.
        """
        return DeepchecksCheckType.MODEL_VALIDATION


class DeepchecksModelDriftCheck(BaseDeepchecksValidationCheck):
    """Mixin class for all Deepchecks model drift checks.

    These are checks that require two datasets and a mandatory model as input.
    """

    @classmethod
    def get_check_type(cls) -> DeepchecksCheckType:
        """Return the type of the check.

        Returns:
            The type of the check.
        """
        return DeepchecksCheckType.MODEL_DRIFT
