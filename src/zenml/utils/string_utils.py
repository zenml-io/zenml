#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
"""Utils for strings."""

import base64
import datetime
import functools
import random
import string
from typing import Any, Callable, Dict, TypeVar, cast

from pydantic import BaseModel

from zenml.constants import BANNED_NAME_CHARACTERS

V = TypeVar("V", bound=Any)


def get_human_readable_time(seconds: float) -> str:
    """Convert seconds into a human-readable string.

    Args:
        seconds: The number of seconds to convert.

    Returns:
        A human-readable string.
    """
    prefix = "-" if seconds < 0 else ""
    seconds = abs(seconds)
    int_seconds = int(seconds)
    days, int_seconds = divmod(int_seconds, 86400)
    hours, int_seconds = divmod(int_seconds, 3600)
    minutes, int_seconds = divmod(int_seconds, 60)
    if days > 0:
        time_string = f"{days}d{hours}h{minutes}m{int_seconds}s"
    elif hours > 0:
        time_string = f"{hours}h{minutes}m{int_seconds}s"
    elif minutes > 0:
        time_string = f"{minutes}m{int_seconds}s"
    else:
        time_string = f"{seconds:.3f}s"

    return prefix + time_string


def get_human_readable_filesize(bytes_: int) -> str:
    """Convert a file size in bytes into a human-readable string.

    Args:
        bytes_: The number of bytes to convert.

    Returns:
        A human-readable string.
    """
    size = abs(float(bytes_))
    for unit in ["B", "KiB", "MiB", "GiB"]:
        if size < 1024.0 or unit == "GiB":
            break
        size /= 1024.0

    return f"{size:.2f} {unit}"


def b64_encode(input_: str) -> str:
    """Returns a base 64 encoded string of the input string.

    Args:
        input_: The input to encode.

    Returns:
        Base64 encoded string.
    """
    input_bytes = input_.encode()
    encoded_bytes = base64.b64encode(input_bytes)
    return encoded_bytes.decode()


def b64_decode(input_: str) -> str:
    """Returns a decoded string of the base 64 encoded input string.

    Args:
        input_: Base64 encoded string.

    Returns:
        Decoded string.
    """
    encoded_bytes = input_.encode()
    decoded_bytes = base64.b64decode(encoded_bytes)
    return decoded_bytes.decode()


def random_str(length: int) -> str:
    """Generate a random human readable string of given length.

    Args:
        length: Length of string

    Returns:
        Random human-readable string.
    """
    random.seed()
    return "".join(random.choices(string.ascii_letters, k=length))


def validate_name(model: BaseModel) -> None:
    """Validator to ensure that the given name has only allowed characters.

    Args:
        model: The model to validate.

    Raises:
        ValueError: If the name has invalid characters.
    """
    cls_name = model.__class__.__name__
    if cls_name.endswith("Base"):
        type_ = cls_name[:-4]
    elif cls_name.endswith("Request"):
        type_ = cls_name[:-7]
    else:
        type_ = cls_name

    if name := getattr(model, "name", None):
        diff = "".join(set(name).intersection(set(BANNED_NAME_CHARACTERS)))
        if diff:
            msg = (
                f"The name `{name}` of the `{type_}` contains "
                f"the following forbidden characters: `{diff}`."
            )
            raise ValueError(msg)
    else:
        raise ValueError(
            f"The class `{cls_name}` has no attribute `name` "
            "or it is set to `None`. Cannot validate the name."
        )


def format_name_template(
    name_template: str,
    **kwargs: str,
) -> str:
    """Formats a name template with the given arguments.

    By default, ZenML support Date and Time placeholders.
    E.g. `my_run_{date}_{time}` will be formatted as `my_run_1970_01_01_00_00_00`.
    Extra placeholders need to be explicitly passed in as kwargs.

    Args:
        name_template: The name template to format.
        **kwargs: The arguments to replace in the template.

    Returns:
        The formatted name template.
    """
    kwargs["date"] = kwargs.get(
        "date",
        datetime.datetime.now(datetime.timezone.utc).strftime("%Y_%m_%d"),
    )
    kwargs["time"] = kwargs.get(
        "time",
        datetime.datetime.now(datetime.timezone.utc).strftime("%H_%M_%S_%f"),
    )
    try:
        return name_template.format(**kwargs)
    except KeyError as e:
        raise KeyError(
            f"Could not format the name template `{name_template}`. "
            f"Missing key: {e}"
        )


def substitute_string(value: V, substitution_func: Callable[[str], str]) -> V:
    """Recursively substitute strings in objects.

    Args:
        value: An object in which the strings should be recursively substituted.
            This can be a pydantic model, dict, set, list, tuple or any
            primitive type.
        substitution_func: The function that does the actual string
            substitution.

    Returns:
        The object with the substitution function applied to all string values.
    """
    substitute_ = functools.partial(
        substitute_string, substitution_func=substitution_func
    )

    if isinstance(value, BaseModel):
        model_values = {}

        for k, v in value.__iter__():
            new_value = substitute_(v)

            if k not in value.model_fields_set and new_value == getattr(
                value, k
            ):
                # This is a default value on the model and was not set
                # explicitly. In this case, we don't include it in the model
                # values to keep the `exclude_unset` behavior the same
                continue

            model_values[k] = new_value

        return cast(V, type(value).model_validate(model_values))
    elif isinstance(value, Dict):
        return cast(
            V, {substitute_(k): substitute_(v) for k, v in value.items()}
        )
    elif isinstance(value, (list, set, tuple)):
        return cast(V, type(value)(substitute_(v) for v in value))
    elif isinstance(value, str):
        return cast(V, substitution_func(value))

    return value
