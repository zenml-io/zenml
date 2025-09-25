# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2025. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Intent classification training pipeline."""

from typing import Any

from steps.data import load_toy_intent_data
from steps.train import train_classifier_step

from zenml import pipeline
from zenml.config import DockerSettings


@pipeline(
    enable_cache=False,
    settings={
        "docker": DockerSettings(
            requirements="requirements.txt",
            environment={
                "OPENAI_API_KEY": "${OPENAI_API_KEY}",
            },
        )
    },
)
def intent_training_pipeline() -> Any:
    """Train intent classifier and tag as production.

    Returns:
        Trained sklearn pipeline with TF-IDF vectorizer and LogisticRegression classifier.
    """
    texts, labels = load_toy_intent_data()
    classifier = train_classifier_step(texts, labels)
    return classifier
