from zenml.utils.string_utils import random_str


def sample_name(prefix: str = "aria") -> str:
    """Function to get random username."""
    return f"{prefix}-{random_str(4)}".lower()
