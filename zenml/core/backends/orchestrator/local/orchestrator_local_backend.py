#  Copyright (c) maiot GmbH 2020. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
#  or implied. See the License for the specific language governing
#  permissions and limitations under the License.
"""Definition of the base Orchestrator Backend"""

from typing import Dict, Text, Any

from tfx.orchestration import pipeline

from zenml.core.backends.base_backend import BaseBackend
from zenml.core.backends.orchestrator.local.zenml_local_orchestrator import \
    ZenMLLocalDagRunner
from zenml.core.standards.standard_keys import EnvironmentKeys


class OrchestratorLocalBackend(BaseBackend):
    """Base class for all ZenML orchestrator backends.

    Every ZenML pipeline runs in backends
    """
    BACKEND_TYPE = 'local'
    BACKEND_KEY = 'orchestrator'

    @staticmethod
    def get_tfx_pipeline(config: Dict[Text, Any]) -> pipeline.Pipeline:
        """
        Converts ZenML config dict to TFX pipeline.

        Args:
            config: a ZenML config dict

        Returns: a TFX pipeline object.
        """
        from zenml.core.pipelines.base_pipeline import BasePipeline
        zenml_pipeline = BasePipeline.from_config(config)
        component_list = zenml_pipeline.get_tfx_component_list(config)
        spec = zenml_pipeline.get_pipeline_spec(config)

        tfx_pipeline = pipeline.Pipeline(
            components=component_list,
            beam_pipeline_args=spec['execution_args'],
            metadata_connection_config=spec['metadata_connection_config'],
            pipeline_name=spec['repo_id'],
            pipeline_root=spec['pipeline_root'],
            log_root=spec['pipeline_log_root'],
            enable_cache=spec[EnvironmentKeys.ENABLE_CACHE])

        # Ensure that the run_id is ZenML pipeline_name
        tfx_pipeline.pipeline_info.run_id = zenml_pipeline.pipeline_name
        return tfx_pipeline

    def run(self, config: Dict[Text, Any]):
        """
        This run function essentially calls an underlying TFX orchestrator run.
        However it is meant as a higher level abstraction with some
        opinionated decisions taken.

        Args:
            config: a ZenML config dict
        """
        tfx_pipeline = self.get_tfx_pipeline(config)
        ZenMLLocalDagRunner().run(tfx_pipeline)
