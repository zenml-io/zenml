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


import pandas as pd
from sklearn.base import ClassifierMixin

from zenml import step, log_metadata
from zenml.client import Client
from zenml.logger import get_logger

logger = get_logger(__name__)

experiment_tracker = Client().active_stack.experiment_tracker


@step(experiment_tracker=experiment_tracker.name)
def model_evaluator(
    model: ClassifierMixin,
    dataset_trn: pd.DataFrame,
    dataset_tst: pd.DataFrame,
    target: str,
    min_train_accuracy: float = 0.0,
    min_test_accuracy: float = 0.0,
    fail_on_accuracy_quality_gates: bool = False,
) -> None:
    """Evaluate a trained model.

    This is an example of a model evaluation step that takes in a model artifact
    previously trained by another step in your pipeline, and a training
    and validation data set pair which it uses to evaluate the model's
    performance. The model metrics are then returned as step output artifacts
    (in this case, the model accuracy on the train and test set).

    The suggested step implementation also outputs some warnings if the model
    performance does not meet some minimum criteria. This is just an example of
    how you can use steps to monitor your model performance and alert you if
    something goes wrong. As an alternative, you can raise an exception in the
    step to force the pipeline run to fail early and all subsequent steps to
    be skipped.

    This step is parameterized to configure the step independently of the step code,
    before running it in a pipeline. In this example, the step can be configured
    to use different values for the acceptable model performance thresholds and
    to control whether the pipeline run should fail if the model performance
    does not meet the minimum criteria. See the documentation for more
    information:

        https://docs.zenml.io/how-to/build-pipelines/use-pipeline-step-parameters

    Args:
        model: The pre-trained model artifact.
        dataset_trn: The train dataset.
        dataset_tst: The test dataset.
        target: Name of target columns in dataset.
        min_train_accuracy: Minimal acceptable training accuracy value.
        min_test_accuracy: Minimal acceptable testing accuracy value.
        fail_on_accuracy_quality_gates: If `True` a `RuntimeException` is raised
            upon not meeting one of the minimal accuracy thresholds.

    Raises:
        RuntimeError: if any of accuracies is lower than respective threshold
    """
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        roc_auc_score,
        confusion_matrix,
        classification_report,
    )
    import numpy as np
    import time
    import psutil
    import json
    from datetime import datetime

    # Start timing
    start_time = time.time()

    # Track Data Quality Metrics
    data_quality_metrics = {
        "train_dataset_size": int(len(dataset_trn)),
        "test_dataset_size": int(len(dataset_tst)),
        "train_features_count": int(len(dataset_trn.drop(columns=[target]).columns)),
        "train_missing_values_pct": float(dataset_trn.isnull().mean().mean() * 100),
        "test_missing_values_pct": float(dataset_tst.isnull().mean().mean() * 100),
    }
    
    # Log data quality metrics at the step level
    log_metadata({"data_quality": data_quality_metrics})

    # Get predictions
    X_train = dataset_trn.drop(columns=[target])
    y_train = dataset_trn[target]
    X_test = dataset_tst.drop(columns=[target])
    y_test = dataset_tst[target]

    y_train_pred = model.predict(X_train)
    y_test_pred = model.predict(X_test)

    # Try to get prediction probabilities if available
    try:
        y_train_proba = model.predict_proba(X_train)
        y_test_proba = model.predict_proba(X_test)
        has_predict_proba = True
    except (AttributeError, NotImplementedError):
        has_predict_proba = False

    # Calculate Performance Metrics
    performance_metrics = {
        "train_accuracy": float(accuracy_score(y_train, y_train_pred)),
        "test_accuracy": float(accuracy_score(y_test, y_test_pred)),
        "train_precision": float(precision_score(y_train, y_train_pred, average='weighted')),
        "test_precision": float(precision_score(y_test, y_test_pred, average='weighted')),
        "train_recall": float(recall_score(y_train, y_train_pred, average='weighted')),
        "test_recall": float(recall_score(y_test, y_test_pred, average='weighted')),
        "train_f1": float(f1_score(y_train, y_train_pred, average='weighted')),
        "test_f1": float(f1_score(y_test, y_test_pred, average='weighted')),
    }

    if has_predict_proba:
        performance_metrics.update({
            "train_roc_auc": float(roc_auc_score(y_train, y_train_proba[:, 1] if y_train_proba.shape[1] == 2 else y_train_proba, multi_class='ovr')),
            "test_roc_auc": float(roc_auc_score(y_test, y_test_proba[:, 1] if y_test_proba.shape[1] == 2 else y_test_proba, multi_class='ovr')),
        })

    # Generate confusion matrices - convert to list of lists with Python types
    train_cm = confusion_matrix(y_train, y_train_pred).tolist()
    train_cm = [[int(cell) for cell in row] for row in train_cm]
    
    test_cm = confusion_matrix(y_test, y_test_pred).tolist()
    test_cm = [[int(cell) for cell in row] for row in test_cm]
    
    # Generate classification reports - convert NumPy types to Python types
    train_report = classification_report(y_train, y_train_pred, output_dict=True)
    # Convert any NumPy types in the report
    _convert_dict_numpy_types(train_report)
    
    test_report = classification_report(y_test, y_test_pred, output_dict=True)
    # Convert any NumPy types in the report
    _convert_dict_numpy_types(test_report)

    # Track Resource Usage Metrics
    process = psutil.Process()
    memory_info = process.memory_info()
    resource_metrics = {
        "memory_usage_mb": float(memory_info.rss / 1024 / 1024),
        "cpu_percent": float(process.cpu_percent()),
    }

    # Track Time-based Metrics
    end_time = time.time()
    time_metrics = {
        "evaluation_time_seconds": float(end_time - start_time),
        "timestamp": datetime.now().isoformat(),
    }

    # Get model parameters if available
    try:
        model_params = model.get_params()
        # Convert any NumPy types in model parameters to Python types
        for key, value in model_params.items():
            if hasattr(value, 'item') and callable(getattr(value, "item")):
                model_params[key] = value.item()
    except:
        model_params = {"error": "Could not retrieve model parameters"}
        logger.warning("Could not log model parameters")

    # Log performance metrics at the step level
    log_metadata({"performance": performance_metrics})
    
    # Log confusion matrices
    log_metadata({
        "confusion_matrices": {
            "train": train_cm,
            "test": test_cm
        }
    })
    
    # Log classification reports
    log_metadata({
        "classification_reports": {
            "train": train_report,
            "test": test_report
        }
    })
    
    # Log resource usage and time metrics
    log_metadata({
        "resources": resource_metrics,
        "time": time_metrics
    })
    
    # Log model parameters
    log_metadata({
        "model_parameters": model_params
    })
    
    # Log evaluation metrics to the model as well
    log_metadata(
        metadata={
            "evaluation_metrics": performance_metrics,
            "confusion_matrices": {
                "train": train_cm,
                "test": test_cm
            },
            "classification_reports": {
                "train": train_report,
                "test": test_report
            }
        },
        infer_model=True,
    )

    # Check accuracy thresholds
    messages = []
    if performance_metrics["train_accuracy"] < min_train_accuracy:
        messages.append(
            f"Train accuracy {performance_metrics['train_accuracy'] * 100:.2f}% is below {min_train_accuracy * 100:.2f}% !"
        )
    if performance_metrics["test_accuracy"] < min_test_accuracy:
        messages.append(
            f"Test accuracy {performance_metrics['test_accuracy'] * 100:.2f}% is below {min_test_accuracy * 100:.2f}% !"
        )
    if fail_on_accuracy_quality_gates and messages:
        raise RuntimeError(
            "Model performance did not meet the minimum criteria:\n"
            + "\n".join(messages)
        )
    else:
        for message in messages:
            logger.warning(message)

    # Log the core metrics for easy access in the dashboard
    logger.info(f"Train accuracy: {performance_metrics['train_accuracy'] * 100:.2f}%")
    logger.info(f"Test accuracy: {performance_metrics['test_accuracy'] * 100:.2f}%")
    logger.info(f"Train F1 score: {performance_metrics['train_f1'] * 100:.2f}%")
    logger.info(f"Test F1 score: {performance_metrics['test_f1'] * 100:.2f}%")

# Helper function to recursively convert NumPy types in a dictionary
def _convert_dict_numpy_types(d):
    """Recursively convert NumPy types in a nested dictionary to Python types."""
    for key, value in d.items():
        if isinstance(value, dict):
            _convert_dict_numpy_types(value)
        elif hasattr(value, "item") and callable(getattr(value, "item")):
            d[key] = value.item()
        elif hasattr(value, "tolist") and callable(getattr(value, "tolist")):
            d[key] = value.tolist()
