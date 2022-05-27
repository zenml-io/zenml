#  Copyright (c) ZenML GmbH 2022. All Rights Reserved.
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


from steps import evaluator, importer, svc_trainer

from zenml.alerter.alerter_step import alerter_post_step
from zenml.pipelines import pipeline
from zenml.steps import step


@step
def test_acc_formatter(test_acc: float) -> str:
    """Wrap given test accuracy in a nice text message."""
    return f"Test Accuracy: {test_acc}"


@pipeline
def slack_pipeline(importer, trainer, evaluator, formatter, alerter):
    """Train and evaluate a model and post the test accuracy to slack."""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    test_acc = evaluator(X_test=X_test, y_test=y_test, model=model)
    message = formatter(test_acc)
    alerter(message)


if __name__ == "__main__":
    slack_pipeline(
        importer=importer(),
        trainer=svc_trainer(),
        evaluator=evaluator(),
        formatter=test_acc_formatter(),
        alerter=alerter_post_step(),
    ).run()
