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
from typing import Any, Dict, Optional, Type

import airflow
from airflow.operators import python
from google.protobuf import message
from tfx.orchestration import metadata
from tfx.orchestration.portable import launcher, runtime_parameter_utils
from tfx.proto.orchestration import pipeline_pb2

from zenml.orchestrators.utils import execute_step
from zenml.repository import Repository


def _airflow_component_launcher(
    pb2_pipeline: pipeline_pb2.Pipeline,
    pipeline_node: pipeline_pb2.PipelineNode,
    mlmd_connection: metadata.Metadata,
    executor_spec: Optional[message.Message] = None,
    custom_driver_spec: Optional[message.Message] = None,
    custom_executor_operators: Optional[
        Dict[Any, Type[launcher.ExecutorOperator]]
    ] = None,
    **kwargs: Any,
) -> None:
    """Helper function to launch TFX component execution.

    Args:
        pb2_pipeline: Protobuf pipeline definition.
        pipeline_node: The specification of the node to launch.
        mlmd_connection: ML metadata connection info.
        executor_spec: Specification for the executor of the node.
        custom_driver_spec: Specification for custom driver.
        custom_executor_operators: Map of executable specs to executor
            operators.
    """
    # get the run name from the airflow task instance
    run_name = kwargs["ti"].get_dagrun().run_id

    # Replace pipeline run id in both the pipeline and node proto files
    for proto in [pb2_pipeline, pipeline_node]:
        runtime_parameter_utils.substitute_runtime_parameter(
            proto,
            {
                "pipeline-run-id": run_name,
            },
        )

    component_launcher = launcher.Launcher(
        pipeline_node=pipeline_node,
        mlmd_connection=metadata.Metadata(mlmd_connection),
        pipeline_info=pb2_pipeline.pipeline_info,
        pipeline_runtime_spec=pb2_pipeline.runtime_spec,
        executor_spec=executor_spec,
        custom_driver_spec=custom_driver_spec,
        custom_executor_operators=custom_executor_operators,
    )
    stack = Repository().active_stack
    stack.prepare_step_run()
    execute_step(component_launcher)
    stack.cleanup_step_run()


class AirflowComponent(python.PythonOperator):
    """Airflow-specific TFX Component.
    This class wrap a component run into its own PythonOperator in Airflow.
    """

    def __init__(
        self,
        *,
        parent_dag: airflow.DAG,
        pb2_pipeline: pipeline_pb2.Pipeline,
        pipeline_node: pipeline_pb2.PipelineNode,
        mlmd_connection: metadata.Metadata,
        executor_spec: Optional[message.Message] = None,
        custom_driver_spec: Optional[message.Message] = None,
        custom_executor_operators: Optional[
            Dict[Any, Type[launcher.ExecutorOperator]]
        ] = None,
    ) -> None:
        """Constructs an Airflow implementation of TFX component.

        Args:
            parent_dag: The airflow DAG that this component is contained in.
            pb2_pipeline: Protobuf pipeline definition.
            pipeline_node: The specification of the node to launch.
            mlmd_connection: ML metadata connection info.
            executor_spec: Specification for the executor of the node.
            custom_driver_spec: Specification for custom driver.
            custom_executor_operators: Map of executable specs to executor
                operators.
        """
        launcher_callable = functools.partial(
            _airflow_component_launcher,
            pb2_pipeline=pb2_pipeline,
            pipeline_node=pipeline_node,
            mlmd_connection=mlmd_connection,
            executor_spec=executor_spec,
            custom_driver_spec=custom_driver_spec,
            custom_executor_operators=custom_executor_operators,
        )

        super().__init__(
            task_id=pipeline_node.node_info.id,
            provide_context=True,
            python_callable=launcher_callable,
            dag=parent_dag,
        )
