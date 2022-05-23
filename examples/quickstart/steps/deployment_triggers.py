from zenml.steps import step


@step
def deployment_trigger(test_acc: float) -> bool:
    """Only deploy if the test accuracy > 90%."""
    return test_acc > 0.9
