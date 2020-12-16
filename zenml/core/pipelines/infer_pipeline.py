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

from typing import Dict, Text, Any, List

from zenml.core.backends.orchestrator.local.orchestrator_local_backend import \
    OrchestratorLocalBackend
from zenml.core.backends.processing.processing_local_backend import \
    ProcessingLocalBackend
from zenml.core.pipelines.base_pipeline import BasePipeline


class BatchInferencePipeline(BasePipeline):
    """BatchInferencePipeline definition to run batch inference pipelines.

    A BatchInferencePipeline is used to run an inference based on a
    TrainingPipeline.
    """
    PIPELINE_TYPE = 'infer'

    def __init__(self, name: Text, *args, **kwargs):
        super().__init__(name, *args, **kwargs)
        raise NotImplementedError('Coming soon!')

    def get_tfx_component_list(self, config: Dict[Text, Any]) -> List:
        pass

    def get_default_backends(self) -> Dict:
        """Gets list of default backends for this pipeline."""
        # For base class, orchestration is always necessary
        return {
            OrchestratorLocalBackend.BACKEND_KEY: OrchestratorLocalBackend(),
            ProcessingLocalBackend.BACKEND_KEY: ProcessingLocalBackend()
        }
