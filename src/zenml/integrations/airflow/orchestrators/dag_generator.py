#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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
"""Module to generate an Airflow DAG from a config file."""

import datetime
import importlib
import os
import zipfile
from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

ENV_ZENML_AIRFLOW_RUN_ID = "ZENML_AIRFLOW_RUN_ID"
ENV_ZENML_LOCAL_STORES_PATH = "ZENML_LOCAL_STORES_PATH"
CONFIG_FILENAME = "config.json"


class TaskConfiguration(BaseModel):
    """Airflow task configuration."""

    id: str
    zenml_step_name: str
    upstream_steps: List[str]

    docker_image: str
    command: List[str]
    arguments: List[str]

    environment: Dict[str, str] = {}

    operator_source: str
    operator_args: Dict[str, Any] = {}


class DagConfiguration(BaseModel):
    """Airflow DAG configuration."""

    id: str
    tasks: List[TaskConfiguration]

    local_stores_path: Optional[str] = None

    schedule: Union[datetime.timedelta, str] = Field(
        union_mode="left_to_right"
    )
    start_date: datetime.datetime
    end_date: Optional[datetime.datetime] = None
    catchup: bool = False

    tags: List[str] = []
    dag_args: Dict[str, Any] = {}


def import_class_by_path(class_path: str) -> Type[Any]:
    """Imports a class based on a given path.

    Args:
        class_path: str, class_source e.g. this.module.Class

    Returns:
        the given class
    """
    module_name, class_name = class_path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    return getattr(module, class_name)  # type: ignore[no-any-return]


def get_operator_init_kwargs(
    operator_class: Type[Any],
    dag_config: DagConfiguration,
    task_config: TaskConfiguration,
) -> Dict[str, Any]:
    """Gets keyword arguments to pass to the operator init method.

    Args:
        operator_class: The operator class for which to get the kwargs.
        dag_config: The configuration of the DAG.
        task_config: The configuration of the task.

    Returns:
        The init keyword arguments.
    """
    init_kwargs = {"task_id": task_config.id}

    try:
        from airflow.providers.docker.operators.docker import DockerOperator

        if issubclass(operator_class, DockerOperator):
            init_kwargs.update(
                get_docker_operator_init_kwargs(
                    dag_config=dag_config, task_config=task_config
                )
            )
    except ImportError:
        pass

    try:
        from airflow.providers.cncf.kubernetes.operators.kubernetes_pod import (
            KubernetesPodOperator,
        )

        if issubclass(operator_class, KubernetesPodOperator):
            init_kwargs.update(
                get_kubernetes_pod_operator_init_kwargs(
                    dag_config=dag_config, task_config=task_config
                )
            )
    except ImportError:
        pass

    init_kwargs.update(task_config.operator_args)
    return init_kwargs


def get_docker_operator_init_kwargs(
    dag_config: DagConfiguration, task_config: TaskConfiguration
) -> Dict[str, Any]:
    """Gets keyword arguments to pass to the DockerOperator.

    Args:
        dag_config: The configuration of the DAG.
        task_config: The configuration of the task.

    Returns:
        The init keyword arguments.
    """
    mounts = []
    extra_hosts = {}
    environment = task_config.environment
    environment[ENV_ZENML_AIRFLOW_RUN_ID] = "{{run_id}}"

    if dag_config.local_stores_path:
        from docker.types import Mount

        environment[ENV_ZENML_LOCAL_STORES_PATH] = dag_config.local_stores_path
        mounts = [
            Mount(
                target=dag_config.local_stores_path,
                source=dag_config.local_stores_path,
                type="bind",
            )
        ]
        extra_hosts = {"host.docker.internal": "host-gateway"}
    return {
        "image": task_config.docker_image,
        "command": task_config.command + task_config.arguments,
        "mounts": mounts,
        "environment": environment,
        "extra_hosts": extra_hosts,
    }


def get_kubernetes_pod_operator_init_kwargs(
    dag_config: DagConfiguration, task_config: TaskConfiguration
) -> Dict[str, Any]:
    """Gets keyword arguments to pass to the KubernetesPodOperator.

    Args:
        dag_config: The configuration of the DAG.
        task_config: The configuration of the task.

    Returns:
        The init keyword arguments.
    """
    from kubernetes.client.models import V1EnvVar

    environment = task_config.environment
    environment[ENV_ZENML_AIRFLOW_RUN_ID] = "{{run_id}}"

    return {
        "name": f"{dag_config.id}_{task_config.id}",
        "namespace": "default",
        "image": task_config.docker_image,
        "cmds": task_config.command,
        "arguments": task_config.arguments,
        "env_vars": [
            V1EnvVar(name=key, value=value)
            for key, value in environment.items()
        ],
    }


try:
    archive = zipfile.ZipFile(os.path.dirname(__file__), "r")
except (IsADirectoryError, PermissionError):
    # Not inside a zip, this happens if we import this file outside of an
    # airflow dag zip
    pass
else:
    import airflow

    config_str = archive.read(CONFIG_FILENAME)
    dag_config = DagConfiguration.model_validate_json(config_str)

    step_name_to_airflow_operator = {}

    with airflow.DAG(
        dag_id=dag_config.id,
        is_paused_upon_creation=False,
        tags=dag_config.tags,
        schedule_interval=dag_config.schedule,
        start_date=dag_config.start_date,
        end_date=dag_config.end_date,
        catchup=dag_config.catchup,
        **dag_config.dag_args,
    ) as dag:
        for task in dag_config.tasks:
            operator_class = import_class_by_path(task.operator_source)
            init_kwargs = get_operator_init_kwargs(
                operator_class=operator_class,
                dag_config=dag_config,
                task_config=task,
            )
            operator = operator_class(**init_kwargs)

            step_name_to_airflow_operator[task.zenml_step_name] = operator
            for upstream_step in task.upstream_steps:
                operator.set_upstream(
                    step_name_to_airflow_operator[upstream_step]
                )
