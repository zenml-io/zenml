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


from datetime import datetime as dt

import click
from config import MetaConfig
from pipelines import e2e_example_pipeline


@click.command(
    help="""
{{ project_name }} CLI v{{ version }}.

Run the {{ project_name }} model training pipeline with various
options.

Examples:


  \b
  # Run the pipeline with default options
  python run.py
               
  \b
  # Run the pipeline without cache
  python run.py --no-cache

  \b
  # Run the pipeline with custom model hyperparameters
  python run.py --hyperparameters C=0.1,max_iter=1000
"""
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run.",
)
# {%- if use_step_params %}
# {%- if configurable_dataset %}
# @click.option(
#     "--dataset",
#     default="{{ sklearn_dataset_name }}",
#     type=click.Choice(SklearnDataset.values()),
#     help="The scikit-learn dataset to load.",
# )
# {%- endif %}
# {%- if configurable_model %}
# @click.option(
#     "--model",
#     default="{{ sklearn_model_name }}",
#     type=click.Choice(SklearnClassifierModel.values()),
#     help="The scikit-learn model to train.",
# )
# {%- endif %}
# @click.option(
#     "--no-drop-na",
#     is_flag=True,
#     default=False,
#     help="Whether to skip dropping rows with missing values in the dataset.",
# )
# @click.option(
#     "--drop-columns",
#     default=None,
#     type=click.STRING,
#     help="Comma-separated list of columns to drop from the dataset.",
# )
# @click.option(
#     "--no-normalize",
#     is_flag=True,
#     default=False,
#     help="Whether to skip normalizing the dataset.",
# )
# @click.option(
#     "--test-size",
#     default=0.2,
#     type=click.FloatRange(0.0, 1.0),
#     help="Proportion of the dataset to include in the test split.",
# )
# @click.option(
#     "--no-shuffle",
#     is_flag=True,
#     default=False,
#     help="Whether to skip shuffling the data before splitting.",
# )
# @click.option(
#     "--no-stratify",
#     is_flag=True,
#     default=False,
#     help="Whether to skip stratifying the data before splitting.",
# )
# @click.option(
#     "--random-state",
#     default=42,
#     type=click.INT,
#     help="Controls the randomness during data shuffling and model training. "
#     "Pass an int for reproducible and cached output across multiple "
#     "pipeline runs.",
# )
@click.option(
    "--hyperparameters",
    default=None,
    type=click.STRING,
    help="Comma-separated list of hyper-parameters to pass to the model "
    "trainer (e.g. `C=0.1,max_iter=1000`).",
)
# @click.option(
#     "--min-train-accuracy",
#     default=0.8,
#     type=click.FloatRange(0.0, 1.0),
#     help="Minimum training accuracy to pass to the model evaluator.",
# )
# @click.option(
#     "--min-test-accuracy",
#     default=0.8,
#     type=click.FloatRange(0.0, 1.0),
#     help="Minimum test accuracy to pass to the model evaluator.",
# )
# @click.option(
#     "--max-train-test-diff",
#     default=0.1,
#     type=click.FloatRange(0.0, 1.0),
#     help="Maximum difference between training and test accuracy to pass to "
#     "the model evaluator.",
# )
# @click.option(
#     "--fail-on-eval-warnings",
#     is_flag=True,
#     default=False,
#     help="Whether to fail the pipeline run if the model evaluation step "
#     "finds that the model is not accurate enough.",
# )
# {%- endif %}
# def main(
#     no_cache: bool = False,
# {%- if use_step_params %}
# {%- if configurable_dataset %}
#     dataset: str = "{{ sklearn_dataset_name }}",
# {%- endif %}
# {%- if configurable_model %}
#     model: str = "{{ sklearn_model_name }}",
# {%- endif %}
#     no_drop_na: bool = False,
#     drop_columns: Optional[str] = None,
#     no_normalize: bool = False,
#     test_size: float = 0.2,
#     no_shuffle: bool = False,
#     no_stratify: bool = False,
#     random_state: int = 42,
#     hyperparameters: Optional[str] = None,
#     min_train_accuracy: float = 0.8,
#     min_test_accuracy: float = 0.8,
#     max_train_test_diff: float = 0.1,
#     fail_on_eval_warnings: bool = False,
# {%- endif %}
# ):
def main(no_cache: bool = False, hyperparameters: str = ""):
    """Main entry point for the pipeline execution.

    This entrypoint is where everything comes together:

      * configuring pipeline with the required parameters
        (some of which may come from command line arguments)
      * launching the pipeline
    """

    # Run a pipeline with the required parameters. This executes
    # all steps in the pipeline in the correct order using the orchestrator
    # stack component that is configured in your active ZenML stack.
    pipeline_args = {
        "run_name": f"{MetaConfig.runs_prefix}{dt.now().strftime('%Y_%m_%d_%H_%M_%S')}"
    }  # "e2e_example_run_{{date}}_{{time}}"}
    if no_cache:
        pipeline_args["enable_cache"] = False

    run_args = {}
    if hyperparameters:
        run_args["hyperparameters"] = {}
        for hp in hyperparameters.split(","):
            if hp:
                name, value = hp.split("=")
                if value.isnumeric():
                    value = int(value)
                elif value.replace(".", "").isnumeric():
                    value = float(value)
                run_args["hyperparameters"][name] = value

    e2e_example_pipeline.with_options(**pipeline_args)(**run_args)


if __name__ == "__main__":
    main()
