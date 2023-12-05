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
"""Deprecation utilities."""

import warnings
from typing import TYPE_CHECKING, Any, Dict, Set, Tuple, Type, Union

from pydantic import BaseModel, root_validator

from zenml.logger import get_logger

if TYPE_CHECKING:
    AnyClassMethod = classmethod[Any]  # type: ignore[type-arg]

logger = get_logger(__name__)

PREVIOUS_DEPRECATION_WARNINGS_ATTRIBUTE = "__previous_deprecation_warnings"


def deprecate_pydantic_attributes(
    *attributes: Union[str, Tuple[str, str]],
) -> "AnyClassMethod":
    """Utility function for deprecating and migrating pydantic attributes.

    **Usage**:
    To use this, you can specify it on any pydantic BaseModel subclass like
    this (all the deprecated attributes need to be non-required):

    ```python
    from pydantic import BaseModel
    from typing import Optional

    class MyModel(BaseModel):
        deprecated: Optional[int] = None

        old_name: Optional[str] = None
        new_name: str

        _deprecation_validator = deprecate_pydantic_attributes(
            "deprecated", ("old_name", "new_name")
        )
    ```

    Args:
        *attributes: List of attributes to deprecate. This is either the name
            of the attribute to deprecate, or a tuple containing the name of
            the deprecated attribute and it's replacement.

    Returns:
        Pydantic validator class method to be used on BaseModel subclasses
        to deprecate or migrate attributes.
    """

    @root_validator(pre=True, allow_reuse=True)
    def _deprecation_validator(
        cls: Type[BaseModel], values: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Pydantic validator function for deprecating pydantic attributes.

        Args:
            cls: The class on which the attributes are defined.
            values: All values passed at model initialization.

        Raises:
            AssertionError: If either the deprecated or replacement attribute
                don't exist.
            TypeError: If the deprecated attribute is a required attribute.
            ValueError: If the deprecated attribute and replacement attribute
                contain different values.

        Returns:
            Input values with potentially migrated values.
        """
        previous_deprecation_warnings: Set[str] = getattr(
            cls, PREVIOUS_DEPRECATION_WARNINGS_ATTRIBUTE, set()
        )

        def _warn(message: str, attribute: str) -> None:
            """Logs and raises a warning for a deprecated attribute.

            Args:
                message: The warning message.
                attribute: The name of the attribute.
            """
            if attribute not in previous_deprecation_warnings:
                logger.warning(message)
                previous_deprecation_warnings.add(attribute)

            warnings.warn(
                message,
                DeprecationWarning,
            )

        for attribute in attributes:
            if isinstance(attribute, str):
                deprecated_attribute = attribute
                replacement_attribute = None
            else:
                deprecated_attribute, replacement_attribute = attribute

                assert (
                    replacement_attribute in cls.__fields__
                ), f"Unable to find attribute {replacement_attribute}."

            assert (
                deprecated_attribute in cls.__fields__
            ), f"Unable to find attribute {deprecated_attribute}."

            if cls.__fields__[deprecated_attribute].required:
                raise TypeError(
                    f"Unable to deprecate attribute '{deprecated_attribute}' "
                    f"of class {cls.__name__}. In order to deprecate an "
                    "attribute, it needs to be a non-required attribute. "
                    "To do so, mark the attribute with an `Optional[...] type "
                    "annotation."
                )

            if values.get(deprecated_attribute, None) is None:
                continue

            if replacement_attribute is None:
                _warn(
                    message=f"The attribute `{deprecated_attribute}` of class "
                    f"`{cls.__name__}` will be deprecated soon.",
                    attribute=deprecated_attribute,
                )
                continue

            _warn(
                message=f"The attribute `{deprecated_attribute}` of class "
                f"`{cls.__name__}` will be deprecated soon. Use the "
                f"attribute `{replacement_attribute}` instead.",
                attribute=deprecated_attribute,
            )

            if values.get(replacement_attribute, None) is None:
                logger.debug(
                    "Migrating value of deprecated attribute %s to "
                    "replacement attribute %s.",
                    deprecated_attribute,
                    replacement_attribute,
                )
                values[replacement_attribute] = values.pop(
                    deprecated_attribute
                )
            elif values[deprecated_attribute] != values[replacement_attribute]:
                raise ValueError(
                    "Got different values for deprecated attribute "
                    f"{deprecated_attribute} and replacement "
                    f"attribute {replacement_attribute}."
                )
            else:
                # Both values are identical, no need to do anything
                pass

        setattr(
            cls,
            PREVIOUS_DEPRECATION_WARNINGS_ATTRIBUTE,
            previous_deprecation_warnings,
        )

        return values

    return _deprecation_validator
