#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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

from typing import List

from torch.utils.data import Dataset
from unstructured.partition.html import partition_html

from .mingpt.bpe import BPETokenizer


class UrlTokenDataset(Dataset):
    def __init__(self, urls: List[str], block_size: int = 20) -> None:
        self.examples = []
        for url in urls:
            elements = partition_html(url=url)
            text = "\n\n".join([str(el) for el in elements])
            tokenizer = BPETokenizer()
            tokens = tokenizer(text).flatten()
            for i in range(0, len(tokens) - block_size + 1, block_size):
                self.examples.append(tokens[i : i + block_size + 1])

    def __len__(self):
        return len(self.examples)

    def __getitem__(self, item):
        example = self.examples[item]
        x = example[:-1].clone()
        y = example[1:].clone()
        return x, y
