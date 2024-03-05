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

import inspect
import json
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

import yaml
from pydantic import BaseModel
from pydantic.decorator import ValidatedFunction
from pydantic.json import pydantic_encoder
from pydantic.utils import sequence_like

from zenml.utils import dict_utils, yaml_utils

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
            template = self._generate_template_for_model(
                self.instance_or_class
            )
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


class YAMLSerializationMixin(BaseModel):
    """Class to serialize/deserialize pydantic models to/from YAML."""

    def yaml(self, sort_keys: bool = False, **kwargs: Any) -> str:
        """YAML string representation..

        Args:
            sort_keys: Whether to sort the keys in the YAML representation.
            **kwargs: Kwargs to pass to the pydantic json(...) method.

        Returns:
            YAML string representation.
        """
        dict_ = json.loads(self.json(**kwargs, sort_keys=sort_keys))
        return yaml.dump(dict_, sort_keys=sort_keys)

    @classmethod
    def from_yaml(cls: Type[M], path: str) -> M:
        """Creates an instance from a YAML file.

        Args:
            path: Path to a YAML file.

        Returns:
            The model instance.
        """
        dict_ = yaml_utils.read_yaml(path)
        return cls.parse_obj(dict_)


def validate_function_args(
    __func: Callable[..., Any],
    __config: Dict[str, Any],
    *args: Any,
    **kwargs: Any,
) -> Dict[str, Any]:
    """Validates arguments passed to a function.

    This function validates that all arguments to call the function exist and
    that the types match.

    It raises a pydantic.ValidationError if the validation fails.

    Args:
        __func: The function for which the arguments are passed.
        __config: The pydantic config for the underlying model that is created
            to validate the types of the arguments.
        *args: Function arguments.
        **kwargs: Function keyword arguments.

    Returns:
        The validated arguments.
    """
    parameter_prefix = "zenml__"

    signature = inspect.signature(__func)
    parameters = [
        param.replace(name=f"{parameter_prefix}{param.name}")
        for param in signature.parameters.values()
    ]
    signature = signature.replace(parameters=parameters)

    def f() -> None:
        pass

    # We create a dummy function with the original function signature, but
    # add a prefix to all arguments to avoid potential clashes with pydantic
    # BaseModel attributes
    f.__signature__ = signature  # type: ignore[attr-defined]
    f.__annotations__ = {
        f"{parameter_prefix}{key}": annotation
        for key, annotation in __func.__annotations__.items()
    }

    validation_func = ValidatedFunction(f, config=__config)

    kwargs = {
        f"{parameter_prefix}{key}": value for key, value in kwargs.items()
    }
    model = validation_func.init_model_instance(*args, **kwargs)

    validated_args = {
        k[len(parameter_prefix) :]: v
        for k, v in model._iter()
        if k in model.__fields_set__
        or model.__fields__[k].default_factory
        or model.__fields__[k].default
    }

    return validated_args
