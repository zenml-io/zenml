from zenml.pipelines import pipeline


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
