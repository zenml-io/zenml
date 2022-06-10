from zenml.steps import Output, step


@step
def get_first_num() -> Output(first_num=int):
    """Returns an integer."""
    return 10
