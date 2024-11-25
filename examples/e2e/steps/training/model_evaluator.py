# 


import mlflow
import pandas as pd
from sklearn.base import ClassifierMixin
from zenml import step
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
    ### ADD YOUR OWN CODE HERE - THIS IS JUST AN EXAMPLE ###
    # Calculate the model accuracy on the train and test set
    trn_acc = model.score(
        dataset_trn.drop(columns=[target]),
        dataset_trn[target],
    )
    logger.info(f"Train accuracy={trn_acc*100:.2f}%")
    tst_acc = model.score(
        dataset_tst.drop(columns=[target]),
        dataset_tst[target],
    )
    logger.info(f"Test accuracy={tst_acc*100:.2f}%")
    mlflow.log_metric("testing_accuracy_score", tst_acc)

    messages = []
    if trn_acc < min_train_accuracy:
        messages.append(
            f"Train accuracy {trn_acc*100:.2f}% is below {min_train_accuracy*100:.2f}% !"
        )
    if tst_acc < min_test_accuracy:
        messages.append(
            f"Test accuracy {tst_acc*100:.2f}% is below {min_test_accuracy*100:.2f}% !"
        )
    if fail_on_accuracy_quality_gates and messages:
        raise RuntimeError(
            "Model performance did not meet the minimum criteria:\n"
            + "\n".join(messages)
        )
    else:
        for message in messages:
            logger.warning(message)

    ### YOUR CODE ENDS HERE ###
