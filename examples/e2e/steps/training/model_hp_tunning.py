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


from typing import Annotated, Any, Dict

import pandas as pd
from config import MetaConfig
from sklearn.metrics import accuracy_score
from sklearn.model_selection import RandomizedSearchCV

from zenml import step
from zenml.logger import get_logger

logger = get_logger(__name__)


@step
def model_hp_tunning(
    hp_tunning_enabled: bool,
    dataset_trn: pd.DataFrame,
    dataset_tst: pd.DataFrame,
) -> Annotated[Dict[str, Any], "best_model"]:
    """Evaluate a trained model.

    This is an example of a model hyperparameter tunning step that takes
    in train and test datatsets to perform a randomized search for best model
    in configured space.

    This step is parameterized to configure the step independently of the step code,
    before running it in a pipeline. In this example, the step can be configured
    to use different input datasets and also have a flag to fall back to default
    model architecture. See the documentation for more information:

        https://docs.zenml.io/user-guide/advanced-guide/configure-steps-pipelines

    Args:
        hp_tunning_enabled: If `False` default model will be used, otherwise search
            will happen.
        dataset_trn: The train dataset.
        dataset_tst: The test dataset.

    Returns:
        The best possible model class and its' parameters.
    """
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    if hp_tunning_enabled:
        logger.info("Running Hyperparameter tunning...")
        best_model = {"class": None, "params": None}
        best_score_overall = -1
        for (
            model_config_name,
            model_config,
        ) in MetaConfig.supported_models.items():
            model_class = model_config["class"]
            grid = model_config["search_grid"]
            cv = RandomizedSearchCV(
                estimator=model_class(),
                param_distributions=grid,
                cv=3,
                n_jobs=-1,
                n_iter=10,
                random_state=42,
                scoring="accuracy",
            )
            cv.fit(
                X=dataset_trn.drop(columns=[MetaConfig.target_column]),
                y=dataset_trn[MetaConfig.target_column],
            )
            y_pred = cv.predict(
                dataset_tst.drop(columns=[MetaConfig.target_column])
            )
            score = accuracy_score(
                dataset_tst[MetaConfig.target_column], y_pred
            )
            if best_score_overall < score:
                logger.info(
                    f"New best model: {model_config_name} with "
                    f"{score*100:.2f}% accuracy on test and following parameters: {cv.best_params_}"
                )
                best_score_overall = score
                best_model["class"] = model_class
                best_model["params"] = cv.best_params_
    else:
        logger.info(
            "Hyperparameter job skipped. "
            f"Using default model: {MetaConfig.default_model_config['class'].__class__.__name__} with "
            f"following parameters:{MetaConfig.default_model_config['params']}"
        )
        best_model = MetaConfig.default_model_config
    ### YOUR CODE ENDS HERE ###
    return best_model
