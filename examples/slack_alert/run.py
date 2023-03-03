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
import click
from pipelines.ask_pipeline import slack_ask_pipeline
from pipelines.post_pipeline import slack_post_pipeline
from steps import (
    digits_data_loader,
    evaluator,
    svc_trainer,
    svc_trainer_mlflow,
    test_acc_ask_formatter,
    test_acc_post_formatter,
)

from zenml.integrations.mlflow.steps import mlflow_model_deployer_step
from zenml.integrations.slack.steps.slack_alerter_ask_step import (
    slack_alerter_ask_step,
)
from zenml.integrations.slack.steps.slack_alerter_post_step import (
    slack_alerter_post_step,
)

POST = "post"
ASK = "ask"


@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Choice([POST, ASK]),
    default=POST,
    help="Configure whether to run the post or ask pipeline.",
)
def main(config: str):
    """Run the Slack alerter example pipeline."""
    post = config == POST

    if post:
        slack_post_pipeline(
            data_loader=digits_data_loader(),
            trainer=svc_trainer(),
            evaluator=evaluator(),
            formatter=test_acc_post_formatter(),
            alerter=slack_alerter_post_step(),
        ).run()
    else:
        slack_ask_pipeline(
            data_loader=digits_data_loader(),
            trainer=svc_trainer_mlflow(),
            evaluator=evaluator(),
            formatter=test_acc_ask_formatter(),
            alerter=slack_alerter_ask_step(),
            deployer=mlflow_model_deployer_step(),
        ).run()


if __name__ == "__main__":
    main()
