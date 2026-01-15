from zenml.utils.string_utils import random_str


def sample_name(prefix: str = "aria", random_factor: int = 4) -> str:
    """Function to get random username."""
    return f"{prefix}-{random_str(random_factor)}".lower()
