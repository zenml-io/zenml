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

from steps.data_loader import digits_data_loader
from steps.evaluator import evaluator
from steps.formatter import test_acc_ask_formatter
from steps.trainer_mlflow import svc_trainer_mlflow

from zenml import pipeline
from zenml.integrations.mlflow.steps import mlflow_model_deployer_step
from zenml.integrations.slack.steps.slack_alerter_ask_step import (
    slack_alerter_ask_step,
)


@pipeline(enable_cache=False)
def slack_ask_pipeline():
    """Train and evaluate a model and asks user in Slack whether to deploy."""
    X_train, X_test, y_train, y_test = digits_data_loader()
    model = svc_trainer_mlflow(X_train=X_train, y_train=y_train)
    test_acc = evaluator(X_test=X_test, y_test=y_test, model=model)
    message = test_acc_ask_formatter(test_acc)
    approved = slack_alerter_ask_step(message)
    mlflow_model_deployer_step(model=model, deploy_decision=approved)
