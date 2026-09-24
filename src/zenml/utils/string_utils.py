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
import functools
import random
import string
from typing import Any, Callable, Dict, Optional, TypeVar, cast

from pydantic import BaseModel

from zenml.constants import BANNED_NAME_CHARACTERS
from zenml.utils.time_utils import utc_now

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
    """Generate a random human-readable string of given length.

    Args:
        length: Length of string

    Returns:
        Random human-readable string.
    """
    random.seed()
    return "".join(random.choices(string.ascii_letters, k=length))


_URI_BANNED_CHARACTERS = ["<", ">", ":", '"', "/", "\\", "|", "?", "*"]


def sanitize_uri_path_component(component: str) -> str:
    """Replace characters that are unsafe in a URI or filesystem path component.

    Args:
        component: The path component to sanitize.

    Returns:
        The component with banned characters replaced by underscores.
    """
    for banned_character in _URI_BANNED_CHARACTERS:
        component = component.replace(banned_character, "_")
    return component


def validate_name(model: BaseModel, name_field: str = "name") -> None:
    """Validator to ensure that the given name has only allowed characters.

    Args:
        model: The model to validate.
        name_field: The name of the field to validate.

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

    if name := getattr(model, name_field, None):
        diff = "".join(set(name).intersection(set(BANNED_NAME_CHARACTERS)))
        if diff:
            msg = (
                f"The {name_field} `{name}` of the `{type_}` contains "
                f"the following forbidden characters: `{diff}`."
            )
            raise ValueError(msg)
    else:
        raise ValueError(
            f"The class `{cls_name}` has no attribute `{name_field}` "
            f"or it is set to `None`. Cannot validate the {name_field}."
        )


def format_name_template(
    name_template: str,
    substitutions: Optional[Dict[str, str]] = None,
) -> str:
    """Formats a name template with the given arguments.

    Default substitutions for `{date}` and `{time}` placeholders will be used if
    not included in the provided substitutions.

    Args:
        name_template: The name template to format.
        substitutions: Substitutions to use in the template.

    Returns:
        The formatted name template.

    Raises:
        KeyError: If a key in template is missing in the substitutions.
        ValueError: If the formatted name is empty.
    """
    substitutions = dict(substitutions or {})

    if ("date" not in substitutions and "{date}" in name_template) or (
        "time" not in substitutions and "{time}" in name_template
    ):
        from zenml import get_step_context

        try:
            pr = get_step_context().pipeline_run
            start_time = pr.start_time
            substitutions.update(pr.config.substitutions)
        except RuntimeError:
            start_time = None

        if start_time is None:
            start_time = utc_now()
        substitutions.setdefault("date", start_time.strftime("%Y_%m_%d"))
        substitutions.setdefault("time", start_time.strftime("%H_%M_%S_%f"))

    try:
        formatted_name = name_template.format(**substitutions)
    except KeyError as e:
        raise KeyError(
            f"Could not format the name template `{name_template}`. "
            f"Missing key: {e}"
        )

    if not formatted_name:
        raise ValueError("Empty names are not allowed.")

    return formatted_name


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

        return cast(V, type(value).model_validate(model_values))  # type: ignore[redundant-cast]
    elif isinstance(value, Dict):
        return cast(
            V, {substitute_(k): substitute_(v) for k, v in value.items()}
        )
    elif isinstance(value, (list, set, tuple)):
        return cast(V, type(value)(substitute_(v) for v in value))
    elif isinstance(value, str):
        return cast(V, substitution_func(value))

    return value


def truncate_str(value: str, max_length: int, suffix: str = "...") -> str:
    """Truncate a string to a maximum length, appending a suffix if it is shortened.

    This is useful for rendering long strings (e.g. artifact URIs, step names,
    or run IDs) cleanly in CLI tables and Rich console panels without overflowing
    fixed-width terminal columns.

    Examples::

        >>> truncate_str("a very long pipeline run name", max_length=20)
        'a very long pipeli...'

        >>> truncate_str("short", max_length=20)
        'short'

        >>> truncate_str("exactly20characterss", max_length=20)
        'exactly20characterss'

    Args:
        value: The original string to truncate.
        max_length: The maximum allowed character length of the output (including
            the suffix). Must be greater than or equal to the length of
            ``suffix``.
        suffix: A suffix appended to indicate truncation. Defaults to ``"..."``.

    Returns:
        str: The original string if it fits within ``max_length``, otherwise the
            string truncated to ``max_length - len(suffix)`` characters with
            ``suffix`` appended.

    Raises:
        ValueError: If ``max_length`` is less than the length of ``suffix``,
            making it impossible to construct a valid truncated result.
    """
    if max_length < len(suffix):
        raise ValueError(
            f"max_length ({max_length}) must be >= len(suffix) ({len(suffix)}). "
            "Cannot truncate with a suffix longer than the allowed output."
        )
    if len(value) <= max_length:
        return value
    return value[: max_length - len(suffix)] + suffix


def slugify(value: str, separator: str = "-") -> str:
    """Convert a string into a URL/filesystem-safe slug.

    Converts whitespace and non-alphanumeric characters to the given separator,
    collapses consecutive separators, and lowercases the result. This is useful
    for generating deterministic, human-readable identifiers from display names
    (e.g., pipeline names, stack names) for use in URLs, file paths, or
    run labels.

    Examples::

        >>> slugify("My Pipeline Run!")
        'my-pipeline-run'

        >>> slugify("Hello  World__2024", separator="_")
        'hello_world_2024'

    Args:
        value: The string to slugify.
        separator: The separator character to use between words. Defaults to
            ``"-"``.

    Returns:
        str: A lowercased, separator-delimited slug derived from ``value``.
    """
    import re

    # Lowercase and replace non-alphanumeric characters with the separator
    slug = re.sub(r"[^a-zA-Z0-9]+", separator, value.strip().lower())
    # Remove leading and trailing separators
    slug = slug.strip(separator)
    return slug

