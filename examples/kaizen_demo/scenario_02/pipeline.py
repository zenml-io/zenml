#  Copyright (c) ZenML GmbH 2026. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at:
#
#       https://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.

"""Score customer activity and evaluate observed conversions."""

from zenml import pipeline
from zenml.config import DockerSettings

from .steps import (
    evaluate_scores,
    load_customer_data,
    prepare_customer_features,
    score_customers,
    train_customer_model,
)


@pipeline(settings={"docker": DockerSettings(requirements="requirements.txt")})
def customer_scoring(source_uri: str) -> dict[str, float]:
    """Read customer activity, score conversion, and calculate quality metrics.

    Args:
        source_uri: CSV path or URI readable through the active artifact store.
            HTTP sources must use a URL without embedded credentials.

    Returns:
        Classification metrics for the observed conversions.
    """
    raw_rows = load_customer_data(source_uri=source_uri)
    features = prepare_customer_features(raw_rows=raw_rows)
    model = train_customer_model()
    predictions = score_customers(
        model=model, features=features, raw_rows=raw_rows
    )
    return evaluate_scores(predictions=predictions)
