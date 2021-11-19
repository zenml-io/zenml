#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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

import os

from zenml.core.repo import Repository

os.environ["ZENML_DEBUG"] = "true"
import pandas as pd

from zenml.pipelines import pipeline
from zenml.steps import step


@step
def importer() -> pd.DataFrame:
    return pd.DataFrame({"X_train": [1, 2, 3], "y_train": [0, 0, 0]})


@step
def preprocesser(df: pd.DataFrame) -> pd.DataFrame:
    return df


@step
def trainer(df: pd.DataFrame) -> int:
    return 2


@step
def evaluator(df: pd.DataFrame, model: int) -> int:
    return 2


@step
def deployer(model: int, evaluation_results: int) -> bool:
    return True


@pipeline
def my_pipeline(importer, preprocesser, trainer, evaluator, deployer):
    df = importer()
    preprocessed_df = preprocesser(df=df)
    model = trainer(df=preprocessed_df)
    evaluation_results = evaluator(df=df, model=model)
    deployer(model=model, evaluation_results=evaluation_results)


# Pipeline
lineage_pipeline = my_pipeline(
    importer=importer(),
    preprocesser=preprocesser(),
    trainer=trainer(),
    evaluator=evaluator(),
    deployer=deployer(),
)

lineage_pipeline.run()

pipeline = Repository().get_pipelines()[-1]

for run in pipeline.runs:
    try:
        deployer_step = run.get_step(name="deployer")
        trainer_step = run.get_step(name="trainer")
        deployed_model_artifact = deployer_step.inputs["model"]
        trained_model_artifact = trainer_step.output

        # lets do the lineage
        print(
            f"trained_model_artifact was produced by: "
            f"{trained_model_artifact.producer_step.id} and is_cached: "
            f"{trained_model_artifact.is_cached} step cached: "
            f"{trainer_step.status}"
        )
    except Exception as e:
        if "No step found for name `deployer`" in str(e):
            pass
        else:
            raise e
