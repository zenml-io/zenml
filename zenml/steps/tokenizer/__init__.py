#  Copyright (c) maiot GmbH 2021. All Rights Reserved.
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

from zenml.steps.tokenizer.base_tokenizer import BaseTokenizer
from zenml.logger import get_logger
from zenml.utils.requirement_utils import check_integration, \
    HUGGINGFACE_INTEGRATION

logger = get_logger(__name__)

# HuggingFace extra requirement
try:
    check_integration(HUGGINGFACE_INTEGRATION)
    from zenml.steps.tokenizer.hf_tokenizer import \
        HuggingFaceTokenizerStep
except ModuleNotFoundError as e:
    logger.debug(f"There were failed imports due to missing integrations. "
                 f"HuggingFaceTokenizerStep was not imported. "
                 f"More information:")
    logger.debug(e)
