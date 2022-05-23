from zenml.pipelines import pipeline


@pipeline(enable_cache=False)
def training_pipeline(
    training_data_loader,
    skew_comparison,
    trainer,
    evaluator,
    deployment_trigger,
    model_deployer,
):
    """Train, evaluate, and deploy a model."""
    X_train, X_test, y_train, y_test = training_data_loader()
    skew_comparison(X_train, X_test)
    model = trainer(X_train=X_train, y_train=y_train)
    test_acc = evaluator(X_test=X_test, y_test=y_test, model=model)
    deployment_decision = deployment_trigger(test_acc)
    model_deployer(deployment_decision, model)
