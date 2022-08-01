from zenml.steps import step


@step
def deployment_trigger() -> bool:
    return True
