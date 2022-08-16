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
from zenml.integrations.slack.steps.slack_alerter_ask_step import (
    slack_alerter_ask_step,
)
from zenml.integrations.slack.steps.slack_alerter_post_step import (
    slack_alerter_post_step,
)

from .data_loader import digits_data_loader
from .deployer import model_deployer
from .evaluator import evaluator
from .formatter import test_acc_ask_formatter, test_acc_post_formatter
from .trainer import svc_trainer, svc_trainer_mlflow

__all__ = [
    "model_deployer",
    "digits_data_loader",
    "evaluator",
    "svc_trainer",
    "test_acc_ask_formatter",
    "test_acc_post_formatter",
    "svc_trainer_mlflow",
    "slack_alerter_post_step",
    "slack_alerter_ask_step",
]
