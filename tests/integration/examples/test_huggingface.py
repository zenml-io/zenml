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

import sys

import pytest

from tests.integration.examples.utils import run_example

# TODO: enable this once the token classification example is fixed
# def test_token_classification(request: pytest.FixtureRequest) -> None:
#     """Runs the huggingface token classification example."""

#     with run_example(
#         request=request,
#         name="huggingface",
#         example_args=["--nlp_task", "token-classification"],
#         pipelines={"token_classifier_train_eval_pipeline": (1, 5)},
#     ):
#         pass


@pytest.mark.skipif(
    sys.version_info.major == 3 and sys.version_info.minor == 8,
    reason="Tensorflow integration does not work as expected with python3.8.",
)
def test_sequence_classification(request: pytest.FixtureRequest) -> None:
    """Runs the huggingface sequence classification example."""

    with run_example(
        request=request,
        name="huggingface",
        example_args=["--task", "sequence-classification"],
        pipelines={"seq_classifier_train_eval_pipeline": (1, 5)},
    ):
        pass
