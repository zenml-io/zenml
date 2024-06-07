# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from transformers import AutoTokenizer, PreTrainedTokenizerBase
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def tokenizer_loader(
    lower_case: bool,
) -> Annotated[PreTrainedTokenizerBase, "tokenizer"]:
    """Tokenizer selection step.

    This step is responsible for selecting and initializing the tokenizer based
    on the model type. The tokenizer is a crucial component in Natural Language
    Processing tasks as it is responsible for converting the input text into a
    format that the model can understand.

    This step is parameterized, which allows you to configure the step independently
    of the step code, before running it in a pipeline. In this example, the step can
    be configured to use different types of tokenizers corresponding to different
    models such as 'bert', 'roberta', or 'distilbert'.

    For more information on how to configure steps in a pipeline, refer to the
    following documentation:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        lower_case: A boolean value indicating whether to convert the input text to
        lower case during tokenization.

    Returns:
        The initialized tokenizer.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    tokenizer = AutoTokenizer.from_pretrained(
        "distilbert-base-uncased", do_lower_case=lower_case
    )
    ### YOUR CODE ENDS HERE ###

    return tokenizer
