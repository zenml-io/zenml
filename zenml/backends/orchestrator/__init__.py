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

from zenml.backends.orchestrator.base.orchestrator_base_backend import \
    OrchestratorBaseBackend
from zenml.backends.orchestrator.gcp.orchestrator_gcp_backend import \
    OrchestratorGCPBackend
from zenml.backends.orchestrator.kubeflow.orchestrator_kubeflow_backend \
    import OrchestratorKubeFlowBackend
from zenml.backends.orchestrator.kubernetes.orchestrator_kubernetes_backend \
    import OrchestratorKubernetesBackend
from zenml.logger import get_logger
from zenml.utils.requirement_utils import check_integration, \
    AWS_INTEGRATION

logger = get_logger(__name__)

# check extra AWS requirements
try:
    check_integration(AWS_INTEGRATION)
    from zenml.backends.orchestrator.aws.orchestrator_aws_backend import \
        OrchestratorAWSBackend
except ModuleNotFoundError as e:
    logger.debug(f"There were failed imports due to missing integrations. "
                 f"OrchestratorAWSBackend was not imported. "
                 f"More information:")
    logger.debug(e)
