#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
"""Databricks utilities."""

from typing import List, Optional

from databricks.sdk.service.compute import Library, PythonPyPiLibrary
from databricks.sdk.service.jobs import PythonWheelTask, TaskDependency
from databricks.sdk.service.jobs import Task as DatabricksTask


def convert_step_to_task(
    task_name: str,
    command: str,
    arguments: List[str],
    libraries: Optional[List[str]] = None,
    depends_on: Optional[List[str]] = None,
    zenml_project_wheel: Optional[str] = None,
    cluster_id: Optional[str] = None,
) -> DatabricksTask:
    """Convert a ZenML step to a Databricks task.

    Args:
        task_name: Name of the task.
        command: Command to run.
        arguments: Arguments to pass to the command.
        libraries: List of libraries to install.
        depends_on: List of tasks to depend on.
        zenml_project_wheel: Path to the ZenML project wheel.
        cluster_id: ID of the Databricks cluster.

    Returns:
        Databricks task.
    """
    db_libraries = []
    if libraries:
        for library in libraries:
            db_libraries.append(Library(pypi=PythonPyPiLibrary(library)))
    db_libraries.append(Library(whl=zenml_project_wheel))
    return DatabricksTask(
        task_key=task_name,
        existing_cluster_id=cluster_id,
        libraries=db_libraries,
        python_wheel_task=PythonWheelTask(
            package_name="zenml",
            entry_point=command,
            parameters=arguments,
        ),
        depends_on=[TaskDependency(task) for task in depends_on]
        if depends_on
        else None,
    )
