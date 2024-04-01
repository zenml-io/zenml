
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
from typing import List, Optional
from pydantic import BaseModel, Field

class PythonWheelTask(BaseModel):
    entry_point: str
    package_name: str
    parameters: List[str] = []

class Library(BaseModel):
    whl: Optional[str] = None
    pypi: Optional[dict] = None

    @root_validator(pre=True)
    def check_one_library_source(cls, values):
        whl = values.get('whl')
        pypi = values.get('pypi')
        if whl and pypi:
            raise ValueError("Only one of 'whl' or 'pypi' should be provided")
        return values

class PyPIPackage(BaseModel):
    package: str
    repo: Optional[str] = None

class DatabricksTask(BaseModel):
    task_key: str
    python_wheel_task: PythonWheelTask
    libraries: List[Library] = Field(default_factory=list)
    upstream_tasks: List[str] = Field(default_factory=list)

def generate_databricks_yaml(pipeline_name, tasks):
    yaml_data = {
        "resources": {
            "jobs": {
                pipeline_name: {
                    "job_clusters": [
                        {
                            "job_cluster_key": "Default",
                            "new_cluster": {
                                "autoscale": {"max_workers": 4, "min_workers": 1},
                                "node_type_id": "${var.default_node_type_id}",
                                "spark_version": "${var.default_spark_version}"
                            }
                        }
                    ],
                    "name": pipeline_name,
                    "tasks": []
                }
            }
        }
    }

    for task in tasks:
        task_data = {
            "job_cluster_key": "Default",
            "libraries": task.libraries,
            "python_wheel_task": task.python_wheel_task,
            "task_key": task.task_key
        }

        if task.upstream_tasks:
            task_data["depends_on"] = [{"task_key": upstream_task} for upstream_task in task.upstream_tasks]

        yaml_data["resources"]["jobs"][pipeline_name]["tasks"].append(task_data)

    return yaml_data