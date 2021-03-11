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

from zenml.steps.trainer.base_trainer import BaseTrainerStep
from zenml.steps.trainer.tensorflow_trainers.tf_base_trainer import \
    TFBaseTrainerStep
from zenml.steps.trainer.tensorflow_trainers.tf_ff_trainer import \
    FeedForwardTrainer as TFFeedForwardTrainer
from zenml.logger import get_logger
from zenml.utils.requirement_utils import check_integration, \
    PYTORCH_INTEGRATION

logger = get_logger(__name__)

# wrap Pytorch extra integrations safely
try:
    check_integration(PYTORCH_INTEGRATION)
    from zenml.steps.trainer.pytorch_trainers.torch_base_trainer import \
        TorchBaseTrainerStep
    from zenml.steps.trainer.pytorch_trainers.torch_ff_trainer import \
        FeedForwardTrainer as TorchFeedForwardTrainer
except ModuleNotFoundError as e:
    logger.debug(f"There were failed imports due to missing integrations. "
                 f"TorchBaseTrainerStep, TorchFeedForwardTrainer were not "
                 f"imported. More information:")
    logger.debug(e)
