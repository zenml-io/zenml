from zenml.exceptions import DoesNotExistException
from zenml.steps import StepContext, step
from zenml.steps.step_interfaces.base_alerter_step import BaseAlerterStepConfig


import numpy as np
from sklearn.base import ClassifierMixin
from sklearn.svm import SVC

from zenml.alerter.alerter_step import alerter_step
from zenml.integrations.sklearn.helpers.digits import get_digits
from zenml.pipelines import pipeline
from zenml.steps import Output, step


@step
def importer() -> Output(
    X_train=np.ndarray,
    X_test=np.ndarray,
    y_train=np.ndarray,
    y_test=np.ndarray,
):
    """Load the digits dataset as numpy arrays."""
    X_train, X_test, y_train, y_test = get_digits()
    return X_train, X_test, y_train, y_test


@step
def svc_trainer(
    X_train: np.ndarray,
    y_train: np.ndarray,
) -> ClassifierMixin:
    """Train a sklearn SVC classifier."""
    model = SVC(gamma=0.001)
    model.fit(X_train, y_train)
    return model


@step
def evaluator(
    X_test: np.ndarray,
    y_test: np.ndarray,
    model: ClassifierMixin,
) -> float:
    """Calculate the test set accuracy of an sklearn model."""
    test_acc = model.score(X_test, y_test)
    print(f"Test accuracy: {test_acc}")
    return test_acc


@step
def test_acc_formatter(test_acc: float) -> str:
    """Wrap given test accuracy in a nice text message."""
    return f"Test Accuracy: {test_acc}"


@pipeline
def slack_pipeline(importer, trainer, evaluator, formatter, alerter):
    """Train and evaluate a model and post the test accuracy to slack."""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    test_acc = evaluator(X_test=X_test, y_test=y_test, model=model)
    message = formatter(test_acc)
    alerter(message)


@step
def alerter_step(
    config: BaseAlerterStepConfig, context: StepContext, message: str
) -> bool:
    """Post a given message to the registered alerter component of the
    active stack.

    Args:
        config: Runtime configuration for the slack alerter.
        context: StepContext of the ZenML repository.
        message: Message to be posted.

    Returns:
        True if operation succeeded, else False.

    Raises:
        ValueError if active stack has no slack alerter.
    """

    # TODO: duplicate code with examples/feast_feature_store/run.py
    if not context.stack:
        raise DoesNotExistException(
            "No active stack is available. "
            "Please make sure that you have registered and set a stack."
        )
    if not context.stack.alerter:
        raise ValueError(
            "The active stack needs to have an alerter component registered "
            "to be able to use `alerter_step`. "
            "You can create a new stack with e.g. a Slack alerter component or update "
            "your existing stack to add this component, e.g.:\n\n"
            "  'zenml alerter register slack_alerter --flavor=slack' ...\n"
            "  'zenml stack register stack-name -al slack_alerter ...'\n"
        )

    response = context.stack.alerter.ask(message, config)
    print(response.body)
    return True


if __name__ == "__main__":
    slack_pipeline(
        importer=importer(),
        trainer=svc_trainer(),
        evaluator=evaluator(),
        formatter=test_acc_formatter(),
        alerter=alerter_step(),
    ).run()
