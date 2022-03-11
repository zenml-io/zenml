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

from tfx.dsl.compiler import compiler
from tfx.dsl.components.base import base_component, base_node
from tfx.orchestration.config import pipeline_config
from tfx.orchestration.data_types import RuntimeParameter
from tfx.orchestration.local import runner_utils
from tfx.orchestration.portable import runtime_parameter_utils
from tfx.proto.orchestration import executable_spec_pb2
from tfx.proto.orchestration.pipeline_pb2 import Pipeline as Pb2Pipeline
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode
from tfx.utils.json_utils import json  # type: ignore[attr-defined]

from zenml.enums import MetadataContextTypes
from zenml.logger import get_logger
from zenml.orchestrators import context_utils
from zenml.orchestrators.utils import create_tfx_pipeline, get_step_for_node
from zenml.repository import Repository

if TYPE_CHECKING:
    import airflow

    from zenml.pipelines.base_pipeline import BasePipeline
    from zenml.runtime_configuration import RuntimeConfiguration
    from zenml.stack import Stack

logger = get_logger(__name__)


class AirflowPipelineConfig(pipeline_config.PipelineConfig):
    """Pipeline config for AirflowDagRunner."""

    def __init__(
        self,
        airflow_dag_config: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
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


class AirflowDagRunner:
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
        self._config = config or pipeline_config.PipelineConfig()

        if isinstance(config, dict):
            warnings.warn(
                "Pass config as a dict type is going to deprecated in 0.1.16. "
                "Use AirflowPipelineConfig type instead.",
                PendingDeprecationWarning,
            )
            self._config = AirflowPipelineConfig(airflow_dag_config=config)

    @property
    def config(self) -> pipeline_config.PipelineConfig:
        return self._config

    def run(
        self,
        pipeline: "BasePipeline",
        stack: "Stack",
        runtime_configuration: "RuntimeConfiguration",
    ) -> "airflow.DAG":
        """Deploys given logical pipeline on Airflow.

        Args:
          pipeline: Logical pipeline containing pipeline args and comps.
          stack: The current stack that ZenML is running on
          runtime_configuration: The configuration of the run

        Returns:
          An Airflow DAG.
        """
        # Only import these when needed.
        import airflow  # noqa

        from zenml.integrations.airflow.orchestrators import airflow_component

        # Merge airflow-specific configs with pipeline args
        tfx_pipeline = create_tfx_pipeline(pipeline, stack=stack)

        if runtime_configuration.schedule:
            catchup = runtime_configuration.schedule.catchup
        else:
            catchup = False

        airflow_dag = airflow.DAG(
            dag_id=tfx_pipeline.pipeline_info.pipeline_name,
            **(
                typing.cast(
                    AirflowPipelineConfig, self._config
                ).airflow_dag_config
            ),
            is_paused_upon_creation=False,
            catchup=catchup,
        )

        pipeline_root = tfx_pipeline.pipeline_info.pipeline_root

        if "tmp_dir" not in tfx_pipeline.additional_pipeline_args:
            tmp_dir = os.path.join(pipeline_root, ".temp", "")
            tfx_pipeline.additional_pipeline_args["tmp_dir"] = tmp_dir

        for component in tfx_pipeline.components:
            if isinstance(component, base_component.BaseComponent):
                component._resolve_pip_dependencies(pipeline_root)
            self._replace_runtime_params(component)

        pb2_pipeline: Pb2Pipeline = compiler.Compiler().compile(tfx_pipeline)

        # Substitute the runtime parameter to be a concrete run_id
        runtime_parameter_utils.substitute_runtime_parameter(
            pb2_pipeline,
            {
                "pipeline-run-id": runtime_configuration.run_name,
            },
        )
        deployment_config = runner_utils.extract_local_deployment_config(
            pb2_pipeline
        )
        connection_config = (
            Repository().active_stack.metadata_store.get_tfx_metadata_config()
        )

        component_impl_map = {}

        for node in pb2_pipeline.nodes:
            pipeline_node: PipelineNode = node.pipeline_node  # type: ignore[valid-type]

            # Add the stack as context to each pipeline node:
            context_utils.add_context_to_node(
                pipeline_node,
                type_=MetadataContextTypes.STACK.value,
                name=str(hash(json.dumps(stack.dict(), sort_keys=True))),
                properties=stack.dict(),
            )

            # Add all pydantic objects from runtime_configuration to the context
            context_utils.add_runtime_configuration_to_node(
                pipeline_node, runtime_configuration
            )

            # Add pipeline requirements as a context
            requirements = " ".join(sorted(pipeline.requirements))
            context_utils.add_context_to_node(
                pipeline_node,
                type_=MetadataContextTypes.PIPELINE_REQUIREMENTS.value,
                name=str(hash(requirements)),
                properties={"pipeline_requirements": requirements},
            )

            node_id = pipeline_node.node_info.id
            executor_spec = runner_utils.extract_executor_spec(
                deployment_config, node_id
            )
            custom_driver_spec = runner_utils.extract_custom_driver_spec(
                deployment_config, node_id
            )
            step = get_step_for_node(
                pipeline_node, steps=list(pipeline.steps.values())
            )
            custom_executor_operators = {
                executable_spec_pb2.PythonClassExecutableSpec: step.executor_operator
            }

            current_airflow_component = airflow_component.AirflowComponent(
                parent_dag=airflow_dag,
                pipeline_node=pipeline_node,
                mlmd_connection=connection_config,
                pipeline_info=pb2_pipeline.pipeline_info,
                pipeline_runtime_spec=pb2_pipeline.runtime_spec,
                executor_spec=executor_spec,
                custom_driver_spec=custom_driver_spec,
                custom_executor_operators=custom_executor_operators,
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
