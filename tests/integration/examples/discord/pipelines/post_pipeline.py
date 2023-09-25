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

from steps.data_loader import digits_data_loader
from steps.evaluator import evaluator
from steps.formatter import test_acc_post_formatter
from steps.trainer import svc_trainer

from zenml import pipeline
from zenml.integrations.discord.steps.discord_alerter_post_step import (
    discord_alerter_post_step,
)


@pipeline(enable_cache=False)
def discord_post_pipeline():
    """Train and evaluate a model and post the test accuracy to Discord."""
    X_train, X_test, y_train, y_test = digits_data_loader()
    model = svc_trainer(X_train=X_train, y_train=y_train)
    test_acc = evaluator(X_test=X_test, y_test=y_test, model=model)
    message = test_acc_post_formatter(test_acc)
    discord_alerter_post_step(message)
