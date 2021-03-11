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
"""Definition of the base Training Backend"""

from zenml.components.trainer.executor import ZenMLTrainerExecutor
from tfx.dsl.components.base import executor_spec

from zenml.backends import BaseBackend


class TrainingBaseBackend(BaseBackend):
    """
    Base class for all base Training ZenML backends.

    Every ZenML pipeline runs in backends.

    A training backend can be used to efficiently train a machine learning
    model on large amounts of data. Since most common machine learning models
    leverage mainly linear algebra operations under the hood, they can
    potentially benefit a lot from dedicated training hardware like Graphics
    Processing Units (GPUs) or application-specific integrated circuits
    (ASICs).
    """
    BACKEND_TYPE = 'training'

    def get_executor_spec(self):
        """Return a TFX Executor spec for the Trainer Component."""
        return executor_spec.ExecutorClassSpec(ZenMLTrainerExecutor)

    def get_custom_config(self):
        """Return a dict to be passed as a custom_config to the Trainer."""
        return {}
