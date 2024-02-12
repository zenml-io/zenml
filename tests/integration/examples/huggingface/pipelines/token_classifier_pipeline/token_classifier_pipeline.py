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
from steps import (
    data_importer,
    load_tokenizer,
    token_classification_tokenization,
    token_evaluator,
    token_trainer,
)

from zenml import pipeline
from zenml.config import DockerSettings
from zenml.integrations.constants import HUGGINGFACE, PYTORCH, TENSORFLOW

docker_settings = DockerSettings(
    required_integrations=[HUGGINGFACE, TENSORFLOW, PYTORCH],
    environment={"HF_HOME": "/app/huggingface"},
)


@pipeline(settings={"docker": docker_settings})
def token_classifier_train_eval_pipeline():
    """Train and Evaluation pipeline."""
    datasets = data_importer("conll2003")
    tokenizer = load_tokenizer()
    tokenized_datasets = token_classification_tokenization(
        tokenizer=tokenizer, datasets=datasets
    )
    model = token_trainer(
        tokenized_datasets=tokenized_datasets, tokenizer=tokenizer
    )
    token_evaluator(
        model=model, tokenized_datasets=tokenized_datasets, tokenizer=tokenizer
    )
