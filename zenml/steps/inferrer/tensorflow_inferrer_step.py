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

from typing import Text, List

from zenml.steps.inferrer import BaseInferrer


class TensorflowInferrer(BaseInferrer):
    """
    Tensorflow Inferrer.
    """

    def __init__(self,
                 labels: List[Text],
                 **kwargs):
        """
        Base Tensorflow Inferrer constructor.

        Args:
            labels: Outward-facing name of the pipeline.
        """
        self.labels = labels
        super(TensorflowInferrer, self).__init__(
            labels=labels,
            **kwargs,
        )
