#  Copyright (c) ZenML GmbH 2024. All Rights Reserved.
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
"""Notebook utilities."""

import hashlib
from typing import Any, Callable, Optional, TypeVar, Union

from zenml.environment import Environment
from zenml.logger import get_logger

ZENML_NOTEBOOK_CELL_CODE_ATTRIBUTE_NAME = "__zenml_notebook_cell_code__"

AnyObject = TypeVar("AnyObject", bound=Any)

logger = get_logger(__name__)


def is_defined_in_notebook_cell(obj: Any) -> bool:
    """Check whether an object is defined in a notebook cell.

    Args:
        obj: The object to check.

    Returns:
        Whether the object is defined in a notebook cell.
    """
    if not Environment.in_notebook():
        return False

    module_name = getattr(obj, "__module__", None)
    return module_name == "__main__"


def enable_notebook_code_extraction(
    _obj: Optional["AnyObject"] = None,
) -> Union["AnyObject", Callable[["AnyObject"], "AnyObject"]]:
    """Decorator to enable code extraction from notebooks.

    Args:
        _obj: The class or function for which to enable code extraction.

    Returns:
        The decorated class or function.
    """

    def inner_decorator(obj: "AnyObject") -> "AnyObject":
        try_to_save_notebook_cell_code(obj)
        return obj

    if _obj is None:
        return inner_decorator
    else:
        return inner_decorator(_obj)


def get_active_notebook_cell_code() -> Optional[str]:
    """Get the code of the currently active notebook cell.

    Returns:
        The code of the currently active notebook cell.
    """
    cell_code = None
    try:
        ipython = get_ipython()  # type: ignore[name-defined]
        cell_code = ipython.get_parent()["content"]["code"]
    except (NameError, KeyError) as e:
        logger.warning("Unable to extract cell code: %s.", str(e))

    return cell_code


def try_to_save_notebook_cell_code(obj: Any) -> None:
    """Try to save the notebook cell code for an object.

    Args:
        obj: The object for which to save the notebook cell code.
    """
    if is_defined_in_notebook_cell(obj):
        if cell_code := get_active_notebook_cell_code():
            setattr(
                obj,
                ZENML_NOTEBOOK_CELL_CODE_ATTRIBUTE_NAME,
                cell_code,
            )


def load_notebook_cell_code(obj: Any) -> Optional[str]:
    """Load the notebook cell code for an object.

    Args:
        obj: The object for which to load the cell code.

    Returns:
        The notebook cell code if it was saved.
    """
    return getattr(obj, ZENML_NOTEBOOK_CELL_CODE_ATTRIBUTE_NAME, None)


def warn_about_notebook_cell_magic_commands(cell_code: str) -> None:
    """Warn about magic commands in the cell code.

    Args:
        cell_code: The cell code.
    """
    if any(line.startswith(("%", "!")) for line in cell_code.splitlines()):
        logger.warning(
            "Some lines in your notebook cell start with a `!` or `%` "
            "character. Running a ZenML step remotely from a notebook "
            "only works if the cell only contains python code. If any "
            "of these lines contain Jupyter notebook magic commands, "
            "remove them and try again."
        )


def compute_cell_replacement_module_name(cell_code: str) -> str:
    """Compute the replacement module name for a given cell code.

    Args:
        cell_code: The code of the notebook cell.

    Returns:
        The replacement module name.
    """
    code_hash = hashlib.sha1(cell_code.encode()).hexdigest()  # nosec
    return f"extracted_notebook_code_{code_hash}"
