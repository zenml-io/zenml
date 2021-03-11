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

from typing import Text, List

from zenml.steps import BaseStep


class BaseTokenizer(BaseStep):
    """
    Base step class for all tokenizers.
    """

    def __init__(self,
                 text_feature: Text,
                 skip_training: bool = False,
                 **kwargs):
        super(BaseTokenizer, self).__init__(text_feature=text_feature,
                                            skip_training=skip_training,
                                            **kwargs)

        self.text_feature = text_feature
        self.skip_training = skip_training

    def train(self, files: List[Text]):
        raise NotImplementedError

    def encode(self, sequence: Text, output_format: Text):
        raise NotImplementedError

    def save(self, output_dir: Text):
        raise NotImplementedError

    def load_vocab(self, path_to_vocab: Text):
        raise NotImplementedError
