# Copyright 2019 Google LLC. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Definition for Airflow component for TFX."""

import functools
from typing import Any, Dict, List, Type

from airflow import models
from airflow.operators import python_operator
from ml_metadata.proto import metadata_store_pb2
from tfx.dsl.components.base import base_node
from tfx.orchestration import data_types, metadata
from tfx.orchestration.config import base_component_config
from tfx.orchestration.launcher import base_component_launcher
from tfx.utils import telemetry_utils


def _airflow_component_launcher(
    component: base_node.BaseNode,
    component_launcher_class: Type[
        base_component_launcher.BaseComponentLauncher
    ],
    pipeline_info: data_types.PipelineInfo,
    driver_args: data_types.DriverArgs,
    metadata_connection_config: metadata_store_pb2.ConnectionConfig,
    beam_pipeline_args: List[str],
    additional_pipeline_args: Dict[str, Any],
    component_config: base_component_config.BaseComponentConfig,
    exec_properties: Dict[str, Any],
    **kwargs
) -> None:
    """Helper function to launch TFX component execution.
    This helper function will be called with Airflow env objects which contains
    run_id that we need to pass into TFX ComponentLauncher.
    Args:
      component: TFX BaseComponent instance. This instance holds all inputs and
        outputs placeholders as well as component properties.
      component_launcher_class: The class of the launcher to launch the component.
      pipeline_info: A data_types.PipelineInfo instance that holds pipeline
        properties
      driver_args: Component specific args for driver.
      metadata_connection_config: Configuration for how to connect to metadata.
      beam_pipeline_args: Pipeline arguments for Beam powered Components.
      additional_pipeline_args: A dict of additional pipeline args.
      component_config: Component config to launch the component.
      exec_properties: Execution properties from the ComponentSpec.
      **kwargs: Context arguments that will be passed in by Airflow, including:
        - ti: TaskInstance object from which we can get run_id of the running
          pipeline.
        For more details, please refer to the code:
        https://github.com/apache/airflow/blob/master/airflow/operators/python_operator.py
    """
    component.exec_properties.update(exec_properties)

    # Populate run id from Airflow task instance.
    pipeline_info.run_id = kwargs["ti"].get_dagrun().run_id
    launcher = component_launcher_class.create(
        component=component,
        pipeline_info=pipeline_info,
        driver_args=driver_args,
        metadata_connection=metadata.Metadata(metadata_connection_config),
        beam_pipeline_args=beam_pipeline_args,
        additional_pipeline_args=additional_pipeline_args,
        component_config=component_config,
    )
    with telemetry_utils.scoped_labels(
        {telemetry_utils.LABEL_TFX_RUNNER: "airflow"}
    ):
        launcher.launch()


class AirflowComponent(python_operator.PythonOperator):
    """Airflow-specific TFX Component.
    This class wrap a component run into its own PythonOperator in Airflow.
    """

    def __init__(
        self,
        *,
        parent_dag: models.DAG,
        component: base_node.BaseNode,
        component_launcher_class: Type[
            base_component_launcher.BaseComponentLauncher
        ],
        pipeline_info: data_types.PipelineInfo,
        enable_cache: bool,
        metadata_connection_config: metadata_store_pb2.ConnectionConfig,
        beam_pipeline_args: List[str],
        additional_pipeline_args: Dict[str, Any],
        component_config: base_component_config.BaseComponentConfig
    ):
        """Constructs an Airflow implementation of TFX component.
        Args:
          parent_dag: An AirflowPipeline instance as the pipeline DAG.
          component: An instance of base_node.BaseNode that holds all
            properties of a logical component.
          component_launcher_class: The class of the launcher to launch the
            component.
          pipeline_info: An instance of data_types.PipelineInfo that holds pipeline
            properties.
          enable_cache: Whether or not cache is enabled for this component run.
          metadata_connection_config: A config proto for metadata connection.
          beam_pipeline_args: Pipeline arguments for Beam powered Components.
          additional_pipeline_args: Additional pipeline args.
          component_config: Component config to launch the component.
        """
        # Prepare parameters to create TFX worker.
        driver_args = data_types.DriverArgs(enable_cache=enable_cache)

        exec_properties = component.exec_properties

        super().__init__(
            task_id=component.id,
            # TODO(b/183172663): Delete `provide_context` when we drop support of
            # airflow 1.x.
            provide_context=True,
            python_callable=functools.partial(
                _airflow_component_launcher,
                component=component,
                component_launcher_class=component_launcher_class,
                pipeline_info=pipeline_info,
                driver_args=driver_args,
                metadata_connection_config=metadata_connection_config,
                beam_pipeline_args=beam_pipeline_args,
                additional_pipeline_args=additional_pipeline_args,
                component_config=component_config,
            ),
            # op_kwargs is a templated field for PythonOperator, which means Airflow
            # will inspect the dictionary and resolve any templated fields.
            op_kwargs={"exec_properties": exec_properties},
            dag=parent_dag,
        )
