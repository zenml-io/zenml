from steps import evaluator, importer, svc_trainer_mlflow

from zenml.alerter.alerter_step import alerter_ask_step
from zenml.integrations.mlflow.steps import mlflow_model_deployer_step
from zenml.pipelines import pipeline
from zenml.steps import step


@step
def test_acc_formatter(test_acc: float) -> str:
    """Wrap given test accuracy in a nice text message."""
    return (
        f"Model training finished. Test accuracy: {test_acc}. "
        f"Deploy now? [approve | reject]"
    )


@pipeline(enable_cache=False)
def slack_ask_pipeline(
    importer, trainer, evaluator, formatter, alerter, deployer
):
    """Train and evaluate a model and asks user in Slack whether to deploy."""
    X_train, X_test, y_train, y_test = importer()
    model = trainer(X_train=X_train, y_train=y_train)
    test_acc = evaluator(X_test=X_test, y_test=y_test, model=model)
    message = formatter(test_acc)
    approved = alerter(message)
    deployer(approved, model)


if __name__ == "__main__":
    slack_ask_pipeline(
        importer=importer(),
        trainer=svc_trainer_mlflow(),
        evaluator=evaluator(),
        formatter=test_acc_formatter(),
        alerter=alerter_ask_step(),
        deployer=mlflow_model_deployer_step(),
    ).run()
