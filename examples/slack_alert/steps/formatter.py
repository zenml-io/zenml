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

from zenml.steps import step


@step
def test_acc_post_formatter(test_acc: float) -> str:
    """Wrap given test accuracy in a nice text message."""
    return f"Test Accuracy: {test_acc}"


@step
def test_acc_ask_formatter(test_acc: float) -> str:
    """Wrap given test accuracy in a nice text message."""
    return (
        f"Model training finished. Test accuracy: {test_acc}. "
        f"Deploy now? [approve | reject]"
    )
