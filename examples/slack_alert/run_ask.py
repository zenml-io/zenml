from steps import evaluator, importer, svc_trainer

from zenml.alerter.alerter_step import alerter_ask_step
from zenml.pipelines import pipeline
from zenml.steps import step


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


if __name__ == "__main__":
    slack_pipeline(
        importer=importer(),
        trainer=svc_trainer(),
        evaluator=evaluator(),
        formatter=test_acc_formatter(),
        alerter=alerter_ask_step(),
    ).run()
