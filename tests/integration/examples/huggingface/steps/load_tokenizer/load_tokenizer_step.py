#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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

from transformers import AutoTokenizer, PreTrainedTokenizerBase

from zenml import step


@step
def load_tokenizer(
    pretrained_model: str = "dhpollack/distilbert-dummy-sentiment",
) -> PreTrainedTokenizerBase:
    """Load pretrained tokenizer."""
    return AutoTokenizer.from_pretrained(pretrained_model)
