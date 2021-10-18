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
from typing import Any, Dict, Optional, Union

from tfx.dsl.components.base import base_component
from tfx.orchestration import pipeline, tfx_runner
from tfx.orchestration.config import config_utils, pipeline_config
from tfx.orchestration.data_types import RuntimeParameter
from tfx.utils.json_utils import json


class AirflowPipelineConfig(pipeline_config.PipelineConfig):
    """Pipeline config for AirflowDagRunner."""

    def __init__(
        self, airflow_dag_config: Optional[Dict[str, Any]] = None, **kwargs
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
        if config and not isinstance(config, AirflowPipelineConfig):
            warnings.warn(
                "Pass config as a dict type is going to deprecated in 0.1.16. "
                "Use AirflowPipelineConfig type instead.",
                PendingDeprecationWarning,
            )
            config = AirflowPipelineConfig(airflow_dag_config=config)
        super().__init__(config)

    def run(self, tfx_pipeline: pipeline.Pipeline):
        """Deploys given logical pipeline on Airflow.

        Args:
          tfx_pipeline: Logical pipeline containing pipeline args and comps.

        Returns:
          An Airflow DAG.
        """
        # Only import these when needed.
        from airflow import models  # noqa

        from zenml.orchestrators.airflow import airflow_component  # noqa

        # Merge airflow-specific configs with pipeline args

        airflow_dag = models.DAG(
            dag_id=tfx_pipeline.pipeline_info.pipeline_name,
            **(
                typing.cast(
                    AirflowPipelineConfig, self._config
                ).airflow_dag_config
            ),
        )
        if "tmp_dir" not in tfx_pipeline.additional_pipeline_args:
            tmp_dir = os.path.join(
                tfx_pipeline.pipeline_info.pipeline_root, ".temp", ""
            )
            tfx_pipeline.additional_pipeline_args["tmp_dir"] = tmp_dir

        component_impl_map = {}
        for tfx_component in tfx_pipeline.components:
            if isinstance(tfx_component, base_component.BaseComponent):
                tfx_component._resolve_pip_dependencies(  # pylint: disable=protected-access
                    tfx_pipeline.pipeline_info.pipeline_root
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
                pipeline_info=tfx_pipeline.pipeline_info,
                enable_cache=tfx_pipeline.enable_cache,
                metadata_connection_config=tfx_pipeline.metadata_connection_config,
                beam_pipeline_args=tfx_pipeline.beam_pipeline_args,
                additional_pipeline_args=tfx_pipeline.additional_pipeline_args,
                component_config=component_config,
            )
            component_impl_map[tfx_component] = current_airflow_component
            for upstream_node in tfx_component.upstream_nodes:
                assert upstream_node in component_impl_map, (
                    "Components is not in " "topological order"
                )
                current_airflow_component.set_upstream(
                    component_impl_map[upstream_node]
                )

        return airflow_dag

    def _replace_runtime_params(self, comp):
        """Replaces runtime params for dynamic Airflow parameter execution.

        Args:
            comp (tfx.component): TFX component to be parsed.

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
                if prop.default.startswith("{{") and prop.default.endswith(
                    "}}"
                ):
                    default = prop.default[2:-2]
                else:
                    default = json.dumps(prop.default)

                template_field = '{{ dag_run.conf.get("%s", %s) }}' % (
                    prop.name,
                    default,
                )
                comp.exec_properties[k] = template_field
        return comp
