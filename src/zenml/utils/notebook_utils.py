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

_UNINITIALIZED = "uninitialized"
_ACTIVE_NOTEBOOK_PATH: Optional[str] = _UNINITIALIZED

O = TypeVar("O", bound=Any)

logger = get_logger(__name__)


def get_active_notebook_path() -> Optional[str]:
    """Get path of the active notebook.

    Returns:
        Path of the active notebook.
    """
    if not Environment.in_notebook():
        return None

    global _ACTIVE_NOTEBOOK_PATH

    if _ACTIVE_NOTEBOOK_PATH == _UNINITIALIZED:
        if path := os.environ.get(ENV_ZENML_NOTEBOOK_PATH, None):
            logger.info(
                "Using notebook path from environment variable: %s", path
            )
            if not is_running_in_notebook(path):
                logger.warning(
                    "You've used the `%s` environment variable to set a "
                    "notebook path, but it does not seem to point to the "
                    "currently running notebook. This might lead to issues "
                    "when trying to run a remote pipeline from this notebook."
                )

            _ACTIVE_NOTEBOOK_PATH = path
        else:
            if path := get_ipython().user_ns.get("__vsc_ipynb_file__", None):
                _ACTIVE_NOTEBOOK_PATH = path
            elif Environment.in_google_colab():
                logger.warning(
                    "Unable to detect active notebook in Google Colab. You can "
                    "use the %s environment variable to manually specify a "
                    "path to the notebook that you're currently using.",
                    ENV_ZENML_NOTEBOOK_PATH,
                )
                _ACTIVE_NOTEBOOK_PATH = None
            else:
                try:
                    import ipynbname

                    _ACTIVE_NOTEBOOK_PATH = str(ipynbname.path())
                except ImportError:
                    logger.warning(
                        "Unable to detect active notebook. You can install "
                        "ZenML with the `notebook` extra (e.g. `pip install "
                        "'zenml[notebook]'`) or use the %s "
                        "environment variable to manually specify a path to the "
                        "notebook that you're currently using.",
                        ENV_ZENML_NOTEBOOK_PATH,
                    )
                    _ACTIVE_NOTEBOOK_PATH = None
                except FileNotFoundError:
                    logger.warning(
                        "Unable to detect active notebook. You can use the %s "
                        "environment variable to manually specify a path to the "
                        "notebook that you're currently using.",
                        ENV_ZENML_NOTEBOOK_PATH,
                    )
                    _ACTIVE_NOTEBOOK_PATH = None

        if _ACTIVE_NOTEBOOK_PATH:
            from zenml.utils import source_utils

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

            if any(line.startswith(("%", "!")) for line in cell["source"]):
                logger.warning(
                    "Some lines in your notebook cell start with a `!` or `%` "
                    "character. Running a ZenML step remotely from a notebook "
                    "only works if the cell only contains python code. If any "
                    "of these lines contain Jupyter notebook magic commands, "
                    "remove them and try again."
                )

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
    try:
        if Environment.in_google_colab():
            cell_id = get_ipython().get_parent()["metadata"]["colab"]["cell_id"]
        else:
            cell_id = get_ipython().get_parent()["metadata"]["cellId"]
    except KeyError as e:
        logger.warning("Unable to extract cell ID: %s.", str(e))

    return cell_id


def try_to_save_notebook_cell_id(obj: Any) -> None:
    """Try to save the notebook cell ID for an object.

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
        try_to_save_notebook_cell_id(obj)
        return obj

    if _obj is None:
        return inner_decorator
    else:
        return inner_decorator(_obj)
