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
"""Definition of Airflow TFX runner. This is an unmodified  copy from the TFX
source code (outside of superficial, stylistic changes)"""

import os
import typing
import warnings
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

import tfx.orchestration.pipeline as tfx_pipeline
from tfx.dsl.compiler import compiler
from tfx.dsl.components.base import base_component, base_node
from tfx.orchestration import tfx_runner
from tfx.orchestration.config import pipeline_config
from tfx.orchestration.data_types import RuntimeParameter
from tfx.orchestration.local import runner_utils
from tfx.orchestration.portable import runtime_parameter_utils
from tfx.utils.json_utils import json  # type: ignore[attr-defined]

if TYPE_CHECKING:
    import airflow


class AirflowPipelineConfig(pipeline_config.PipelineConfig):
    """Pipeline config for AirflowDagRunner."""

    def __init__(
        self, airflow_dag_config: Optional[Dict[str, Any]] = None, **kwargs: Any
    ):
        """Creates an instance of AirflowPipelineConfig.

        Args:
          airflow_dag_config: Configs of Airflow DAG model. See
            https://airflow.apache.org/_api/airflow/models/dag/index.html#airflow.models.dag.DAG
            for the full spec.
          **kwargs: keyword args for PipelineConfig.
        """

        super().__init__(**kwargs)
        self.airflow_dag_config = airflow_dag_config or {}


class AirflowDagRunner(tfx_runner.TfxRunner):
    """Tfx runner on Airflow."""

    def __init__(
        self,
        config: Optional[Union[Dict[str, Any], AirflowPipelineConfig]] = None,
    ):
        """Creates an instance of AirflowDagRunner.

        Args:
          config: Optional Airflow pipeline config for customizing the
          launching of each component.
        """
        if isinstance(config, dict):
            warnings.warn(
                "Pass config as a dict type is going to deprecated in 0.1.16. "
                "Use AirflowPipelineConfig type instead.",
                PendingDeprecationWarning,
            )
            config = AirflowPipelineConfig(airflow_dag_config=config)
        super().__init__(config)

    def run(
        self, pipeline: tfx_pipeline.Pipeline, run_name: str = ""
    ) -> "airflow.DAG":
        """Deploys given logical pipeline on Airflow.

        Args:
          pipeline: Logical pipeline containing pipeline args and comps.
          run_name: Optional name for the run.

        Returns:
          An Airflow DAG.
        """
        # Only import these when needed.
        import airflow  # noqa

        from zenml.integrations.airflow.orchestrators import airflow_component

        # Merge airflow-specific configs with pipeline args

        airflow_dag = airflow.DAG(
            dag_id=pipeline.pipeline_info.pipeline_name,
            **(
                typing.cast(
                    AirflowPipelineConfig, self._config
                ).airflow_dag_config
            ),
            is_paused_upon_creation=False,
            catchup=False,  # no backfill
        )
        if "tmp_dir" not in pipeline.additional_pipeline_args:
            tmp_dir = os.path.join(
                pipeline.pipeline_info.pipeline_root, ".temp", ""
            )
            pipeline.additional_pipeline_args["tmp_dir"] = tmp_dir

        for component in pipeline.components:
            if isinstance(component, base_component.BaseComponent):
                component._resolve_pip_dependencies(
                    pipeline.pipeline_info.pipeline_root
                )
            self._replace_runtime_params(component)

        c = compiler.Compiler()
        pipeline = c.compile(pipeline)

        # Substitute the runtime parameter to be a concrete run_id
        runtime_parameter_utils.substitute_runtime_parameter(
            pipeline,
            {
                "pipeline-run-id": run_name,
            },
        )
        deployment_config = runner_utils.extract_local_deployment_config(
            pipeline
        )
        connection_config = deployment_config.metadata_connection_config  # type: ignore[attr-defined] # noqa

        component_impl_map = {}

        for node in pipeline.nodes:
            pipeline_node = node.pipeline_node
            node_id = pipeline_node.node_info.id
            executor_spec = runner_utils.extract_executor_spec(
                deployment_config, node_id
            )
            custom_driver_spec = runner_utils.extract_custom_driver_spec(
                deployment_config, node_id
            )

            current_airflow_component = airflow_component.AirflowComponent(
                parent_dag=airflow_dag,
                pipeline_node=pipeline_node,
                mlmd_connection=connection_config,
                pipeline_info=pipeline.pipeline_info,
                pipeline_runtime_spec=pipeline.runtime_spec,
                executor_spec=executor_spec,
                custom_driver_spec=custom_driver_spec,
            )
            component_impl_map[node_id] = current_airflow_component
            for upstream_node in node.pipeline_node.upstream_nodes:
                assert (
                    upstream_node in component_impl_map
                ), "Components is not in topological order"
                current_airflow_component.set_upstream(
                    component_impl_map[upstream_node]
                )

        return airflow_dag

    def _replace_runtime_params(
        self, comp: base_node.BaseNode
    ) -> base_node.BaseNode:
        """Replaces runtime params for dynamic Airflow parameter execution.

        Args:
            comp: TFX component to be parsed.

        Returns:
            Returns edited component.
        """
        for k, prop in comp.exec_properties.copy().items():
            if isinstance(prop, RuntimeParameter):
                # Airflow only supports string parameters.
                if prop.ptype != str:
                    raise RuntimeError(
                        f"RuntimeParameter in Airflow does not support "
                        f"{prop.ptype}. The only ptype supported is string."
                    )

                # If the default is a template, drop the template markers
                # when inserting it into the .get() default argument below.
                # Otherwise, provide the default as a quoted string.
                default = cast(str, prop.default)
                if default.startswith("{{") and default.endswith("}}"):
                    default = default[2:-2]
                else:
                    default = json.dumps(default)

                template_field = '{{ dag_run.conf.get("%s", %s) }}' % (
                    prop.name,
                    default,
                )
                comp.exec_properties[k] = template_field
        return comp
