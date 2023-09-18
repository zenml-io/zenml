# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2023. All rights reserved.
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
#


import pandas as pd
from artifacts.materializer import ModelMetadataMaterializer
from artifacts.model_metadata import ModelMetadata
from sklearn.metrics import accuracy_score
from sklearn.model_selection import RandomizedSearchCV
from typing_extensions import Annotated

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step(output_materializers=ModelMetadataMaterializer)
def hp_tuning_single_search(
    model_metadata: ModelMetadata,
    dataset_trn: pd.DataFrame,
    dataset_tst: pd.DataFrame,
    target: str,
) -> Annotated[ModelMetadata, "best_model"]:
    """Evaluate a trained model.

    This is an example of a model hyperparameter tuning step that takes
    in train and test datasets to perform a randomized search for best model
    in configured space.

    This step is parameterized to configure the step independently of the step code,
    before running it in a pipeline. In this example, the step can be configured
    to use different input datasets and also have a flag to fall back to default
    model architecture. See the documentation for more information:

        https://docs.zenml.io/user-guide/advanced-guide/configure-steps-pipelines

    Args:
        model_metadata: `ModelMetadata` to search
        dataset_trn: The train dataset.
        dataset_tst: The test dataset.
        target: Name of target columns in dataset.

    Returns:
        The best possible model parameters for given config.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###

    X_trn = dataset_trn.drop(columns=[target])
    y_trn = dataset_trn[target]
    X_tst = dataset_tst.drop(columns=[target])
    y_tst = dataset_tst[target]
    logger.info("Running Hyperparameter tuning...")
    best_model = {"class": None, "params": None, "metric": -1}
    cv = RandomizedSearchCV(
        estimator=model_metadata.model_class(),
        param_distributions=model_metadata.search_grid,
        cv=3,
        n_jobs=-1,
        n_iter=10,
        random_state=42,
        scoring="accuracy",
    )
    cv.fit(X=X_trn, y=y_trn)
    y_pred = cv.predict(X_tst)
    score = accuracy_score(y_tst, y_pred)
    best_model = ModelMetadata(
        model_metadata.model_class,
        params=cv.best_params_,
        metric=score,
    )
    ### YOUR CODE ENDS HERE ###
    return best_model
