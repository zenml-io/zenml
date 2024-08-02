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
from typing import TYPE_CHECKING, Any, Dict, Optional

from IPython import get_ipython

from zenml.config.source import NotebookSource, SourceType
from zenml.environment import Environment
from zenml.logger import get_logger
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.config.step_configurations import Step
    from zenml.models import PipelineDeploymentBase
    from zenml.stack import Stack


ZENML_NOTEBOOK_CELL_ID_ATTRIBUTE_NAME = "__zenml_notebook_cell_id__"

logger = get_logger(__name__)


def get_notebook_extra_files(
    deployment: "PipelineDeploymentBase", stack: "Stack"
) -> Dict[str, str]:
    """Get extra required files for running notebook code remotely.

    Args:
        deployment: The deployment for which to get the files.
        stack: The stack on which the deployment will run.

    Raises:
        RuntimeError: If the cell ID for a remote step of the deployment is
            not stored.

    Returns:
        A dict (file_path, file_content) of the required extra files.
    """
    if not Environment.in_notebook():
        return {}

    files = {}

    for step in deployment.step_configurations.values():
        if step.spec.source.type == SourceType.NOTEBOOK:
            assert isinstance(step.spec.source, NotebookSource)

            if not step_will_run_remotely(step=step, stack=stack):
                continue

            cell_id = step.spec.source.cell_id
            if not cell_id:
                raise RuntimeError(
                    "Failed to extract notebook cell code because no cell ID"
                    "was saved for this step."
                )

            module_name = (
                f"zenml_extracted_notebook_code_{cell_id.replace('-', '_')}"
            )
            filename = f"{module_name}.py"
            file_content = extract_notebook_cell_code(cell_id=cell_id)

            step.spec.source.replacement_module = module_name
            files[filename] = file_content

    return files


def step_will_run_remotely(step: "Step", stack: "Stack") -> bool:
    """Check whether a step will run remotely.

    Args:
        step: The step to check.
        stack: The stack on which the step will run.

    Returns:
        Whether the step will run remotely.
    """
    if step.config.step_operator:
        return True

    if stack.orchestrator.config.is_remote:
        return True

    return False


def get_active_notebook_cell_id() -> str:
    """Get the ID of the currently active notebook cell.

    Returns:
        The ID of the currently active notebook cell.
    """
    cell_id = get_ipython().get_parent()["metadata"]["cellId"]
    return cell_id


def load_active_notebook() -> Dict[str, Any]:
    """Load the active notebook.

    Raises:
        RuntimeError: If the active notebook can't be loaded.

    Returns:
        Dictionary of the notebook.
    """
    if not Environment.in_notebook():
        raise RuntimeError(
            "Can't load active notebook as you're currently not running in a "
            "notebook."
        )
    notebook_path = os.path.join(source_utils.get_source_root(), "test.ipynb")

    if not os.path.exists(notebook_path):
        raise RuntimeError(f"Notebook at path {notebook_path} does not exist.")

    with open(notebook_path) as f:
        notebook_json = json.loads(f.read())

    cell_id = get_active_notebook_cell_id()

    for cell in notebook_json["cells"]:
        if cell["id"] == cell_id:
            return notebook_json

    raise RuntimeError(
        f"Notebook at path {notebook_path} is not the active notebook."
    )


def extract_notebook_cell_code(cell_id: str) -> str:
    """Extract code from a notebook cell.

    Args:
        notebook_path: Path to the notebook file.
        cell_id: ID of the cell for which to extract the code.

    Raises:
        RuntimeError: If the notebook contains no cell with the given ID.

    Returns:
        The cell content.
    """
    notebook_json = load_active_notebook()

    for cell in notebook_json["cells"]:
        if cell["id"] == cell_id:
            if cell["cell_type"] != "code":
                logger.warning(
                    "Trying to extract code from notebook cell, but the cell "
                    "type is %s. Continuing anyway..",
                    cell["cell_type"],
                )

            return "\n".join(cell["source"])

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
