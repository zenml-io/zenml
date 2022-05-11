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

import os
from typing import List, Optional, Set

import kfp
from kubernetes import config as k8s_config
from tfx.orchestration.portable import data_types
from tfx.proto.orchestration.pipeline_pb2 import PipelineNode as Pb2PipelineNode

from zenml.entrypoints.step_entrypoint_configuration import (
    StepEntrypointConfiguration,
)
from zenml.integrations.kubeflow.orchestrators import entrypoint_utils
from zenml.steps import BaseStep


class KubeflowEntrypointConfiguration(StepEntrypointConfiguration):
    @classmethod
    def get_custom_entrypoint_options(cls) -> Set[str]:
        return {"metadata_ui_path"}

    @classmethod
    def get_custom_entrypoint_arguments(cls, step: BaseStep) -> List[str]:
        """Overwrite this in subclass if it needs custom additional arguments."""
        return ["--metadata_ui_path", "/outputs/mlpipeline-ui-metadata.json"]

    def get_run_name(self, pipeline_name: str) -> str:
        """"""
        k8s_config.load_incluster_config()
        run_id = os.environ["KFP_RUN_ID"]
        return kfp.Client().get_run(run_id).run.name  # type: ignore[no-any-return]

    def post_run(
        self,
        pipeline_name: str,
        step_name: str,
        pipeline_node: Pb2PipelineNode,
        execution_info: Optional[data_types.ExecutionInfo] = None,
    ) -> None:
        if execution_info:
            entrypoint_utils.dump_ui_metadata(
                node=pipeline_node,
                execution_info=execution_info,
                ui_metadata_path=self.entrypoint_args["metadata_ui_path"],
            )
