from zenml.utils.string_utils import random_str


def sample_name(prefix: str = "aria") -> str:
    """Function to get random username."""
    return f"{prefix}_{random_str(4)}"
