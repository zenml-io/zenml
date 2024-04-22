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
from json.decoder import JSONDecodeError
from typing import Any, Callable, Dict, Optional, Type, TypeVar, Union, cast

import yaml
from pydantic import BaseModel, ValidationInfo

# TODO: Investigate if we can solve this import a different way.
from pydantic.deprecated.decorator import ValidatedFunction
from pydantic.json import pydantic_encoder
from pydantic.v1.utils import sequence_like

from zenml.logger import get_logger
from zenml.utils import dict_utils, yaml_utils

logger = get_logger(__name__)

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
            **kwargs: Kwargs to pass to the pydantic model_dump(...) method.

        Returns:
            YAML string representation.
        """
        dict_ = json.loads(
            json.dumps(
                self.model_dump(mode="json", **kwargs), sort_keys=sort_keys
            )
        )
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
        return cls.model_validate(dict_)


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


def model_validator_data_handler(
    raw_data: Any,
    base_class: Type[BaseModel],
    validation_info: ValidationInfo,
) -> Dict[str, Any]:
    """Utility function to parse raw input data of varying types to a dict.

    With the change to pydantic v2, validators which operate with "before"
    (or previously known as the "pre" parameter) are getting "Any" types of raw
    input instead of a "Dict[str, Any]" as before. Depending on the use-case,
    this can create conflicts after the migration and this function will be
    used as a helper function to handle different types of raw input data.

    A code snippet to showcase how the behaviour changes. The "before" validator
    prints the type of the input:

        class Base(BaseModel):
            a: int = 3

        class MyClass(Base):
            @model_validator(mode="before")
            @classmethod
            def before_validator(cls, data: Any) -> Any:
                print(type(data))
                return {}

        one = MyClass() # prints "<class 'dict'>"
        MyClass.model_validate(one)  # prints NOTHING, it is already validated
        MyClass.model_validate("asdf")  # prints "<class 'str'>", fails without the modified return.
        MyClass.model_validate(RandomClass())  # prints "<class 'RandomClass'>", fails without the modified return.
        MyClass.model_validate(Base())  # prints "<class 'Base'>", fails without the modified return.
        MyClass.model_validate_json(json.dumps("aria"))  # prints "<class 'str'>", fails without the modified return.
        MyClass.model_validate_json(json.dumps([1]))  # prints "<class 'list'>", fails without the modified return.
        MyClass.model_validate_json(one.model_dump_json())  # prints "<class 'dict'>"

    Args:
        raw_data: The raw data passed to the validator, can be "Any" type.
        base_class: The class that the validator belongs to
        validation_info: Extra information about the validation process.

    Raises:
        TypeError: if the type of the data is not processable.

    Returns:
        A dictionary which will be passed to the eventual validator of pydantic.
    """
    if validation_info.mode == "python":
        # This is mode is only active if people validate objects using pythonic
        # raw data such as MyClass(...) or MyClass.model_validate()

        if isinstance(raw_data, dict):
            # In most cases, this is the behaviour as the raw input is a dict
            return raw_data

        elif isinstance(raw_data, base_class):
            # In some cases, we pass the same object type to the validation
            # in such cases, it is critical we keep the original structure of
            # fields that are already set.
            return dict(raw_data)

        elif issubclass(base_class, raw_data.__class__):
            # There are a few occurrences where the annotation of the field is
            # denoted by a subclass, and we use the instance of its super class
            # as the raw input. In such cases we will use the same approach as
            # before, while raising a debug message.
            logger.debug(
                f"During the validation of a `{base_class}` object, an instance"
                f"of `{raw_data.__class__}` (super class of `{base_class}`) "
                f"has been passed as raw input. This might lead to unexpected "
                f"behaviour in case `{base_class}` have features which can not"
                f"be extracted from an instance of a `{raw_data.__class__}`."
            )
            return dict(raw_data)

        elif isinstance(raw_data, str):
            # If the raw input is a raw string, we can try to use the `json`
            # module to parse it. The resulting data needs to be a proper
            # dict for us to pass it to the validation process.
            try:
                json_data = json.loads(raw_data)

                if isinstance(json_data, dict):
                    return json_data
                else:
                    raise TypeError("The resulting json data is not a dict!")

            except (TypeError, JSONDecodeError) as e:
                raise TypeError(
                    "The raw json input string can not be converted to a "
                    f"dict: {e}"
                )
        else:
            raise TypeError(
                "Unsupported type of raw input data for the `python` validation"
                "mode of the pydantic class. Please consider changing the way "
                f"you are creating using the `{base_class}` or instead use"
                f"`{base_class}.model_validate_json()`."
            )

    elif validation_info.mode == "json":
        # This is mode is only active if people validate objects using json
        # input data such as MyClass.model_validate_json()
        if isinstance(raw_data, dict):
            return raw_data
        else:
            raise TypeError(
                f"The resulting JSON data {raw_data} is not a dict, therefore"
                f"can not be used by the validation process."
            )
    else:
        # Unknown validation mode
        raise ValueError(f"Unknown validation mode. {validation_info.mode}")


def before_validator_handler(
    method: Callable[[Any, Any], Any],
) -> Callable[[Any, Any, Any], Any]:
    """Decorator to handle the raw input data for pydantic model validators.

    Args:
        method: the class method with the actual validation logic.

    Returns:
        the validator method
    """

    def before_validator(
        cls, data: Any, validation_info: ValidationInfo
    ) -> Any:
        """Wrapper method to handle the raw data.

        Args:
            cls: the class handler
            data: the raw input data
            validation_info: the context of the validation.

        Returns:
            the validated data
        """
        data = model_validator_data_handler(
            raw_data=data, base_class=cls, validation_info=validation_info
        )
        return method(cls=cls, data=data)

    return before_validator
