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

from zenml import step


@step
def deployment_trigger(
    accuracy: float,
    min_accuracy: float,
) -> bool:
    """Implement a simple model deployment trigger.

    The trigger looks at the input model accuracy and decides if it is good
    enough to deploy.

    Args:
        accuracy: The accuracy of the model.
        min_accuracy: The minimum accuracy required to deploy the model.


    Returns:
        True if the model is good enough to deploy, False otherwise.
    """
    return accuracy > min_accuracy
