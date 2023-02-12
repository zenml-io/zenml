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

from typing import Any, Dict, Optional

import click
from pipelines import (
    model_training_pipeline,
)
from steps import (
    DataLoaderStepParameters,
    DataProcessorStepParameters,
    DataSplitterStepParameters,
    ModelEvaluatorStepParameters,
    ModelTrainerStepParameters,
    SklearnClassifierModel,
    SklearnDataset,
    data_loader,
    data_processor,
    data_splitter,
    model_evaluator,
    model_trainer,
)


def process_hyper_parameters(params: Optional[str] = None) -> Dict[str, Any]:
    """Process hyper parameters entered by the user from the command line.

    This function is used to parse hyper parameters entered by the user in
    the command line from a key-value string format (e.g. "C=0.1,max_iter=1000")
    to a dictionary with the correct data types (int, float, bool).

    Args:
        params: A string of comma-separated key-value pairs.

    Returns:
        A dictionary of hyper parameters converted to the correct type (int,
        float, bool)
    """
    if not params:
        return {}
    try:
        params = params.split(",")
        params = [param.split("=") for param in params]
        params = {key: value for key, value in params}
    except ValueError:
        raise ValueError(
            "Invalid format for hyperparameters. "
            "Expected a comma-separated list of key-value pairs "
            "(e.g. 'C=0.1,max_iter=1000')."
        )
    for key, value in params.items():
        try:
            params[key] = int(value)
            continue
        except ValueError:
            pass
        try:
            params[key] = float(value)
            continue
        except ValueError:
            pass
        if value.lower() == "true":
            params[key] = True
            continue
        if value.lower() == "false":
            params[key] = False
            continue
    return params


@click.command(
    help="""
ZenML Starter CLI v0.1.0.

Run the ZenML Starter model training pipeline with various
options.

Examples:

  \b
  # Run the pipeline with default options
  python run.py

  \b
  # Run the pipeline with caching disabled
  python run.py --no-cache

  \b
  # Run the pipeline with a different dataset
  python run.py --dataset=breast_cancer

  \b
  # Run the pipeline with a different model
  python run.py --model=SVM

  \b
  # Run the pipeline with custom hyperparameters for the model training step
  python run.py --hyperparameters="C=0.1,max_iter=1000"

  \b
  # Run the pipeline with custom data splitter step parameters
  python run.py --test-size=0.1 --no-stratify

  \b
  # Run the pipeline with custom data processor step parameters
  python run.py --drop-columns="alcohol,ash" --no-normalize

  \b
  # Run the pipeline with a different random seed
  python run.py --random-state=40

  \b
  # Change the model evaluation thresholds
  python run.py --min-train-accuracy=0.98 --min-test-accuracy=0.98 --max-train-test-diff=0.05 --fail-on-eval-warnings
"""
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run.",
)
@click.option(
    "--dataset",
    default="wine",
    type=click.Choice(SklearnDataset.values()),
    help="The scikit-learn dataset to load.",
)
@click.option(
    "--model",
    default="LogisticRegression",
    type=click.Choice(SklearnClassifierModel.values()),
    help="The scikit-learn model to train.",
)
@click.option(
    "--no-drop-na",
    is_flag=True,
    default=False,
    help="Whether to skip dropping rows with missing values in the dataset.",
)
@click.option(
    "--drop-columns",
    default=None,
    type=click.STRING,
    help="Comma-separated list of columns to drop from the dataset.",
)
@click.option(
    "--no-normalize",
    is_flag=True,
    default=False,
    help="Whether to skip normalizing the dataset.",
)
@click.option(
    "--test-size",
    default=0.2,
    type=click.FloatRange(0.0, 1.0),
    help="Proportion of the dataset to include in the test split.",
)
@click.option(
    "--no-shuffle",
    is_flag=True,
    default=False,
    help="Whether to skip shuffling the data before splitting.",
)
@click.option(
    "--no-stratify",
    is_flag=True,
    default=False,
    help="Whether to skip stratifying the data before splitting.",
)
@click.option(
    "--random-state",
    default=42,
    type=click.INT,
    help="Controls the randomness during data shuffling and model training. "
    "Pass an int for reproducible and cached output across multiple "
    "pipeline runs.",
)
@click.option(
    "--hyperparameters",
    default=None,
    type=click.STRING,
    help="Comma-separated list of hyper-parameters to pass to the model "
    "trainer (e.g. 'C=0.1,max_iter=1000').",
)
@click.option(
    "--min-train-accuracy",
    default=0.8,
    type=click.FloatRange(0.0, 1.0),
    help="Minimum training accuracy to pass to the model evaluator.",
)
@click.option(
    "--min-test-accuracy",
    default=0.8,
    type=click.FloatRange(0.0, 1.0),
    help="Minimum test accuracy to pass to the model evaluator.",
)
@click.option(
    "--max-train-test-diff",
    default=0.1,
    type=click.FloatRange(0.0, 1.0),
    help="Maximum difference between training and test accuracy to pass to "
    "the model evaluator.",
)
@click.option(
    "--fail-on-eval-warnings",
    is_flag=True,
    default=False,
    help="Whether to fail the pipeline run if the model evaluation step "
    "finds that the model is not accurate enough.",
)
def main(
    no_cache: bool = False,
    dataset: str = "wine",
    model: str = "LogisticRegression",
    no_drop_na: bool = False,
    drop_columns: Optional[str] = None,
    no_normalize: bool = False,
    test_size: float = 0.2,
    no_shuffle: bool = False,
    no_stratify: bool = False,
    random_state: int = 42,
    hyperparameters: Optional[str] = None,
    min_train_accuracy: float = 0.8,
    min_test_accuracy: float = 0.8,
    max_train_test_diff: float = 0.1,
    fail_on_eval_warnings: bool = False,
):
    """Main entry point for the pipeline execution.

    This entrypoint is where everything comes together:

      * instantiating the steps and configuring them with the required
        parameters (some of which may come from command line arguments)
      * creating a pipeline instance that brings together all step instances
      * launching the pipeline
      * extracting and looking at the artifacts logged by the pipeline run
    """

    # Initialize a pipeline. This is also where we instantiate the steps and
    # configure them with the required parameters. The step instances are
    # then passed to the pipeline constructor. The result is a pipeline
    # instance that is ready to be run.
    pipeline = model_training_pipeline(
        data_loader=data_loader(
            params=DataLoaderStepParameters(
                dataset=SklearnDataset(dataset),
            ),
        ),
        data_processor=data_processor(
            params=DataProcessorStepParameters(
                drop_na=not no_drop_na,
                drop_columns=drop_columns.split(",") if drop_columns else [],
                normalize=not no_normalize,
            ),
        ),
        data_splitter=data_splitter(
            params=DataSplitterStepParameters(
                test_size=test_size,
                shuffle=not no_shuffle,
                stratify=not no_stratify,
                random_state=random_state,
            ),
        ),
        model_trainer=model_trainer(
            params=ModelTrainerStepParameters(
                model=SklearnClassifierModel(model),
                random_state=random_state,
                hyperparameters=process_hyper_parameters(hyperparameters),
            ),
        ),
        model_evaluator=model_evaluator(
            params=ModelEvaluatorStepParameters(
                min_train_accuracy=min_train_accuracy,
                min_test_accuracy=min_test_accuracy,
                max_train_test_accuracy_difference=max_train_test_diff,
                fail_on_warnings=fail_on_eval_warnings,
            ),
        ),
    )

    pipeline_args = {}
    if no_cache:
        pipeline_args["enable_cache"] = False

    # Run the pipeline. This executes all steps in the pipeline in the
    # correct order using the orchestrator stack component that is configured
    # in your active ZenML stack.
    pipeline.run(**pipeline_args)

    # TODO:
    # extract the evaluator result and show here
    # Point to the dashboard URL (if running); instruct to start the dashboard
    # info on how to use the CLI to show pipeline run details.
    # add experiment tracker to steps (flag)

    # materialization:
    # * - create a dummy class (statistics, report, visualization) and use that
    #   in the pipeline step and post-execution


if __name__ == "__main__":
    main()
