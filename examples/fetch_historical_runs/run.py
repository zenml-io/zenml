#  Copyright (c) ZenML GmbH 2021. All Rights Reserved.
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
import random
from zenml.pipelines import pipeline
from zenml.steps import Output, StepContext, step


@step
def get_current_time() -> Output(random_num=int):
    """Loads the digits array as normal numpy arrays."""
    return random.randint(0, 100)


@step
def compare_to_previous_runs(
    context: StepContext,
    random_num: int
) -> None:
    """Evaluate all models and return the best one."""
    highest_random_number = random_num
    best_run = 'current run'

    pipeline_runs = context.metadata_store.get_pipeline("mnist_pipeline").runs
    for run in pipeline_runs:
        # get the trained model of all pipeline runs
        old_random_num = run.get_step("get_current_time").output.read()
        if old_random_num > highest_random_number:
            # if the model accuracy is better than our currently best model,
            # store it
            highest_random_number = old_random_num
            best_run = run.name

    print(f"Pipeline run  : {best_accuracy}")
    return best_model


@pipeline()
def example_pipeline(
    importer,
    trainer,
    evaluator,
):
    """Links all the steps together in a pipeline"""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    evaluator(X_test=X_test, y_test=y_test, model=model)


if __name__ == "__main__":

    pipeline = mnist_pipeline(
        importer=importer(),
        trainer=trainer(),
        evaluator=evaluate_and_store_best_model(),
    )
    pipeline.run()
