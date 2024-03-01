# Apache Software License 2.0
#
# Copyright (c) ZenML GmbH 2024. All rights reserved.
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

import os
from datetime import datetime as dt

import click
from pipelines import (
    nlp_use_case_deploy_pipeline,
    nlp_use_case_promote_pipeline,
    nlp_use_case_training_pipeline,
)

from zenml.enums import ModelStages
from zenml.logger import get_logger
from zenml.model.model import Model

logger = get_logger(__name__)


@click.command(
    help="""
ZenML NLP project CLI v0.0.1.

Run the ZenML NLP project model training pipeline with various
options.

Examples:


  \b
  # Run the pipeline with default options
  python run.py
               
  \b
  # Run the pipeline without cache
  python run.py --no-cache

  \b
  # Run the pipeline without NA drop and normalization, 
  # but dropping columns [A,B,C] and keeping 10% of dataset 
  # as test set.
  python run.py --num-epochs 3 --train-batch-size 8 --eval-batch-size 8

  \b
  # Run the pipeline with Quality Gate for accuracy set at 90% for train set 
  # and 85% for test set. If any of accuracies will be lower - pipeline will fail.
  python run.py --min-train-accuracy 0.9 --min-test-accuracy 0.85 --fail-on-accuracy-quality-gates


"""
)
@click.option(
    "--no-cache",
    is_flag=True,
    default=True,
    help="Disable caching for the pipeline run.",
)
@click.option(
    "--num-epochs",
    default=1,
    type=click.INT,
    help="Number of epochs to train the model for.",
)
@click.option(
    "--train-batch-size",
    default=8,
    type=click.INT,
    help="Batch size for training the model.",
)
@click.option(
    "--eval-batch-size",
    default=8,
    type=click.INT,
    help="Batch size for evaluating the model.",
)
@click.option(
    "--learning-rate",
    default=2e-5,
    type=click.FLOAT,
    help="Learning rate for training the model.",
)
@click.option(
    "--weight-decay",
    default=0.01,
    type=click.FLOAT,
    help="Weight decay for training the model.",
)
@click.option(
    "--training-pipeline",
    is_flag=True,
    default=True,
    help="Whether to run the pipeline that train the model to staging.",
)
@click.option(
    "--promoting-pipeline",
    is_flag=True,
    default=True,
    help="Whether to run the pipeline that promotes the model to staging.",
)
@click.option(
    "--deploying-pipeline",
    is_flag=True,
    default=False,
    help="Whether to run the pipeline that deploys the model to selected deployment platform.",
)
@click.option(
    "--deployment-app-title",
    default="Sentiment Analyzer",
    type=click.STRING,
    help="Title of the Gradio interface.",
)
@click.option(
    "--deployment-app-description",
    default="Sentiment Analyzer",
    type=click.STRING,
    help="Description of the Gradio interface.",
)
@click.option(
    "--deployment-app-interpretation",
    default="default",
    type=click.STRING,
    help="Interpretation mode for the Gradio interface.",
)
@click.option(
    "--deployment-app-example",
    default="",
    type=click.STRING,
    help="Comma-separated list of examples to show in the Gradio interface.",
)
@click.option(
    "--zenml-model-name",
    default="sentiment_analysis",
    type=click.STRING,
    help="Name of the ZenML Model.",
)
def main(
    no_cache: bool = True,
    num_epochs: int = 3,
    train_batch_size: int = 8,
    eval_batch_size: int = 8,
    learning_rate: float = 2e-5,
    weight_decay: float = 0.01,
    training_pipeline: bool = True,
    promoting_pipeline: bool = True,
    deploying_pipeline: bool = False,
    deployment_app_title: str = "Sentiment Analyzer",
    deployment_app_description: str = "Sentiment Analyzer",
    deployment_app_interpretation: str = "default",
    deployment_app_example: str = "",
    zenml_model_name: str = "sentiment_analysis",
):
    """Main entry point for the pipeline execution.

    This entrypoint is where everything comes together:

      * configuring pipeline with the required parameters
        (some of which may come from command line arguments)
      * launching the pipeline

    Args:
        no_cache: If `True` cache will be disabled.
    """

    # Run a pipeline with the required parameters. This executes
    # all steps in the pipeline in the correct order using the orchestrator
    # stack component that is configured in your active ZenML stack.
    pipeline_args = {
        "config_path": os.path.join(
            os.path.dirname(os.path.realpath(__file__)),
            "config.yaml",
        )
    }
    if no_cache:
        pipeline_args["enable_cache"] = False

    if training_pipeline:
        # Execute Training Pipeline
        run_args_train = {
            "num_epochs": num_epochs,
            "train_batch_size": train_batch_size,
            "eval_batch_size": eval_batch_size,
            "learning_rate": learning_rate,
            "weight_decay": weight_decay,
        }

        model = Model(
            name=zenml_model_name,
            license="apache",
            description="Show case Model Control Plane.",
            delete_new_version_on_failure=True,
            tags=["sentiment_analysis", "huggingface"],
        )

        pipeline_args["model"] = model

        pipeline_args["run_name"] = (
            f"nlp_use_case_run_{dt.now().strftime('%Y_%m_%d_%H_%M_%S')}"
        )
        nlp_use_case_training_pipeline.with_options(**pipeline_args)(
            **run_args_train
        )
        logger.info("Training pipeline finished successfully!")

    # Execute Promoting Pipeline
    if promoting_pipeline:
        run_args_promoting = {}
        model = Model(name=zenml_model_name, version=ModelStages.LATEST)
        pipeline_args["model"] = model
        pipeline_args["run_name"] = (
            f"nlp_use_case_promoting_pipeline_run_{dt.now().strftime('%Y_%m_%d_%H_%M_%S')}"
        )
        nlp_use_case_promote_pipeline.with_options(**pipeline_args)(
            **run_args_promoting
        )
        logger.info("Promoting pipeline finished successfully!")

    if deploying_pipeline:
        pipeline_args["enable_cache"] = False
        # Deploying pipeline has new ZenML model config
        model = Model(
            name=zenml_model_name,
            version=ModelStages("staging"),
        )
        pipeline_args["model"] = model
        run_args_deploying = {
            "title": deployment_app_title,
            "description": deployment_app_description,
            "interpretation": deployment_app_interpretation,
            "example": deployment_app_example,
        }
        pipeline_args["run_name"] = (
            f"nlp_use_case_deploy_pipeline_run_{dt.now().strftime('%Y_%m_%d_%H_%M_%S')}"
        )
        nlp_use_case_deploy_pipeline.with_options(**pipeline_args)(
            **run_args_deploying
        )
        logger.info("Deploying pipeline finished successfully!")


if __name__ == "__main__":
    main()
