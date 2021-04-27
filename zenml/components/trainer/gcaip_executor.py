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
"""Definition of the GCAIP Training Executor"""

from tfx.extensions.google_cloud_ai_platform.trainer.executor import \
    GenericExecutor

from zenml.components.trainer.executor import ZenMLTrainerExecutor

# Keys to the items in custom_config passed as a part of exec_properties.
TRAINING_ARGS_KEY = 'ai_platform_training_args'
JOB_ID_KEY = 'ai_platform_training_job_id'
_CUSTOM_CONFIG_KEY = 'custom_config'


class ZenMLTrainerGCAIPExecutor(GenericExecutor):
    """Start a trainer job on Google Cloud AI Platform using a default
    Trainer."""

    def _GetExecutorClass(self):
        return ZenMLTrainerExecutor
