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
"""Definition of Airflow TFX runner. This is an unmodified  copy from the TFX
source code (outside of superficial, stylistic changes)"""

import os
import typing
import warnings
from typing import TYPE_CHECKING, Any, Dict, Optional, Union, cast

import tfx.orchestration.pipeline as tfx_pipeline
from tfx.dsl.components.base import base_component, base_node
from tfx.orchestration import tfx_runner
from tfx.orchestration.config import config_utils, pipeline_config
from tfx.orchestration.data_types import RuntimeParameter
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

    def run(self, pipeline: tfx_pipeline.Pipeline) -> "airflow.DAG":
        """Deploys given logical pipeline on Airflow.

        Args:
          pipeline: Logical pipeline containing pipeline args and comps.

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

        component_impl_map = {}
        for tfx_component in pipeline.components:
            if isinstance(tfx_component, base_component.BaseComponent):
                tfx_component._resolve_pip_dependencies(  # noqa
                    pipeline.pipeline_info.pipeline_root
                )

            tfx_component = self._replace_runtime_params(tfx_component)

            (
                component_launcher_class,
                component_config,
            ) = config_utils.find_component_launch_info(
                self._config, tfx_component
            )
            current_airflow_component = airflow_component.AirflowComponent(
                parent_dag=airflow_dag,
                component=tfx_component,
                component_launcher_class=component_launcher_class,
                pipeline_info=pipeline.pipeline_info,
                enable_cache=pipeline.enable_cache,  # type: ignore[arg-type]
                metadata_connection_config=pipeline.metadata_connection_config,
                beam_pipeline_args=pipeline.beam_pipeline_args,
                additional_pipeline_args=pipeline.additional_pipeline_args,
                component_config=component_config,  # type: ignore[arg-type]
            )
            component_impl_map[tfx_component] = current_airflow_component
            for upstream_node in tfx_component.upstream_nodes:
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
