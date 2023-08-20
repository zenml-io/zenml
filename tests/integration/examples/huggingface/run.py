#  Copyright (c) ZenML GmbH 2023. All Rights Reserved.
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
import click
from pipelines import (
    seq_classifier_train_eval_pipeline,
    token_classifier_train_eval_pipeline,
)


@click.command()
@click.option(
    "--nlp_task",
    type=click.Choice(["token-classification", "sequence-classification"]),
    default="sequence-classification",
    help="Name NLP task i.e. token-classification, sequence-classification",
)
def main(nlp_task: str):
    if nlp_task == "token-classification":
        token_classifier_train_eval_pipeline()

    elif nlp_task == "sequence-classification":
        seq_classifier_train_eval_pipeline()


if __name__ == "__main__":
    main()
