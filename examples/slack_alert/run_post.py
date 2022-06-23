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

from pipelines.post_pipeline import slack_post_pipeline
from steps import evaluator, importer, svc_trainer, test_acc_post_formatter

from zenml.integrations.slack.steps.slack_alerter_post_step import (
    slack_alerter_post_step,
)

if __name__ == "__main__":
    slack_post_pipeline(
        importer=importer(),
        trainer=svc_trainer(),
        evaluator=evaluator(),
        formatter=test_acc_post_formatter(),
        alerter=slack_alerter_post_step(),
    ).run()
