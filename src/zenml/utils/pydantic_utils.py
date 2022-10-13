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
"""Utilities for pydantic models."""
import json
from typing import Any, Dict, Optional, Type, TypeVar, Union, cast

from pydantic import BaseModel
from pydantic.json import pydantic_encoder
from pydantic.utils import sequence_like

from zenml.utils import dict_utils

M = TypeVar("M", bound="BaseModel")


def update_model(
    original: M,
    update: Union["BaseModel", Dict[str, Any]],
    recursive: bool = True,
    exclude_none: bool = True,
) -> M:
    """Updates a pydantic model.

    Args:
        original: The model to update.
        update: The update values.
        recursive: If `True`, dictionary values will be updated recursively.
        exclude_none: If `True`, `None` values in the update dictionary
            will be removed.

    Returns:
        The updated model.
    """
    if isinstance(update, Dict):
        if exclude_none:
            update_dict = dict_utils.remove_none_values(
                update, recursive=recursive
            )
        else:
            update_dict = update
    else:
        update_dict = update.dict(exclude_unset=True)

    original_dict = original.dict(exclude_unset=True)
    if recursive:
        values = dict_utils.recursive_update(original_dict, update_dict)
    else:
        values = {**original_dict, **update_dict}

    return original.__class__(**values)


class TemplateGenerator:
    """Class to generate templates for pydantic models or classes."""

    def __init__(
        self, instance_or_class: Union[BaseModel, Type[BaseModel]]
    ) -> None:
        """Initializes the template generator.

        Args:
            instance_or_class: The pydantic model or model class for which to
                generate a template.
        """
        self.instance_or_class = instance_or_class

    def run(self) -> Dict[str, Any]:
        """Generates the template.

        Returns:
            The template dictionary.
        """
        if isinstance(self.instance_or_class, BaseModel):
            template = self._generate_template_for_model(self.instance_or_class)
        else:
            template = self._generate_template_for_model_class(
                self.instance_or_class
            )

        # Convert to json in an intermediate step so we can leverage Pydantic's
        # encoder to support types like UUID and datetime
        json_string = json.dumps(template, default=pydantic_encoder)
        return cast(Dict[str, Any], json.loads(json_string))

    def _generate_template_for_model(self, model: BaseModel) -> Dict[str, Any]:
        """Generates a template for a pydantic model.

        Args:
            model: The model for which to generate the template.

        Returns:
            The model template.
        """
        template = self._generate_template_for_model_class(model.__class__)

        for name in model.__fields_set__:
            value = getattr(model, name)
            template[name] = self._generate_template_for_value(value)

        return template

    def _generate_template_for_model_class(
        self,
        model_class: Type[BaseModel],
    ) -> Dict[str, Any]:
        """Generates a template for a pydantic model class.

        Args:
            model_class: The model class for which to generate the template.

        Returns:
            The model class template.
        """
        template: Dict[str, Any] = {}

        for name, field in model_class.__fields__.items():
            if self._is_model_class(field.outer_type_):
                template[name] = self._generate_template_for_model_class(
                    field.outer_type_
                )
            elif field.outer_type_ is Optional and self._is_model_class(
                field.type_
            ):
                template[name] = self._generate_template_for_model_class(
                    field.type_
                )
            else:
                template[name] = field._type_display()

        return template

    def _generate_template_for_value(self, value: Any) -> Any:
        """Generates a template for an arbitrary value.

        Args:
            value: The value for which to generate the template.

        Returns:
            The value template.
        """
        if isinstance(value, Dict):
            return {
                k: self._generate_template_for_value(v)
                for k, v in value.items()
            }
        elif sequence_like(value):
            return [self._generate_template_for_value(v) for v in value]
        elif isinstance(value, BaseModel):
            return self._generate_template_for_model(value)
        else:
            return value

    @staticmethod
    def _is_model_class(value: Any) -> bool:
        """Checks if the given value is a pydantic model class.

        Args:
            value: The value to check.

        Returns:
            If the value is a pydantic model class.
        """
        return isinstance(value, type) and issubclass(value, BaseModel)
