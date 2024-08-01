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
from typing import TYPE_CHECKING, Any, Dict

from IPython import get_ipython

from zenml.config.source import NotebookSource, SourceType
from zenml.environment import Environment
from zenml.utils import source_utils

if TYPE_CHECKING:
    from zenml.models import PipelineDeploymentBase


def get_notebook_extra_files(
    deployment: "PipelineDeploymentBase",
) -> Dict[str, str]:
    files = {}
    notebook_path = get_notebook_path()

    for step in deployment.pipeline_spec.steps:
        if step.source.type == SourceType.NOTEBOOK:
            assert isinstance(step.source, NotebookSource)

            cell_id = step.source.cell_id
            if not cell_id:
                raise RuntimeError(
                    "Can't extract notebook code, missing cell ID."
                )

            module_name = (
                f"zenml_extracted_notebook_code_{cell_id.replace('-', '_')}"
            )
            filename = f"{module_name}.py"
            file_content = extract_cell_code(
                notebook_path=notebook_path, cell_id=cell_id
            )

            step.source.replacement_module = module_name
            files[filename] = file_content

    return files


def get_current_notebook_cell_id() -> str:
    cell_id = get_ipython().get_parent()["metadata"]["cellId"]
    return cell_id


def get_notebook_path() -> str:
    return os.path.join(source_utils.get_source_root(), "test.ipynb")


def extract_cell_code(notebook_path: str, cell_id: str) -> str:
    # import ipynbname

    # notebook_path = ipynbname.path()

    with open(notebook_path) as f:
        notebook_json = json.loads(f.read())

    for cell in notebook_json["cells"]:
        if cell["id"] == cell_id:
            return "\n".join(cell["source"])

    raise RuntimeError(
        f"Cell with ID {cell_id} not found in notebook {notebook_path}."
    )


def store_cell_id(obj: Any) -> None:
    if Environment.in_notebook():
        cell_id = get_current_notebook_cell_id()

        # TODO: check if object defined in cell
        setattr(
            obj,
            source_utils.ZENML_NOTEBOOK_CELL_ID_ATTRIBUTE_NAME,
            cell_id,
        )
