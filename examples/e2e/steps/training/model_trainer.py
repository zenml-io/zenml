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
#

import platform
import time
from datetime import datetime

import mlflow
import numpy as np
import pandas as pd
import psutil
from sklearn.base import ClassifierMixin
from sklearn.model_selection import cross_val_score
from typing_extensions import Annotated

from zenml import ArtifactConfig, get_step_context, log_metadata, step
from zenml.client import Client
from zenml.integrations.mlflow.experiment_trackers import (
    MLFlowExperimentTracker,
)
from zenml.integrations.mlflow.steps.mlflow_registry import (
    mlflow_register_model_step,
)
from zenml.logger import get_logger

logger = get_logger(__name__)

experiment_tracker = Client().active_stack.experiment_tracker

if not experiment_tracker or not isinstance(
    experiment_tracker, MLFlowExperimentTracker
):
    raise RuntimeError(
        "Your active stack needs to contain a MLFlow experiment tracker for "
        "this example to work."
    )


@step(experiment_tracker=experiment_tracker.name)
def model_trainer(
    dataset_trn: pd.DataFrame,
    model: ClassifierMixin,
    target: str,
    name: str,
) -> Annotated[
    ClassifierMixin, ArtifactConfig(name="model", is_model_artifact=True)
]:
    """Configure and train a model on the training dataset.

    This is an example of a model training step that takes in a dataset artifact
    previously loaded and pre-processed by other steps in your pipeline, then
    configures and trains a model on it. The model is then returned as a step
    output artifact.

    Model training steps should have caching disabled if they are not
    deterministic (i.e. if the model training involve some random processes
    like initializing weights or shuffling data that are not controlled by
    setting a fixed random seed). This example step ensures the outcome is
    deterministic by initializing the model with a fixed random seed.

    This step is parameterized to configure the step independently of the step code,
    before running it in a pipeline. In this example, the step can be configured
    to use a different model, change the random seed, or pass different
    hyperparameters to the model constructor. See the documentation for more
    information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        dataset_trn: The preprocessed train dataset.
        model: The model instance to train.
        target: Name of target columns in dataset.
        name: The name of the model.

    Returns:
        The trained model artifact.
    """
    # Start timing
    start_time = time.time()

    # Collect dataset characteristics
    dataset_metrics = {
        "dataset_size": int(len(dataset_trn)),
        "feature_count": int(len(dataset_trn.drop(columns=[target]).columns)),
        "class_count": int(len(dataset_trn[target].unique())),
    }
    
    # Log dataset metrics to step metadata
    log_metadata({"dataset_metrics": dataset_metrics})
    

    # Track initial resource usage
    process = psutil.Process()
    initial_memory = process.memory_info().rss / 1024 / 1024  # MB

    # Train the model
    logger.info(f"Training model {model}...")
    mlflow.sklearn.autolog()
    model.fit(
        dataset_trn.drop(columns=[target]),
        dataset_trn[target],
    )

    # Calculate training time and resource usage
    end_time = time.time()
    final_memory = process.memory_info().rss / 1024 / 1024  # MB

    resource_metrics = {
        "training_time_seconds": float(end_time - start_time),
        "memory_usage_mb": float(final_memory),
        "memory_increase_mb": float(final_memory - initial_memory),
        "cpu_percent": float(process.cpu_percent()),
        "timestamp": datetime.now().isoformat(),
    }
    
    # Log resource metrics
    log_metadata({"resource_metrics": resource_metrics})

    # Get model parameters
    try:
        model_params = model.get_params()
        # Convert any NumPy types in model parameters to Python types
        for key, value in model_params.items():
            if hasattr(value, "item") and callable(getattr(value, "item")):
                model_params[key] = value.item()
    except:
        model_params = {"error": "Could not retrieve model parameters"}
        logger.warning("Could not log model parameters")
    
    # Build comprehensive model metadata
    model_metadata = {
        "model_name": name,
        "model_type": type(model).__name__,
        "model_framework": type(model).__module__.split('.')[0],
        "model_parameters": model_params,
        "training_timestamp": datetime.now().isoformat(),
        "python_version": platform.python_version(),
        "system_platform": platform.platform(),
    }
    
    # Log model metadata to step
    log_metadata({"model_metadata": model_metadata})
    
    # Log individual metadata groups to the model artifact itself
    # This avoids the type error with nested dictionaries
    log_metadata(
        metadata={"dataset_metrics": dataset_metrics},
        infer_model=True,
    )
    
    log_metadata(
        metadata={"resource_metrics": resource_metrics},
        infer_model=True,
    )
    
    log_metadata(
        metadata={"model_info": model_metadata},
        infer_model=True,
    )
    
    log_metadata(metadata={
        "train_dataset_size": int(len(dataset_trn)),
        "train_feature_count": int(len(dataset_trn.drop(columns=[target]).columns)),
        "training_time_seconds": float(end_time - start_time),
        "training_memory_usage_mb": float(final_memory),
        "training_memory_increase_mb": float(final_memory - initial_memory),
        "training_cpu_percent": float(process.cpu_percent()),
        "training_timestamp": datetime.now().isoformat(),
    })
        
    # Register the model (still using MLflow for the registry as in the original example)
    mlflow_register_model_step.entrypoint(model, name=name)

    # Keep track of mlflow version for future use
    model_registry = Client().active_stack.model_registry
    if model_registry:
        version = model_registry.get_latest_model_version(name=name, stage=None)
        if version:
            # Add registry version to model metadata
            log_metadata(
                metadata={"model_registry_version": str(version.version)},
                infer_model=True,
            )

    # Log some summary information for easy access
    logger.info(f"Model '{name}' training completed")
    logger.info(f"Dataset size: {dataset_metrics['dataset_size']} samples")
    logger.info(f"Training time: {resource_metrics['training_time_seconds']:.2f} seconds")

    return model
