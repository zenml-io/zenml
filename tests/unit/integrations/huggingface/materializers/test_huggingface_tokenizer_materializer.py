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
from contextlib import ExitStack as does_not_raise

from transformers import AutoTokenizer
from transformers.tokenization_utils_base import PreTrainedTokenizerBase

from tests.unit.test_general import _test_materializer
from zenml.integrations.huggingface.materializers.huggingface_tokenizer_materializer import (
    HFTokenizerMaterializer,
)


def test_huggingface_tokenizer_materializer(clean_repo):
    """Tests whether the steps work for the Huggingface Tokenizer materializer."""

    with does_not_raise():
        _test_materializer(
            step_output=AutoTokenizer.from_pretrained("bert-base-cased"),
            materializer=HFTokenizerMaterializer,
        )

    last_run = clean_repo.get_pipeline("test_pipeline").runs[-1]
    tokenizer = last_run.steps[-1].output.read()
    assert isinstance(tokenizer, PreTrainedTokenizerBase)
    assert tokenizer.model_max_length == 512
