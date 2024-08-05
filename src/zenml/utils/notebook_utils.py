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

import json
import os
from typing import Any, Callable, Dict, Optional, TypeVar, Union

from IPython import get_ipython

from zenml.constants import ENV_ZENML_NOTEBOOK_PATH
from zenml.environment import Environment
from zenml.logger import get_logger

ZENML_NOTEBOOK_CELL_ID_ATTRIBUTE_NAME = "__zenml_notebook_cell_id__"

DEFAULT_NOTEBOOK_NAME = "test.ipynb"

logger = get_logger(__name__)

_UNINITIALIZED = "uninitialized"
_ACTIVE_NOTEBOOK_PATH: Optional[str] = _UNINITIALIZED

O = TypeVar("O", bound=Any)


def get_active_notebook_path() -> Optional[str]:
    """Get path of the active notebook.

    Returns:
        Path of the active notebook.
    """
    if not Environment.in_notebook():
        return None

    global _ACTIVE_NOTEBOOK_PATH

    if _ACTIVE_NOTEBOOK_PATH == _UNINITIALIZED:
        import ipynbname

        from zenml.utils import source_utils

        if path := os.environ.get(ENV_ZENML_NOTEBOOK_PATH, None):
            logger.info(
                "Using notebook path from environment variable: %s", path
            )

            _ACTIVE_NOTEBOOK_PATH = path
        else:
            from IPython import get_ipython

            ip = get_ipython()
            if "__vsc_ipynb_file__" in ip.user_ns:
                _ACTIVE_NOTEBOOK_PATH = ip.user_ns["__vsc_ipynb_file__"]
            else:
                try:
                    _ACTIVE_NOTEBOOK_PATH = str(ipynbname.path())
                except FileNotFoundError:
                    logger.warning(
                        "Unable to detect active notebook. You can use the %s "
                        "environment variable to manually specify a path to the "
                        "notebook that you're currently using.",
                        ENV_ZENML_NOTEBOOK_PATH,
                    )
                    _ACTIVE_NOTEBOOK_PATH = None

        if _ACTIVE_NOTEBOOK_PATH:
            relative_path = os.path.relpath(
                _ACTIVE_NOTEBOOK_PATH, source_utils.get_source_root()
            )
            if relative_path.startswith(os.path.pardir):
                logger.warning(
                    "Notebook path %s is not in source root %s, ignoring it..",
                    _ACTIVE_NOTEBOOK_PATH,
                    source_utils.get_source_root(),
                )
                _ACTIVE_NOTEBOOK_PATH = None

    return _ACTIVE_NOTEBOOK_PATH


def load_notebook(notebook_path: str) -> Dict[str, Any]:
    """Load a notebook.

    Args:
        notebook_path: Path to the notebook.

    Raises:
        FileNotFoundError: If no notebook exist at the path.

    Returns:
        Dictionary of the notebook.
    """
    if not os.path.exists(notebook_path):
        raise FileNotFoundError(
            f"Notebook at path {notebook_path} does not exist."
        )

    with open(notebook_path) as f:
        notebook_json = json.loads(f.read())

    return notebook_json


def is_running_in_notebook(notebook_path: str) -> None:
    """Check if the current code is running in the given notebook.

    Args:
        notebook_path: Path of the notebook.

    Returns:
        If the current code is running in the given notebook.
    """
    if not Environment.in_notebook():
        return False

    try:
        notebook_json = load_notebook(notebook_path)
    except FileNotFoundError:
        return False

    active_cell_id = get_active_notebook_cell_id()

    for cell in notebook_json["cells"]:
        if cell["id"] == active_cell_id:
            # This isn't a 100% guarantee if the notebook was copied but a good
            # quick check
            return True

    return False


def extract_notebook_cell_code(notebook_path: str, cell_id: str) -> str:
    """Extract code from a notebook cell.

    Args:
        notebook_path: Path to the notebook file.
        cell_id: ID of the cell for which to extract the code.

    Raises:
        RuntimeError: If the notebook contains no cell with the given ID.

    Returns:
        The cell content.
    """
    notebook_json = load_notebook(notebook_path)

    for cell in notebook_json["cells"]:
        if cell["id"] == cell_id:
            if cell["cell_type"] != "code":
                logger.warning(
                    "Trying to extract code from notebook cell, but the cell "
                    "type is %s. Continuing anyway..",
                    cell["cell_type"],
                )

            # TODO: Should we exclude lines starting with special symbols here?
            # Or whould that mess with some code?

            return "".join(cell["source"])

    raise RuntimeError(f"Cell with ID {cell_id} not found in active notebook.")


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


def get_active_notebook_cell_id() -> str:
    """Get the ID of the currently active notebook cell.

    Returns:
        The ID of the currently active notebook cell.
    """
    cell_id = get_ipython().get_parent()["metadata"]["cellId"]
    return cell_id


def save_notebook_cell_id(obj: Any) -> None:
    """Save the notebook cell ID for an object.

    Args:
        obj: The object for which to save the notebook cell ID.
    """
    if is_defined_in_notebook_cell(obj):
        cell_id = get_active_notebook_cell_id()

        setattr(
            obj,
            ZENML_NOTEBOOK_CELL_ID_ATTRIBUTE_NAME,
            cell_id,
        )


def load_notebook_cell_id(obj: Any) -> Optional[str]:
    """Load the notebook cell ID for an object.

    Args:
        obj: The object for which to load the cell ID.

    Returns:
        The notebook cell ID if it was saved.
    """
    return getattr(obj, ZENML_NOTEBOOK_CELL_ID_ATTRIBUTE_NAME, None)


def enable_notebook_code_extraction(
    _obj: Optional["O"] = None,
) -> Union["O", Callable[["O"], "O"]]:
    """Decorator to enable code extraction from notebooks.

    Args:
        _obj: The class or function for which to enable code extraction.

    Returns:
        The decorated class or function.
    """

    def inner_decorator(obj: "O") -> "O":
        save_notebook_cell_id(obj)
        return obj

    if _obj is None:
        return inner_decorator
    else:
        return inner_decorator(_obj)
