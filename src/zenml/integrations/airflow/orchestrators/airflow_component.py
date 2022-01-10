# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Definition for Airflow component for TFX."""

import functools
from typing import Optional

import airflow
from airflow.operators import python
from google.protobuf import message
from tfx.orchestration import metadata
from tfx.orchestration.portable import launcher
from tfx.proto.orchestration import pipeline_pb2

from zenml.orchestrators.utils import execute_step


def _airflow_component_launcher(
    pipeline_node: pipeline_pb2.PipelineNode,
    mlmd_connection: metadata.Metadata,
    pipeline_info: pipeline_pb2.PipelineInfo,
    pipeline_runtime_spec: pipeline_pb2.PipelineRuntimeSpec,
    executor_spec: Optional[message.Message] = None,
    custom_driver_spec: Optional[message.Message] = None,
) -> None:
    """Helper function to launch TFX component execution.

    Args:
        pipeline_node: The specification of the node to launch.
        mlmd_connection: ML metadata connection info.
        pipeline_info: The information of the pipeline that this node runs in.
        pipeline_runtime_spec: The runtime information of the pipeline that this
            node runs in.
        executor_spec: Specification for the executor of the node.
        custom_driver_spec: Specification for custom driver.
    """
    component_launcher = launcher.Launcher(
        pipeline_node=pipeline_node,
        mlmd_connection=metadata.Metadata(mlmd_connection),
        pipeline_info=pipeline_info,
        pipeline_runtime_spec=pipeline_runtime_spec,
        executor_spec=executor_spec,
        custom_driver_spec=custom_driver_spec,
    )
    execute_step(component_launcher)


class AirflowComponent(python.PythonOperator):
    """Airflow-specific TFX Component.
    This class wrap a component run into its own PythonOperator in Airflow.
    """

    def __init__(
        self,
        *,
        parent_dag: airflow.DAG,
        pipeline_node: pipeline_pb2.PipelineNode,
        mlmd_connection: metadata.Metadata,
        pipeline_info: pipeline_pb2.PipelineInfo,
        pipeline_runtime_spec: pipeline_pb2.PipelineRuntimeSpec,
        executor_spec: Optional[message.Message] = None,
        custom_driver_spec: Optional[message.Message] = None
    ) -> None:
        """Constructs an Airflow implementation of TFX component.

        Args:
            parent_dag: The airflow DAG that this component is contained in.
            pipeline_node: The specification of the node to launch.
            mlmd_connection: ML metadata connection info.
            pipeline_info: The information of the pipeline that this node
                runs in.
            pipeline_runtime_spec: The runtime information of the pipeline
                that this node runs in.
            executor_spec: Specification for the executor of the node.
            custom_driver_spec: Specification for custom driver.
        """
        launcher_callable = functools.partial(
            _airflow_component_launcher,
            pipeline_node=pipeline_node,
            mlmd_connection=mlmd_connection,
            pipeline_info=pipeline_info,
            pipeline_runtime_spec=pipeline_runtime_spec,
            executor_spec=executor_spec,
            custom_driver_spec=custom_driver_spec,
        )

        super().__init__(
            task_id=pipeline_node.node_info.id,
            provide_context=True,
            python_callable=launcher_callable,
            dag=parent_dag,
        )
