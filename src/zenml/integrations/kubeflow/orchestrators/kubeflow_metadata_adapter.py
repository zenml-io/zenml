# Copyright 2019 Google LLC
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
"""A Metadata adapter class used to add Kubeflow-specific context."""

import os
from typing import Any, Dict

import absl
from ml_metadata.proto import metadata_store_pb2
from tfx.orchestration import data_types, metadata

_KFP_POD_NAME_ENV_KEY = "KFP_POD_NAME"
_KFP_POD_NAME_PROPERTY_KEY = "kfp_pod_name"


class KubeflowMetadataAdapter(metadata.Metadata):
    """A Metadata adapter class for pipelines run using KFP.

    This is used to add properties to artifacts and executions, such as the Argo
    pod IDs.
    """

    def _is_eligible_previous_execution(
        self,
        current_execution: metadata_store_pb2.Execution,
        target_execution: metadata_store_pb2.Execution,
    ) -> bool:
        current_execution.properties[
            _KFP_POD_NAME_PROPERTY_KEY
        ].string_value = ""
        target_execution.properties[
            _KFP_POD_NAME_PROPERTY_KEY
        ].string_value = ""
        return super()._is_eligible_previous_execution(
            current_execution, target_execution
        )

    def _prepare_execution(
        self,
        state: str,
        exec_properties: Dict[str, Any],
        pipeline_info: data_types.PipelineInfo,
        component_info: data_types.ComponentInfo,
    ) -> metadata_store_pb2.Execution:
        if os.environ[_KFP_POD_NAME_ENV_KEY]:
            kfp_pod_name = os.environ[_KFP_POD_NAME_ENV_KEY]
            absl.logging.info(
                "Adding KFP pod name %s to execution" % kfp_pod_name
            )
            exec_properties[_KFP_POD_NAME_PROPERTY_KEY] = kfp_pod_name
        return super()._prepare_execution(
            state, exec_properties, pipeline_info, component_info
        )
