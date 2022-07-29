from zenml.steps import step


@step
def deployment_trigger() -> bool:
    return True  # TODO: only return True if dataset changed
