# 

import os
from datetime import datetime as dt
from typing import Optional

import click
from zenml.logger import get_logger

from pipelines import (
    supply_chain_forecast_batch_inference,
    supply_chain_forecast_deployment,
    supply_chain_forecast_training,
)

logger = get_logger(__name__)


@click.command(
    help="""
Supply Chain Forecasting CLI v0.0.1.

Run the Supply Chain Forecasting model training pipeline with various
options.

Examples:


  \b
  # Run the pipeline with default options
  python run.py
               
  \b
  # Run the pipeline without cache
  python run.py --no-cache

  \b
  # Run the pipeline without Hyperparameter tuning
  python run.py --no-hp-tuning

  \b
  # Run the pipeline without NA drop and normalization, 
  # but dropping columns [A,B,C] and keeping 10% of dataset 
  # as test set.
  python run.py --no-drop-na --no-normalize --drop-columns A,B,C --test-size 0.1

  \b
  # Run the pipeline with Quality Gate for accuracy set at 90% for train set 
  # and 85% for test set. If any of accuracies will be lower - pipeline will fail.
  python run.py --min-train-accuracy 0.9 --min-test-accuracy 0.85 --fail-on-accuracy-quality-gates


"""
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=False,
    help="Disable caching for the pipeline run.",
)
@click.option(
    "--no-drop-na",
    is_flag=True,
    default=False,
    help="Whether to skip dropping rows with missing values in the dataset.",
)
@click.option(
    "--no-normalize",
    is_flag=True,
    default=False,
    help="Whether to skip normalization in the dataset.",
)
@click.option(
    "--drop-columns",
    default=None,
    type=click.STRING,
    help="Comma-separated list of columns to drop from the dataset.",
)
@click.option(
    "--test-size",
    default=0.2,
    type=click.FloatRange(0.0, 1.0),
    help="Proportion of the dataset to include in the test split.",
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
    "--fail-on-accuracy-quality-gates",
    is_flag=True,
    default=False,
    help="Whether to fail the pipeline run if the model evaluation step "
    "finds that the model is not accurate enough.",
)
@click.option(
    "--only-inference",
    is_flag=True,
    default=False,
    help="Whether to run only inference pipeline.",
)
def main(
    no_cache: bool = False,
    no_drop_na: bool = False,
    no_normalize: bool = False,
    drop_columns: Optional[str] = None,
    test_size: float = 0.2,
    min_train_accuracy: float = 0.8,
    min_test_accuracy: float = 0.8,
    fail_on_accuracy_quality_gates: bool = False,
    only_inference: bool = False,
):
    """Main entry point for the pipeline execution.

    This entrypoint is where everything comes together:

      * configuring pipeline with the required parameters
        (some of which may come from command line arguments)
      * launching the pipeline

    Args:
        no_cache: If `True` cache will be disabled.
        no_drop_na: If `True` NA values will not be dropped from the dataset.
        no_normalize: If `True` normalization will not be done for the dataset.
        drop_columns: List of comma-separated names of columns to drop from the dataset.
        test_size: Percentage of records from the training dataset to go into the test dataset.
        min_train_accuracy: Minimum acceptable accuracy on the train set.
        min_test_accuracy: Minimum acceptable accuracy on the test set.
        fail_on_accuracy_quality_gates: If `True` and any of minimal accuracy
            thresholds are violated - the pipeline will fail. If `False` thresholds will
            not affect the pipeline.
        only_inference: If `True` only inference pipeline will be triggered.
    """

    # Run a pipeline with the required parameters. This executes
    # all steps in the pipeline in the correct order using the orchestrator
    # stack component that is configured in your active ZenML stack.
    pipeline_args = {}
    if no_cache:
        pipeline_args["enable_cache"] = False

    if not only_inference:
        # Execute Training Pipeline
        run_args_train = {
            "drop_na": not no_drop_na,
            "normalize": not no_normalize,
            "test_size": test_size,
            "min_train_accuracy": min_train_accuracy,
            "min_test_accuracy": min_test_accuracy,
            "fail_on_accuracy_quality_gates": fail_on_accuracy_quality_gates,
        }
        if drop_columns:
            run_args_train["drop_columns"] = drop_columns.split(",")

        pipeline_args["config_path"] = os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "configs",
            "train_config.yaml",
        )
        pipeline_args[
            "run_name"
        ] = f"supply_chain_forecasting_training_run_{dt.now().strftime('%Y_%m_%d_%H_%M_%S')}"
        supply_chain_forecast_training.with_options(**pipeline_args)(**run_args_train)
        logger.info("Training pipeline finished successfully!")


    # Execute Batch Inference Pipeline
    run_args_inference = {}
    pipeline_args["config_path"] = os.path.join(
        os.path.dirname(os.path.realpath(__file__)),
        "configs",
        "inference_config.yaml",
    )
    pipeline_args[
        "run_name"
    ] = f"supply_chain_forecasting_batch_inference_run_{dt.now().strftime('%Y_%m_%d_%H_%M_%S')}"
    supply_chain_forecast_batch_inference.with_options(**pipeline_args)(**run_args_inference)



if __name__ == "__main__":
    main()
