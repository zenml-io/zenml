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

# contains extra AWS requirements
try:
    from zenml.core.backends.orchestrator.aws.orchestrator_aws_backend import \
     OrchestratorAWSBackend
except ModuleNotFoundError:
    pass

from zenml.core.backends.orchestrator.base.orchestrator_base_backend import \
    OrchestratorBaseBackend
# errors out because of breaking changes in TFX
# from zenml.core.backends.orchestrator.beam.orchestrator_beam_backend import \
#     OrchestratorBeamBackend
from zenml.core.backends.orchestrator.gcp.orchestrator_gcp_backend import \
    OrchestratorGCPBackend
from zenml.core.backends.orchestrator.kubeflow.orchestrator_kubeflow_backend \
    import OrchestratorKubeFlowBackend
from zenml.core.backends.orchestrator.kubernetes.\
    orchestrator_kubernetes_backend import OrchestratorKubernetesBackend
