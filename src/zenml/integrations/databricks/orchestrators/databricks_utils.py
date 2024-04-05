
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
from typing import Dict, List, Optional
from pydantic import BaseModel, Field, root_validator

class PythonWheelTask(BaseModel):
    entry_point: str
    package_name: str
    parameters: List[str] = []

class DatabricksTask(BaseModel):
    task_key: str
    python_wheel_task: PythonWheelTask
    libraries: List[Dict] = Field(default_factory=list)
    depends_on: Optional[List[Dict[str, str]]] = None

def generate_databricks_yaml(pipeline_name, tasks):
    return {
        "resources": {
            "jobs": {
                pipeline_name: {
                    "job_clusters": [
                        {
                            "job_cluster_key": "Default",
                            "new_cluster": {
                                "autoscale": {
                                    "max_workers": 4,
                                    "min_workers": 1,
                                },
                                "node_type_id": "${var.default_node_type_id}",
                                "spark_version": "${var.default_spark_version}",
                            },
                        }
                    ],
                    "name": pipeline_name,
                    "tasks": [
                        task.dict(exclude_none=True) for task in tasks
                    ],  # Convert tasks to dictionaries
                }
            }
        }
    }

def convert_step_to_task(task_name: str, command: str, arguments: List[str], libraries: Optional[List[str]] = None, depends_on: Optional[List[str]] = None):
    dependencies = [
            {
                "whl": "../../dist/*.whl",
            },
            {
                "pypi": {
                    "package": "zenml",
                }
            },

        ]
    if libraries:
        dependencies.extend([{"pypi": {"package": lib}} for lib in libraries])
    return DatabricksTask(
        task_key=task_name,
        job_cluster_key="Default",
        python_wheel_task=PythonWheelTask(
            entry_point=command,
            package_name="zenml",
            parameters=arguments,
        ),
        libraries=dependencies,
        depends_on=[
            {"task_key": task} for task in depends_on
        ] if depends_on else None,
    )
