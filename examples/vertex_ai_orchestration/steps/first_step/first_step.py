from zenml import step
from zenml.steps import Output


@step
def get_first_num() -> Output(first_num=int):
    """Returns an integer."""
    return 10
